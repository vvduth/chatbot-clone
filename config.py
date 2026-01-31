import os
from dotenv import load_dotenv

# Load environment variables (optional, for local development)
# In Docker/production, environment variables should be set directly
load_dotenv()

# Configuration
ZENDESK_DOMAIN = os.getenv("ZENDESK_DOMAIN", "support.optisigns.com")
API_BASE_URL = f"https://{ZENDESK_DOMAIN}/api/v2/help_center/articles.json"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/articles")
STATE_FILE = os.getenv("STATE_FILE", "data/state.json")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
