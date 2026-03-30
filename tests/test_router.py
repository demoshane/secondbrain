"""Tests for engine/router.py — ModelRouter (AI-03, AI-04, AI-05, AI-06)."""
import pytest
from pathlib import Path


def test_pii_routes_to_ollama(tmp_config_toml):
    from engine.router import get_adapter
    from engine.adapters.ollama_adapter import OllamaAdapter
    adapter = get_adapter("pii", tmp_config_toml)
    assert isinstance(adapter, OllamaAdapter)


def test_public_routes_to_claude(tmp_config_toml):
    from engine.router import get_adapter
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = get_adapter("public", tmp_config_toml)
    assert isinstance(adapter, ClaudeAdapter)


def test_private_routes_to_claude(tmp_config_toml):
    from engine.router import get_adapter
    from engine.adapters.claude_adapter import ClaudeAdapter
    adapter = get_adapter("private", tmp_config_toml)
    assert isinstance(adapter, ClaudeAdapter)


def test_config_change_no_restart(tmp_path):
    from engine.router import get_adapter
    from engine.adapters.ollama_adapter import OllamaAdapter
    from engine.adapters.claude_adapter import ClaudeAdapter
    cfg = tmp_path / "config.toml"
    cfg.write_bytes(
        b'[routing]\npii_model="ollama/llama3.2"\nprivate_model="claude"\npublic_model="ollama/llama3.2"\n\n'
        b'[ollama]\nhost="http://host.docker.internal:11434"\n\n'
        b'[models]\n"ollama/llama3.2"={adapter="ollama",model="llama3.2"}\n"claude"={adapter="claude",model=""}'
    )
    adapter1 = get_adapter("public", cfg)
    assert isinstance(adapter1, OllamaAdapter)
    # Update config in-place — no restart
    cfg.write_bytes(
        b'[routing]\npii_model="ollama/llama3.2"\nprivate_model="claude"\npublic_model="claude"\n\n'
        b'[ollama]\nhost="http://host.docker.internal:11434"\n\n'
        b'[models]\n"ollama/llama3.2"={adapter="ollama",model="llama3.2"}\n"claude"={adapter="claude",model=""}'
    )
    adapter2 = get_adapter("public", cfg)
    assert isinstance(adapter2, ClaudeAdapter)


def test_pii_zero_anthropic_calls(tmp_config_toml, monkeypatch):
    from engine.router import get_adapter
    from engine.adapters.ollama_adapter import OllamaAdapter
    adapter = get_adapter("pii", tmp_config_toml)
    assert isinstance(adapter, OllamaAdapter)
    # ClaudeAdapter must not be instantiated for pii traffic
    assert not hasattr(adapter, '_subprocess_used')


# ── all_local and Groq feature routing tests ─────────────────────────────────

def _make_config(tmp_path, extra_routing="", extra_sections=""):
    """Write a minimal config.toml with optional routing/section overrides."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[routing]\n'
        'pii_model = "ollama/llama3"\n'
        'private_model = "claude"\n'
        'public_model = "claude"\n'
        'fallback_model = "ollama/llama3"\n'
        + extra_routing
        + '\n[ollama]\n'
        'host = "http://host.docker.internal:11434"\n'
        '\n[models]\n'
        '"ollama/llama3" = {adapter = "ollama", model = "llama3"}\n'
        '"ollama/llama3.2" = {adapter = "ollama", model = "llama3.2"}\n'
        '"claude" = {adapter = "claude", model = ""}\n'
        + extra_sections
    )
    return cfg


def test_all_local_true_returns_ollama(tmp_path):
    """get_adapter with all_local=true always returns OllamaAdapter regardless of sensitivity."""
    from engine.router import get_adapter
    from engine.adapters.ollama_adapter import OllamaAdapter
    cfg = _make_config(tmp_path, extra_routing='all_local = true\n')
    adapter = get_adapter("public", cfg)
    assert isinstance(adapter, OllamaAdapter)


def test_all_local_true_overrides_groq_toggle(tmp_path):
    """all_local=true takes precedence over groq.ask_brain=true (rule 1 > rule 2)."""
    from engine.router import get_adapter
    from engine.adapters.ollama_adapter import OllamaAdapter
    from unittest.mock import patch
    cfg = _make_config(
        tmp_path,
        extra_routing='all_local = true\n',
        extra_sections='\n[groq]\nask_brain = true\n',
    )
    with patch("keyring.get_password", return_value="gsk_key"):
        adapter = get_adapter("public", cfg, feature="ask_brain")
    assert isinstance(adapter, OllamaAdapter)


def test_groq_feature_enabled_with_key_returns_fallback_adapter(tmp_path):
    """groq.ask_brain=true + key present → FallbackAdapter with GroqAdapter as primary."""
    from engine.router import get_adapter
    from engine.adapters.fallback_adapter import FallbackAdapter
    from engine.adapters.groq_adapter import GroqAdapter
    from unittest.mock import patch
    cfg = _make_config(
        tmp_path,
        extra_sections='\n[groq]\nask_brain = true\n',
    )
    with patch("keyring.get_password", return_value="gsk_test_key"):
        adapter = get_adapter("public", cfg, feature="ask_brain")
    assert isinstance(adapter, FallbackAdapter)
    assert isinstance(adapter._primary, GroqAdapter)


def test_groq_feature_enabled_but_no_key_falls_through(tmp_path):
    """groq.ask_brain=true but keyring returns None → existing routing (no Groq)."""
    from engine.router import get_adapter
    from engine.adapters.groq_adapter import GroqAdapter
    from engine.adapters.fallback_adapter import FallbackAdapter
    from unittest.mock import patch
    cfg = _make_config(
        tmp_path,
        extra_sections='\n[groq]\nask_brain = true\n',
    )
    with patch("keyring.get_password", return_value=None):
        adapter = get_adapter("public", cfg, feature="ask_brain")
    # Falls through to existing routing — no Groq in the adapter chain
    if isinstance(adapter, FallbackAdapter):
        assert not isinstance(adapter._primary, GroqAdapter), "Should not use Groq when key is absent"
    else:
        assert not isinstance(adapter, GroqAdapter)


def test_groq_feature_disabled_returns_existing_routing(tmp_path):
    """groq.ask_brain=false → existing routing unchanged (no Groq even if key present)."""
    from engine.router import get_adapter
    from engine.adapters.groq_adapter import GroqAdapter
    from engine.adapters.fallback_adapter import FallbackAdapter
    from unittest.mock import patch
    cfg = _make_config(
        tmp_path,
        extra_sections='\n[groq]\nask_brain = false\n',
    )
    with patch("keyring.get_password", return_value="gsk_key"):
        adapter = get_adapter("public", cfg, feature="ask_brain")
    # Groq toggle is off — no GroqAdapter in the chain
    if isinstance(adapter, FallbackAdapter):
        assert not isinstance(adapter._primary, GroqAdapter), "Should not use Groq when toggle is off"
    else:
        assert not isinstance(adapter, GroqAdapter)


def test_pii_sensitivity_ignores_groq_toggle(tmp_path):
    """PII sensitivity always uses pii_model routing, ignoring groq toggle (D-06)."""
    from engine.router import get_adapter
    from engine.adapters.ollama_adapter import OllamaAdapter
    from unittest.mock import patch
    cfg = _make_config(
        tmp_path,
        extra_sections='\n[groq]\nask_brain = true\n',
    )
    with patch("keyring.get_password", return_value="gsk_key"):
        adapter = get_adapter("pii", cfg, feature="ask_brain")
    assert isinstance(adapter, OllamaAdapter)


def test_no_feature_param_returns_existing_routing(tmp_path):
    """get_adapter without feature param returns existing routing (backward compat — no Groq)."""
    from engine.router import get_adapter
    from engine.adapters.groq_adapter import GroqAdapter
    from engine.adapters.fallback_adapter import FallbackAdapter
    cfg = _make_config(tmp_path)
    adapter = get_adapter("public", cfg)
    # No feature param → no Groq routing, whatever existing routing returns
    if isinstance(adapter, FallbackAdapter):
        assert not isinstance(adapter._primary, GroqAdapter)
    else:
        assert not isinstance(adapter, GroqAdapter)
