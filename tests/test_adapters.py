"""Tests for engine/adapters/ — OllamaAdapter and ClaudeAdapter (AI-03, AI-10)."""
import pytest
from unittest.mock import MagicMock, patch


def test_ollama_adapter_generate():
    from engine.adapters.ollama_adapter import OllamaAdapter
    adapter = OllamaAdapter(model="llama3.2")
    mock_response = MagicMock()
    mock_response.message.content = "test response"
    with patch("ollama.Client") as MockClient:
        MockClient.return_value.chat.return_value = mock_response
        adapter._client = MockClient.return_value
        result = adapter.generate("user content", "system prompt")
    assert result == "test response"


def test_claude_adapter_generate():
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = ClaudeAdapter()
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "  response text  "
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = adapter.generate("user content", "system prompt")
    assert result == "response text"
    # Verify user content is not in the system_prompt position
    call_args = mock_run.call_args[0][0]
    assert "user content" in call_args[2]  # combined prompt arg


def test_claude_adapter_no_claude_raises():
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = ClaudeAdapter()
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="claude CLI not found"):
            adapter.generate("some content")


def test_claude_adapter_nonzero_raises():
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = ClaudeAdapter()
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error"
    with patch("subprocess.run", return_value=mock_result):
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with pytest.raises(RuntimeError):
                adapter.generate("content")


def test_system_prompt_not_in_system_field_of_subprocess(mock_subprocess_claude):
    # AI-10: user_content must not appear in system_prompt position
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = ClaudeAdapter()
    with mock_subprocess_claude as mock_run:
        adapter.generate(user_content="INJECT_MARKER", system_prompt="static system")
    call_args = mock_run.call_args[0][0]
    full_prompt = call_args[2]
    # system_prompt is first; user content follows separator
    assert "static system" in full_prompt
    assert "INJECT_MARKER" in full_prompt
    # system_prompt string itself must not contain user content
    assert full_prompt.index("static system") < full_prompt.index("INJECT_MARKER")


# ── Router / adapter selection tests ─────────────────────────────────────────

def test_get_adapter_pii_returns_ollama_adapter(tmp_config_toml):
    from engine.router import get_adapter
    from engine.adapters.ollama_adapter import OllamaAdapter
    with patch("ollama.Client"):
        adapter = get_adapter("pii", tmp_config_toml)
    assert isinstance(adapter, OllamaAdapter)


def test_get_adapter_private_returns_claude_adapter(tmp_config_toml):
    from engine.router import get_adapter
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = get_adapter("private", tmp_config_toml)
    assert isinstance(adapter, ClaudeAdapter)


def test_get_adapter_public_returns_claude_adapter(tmp_config_toml):
    from engine.router import get_adapter
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = get_adapter("public", tmp_config_toml)
    assert isinstance(adapter, ClaudeAdapter)


def test_get_adapter_unknown_sensitivity_falls_back_to_public(tmp_config_toml):
    from engine.router import get_adapter
    from engine.adapters.claude_adapter import ClaudeAdapter
    # Unknown sensitivity falls back to public_model routing
    adapter = get_adapter("classified", tmp_config_toml)
    assert isinstance(adapter, ClaudeAdapter)


def test_base_adapter_is_abstract():
    from engine.adapters.base import BaseAdapter
    import inspect
    assert inspect.isabstract(BaseAdapter)
