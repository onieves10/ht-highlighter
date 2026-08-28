"""Central config — loads .env (gitignored). Nothing secret is hardcoded."""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Railway auto-injects DATABASE_URL in prod. Empty -> in-memory cache fallback.
DATABASE_URL = os.getenv("DATABASE_URL", "") or ""
CRM_CSV_URL = os.getenv("CRM_CSV_URL", "")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "HT Highlighter example@example.com")

# Single knob for the model so it's trivial to swap.
MODEL = os.getenv("MODEL", "claude-sonnet-4-6")

CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "7"))
