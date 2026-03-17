"""SQLite database layer — connection, schema init, FTS5 triggers."""
import sqlite3
from pathlib import Path
from engine.paths import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY,
    path        TEXT UNIQUE NOT NULL,
    type        TEXT NOT NULL DEFAULT 'note',
    title       TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    tags        TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    sensitivity TEXT NOT NULL DEFAULT 'public'
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    body,
    content=notes,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

CREATE TABLE IF NOT EXISTS relationships (
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    rel_type    TEXT NOT NULL DEFAULT 'link',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (source_path, target_path, rel_type)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    note_path  TEXT,
    detail     TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS note_embeddings (
    note_path    TEXT PRIMARY KEY,
    embedding    BLOB,
    content_hash TEXT,
    stale        BOOL NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS action_items (
    id         INTEGER PRIMARY KEY,
    note_path  TEXT NOT NULL,
    text       TEXT NOT NULL,
    done       BOOL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
"""

DROP_SQL = """
DROP TABLE IF EXISTS notes_fts;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS relationships;
DROP TABLE IF EXISTS audit_log;
"""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a connection to the brain SQLite database.

    Args:
        db_path: Optional path string to override DB_PATH (useful in tests).
    """
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def migrate_add_people_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'people' TEXT column to notes if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "people" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]'")
        conn.commit()


def migrate_add_entities_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'entities' TEXT column to notes if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "entities" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN entities TEXT NOT NULL DEFAULT '{}'")
        conn.commit()


def migrate_add_action_items_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create action_items table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS action_items (
            id         INTEGER PRIMARY KEY,
            note_path  TEXT NOT NULL,
            text       TEXT NOT NULL,
            done       BOOL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()


def migrate_add_attachments_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create attachments table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id          INTEGER PRIMARY KEY,
            note_path   TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            filename    TEXT NOT NULL,
            size        INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()


def init_schema(conn: sqlite3.Connection, reset: bool = False) -> None:
    """Create (or optionally recreate) the full schema.

    Idempotent when reset=False — uses IF NOT EXISTS throughout.
    When reset=True, drops all tables first (DESTRUCTIVE).
    """
    if reset:
        conn.executescript(DROP_SQL)

    conn.executescript(SCHEMA_SQL)
    migrate_add_people_column(conn)
    migrate_add_entities_column(conn)
    migrate_add_action_items_table(conn)
    migrate_add_attachments_table(conn)
