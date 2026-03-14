import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


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
