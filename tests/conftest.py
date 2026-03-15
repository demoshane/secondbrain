import sqlite3
import struct
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


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
    yield conn
    conn.close()


@pytest.fixture
def seeded_db(db_conn):
    """In-memory DB with schema + 1000 synthetic notes for perf tests."""
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
