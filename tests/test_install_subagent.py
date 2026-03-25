"""Tests for scripts/install_subagent.py."""
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent.parent / "scripts" / "install_subagent.py"
SUBAGENT_CONTENT = "# second-brain subagent\nThis is a test agent."


def _run(cwd: Path, home: Path | None = None) -> subprocess.CompletedProcess:
    env = None
    if home is not None:
        import os
        env = os.environ.copy()
        env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
    )


def _setup_source(cwd: Path) -> Path:
    """Create .claude/agents/second-brain.md in cwd to mimic repo root."""
    src_dir = cwd / ".claude" / "agents"
    src_dir.mkdir(parents=True)
    src = src_dir / "second-brain.md"
    src.write_text(SUBAGENT_CONTENT)
    return src


def test_install_copies_file(tmp_path):
    """Happy path: source exists, file is copied to ~/.claude/agents/."""
    home = tmp_path / "home"
    home.mkdir()
    _setup_source(tmp_path)

    result = _run(tmp_path, home=home)

    assert result.returncode == 0, result.stderr
    dst = home / ".claude" / "agents" / "second-brain.md"
    assert dst.exists(), "Destination file not created"
    assert dst.read_text() == SUBAGENT_CONTENT


def test_install_creates_target_directory(tmp_path):
    """Target ~/.claude/agents/ directory is created if it doesn't exist."""
    home = tmp_path / "home"
    home.mkdir()
    # Intentionally do NOT pre-create ~/.claude/agents/
    _setup_source(tmp_path)

    result = _run(tmp_path, home=home)

    assert result.returncode == 0, result.stderr
    assert (home / ".claude" / "agents").is_dir()


def test_install_idempotent(tmp_path):
    """Running twice does not error and file content is unchanged."""
    home = tmp_path / "home"
    home.mkdir()
    _setup_source(tmp_path)

    _run(tmp_path, home=home)
    result = _run(tmp_path, home=home)

    assert result.returncode == 0, result.stderr
    dst = home / ".claude" / "agents" / "second-brain.md"
    assert dst.read_text() == SUBAGENT_CONTENT


def test_install_missing_source(tmp_path):
    """Missing source file raises FileNotFoundError (non-zero exit)."""
    home = tmp_path / "home"
    home.mkdir()
    # Do NOT create .claude/agents/second-brain.md

    result = _run(tmp_path, home=home)

    assert result.returncode != 0
    assert "second-brain.md" in result.stderr or "FileNotFoundError" in result.stderr
