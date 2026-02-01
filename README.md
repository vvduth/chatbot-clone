# OptiBot Scraper

A Python pipeline that syncs OptiSigns Help Center articles to an OpenAI Vector Store for AI-powered customer support.

## What It Does

1. Fetches articles from Zendesk Help Center API
2. Converts HTML to clean Markdown (strips navigation, scripts, ads)
3. Uploads changed files to OpenAI Vector Store
4. Tracks state to avoid redundant uploads (cost optimization)

## Screen Shot
![agent reply](<working link youtube.png>)
* <i>Example of AI-powered agent replying using embeddings from Zendesk articles with citation.</i>

![another reply](<microsoft res.png>)
## Architecture

```
main.py
   ├── Scraper          → Zendesk API → HTML to Markdown
   ├── StateManager     → DigitalOcean Spaces (state.json)
   └── VectorStoreManager → OpenAI Files & Vector Store API
```

| File | Purpose |
|------|---------|
| `main.py` | Orchestrates the pipeline, handles stats |
| `scraper.py` | Fetches articles, converts HTML→Markdown |
| `state_manager.py` | Persists state to DO Spaces |
| `vector_store_manager.py` | OpenAI file uploads and vector store management |
| `config.py` | Environment variable loading |

## Delta Detection

The pipeline uses a two-layer change detection to minimize OpenAI API costs:

```python
# Skip if both timestamp and content hash match
if stored_last_modified == last_modified and last_hash == content_hash:
    skip()  # No upload needed
```

- **Layer 1**: Compare `Last-Modified` header from Zendesk API
- **Layer 2**: Compare MD5 hash of markdown content

State is stored in DigitalOcean Spaces (`state.json`), not the local filesystem. This ensures Docker containers can be ephemeral while state persists.

## Chunking Strategy

This pipeline uses **OpenAI's default chunking** for Vector Store file search:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_chunk_size_tokens` | 800 | Maximum tokens per chunk |
| `chunk_overlap_tokens` | 400 | Overlap between consecutive chunks |

**Why default chunking works well here:**

Our preprocessing (HTML → Markdown) removes noise that would otherwise pollute chunks:
- Navigation menus, footers, sidebars
- Script tags and inline styles  
- Advertising and tracking elements

The clean Markdown means OpenAI's chunker operates on pure content, producing higher-quality embeddings without custom tuning.

## Setup
### Clone Repository

```bash
git clone https://github.com/vvduth/chatbot-clone.git
cd chatbot-clone
```

### Environment Variables

Create a `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-...
ZENDESK_API_TOKEN=...
BUCKET_NAME=your-do-spaces-bucket
BUCKET_ACCESS_KEY_ID=...
BUCKET_SECRET_ACCESS_KEY=...

# Optional
ZENDESK_EMAIL=your-email@example.com
ZENDESK_DOMAIN=support.optisigns.com
```

### Run Locally

```bash
pip install -r requirements.txt
python main.py
```

### Run with Docker

```bash
docker build -t optibot-scraper .
docker run --env-file .env optibot-scraper
```

## Testing

Tests use pytest with mocking for external services (Zendesk, OpenAI, DO Spaces).

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_scraper.py -v
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (mock clients, sample data)
├── test_config.py           # Config loading tests
├── test_scraper.py          # Zendesk fetch + HTML conversion
├── test_state_manager.py    # State persistence to DO Spaces
├── test_vector_store_manager.py  # OpenAI API interactions
└── test_main.py             # Integration tests for full pipeline
```

### Key Testing Patterns

- **External APIs are mocked** — no real Zendesk/OpenAI calls in tests
- **State isolation** — each test gets fresh state
- **Error paths tested** — network failures, API errors, malformed data

## Logs

Output format: `TIMESTAMP - LEVEL - MESSAGE`

```
2026-01-28 16:44:02 - INFO - Starting OptiBot scraper job
2026-01-28 16:44:02 - INFO - Fetched 30 articles.
2026-01-28 16:44:02 - INFO - Skipping 12345 (No changes - hash and last_modified match)
2026-01-28 16:44:03 - INFO - Added local file: data/articles/67890-How-to-Setup.md
2026-01-28 16:44:04 - INFO - Uploaded file to OpenAI: file-abc123
2026-01-28 16:44:05 - INFO - Job Complete. Stats: {'added': 1, 'updated': 0, 'skipped': 29, 'deleted': 0}
```

## Deployment

Designed for DigitalOcean App Platform as a scheduled job:

```bash
# Deploy via CLI
doctl apps create --spec .do/app.yaml
```

Or via Dashboard:
1. Create App → Connect GitHub
2. Select "Scheduled Job" 
3. Schedule: `0 0 * * *` (daily at midnight UTC)
4. Add environment variables as secrets

## Utilities

```bash
# Reset everything (destructive!)
python -c "from main import clear_everything; clear_everything()"
```

This clears:
- All files from OpenAI Vector Store
- All files from OpenAI storage  
- State from DO Spaces
- Local markdown files


