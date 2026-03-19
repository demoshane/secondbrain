import os
from pathlib import Path

def _detect_roots() -> tuple[Path, Path]:
    # Env var override (used by tests and custom setups)
    env = os.environ.get("BRAIN_PATH")
    if env:
        p = Path(env)
        return p, p / ".index"
    # Container: /workspace/brain mounted by devcontainer
    workspace = Path("/workspace")
    if workspace.exists() and not (workspace.stat().st_mode & 0o200 == 0):
        return workspace / "brain", workspace / "brain-index"
    # Host: ~/SecondBrain
    host = Path.home() / "SecondBrain"
    return host, host / ".index"

BRAIN_ROOT, INDEX_ROOT = _detect_roots()
DB_PATH       = INDEX_ROOT / "brain.db"
META_DIR      = BRAIN_ROOT / ".meta"
TEMPLATES_DIR = META_DIR / "templates"
CONFIG_FILE   = META_DIR / "config.toml"
CONFIG_PATH   = CONFIG_FILE  # alias used by engine/ai.py and capture.py

BRAIN_SUBDIRS = [
    "coding", "person", "meetings", "strategy",
    "projects", "personal", "ideas", "files", ".meta", ".meta/templates"
]
