"""GDPR Article 20 data portability — sb-export CLI."""
import json
import datetime
from pathlib import Path
import sqlite3


def export_brain(brain_root: Path, conn: sqlite3.Connection, output_path: Path, fmt: str = "json") -> int:
    """Export all notes to portable format. Returns count. STUB."""
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError
