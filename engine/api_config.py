"""Flask Blueprint for configuration routes (/config/*, /ui/prefs)."""
import json
import os
import threading
from pathlib import Path as _Path

from flask import Blueprint, jsonify, request

config_bp = Blueprint("config", __name__)

_config_write_lock = threading.Lock()  # serialise all config.toml read-modify-write ops


def _get_prefs_path() -> _Path:
    """Return the prefs file path, resolved at call time to respect BRAIN_PATH changes in tests."""
    # Read at call time for test isolation (tests monkeypatch BRAIN_PATH env var after import).
    brain = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    return _Path(brain) / ".sb-gui-prefs.json"


@config_bp.get("/ui/prefs")
def get_prefs():
    p = _get_prefs_path()
    if p.exists():
        try:
            return jsonify(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jsonify({})


@config_bp.put("/ui/prefs")
def put_prefs():
    data = request.get_json(force=True) or {}
    p = _get_prefs_path()
    try:
        p.write_text(json.dumps(data), encoding="utf-8")
        return jsonify({"saved": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@config_bp.get("/config")
def get_config():
    """Return the user-editable AI routing config (narrow: routing + ollama + models)."""
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH
    cfg = load_config(CONFIG_PATH)
    return jsonify({
        "routing": cfg.get("routing", {}),
        "ollama": cfg.get("ollama", {}),
        "models": cfg.get("models", {}),
    })


@config_bp.put("/config")
def put_config():
    """Persist changes to routing.* and ollama.* in config.toml. Other sections untouched."""
    import tomli_w
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH

    data = request.get_json(force=True, silent=True) or {}
    allowed_routing_keys = {"public_model", "private_model", "pii_model", "fallback_model"}

    try:
        with _config_write_lock:
            cfg = load_config(CONFIG_PATH)

            if "routing" in data:
                for k, v in data["routing"].items():
                    if k in allowed_routing_keys:
                        cfg.setdefault("routing", {})[k] = v

            if "ollama" in data and "host" in data["ollama"]:
                cfg.setdefault("ollama", {})["host"] = data["ollama"]["host"]

            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "wb") as f:
                tomli_w.dump(cfg, f)

        return jsonify({"saved": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@config_bp.get("/config/action-item-markers")
def get_action_item_markers():
    """Return current custom action-item markers + built-in defaults."""
    from engine.config_loader import load_config
    from engine.passes.p4_actions import DEFAULT_MARKERS
    from engine.paths import CONFIG_PATH
    config = load_config(CONFIG_PATH)
    markers = config.get("action_items", {}).get("custom_markers", [])
    return jsonify({"custom_markers": markers, "defaults": DEFAULT_MARKERS})


@config_bp.put("/config/action-item-markers")
def put_action_item_markers():
    """Persist custom action-item markers to config.toml [action_items] section."""
    import tomli_w
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH
    data = request.get_json(force=True, silent=True) or {}
    markers = data.get("custom_markers", [])
    if not isinstance(markers, list):
        return jsonify({"error": "custom_markers must be a list"}), 400
    try:
        with _config_write_lock:
            cfg = load_config(CONFIG_PATH)
            cfg.setdefault("action_items", {})["custom_markers"] = markers
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "wb") as f:
                tomli_w.dump(cfg, f)
        return jsonify({"saved": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@config_bp.get("/config/me")
def get_config_me():
    """Return the configured user identity (path to person note)."""
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH
    cfg = load_config(CONFIG_PATH)
    identity = cfg.get("user", {}).get("identity", "")
    return jsonify({"identity": identity})


@config_bp.put("/config/me")
def put_config_me():
    """Persist user identity (me person path) to config.toml [user] section."""
    import tomli_w
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH
    data = request.get_json(force=True, silent=True) or {}
    identity = data.get("identity", "")
    try:
        with _config_write_lock:
            cfg = load_config(CONFIG_PATH)
            cfg.setdefault("user", {})["identity"] = identity
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "wb") as f:
                tomli_w.dump(cfg, f)
        return jsonify({"saved": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# --- Groq / AI provider config ---

@config_bp.get("/config/groq")
def get_groq_config():
    """Return whether a Groq API key is stored in the macOS Keychain."""
    import keyring as _kr
    configured = _kr.get_password("second-brain", "groq_api_key") is not None
    return jsonify({"configured": configured})


@config_bp.post("/config/groq")
def save_groq_key():
    """Save a Groq API key to the macOS Keychain."""
    import keyring as _kr
    data = request.get_json(force=True, silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key or not api_key.startswith("gsk_"):
        return jsonify({"error": "Key format invalid \u2014 Groq keys start with gsk_"}), 400
    _kr.set_password("second-brain", "groq_api_key", api_key)
    return jsonify({"ok": True})


@config_bp.delete("/config/groq")
def delete_groq_key():
    """Remove the Groq API key from the macOS Keychain (idempotent)."""
    import keyring as _kr
    try:
        _kr.delete_password("second-brain", "groq_api_key")
    except _kr.errors.PasswordDeleteError:
        pass
    return jsonify({"ok": True})


@config_bp.post("/config/groq/test")
def test_groq_connection():
    """Test the stored Groq API key by calling the models endpoint."""
    import keyring as _kr
    import httpx
    key = _kr.get_password("second-brain", "groq_api_key")
    if not key:
        return jsonify({"ok": False, "error": "No key configured"})
    try:
        resp = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return jsonify({"ok": True, "error": None})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@config_bp.get("/config/groq-settings")
def get_groq_settings():
    """Return all_local toggle and groq feature toggles from config.toml."""
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH
    cfg = load_config(CONFIG_PATH)
    return jsonify({
        "all_local": cfg.get("routing", {}).get("all_local", False),
        "groq": cfg.get("groq", {
            "ask_brain": False, "followup_questions": False,
            "digest": False, "person_synthesis": False,
        }),
    })


@config_bp.put("/config/groq-settings")
def put_groq_settings():
    """Persist all_local and groq feature toggles to config.toml."""
    import tomli_w
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH
    data = request.get_json(force=True, silent=True) or {}
    try:
        with _config_write_lock:
            cfg = load_config(CONFIG_PATH)
            if "all_local" in data:
                cfg.setdefault("routing", {})["all_local"] = bool(data["all_local"])
            allowed_groq_keys = {"ask_brain", "followup_questions", "digest", "person_synthesis"}
            if "groq" in data and isinstance(data["groq"], dict):
                groq_section = cfg.setdefault("groq", {})
                for k, v in data["groq"].items():
                    if k in allowed_groq_keys:
                        groq_section[k] = bool(v)
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "wb") as f:
                tomli_w.dump(cfg, f)
        return jsonify({"saved": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
