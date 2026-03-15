"""GDPR runtime anonymization — replace PII tokens in note body."""
from pathlib import Path
import sqlite3


def anonymize_note(
    path: Path,
    tokens: list[str],
    conn: sqlite3.Connection,
    downgrade_sensitivity: bool = False,
) -> dict:
    """Replace tokens with [REDACTED]. STUB."""
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError
