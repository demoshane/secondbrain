import sqlite3
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.db import init_schema


def test_schema_complete(db_conn):
    init_schema(db_conn)
    tables = {r[0] for r in db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','shadow')"
    ).fetchall()}
    for expected in ["notes", "relationships", "audit_log"]:
        assert expected in tables, f"Table {expected} missing"
    # FTS5 virtual table shows as 'table' in sqlite_master
    all_names = {r[0] for r in db_conn.execute(
        "SELECT name FROM sqlite_master"
    ).fetchall()}
    assert "notes_fts" in all_names


def test_schema_idempotent(db_conn):
    init_schema(db_conn)
    init_schema(db_conn)  # second call must not raise


def test_fts5_triggers_exist(db_conn):
    init_schema(db_conn)
    triggers = {r[0] for r in db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'"
    ).fetchall()}
    for t in ["notes_ai", "notes_ad", "notes_au"]:
        assert t in triggers, f"Trigger {t} missing"


def test_foreign_keys_enabled(db_conn):
    """get_connection() must enable PRAGMA foreign_keys on every connection."""
    row = db_conn.execute("PRAGMA foreign_keys").fetchone()
    assert row is not None
    assert row[0] == 1, f"Expected foreign_keys=1, got {row[0]}"


@pytest.mark.xfail(strict=False, reason="GPAG-03: assignee_path migration not yet implemented")
def test_migrate_assignee_path(tmp_path):
    import sqlite3
    from engine.db import init_schema
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    init_schema(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "assignee_path" in cols
    # Idempotency: second call must not raise
    init_schema(conn)
    cols2 = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "assignee_path" in cols2
    conn.close()


@pytest.mark.xfail(strict=False, reason="GPAG-03: due_date migration not yet implemented")
def test_migrate_due_date(tmp_path):
    import sqlite3
    from engine.db import init_schema
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    init_schema(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "due_date" in cols
    # Idempotency: second call must not raise
    init_schema(conn)
    cols2 = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "due_date" in cols2
    conn.close()


def test_action_items_archive_table_exists(db_conn):
    """32-04: action_items_archive table must exist after init_schema()."""
    from engine.db import init_schema
    init_schema(db_conn)
    tables = {r[0] for r in db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "action_items_archive" in tables


def test_action_items_archive_columns(db_conn):
    """32-04: action_items_archive must have the correct columns."""
    from engine.db import init_schema
    init_schema(db_conn)
    cols = {row[1] for row in db_conn.execute("PRAGMA table_info(action_items_archive)").fetchall()}
    expected = {"id", "note_path", "text", "done_at", "created_at", "archived_at", "archived_reason"}
    assert expected.issubset(cols), f"Missing columns: {expected - cols}"


def test_action_items_archive_idempotent(db_conn):
    """32-04: init_schema() called twice must not raise."""
    from engine.db import init_schema
    init_schema(db_conn)
    init_schema(db_conn)  # second call must not raise


def test_audit_log_index_exists(db_conn):
    """32-04: audit_log must have composite index on (created_at, note_path)."""
    from engine.db import init_schema
    init_schema(db_conn)
    indexes = {r[1] for r in db_conn.execute(
        "SELECT type, name FROM sqlite_master WHERE type='index'"
    ).fetchall()}
    assert "idx_audit_log_created_path" in indexes


# ---------------------------------------------------------------------------
# 32-01: migrate_paths_to_relative tests
# ---------------------------------------------------------------------------

class TestMigratePathsToRelative:
    """Tests for the migrate_paths_to_relative() function in engine/db.py."""

    def _insert_note(self, conn, path, title="Test Note"):
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags) VALUES (?, 'note', ?, '', '[]')",
            (path, title),
        )

    def _insert_relationship(self, conn, source_path, target_path):
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, 'link')",
            (source_path, target_path),
        )

    def _insert_action_item(self, conn, note_path):
        conn.execute(
            "INSERT INTO action_items (note_path, text) VALUES (?, 'test action')",
            (note_path,),
        )

    def _insert_embedding(self, conn, note_path):
        conn.execute(
            "INSERT OR IGNORE INTO note_embeddings (note_path, content_hash) VALUES (?, 'abc123')",
            (note_path,),
        )

    def _insert_audit_log(self, conn, note_path):
        conn.execute(
            "INSERT INTO audit_log (event_type, note_path) VALUES ('create', ?)",
            (note_path,),
        )

    def _insert_attachment(self, conn, note_path):
        conn.execute(
            "INSERT INTO attachments (note_path, file_path, filename, size) VALUES (?, '/tmp/f.jpg', 'f.jpg', 100)",
            (note_path,),
        )

    def test_absolute_paths_converted_to_relative(self, tmp_path, monkeypatch):
        """After migrate_paths_to_relative(), notes with absolute paths become relative."""
        import engine.paths as _paths
        import engine.db as _db
        from engine.db import migrate_paths_to_relative, init_schema
        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(str(tmp_path / "test.db"))
        init_schema(conn)

        abs_path = str(brain / "coding" / "note.md")
        self._insert_note(conn, abs_path)
        conn.commit()

        migrate_paths_to_relative(conn, brain)

        row = conn.execute("SELECT path FROM notes WHERE rowid=1").fetchone()
        assert row is not None
        assert not row[0].startswith("/"), f"Expected relative path, got: {row[0]}"
        assert row[0] == "coding/note.md"
        conn.close()

    def test_relative_paths_untouched(self, tmp_path, monkeypatch):
        """Already-relative paths are not modified by migration."""
        import engine.paths as _paths
        import engine.db as _db
        from engine.db import migrate_paths_to_relative, init_schema
        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(str(tmp_path / "test.db"))
        init_schema(conn)

        self._insert_note(conn, "coding/note.md")
        conn.commit()

        migrate_paths_to_relative(conn, brain)

        row = conn.execute("SELECT path FROM notes WHERE path='coding/note.md'").fetchone()
        assert row is not None, "Relative path should still exist after migration"
        conn.close()

    def test_child_tables_migrated(self, tmp_path, monkeypatch):
        """relationships, action_items, note_embeddings, audit_log, attachments all migrated."""
        import engine.paths as _paths
        import engine.db as _db
        from engine.db import migrate_paths_to_relative, init_schema
        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(str(tmp_path / "test.db"))
        init_schema(conn)

        abs_note = str(brain / "meetings" / "meeting.md")
        abs_target = str(brain / "people" / "alice.md")

        self._insert_note(conn, abs_note)
        self._insert_note(conn, abs_target, title="Alice")
        self._insert_relationship(conn, abs_note, abs_target)
        self._insert_action_item(conn, abs_note)
        self._insert_embedding(conn, abs_note)
        self._insert_audit_log(conn, abs_note)
        self._insert_attachment(conn, abs_note)
        conn.commit()

        migrate_paths_to_relative(conn, brain)

        # notes table
        row = conn.execute("SELECT path FROM notes WHERE title='Test Note' OR title='Test Note'").fetchone()
        # relationships
        rel = conn.execute("SELECT source_path, target_path FROM relationships").fetchone()
        assert rel is not None
        assert not rel[0].startswith("/"), f"relationship source_path not migrated: {rel[0]}"
        assert not rel[1].startswith("/"), f"relationship target_path not migrated: {rel[1]}"

        # action_items
        ai = conn.execute("SELECT note_path FROM action_items").fetchone()
        assert ai is not None
        assert not ai[0].startswith("/"), f"action_items.note_path not migrated: {ai[0]}"

        # note_embeddings
        emb = conn.execute("SELECT note_path FROM note_embeddings").fetchone()
        assert emb is not None
        assert not emb[0].startswith("/"), f"note_embeddings.note_path not migrated: {emb[0]}"

        # audit_log
        log = conn.execute("SELECT note_path FROM audit_log WHERE event_type='create'").fetchone()
        assert log is not None
        assert not log[0].startswith("/"), f"audit_log.note_path not migrated: {log[0]}"

        # attachments
        att = conn.execute("SELECT note_path FROM attachments").fetchone()
        assert att is not None
        assert not att[0].startswith("/"), f"attachments.note_path not migrated: {att[0]}"

        conn.close()

    def test_idempotent(self, tmp_path, monkeypatch):
        """Running migrate_paths_to_relative twice produces the same result."""
        import engine.paths as _paths
        import engine.db as _db
        from engine.db import migrate_paths_to_relative, init_schema
        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(str(tmp_path / "test.db"))
        init_schema(conn)

        abs_path = str(brain / "ideas" / "note.md")
        self._insert_note(conn, abs_path)
        conn.commit()

        migrate_paths_to_relative(conn, brain)
        conn.commit()
        migrate_paths_to_relative(conn, brain)  # second call must not raise or change anything
        conn.commit()

        rows = conn.execute("SELECT path FROM notes WHERE path LIKE '/%'").fetchall()
        assert rows == [], f"Absolute paths remain after second migration: {rows}"
        conn.close()

    def test_paths_outside_brain_root_skipped(self, tmp_path, monkeypatch):
        """Paths outside BRAIN_ROOT are skipped (not crashed) with a warning."""
        import logging
        import engine.paths as _paths
        import engine.db as _db
        from engine.db import migrate_paths_to_relative, init_schema
        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(str(tmp_path / "test.db"))
        init_schema(conn)

        # Insert a note with a path inside the brain
        abs_path = str(brain / "coding" / "good.md")
        self._insert_note(conn, abs_path, title="Good Note")
        # Insert a note with a path outside the brain
        outside_path = "/tmp/outside-brain/note.md"
        self._insert_note(conn, outside_path, title="Outside Note")
        conn.commit()

        # Should not raise
        migrate_paths_to_relative(conn, brain)

        # The inside note should be migrated
        good = conn.execute("SELECT path FROM notes WHERE title='Good Note'").fetchone()
        assert good is not None
        assert good[0] == "coding/good.md"

        # The outside note's path should remain unchanged (skipped)
        outside = conn.execute("SELECT path FROM notes WHERE title='Outside Note'").fetchone()
        assert outside is not None
        assert outside[0] == outside_path  # unchanged
        conn.close()

    def test_migration_runs_in_init_schema(self, tmp_path, monkeypatch):
        """init_schema() must call migrate_paths_to_relative() automatically."""
        import engine.paths as _paths
        import engine.db as _db
        from engine.db import init_schema
        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(str(tmp_path / "test.db"))

        # Initialize schema first, then inject an absolute path directly via SQL
        # (simulating a pre-migration DB that already has schema but absolute paths)
        init_schema(conn)
        abs_path = str(brain / "note.md")
        conn.execute("INSERT OR REPLACE INTO notes (path, title) VALUES (?, 'Test')", (abs_path,))
        conn.commit()

        # Verify the absolute path is stored
        row = conn.execute("SELECT path FROM notes WHERE title='Test'").fetchone()
        assert row is not None
        assert row[0] == abs_path, f"Setup failed: expected absolute path, got: {row[0]}"

        # Calling init_schema again (idempotent) should trigger migration
        init_schema(conn)

        row = conn.execute("SELECT path FROM notes WHERE title='Test'").fetchone()
        assert row is not None
        assert not row[0].startswith("/"), f"Expected relative path after init_schema, got: {row[0]}"
        conn.close()


# ---------------------------------------------------------------------------
# 32-03: note_tags and note_people junction table tests
# ---------------------------------------------------------------------------

class TestJunctionTables:
    """Tests for note_tags and note_people junction tables (32-03)."""

    def _insert_note(self, conn, path, tags="[]", people="[]", title="Test Note"):
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people) VALUES (?, 'note', ?, '', ?, ?)",
            (path, title, tags, people),
        )
        conn.commit()

    def test_note_tags_table_exists(self, db_conn):
        """note_tags junction table must exist after init_schema()."""
        from engine.db import init_schema
        init_schema(db_conn)
        tables = {r[0] for r in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "note_tags" in tables

    def test_note_people_table_exists(self, db_conn):
        """note_people junction table must exist after init_schema()."""
        from engine.db import init_schema
        init_schema(db_conn)
        tables = {r[0] for r in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "note_people" in tables

    def test_note_tags_columns(self, db_conn):
        """note_tags must have (note_path, tag) columns."""
        from engine.db import init_schema
        init_schema(db_conn)
        cols = {row[1] for row in db_conn.execute("PRAGMA table_info(note_tags)").fetchall()}
        assert {"note_path", "tag"}.issubset(cols)

    def test_note_people_columns(self, db_conn):
        """note_people must have (note_path, person) columns."""
        from engine.db import init_schema
        init_schema(db_conn)
        cols = {row[1] for row in db_conn.execute("PRAGMA table_info(note_people)").fetchall()}
        assert {"note_path", "person"}.issubset(cols)

    def test_note_tags_indexes_exist(self, db_conn):
        """note_tags must have indexes on (tag) and (note_path)."""
        from engine.db import init_schema
        init_schema(db_conn)
        indexes = {r[1] for r in db_conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        assert "idx_note_tags_tag" in indexes
        assert "idx_note_tags_note_path" in indexes

    def test_note_people_indexes_exist(self, db_conn):
        """note_people must have indexes on (person) and (note_path)."""
        from engine.db import init_schema
        init_schema(db_conn)
        indexes = {r[1] for r in db_conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        assert "idx_note_people_person" in indexes
        assert "idx_note_people_note_path" in indexes

    def test_migration_populates_note_tags_from_json(self, db_conn):
        """migrate_add_note_tags_table() populates note_tags from existing JSON tags column."""
        from engine.db import init_schema, migrate_add_note_tags_table
        init_schema(db_conn)
        self._insert_note(db_conn, "coding/note.md", tags='["python", "testing"]')

        # Clear any auto-populated rows, then re-run migration
        db_conn.execute("DELETE FROM note_tags")
        db_conn.commit()
        migrate_add_note_tags_table(db_conn)

        rows = db_conn.execute(
            "SELECT tag FROM note_tags WHERE note_path='coding/note.md' ORDER BY tag"
        ).fetchall()
        tags = [r[0] for r in rows]
        assert tags == ["python", "testing"], f"Expected tags populated, got: {tags}"

    def test_migration_populates_note_people_from_json(self, db_conn):
        """migrate_add_note_people_table() populates note_people from existing JSON people column."""
        from engine.db import init_schema, migrate_add_note_people_table
        init_schema(db_conn)
        self._insert_note(db_conn, "meetings/meeting.md", people='["people/alice.md", "people/bob.md"]')

        # Clear any auto-populated rows, then re-run migration
        db_conn.execute("DELETE FROM note_people")
        db_conn.commit()
        migrate_add_note_people_table(db_conn)

        rows = db_conn.execute(
            "SELECT person FROM note_people WHERE note_path='meetings/meeting.md' ORDER BY person"
        ).fetchall()
        people = [r[0] for r in rows]
        assert people == ["people/alice.md", "people/bob.md"], f"Expected people populated, got: {people}"

    def test_migration_idempotent_note_tags(self, db_conn):
        """Running migrate_add_note_tags_table() twice must not duplicate rows."""
        from engine.db import init_schema, migrate_add_note_tags_table
        init_schema(db_conn)
        self._insert_note(db_conn, "coding/note.md", tags='["python"]')

        db_conn.execute("DELETE FROM note_tags")
        db_conn.commit()
        migrate_add_note_tags_table(db_conn)
        migrate_add_note_tags_table(db_conn)  # second call must not duplicate

        count = db_conn.execute(
            "SELECT COUNT(*) FROM note_tags WHERE note_path='coding/note.md' AND tag='python'"
        ).fetchone()[0]
        assert count == 1, f"Expected 1 row, got {count} (duplicate inserted on second migration)"

    def test_migration_idempotent_note_people(self, db_conn):
        """Running migrate_add_note_people_table() twice must not duplicate rows."""
        from engine.db import init_schema, migrate_add_note_people_table
        init_schema(db_conn)
        self._insert_note(db_conn, "meetings/meeting.md", people='["people/alice.md"]')

        db_conn.execute("DELETE FROM note_people")
        db_conn.commit()
        migrate_add_note_people_table(db_conn)
        migrate_add_note_people_table(db_conn)  # second call must not duplicate

        count = db_conn.execute(
            "SELECT COUNT(*) FROM note_people WHERE note_path='meetings/meeting.md'"
        ).fetchone()[0]
        assert count == 1, f"Expected 1 row, got {count} (duplicate inserted on second migration)"

    def test_old_idx_notes_people_dropped(self, db_conn):
        """idx_notes_people (the useless JSON text index) must be dropped by migration."""
        from engine.db import init_schema, migrate_add_note_people_table
        init_schema(db_conn)
        migrate_add_note_people_table(db_conn)
        indexes = {r[1] for r in db_conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        assert "idx_notes_people" not in indexes, "idx_notes_people JSON text index should be dropped"

    def test_note_tags_in_init_schema(self, db_conn):
        """init_schema() must auto-create note_tags table."""
        from engine.db import init_schema
        init_schema(db_conn)
        tables = {r[0] for r in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "note_tags" in tables
        assert "note_people" in tables
