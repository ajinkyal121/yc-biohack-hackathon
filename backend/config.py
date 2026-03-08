import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TAMARIND_API_KEY = os.getenv("TAMARIND_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
TAMARIND_BASE_URL = os.getenv("TAMARIND_BASE_URL", "https://app.tamarind.bio/api")
BIORXIV_BASE_URL = os.getenv("BIORXIV_BASE_URL", "https://api.biorxiv.org")
MAX_PAPERS = int(os.getenv("MAX_PAPERS", "5"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
MAX_LOOP_ITERATIONS = int(os.getenv("MAX_LOOP_ITERATIONS", "3"))
USE_PDF_SUMMARIZATION = os.getenv("USE_PDF_SUMMARIZATION", "false").lower() == "true"
