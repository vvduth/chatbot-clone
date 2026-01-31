"""
Unit tests for main.py module.
"""
import os
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from main import main
from state_manager import StateManager
from vector_store_manager import VectorStoreManager
from scraper import Scraper


class TestMain:
    """Test cases for main pipeline."""
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    def test_main_full_pipeline_new_articles(
        self, mock_logging, mock_state_manager_class, mock_scraper_class, 
        mock_vector_manager_class, temp_state_file, temp_output_dir, sample_articles_list
    ):
        """Test main pipeline with new articles."""
        # Setup mocks
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = []
        mock_state_manager.get_article_state.return_value = {}
        mock_state_manager.get_vector_store_id.return_value = None
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = sample_articles_list
        mock_scraper.process_article.side_effect = [
            (os.path.join(temp_output_dir, "12345-Article-1.md"), "# Article 1\n\nContent", "hash1", "2024-01-01T00:00:00"),
            (os.path.join(temp_output_dir, "67890-Article-2.md"), "# Article 2\n\nContent", "hash2", "2024-01-02T00:00:00")
        ]
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager.upload_file.side_effect = ["file_1", "file_2"]
        mock_vector_manager_class.return_value = mock_vector_manager
        
        # Run main
        with patch('main.os.path.exists', return_value=False):
            result = main()
        
        # Verify state manager was initialized
        mock_state_manager_class.assert_called_once()
        
        # Verify vector store was created/retrieved
        mock_vector_manager.get_or_create_vector_store.assert_called_once_with(mock_state_manager)
        
        # Verify articles were fetched
        mock_scraper.fetch_articles.assert_called_once_with(limit=None)
        
        # Verify articles were processed
        assert mock_scraper.process_article.call_count == 2
        
        # Verify files were uploaded
        assert mock_vector_manager.upload_file.call_count == 2
        
        # Verify files were added to vector store
        assert mock_vector_manager.add_file_to_vector_store.call_count == 2
        
        # Verify state was updated (with last_modified parameter)
        assert mock_state_manager.update_article_state.call_count == 2
        # Check that last_modified was passed
        calls = mock_state_manager.update_article_state.call_args_list
        assert calls[0][0][3] == "2024-01-01T00:00:00"  # last_modified parameter
        assert calls[1][0][3] == "2024-01-02T00:00:00"
        
        # Verify state was saved
        mock_state_manager.save_state.assert_called_once()
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    @patch('main.os.path.exists')
    def test_main_skips_unchanged_articles(
        self, mock_exists, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file, temp_output_dir
    ):
        """Test that main skips articles with unchanged hash."""
        article = {
            "id": 12345,
            "title": "Test Article",
            "body": "<h1>Content</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        # Setup mocks
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = ["12345"]
        mock_state_manager.get_article_state.return_value = {"hash": "hash1", "openai_file_id": "file_1"}
        mock_state_manager.get_vector_store_id.return_value = "vs_123"
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = [article]
        mock_scraper.process_article.return_value = (
            os.path.join(temp_output_dir, "12345-Test-Article.md"), 
            "# Test Article\n\nContent", 
            "hash1",  # Same hash
            "2024-01-01T00:00:00"  # Same last_modified
        )
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager_class.return_value = mock_vector_manager
        
        mock_exists.return_value = True  # File exists
        
        # Run main
        main()
        
        # Verify article was processed
        mock_scraper.process_article.assert_called_once()
        
        # Verify file was NOT uploaded (skipped)
        mock_vector_manager.upload_file.assert_not_called()
        
        # Verify state was NOT updated
        mock_state_manager.update_article_state.assert_not_called()
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    @patch('main.os.path.exists')
    def test_main_updates_changed_articles(
        self, mock_exists, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file, temp_output_dir
    ):
        """Test that main updates articles with changed hash."""
        article = {
            "id": 12345,
            "title": "Test Article",
            "body": "<h1>Updated Content</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        # Setup mocks
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = ["12345"]
        # get_article_state is called with article_id (int 12345) in main.py line 74
        # State has old hash and old last_modified, but new hash and new last_modified are different
        mock_state_manager.get_article_state.return_value = {
            "hash": "old_hash", 
            "openai_file_id": "file_1",
            "last_modified": "2024-01-01T00:00:00"  # Different from new last_modified
        }
        mock_state_manager.get_vector_store_id.return_value = "vs_123"
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = [article]
        filepath = os.path.join(temp_output_dir, "12345-Test-Article.md")
        mock_scraper.process_article.return_value = (
            filepath, 
            "# Test Article\n\nUpdated Content", 
            "new_hash",  # Different hash
            "2024-01-02T00:00:00"  # Different last_modified
        )
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager.upload_file.return_value = "file_new"
        mock_vector_manager_class.return_value = mock_vector_manager
        
        # File doesn't exist or hash changed, so it should be processed
        mock_exists.return_value = False
        
        # Run main
        main()
        
        # Verify file was uploaded
        mock_vector_manager.upload_file.assert_called_once()
        
        # Verify file was added to vector store
        mock_vector_manager.add_file_to_vector_store.assert_called_once_with("vs_123", "file_new")
        
        # Verify state was updated (article_id is int 12345 in main.py, with last_modified)
        mock_state_manager.update_article_state.assert_called_once_with(
            12345, "new_hash", "file_new", "2024-01-02T00:00:00"
        )
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    def test_main_deletes_removed_articles(
        self, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file
    ):
        """Test that main deletes articles no longer in source."""
        # Setup mocks - state has article 12345, but scraper returns empty
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = ["12345", "67890"]
        mock_state_manager.get_article_state.side_effect = [
            {"hash": "hash1", "openai_file_id": "file_1"},  # For 12345
            {"hash": "hash2", "openai_file_id": "file_2"}  # For 67890
        ]
        mock_state_manager.get_vector_store_id.return_value = "vs_123"
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = []  # No articles returned (but deletion should still happen)
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager_class.return_value = mock_vector_manager
        
        # Run main
        result = main()
        
        # Verify files were removed from vector store
        assert mock_vector_manager.remove_file_from_vector_store.call_count == 2
        mock_vector_manager.remove_file_from_vector_store.assert_any_call("vs_123", "file_1")
        mock_vector_manager.remove_file_from_vector_store.assert_any_call("vs_123", "file_2")
        
        # Verify files were removed from OpenAI
        assert mock_vector_manager.remove_file_from_openai.call_count == 2
        
        # Verify article states were removed
        assert mock_state_manager.remove_article_state.call_count == 2
        mock_state_manager.remove_article_state.assert_any_call("12345")
        mock_state_manager.remove_article_state.assert_any_call("67890")
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    def test_main_handles_article_with_no_body(
        self, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file
    ):
        """Test that main handles articles with no body."""
        article = {
            "id": 12345,
            "title": "Test Article",
            "body": "",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        # Setup mocks
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = []
        mock_state_manager.get_vector_store_id.return_value = "vs_123"
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = [article]
        mock_scraper.process_article.return_value = (None, None, None, None)  # No body
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager_class.return_value = mock_vector_manager
        
        # Run main
        main()
        
        # Verify article was processed
        mock_scraper.process_article.assert_called_once()
        
        # Verify file was NOT uploaded (no body)
        mock_vector_manager.upload_file.assert_not_called()
        
        # Verify state was NOT updated
        mock_state_manager.update_article_state.assert_not_called()
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    @patch('main.os.path.exists')
    def test_main_works_without_openai(
        self, mock_exists, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file, temp_output_dir
    ):
        """Test that main works when OpenAI is not available."""
        article = {
            "id": 12345,
            "title": "Test Article",
            "body": "<h1>Content</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        # Setup mocks
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = []
        mock_state_manager.get_article_state.return_value = {}
        mock_state_manager.get_vector_store_id.return_value = None
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = [article]
        mock_scraper.process_article.return_value = (
            os.path.join(temp_output_dir, "12345-Test-Article.md"), 
            "# Test Article\n\nContent", 
            "hash1",
            "2024-01-01T00:00:00"
        )
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = None  # No vector store
        mock_vector_manager_class.return_value = mock_vector_manager
        
        mock_exists.return_value = False
        
        # Run main
        main()
        
        # Verify article was processed
        mock_scraper.process_article.assert_called_once()
        
        # Verify file was NOT uploaded (no vector store)
        mock_vector_manager.upload_file.assert_not_called()
        
        # Verify state was updated with None file_id (article_id is int 12345 in main.py, with last_modified)
        mock_state_manager.update_article_state.assert_called_once_with(
            12345, "hash1", None, "2024-01-01T00:00:00"
        )
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    def test_main_handles_upload_failure(
        self, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file, temp_output_dir
    ):
        """Test that main handles file upload failures gracefully."""
        article = {
            "id": 12345,
            "title": "Test Article",
            "body": "<h1>Content</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        }
        
        # Setup mocks
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = []
        mock_state_manager.get_article_state.return_value = {}
        mock_state_manager.get_vector_store_id.return_value = "vs_123"
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = [article]
        mock_scraper.process_article.return_value = (
            os.path.join(temp_output_dir, "12345-Test-Article.md"), 
            "# Test Article\n\nContent", 
            "hash1",
            "2024-01-01T00:00:00"
        )
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager.upload_file.return_value = None  # Upload failed
        mock_vector_manager_class.return_value = mock_vector_manager
        
        # Run main
        with patch('main.os.path.exists', return_value=False):
            main()
        
        # Verify upload was attempted
        mock_vector_manager.upload_file.assert_called_once()
        
        # Verify file was NOT added to vector store (upload failed)
        mock_vector_manager.add_file_to_vector_store.assert_not_called()
        
        # Verify state was NOT updated (upload failed)
        mock_state_manager.update_article_state.assert_not_called()
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    def test_main_handles_deletion_errors(
        self, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file
    ):
        """Test that main handles errors during article deletion gracefully."""
        # Setup mocks
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = ["12345"]
        mock_state_manager.get_article_state.return_value = {
            "hash": "hash1", 
            "openai_file_id": "file_1"
        }
        mock_state_manager.get_vector_store_id.return_value = "vs_123"
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = []  # No articles
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager.remove_file_from_vector_store.side_effect = Exception("Delete error")
        mock_vector_manager_class.return_value = mock_vector_manager
        
        # Run main - should not raise exception
        main()
        
        # Verify deletion was attempted
        mock_vector_manager.remove_file_from_vector_store.assert_called_once()
        
        # Verify state was still removed
        mock_state_manager.remove_article_state.assert_called_once_with("12345")
    
    @patch('main.VectorStoreManager')
    @patch('main.Scraper')
    @patch('main.StateManager')
    @patch('main.logging')
    @patch('main.os.path.exists')
    def test_main_stats_tracking(
        self, mock_exists, mock_logging, mock_state_manager_class, 
        mock_scraper_class, mock_vector_manager_class, temp_state_file, temp_output_dir
    ):
        """Test that main correctly tracks statistics."""
        articles = [
            {"id": 1, "title": "New", "body": "<h1>New</h1>", "html_url": "https://example.com/1"},
            {"id": 2, "title": "Updated", "body": "<h1>Updated</h1>", "html_url": "https://example.com/2"},
            {"id": 3, "title": "Skipped", "body": "<h1>Skipped</h1>", "html_url": "https://example.com/3"}
        ]
        
        # Setup mocks - get_article_state is called with article_id (int) for each article
        def get_article_state_side_effect(article_id):
            if article_id == 1:
                return {}  # New article
            elif article_id == 2:
                return {"hash": "old", "openai_file_id": "file_2", "last_modified": "2024-01-01T00:00:00"}  # Updated article
            elif article_id == 3:
                return {"hash": "hash3", "openai_file_id": "file_3", "last_modified": "2024-01-03T00:00:00"}  # Skipped article (hash and last_modified match)
            return {}
        
        mock_state_manager = MagicMock(spec=StateManager)
        mock_state_manager.get_all_article_ids.return_value = ["3"]
        mock_state_manager.get_article_state.side_effect = get_article_state_side_effect
        mock_state_manager.get_vector_store_id.return_value = "vs_123"
        mock_state_manager_class.return_value = mock_state_manager
        
        mock_scraper = MagicMock(spec=Scraper)
        mock_scraper.fetch_articles.return_value = articles
        mock_scraper.process_article.side_effect = [
            (os.path.join(temp_output_dir, "1-New.md"), "# New\n\nContent", "hash1", "2024-01-01T00:00:00"),
            (os.path.join(temp_output_dir, "2-Updated.md"), "# Updated\n\nContent", "hash2", "2024-01-02T00:00:00"),
            (os.path.join(temp_output_dir, "3-Skipped.md"), "# Skipped\n\nContent", "hash3", "2024-01-03T00:00:00")
        ]
        mock_scraper_class.return_value = mock_scraper
        
        mock_vector_manager = MagicMock(spec=VectorStoreManager)
        mock_vector_manager.get_or_create_vector_store.return_value = "vs_123"
        mock_vector_manager.upload_file.side_effect = ["file_1", "file_2"]
        mock_vector_manager_class.return_value = mock_vector_manager
        
        # For skipped article (hash matches), file should exist
        def exists_side_effect(path):
            if "3-Skipped" in path:
                return True  # File exists for skipped article
            return False  # Files don't exist for new/updated
        
        mock_exists.side_effect = exists_side_effect
        
        # Run main
        main()
        
        # Verify final stats logging (checking that logging.info was called with stats)
        # The actual stats are internal, but we can verify the flow
        assert mock_state_manager.save_state.called
        # Verify correct number of operations
        assert mock_vector_manager.upload_file.call_count == 2  # New + Updated (not Skipped)
        assert mock_state_manager.update_article_state.call_count == 2  # New + Updated (not Skipped)
