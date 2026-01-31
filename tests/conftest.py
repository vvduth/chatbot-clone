"""
Shared fixtures and utilities for pytest tests.
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_state_file(temp_dir):
    """Create a temporary state file path."""
    return os.path.join(temp_dir, "state.json")


@pytest.fixture
def temp_output_dir(temp_dir):
    """Create a temporary output directory."""
    output_dir = os.path.join(temp_dir, "articles")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


@pytest.fixture
def sample_state_data():
    """Sample state data for testing."""
    return {
        "articles": {
            "123": {
                "hash": "abc123",
                "openai_file_id": "file-xyz",
                "updated_at": "2024-01-01T00:00:00"
            },
            "456": {
                "hash": "def456",
                "openai_file_id": "file-abc",
                "updated_at": "2024-01-02T00:00:00"
            }
        },
        "vector_store_id": "vs_test123"
    }


@pytest.fixture
def sample_article():
    """Sample article data from Zendesk API."""
    return {
        "id": 12345,
        "title": "Test Article",
        "body": "<h1>Test Content</h1><p>This is a test article.</p>",
        "html_url": "https://support.optisigns.com/articles/12345"
    }


@pytest.fixture
def sample_articles_list():
    """List of sample articles."""
    return [
        {
            "id": 12345,
            "title": "Article 1",
            "body": "<h1>Content 1</h1>",
            "html_url": "https://support.optisigns.com/articles/12345"
        },
        {
            "id": 67890,
            "title": "Article 2",
            "body": "<h1>Content 2</h1>",
            "html_url": "https://support.optisigns.com/articles/67890"
        }
    ]


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = MagicMock()
    
    # Mock vector store operations
    mock_vector_store = MagicMock()
    mock_vector_store.id = "vs_test123"
    client.vector_stores.create.return_value = mock_vector_store
    client.vector_stores.retrieve.return_value = mock_vector_store
    
    # Mock file operations
    mock_file = MagicMock()
    mock_file.id = "file_test123"
    client.files.create.return_value = mock_file
    
    # Mock vector store file operations
    mock_vs_file = MagicMock()
    mock_vs_file.status = "completed"
    mock_vs_file.last_error = None
    client.vector_stores.files.create.return_value = mock_vs_file
    
    # Mock list operations
    mock_list = MagicMock()
    mock_list.data = []
    client.vector_stores.files.list.return_value = mock_list
    client.files.list.return_value = mock_list
    
    return client


@pytest.fixture
def mock_requests_response():
    """Mock requests response."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "articles": [
            {
                "id": 12345,
                "title": "Test Article",
                "body": "<h1>Test</h1>",
                "html_url": "https://support.optisigns.com/articles/12345"
            }
        ]
    }
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def env_vars(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("ZENDESK_API_TOKEN", "test_zendesk_token")
    return {
        "OPENAI_API_KEY": "test_openai_key",
        "ZENDESK_API_TOKEN": "test_zendesk_token"
    }
