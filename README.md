# OptiBot Mini-Clone

This repository contains a daily job that scrapes OptiSigns support articles, converts them to clean Markdown, and syncs them to an OpenAI Vector Store for use by an AI Assistant.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repo_url>
    cd <repo_name>
    ```

2.  **Environment Variables:**
    Copy `.env.sample` to `.env` and fill in your keys:
    ```bash
    cp .env.sample .env
    ```
    *   `OPENAI_API_KEY`: Required for Vector Store sync.
    *   `ZENDESK_API_TOKEN`: Optional (public articles are fetched without it).

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

## Architecture & Logic

### Scraper
The `main.py` script helps fetch articles from `support.optisigns.com` via the Zendesk API.
-   **Extraction**: URLs are fetched via `/api/v2/help_center/articles.json`.
-   **Normalization**: HTML bodies are converted to Markdown using `markdownify`. This removes navigation, scripts, and ads, preserving only headers, text, and links.
-   **Delta Tracking**: We calculate an MD5 hash of the normalized Markdown content.
    -   If the hash matches the local state (`data/state.json`), the file is **skipped**.
    -   If the hash differs or the file is new, it is **uploaded** to OpenAI.

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
