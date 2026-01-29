import os
import requests
import logging
import hashlib
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
