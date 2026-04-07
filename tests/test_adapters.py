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
    with patch("shutil.which", return_value="/usr/local/bin/claude"), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
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
    with patch("shutil.which", return_value="/usr/local/bin/claude"), \
         mock_subprocess_claude as mock_run:
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


# ── GroqAdapter tests ──────────────────────────────────────────────────────────

class TestGroqAdapter:
    def test_generate_calls_groq_endpoint(self):
        """GroqAdapter.generate() posts to Groq API with correct URL and Bearer header."""
        from engine.adapters.groq_adapter import GroqAdapter, GROQ_API_URL, GROQ_MODEL
        adapter = GroqAdapter()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Groq answer"}}]
        }
        mock_resp.raise_for_status.return_value = None
        with patch("keyring.get_password", return_value="gsk_test_key"):
            with patch("httpx.post", return_value=mock_resp) as mock_post:
                result = adapter.generate("hello", "be helpful")
        assert result == "Groq answer"
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == GROQ_API_URL
        headers = call_kwargs[1]["headers"]
        assert headers["Authorization"] == "Bearer gsk_test_key"
        body = call_kwargs[1]["json"]
        assert body["model"] == GROQ_MODEL

    def test_generate_includes_system_prompt(self):
        """GroqAdapter.generate() includes system prompt as first message when provided."""
        from engine.adapters.groq_adapter import GroqAdapter
        adapter = GroqAdapter()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_resp.raise_for_status.return_value = None
        with patch("keyring.get_password", return_value="gsk_key"):
            with patch("httpx.post", return_value=mock_resp) as mock_post:
                adapter.generate("user msg", "sys prompt")
        messages = mock_post.call_args[1]["json"]["messages"]
        assert messages[0] == {"role": "system", "content": "sys prompt"}
        assert messages[1] == {"role": "user", "content": "user msg"}

    def test_generate_omits_system_when_empty(self):
        """GroqAdapter.generate() sends only user message when system_prompt is empty."""
        from engine.adapters.groq_adapter import GroqAdapter
        adapter = GroqAdapter()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_resp.raise_for_status.return_value = None
        with patch("keyring.get_password", return_value="gsk_key"):
            with patch("httpx.post", return_value=mock_resp) as mock_post:
                adapter.generate("user msg")
        messages = mock_post.call_args[1]["json"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_generate_raises_when_no_key(self):
        """GroqAdapter.generate() raises RuntimeError when keyring returns None."""
        from engine.adapters.groq_adapter import GroqAdapter
        adapter = GroqAdapter()
        with patch("keyring.get_password", return_value=None):
            with pytest.raises(RuntimeError, match="no API key"):
                adapter.generate("hello")

    def test_generate_raises_on_httpx_error(self):
        """GroqAdapter.generate() propagates httpx errors."""
        import httpx
        from engine.adapters.groq_adapter import GroqAdapter
        adapter = GroqAdapter()
        with patch("keyring.get_password", return_value="gsk_key"):
            with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
                with pytest.raises(httpx.ConnectError):
                    adapter.generate("hello")


# ── FallbackAdapter.used_fallback tracking tests ──────────────────────────────

class TestFallbackAdapterTracking:
    def test_used_fallback_false_after_primary_succeeds(self):
        """FallbackAdapter.used_fallback is False after primary succeeds."""
        from engine.adapters.fallback_adapter import FallbackAdapter
        primary = MagicMock()
        primary.generate.return_value = "primary response"
        fallback = MagicMock()
        adapter = FallbackAdapter(primary, fallback)
        result = adapter.generate("input")
        assert result == "primary response"
        assert adapter.used_fallback is False

    def test_used_fallback_true_after_primary_fails(self):
        """FallbackAdapter.used_fallback is True after primary fails and fallback succeeds."""
        from engine.adapters.fallback_adapter import FallbackAdapter
        primary = MagicMock()
        primary.generate.side_effect = RuntimeError("primary down")
        fallback = MagicMock()
        fallback.generate.return_value = "fallback response"
        adapter = FallbackAdapter(primary, fallback)
        result = adapter.generate("input")
        assert result == "fallback response"
        assert adapter.used_fallback is True

    def test_used_fallback_resets_on_subsequent_success(self):
        """FallbackAdapter.used_fallback resets to False when primary succeeds after a failure."""
        from engine.adapters.fallback_adapter import FallbackAdapter
        primary = MagicMock()
        fallback = MagicMock()
        adapter = FallbackAdapter(primary, fallback)
        # First call: primary fails → used_fallback = True
        primary.generate.side_effect = RuntimeError("down")
        fallback.generate.return_value = "fallback"
        adapter.generate("first")
        assert adapter.used_fallback is True
        # Second call: primary succeeds → used_fallback = False
        primary.generate.side_effect = None
        primary.generate.return_value = "primary"
        adapter.generate("second")
        assert adapter.used_fallback is False


# ── DEFAULT_CONFIG tests ──────────────────────────────────────────────────────

class TestDefaultConfig:
    def test_pii_model_uses_llama3(self):
        """DEFAULT_CONFIG routing.pii_model is ollama/llama3 (not llama3.2)."""
        from engine.config_loader import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["routing"]["pii_model"] == "ollama/llama3"

    def test_fallback_model_uses_llama3(self):
        """DEFAULT_CONFIG routing.fallback_model is ollama/llama3 (not llama3.2)."""
        from engine.config_loader import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["routing"]["fallback_model"] == "ollama/llama3"

    def test_models_contains_ollama_llama3(self):
        """DEFAULT_CONFIG models has ollama/llama3 entry with adapter=ollama and model=llama3."""
        from engine.config_loader import DEFAULT_CONFIG
        assert "ollama/llama3" in DEFAULT_CONFIG["models"]
        entry = DEFAULT_CONFIG["models"]["ollama/llama3"]
        assert entry["adapter"] == "ollama"
        assert entry["model"] == "llama3"

    def test_models_still_contains_ollama_llama3_2(self):
        """DEFAULT_CONFIG still keeps ollama/llama3.2 for backward compat with existing configs."""
        from engine.config_loader import DEFAULT_CONFIG
        assert "ollama/llama3.2" in DEFAULT_CONFIG["models"]

    def test_groq_section_present_with_all_false(self):
        """DEFAULT_CONFIG has a groq section with all feature toggles defaulting to False."""
        from engine.config_loader import DEFAULT_CONFIG
        assert "groq" in DEFAULT_CONFIG
        groq = DEFAULT_CONFIG["groq"]
        for key in ("ask_brain", "followup_questions", "digest", "person_synthesis"):
            assert groq[key] is False, f"groq.{key} should be False by default"

    def test_routing_all_local_false(self):
        """DEFAULT_CONFIG routing.all_local is False by default."""
        from engine.config_loader import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["routing"]["all_local"] is False
