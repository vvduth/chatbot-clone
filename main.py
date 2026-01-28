import os
import requests
import json
import logging
import hashlib
from markdownify import markdownify as md
from dotenv import load_dotenv
from openai import OpenAI
from requests.auth import HTTPBasicAuth

# Load environment variables
load_dotenv()

# Configuration
ZENDESK_DOMAIN = "support.optisigns.com"
API_BASE_URL = f"https://{ZENDESK_DOMAIN}/api/v2/help_center/articles.json"
OUTPUT_DIR = "data/articles"
STATE_FILE = "data/state.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StateManager:
    """Manages the state of processed articles and the vector store ID."""

    def __init__(self, state_file):
        """Initializes the StateManager.
        
        Args:
            state_file (str): The path to the JSON file where state is stored.
        """
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self):
        """Loads the state from the JSON file. 
        
        Returns:
            dict: The loaded state or a default empty state if the file doesn't exist.
        """
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {"articles": {}, "vector_store_id": None}

    def save_state(self):
        """Saves the current state to the JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_article_state(self, article_id):
        """Retrieves the state for a specific article.
        
        Args:
           article_id (int|str): The unique identifier of the article.
           
        Returns:
           dict: The state dictionary for the article (e.g. hash, openai_file_id).
        """
        return self.state["articles"].get(str(article_id), {})

    def update_article_state(self, article_id, file_hash, openai_file_id=None):
        """Updates the state for an article.
        
        Args:
            article_id (int|str): The unique identifier of the article.
            file_hash (str): The MD5 hash of the article content.
            openai_file_id (str, optional): The ID of the file uploaded to OpenAI.
        """
        self.state["articles"][str(article_id)] = {
            "hash": file_hash,
            "openai_file_id": openai_file_id,
            "updated_at": "now" # In real app use datetime
        }
    
    def get_vector_store_id(self):
        """Gets the stored OpenAI Vector Store ID.

        Returns:
            str: The Vector Store ID, or None if not set.
        """
        return self.state.get("vector_store_id")

    def set_vector_store_id(self, vs_id):
        """Sets and saves the OpenAI Vector Store ID.

        Args:
            vs_id (str): The Vector Store ID to save.
        """
        self.state["vector_store_id"] = vs_id

class VectorStoreManager:
    """Handles interactions with OpenAI's Vector Store API."""

    def __init__(self, api_key):
        """Initializes the VectorStoreManager.

        Args:
            api_key (str): The OpenAI API key.
        """
        self.client = OpenAI(api_key=api_key) if api_key else None
        if not self.client:
            logging.warning("OpenAI API Key not found. OpenAI integration disabled.")

    def get_or_create_vector_store(self, state_manager, name="OptiBot Knowledge Base"):
        """Retrieves an existing Vector Store or creates a new one if not found.

        Args:
            state_manager (StateManager): The state manager to retrieve/save the stored ID.
            name (str): The name for the new Vector Store if creation is needed.

        Returns:
            str: The Vector Store ID.
        """
        if not self.client: return None
        
        vs_id = state_manager.get_vector_store_id()
        if vs_id:
            try:
                # Validate it exists
                self.client.beta.vector_stores.retrieve(vs_id)
                logging.info(f"Using existing Vector Store: {vs_id}")
                return vs_id
            except Exception:
                logging.warning(f"Saved Vector Store {vs_id} not found/accessible. Creating new one.")
        
        try:
            vs = self.client.beta.vector_stores.create(name=name)
            vs_id = vs.id
            state_manager.set_vector_store_id(vs_id)
            logging.info(f"Created new Vector Store: {vs_id}")
            return vs_id
        except Exception as e:
            logging.error(f"Failed to create Vector Store: {e}")
            return None

    def upload_file(self, filepath):
        """Uploads a file to OpenAI for 'assistants' purpose.
        
        Args:
            filepath (str): The path to the local file to upload.

        Returns:
            str: The OpenAI File ID if successful, else None.
        """
        if not self.client: return "mock_file_id"
        
        try:
            with open(filepath, "rb") as file_stream:
                file_obj = self.client.files.create(
                    file=file_stream,
                    purpose="assistants"
                )
            logging.info(f"Uploaded file {filepath} to OpenAI: {file_obj.id}")
            return file_obj.id
        except Exception as e:
            logging.error(f"Failed to upload {filepath}: {e}")
            return None

    def add_file_to_vector_store(self, vector_store_id, file_id):
        """Links an uploaded file to a Vector Store.

        Args:
            vector_store_id (str): The ID of the Vector Store.
            file_id (str): The ID of the uploaded file.
        """
        if not self.client or not vector_store_id or not file_id: return
        
        try:
            self.client.beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            logging.info(f"Linked file {file_id} to Vector Store {vector_store_id}")
        except Exception as e:
            logging.error(f"Failed to link file {file_id}: {e}")

class Scraper:
    """Handles fetching and processing of articles from Zendesk."""

    def __init__(self, output_dir):
        """Initializes the Scraper.

        Args:
           output_dir (str): The directory where processed markdown files will be saved.
        """
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def fetch_articles(self, limit=30):
        """Fetches articles from Zendesk Help Center API.

        Args:
            limit (int): The maximum number of articles to fetch per page.
        
        Returns:
            list: A list of article dictionaries fetched from the API.
        """
        articles = []
        auth = HTTPBasicAuth('ducthai060501@gmail.com/token', os.getenv("ZENDESK_API_TOKEN"))
        url = f"{API_BASE_URL}?per_page={limit}"
        # Parameters
        params = {
            'per_page': limit  # Fetch 30 articles
        }
        logging.info(f"Fetching articles from {url}...")
        try:
            response = requests.get(url, auth=auth, params=params)
            response.raise_for_status()
            data = response.json()
            articles.extend(data.get('articles', []))
            logging.info(f"Fetched {len(articles)} articles.")
            return articles
        except Exception as e:
            logging.error(f"Error fetching articles: {e}")
            return []

    def process_article(self, article):
        """Converts an article's HTML body to Markdown and determines content hash.

        Args:
            article (dict): The article data from Zendesk API.

        Returns:
            tuple: (filepath, file_content, content_hash)
                   filepath (str): Path where the markdown file should be saved.
                   file_content (str): The converted markdown content with headers.
                   content_hash (str): MD5 hash of the content for delta tracking.
                   Returns (None, None, None) if the article has no body.
        """
        title = article.get('title', 'Untitled')
        body = article.get('body', '')
        article_id = article.get('id')
        html_url = article.get('html_url')
        
        if not body:
            return None, None, None

        markdown_content = md(body, heading_style="ATX")
        file_content = f"# {title}\n\nArticle URL: {html_url}\n\n{markdown_content}"
        
        # Determine filename
        safe_title = "".join([c if c.isalnum() else "-" for c in title]).strip("-")
        filename = f"{article_id}-{safe_title}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        # Calculate hash
        content_hash = hashlib.md5(file_content.encode('utf-8')).hexdigest()
        
        return filepath, file_content, content_hash

# def main():
#     """Main execution entry point.
    
#     Orchestrates the scraping, processing, state management, and OpenAI upload workflow.
#     """
#     state_manager = StateManager(STATE_FILE)
#     vector_manager = VectorStoreManager(OPENAI_API_KEY)
#     scraper = Scraper(OUTPUT_DIR)
    
#     # Initialize Vector Store
#     vs_id = vector_manager.get_or_create_vector_store(state_manager)
    
#     articles = scraper.fetch_articles(limit=30)
    
#     stats = {"added": 0, "updated": 0, "skipped": 0}
    
#     for article in articles:
#         article_id = article.get('id')
#         filepath, content, content_hash = scraper.process_article(article)
        
#         if not filepath:
#             continue
            
#         # Check state
#         current_state = state_manager.get_article_state(article_id)
#         last_hash = current_state.get("hash")
        
#         if last_hash == content_hash and os.path.exists(filepath):
#             logging.info(f"Skipping {article_id} (No changes)")
#             stats["skipped"] += 1
#             continue

#         # Save file locally
#         with open(filepath, "w", encoding="utf-8") as f:
#             f.write(content)
        
#         action = "Updated" if last_hash else "Added"
#         logging.info(f"{action} local file: {filepath}")
        
#         # Upload to OpenAI
#         if vs_id:
#             file_id = vector_manager.upload_file(filepath)
#             if file_id:
#                 vector_manager.add_file_to_vector_store(vs_id, file_id)
#                 state_manager.update_article_state(article_id, content_hash, file_id)
#                 if action == "Updated":
#                     stats["updated"] += 1
#                 else: 
#                     stats["added"] += 1
#         else:
#             # Update state even if no OpenAI (local only mode)
#              state_manager.update_article_state(article_id, content_hash, None)
#              if action == "Updated":
#                  stats["updated"] += 1
#              else:
#                  stats["added"] += 1

#     state_manager.save_state()
#     logging.info(f"Job Complete. Stats: {stats}")


def main():
    """Main execution entry point.
    
    Orchestrates the scraping, processing, state management, and OpenAI upload workflow.
    """
    scrapper = Scraper(OUTPUT_DIR)
    articles = scrapper.fetch_articles(limit=1)
    print(articles)

if __name__ == "__main__":
    main()
