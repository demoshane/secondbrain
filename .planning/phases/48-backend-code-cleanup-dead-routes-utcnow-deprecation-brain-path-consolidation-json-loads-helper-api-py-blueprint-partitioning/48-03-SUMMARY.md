---
phase: 48-backend-code-cleanup
plan: 03
status: complete
---

## What was done

Extracted all config/prefs routes from `engine/api.py` into a new Flask Blueprint in `engine/api_config.py`.

**Routes moved (14 handlers):**
- `GET/PUT /ui/prefs`
- `GET/PUT /config`
- `GET/PUT /config/action-item-markers`
- `GET/PUT /config/me`
- `GET/POST/DELETE /config/groq`
- `POST /config/groq/test`
- `GET/PUT /config/groq-settings`

**Also moved:**
- `_get_prefs_path()` helper (only used by prefs routes)
- `_config_write_lock` threading lock (only used by config write routes)

**api.py changes:**
- Added `from engine.api_config import config_bp` + `app.register_blueprint(config_bp)` after CORS setup
- Removed all extracted route handlers and helpers
- Line count: 2792 → 2552 (-240 lines)

## Verification

- `engine/api_config.py` created with `config_bp = Blueprint("config", __name__)`
- `grep -c "register_blueprint" engine/api.py` → 1
- No `@app.*"/config` or `@app.*"/ui/prefs"` remain in api.py
- `grep -c '@config_bp' engine/api_config.py` → 14
- All tests pass: `63 passed, 4 xfailed, 1 xpassed`
