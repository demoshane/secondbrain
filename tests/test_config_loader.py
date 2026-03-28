"""Tests for engine/config_loader.py — COV-08."""
import pytest
from pathlib import Path
from engine.config_loader import load_config, DEFAULT_CONFIG


def test_missing_file_returns_default(tmp_path):
    """load_config returns DEFAULT_CONFIG when config file does not exist."""
    non_existent = tmp_path / "no_such_config.toml"
    result = load_config(non_existent)
    assert result == DEFAULT_CONFIG


def test_valid_toml_parsed(tmp_path):
    """load_config parses a valid TOML file and returns its contents."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_bytes(
        b'[routing]\n'
        b'pii_model = "ollama/llama3.2"\n'
        b'private_model = "claude"\n'
        b'public_model = "claude"\n'
        b'\n'
        b'[ollama]\n'
        b'host = "http://host.docker.internal:11434"\n'
    )
    result = load_config(cfg_file)
    assert result["routing"]["pii_model"] == "ollama/llama3.2"
    assert result["ollama"]["host"] == "http://host.docker.internal:11434"


def test_default_config_has_required_keys():
    """DEFAULT_CONFIG contains all critical top-level keys."""
    assert "routing" in DEFAULT_CONFIG
    assert "ollama" in DEFAULT_CONFIG
    assert "models" in DEFAULT_CONFIG
    assert "embeddings" in DEFAULT_CONFIG


def test_default_config_routing_keys():
    """DEFAULT_CONFIG routing section has pii_model, private_model, public_model."""
    routing = DEFAULT_CONFIG["routing"]
    assert "pii_model" in routing
    assert "private_model" in routing
    assert "public_model" in routing


def test_default_config_embeddings_provider():
    """DEFAULT_CONFIG embeddings section has provider and batch_size."""
    embeddings = DEFAULT_CONFIG["embeddings"]
    assert "provider" in embeddings
    assert "batch_size" in embeddings
    assert isinstance(embeddings["batch_size"], int)
