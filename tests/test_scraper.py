"""
Unit tests for scraper.py module.
"""
import os
import hashlib
import pytest
from unittest.mock import patch, Mock, MagicMock
from scraper import Scraper


class TestScraper:
    """Test cases for Scraper class."""
    
    def test_init_creates_output_dir(self, temp_dir):
        """Test that Scraper creates output directory if it doesn't exist."""
        output_dir = os.path.join(temp_dir, "new_dir")
        scraper = Scraper(output_dir)
        
        assert os.path.exists(output_dir)
        assert scraper.output_dir == output_dir
    
    def test_init_uses_existing_output_dir(self, temp_output_dir):
        """Test that Scraper uses existing output directory."""
        scraper = Scraper(temp_output_dir)
        
        assert os.path.exists(temp_output_dir)
        assert scraper.output_dir == temp_output_dir
    
    @patch('scraper.requests.get')
    @patch.dict(os.environ, {"ZENDESK_API_TOKEN": "test_token"})
    def test_fetch_articles_success(self, mock_get, temp_output_dir, mock_requests_response):
        """Test successful article fetching."""
        mock_get.return_value = mock_requests_response
        
        scraper = Scraper(temp_output_dir)
        articles = scraper.fetch_articles(limit=10)
        
        assert len(articles) == 1
        assert articles[0]["id"] == 12345
        assert articles[0]["title"] == "Test Article"
        mock_get.assert_called_once()
        mock_requests_response.raise_for_status.assert_called_once()
    
    @patch('scraper.requests.get')
    @patch.dict(os.environ, {"ZENDESK_API_TOKEN": "test_token"})
    def test_fetch_articles_with_limit(self, mock_get, temp_output_dir, mock_requests_response):
        """Test fetching articles with limit parameter."""
        mock_get.return_value = mock_requests_response
        
        scraper = Scraper(temp_output_dir)
        articles = scraper.fetch_articles(limit=5)
        
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['per_page'] == 5
    
    @patch('scraper.requests.get')
    @patch.dict(os.environ, {"ZENDESK_API_TOKEN": "test_token"})
    def test_fetch_articles_with_none_limit(self, mock_get, temp_output_dir, mock_requests_response):
        """Test fetching articles with None limit."""
        mock_get.return_value = mock_requests_response
        
        scraper = Scraper(temp_output_dir)
        articles = scraper.fetch_articles(limit=None)
        
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['per_page'] is None
    
    @patch('scraper.requests.get')
    @patch.dict(os.environ, {"ZENDESK_API_TOKEN": "test_token"})
    def test_fetch_articles_empty_response(self, mock_get, temp_output_dir):
        """Test handling empty API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"articles": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        scraper = Scraper(temp_output_dir)
        articles = scraper.fetch_articles(limit=10)
        
        assert articles == []
    
    @patch('scraper.requests.get')
    @patch.dict(os.environ, {"ZENDESK_API_TOKEN": "test_token"})
    def test_fetch_articles_http_error(self, mock_get, temp_output_dir):
        """Test handling HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response
        
        scraper = Scraper(temp_output_dir)
        articles = scraper.fetch_articles(limit=10)
        
        assert articles == []
    
    @patch('scraper.requests.get')
    @patch.dict(os.environ, {"ZENDESK_API_TOKEN": "test_token"})
    def test_fetch_articles_network_error(self, mock_get, temp_output_dir):
        """Test handling network errors."""
        mock_get.side_effect = Exception("Network error")
        
        scraper = Scraper(temp_output_dir)
        articles = scraper.fetch_articles(limit=10)
        
        assert articles == []
    
    @patch('scraper.requests.get')
    @patch.dict(os.environ, {"ZENDESK_API_TOKEN": "test_token"})
    def test_fetch_articles_authentication(self, mock_get, temp_output_dir, mock_requests_response):
        """Test that authentication is correctly set up."""
        mock_get.return_value = mock_requests_response
        
        scraper = Scraper(temp_output_dir)
        scraper.fetch_articles(limit=10)
        
        call_args = mock_get.call_args
        assert call_args[1]['auth'] is not None
    
    def test_process_article_success(self, temp_output_dir, sample_article):
        """Test successful article processing."""
        scraper = Scraper(temp_output_dir)
        filepath, content, content_hash, last_modified = scraper.process_article(sample_article)
        
        assert filepath is not None
        assert content is not None
        assert content_hash is not None
        assert "Test Article" in content
        assert "https://support.optisigns.com/articles/12345" in content
        assert str(sample_article["id"]) in filepath
        assert filepath.endswith(".md")
    
    def test_process_article_no_body(self, temp_output_dir):
        """Test processing article with no body."""
        article = {
            "id": 12345,
            "title": "No Body Article",
            "body": "",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        scraper = Scraper(temp_output_dir)
        filepath, content, content_hash, last_modified = scraper.process_article(article)
        
        assert filepath is None
        assert content is None
        assert content_hash is None
        assert last_modified is None
    
    def test_process_article_missing_body_key(self, temp_output_dir):
        """Test processing article with missing body key."""
        article = {
            "id": 12345,
            "title": "Missing Body Key",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        scraper = Scraper(temp_output_dir)
        filepath, content, content_hash, last_modified = scraper.process_article(article)
        
        assert filepath is None
        assert content is None
        assert content_hash is None
        assert last_modified is None
    
    def test_process_article_hash_consistency(self, temp_output_dir, sample_article):
        """Test that content hash is consistent for same content."""
        scraper = Scraper(temp_output_dir)
        _, content1, hash1, _ = scraper.process_article(sample_article)
        _, content2, hash2, _ = scraper.process_article(sample_article)
        
        assert hash1 == hash2
        assert content1 == content2
    
    def test_process_article_hash_changes_with_content(self, temp_output_dir):
        """Test that content hash changes when content changes."""
        article1 = {
            "id": 12345,
            "title": "Test Article",
            "body": "<h1>Content 1</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        article2 = {
            "id": 12345,
            "title": "Test Article",
            "body": "<h1>Content 2</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        scraper = Scraper(temp_output_dir)
        _, _, hash1, _ = scraper.process_article(article1)
        _, _, hash2, _ = scraper.process_article(article2)
        
        assert hash1 != hash2
    
    def test_process_article_filename_sanitization(self, temp_output_dir):
        """Test that filename is properly sanitized."""
        article = {
            "id": 12345,
            "title": "Test Article: With Special/Chars?",
            "body": "<h1>Content</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        scraper = Scraper(temp_output_dir)
        filepath, _, _, _ = scraper.process_article(article)
        
        assert "12345" in filepath
        assert "Test-Article--With-Special-Chars" in filepath
        assert filepath.endswith(".md")
        assert "/" not in os.path.basename(filepath)
        assert "?" not in os.path.basename(filepath)
        assert ":" not in os.path.basename(filepath)
    
    def test_process_article_untitled(self, temp_output_dir):
        """Test processing article with missing title."""
        article = {
            "id": 12345,
            "body": "<h1>Content</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        scraper = Scraper(temp_output_dir)
        filepath, content, _, _ = scraper.process_article(article)
        
        assert "Untitled" in content
        assert filepath is not None
    
    def test_process_article_markdown_conversion(self, temp_output_dir):
        """Test that HTML is properly converted to Markdown."""
        article = {
            "id": 12345,
            "title": "Test",
            "body": "<h1>Heading</h1><p>Paragraph with <strong>bold</strong> text.</p>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        scraper = Scraper(temp_output_dir)
        _, content, _, _ = scraper.process_article(article)
        
        # Check that HTML tags are removed/converted
        assert "<h1>" not in content
        assert "<p>" not in content
        assert "<strong>" not in content
        # Check that markdown structure is present
        assert "# Heading" in content or "Heading" in content
    
    def test_process_article_filepath_in_output_dir(self, temp_output_dir, sample_article):
        """Test that filepath is within output directory."""
        scraper = Scraper(temp_output_dir)
        filepath, _, _, _ = scraper.process_article(sample_article)
        
        assert filepath.startswith(temp_output_dir)
        assert os.path.dirname(filepath) == temp_output_dir
    
    def test_process_article_content_structure(self, temp_output_dir, sample_article):
        """Test that processed content has correct structure."""
        scraper = Scraper(temp_output_dir)
        _, content, _, _ = scraper.process_article(sample_article)
        
        assert content.startswith("#")
        assert "Article URL:" in content
        assert sample_article["title"] in content
        assert sample_article["html_url"] in content
