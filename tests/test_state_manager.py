"""
Unit tests for state_manager.py module.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from botocore.exceptions import ClientError
from state_manager import StateManager


class TestStateManager:
    """Test cases for StateManager class."""
    
    @patch('state_manager.boto3.client')
    def test_init_creates_empty_state_when_file_not_exists(self, mock_boto_client, env_vars, mock_s3_client):
        """Test that StateManager initializes with empty state when file doesn't exist."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        assert manager.state == {"articles": {}, "vector_store_id": None}
    
    @patch('state_manager.boto3.client')
    def test_init_loads_existing_state(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test that StateManager loads existing state from S3."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        assert manager.state == sample_state_data
        assert manager.state["vector_store_id"] == "vs_test123"
        assert len(manager.state["articles"]) == 2
    
    @patch('state_manager.boto3.client')
    def test_init_handles_corrupted_state_file(self, mock_boto_client, env_vars, mock_s3_client):
        """Test that StateManager handles corrupted JSON gracefully."""
        def get_object_side_effect(Bucket, Key):
            mock_response = MagicMock()
            mock_response['Body'] = BytesIO(b"invalid json content {")
            return mock_response
        
        mock_s3_client.get_object.side_effect = get_object_side_effect
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        assert manager.state == {"articles": {}, "vector_store_id": None}
    
    @patch('state_manager.boto3.client')
    def test_init_handles_empty_state_file(self, mock_boto_client, env_vars, mock_s3_client):
        """Test that StateManager handles empty state file."""
        def get_object_side_effect(Bucket, Key):
            mock_response = MagicMock()
            mock_response['Body'] = BytesIO(b"")
            return mock_response
        
        mock_s3_client.get_object.side_effect = get_object_side_effect
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        assert manager.state == {"articles": {}, "vector_store_id": None}
    
    @patch('state_manager.boto3.client')
    def test_save_state_creates_file(self, mock_boto_client, env_vars, mock_s3_client):
        """Test that save_state saves to S3."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        manager.state["vector_store_id"] = "vs_new"
        manager.save_state()
        
        # Verify put_object was called
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == "test-bucket"
        assert call_args[1]['Key'] == "state.json"
        saved_state = json.loads(call_args[1]['Body'])
        assert saved_state["vector_store_id"] == "vs_new"
    
    @patch('state_manager.boto3.client')
    def test_save_state_saves_to_s3(self, mock_boto_client, env_vars, mock_s3_client):
        """Test that save_state saves to S3."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        manager.save_state()
        
        # Verify put_object was called
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == "test-bucket"
        assert call_args[1]['Key'] == "state.json"
    
    @patch('state_manager.boto3.client')
    def test_get_article_state_existing(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test getting state for an existing article."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        state = manager.get_article_state("123")
        
        assert state["hash"] == "abc123"
        assert state["openai_file_id"] == "file-xyz"
    
    @patch('state_manager.boto3.client')
    def test_get_article_state_nonexistent(self, mock_boto_client, env_vars, mock_s3_client):
        """Test getting state for a non-existent article returns empty dict."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        state = manager.get_article_state("999")
        
        assert state == {}
    
    @patch('state_manager.boto3.client')
    def test_get_article_state_with_int_id(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test that article state can be retrieved with integer ID."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        state = manager.get_article_state(123)  # int instead of str
        
        assert state["hash"] == "abc123"
    
    @patch('state_manager.boto3.client')
    def test_update_article_state_new(self, mock_boto_client, env_vars, mock_s3_client):
        """Test updating state for a new article."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        manager.update_article_state("789", "new_hash", "file_new")
        
        state = manager.get_article_state("789")
        assert state["hash"] == "new_hash"
        assert state["openai_file_id"] == "file_new"
        assert "updated_at" in state
    
    @patch('state_manager.boto3.client')
    def test_update_article_state_existing(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test updating state for an existing article."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        manager.update_article_state("123", "updated_hash", "file_updated")
        
        state = manager.get_article_state("123")
        assert state["hash"] == "updated_hash"
        assert state["openai_file_id"] == "file_updated"
    
    @patch('state_manager.boto3.client')
    def test_update_article_state_without_file_id(self, mock_boto_client, env_vars, mock_s3_client):
        """Test updating article state without OpenAI file ID."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        manager.update_article_state("789", "hash_only", None)
        
        state = manager.get_article_state("789")
        assert state["hash"] == "hash_only"
        assert state["openai_file_id"] is None
    
    @patch('state_manager.boto3.client')
    def test_get_vector_store_id_existing(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test getting existing vector store ID."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        vs_id = manager.get_vector_store_id()
        
        assert vs_id == "vs_test123"
    
    @patch('state_manager.boto3.client')
    def test_get_vector_store_id_nonexistent(self, mock_boto_client, env_vars, mock_s3_client):
        """Test getting vector store ID when not set."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        vs_id = manager.get_vector_store_id()
        
        assert vs_id is None
    
    @patch('state_manager.boto3.client')
    def test_set_vector_store_id(self, mock_boto_client, env_vars, mock_s3_client):
        """Test setting vector store ID."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        manager.set_vector_store_id("vs_new_id")
        
        assert manager.get_vector_store_id() == "vs_new_id"
    
    @patch('state_manager.boto3.client')
    def test_get_all_article_ids(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test getting all article IDs."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        ids = manager.get_all_article_ids()
        
        assert set(ids) == {"123", "456"}
        assert len(ids) == 2
    
    @patch('state_manager.boto3.client')
    def test_get_all_article_ids_empty(self, mock_boto_client, env_vars, mock_s3_client):
        """Test getting article IDs when state is empty."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        ids = manager.get_all_article_ids()
        
        assert ids == []
    
    @patch('state_manager.boto3.client')
    def test_remove_article_state_existing(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test removing an existing article state."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        manager.remove_article_state("123")
        
        assert manager.get_article_state("123") == {}
        assert manager.get_article_state("456")["hash"] == "def456"
    
    @patch('state_manager.boto3.client')
    def test_remove_article_state_nonexistent(self, mock_boto_client, env_vars, mock_s3_client):
        """Test removing a non-existent article state (should not raise error)."""
        mock_boto_client.return_value = mock_s3_client
        manager = StateManager()
        # Should not raise an error
        manager.remove_article_state("999")
        
        assert manager.get_article_state("999") == {}
    
    @patch('state_manager.boto3.client')
    def test_remove_article_state_with_int_id(self, mock_boto_client, env_vars, mock_s3_with_state, sample_state_data):
        """Test removing article state with integer ID."""
        mock_boto_client.return_value = mock_s3_with_state
        manager = StateManager()
        manager.remove_article_state(123)  # int instead of str
        
        assert manager.get_article_state("123") == {}
    
    @patch('state_manager.boto3.client')
    def test_state_persistence(self, mock_boto_client, env_vars):
        """Test that state persists across StateManager instances."""
        # Store state between calls - use a mutable dict that both functions can access
        saved_state = {"articles": {}, "vector_store_id": None}
        
        def get_object_side_effect(Bucket, Key):
            # Always return current saved_state (create new BytesIO each time)
            body_content = json.dumps(saved_state).encode('utf-8')
            body_stream = BytesIO(body_content)
            return {'Body': body_stream}
        
        def put_object_side_effect(Bucket, Key, Body, **kwargs):
            # Completely replace saved_state when save is called
            new_state = json.loads(Body)
            # Deep copy the state to ensure nested structures are preserved
            import copy
            saved_state.clear()
            saved_state.update(copy.deepcopy(new_state))
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        mock_s3_client = MagicMock()
        mock_s3_client.get_object.side_effect = get_object_side_effect
        mock_s3_client.put_object.side_effect = put_object_side_effect
        mock_boto_client.return_value = mock_s3_client
        
        manager1 = StateManager()
        manager1.update_article_state("111", "hash1", "file1")
        manager1.set_vector_store_id("vs_persist")
        manager1.save_state()
        
        # Verify saved_state was updated correctly
        assert "111" in saved_state["articles"]
        assert saved_state["articles"]["111"]["hash"] == "hash1"
        assert saved_state["vector_store_id"] == "vs_persist"
        
        # Create new manager instance - should load saved state
        manager2 = StateManager()
        state_111 = manager2.get_article_state("111")
        assert state_111["hash"] == "hash1"
        assert manager2.get_vector_store_id() == "vs_persist"
