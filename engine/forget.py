from pathlib import Path
import sqlite3


def forget_person(slug: str, brain_root: Path, conn: sqlite3.Connection) -> dict:
    """Erase all traces of a person from brain and index. GDPR-01, GDPR-02."""
    raise NotImplementedError


def main() -> None:
    """CLI entry point for sb-forget."""
    raise NotImplementedError
