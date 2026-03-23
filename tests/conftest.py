import os
import sqlite3
import struct
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# ---------------------------------------------------------------------------
# Environment detection — used to skip tests that can't run in containers
# ---------------------------------------------------------------------------
IN_DEVCONTAINER = Path("/workspace").exists() and os.environ.get("UV_PROJECT_ENVIRONMENT", "") != ""

# ---------------------------------------------------------------------------
# Module-level sentinel: set by gui_brain fixture once the GUI test DB is ready.
# Used by _restore_gui_db autouse fixture to re-anchor DB_PATH after each test
# so that other test files' function-scoped monkeypatches cannot permanently
# restore the original (real) DB_PATH mid-session.
# ---------------------------------------------------------------------------
_GUI_DB_PATH = None


# ---------------------------------------------------------------------------
# Real-brain write guard — fails loudly if any test writes to ~/SecondBrain
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _guard_real_brain():
    """Detect any .md files written to the real ~/SecondBrain during the test run.

    Snapshots mtimes before the session and diffs after.  Fails the session if
    new files appear, so regressions are caught immediately rather than silently
    polluting Drive-synced brain data.
    """
    # Check both host path and container bind-mount path
    real_brain = Path.home() / "SecondBrain"
    container_brain = Path("/workspace/brain")
    brain_dirs = [d for d in (real_brain, container_brain) if d.exists()]
    if not brain_dirs:
        yield
        return

    def _snapshot(root: Path) -> dict:
        result = {}
        try:
            for p in root.rglob("*.md"):
                # Skip hidden dirs (e.g. .meta/)
                if any(part.startswith(".") for part in p.relative_to(root).parts):
                    continue
                try:
                    result[str(p)] = p.stat().st_mtime
                except OSError:
                    pass
        except OSError:
            pass
        return result

    before = {}
    for d in brain_dirs:
        before.update(_snapshot(d))
    yield
    after = {}
    for d in brain_dirs:
        after.update(_snapshot(d))

    new_files = sorted(k for k in after if k not in before)
    modified = sorted(
        k for k in after
        if k in before and after[k] != before[k]
    )
    problems = new_files + modified
    if problems:
        msg = (
            "ISOLATION FAILURE: test suite wrote to real brain data!\n"
            + "\n".join(f"  {'NEW' if f in new_files else 'MODIFIED'}: {f}" for f in problems)
        )
        pytest.fail(msg, pytrace=False)


# ---------------------------------------------------------------------------
# GUI DB re-anchor — prevents other tests' monkeypatches from restoring the
# original DB_PATH mid-session and breaking the Flask server's data access.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _restore_gui_db():
    """Re-anchor DB_PATH to the GUI test DB before and after every test.

    Other test files use function-scoped monkeypatch fixtures that set and then
    restore engine.db.DB_PATH / engine.paths.DB_PATH.  When monkeypatch.undo()
    runs during teardown, it restores the attribute to the value it captured at
    setup time.  If monkeypatch captured the value BEFORE gui_brain ran
    (session fixture ordering is not guaranteed across files), the restore puts
    back the real ~/SecondBrain DB path, leaving the Flask server pointing at
    the wrong DB for all subsequent Playwright tests.

    This fixture runs before setup AND after teardown of every test.  It
    re-asserts the correct path after each test's teardown so that any
    monkeypatch restore is immediately overwritten.
    """
    import engine.db as _db
    import engine.paths as _paths
    if _GUI_DB_PATH is not None:
        _db.DB_PATH = _GUI_DB_PATH
        _paths.DB_PATH = _GUI_DB_PATH
    yield
    if _GUI_DB_PATH is not None:
        _db.DB_PATH = _GUI_DB_PATH
        _paths.DB_PATH = _GUI_DB_PATH


# ---------------------------------------------------------------------------
# Embedding stub — prevents sentence-transformers download in all tests
# ---------------------------------------------------------------------------

def _fake_embed_texts(texts, provider="sentence-transformers", batch_size=32):
    """Return deterministic 384-float BLOBs without any model download."""
    blob = struct.pack("384f", *[0.1] * 384)
    return [blob for _ in texts]


@pytest.fixture(autouse=True)
def stub_engine_embeddings(request):
    """Inject a lightweight engine.embeddings stub so no model is downloaded.

    Skipped for tests that need the real engine.embeddings module:
    - TestEmbedTexts and TestSerialize test the real dispatch logic and patch
      internals (_get_model, _serialize) — they must use the real module.
    - TestReindexGeneratesEmbeddings injects its own stub per-test and cleans
      up in a finally block, so we leave it alone too.

    For all other tests (test_reindex.py, etc.) we inject the stub so no
    sentence-transformers download is attempted.
    """
    # Classes/modules that need the real engine.embeddings — do not stub
    skip_classes = {"TestEmbedTexts", "TestSerialize", "TestReindexGeneratesEmbeddings"}
    cls = request.node.cls
    if cls is not None and cls.__name__ in skip_classes:
        yield
        return

    already_present = "engine.embeddings" in sys.modules
    if not already_present:
        fake_mod = types.ModuleType("engine.embeddings")
        fake_mod.embed_texts = _fake_embed_texts
        sys.modules["engine.embeddings"] = fake_mod
    yield
    # Only remove the stub we injected; leave test-injected mocks for the
    # test's own finally block to clean up.
    if not already_present:
        sys.modules.pop("engine.embeddings", None)


@pytest.fixture
def brain_root(tmp_path: Path) -> Path:
    """Temporary brain root with all 9 subdirs created."""
    root = tmp_path / "brain"
    root.mkdir()
    return root


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """In-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


@pytest.fixture
def seeded_db(db_conn):
    """In-memory DB with schema + 1000 synthetic notes for perf tests.

    Also populates note_embeddings for the first 100 notes using the stub
    embed_texts (constant 384-float BLOBs) so that semantic search tests can
    find results without downloading any model.
    """
    from engine.db import init_schema
    init_schema(db_conn)
    # migrate people column
    cols = {r[1] for r in db_conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "people" not in cols:
        db_conn.execute("ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]'")
    for i in range(1000):
        db_conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people) VALUES (?, ?, ?, ?, ?, ?)",
            (f"notes/note_{i:04d}.md", "note", f"Note {i}", f"Content about topic_{i % 50}", "[]", "[]"),
        )
    db_conn.commit()

    # Seed embeddings for the first 100 notes so semantic/hybrid tests work
    blob = struct.pack("384f", *[0.1] * 384)
    for i in range(100):
        db_conn.execute(
            "INSERT OR IGNORE INTO note_embeddings (note_path, embedding, content_hash, stale) "
            "VALUES (?, ?, ?, 0)",
            (f"notes/note_{i:04d}.md", blob, f"hash_{i}"),
        )
    db_conn.commit()

    # Seed alice PII notes so TestRecapEntity* tests can find results
    for i in range(3):
        db_conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                f"notes/alice_meeting_{i:04d}.md",
                "meeting",
                f"Meeting with Alice {i}",
                f"Discussed project status with alice. Action: follow up on item {i}.",
                "[]",
                '["alice"]',
                "pii",
            ),
        )
    db_conn.commit()
    return db_conn


@pytest.fixture
def initialized_db(db_conn):
    """In-memory DB with schema only (no notes), for capture tests."""
    from engine.db import init_schema
    init_schema(db_conn)
    cols = {r[1] for r in db_conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "people" not in cols:
        db_conn.execute("ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]'")
    db_conn.commit()
    return db_conn


# ---------------------------------------------------------------------------
# Phase 3 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_adapter():
    """MagicMock adapter whose generate() returns a canned question list."""
    adapter = MagicMock()
    adapter.generate.return_value = "1. Question one\n2. Question two\n3. Question three"
    return adapter


@pytest.fixture
def tmp_config_toml(tmp_path):
    """Temporary config.toml for router/adapter tests. Returns the Path."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[routing]\n'
        'pii_model = "ollama/llama3.2"\n'
        'private_model = "claude"\n'
        'public_model = "claude"\n'
        '\n'
        '[ollama]\n'
        'host = "http://host.docker.internal:11434"\n'
        '\n'
        '[models]\n'
        '"ollama/llama3.2" = {adapter = "ollama", model = "llama3.2"}\n'
        '"claude" = {adapter = "claude", model = ""}\n'
    )
    return cfg


@pytest.fixture
def mock_subprocess_claude():
    """Context manager that patches subprocess.run with a successful Claude response."""
    mock_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="1. Question one\n2. Question two\n3. Question three",
        stderr="",
    )
    return patch("subprocess.run", return_value=mock_result)


# ---------------------------------------------------------------------------
# Phase 24: Playwright GUI test fixtures
# ---------------------------------------------------------------------------
import os
import socket
import threading
import time
import json
import datetime


@pytest.fixture(scope="session", autouse=False)
def gui_brain(tmp_path_factory):
    """Session-scoped temp brain dir. Sets BRAIN_PATH + DB_PATH before Flask starts.

    Must be listed as dependency of live_server_url to guarantee ordering.
    autouse=False — only activates when live_server_url or test_gui.py requests it.
    """
    from pathlib import Path as _Path
    import engine.db as _db
    import engine.paths as _paths
    brain = tmp_path_factory.mktemp("gui_brain")
    for d in ["ideas", "meetings", "projects", "people", "work", "files"]:
        (brain / d).mkdir(parents=True, exist_ok=True)
    # Set BRAIN_PATH so Flask route handlers resolve correct brain dir
    os.environ["BRAIN_PATH"] = str(brain)
    # Patch DB_PATH on both engine.paths and engine.db so get_connection() uses tmp db
    tmp_db = _Path(str(brain / "index.db"))
    _paths.DB_PATH = tmp_db
    _db.DB_PATH = tmp_db
    # Patch BRAIN_ROOT so store_path() validates against the tmp brain, not ~/SecondBrain
    # (BRAIN_ROOT is computed at import time from env var — must be patched directly)
    _paths.BRAIN_ROOT = brain
    # Set module-level sentinel so _restore_gui_db can re-anchor after each test
    global _GUI_DB_PATH
    _GUI_DB_PATH = tmp_db
    # Init schema so the DB is ready before Flask starts
    from engine.db import init_schema, get_connection
    conn = get_connection()
    init_schema(conn)
    conn.close()
    # Seed a person note so People page tests have data to click
    person_file = brain / "people" / "test-person.md"
    now = datetime.datetime.utcnow().isoformat()
    person_file.write_text(
        "---\ntitle: Test Person\ntype: person\ntags: []\n---\n\n# Test Person\n\nA test person note.\n",
        encoding="utf-8",
    )
    conn2 = get_connection()
    conn2.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(person_file), "Test Person", "person", "A test person note.", "[]", now, now),
    )
    conn2.commit()
    conn2.close()
    # Seed a meeting note so Meetings page tests have data to click
    meeting_path = brain / "meetings" / "q1-kickoff.md"
    meeting_path.parent.mkdir(parents=True, exist_ok=True)
    meeting_path.write_text(
        '---\ntitle: Q1 Kickoff\ntype: meeting\npeople: ["Alice"]\n---\n# Q1 Kickoff\nNotes here.\n',
        encoding="utf-8",
    )
    conn3 = get_connection()
    conn3.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, people, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(meeting_path), "Q1 Kickoff", "meeting", "Notes here.", '["Alice"]',
         "2026-03-01 09:00:00", "2026-03-01 09:00:00"),
    )
    conn3.commit()
    conn3.close()
    # Seed a project note so Projects page tests have data to click
    project_path = brain / "projects" / "test-project.md"
    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.write_text(
        "---\ntitle: Test Project\ntype: projects\ntags: []\n---\n\n# Test Project\n\nActive development.\n",
        encoding="utf-8",
    )
    conn4 = get_connection()
    conn4.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(project_path), "Test Project", "projects", "Active development.", "[]",
         "2026-03-01 09:00:00", "2026-03-01 09:00:00"),
    )
    conn4.commit()
    conn4.close()
    # Seed a second person note — regression guard to confirm multiple people appear in People page
    people_group_path = brain / "person" / "test-group.md"
    people_group_path.parent.mkdir(parents=True, exist_ok=True)
    people_group_path.write_text(
        "---\ntitle: Test Group\ntype: person\ntags: []\n---\n\n# Test Group\n\nA second person note.\n",
        encoding="utf-8",
    )
    conn5 = get_connection()
    conn5.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(people_group_path), "Test Group", "person", "A second person note.", "[]",
         "2026-03-01 09:00:00", "2026-03-01 09:00:00"),
    )
    conn5.commit()
    conn5.close()
    # Seed a note whose body mentions "Test Person" — used to exercise right panel people badge detection
    mention_path = brain / "ideas" / "test-mention-note.md"
    mention_path.write_text(
        "---\ntitle: Test Mention Note\ntype: idea\ntags: []\n---\n\n# Test Mention Note\n\nThis note mentions Test Person in the body.\n",
        encoding="utf-8",
    )
    conn6 = get_connection()
    conn6.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(mention_path), "Test Mention Note", "idea",
         "This note mentions Test Person in the body.", "[]",
         "2026-03-01 09:00:00", "2026-03-01 09:00:00"),
    )
    conn6.commit()
    conn6.close()
    # Seed inbox test data: unassigned action item + recent untagged ideas note + empty note
    inbox_note_path = brain / "ideas" / "inbox-test-note.md"
    inbox_note_path.write_text(
        "---\ntitle: Inbox Test Note\ntype: ideas\ntags: []\n---\n\nSome content here.\n",
        encoding="utf-8",
    )
    inbox_empty_path = brain / "notes" / "inbox-empty.md"
    inbox_empty_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_empty_path.write_text(
        "---\ntitle: Empty Inbox Note\ntype: note\n---\n\n",
        encoding="utf-8",
    )
    conn7 = get_connection()
    inbox_now = datetime.datetime.utcnow().isoformat()
    conn7.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(inbox_note_path), "Inbox Test Note", "ideas", "Some content here.", None,
         inbox_now, inbox_now),
    )
    conn7.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(inbox_empty_path), "Empty Inbox Note", "note", "", None,
         inbox_now, inbox_now),
    )
    conn7.execute(
        "INSERT OR REPLACE INTO action_items (note_path, text, done, assignee_path)"
        " VALUES (?,?,?,?)",
        (str(inbox_note_path), "Inbox test action", 0, None),
    )
    conn7.commit()
    conn7.close()
    return brain


@pytest.fixture(scope="session")
def live_server_url(gui_brain):
    """Start Flask in a daemon thread; return base URL like http://127.0.0.1:PORT.

    Uses threading.Thread(daemon=True) — NOT pytest-flask live_server which has a
    documented teardown hang with playwright-pytest (github.com/microsoft/playwright-pytest/issues/187).
    gui_brain is listed as dependency to guarantee BRAIN_PATH is set before app.run().
    """
    from engine.api import app as flask_app
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    t = threading.Thread(
        target=lambda: flask_app.run(
            host="127.0.0.1", port=port, use_reloader=False, threaded=True
        ),
        daemon=True,
    )
    t.start()
    # Wait for server to accept connections
    for _ in range(20):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    return f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def base_url(live_server_url):
    """Override pytest-playwright base_url fixture to point at test server."""
    return live_server_url


@pytest.fixture(scope="session")
def seed_note_fn(gui_brain):
    """Return a callable seed_note(brain, title, body, tags=None) -> str path.

    Writes .md file to brain/ideas/ and inserts into SQLite.
    Returns absolute path string.
    """
    from engine.db import get_connection

    def seed_note(brain, title: str, body: str, tags=None):
        tags = tags or []
        slug = title.lower().replace(" ", "-").replace("/", "-")
        note_file = brain / "ideas" / f"{slug}.md"
        now = datetime.datetime.utcnow().isoformat()
        note_file.write_text(
            f"---\ntitle: {title}\ntags: {json.dumps(tags)}\ntype: idea\n---\n\n{body}\n",
            encoding="utf-8",
        )
        conn = get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (str(note_file), title, "idea", body, json.dumps(tags), now, now),
        )
        conn.commit()
        conn.close()
        return str(note_file)

    return seed_note
