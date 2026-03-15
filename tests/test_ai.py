"""Tests for engine/ai.py — follow-up questions and memory update (AI-01, AI-10, CAP-06)."""
import pytest
from unittest.mock import MagicMock, patch


def test_followup_questions_returns_2_to_3(tmp_config_toml, mock_subprocess_claude):
    from engine.ai import ask_followup_questions
    with mock_subprocess_claude:
        questions = ask_followup_questions("meeting", "Q1 Planning", "public", tmp_config_toml)
    assert 2 <= len(questions) <= 3


def test_followup_questions_all_content_types(tmp_config_toml, mock_subprocess_claude):
    from engine.ai import ask_followup_questions, QUESTION_SYSTEM_PROMPTS
    for note_type in QUESTION_SYSTEM_PROMPTS:
        with mock_subprocess_claude:
            questions = ask_followup_questions(note_type, "Test Title", "public", tmp_config_toml)
        assert len(questions) >= 1


def test_no_user_content_in_system_prompt(tmp_config_toml):
    from engine.ai import ask_followup_questions
    captured_system = []

    def fake_generate(user_content, system_prompt=""):
        captured_system.append(system_prompt)
        return "1. Q1\n2. Q2"

    mock_adapter = MagicMock()
    mock_adapter.generate.side_effect = fake_generate
    with patch("engine.router.get_adapter", return_value=mock_adapter):
        ask_followup_questions("meeting", "SENSITIVE_TITLE", "public", tmp_config_toml)
    assert len(captured_system) == 1
    assert "SENSITIVE_TITLE" not in captured_system[0]  # AI-10


def test_ai_failure_does_not_block_questions(tmp_config_toml):
    from engine.ai import ask_followup_questions
    mock_adapter = MagicMock()
    mock_adapter.generate.side_effect = RuntimeError("Ollama unreachable")
    with patch("engine.router.get_adapter", return_value=mock_adapter):
        questions = ask_followup_questions("meeting", "Title", "public", tmp_config_toml)
    assert isinstance(questions, list)  # returns empty list, not raises


def test_cap06_memory_update_uses_write_tool(tmp_config_toml):
    from engine.ai import update_memory
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="done")
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            update_memory("people", "Alice is the CTO", tmp_config_toml)
    call_args = mock_run.call_args[0][0]
    assert "--allowedTools" in call_args
    allowed = call_args[call_args.index("--allowedTools") + 1]
    assert "Write" in allowed


def test_update_memory_routing_uses_config(tmp_config_toml):
    """AI-05: config_path is active — routing config affects adapter selected by update_memory()."""
    from engine.ai import update_memory
    with patch("engine.router.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="done")
                update_memory("people", "Alice is CTO", tmp_config_toml)
        mock_get_adapter.assert_called_once_with("public", tmp_config_toml)


def test_sb_update_memory_entry_point_registered():
    import importlib.metadata
    eps = {ep.name: ep for ep in importlib.metadata.entry_points(group="console_scripts")}
    assert "sb-update-memory" in eps, "sb-update-memory missing from [project.scripts] in pyproject.toml"


def test_update_memory_main_argparse():
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "engine.ai", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"engine.ai --help failed:\n{result.stderr}"
