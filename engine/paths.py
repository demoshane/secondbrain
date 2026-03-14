from pathlib import Path

def _detect_roots() -> tuple[Path, Path]:
    workspace = Path("/workspace")
    if workspace.exists() and not (workspace.stat().st_mode & 0o200 == 0):
        return workspace / "brain", workspace / "brain-index"
    host = Path.home() / "SecondBrain"
    return host, host / ".index"

BRAIN_ROOT, INDEX_ROOT = _detect_roots()
DB_PATH       = INDEX_ROOT / "brain.db"
META_DIR      = BRAIN_ROOT / ".meta"
TEMPLATES_DIR = META_DIR / "templates"
CONFIG_FILE   = META_DIR / "config.toml"
CONFIG_PATH   = CONFIG_FILE  # alias used by engine/ai.py and capture.py

BRAIN_SUBDIRS = [
    "coding", "people", "meetings", "strategy",
    "projects", "personal", "ideas", "files", ".meta", ".meta/templates"
]
