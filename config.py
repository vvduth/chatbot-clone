import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ZENDESK_DOMAIN = "support.optisigns.com"
API_BASE_URL = f"https://{ZENDESK_DOMAIN}/api/v2/help_center/articles.json"
OUTPUT_DIR = "data/articles"
STATE_FILE = "data/state.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
