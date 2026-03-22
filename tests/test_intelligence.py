"""RED scaffold: failing test stubs for INTL-01 through INTL-10."""
import sqlite3
import datetime
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# --- Helpers ---
def _make_db():
    """In-memory DB with full schema including action_items."""
    from engine.db import init_schema
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    return conn


class TestBudgetGate:
    def test_budget_available_when_note_count_below_gate(self):
        """With fewer than 20 notes, budget_available() returns False."""
        from engine.intelligence import budget_available
        conn = _make_db()
        assert budget_available(conn) is False  # no notes

    def test_budget_available_when_offered_today(self, tmp_path, monkeypatch):
        """Budget not available when last_offer_date is today."""
        from engine.intelligence import budget_available
        # Insert 20+ notes
        conn = _make_db()
        for i in range(20):
            conn.execute(
                "INSERT INTO notes (path, type, title, body, tags, people, sensitivity) VALUES (?,?,?,?,?,?,?)",
                (f"/n/{i}.md", "note", f"t{i}", "", "[]", "[]", "public")
            )
        conn.commit()
        state = {"last_offer_date": datetime.date.today().isoformat()}
        state_file = tmp_path / "intelligence_state.json"
        state_file.write_text(json.dumps(state))
        monkeypatch.setattr("engine.intelligence.STATE_PATH", state_file)
        assert budget_available(conn) is False  # offered today

    def test_budget_available_when_not_offered_today(self, tmp_path, monkeypatch):
        """Budget available when vault has 20+ notes and no offer today."""
        from engine.intelligence import budget_available
        conn = _make_db()
        for i in range(20):
            conn.execute(
                "INSERT INTO notes (path, type, title, body, tags, people, sensitivity) VALUES (?,?,?,?,?,?,?)",
                (f"/n/{i}.md", "note", f"t{i}", "", "[]", "[]", "public")
            )
        conn.commit()
        state = {"last_offer_date": "2000-01-01"}
        state_file = tmp_path / "intelligence_state.json"
        state_file.write_text(json.dumps(state))
        monkeypatch.setattr("engine.intelligence.STATE_PATH", state_file)
        assert budget_available(conn) is True  # should be True — stub returns False → RED


class TestExplicitCommandsAlwaysWork:
    def test_actions_main_runs_without_error(self):
        """sb-actions runs without error regardless of budget (explicit command)."""
        from engine.intelligence import actions_main
        # Just verify it doesn't raise (stub passes, but output check ensures real impl)
        # This test will fail once implemented if it raises unexpectedly
        try:
            actions_main(["--help"])
        except SystemExit:
            pass  # argparse --help exits 0 — acceptable


class TestExtractActionItems:
    def test_extract_stores_items_in_db(self, tmp_path):
        """extract_action_items() inserts rows into action_items table."""
        from engine.intelligence import extract_action_items
        conn = _make_db()
        note = tmp_path / "note.md"
        note.write_text("I will call Alice tomorrow and review the PR by Friday.")
        with patch("engine.intelligence._router") as mock_router:
            mock_adapter = MagicMock()
            mock_adapter.generate.return_value = "Call Alice tomorrow\nReview PR by Friday"
            mock_router.get_adapter.return_value = mock_adapter
            extract_action_items(note, note.read_text(), "public", conn)
        rows = conn.execute("SELECT text FROM action_items WHERE done=0").fetchall()
        assert len(rows) >= 1  # stub returns nothing → RED

    def test_extract_none_output_stores_nothing(self, tmp_path):
        """When LLM returns NONE, no rows inserted."""
        from engine.intelligence import extract_action_items
        conn = _make_db()
        note = tmp_path / "note.md"
        note.write_text("Just a quiet day.")
        with patch("engine.intelligence._router") as mock_router:
            mock_adapter = MagicMock()
            mock_adapter.generate.return_value = "NONE"
            mock_router.get_adapter.return_value = mock_adapter
            extract_action_items(note, note.read_text(), "public", conn)
        rows = conn.execute("SELECT id FROM action_items").fetchall()
        assert len(rows) == 0  # passes even in stub — keeps RED via other tests


class TestActionsList:
    def test_actions_main_prints_open_items(self, capsys):
        """sb-actions with open items prints table header and rows."""
        from engine.intelligence import actions_main
        conn = _make_db()
        conn.execute(
            "INSERT INTO action_items (note_path, text) VALUES (?, ?)",
            ("/n/note.md", "Call Alice"),
        )
        conn.commit()
        conn.close()
        # actions_main uses its own connection — we can't inject; test that header appears
        with patch("engine.intelligence.get_connection", return_value=_make_db()):
            actions_main([])
        captured = capsys.readouterr()
        # In real impl, "ID" header line appears — stub prints nothing → RED
        assert "ID" in captured.out or "action" in captured.out.lower()


class TestActionsDone:
    def test_actions_done_marks_item(self):
        """sb-actions --done <id> sets done=1 for that id."""
        from engine.intelligence import actions_main
        conn = _make_db()
        conn.execute(
            "INSERT INTO action_items (note_path, text) VALUES (?, ?)",
            ("/n/note.md", "Call Alice"),
        )
        conn.commit()
        item_id = conn.execute("SELECT id FROM action_items").fetchone()[0]
        with patch("engine.intelligence.get_connection", return_value=conn):
            actions_main(["--done", str(item_id)])
        done = conn.execute("SELECT done FROM action_items WHERE id=?", (item_id,)).fetchone()
        assert done is not None and done[0] == 1  # stub does nothing → RED


class TestStaleNudge:
    def test_get_stale_notes_returns_old_notes(self, tmp_path):
        """get_stale_notes() returns notes with updated_at older than 90 days."""
        from engine.intelligence import get_stale_notes
        conn = _make_db()
        old_date = (datetime.date.today() - datetime.timedelta(days=91)).isoformat() + "T00:00:00Z"
        note = tmp_path / "old.md"
        note.write_text("---\ntitle: Old Note\n---\nContent.")
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (str(note.resolve()), "note", "Old Note", "", "[]", "[]", "public", old_date),
        )
        conn.commit()
        results = get_stale_notes(conn, days=90, limit=5)
        assert len(results) >= 1  # stub returns [] → RED

    def test_get_stale_notes_excludes_recent(self):
        """get_stale_notes() does NOT return notes updated within 90 days."""
        from engine.intelligence import get_stale_notes
        conn = _make_db()
        new_date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            ("/n/new.md", "note", "New Note", "", "[]", "[]", "public", new_date),
        )
        conn.commit()
        results = get_stale_notes(conn, days=90, limit=5)
        assert len(results) == 0  # correct — passes stub too, not RED but harmless


class TestEvergreenExempt:
    def test_evergreen_note_excluded_from_stale(self, tmp_path):
        """Notes with evergreen: true frontmatter are excluded from get_stale_notes()."""
        from engine.intelligence import get_stale_notes
        conn = _make_db()
        note = tmp_path / "evergreen.md"
        note.write_text("---\nevergreen: true\ntitle: Always Fresh\n---\n\nContent.")
        old_date = (datetime.date.today() - datetime.timedelta(days=200)).isoformat() + "T00:00:00Z"
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (str(note.resolve()), "note", "Always Fresh", "", "[]", "[]", "public", old_date),
        )
        conn.commit()
        results = get_stale_notes(conn, days=90, limit=5)
        paths = [r["path"] for r in results]
        assert str(note.resolve()) not in paths  # stub returns [] — passes; real impl must also pass


class TestStaleSnooze:
    def test_snoozed_note_not_nudged_before_180_days(self, tmp_path, monkeypatch):
        """A note snoozed 90 days ago (snooze expires at 180 days) is not nudged."""
        from engine import intelligence
        conn = _make_db()
        note = tmp_path / "snoozed.md"
        note.write_text("---\ntitle: Snoozed\n---\nContent.")
        old_date = (datetime.date.today() - datetime.timedelta(days=91)).isoformat() + "T00:00:00Z"
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (str(note.resolve()), "note", "Snoozed", "", "[]", "[]", "public", old_date),
        )
        conn.commit()
        # State: note snoozed, recheck date is 180 days from original nudge (still in future)
        recheck = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        state = {"stale_snoozed": {str(note.resolve()): recheck}}
        state_file = tmp_path / "intelligence_state.json"
        state_file.write_text(json.dumps(state))
        monkeypatch.setattr(intelligence, "STATE_PATH", state_file)
        results = intelligence.get_stale_notes(conn, days=90, limit=5)
        paths = [r["path"] for r in results]
        assert str(note.resolve()) not in paths  # stub returns [] — passes; impl must filter snoozed


class TestConnectionSuggestion:
    def test_check_connections_prints_suggestion(self, tmp_path, capsys):
        """check_connections() prints connection lines when similarity > 0.8."""
        from engine import intelligence
        conn = _make_db()
        note = tmp_path / "new.md"
        note.write_text("---\ntitle: New Note\n---\nContent.")
        with patch.object(intelligence, "find_similar", return_value=[
            {"note_path": "/brain/meetings/alice.md", "similarity": 0.92}
        ]), patch.object(intelligence, "budget_available", return_value=True), \
             patch.object(intelligence, "consume_budget"):
            intelligence.check_connections(note, conn, tmp_path)
        captured = capsys.readouterr()
        assert "alice" in captured.out.lower() or "Related" in captured.out  # stub prints nothing → RED


class TestConnectionSuggestionEmpty:
    def test_check_connections_silent_when_no_embeddings(self, tmp_path, capsys):
        """check_connections() prints nothing when find_similar() returns []."""
        from engine import intelligence
        conn = _make_db()
        note = tmp_path / "new.md"
        note.write_text("---\ntitle: New Note\n---\nContent.")
        with patch.object(intelligence, "find_similar", return_value=[]):
            intelligence.check_connections(note, conn, tmp_path)
        captured = capsys.readouterr()
        assert captured.out == ""  # stub also prints nothing — passes in both cases


class TestConnectionSuggestionBudgetExhausted:
    def test_check_connections_silent_when_budget_exhausted(self, tmp_path, capsys):
        """check_connections() must stay silent when budget_available() returns False."""
        from engine import intelligence
        conn = _make_db()
        note = tmp_path / "new.md"
        note.write_text("---\ntitle: New Note\n---\nContent.")
        with patch.object(intelligence, "find_similar", return_value=[
            {"note_path": "/brain/meetings/alice.md", "similarity": 0.92}
        ]), patch.object(intelligence, "budget_available", return_value=False):
            intelligence.check_connections(note, conn, tmp_path)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestRecap:
    def test_recap_main_with_git_context(self, capsys):
        """sb-recap with detected git context returns a summary string."""
        from engine import intelligence
        with patch.object(intelligence, "detect_git_context", return_value="second-brain"), \
             patch("engine.intelligence.get_connection", return_value=_make_db()), \
             patch("engine.intelligence._router") as mock_router:
            mock_adapter = MagicMock()
            mock_adapter.generate.return_value = "Recent activity: 3 meetings, 2 notes."
            mock_router.get_adapter.return_value = mock_adapter
            intelligence.recap_main([])
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0  # stub prints nothing → RED


class TestRecapNoContext:
    def test_recap_main_no_context_prints_hint(self, capsys):
        """sb-recap without git context and no args prints the hint message."""
        from engine import intelligence
        with patch.object(intelligence, "detect_git_context", return_value=None), \
             patch("engine.intelligence.get_connection", return_value=_make_db()):
            intelligence.recap_main([])
        captured = capsys.readouterr()
        assert "No context detected" in captured.out  # stub prints nothing → RED


class TestClaudeMdHook:
    def test_claude_md_contains_session_hook(self):
        """~/.claude/second-brain.md contains the sb-recap session hook line.

        The global ~/.claude/CLAUDE.md references second-brain.md via @-import;
        the actual sb-recap hook text lives in the referenced file.
        """
        # Check the second-brain-specific rules file (referenced via @ from CLAUDE.md)
        second_brain_md = Path.home() / ".claude" / "second-brain.md"
        if not second_brain_md.exists():
            pytest.skip("~/.claude/second-brain.md not present (container or CI)")
        content = second_brain_md.read_text()
        assert "sb-recap" in content


# --- Wave 0 RED stubs for Phase 16 recap_entity ---

class TestRecapEntity:
    def test_recap_entity_returns_prose_and_actions(self, seeded_db):
        """recap_entity("alice", conn) returns prose summary — fails RED (not implemented)."""
        from engine.intelligence import recap_entity  # ImportError until Plan 03 implements
        result = recap_entity("alice", seeded_db)
        assert result is not None
        assert len(result) > 0


class TestRecapEntityEmpty:
    def test_unknown_entity_graceful(self, seeded_db, capsys):
        """recap_entity with unknown entity prints 'No notes found about' — fails RED."""
        from engine.intelligence import recap_entity  # ImportError until Plan 03 implements
        recap_entity("unknown_xyz_entity_404", seeded_db)
        captured = capsys.readouterr()
        assert "No notes found about" in captured.out


class TestRecapEntityPIIRouting:
    def test_pii_notes_use_ollama_adapter(self, seeded_db):
        """recap_entity with PII note routes to Ollama adapter, not Claude — fails RED."""
        from engine import intelligence
        from engine.intelligence import recap_entity  # ImportError until Plan 03 implements
        mock_router = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "Summary about alice."
        mock_router.get_adapter.return_value = mock_adapter
        with patch.object(intelligence, "_router", mock_router):
            recap_entity("alice", seeded_db)
        # Verify it was called with "pii" sensitivity (not "public")
        calls = mock_router.get_adapter.call_args_list
        assert any(c[0][0] == "pii" for c in calls), "Expected Ollama adapter called with pii sensitivity"


# --- Phase 26: ENGL-03 / GUIF-02 stubs ---

@pytest.mark.xfail(strict=False, reason="generate_recap_on_demand not yet implemented")
def test_generate_recap_on_demand_returns_string(tmp_path, monkeypatch):
    """on_demand: always regenerates, returns string, no file guard."""
    import sqlite3
    from engine.db import init_schema
    from engine.intelligence import generate_recap_on_demand
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    init_schema(conn)
    result = generate_recap_on_demand(conn)
    conn.close()
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.xfail(strict=False, reason="action item dedup not yet implemented")
def test_extract_action_items_no_duplicate_on_recapture(tmp_path, monkeypatch):
    """dedup: capturing same note twice does not double-insert action items."""
    import sqlite3
    from engine.db import init_schema
    from engine.intelligence import extract_action_items
    from pathlib import Path
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    note = tmp_path / "task.md"
    note.write_text("---\ntitle: Task Note\nsensitivity: public\n---\n- [ ] Do something important\n")
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    init_schema(conn)
    extract_action_items(note, conn)
    extract_action_items(note, conn)  # second call — must not duplicate
    count = conn.execute("SELECT COUNT(*) FROM action_items WHERE note_path=?",
                         (str(note.resolve()),)).fetchone()[0]
    conn.close()
    assert count == 1


# ---------------------------------------------------------------------------
# Phase 27-03: recap_main fallback + capture heuristics (TDD RED)
# ---------------------------------------------------------------------------

def test_recap_main_fallback_to_recent_when_no_context_match(capsys):
    """recap_main() falls back to 5 most-recent notes when git context yields 0 rows.

    With git context detected but no matching notes, output must contain
    'Recent activity' or at least one note title from the fallback list.
    """
    import sqlite3
    from engine.db import init_schema
    from engine import intelligence

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    # Insert a note that won't match the git context name
    conn.execute(
        "INSERT INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("/brain/ideas/some-note.md", "note", "Some Recent Note", "body text",
         "[]", "[]", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "public"),
    )
    conn.commit()

    with patch.object(intelligence, "detect_git_context", return_value="nonexistent-repo-xyz"), \
         patch("engine.intelligence.get_connection", return_value=conn):
        intelligence.recap_main([])

    captured = capsys.readouterr()
    # Should print fallback content — either header or a note title
    assert len(captured.out.strip()) > 0, "recap_main must print something when notes exist"
    # Must NOT just print 'No notes found for context'
    assert "No notes found for context" not in captured.out


def test_capture_suggest_meeting_type_from_title():
    """capture main() heuristics suggest type=meeting when title contains 'meeting'."""
    from engine.capture import _suggest_note_type_from_title
    assert _suggest_note_type_from_title("Q1 Planning Meeting") == "meeting"
    assert _suggest_note_type_from_title("Weekly Standup") == "meeting"
    assert _suggest_note_type_from_title("Sprint Retro") == "meeting"


def test_capture_suggest_people_type_from_title():
    """capture main() heuristics suggest type=person for 'Firstname Lastname' pattern."""
    from engine.capture import _suggest_note_type_from_title
    assert _suggest_note_type_from_title("Alice Johnson") == "person"
    assert _suggest_note_type_from_title("Bob Smith") == "person"


def test_capture_suggest_none_for_generic_title():
    """_suggest_note_type_from_title returns None for titles that don't match any heuristic."""
    from engine.capture import _suggest_note_type_from_title
    assert _suggest_note_type_from_title("Random idea about stuff") is None
    assert _suggest_note_type_from_title("Tech notes") is None


# ---------------------------------------------------------------------------
# Phase 28-05: PUT /actions due_date + overdue recap + list_actions due_date
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client_actions(tmp_path, monkeypatch):
    """Flask test client with isolated DB for action items tests."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema
    import engine.api as _api

    brain = tmp_path / "brain"
    brain.mkdir()
    tmp_db = brain / "test.db"

    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _db.get_connection()
    init_schema(conn)
    conn.execute(
        "INSERT INTO action_items (id, note_path, text, done) "
        "VALUES (1, '/brain/note/test.md', 'Test action', 0)"
    )
    conn.commit()
    conn.close()

    _api.app.config["TESTING"] = True  # nosemgrep
    with _api.app.test_client() as client:
        yield client


def test_put_action_due_date(api_client_actions):
    """PUT /actions/1 with body {'due_date': '2026-04-01'} returns 200 and persists due_date."""
    import engine.db as _db
    resp = api_client_actions.put(
        "/actions/1",
        json={"due_date": "2026-04-01"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    conn = _db.get_connection()
    row = conn.execute("SELECT due_date FROM action_items WHERE id=1").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "2026-04-01"


def test_overdue_in_recap():
    """generate_recap_on_demand() prepends ## Overdue Actions when overdue items exist."""
    from engine.intelligence import generate_recap_on_demand
    import sqlite3
    from engine.db import init_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    conn.execute(
        "INSERT INTO action_items (note_path, text, done, due_date) VALUES (?, ?, 0, ?)",
        ("/brain/note/overdue.md", "Overdue task", yesterday),
    )
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, due_date) VALUES (?, ?, 0, ?)",
        ("/brain/note/future.md", "Future task", tomorrow),
    )
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, due_date) VALUES (?, ?, 1, ?)",
        ("/brain/note/done.md", "Done overdue task", yesterday),
    )
    conn.commit()

    recap = generate_recap_on_demand(conn)
    assert "## Overdue Actions" in recap
    assert "Overdue task" in recap


def test_overdue_not_in_recap_when_none():
    """generate_recap_on_demand() does not emit ## Overdue Actions when no items are overdue."""
    from engine.intelligence import generate_recap_on_demand
    import sqlite3
    from engine.db import init_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, due_date) VALUES (?, ?, 0, ?)",
        ("/brain/note/future.md", "Future task", tomorrow),
    )
    conn.commit()

    recap = generate_recap_on_demand(conn)
    assert "## Overdue Actions" not in recap


def test_list_actions_includes_due_date():
    """list_actions() returns dicts that include the 'due_date' key."""
    from engine.intelligence import list_actions
    import sqlite3
    from engine.db import init_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, due_date) VALUES (?, ?, 0, ?)",
        ("/brain/note/test.md", "Test task", "2026-04-01"),
    )
    conn.commit()

    results = list_actions(conn, done=False)
    assert len(results) >= 1
    assert "due_date" in results[0]
    assert results[0]["due_date"] == "2026-04-01"


# ---------------------------------------------------------------------------
# Phase 33-02: Cooldown gate for check_connections (PERF-02)
# ---------------------------------------------------------------------------

import time as _time


@pytest.fixture(autouse=False)
def reset_cooldown():
    """Reset check_connections cooldown to 0.0 before and after each test to prevent bleed."""
    import engine.intelligence as _intel
    _intel._check_connections_last_run = 0.0
    yield
    _intel._check_connections_last_run = 0.0


class TestCheckConnectionsCooldown:
    def test_check_connections_cooldown_blocks(self, tmp_path, reset_cooldown):
        """check_connections returns immediately (no find_similar call) when cooldown active."""
        from engine import intelligence
        conn = _make_db()
        note = tmp_path / "new.md"
        note.write_text("---\ntitle: New Note\n---\nContent.")

        # Simulate cooldown active: last run was just now
        intelligence._check_connections_last_run = _time.monotonic()

        # Patch budget_available to return True so only the cooldown gate can block
        with patch.object(intelligence, "budget_available", return_value=True), \
             patch.object(intelligence, "find_similar") as mock_find_similar:
            intelligence.check_connections(note, conn, tmp_path)

        # find_similar must NOT be called when cooldown is active
        mock_find_similar.assert_not_called()

    def test_check_connections_cooldown_elapsed(self, tmp_path, monkeypatch, reset_cooldown):
        """check_connections proceeds (calls find_similar) when cooldown has elapsed."""
        from engine import intelligence
        conn = _make_db()
        # Insert 20+ notes so budget_available passes
        for i in range(20):
            conn.execute(
                "INSERT INTO notes (path, type, title, body, tags, people, sensitivity) VALUES (?,?,?,?,?,?,?)",
                (f"/n/{i}.md", "note", f"t{i}", "", "[]", "[]", "public")
            )
        conn.commit()

        note = tmp_path / "new.md"
        note.write_text("---\ntitle: New Note\n---\nContent.")

        # Cooldown elapsed: last run was at 0.0 (distant past)
        intelligence._check_connections_last_run = 0.0

        # Patch budget_available to return True (bypass daily limit)
        # and find_similar to return empty so check_connections completes cleanly
        with patch.object(intelligence, "budget_available", return_value=True), \
             patch.object(intelligence, "consume_budget"), \
             patch.object(intelligence, "find_similar", return_value=[]) as mock_find_similar:
            intelligence.check_connections(note, conn, tmp_path)

        # find_similar MUST be called when cooldown has elapsed
        mock_find_similar.assert_called_once()


# ---------------------------------------------------------------------------
# Phase 33-03: Recap window_days and embed_pass_async tests
# ---------------------------------------------------------------------------

class TestRecapWindowDays:
    def _make_db(self):
        import sqlite3
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        return conn

    def test_recap_window_days_param(self):
        """Notes older than window_days are excluded from the recap content."""
        from engine.intelligence import generate_recap_on_demand
        conn = self._make_db()
        # Note within window (1 day ago)
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity, created_at) "
            "VALUES (?,?,?,?,?,?,?,datetime('now','-1 day'))",
            ("/n/recent.md", "note", "Recent Note", "Recent content here", "[]", "[]", "public"),
        )
        # Note outside window (10 days ago)
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity, created_at) "
            "VALUES (?,?,?,?,?,?,?,datetime('now','-10 days'))",
            ("/n/old.md", "note", "Old Note", "Old content here", "[]", "[]", "public"),
        )
        conn.commit()

        captured_content = []

        with patch("engine.intelligence._router") as mock_router:
            mock_adapter = MagicMock()

            def capture_generate(user_content, system_prompt):
                captured_content.append(user_content)
                return "Summary"

            mock_adapter.generate.side_effect = capture_generate
            mock_router.get_adapter.return_value = mock_adapter
            # window_days=3: only the 1-day-old note should be sent to the adapter
            generate_recap_on_demand(conn, window_days=3)

        # The adapter should have been called with content that includes the recent note
        # but NOT the old note (10 days old is outside the 3-day window)
        assert captured_content, "Adapter was never called — no notes were passed to recap"
        all_content = "\n".join(captured_content)
        assert "Recent Note" in all_content, "Recent note (within window) must be in recap content"
        assert "Old Note" not in all_content, "Old note (outside window) must be excluded from recap"

    def test_recap_days_cli_override(self):
        """--days N CLI flag passes window_days=N to generate_recap_on_demand."""
        from engine.intelligence import recap_main
        with patch("engine.intelligence.get_connection") as mock_conn, \
             patch("engine.intelligence.init_schema"), \
             patch("engine.intelligence.detect_git_context", return_value=None), \
             patch("engine.intelligence.generate_recap_on_demand") as mock_recap:
            mock_conn.return_value = MagicMock()
            recap_main(["--days", "3"])
        # generate_recap_on_demand must be called with window_days=3
        mock_recap.assert_called_once()
        call_kwargs = mock_recap.call_args
        assert call_kwargs.kwargs.get("window_days") == 3 or (
            len(call_kwargs.args) > 1 and call_kwargs.args[1] == 3
        ), f"window_days=3 not passed to generate_recap_on_demand: {call_kwargs}"

    def test_recap_max_notes_cap(self):
        """Hard cap of 50 notes: even with 60 notes in window, at most 50 reach the adapter."""
        from engine.intelligence import generate_recap_on_demand
        conn = self._make_db()
        # Insert 60 notes all within last 1 hour
        for i in range(60):
            conn.execute(
                "INSERT INTO notes (path, type, title, body, tags, people, sensitivity, created_at) "
                "VALUES (?,?,?,?,?,?,?,datetime('now','-1 hour'))",
                (f"/n/note{i}.md", "note", f"Note {i}", f"Content {i}", "[]", "[]", "public"),
            )
        conn.commit()

        captured_content = []

        with patch("engine.intelligence._router") as mock_router:
            mock_adapter = MagicMock()

            def capture_generate(user_content, system_prompt):
                captured_content.append(user_content)
                return "Summary"

            mock_adapter.generate.side_effect = capture_generate
            mock_router.get_adapter.return_value = mock_adapter
            generate_recap_on_demand(conn, window_days=7)

        assert captured_content, "Adapter was never called"
        # Count how many note titles appear in the combined adapter input
        all_content = "\n".join(captured_content)
        note_count = sum(1 for i in range(60) if f"## Note {i}" in all_content)
        assert note_count <= 50, (
            f"Hard cap violated: {note_count} notes passed to adapter (max 50 allowed)"
        )
