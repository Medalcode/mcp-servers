import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = os.getenv("PATHWISE_DB_PATH", str(BASE_DIR / "pathwise.db"))
PROFILE_PATH = os.getenv("PATHWISE_PROFILE_PATH", str(BASE_DIR / "profile.json"))
ROUTEMCP_ENABLED = os.getenv("ROUTEMCP_ENABLED", "true").lower() == "true"
SCRAPEMCP_ENABLED = os.getenv("SCRAPEMCP_ENABLED", "true").lower() == "true"
BROWSERMCP_ENABLED = os.getenv("BROWSERMCP_ENABLED", "true").lower() == "true"
