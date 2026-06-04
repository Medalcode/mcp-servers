import os
from pathlib import Path

DATA_DIR = Path(os.getenv("PATHWISE_DATA_DIR", str(Path.home() / ".local" / "share" / "pathwise")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = os.getenv("PATHWISE_DB_PATH", str(DATA_DIR / "pathwise.db"))
PROFILE_PATH = os.getenv("PATHWISE_PROFILE_PATH", str(Path.cwd() / "profile.json"))
ROUTEMCP_ENABLED = os.getenv("ROUTEMCP_ENABLED", "true").lower() == "true"
SCRAPEMCP_ENABLED = os.getenv("SCRAPEMCP_ENABLED", "true").lower() == "true"
BROWSERMCP_ENABLED = os.getenv("BROWSERMCP_ENABLED", "true").lower() == "true"
