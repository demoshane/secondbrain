"""Config loader for .meta/config.toml — AI-05: reads fresh on every call."""
import tomllib
from pathlib import Path

DEFAULT_CONFIG = {
    "routing": {
        "pii_model": "ollama/llama3.2",
        "private_model": "claude",
        "public_model": "claude",
    },
    "ollama": {
        "host": "http://host.docker.internal:11434",
    },
    "models": {
        "ollama/llama3.2": {"adapter": "ollama", "model": "llama3.2"},
        "claude": {"adapter": "claude", "model": ""},
    },
}


def load_config(config_path: Path) -> dict:
    """Load .meta/config.toml. Returns DEFAULT_CONFIG if file not found.

    Reads file fresh on every call — no caching (AI-05: no restart needed).
    """
    try:
        with open(config_path, "rb") as f:  # tomllib requires binary mode
            return tomllib.load(f)
    except FileNotFoundError:
        return DEFAULT_CONFIG
