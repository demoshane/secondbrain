from pathlib import Path
import sqlite3


def read_note(path: Path, conn: sqlite3.Connection) -> int:
    """Display note, gating PII notes behind passphrase. GDPR-04. Returns 0 on success, 1 on denial."""
    raise NotImplementedError


def main() -> None:
    """CLI entry point for sb-read."""
    raise NotImplementedError
