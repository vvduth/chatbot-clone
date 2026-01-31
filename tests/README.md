# Test Suite Documentation

This directory contains comprehensive unit tests for the chatbot-clone application.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and test utilities
├── test_config.py           # Tests for configuration module
├── test_state_manager.py    # Tests for state management
├── test_scraper.py          # Tests for article scraping
├── test_vector_store_manager.py  # Tests for OpenAI integration
└── test_main.py             # Tests for main pipeline
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=. --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_scraper.py
```

### Run specific test class
```bash
pytest tests/test_scraper.py::TestScraper
```

### Run specific test method
```bash
pytest tests/test_scraper.py::TestScraper::test_fetch_articles_success
```

### Run with verbose output
```bash
pytest -v
```

### Run with detailed output
```bash
pytest -vv
```

## Test Coverage

The test suite aims for comprehensive coverage of:
- ✅ Configuration loading and validation
- ✅ State management (CRUD operations)
- ✅ Article scraping and processing
- ✅ OpenAI Vector Store integration
- ✅ Main pipeline orchestration
- ✅ Error handling and edge cases

## Test Fixtures

Common fixtures available in `conftest.py`:
- `temp_dir`: Temporary directory for test files
- `temp_state_file`: Temporary state file path
- `temp_output_dir`: Temporary output directory
- `sample_state_data`: Sample state data structure
- `sample_article`: Sample article from Zendesk API
- `sample_articles_list`: List of sample articles
- `mock_openai_client`: Mock OpenAI client
- `mock_requests_response`: Mock HTTP response
- `env_vars`: Environment variables setup

## Best Practices

1. **Isolation**: Each test is independent and doesn't rely on other tests
2. **Mocking**: External dependencies (APIs, file I/O) are mocked
3. **Fixtures**: Common setup/teardown logic is in fixtures
4. **AAA Pattern**: Tests follow Arrange-Act-Assert structure
5. **Descriptive Names**: Test names clearly describe what they test
6. **Edge Cases**: Tests cover error conditions and boundary cases

## Continuous Integration

These tests are designed to run in CI/CD pipelines. They:
- Don't require external API access (all APIs are mocked)
- Don't require actual OpenAI credentials
- Use temporary directories that are cleaned up automatically
- Are deterministic and fast
