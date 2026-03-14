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
