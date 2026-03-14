"""ModelRouter — GDPR enforcement dispatcher (AI-03, AI-04, AI-05)."""
from pathlib import Path

from engine.adapters.claude_adapter import ClaudeAdapter
from engine.adapters.ollama_adapter import OllamaAdapter
from engine.config_loader import load_config

ADAPTER_MAP = {
    "ollama": OllamaAdapter,
    "claude": ClaudeAdapter,
}


def get_adapter(sensitivity: str, config_path: Path):
    """Return configured adapter for given sensitivity level.

    Reads config.toml fresh on every call (AI-05: no restart needed).
    sensitivity: 'pii', 'private', or 'public'. Unknown values fall back to public routing.
    """
    config = load_config(config_path)
    routing = config["routing"]
    models = config["models"]
    ollama_host = config.get("ollama", {}).get("host", "http://host.docker.internal:11434")

    model_key = routing.get(f"{sensitivity}_model", routing["public_model"])
    model_def = models[model_key]

    adapter_cls = ADAPTER_MAP[model_def["adapter"]]
    if model_def["adapter"] == "ollama":
        return adapter_cls(model=model_def["model"], host=ollama_host)
    return adapter_cls(model=model_def.get("model", ""))
