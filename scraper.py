import os
import requests
import logging
import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime
from markdownify import markdownify as md
from requests.auth import HTTPBasicAuth
from config import API_BASE_URL

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
    
    def clear_output_directory(self):
        """Clears all files in the output directory."""
        for filename in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logging.error(f"Error deleting file {file_path}: {e}")

    def fetch_articles(self, limit):
        """Fetches articles from Zendesk Help Center API.

        Args:
            limit (int): The maximum number of articles to fetch per page.
        
        Returns:
            list: A list of article dictionaries fetched from the API, each with 'last_modified' timestamp.
        """
        articles = []
        zendesk_email = os.getenv("ZENDESK_EMAIL", "ducthai060501@gmail.com")
        auth = HTTPBasicAuth(f'{zendesk_email}/token', os.getenv("ZENDESK_API_TOKEN"))
        url = f"{API_BASE_URL}"
        # Parameters
        params = {
            'per_page': limit  # Fetch articles per page
        }
        logging.info(f"Fetching articles from {url}...")
        try:
            response = requests.get(url, auth=auth, params=params)
            response.raise_for_status()
            
            # Capture Last-Modified header from response
            last_modified_header = response.headers.get('Last-Modified')
            api_last_modified = None
            if last_modified_header:
                try:
                    api_last_modified = parsedate_to_datetime(last_modified_header).isoformat()
                except (ValueError, TypeError) as e:
                    logging.warning(f"Could not parse Last-Modified header: {e}")
            
            data = response.json()
            fetched_articles = data.get('articles', [])
            
            # Add last_modified timestamp to each article
            # Use API response header if available, otherwise use article's updated_at
            for article in fetched_articles:
                # Prefer API response Last-Modified, fallback to article's updated_at field
                if api_last_modified:
                    article['_api_last_modified'] = api_last_modified
                elif article.get('updated_at'):
                    article['_api_last_modified'] = article['updated_at']
                else:
                    article['_api_last_modified'] = None
            
            articles.extend(fetched_articles)
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
            tuple: (filepath, file_content, content_hash, last_modified)
                   filepath (str): Path where the markdown file should be saved.
                   file_content (str): The converted markdown content with headers.
                   content_hash (str): MD5 hash of the content for delta tracking.
                   last_modified (str): ISO format timestamp from API (Last-Modified header or updated_at).
                   Returns (None, None, None, None) if the article has no body.
        """
        title = article.get('title', 'Untitled')
        body = article.get('body', '')
        article_id = article.get('id')
        html_url = article.get('html_url')
        
        if not body:
            return None, None, None, None

        markdown_content = md(body, heading_style="ATX")
        file_content = f"# {title}\n\nArticle URL: {html_url}\n\n{markdown_content}"
        
        # Determine filename
        safe_title = "".join([c if c.isalnum() else "-" for c in title]).strip("-")
        filename = f"{article_id}-{safe_title}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        # Calculate hash
        content_hash = hashlib.md5(file_content.encode('utf-8')).hexdigest()
        
        # Get last_modified timestamp (from API response or article metadata)
        last_modified = article.get('_api_last_modified') or article.get('updated_at')
        
        return filepath, file_content, content_hash, last_modified
