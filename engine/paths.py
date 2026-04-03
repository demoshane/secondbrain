import os
from pathlib import Path
from typing import NamedTuple


class ResolvedPath(NamedTuple):
    """A note path carrying both the absolute (for disk I/O) and relative (for DB) forms."""
    absolute: Path
    relative: str

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
    "projects", "personal", "ideas", "files", "syntheses", ".meta", ".meta/templates"
]


def store_path(abs_path: "str | Path") -> str:
    """Convert an absolute path to a relative path (relative to BRAIN_ROOT).

    If the path is already relative (does not start with '/'), return it as-is.
    If the path is outside BRAIN_ROOT, raise ValueError.

    Args:
        abs_path: Absolute or relative path to a note file.

    Returns:
        Relative path string (POSIX, no leading slash).

    Raises:
        ValueError: If abs_path is absolute but outside BRAIN_ROOT.
    """
    p = Path(abs_path)
    if not p.is_absolute():
        # Already relative — return as-is (idempotent for already-migrated paths)
        return str(abs_path)
    try:
        return str(p.relative_to(BRAIN_ROOT))
    except ValueError:
        raise ValueError(
            f"Path {abs_path!r} is outside BRAIN_ROOT {BRAIN_ROOT!r}"
        )


def resolve_path(rel_path: "str | Path") -> Path:
    """Resolve a relative path to an absolute Path using BRAIN_ROOT.

    If the path is already absolute, return it as-is (backward compatibility
    during the migration window when some DB rows may still have absolute paths).

    Args:
        rel_path: Relative path string (e.g. "coding/note.md") or absolute path.

    Returns:
        Absolute Path object.
    """
    p = Path(rel_path)
    if p.is_absolute():
        return p  # backward compat — already absolute
    return BRAIN_ROOT / p
