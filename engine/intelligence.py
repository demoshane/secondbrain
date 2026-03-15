"""Intelligence layer: session recap, action items, stale nudges, connection suggestions."""
import json
import datetime
import subprocess
from pathlib import Path

STATE_PATH = Path.home() / ".meta" / "intelligence_state.json"
VAULT_GATE = 20


def _load_state() -> dict:
    return {}


def _save_state(state: dict) -> None:
    pass


def budget_available(conn) -> bool:
    return False


def consume_budget() -> None:
    pass


def detect_git_context() -> str | None:
    return None


def extract_action_items(note_path: Path, body: str, sensitivity: str, conn) -> None:
    pass


def get_stale_notes(conn, days: int = 90, limit: int = 5) -> list[dict]:
    return []


def check_stale_nudge(conn) -> None:
    pass


def find_similar(note_path: str, conn, threshold: float = 0.8, limit: int = 3) -> list[dict]:
    return []


def check_connections(note_path: Path, conn, brain_root: Path) -> None:
    pass


def recap_main(argv=None) -> None:
    pass


def actions_main(argv=None) -> None:
    pass
