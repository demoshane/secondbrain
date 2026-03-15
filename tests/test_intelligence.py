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
        """~/.claude/CLAUDE.md contains the sb-recap session hook line."""
        claude_md = Path.home() / ".claude" / "CLAUDE.md"
        assert claude_md.exists(), "~/.claude/CLAUDE.md must exist"
        content = claude_md.read_text()
        assert "sb-recap" in content  # not yet added → RED


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
