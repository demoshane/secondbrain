"""Tests for Claude subagent files and rate limiter (AI-07, AI-08, AI-09)."""
import pytest
from pathlib import Path
import time

AGENTS_DIR = Path(".claude/agents")
COMMANDS_DIR = Path(".claude/commands")


def test_subagent_file_exists():
    assert (AGENTS_DIR / "second-brain.md").exists(), "second-brain.md not found in .claude/agents/"


def test_subagent_frontmatter_valid():
    content = (AGENTS_DIR / "second-brain.md").read_text()
    assert content.startswith("---"), "Must start with YAML frontmatter"
    parts = content.split("---", 2)
    assert len(parts) >= 3
    lines = parts[1].strip().splitlines()
    keys = {line.split(":")[0].strip() for line in lines if ":" in line}
    assert "name" in keys
    assert "description" in keys
    assert "tools" in keys


def test_slash_command_file_exists():
    assert (COMMANDS_DIR / "sb-capture.md").exists(), "sb-capture.md not found in .claude/commands/"


def test_slash_command_has_description():
    content = (COMMANDS_DIR / "sb-capture.md").read_text()
    assert "description" in content.lower() or content.startswith("---")


def test_rate_limiter_enforces_max_calls():
    from engine.ratelimit import RateLimiter
    rl = RateLimiter(max_calls=2, window_seconds=1)
    assert rl.allow() is True
    assert rl.allow() is True
    assert rl.allow() is False  # 3rd call denied within 1s window


def test_rate_limiter_resets_after_window():
    from engine.ratelimit import RateLimiter
    rl = RateLimiter(max_calls=1, window_seconds=0.1)
    assert rl.allow() is True
    assert rl.allow() is False
    time.sleep(0.15)
    assert rl.allow() is True  # window expired, call allowed again


@pytest.mark.xfail(strict=True, reason="CAP-08 not expanded yet")
def test_subagent_documents_all_commands():
    agent_file = Path(__file__).parent.parent / ".claude" / "agents" / "second-brain.md"
    content = agent_file.read_text()
    for cmd in ["sb-capture", "sb-search", "sb-forget", "sb-read", "sb-check-links"]:
        assert cmd in content, f"Command '{cmd}' not documented in second-brain.md"
