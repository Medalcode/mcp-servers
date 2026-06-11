import os
from pathlib import Path


def get_data_dir() -> Path:
    d = Path(os.getenv("PATHWISE_DATA_DIR", str(Path.home() / ".local" / "share" / "pathwise")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> str:
    return os.getenv("PATHWISE_DB_PATH", str(get_data_dir() / "pathwise.db"))


def get_profile_path() -> str:
    return os.getenv("PATHWISE_PROFILE_PATH", str(Path.cwd() / "profile.json"))


def is_scrapemcp_enabled() -> bool:
    return os.getenv("SCRAPEMCP_ENABLED", "true").lower() == "true"


def is_browsermcp_enabled() -> bool:
    return os.getenv("BROWSERMCP_ENABLED", "true").lower() == "true"
