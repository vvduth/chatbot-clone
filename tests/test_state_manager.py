"""
Unit tests for state_manager.py module.
"""
import os
import json
import pytest
from state_manager import StateManager


class TestStateManager:
    """Test cases for StateManager class."""
    
    def test_init_creates_empty_state_when_file_not_exists(self, temp_state_file):
        """Test that StateManager initializes with empty state when file doesn't exist."""
        manager = StateManager(temp_state_file)
        assert manager.state == {"articles": {}, "vector_store_id": None}
        assert not os.path.exists(temp_state_file)
    
    def test_init_loads_existing_state(self, temp_state_file, sample_state_data):
        """Test that StateManager loads existing state from file."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        assert manager.state == sample_state_data
        assert manager.state["vector_store_id"] == "vs_test123"
        assert len(manager.state["articles"]) == 2
    
    def test_init_handles_corrupted_state_file(self, temp_state_file):
        """Test that StateManager handles corrupted JSON gracefully."""
        with open(temp_state_file, 'w') as f:
            f.write("invalid json content {")
        
        manager = StateManager(temp_state_file)
        assert manager.state == {"articles": {}, "vector_store_id": None}
    
    def test_init_handles_empty_state_file(self, temp_state_file):
        """Test that StateManager handles empty state file."""
        with open(temp_state_file, 'w') as f:
            f.write("")
        
        manager = StateManager(temp_state_file)
        assert manager.state == {"articles": {}, "vector_store_id": None}
    
    def test_save_state_creates_file(self, temp_state_file):
        """Test that save_state creates the state file."""
        manager = StateManager(temp_state_file)
        manager.state["vector_store_id"] = "vs_new"
        manager.save_state()
        
        assert os.path.exists(temp_state_file)
        with open(temp_state_file, 'r') as f:
            saved_state = json.load(f)
        assert saved_state["vector_store_id"] == "vs_new"
    
    def test_save_state_creates_directory(self, temp_dir):
        """Test that save_state creates parent directory if it doesn't exist."""
        state_file = os.path.join(temp_dir, "nested", "state.json")
        manager = StateManager(state_file)
        manager.save_state()
        
        assert os.path.exists(state_file)
    
    def test_get_article_state_existing(self, temp_state_file, sample_state_data):
        """Test getting state for an existing article."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        state = manager.get_article_state("123")
        
        assert state["hash"] == "abc123"
        assert state["openai_file_id"] == "file-xyz"
    
    def test_get_article_state_nonexistent(self, temp_state_file):
        """Test getting state for a non-existent article returns empty dict."""
        manager = StateManager(temp_state_file)
        state = manager.get_article_state("999")
        
        assert state == {}
    
    def test_get_article_state_with_int_id(self, temp_state_file, sample_state_data):
        """Test that article state can be retrieved with integer ID."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        state = manager.get_article_state(123)  # int instead of str
        
        assert state["hash"] == "abc123"
    
    def test_update_article_state_new(self, temp_state_file):
        """Test updating state for a new article."""
        manager = StateManager(temp_state_file)
        manager.update_article_state("789", "new_hash", "file_new")
        
        state = manager.get_article_state("789")
        assert state["hash"] == "new_hash"
        assert state["openai_file_id"] == "file_new"
        assert "updated_at" in state
    
    def test_update_article_state_existing(self, temp_state_file, sample_state_data):
        """Test updating state for an existing article."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        manager.update_article_state("123", "updated_hash", "file_updated")
        
        state = manager.get_article_state("123")
        assert state["hash"] == "updated_hash"
        assert state["openai_file_id"] == "file_updated"
    
    def test_update_article_state_without_file_id(self, temp_state_file):
        """Test updating article state without OpenAI file ID."""
        manager = StateManager(temp_state_file)
        manager.update_article_state("789", "hash_only", None)
        
        state = manager.get_article_state("789")
        assert state["hash"] == "hash_only"
        assert state["openai_file_id"] is None
    
    def test_get_vector_store_id_existing(self, temp_state_file, sample_state_data):
        """Test getting existing vector store ID."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        vs_id = manager.get_vector_store_id()
        
        assert vs_id == "vs_test123"
    
    def test_get_vector_store_id_nonexistent(self, temp_state_file):
        """Test getting vector store ID when not set."""
        manager = StateManager(temp_state_file)
        vs_id = manager.get_vector_store_id()
        
        assert vs_id is None
    
    def test_set_vector_store_id(self, temp_state_file):
        """Test setting vector store ID."""
        manager = StateManager(temp_state_file)
        manager.set_vector_store_id("vs_new_id")
        
        assert manager.get_vector_store_id() == "vs_new_id"
    
    def test_get_all_article_ids(self, temp_state_file, sample_state_data):
        """Test getting all article IDs."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        ids = manager.get_all_article_ids()
        
        assert set(ids) == {"123", "456"}
        assert len(ids) == 2
    
    def test_get_all_article_ids_empty(self, temp_state_file):
        """Test getting article IDs when state is empty."""
        manager = StateManager(temp_state_file)
        ids = manager.get_all_article_ids()
        
        assert ids == []
    
    def test_remove_article_state_existing(self, temp_state_file, sample_state_data):
        """Test removing an existing article state."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        manager.remove_article_state("123")
        
        assert manager.get_article_state("123") == {}
        assert manager.get_article_state("456")["hash"] == "def456"
    
    def test_remove_article_state_nonexistent(self, temp_state_file):
        """Test removing a non-existent article state (should not raise error)."""
        manager = StateManager(temp_state_file)
        # Should not raise an error
        manager.remove_article_state("999")
        
        assert manager.get_article_state("999") == {}
    
    def test_remove_article_state_with_int_id(self, temp_state_file, sample_state_data):
        """Test removing article state with integer ID."""
        with open(temp_state_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        manager = StateManager(temp_state_file)
        manager.remove_article_state(123)  # int instead of str
        
        assert manager.get_article_state("123") == {}
    
    def test_state_persistence(self, temp_state_file):
        """Test that state persists across StateManager instances."""
        manager1 = StateManager(temp_state_file)
        manager1.update_article_state("111", "hash1", "file1")
        manager1.set_vector_store_id("vs_persist")
        manager1.save_state()
        
        manager2 = StateManager(temp_state_file)
        assert manager2.get_article_state("111")["hash"] == "hash1"
        assert manager2.get_vector_store_id() == "vs_persist"
