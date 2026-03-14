from pathlib import Path

BRAIN_ROOT    = Path("/workspace/brain")
INDEX_ROOT    = Path("/workspace/brain-index")
DB_PATH       = INDEX_ROOT / "brain.db"
META_DIR      = BRAIN_ROOT / ".meta"
TEMPLATES_DIR = META_DIR / "templates"
CONFIG_FILE   = META_DIR / "config.toml"

BRAIN_SUBDIRS = [
    "coding", "people", "meetings", "strategy",
    "projects", "personal", "ideas", "files", ".meta"
]
