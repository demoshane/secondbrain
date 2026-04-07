"""Config loader for .meta/config.toml — AI-05: reads fresh on every call."""
import tomllib
from pathlib import Path

DEFAULT_CONFIG = {
    "routing": {
        "pii_model": "ollama/llama3",
        "private_model": "claude",
        "public_model": "claude",
        "fallback_model": "ollama/llama3",
        "all_local": False,
    },
    "ollama": {
        "host": "http://localhost:11434",
    },
    "models": {
        # llama3 (8B) — new default for pii/fallback routing (D-07)
        "ollama/llama3": {"adapter": "ollama", "model": "llama3"},
        # llama3.2 kept for backward compat — existing config.toml files still resolve (Pitfall 6)
        "ollama/llama3.2": {"adapter": "ollama", "model": "llama3.2"},
        "claude": {"adapter": "claude", "model": ""},
    },
    "embeddings": {
        "provider": "ollama",
        "batch_size": 32,
    },
    "action_items": {
        "custom_markers": [],
    },
    "user": {
        "identity": "",
    },
    # Per-feature Groq routing toggles (D-03). All false by default.
    "groq": {
        "ask_brain": False,
        "followup_questions": False,
        "digest": False,
        "person_synthesis": False,
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
