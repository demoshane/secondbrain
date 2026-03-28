"""SQLite database layer — connection, schema init, FTS5 triggers."""
import logging
import sqlite3
from pathlib import Path
from engine.paths import DB_PATH

logger = logging.getLogger(__name__)

# ARCH-16: Canonical person type values used across engine modules
PERSON_TYPES = ("person",)
PERSON_TYPES_PH = ",".join("?" for _ in PERSON_TYPES)  # SQL placeholder string


def _escape_like(s: str) -> str:
    """ARCH-14: Escape LIKE wildcards in user-supplied strings."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
    conn.execute("PRAGMA foreign_keys = ON")
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


def migrate_add_assignee_path(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'assignee_path' TEXT column to action_items if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    if "assignee_path" not in cols:
        conn.execute("ALTER TABLE action_items ADD COLUMN assignee_path TEXT NULL")
        conn.commit()


def migrate_add_due_date(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'due_date' TEXT column to action_items if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    if "due_date" not in cols:
        conn.execute("ALTER TABLE action_items ADD COLUMN due_date TEXT NULL")
        conn.commit()


def migrate_add_done_at(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'done_at' TEXT column to action_items if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    if "done_at" not in cols:
        conn.execute("ALTER TABLE action_items ADD COLUMN done_at TEXT NULL")
        conn.commit()


def migrate_add_dismissed_inbox_items_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create dismissed_inbox_items table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dismissed_inbox_items (
            path         TEXT NOT NULL,
            item_type    TEXT NOT NULL,
            dismissed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            PRIMARY KEY (path, item_type)
        )
    """)
    conn.commit()


def migrate_add_url_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'url' TEXT column to notes if absent."""
    try:
        conn.execute("ALTER TABLE notes ADD COLUMN url TEXT NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists


def migrate_add_action_items_archive_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create action_items_archive table if absent.

    Archives completed action items older than 90 days for GDPR audit trail.
    Columns mirror action_items plus archived_at and archived_reason.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS action_items_archive (
            id              INTEGER PRIMARY KEY,
            note_path       TEXT NOT NULL,
            text            TEXT NOT NULL,
            done_at         TEXT,
            created_at      TEXT NOT NULL,
            archived_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            archived_reason TEXT NOT NULL DEFAULT 'auto_90day'
        )
    """)
    conn.commit()


def migrate_add_note_tags_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create note_tags junction table and populate from JSON tags column.

    Creates:
        note_tags(note_path TEXT, tag TEXT, PRIMARY KEY (note_path, tag),
                  FOREIGN KEY note_path REFERENCES notes(path) ON DELETE CASCADE)
    Indexes: idx_note_tags_tag on (tag), idx_note_tags_note_path on (note_path).
    Populates from existing notes.tags JSON column via INSERT OR IGNORE.
    Migration is idempotent — running twice inserts no duplicates.
    """
    import json as _json
    conn.execute("""
        CREATE TABLE IF NOT EXISTS note_tags (
            note_path TEXT NOT NULL,
            tag       TEXT NOT NULL,
            PRIMARY KEY (note_path, tag),
            FOREIGN KEY (note_path) REFERENCES notes(path) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_tag ON note_tags(tag)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_note_path ON note_tags(note_path)")
    conn.commit()

    rows = conn.execute("SELECT path, tags FROM notes WHERE tags IS NOT NULL AND tags != '[]'").fetchall()
    count = 0
    for (note_path, tags_json) in rows:
        try:
            tags = _json.loads(tags_json or "[]")
        except Exception:
            continue
        for tag in tags:
            if tag:
                conn.execute(
                    "INSERT OR IGNORE INTO note_tags (note_path, tag) VALUES (?, ?)",
                    (note_path, tag),
                )
                count += 1
    conn.commit()
    logger.info("migrate_add_note_tags_table: populated %d tag rows from JSON column", count)


def migrate_add_note_people_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create note_people junction table and populate from JSON people column.

    Creates:
        note_people(note_path TEXT, person TEXT, PRIMARY KEY (note_path, person),
                    FOREIGN KEY note_path REFERENCES notes(path) ON DELETE CASCADE)
    Indexes: idx_note_people_person on (person), idx_note_people_note_path on (note_path).
    Populates from existing notes.people JSON column via INSERT OR IGNORE.
    Drops the useless idx_notes_people index on the JSON text column.
    Migration is idempotent — running twice inserts no duplicates.
    """
    import json as _json
    conn.execute("""
        CREATE TABLE IF NOT EXISTS note_people (
            note_path TEXT NOT NULL,
            person    TEXT NOT NULL,
            PRIMARY KEY (note_path, person),
            FOREIGN KEY (note_path) REFERENCES notes(path) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_people_person ON note_people(person)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_people_note_path ON note_people(note_path)")
    # Drop the useless JSON text index — it does not help filter queries
    conn.execute("DROP INDEX IF EXISTS idx_notes_people")
    conn.commit()

    rows = conn.execute(
        "SELECT path, people FROM notes WHERE people IS NOT NULL AND people != '[]'"
    ).fetchall()
    count = 0
    for (note_path, people_json) in rows:
        try:
            people = _json.loads(people_json or "[]")
        except Exception:
            continue
        for person in people:
            if person:
                conn.execute(
                    "INSERT OR IGNORE INTO note_people (note_path, person) VALUES (?, ?)",
                    (note_path, person),
                )
                count += 1
    conn.commit()
    logger.info("migrate_add_note_people_table: populated %d person rows from JSON column", count)


def migrate_paths_to_relative(conn: sqlite3.Connection, brain_root: Path | None = None) -> None:
    """Convert all absolute paths in DB tables to paths relative to brain_root.

    Migrates the following columns:
    - notes.path
    - relationships.source_path, relationships.target_path
    - action_items.note_path, action_items.assignee_path
    - note_embeddings.note_path
    - audit_log.note_path
    - attachments.note_path

    Already-relative paths are untouched. Paths outside brain_root are skipped
    with a warning. Migration runs in a single transaction. Idempotent — running
    twice produces the same result.

    Args:
        conn: Open SQLite connection with schema initialized.
        brain_root: Brain root path. Defaults to engine.paths.BRAIN_ROOT.
    """
    if brain_root is None:
        # Import dynamically so monkeypatching engine.paths.BRAIN_ROOT works in tests
        import engine.paths as _paths
        brain_root = _paths.BRAIN_ROOT
    brain_root = Path(brain_root)

    # Check if there are any absolute paths to migrate
    row = conn.execute("SELECT COUNT(*) FROM notes WHERE path LIKE '/%'").fetchone()
    if row[0] == 0:
        logger.debug("migrate_paths_to_relative: no absolute paths found — skipping")
        return

    count_total = row[0]
    count_migrated = 0
    count_skipped = 0

    # Build a mapping of absolute path → relative path for all notes
    abs_rows = conn.execute("SELECT path FROM notes WHERE path LIKE '/%'").fetchall()
    path_map: dict[str, str] = {}
    for (abs_path,) in abs_rows:
        try:
            rel = str(Path(abs_path).relative_to(brain_root))
            path_map[abs_path] = rel
            count_migrated += 1
        except ValueError:
            logger.warning(
                "migrate_paths_to_relative: path outside BRAIN_ROOT, skipping: %s", abs_path
            )
            count_skipped += 1

    if not path_map:
        logger.info(
            "migrate_paths_to_relative: all %d absolute paths outside BRAIN_ROOT — skipped",
            count_skipped,
        )
        return

    # Disable FK enforcement for the duration of this migration.
    # Updating notes.path (PK) while child tables still hold the old value would
    # violate FK constraints — we update all tables atomically, so FKs are
    # consistent at the end of the transaction even if momentarily violated.
    original_fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        with conn:
            for abs_path, rel_path in path_map.items():
                # If the relative path already exists, the absolute row is a stale duplicate — remove it.
                existing = conn.execute("SELECT 1 FROM notes WHERE path=?", (rel_path,)).fetchone()
                if existing:
                    conn.execute("DELETE FROM notes WHERE path=?", (abs_path,))
                    logger.warning(
                        "migrate_paths_to_relative: duplicate removed (relative path already exists): %s",
                        abs_path,
                    )
                    continue
                conn.execute(
                    "UPDATE notes SET path=? WHERE path=?",
                    (rel_path, abs_path),
                )
                conn.execute(
                    "UPDATE relationships SET source_path=? WHERE source_path=?",
                    (rel_path, abs_path),
                )
                conn.execute(
                    "UPDATE relationships SET target_path=? WHERE target_path=?",
                    (rel_path, abs_path),
                )
                conn.execute(
                    "UPDATE action_items SET note_path=? WHERE note_path=?",
                    (rel_path, abs_path),
                )
                try:
                    # assignee_path may not exist on older schemas — guard idempotently
                    conn.execute(
                        "UPDATE action_items SET assignee_path=? WHERE assignee_path=?",
                        (rel_path, abs_path),
                    )
                except sqlite3.OperationalError:
                    pass
                conn.execute(
                    "UPDATE note_embeddings SET note_path=? WHERE note_path=?",
                    (rel_path, abs_path),
                )
                conn.execute(
                    "UPDATE audit_log SET note_path=? WHERE note_path=?",
                    (rel_path, abs_path),
                )
                conn.execute(
                    "UPDATE attachments SET note_path=? WHERE note_path=?",
                    (rel_path, abs_path),
                )
    finally:
        conn.execute(f"PRAGMA foreign_keys = {original_fk}")  # noqa: S608 — integer value from PRAGMA, not user input

    logger.info(
        "migrate_paths_to_relative: migrated %d paths to relative (%d skipped outside BRAIN_ROOT)",
        count_migrated,
        count_skipped,
    )


def migrate_people_type_to_person(conn: sqlite3.Connection) -> None:
    """Idempotent migration: rename note type 'people' → 'person'."""
    conn.execute("UPDATE notes SET type = 'person' WHERE type = 'people'")
    conn.commit()


def migrate_add_health_snapshots_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create health_snapshots table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_snapshots (
            id              INTEGER PRIMARY KEY,
            snapped_at      TEXT NOT NULL,
            score           INTEGER,
            total_notes     INTEGER,
            orphan_count    INTEGER,
            broken_count    INTEGER,
            duplicate_count INTEGER,
            stub_count      INTEGER
        )
    """)
    conn.commit()


def migrate_create_note_chunks(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create note_chunks table if absent.

    Stores per-chunk text and embedding blobs produced by split_text_into_chunks()
    during embed_pass(). Enables paragraph-level search and excerpt return for
    long notes (>= CHUNK_THRESHOLD characters).

    Columns:
        id          - rowid alias
        note_path   - absolute (or relative) path matching notes.path
        chunk_index - zero-based position within the note
        chunk_text  - raw character window text
        embedding   - float32 BLOB (same dimensions as note_embeddings.embedding)
        created_at  - ISO8601 UTC timestamp

    Constraints:
        UNIQUE(note_path, chunk_index) — one row per chunk position per note;
        ON CONFLICT ... DO UPDATE is used by embed_pass for idempotent writes.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS note_chunks (
            id          INTEGER PRIMARY KEY,
            note_path   TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text  TEXT NOT NULL,
            embedding   BLOB,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(note_path, chunk_index)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_note_chunks_path ON note_chunks(note_path)"
    )
    conn.commit()


def migrate_add_archived_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'archived' INTEGER column to notes (0=active, 1=archived)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "archived" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def migrate_add_summary_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'summary' TEXT column to notes for auto-generated summaries."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "summary" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN summary TEXT")
        conn.commit()


def migrate_add_status_column(conn: sqlite3.Connection) -> None:
    """Idempotent: add 'status' TEXT column to notes if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "status" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        conn.commit()


def migrate_create_person_insights(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create person_insights table for 24h-cached AI insights."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS person_insights (
            person_path  TEXT PRIMARY KEY,
            insight      TEXT NOT NULL DEFAULT '',
            generated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()


def migrate_create_audit_log_archive(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create audit_log_archive table if absent.

    Archives audit log entries older than 90 days to keep the hot audit_log
    table performant at scale (100K+ note operations).
    Columns mirror audit_log plus archived_at (filled by DEFAULT on insert).
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log_archive (
            id          INTEGER PRIMARY KEY,
            event_type  TEXT NOT NULL,
            note_path   TEXT,
            detail      TEXT,
            created_at  TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()


def _migrate_fk_cascade(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add ON DELETE CASCADE FK constraints to note_embeddings,
    action_items, and relationships using the rename-recreate pattern.

    SQLite does not support ALTER TABLE ... ADD CONSTRAINT, so each table must be
    recreated with the correct schema. Existing data is preserved via INSERT SELECT.

    audit_log is intentionally excluded — audit entries must survive note deletion
    for compliance.

    Migration is skipped if note_embeddings already has ON DELETE CASCADE
    (detected via PRAGMA foreign_key_list).
    """
    # Check if migration already applied by inspecting note_embeddings FK
    fk_list = conn.execute("PRAGMA foreign_key_list(note_embeddings)").fetchall()
    already_cascaded = any(row[6] == "CASCADE" for row in fk_list)  # row[6] = on_delete
    if already_cascaded:
        logger.debug("_migrate_fk_cascade: already applied, skipping")
        return

    logger.info("_migrate_fk_cascade: applying FK CASCADE migration")

    # Save the current FK enforcement state and disable it during migration.
    # Recreating tables while child rows reference the old table name requires FK OFF.
    # We restore to the original state (not unconditionally ON) so callers using
    # raw sqlite3.connect() (e.g. tests) are not silently affected.
    original_fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        with conn:
            # --- note_embeddings ---
            # Inspect actual columns (future-proof against additional migrations)
            ne_cols = [row[1] for row in conn.execute("PRAGMA table_info(note_embeddings)").fetchall()]
            conn.execute("ALTER TABLE note_embeddings RENAME TO _ne_old")
            conn.execute("""
                CREATE TABLE note_embeddings (
                    note_path    TEXT PRIMARY KEY REFERENCES notes(path) ON DELETE CASCADE,
                    embedding    BLOB,
                    content_hash TEXT,
                    stale        BOOL NOT NULL DEFAULT 0,
                    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                )
            """)
            col_list = ", ".join(ne_cols)
            conn.execute(f"INSERT INTO note_embeddings ({col_list}) SELECT {col_list} FROM _ne_old")  # noqa: S608
            conn.execute("DROP TABLE _ne_old")

            # --- action_items ---
            # Columns vary by migration history — discover at runtime
            ai_cols = [row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()]
            conn.execute("ALTER TABLE action_items RENAME TO _ai_old")
            # Build the CREATE TABLE with all columns from current schema.
            # Base columns always present; extended columns discovered via PRAGMA.
            ai_col_defs = (
                "id INTEGER PRIMARY KEY, "
                "note_path TEXT NOT NULL REFERENCES notes(path) ON DELETE CASCADE, "
                "text TEXT NOT NULL, "
                "done BOOL NOT NULL DEFAULT 0, "
                "created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))"
            )
            extra_defs = []
            if "assignee_path" in ai_cols:
                extra_defs.append("assignee_path TEXT NULL")
            if "due_date" in ai_cols:
                extra_defs.append("due_date TEXT NULL")
            if "done_at" in ai_cols:
                extra_defs.append("done_at TEXT NULL")
            if extra_defs:
                ai_col_defs += ", " + ", ".join(extra_defs)
            conn.execute(f"CREATE TABLE action_items ({ai_col_defs})")  # noqa: S608
            col_list_ai = ", ".join(ai_cols)
            conn.execute(f"INSERT INTO action_items ({col_list_ai}) SELECT {col_list_ai} FROM _ai_old")  # noqa: S608
            conn.execute("DROP TABLE _ai_old")

            # --- relationships ---
            # Check actual columns (composite PK: source_path, target_path, rel_type)
            rel_cols = [row[1] for row in conn.execute("PRAGMA table_info(relationships)").fetchall()]
            conn.execute("ALTER TABLE relationships RENAME TO _rel_old")
            conn.execute("""
                CREATE TABLE relationships (
                    source_path TEXT NOT NULL REFERENCES notes(path) ON DELETE CASCADE,
                    target_path TEXT NOT NULL REFERENCES notes(path) ON DELETE CASCADE,
                    rel_type    TEXT NOT NULL DEFAULT 'link',
                    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    PRIMARY KEY (source_path, target_path, rel_type)
                )
            """)
            col_list_rel = ", ".join(rel_cols)
            conn.execute(f"INSERT INTO relationships ({col_list_rel}) SELECT {col_list_rel} FROM _rel_old")  # noqa: S608
            conn.execute("DROP TABLE _rel_old")

    finally:
        conn.execute(f"PRAGMA foreign_keys = {original_fk}")  # noqa: S608 — integer value from PRAGMA, not user input

    logger.info("_migrate_fk_cascade: FK CASCADE migration complete")


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
    migrate_add_assignee_path(conn)
    migrate_add_due_date(conn)
    migrate_add_done_at(conn)
    migrate_add_dismissed_inbox_items_table(conn)
    migrate_add_url_column(conn)
    migrate_add_action_items_archive_table(conn)
    # ARCH-01: Convert absolute paths to relative — must run before junction table migrations
    migrate_paths_to_relative(conn)
    # ARCH-05/15: Junction tables for indexed tag and people lookups (32-03)
    migrate_add_note_tags_table(conn)
    migrate_add_note_people_table(conn)
    migrate_people_type_to_person(conn)
    migrate_add_health_snapshots_table(conn)
    migrate_create_audit_log_archive(conn)
    migrate_create_note_chunks(conn)
    migrate_add_archived_column(conn)
    migrate_add_summary_column(conn)
    migrate_add_status_column(conn)
    migrate_create_person_insights(conn)
    # F-10: Add FK CASCADE constraints to note_embeddings, action_items, relationships
    _migrate_fk_cascade(conn)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_url ON notes(url)")
    # idx_notes_people is dropped by migrate_add_note_people_table — do not re-create
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created_path ON audit_log(created_at, note_path)")
    # F-10 performance indexes: archived filter and action_items lookup
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_archived ON notes(archived)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_action_items_note_path ON action_items(note_path)")
    conn.commit()
