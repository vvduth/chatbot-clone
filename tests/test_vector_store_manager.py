"""
Unit tests for vector_store_manager.py module.
"""
import os
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from vector_store_manager import VectorStoreManager
from state_manager import StateManager


class TestVectorStoreManager:
    """Test cases for VectorStoreManager class."""
    
    def test_init_with_api_key(self, mock_openai_client, temp_state_file):
        """Test initialization with API key."""
        with patch('vector_store_manager.OpenAI', return_value=mock_openai_client):
            manager = VectorStoreManager("test_key")
            assert manager.client is not None
    
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        manager = VectorStoreManager(None)
        assert manager.client is None
    
    def test_init_with_empty_api_key(self):
        """Test initialization with empty API key."""
        manager = VectorStoreManager("")
        assert manager.client is None
    
    @patch('vector_store_manager.OpenAI')
    def test_get_or_create_vector_store_existing_valid(self, mock_openai_class, temp_state_file):
        """Test getting existing valid vector store."""
        state_manager = StateManager(temp_state_file)
        state_manager.set_vector_store_id("vs_existing")
        
        mock_client = MagicMock()
        mock_vector_store = MagicMock()
        mock_vector_store.id = "vs_existing"
        mock_client.vector_stores.retrieve.return_value = mock_vector_store
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        vs_id = manager.get_or_create_vector_store(state_manager)
        
        assert vs_id == "vs_existing"
        mock_client.vector_stores.retrieve.assert_called_once_with(vector_store_id="vs_existing")
    
    @patch('vector_store_manager.OpenAI')
    def test_get_or_create_vector_store_existing_invalid(self, mock_openai_class, temp_state_file):
        """Test creating new vector store when existing one is invalid."""
        state_manager = StateManager(temp_state_file)
        state_manager.set_vector_store_id("vs_invalid")
        
        mock_client = MagicMock()
        mock_client.vector_stores.retrieve.side_effect = Exception("Not found")
        
        mock_new_vs = MagicMock()
        mock_new_vs.id = "vs_new"
        mock_client.vector_stores.create.return_value = mock_new_vs
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        vs_id = manager.get_or_create_vector_store(state_manager)
        
        assert vs_id == "vs_new"
        assert state_manager.get_vector_store_id() == "vs_new"
        mock_client.vector_stores.create.assert_called_once()
    
    @patch('vector_store_manager.OpenAI')
    def test_get_or_create_vector_store_new(self, mock_openai_class, temp_state_file):
        """Test creating new vector store when none exists."""
        state_manager = StateManager(temp_state_file)
        
        mock_client = MagicMock()
        mock_new_vs = MagicMock()
        mock_new_vs.id = "vs_new"
        mock_client.vector_stores.create.return_value = mock_new_vs
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        vs_id = manager.get_or_create_vector_store(state_manager, name="Test Store")
        
        assert vs_id == "vs_new"
        assert state_manager.get_vector_store_id() == "vs_new"
        call_args = mock_client.vector_stores.create.call_args
        assert call_args[1]['name'] == "Test Store"
        assert 'expires_after' in call_args[1]
    
    @patch('vector_store_manager.OpenAI')
    def test_get_or_create_vector_store_creation_failure(self, mock_openai_class, temp_state_file):
        """Test handling vector store creation failure."""
        state_manager = StateManager(temp_state_file)
        
        mock_client = MagicMock()
        mock_client.vector_stores.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        vs_id = manager.get_or_create_vector_store(state_manager)
        
        assert vs_id is None
    
    def test_get_or_create_vector_store_no_client(self, temp_state_file):
        """Test that None is returned when client is not available."""
        state_manager = StateManager(temp_state_file)
        manager = VectorStoreManager(None)
        vs_id = manager.get_or_create_vector_store(state_manager)
        
        assert vs_id is None
    
    @patch('vector_store_manager.OpenAI')
    def test_upload_file_success(self, mock_openai_class, temp_output_dir):
        """Test successful file upload."""
        test_file = os.path.join(temp_output_dir, "test.md")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        mock_client = MagicMock()
        mock_file = MagicMock()
        mock_file.id = "file_123"
        mock_client.files.create.return_value = mock_file
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        file_id = manager.upload_file(test_file)
        
        assert file_id == "file_123"
        mock_client.files.create.assert_called_once()
        call_args = mock_client.files.create.call_args
        assert call_args[1]['purpose'] == "assistants"
    
    @patch('vector_store_manager.OpenAI')
    def test_upload_file_failure(self, mock_openai_class, temp_output_dir):
        """Test handling file upload failure."""
        test_file = os.path.join(temp_output_dir, "test.md")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        mock_client = MagicMock()
        mock_client.files.create.side_effect = Exception("Upload failed")
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        file_id = manager.upload_file(test_file)
        
        assert file_id is None
    
    def test_upload_file_no_client(self, temp_output_dir):
        """Test that mock file ID is returned when client is not available."""
        test_file = os.path.join(temp_output_dir, "test.md")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        manager = VectorStoreManager(None)
        file_id = manager.upload_file(test_file)
        
        assert file_id == "mock_file_id"
    
    @patch('vector_store_manager.OpenAI')
    def test_add_file_to_vector_store_success(self, mock_openai_class):
        """Test successfully adding file to vector store."""
        mock_client = MagicMock()
        mock_vs_file = MagicMock()
        mock_vs_file.status = "completed"
        mock_vs_file.last_error = None
        mock_client.vector_stores.files.create.return_value = mock_vs_file
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        manager.add_file_to_vector_store("vs_123", "file_456")
        
        mock_client.vector_stores.files.create.assert_called_once_with(
            vector_store_id="vs_123",
            file_id="file_456"
        )
    
    @patch('vector_store_manager.OpenAI')
    def test_add_file_to_vector_store_pending_status(self, mock_openai_class):
        """Test handling file with pending status."""
        mock_client = MagicMock()
        mock_vs_file = MagicMock()
        mock_vs_file.status = "in_progress"
        mock_vs_file.last_error = None
        mock_client.vector_stores.files.create.return_value = mock_vs_file
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        # Should not raise an error
        manager.add_file_to_vector_store("vs_123", "file_456")
    
    @patch('vector_store_manager.OpenAI')
    def test_add_file_to_vector_store_failure(self, mock_openai_class):
        """Test handling failure when adding file to vector store."""
        mock_client = MagicMock()
        mock_client.vector_stores.files.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        # Should not raise an error
        manager.add_file_to_vector_store("vs_123", "file_456")
    
    def test_add_file_to_vector_store_no_client(self):
        """Test that nothing happens when client is not available."""
        manager = VectorStoreManager(None)
        # Should not raise an error
        manager.add_file_to_vector_store("vs_123", "file_456")
    
    def test_add_file_to_vector_store_no_vector_store_id(self):
        """Test that nothing happens when vector store ID is None."""
        with patch('vector_store_manager.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            manager = VectorStoreManager("test_key")
            manager.add_file_to_vector_store(None, "file_456")
            
            mock_client.vector_stores.files.create.assert_not_called()
    
    def test_add_file_to_vector_store_no_file_id(self):
        """Test that nothing happens when file ID is None."""
        with patch('vector_store_manager.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            manager = VectorStoreManager("test_key")
            manager.add_file_to_vector_store("vs_123", None)
            
            mock_client.vector_stores.files.create.assert_not_called()
    
    @patch('vector_store_manager.OpenAI')
    def test_remove_file_from_vector_store_success(self, mock_openai_class):
        """Test successfully removing file from vector store."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        manager.remove_file_from_vector_store("vs_123", "file_456")
        
        mock_client.vector_stores.files.delete.assert_called_once_with(
            vector_store_id="vs_123",
            file_id="file_456"
        )
    
    @patch('vector_store_manager.OpenAI')
    def test_remove_file_from_vector_store_failure(self, mock_openai_class):
        """Test handling failure when removing file from vector store."""
        mock_client = MagicMock()
        mock_client.vector_stores.files.delete.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        # Should not raise an error
        manager.remove_file_from_vector_store("vs_123", "file_456")
    
    def test_remove_file_from_vector_store_no_client(self):
        """Test that nothing happens when client is not available."""
        manager = VectorStoreManager(None)
        manager.remove_file_from_vector_store("vs_123", "file_456")
        # Should complete without error
    
    @patch('vector_store_manager.OpenAI')
    def test_remove_file_from_openai_success(self, mock_openai_class):
        """Test successfully removing file from OpenAI storage."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        manager.remove_file_from_openai("file_123")
        
        mock_client.files.delete.assert_called_once_with(file_id="file_123")
    
    @patch('vector_store_manager.OpenAI')
    def test_remove_file_from_openai_failure(self, mock_openai_class):
        """Test handling failure when removing file from OpenAI."""
        mock_client = MagicMock()
        mock_client.files.delete.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        # Should not raise an error
        manager.remove_file_from_openai("file_123")
    
    def test_remove_file_from_openai_no_client(self):
        """Test that nothing happens when client is not available."""
        manager = VectorStoreManager(None)
        manager.remove_file_from_openai("file_123")
        # Should complete without error
    
    @patch('vector_store_manager.OpenAI')
    def test_clear_all_files_from_vector_store_success(self, mock_openai_class):
        """Test successfully clearing all files from vector store."""
        mock_client = MagicMock()
        mock_file1 = MagicMock()
        mock_file1.id = "file_1"
        mock_file2 = MagicMock()
        mock_file2.id = "file_2"
        
        mock_list = MagicMock()
        mock_list.data = [mock_file1, mock_file2]
        mock_client.vector_stores.files.list.return_value = mock_list
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        manager.clear_all_files_from_vector_store("vs_123")
        
        assert mock_client.vector_stores.files.delete.call_count == 2
    
    @patch('vector_store_manager.OpenAI')
    def test_clear_all_files_from_vector_store_empty(self, mock_openai_class):
        """Test clearing files from empty vector store."""
        mock_client = MagicMock()
        mock_list = MagicMock()
        mock_list.data = []
        mock_client.vector_stores.files.list.return_value = mock_list
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        manager.clear_all_files_from_vector_store("vs_123")
        
        mock_client.vector_stores.files.delete.assert_not_called()
    
    @patch('vector_store_manager.OpenAI')
    def test_clear_all_files_from_vector_store_failure(self, mock_openai_class):
        """Test handling failure when clearing files."""
        mock_client = MagicMock()
        mock_client.vector_stores.files.list.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        # Should not raise an error
        manager.clear_all_files_from_vector_store("vs_123")
    
    def test_clear_all_files_from_vector_store_no_client(self):
        """Test that nothing happens when client is not available."""
        manager = VectorStoreManager(None)
        manager.clear_all_files_from_vector_store("vs_123")
        # Should complete without error
    
    @patch('vector_store_manager.OpenAI')
    def test_clear_file_from_storage_success(self, mock_openai_class):
        """Test successfully clearing all files from OpenAI storage."""
        mock_client = MagicMock()
        mock_file1 = MagicMock()
        mock_file1.id = "file_1"
        mock_file2 = MagicMock()
        mock_file2.id = "file_2"
        
        mock_list = MagicMock()
        mock_list.data = [mock_file1, mock_file2]
        mock_client.files.list.return_value = mock_list
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        manager.clear_file_from_storage()
        
        assert mock_client.files.delete.call_count == 2
    
    @patch('vector_store_manager.OpenAI')
    def test_clear_file_from_storage_empty(self, mock_openai_class):
        """Test clearing files when storage is empty."""
        mock_client = MagicMock()
        mock_list = MagicMock()
        mock_list.data = []
        mock_client.files.list.return_value = mock_list
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        manager.clear_file_from_storage()
        
        mock_client.files.delete.assert_not_called()
    
    @patch('vector_store_manager.OpenAI')
    def test_clear_file_from_storage_failure(self, mock_openai_class):
        """Test handling failure when clearing files from storage."""
        mock_client = MagicMock()
        mock_client.files.list.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        manager = VectorStoreManager("test_key")
        # Should not raise an error
        manager.clear_file_from_storage()
    
    def test_clear_file_from_storage_no_client(self):
        """Test that nothing happens when client is not available."""
        manager = VectorStoreManager(None)
        manager.clear_file_from_storage()
        # Should complete without error
