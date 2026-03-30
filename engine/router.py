"""ModelRouter — GDPR enforcement dispatcher (AI-03, AI-04, AI-05)."""
from pathlib import Path

from engine.adapters.claude_adapter import ClaudeAdapter
from engine.adapters.fallback_adapter import FallbackAdapter
from engine.adapters.groq_adapter import GroqAdapter
from engine.adapters.ollama_adapter import OllamaAdapter
from engine.config_loader import load_config

ADAPTER_MAP = {
    "ollama": OllamaAdapter,
    "claude": ClaudeAdapter,
    "groq": GroqAdapter,
}


def _build_adapter(model_key: str, models: dict, ollama_host: str):
    """Instantiate a single adapter from its model definition."""
    model_def = models[model_key]
    adapter_cls = ADAPTER_MAP[model_def["adapter"]]
    if model_def["adapter"] == "ollama":
        return adapter_cls(model=model_def["model"], host=ollama_host)
    return adapter_cls(model=model_def.get("model", ""))


def get_adapter(sensitivity: str, config_path: Path, feature: str = ""):
    """Return configured adapter for given sensitivity level.

    Reads config.toml fresh on every call (AI-05: no restart needed).
    sensitivity: 'pii', 'private', or 'public'. Unknown values fall back to public routing.
    feature: optional feature name (e.g. 'ask_brain') for Groq per-feature routing (D-05).

    Routing precedence (D-04, D-05, D-06):
      Rule 1: routing.all_local=true → OllamaAdapter regardless of Groq config or toggles
      Rule 2: groq.[feature]=true AND Keychain key present → FallbackAdapter(Groq, Claude)
      Rule 3: existing sensitivity-based routing (unchanged for backward compatibility)

    PII sensitivity always follows Rule 3 (D-06): pii_model → OllamaAdapter.
    """
    config = load_config(config_path)
    routing = config["routing"]
    models = config["models"]
    ollama_host = config.get("ollama", {}).get("host", "http://host.docker.internal:11434")

    # Rule 1: all_local overrides everything — use llama3 (or llama3.2 fallback) (D-04)
    if routing.get("all_local", False):
        ollama_model_def = models.get("ollama/llama3") or models.get("ollama/llama3.2")
        if ollama_model_def:
            return OllamaAdapter(model=ollama_model_def["model"], host=ollama_host)

    # Rule 2: Groq feature toggle — only for non-PII content (D-05, D-06)
    # PII sensitivity must never reach cloud providers; skip Rule 2 for pii.
    if feature and sensitivity != "pii" and config.get("groq", {}).get(feature, False):
        import keyring as _kr
        if _kr.get_password("second-brain", "groq_api_key"):
            return FallbackAdapter(GroqAdapter(), ClaudeAdapter())

    # Rule 3: existing sensitivity-based routing (backward compatible)
    model_key = routing.get(f"{sensitivity}_model", routing["public_model"])
    primary = _build_adapter(model_key, models, ollama_host)

    fallback_key = routing.get("fallback_model")
    if fallback_key and fallback_key != model_key:
        fallback = _build_adapter(fallback_key, models, ollama_host)
        return FallbackAdapter(primary, fallback)

    return primary
