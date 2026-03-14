"""Backlink maintenance and orphan checker (PEOPLE-03, PEOPLE-04, SEARCH-03). Implementation in plan 04-01."""
from pathlib import Path
import sqlite3


def add_backlinks(note_path: Path, people: list, brain_root: Path, conn: sqlite3.Connection) -> None:
    """Stub — implemented in plan 04-01."""
    raise NotImplementedError


def check_links(brain_root: Path, conn: sqlite3.Connection) -> list:
    """Stub — implemented in plan 04-01."""
    raise NotImplementedError


def main_check_links() -> None:
    """Stub — implemented in plan 04-01."""
    raise NotImplementedError
