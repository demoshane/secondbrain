"""ModelRouter — GDPR enforcement dispatcher (AI-03, AI-04, AI-05)."""
from pathlib import Path

from engine.adapters.claude_adapter import ClaudeAdapter
from engine.adapters.fallback_adapter import FallbackAdapter
from engine.adapters.ollama_adapter import OllamaAdapter
from engine.config_loader import load_config

ADAPTER_MAP = {
    "ollama": OllamaAdapter,
    "claude": ClaudeAdapter,
}


def _build_adapter(model_key: str, models: dict, ollama_host: str):
    """Instantiate a single adapter from its model definition."""
    model_def = models[model_key]
    adapter_cls = ADAPTER_MAP[model_def["adapter"]]
    if model_def["adapter"] == "ollama":
        return adapter_cls(model=model_def["model"], host=ollama_host)
    return adapter_cls(model=model_def.get("model", ""))


def get_adapter(sensitivity: str, config_path: Path):
    """Return configured adapter for given sensitivity level.

    Reads config.toml fresh on every call (AI-05: no restart needed).
    sensitivity: 'pii', 'private', or 'public'. Unknown values fall back to public routing.

    If routing.fallback_model is set and the primary adapter is different from the
    fallback, returns a FallbackAdapter that tries primary first.
    """
    config = load_config(config_path)
    routing = config["routing"]
    models = config["models"]
    ollama_host = config.get("ollama", {}).get("host", "http://host.docker.internal:11434")

    model_key = routing.get(f"{sensitivity}_model", routing["public_model"])
    primary = _build_adapter(model_key, models, ollama_host)

    fallback_key = routing.get("fallback_model")
    if fallback_key and fallback_key != model_key:
        fallback = _build_adapter(fallback_key, models, ollama_host)
        return FallbackAdapter(primary, fallback)

    return primary
