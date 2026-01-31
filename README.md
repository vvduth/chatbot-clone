# OptiBot Mini-Clone

This repository contains a daily job that scrapes OptiSigns support articles, converts them to clean Markdown, and syncs them to an OpenAI Vector Store for use by an AI Assistant.

## Features

- **Delta Detection**: Uses MD5 hash and Last-Modified headers for efficient change detection
- **State Persistence**: Tracks processed articles to only upload changes
- **Dockerized**: Ready for containerized deployment
- **Scheduled Jobs**: Configured for Digital Ocean App Platform daily execution

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/vvduth/chatbot-clone.git
    cd chatbot-clone
    ```

2.  **Environment Variables:**
    Create a `.env` file with the following variables:
    ```bash
    OPENAI_API_KEY=your_openai_api_key
    ZENDESK_API_TOKEN=your_zendesk_token
    ZENDESK_EMAIL=your_email@example.com
    ```
    *   `OPENAI_API_KEY`: Required for Vector Store sync.
    *   `ZENDESK_API_TOKEN`: Required for authenticated API access.
    *   `ZENDESK_EMAIL`: Your Zendesk account email (used for API authentication).

## How to Run

### Run Locally (Python)

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the scraper:
    ```bash
    python main.py
    ```

### Run with Docker

1.  Build the image:
    ```bash
    docker build -t optibot-scraper .
    ```
2.  Run the job:
    ```bash
    docker run --env-file .env optibot-scraper
    ```
3.  Run with volume for state persistence:
    ```bash
    docker run --env-file .env -v $(pwd)/data:/app/data optibot-scraper
    ```

## Architecture & Logic

### Scraper
The `main.py` script helps fetch articles from `support.optisigns.com` via the Zendesk API.
-   **Extraction**: URLs are fetched via `/api/v2/help_center/articles.json`.
-   **Normalization**: HTML bodies are converted to Markdown using `markdownify`. This removes navigation, scripts, and ads, preserving only headers, text, and links.
-   **Delta Tracking**: Enhanced change detection using both MD5 hash and Last-Modified headers.
    -   **Fast Path**: If `last_modified` timestamp matches stored value AND hash matches → skip (no API call needed)
    -   **Hash Check**: If hash matches stored value → skip
    -   **Upload**: If hash differs or article is new → process and upload to OpenAI
    -   State is persisted in `data/state.json` for tracking across runs

### State Persistence
- State file (`data/state.json`) stores:
  - Article hashes for content comparison
  - Last-Modified timestamps from API responses
  - OpenAI file IDs for vector store management
  - Vector store ID for persistence across runs
- **Important**: For scheduled jobs, mount a volume to persist the `data/` directory

### OpenAI Integration
We use the **OpenAI Vector Store** (beta) for embeddings.
-   **Chunking Strategy**: We rely on OpenAI's native file search chunking. However, our pre-processing (HTML -> Markdown) significantly improves chunk quality by removing non-content HTML noise that would otherwise pollute the embeddings.
-   **Uploads**: Only changed files are uploaded to save bandwidth and API costs.
-   **Files**: Stored in `data/articles/` locally for debug/review.

## Logs
The job outputs structured logs to `stdout`.
-   **Daily Job**: On platforms like DigitalOcean, these logs are automatically captured and archived.
-   **Format**: `TIMESTAMP - LEVEL - MESSAGE`
-   **Sample**:
    ```text
    2026-01-28 16:44:02 - INFO - Fetched 30 articles.
    2026-01-28 16:44:02 - INFO - Skipped 3433 (No changes)
    2026-01-28 16:44:02 - INFO - Updated local file: data/articles/123-How-to-Setup.md
    2026-01-28 16:44:03 - INFO - Uploaded file to OpenAI: file-abc12345
    ```

## Deployment on Digital Ocean App Platform

### Prerequisites
- Digital Ocean account
- GitHub repository with this code
- Environment variables configured

### Quick Deploy

1. **Update `.do/app.yaml`**:
   - Set your GitHub repository path
   - Verify environment variable names

2. **Deploy via CLI**:
   ```bash
   doctl apps create --spec .do/app.yaml
   ```

3. **Or deploy via Dashboard**:
   - Go to [Digital Ocean App Platform](https://cloud.digitalocean.com/apps)
   - Create new app → Connect GitHub → Select "Scheduled Job"
   - Configure schedule: `0 0 * * *` (daily at midnight UTC)
   - Add environment variables as secrets
   - Mount volume at `/app/data` for state persistence
   - Deploy

### Configuration

- **Schedule**: Daily at midnight UTC (configurable in `app.yaml`)
- **Resources**: Minimal (basic-xxs) - suitable for scheduled jobs
- **State Persistence**: Volume mounted at `/app/data` (1 GB)
- **Logs**: Available in Digital Ocean dashboard

See [.do/README.md](.do/README.md) for detailed deployment instructions.

## Assistant Setup (Playground)

To recreate the OptiBot Assistant:
1.  Go to [OpenAI Playground](https://platform.openai.com/playground).
2.  Create a new Assistant.
3.  **Name**: OptiBot
4.  **Instructions**:
    > You are OptiBot, the customer-support bot for OptiSigns.com.
    > • Tone: helpful, factual, concise.
    > • Only answer using the uploaded docs.
    > • Max 5 bullet points; else link to the doc.
    > • Cite up to 3 "Article URL:" lines per reply.
5.  **Tools**: Enable "File Search".
6.  **Vector Store**: Select "OptiBot Knowledge Base" (created by this script).
