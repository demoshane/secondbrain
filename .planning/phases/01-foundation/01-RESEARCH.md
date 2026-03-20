# Phase 1: Foundation - Research

**Researched:** 2026-03-14
**Domain:** DevContainer configuration, secret scanning, SQLite FTS5, Python CLI tooling
**Confidence:** HIGH (core decisions locked; technical details verified via official docs and WebSearch)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `remoteUser` must be `vscode` (not root) — current devcontainer.json has `root`, must be corrected
- Consistent user everywhere: Dockerfile, devcontainer.json, bind-mount targets
- `/sb-init`: validate Drive mount is active and writable BEFORE creating any folders (FOUND-05)
- `/sb-init`: report what already exists vs. what was created — not silent, not erroring
- `/sb-init`: skip SQLite schema creation if tables already exist (idempotent re-runs are safe)
- `/sb-init`: `--force` flag recreates folders (mkdir -p, no-op if exists) but preserves existing notes
- `/sb-init`: schema reinit only if `--reset-db` is passed separately (explicit, destructive operation)

### Claude's Discretion
- bootstrap.py output format and verbosity (fail-fast vs. check-all is implementation detail)
- .env.host placement and Drive exclusion method (.gdriveignore or folder placement)
- Pre-commit hook implementation (detect-secrets or custom patterns)
- /sb-init exit codes and exact output formatting

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | DevContainer runs correctly on macOS with correct `remoteUser: vscode`, gcloud bind-mount, and `.env.host` injection | Dockerfile `vscode` user creation pattern; devcontainer.json `runArgs --env-file` for .env.host injection |
| FOUND-02 | DevContainer runs correctly on Windows (Docker Desktop + WSL2) with correct `${localEnv:HOME}` path expansion | Known bug: localEnv doesn't always pick up WSL2 env vars; workaround documented |
| FOUND-03 | `/sb-init` creates full brain folder structure (9 subdirs) | `pathlib.Path.mkdir(parents=True, exist_ok=True)` pattern |
| FOUND-04 | `/sb-init` initializes SQLite schema (notes table, FTS5 index, audit log, relationships table) in named volume | FTS5 virtual table creation; named volume mount in devcontainer.json |
| FOUND-05 | `/sb-init` validates Google Drive mount is active and writable before completing | `os.access(path, os.W_OK)` + write-then-delete probe file |
| FOUND-06 | `/sb-init` generates `.vscode/settings.json` hiding binary files from VS Code explorer | `files.exclude` setting in VS Code JSON |
| FOUND-07 | `/sb-reindex` rebuilds SQLite index fully from markdown source files | Walk `/workspace/brain/**/*.md`, parse frontmatter, insert into FTS5 |
| FOUND-08 | Pre-commit git hook scans staged files for secrets | detect-secrets v1.5.0 + `.pre-commit-config.yaml` + `.secrets.baseline` |
| FOUND-09 | `.env.host` excluded from git AND Google Drive sync | `.gitignore` entry; place `.env.host` outside `~/SecondBrain/` folder (Drive has no ignore file) |
| FOUND-10 | `bootstrap.py --dev` validates environment | argparse + sequential checks returning pass/fail per check |
| FOUND-11 | Fresh install procedure works end-to-end | bootstrap.py orchestrates: Drive check → .env.host check → SQLite volume check → Python deps check |
| FOUND-12 | `pathlib.Path` used throughout engine — no hardcoded path separators | pathlib.Path API patterns |
</phase_requirements>

---

## Summary

Phase 1 is pure infrastructure: no user-facing features, no AI behavior. The repo currently contains only a devcontainer skeleton (`Dockerfile` + `devcontainer.json`) with two critical problems — `remoteUser: root` and missing brain mount, SQLite volume, and `.env.host` injection. Everything else (Python CLI scripts, pre-commit hook, .gitignore, bootstrap.py) must be created from scratch.

The two highest-risk items are the `remoteUser` migration (root → vscode requires Dockerfile changes and all bind-mount paths to be updated consistently) and the Windows `${localEnv:HOME}` expansion issue (a confirmed VS Code bug with WSL2 that needs a documented workaround or Windows-specific devcontainer override). Both blockers were identified in STATE.md and must be resolved before the phase is considered done.

Google Drive for Desktop has no `.gdriveignore` file — this is not a missing feature but a permanent product limitation. The correct strategy is to place `.env.host` outside `~/SecondBrain/` entirely (e.g., `~/.config/second-brain/.env.host`) and bind-mount it into the container from that location. The SQLite volume exclusion is handled automatically because named Docker volumes are never on the host filesystem that Drive can see.

**Primary recommendation:** Fix devcontainer first (remoteUser, mounts, env injection), then write Python CLI scripts using uv, then wire up detect-secrets. All Python code uses `pathlib.Path` exclusively — no `os.path.join`.

---

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| Python | 3.12 (already in Dockerfile) | Engine language | Already chosen; slim image exists |
| uv | latest (already in Dockerfile) | Python package/venv management | Already chosen; faster than pip |
| SQLite FTS5 | built-in (sqlite3 3.35+) | Full-text search index | Zero infrastructure; ships with Python |
| detect-secrets | 1.5.0 | Pre-commit secret scanning | Yelp/OSS; baseline model handles false positives; integrates with pre-commit framework |
| pre-commit | 3.x | Hook framework | Industry standard; manages hook versions declaratively |
| pathlib.Path | stdlib | All path handling | Mandated by FOUND-12; cross-platform |
| argparse | stdlib | CLI argument parsing | No extra dep; sufficient for bootstrap.py and sb-init |

### Supporting

| Library/Tool | Version | Purpose | When to Use |
|---|---|---|---|
| python-frontmatter | 1.x | Parse YAML frontmatter from .md files | `/sb-reindex` needs to read note metadata |
| tomllib | stdlib (3.11+) | Read `.meta/config.toml` | Config parsing in later phases; install now so it's available |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| detect-secrets | gitleaks, trufflehog | detect-secrets has baseline/audit workflow ideal for new repos; gitleaks is faster but less tunable for false positives |
| pre-commit framework | raw `.git/hooks/pre-commit` shell script | Framework manages hook versions and virtualenvs; raw script is simpler but doesn't scale |
| argparse | click, typer | argparse is zero-dep; click/typer add value in phase 2+ when UX matters |

**Installation (inside container, via uv):**
```bash
uv pip install detect-secrets pre-commit python-frontmatter
```

**Pre-commit installation (run once after clone):**
```bash
pre-commit install
detect-secrets scan > .secrets.baseline
```

---

## Architecture Patterns

### Recommended Project Structure

```
second-brain/              # Engine repo (git)
├── .devcontainer/
│   ├── Dockerfile         # Add vscode user; keep Python 3.12-slim + Node 22
│   └── devcontainer.json  # Fix remoteUser, add mounts, add runArgs for .env.host
├── .pre-commit-config.yaml
├── .secrets.baseline
├── .gitignore             # .env.host, __pycache__, *.db, .venv/
├── engine/
│   ├── __init__.py
│   ├── paths.py           # CANONICAL_BRAIN, CANONICAL_INDEX — single source of truth
│   ├── db.py              # SQLite connection, schema init, FTS5 helpers
│   ├── init_brain.py      # /sb-init logic
│   └── reindex.py         # /sb-reindex logic
├── scripts/
│   ├── bootstrap.py       # --dev validation entrypoint
│   ├── sb-init            # Thin shell wrapper → python engine/init_brain.py
│   └── sb-reindex         # Thin shell wrapper → python engine/reindex.py
└── pyproject.toml         # uv project file; declares deps; registers console_scripts
```

### Pattern 1: Non-root User in Dockerfile

**What:** Create `vscode` user (UID 1000) in Dockerfile; set as default USER; update all bind-mount targets from `/root/` to `/home/vscode/`.

**When to use:** Any devcontainer that bind-mounts host directories — root container + bind mount = host files owned by root.

```dockerfile
# Source: https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get install -y sudo \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME
```

devcontainer.json must also set:
```json
"remoteUser": "vscode"
```

### Pattern 2: Named Volume + Bind Mount in devcontainer.json

**What:** Use `mounts` array; named volume for SQLite, bind mount for brain folder and `.env.host`.

**When to use:** Any data that must persist across container rebuilds (named volume) or that lives on the host (bind mount).

```json
"mounts": [
  "source=brain-index-data,target=/workspace/brain-index,type=volume",
  "source=${localEnv:HOME}/SecondBrain,target=/workspace/brain,type=bind,consistency=cached",
  "source=${localEnv:HOME}/.config/second-brain/.env.host,target=/workspace/.env.host,type=bind,consistency=cached",
  "source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached",
  "source=${localEnv:HOME}/.config/claude,target=/home/vscode/.config/claude,type=bind,consistency=cached"
]
```

Note: `.env.host` is bind-mounted from `~/.config/second-brain/` (outside Drive sync folder) rather than from `~/SecondBrain/`.

### Pattern 3: .env.host Injection via runArgs

**What:** Inject host secrets as container environment variables using Docker's `--env-file` flag.

**When to use:** Secrets that must be available as env vars inside the container without appearing in devcontainer.json.

```json
"runArgs": ["--env-file", "${localEnv:HOME}/.config/second-brain/.env.host"]
```

**Caveat:** If the file doesn't exist, Docker fails hard. `bootstrap.py` must detect and report this clearly. Create an `.env.host.example` template in the repo.

### Pattern 4: SQLite FTS5 Schema

**What:** Notes stored in a regular table; FTS5 virtual table as search index; kept in sync via triggers.

```sql
-- Source: https://www.sqlite.org/fts5.html
CREATE TABLE IF NOT EXISTS notes (
    id       INTEGER PRIMARY KEY,
    path     TEXT UNIQUE NOT NULL,
    type     TEXT NOT NULL,
    title    TEXT,
    body     TEXT,
    tags     TEXT,   -- JSON array stored as text
    created_at  TEXT,
    updated_at  TEXT,
    sensitivity TEXT DEFAULT 'public'
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
    USING fts5(title, body, content=notes, content_rowid=id);

CREATE TABLE IF NOT EXISTS relationships (
    from_path TEXT NOT NULL,
    to_path   TEXT NOT NULL,
    rel_type  TEXT NOT NULL,
    PRIMARY KEY (from_path, to_path, rel_type)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY,
    path      TEXT NOT NULL,
    operation TEXT NOT NULL,  -- 'create' | 'read' | 'update' | 'delete'
    ts        TEXT NOT NULL   -- ISO 8601
);
```

FTS5 `content=` mode keeps the index in sync without storing content twice. Rebuild command:
```sql
INSERT INTO notes_fts(notes_fts) VALUES('rebuild');
```

### Pattern 5: paths.py — Single Source of Truth for Paths

**What:** One module that defines canonical container paths. All other modules import from here. Never hardcode `/workspace/brain` anywhere else.

```python
# engine/paths.py
from pathlib import Path

BRAIN_ROOT    = Path("/workspace/brain")
INDEX_ROOT    = Path("/workspace/brain-index")
DB_PATH       = INDEX_ROOT / "brain.db"
META_DIR      = BRAIN_ROOT / ".meta"
TEMPLATES_DIR = META_DIR / "templates"
CONFIG_FILE   = META_DIR / "config.toml"

BRAIN_SUBDIRS = [
    "coding", "people", "meetings", "strategy",
    "projects", "personal", "ideas", "files", ".meta"
]
```

### Pattern 6: bootstrap.py Check-All Pattern

**What:** Run all checks and report each one; don't fail-fast by default (gives user full picture).

```python
# scripts/bootstrap.py
import sys, argparse
from pathlib import Path

checks = []

def check(label):
    def decorator(fn):
        checks.append((label, fn))
        return fn
    return decorator

@check("Drive mount active and writable")
def check_drive():
    p = Path.home() / "SecondBrain"
    if not p.is_dir():
        return False, f"{p} not found"
    probe = p / ".sb-probe"
    try:
        probe.write_text("probe"); probe.unlink()
        return True, str(p)
    except OSError as e:
        return False, str(e)

# ... more checks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    args = ap.parse_args()
    results = [(label, fn()) for label, fn in checks]
    all_pass = all(ok for _, (ok, _) in results)
    for label, (ok, msg) in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}: {msg}")
    sys.exit(0 if all_pass else 1)
```

### Anti-Patterns to Avoid

- **Using `os.path.join` or string concatenation for paths:** Breaks on Windows. Use `pathlib.Path` / operator exclusively.
- **Hardcoding `/workspace/brain` in multiple files:** When the path changes, you get a grep hunt. Import from `engine/paths.py`.
- **Storing `.env.host` inside `~/SecondBrain/`:** Google Drive will sync it. Place it at `~/.config/second-brain/.env.host` instead.
- **Using `devcontainer.json` comments in JSON:** The existing devcontainer.json uses `//` comments, which is valid for VS Code's JSON parser (JSONC) but will break any tool that parses it as strict JSON. Keep comments only if the file stays JSONC; remove them if it needs to be machine-parseable.
- **Setting `remoteUser: root` with bind mounts:** Host files get owned by root. Always use a named non-root user.
- **Using `INSERT OR REPLACE` for idempotent schema init:** Use `CREATE TABLE IF NOT EXISTS` — no data loss risk.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Secret detection in staged files | Custom regex scanner | detect-secrets + pre-commit | Yelp's tool covers 20+ secret types including high-entropy strings; baseline model handles project-specific false positives |
| YAML frontmatter parsing | Manual regex | python-frontmatter | Handles edge cases: multi-line values, special chars, missing delimiters |
| Pre-commit hook versioning | Manual shell scripts in `.git/hooks/` | pre-commit framework | Framework pins hook versions, manages virtualenvs, shareable via `.pre-commit-config.yaml` |
| FTS5 full rebuild | Manual DELETE + re-INSERT | `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` | SQLite's built-in rebuild is atomic and correct |

**Key insight:** This phase is infrastructure plumbing. The risk is not building wrong features — it's misconfiguring security (wrong user, wrong secret exclusion) and having to redo everything when permissions break.

---

## Common Pitfalls

### Pitfall 1: Google Drive Has No .gdriveignore

**What goes wrong:** Developer creates `.gdriveignore` or similar file expecting Drive to respect it. File silently uploads to Drive anyway.

**Why it happens:** Google Drive for Desktop has no built-in file exclusion mechanism (confirmed from Google support forums as of 2025). This is a permanent product limitation.

**How to avoid:** Place `.env.host` at `~/.config/second-brain/.env.host` — completely outside the `~/SecondBrain/` Drive-synced folder. Bind-mount it from that location into the container.

**Warning signs:** Any solution that involves writing `.env.host` anywhere inside `~/SecondBrain/` is wrong.

### Pitfall 2: ${localEnv:HOME} Fails on Windows + WSL2

**What goes wrong:** On Windows with Docker Desktop (WSL2 backend), `${localEnv:HOME}` in devcontainer.json mounts may fail to expand, causing the container to start without the brain bind mount or silently mount wrong paths.

**Why it happens:** Confirmed VS Code bug (issue #6287). `localEnv` reads from the VS Code process environment, which on Windows may be the Windows environment (C:\Users\...) not the WSL2 environment (/home/...). The two have incompatible path formats for Docker.

**How to avoid:**
- Document this as a known Windows-specific step in README/bootstrap.py output
- Create `.devcontainer/devcontainer.windows.json` override that uses `${localEnv:USERPROFILE}` with WSL path translation, OR
- Use `COMPOSE_CONVERT_WINDOWS_PATHS=1` in a Docker Compose override for Windows
- At minimum: `bootstrap.py` should detect Windows host and warn explicitly

**Warning signs:** Container starts but `/workspace/brain` is empty or contains wrong content on Windows.

### Pitfall 3: remoteUser Mismatch Breaks Drive Mount Permissions

**What goes wrong:** Container runs as root; bind-mounted `~/SecondBrain/` files are owned by root on the host after any container write. Drive sync may fail or create duplicate files.

**Why it happens:** Docker bind mounts use the UID of the process writing the files. If container runs as root (UID 0) but host user is UID 1000, writes from container change file ownership on host.

**How to avoid:**
- Add `vscode` user (UID 1000) in Dockerfile
- Set `"remoteUser": "vscode"` in devcontainer.json
- Update ALL mount targets from `/root/...` to `/home/vscode/...`
- On Linux, devcontainer automatically remaps UID to match host user when using non-root remoteUser with a Dockerfile

**Warning signs:** `ls -la ~/SecondBrain/` shows files owned by `root` after container writes.

### Pitfall 4: Named Volume Lost After docker volume prune

**What goes wrong:** Developer runs `docker system prune` or `docker volume prune`; SQLite index gone; all indexed data lost.

**Why it happens:** Named volumes persist across container rebuilds but NOT across explicit prune commands or fresh machine setup.

**How to avoid:** `/sb-reindex` MUST be implemented and tested before any real data is stored. The bootstrap.py check for "SQLite volume exists" should detect an empty/missing DB and prompt the user to run `/sb-reindex`.

**Warning signs:** SQLite volume missing on a machine that never ran before, or after prune.

### Pitfall 5: --env-file Hard Fails if File Missing

**What goes wrong:** Developer clones repo; container fails to start because `~/.config/second-brain/.env.host` doesn't exist yet.

**Why it happens:** Docker's `--env-file` fails hard if the referenced file is not present at container start time.

**How to avoid:**
- Ship `.env.host.example` in the repo (committed, no real values)
- bootstrap.py detects missing `.env.host` and shows clear copy instruction
- Document in README: "Copy `.env.host.example` to `~/.config/second-brain/.env.host` before opening devcontainer"

**Warning signs:** "no such file or directory" Docker error when opening devcontainer.

### Pitfall 6: FTS5 Content= Mode Requires Manual Triggers

**What goes wrong:** Notes are inserted/updated in the `notes` table but FTS5 index is not updated because `content=` mode is external-content and does NOT auto-update.

**Why it happens:** FTS5 `content=notes` tells FTS5 to read content from the `notes` table for retrieval, but does NOT create write triggers automatically.

**How to avoid:** Create explicit SQLite triggers:
```sql
CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
END;
CREATE TRIGGER notes_au AFTER UPDATE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
```
Or use content-less mode and store all content in FTS5 itself (simpler for this phase; tradeoff: no SELECT * from notes table).

---

## Code Examples

### devcontainer.json (corrected, complete)

```jsonc
// Source: https://containers.dev/implementors/json_reference/
{
  "name": "second-brain",
  "build": {
    "dockerfile": "Dockerfile"
  },
  "features": {},
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "DavidAnson.vscode-markdownlint"
      ]
    }
  },
  "mounts": [
    "source=brain-index-data,target=/workspace/brain-index,type=volume",
    "source=${localEnv:HOME}/SecondBrain,target=/workspace/brain,type=bind,consistency=cached",
    "source=${localEnv:HOME}/.config/second-brain/.env.host,target=/workspace/.env.host,type=bind,consistency=cached",
    "source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached",
    "source=${localEnv:HOME}/.config/claude,target=/home/vscode/.config/claude,type=bind,consistency=cached"
  ],
  "runArgs": ["--env-file", "${localEnv:HOME}/.config/second-brain/.env.host"],
  "postCreateCommand": "npm install -g @anthropic-ai/claude-code && pip install uv && uv pip install -e .",
  "remoteUser": "vscode"
}
```

### Dockerfile (corrected, with vscode user)

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git sqlite3 libsqlite3-dev curl ca-certificates sudo \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME
WORKDIR /workspace
```

### .pre-commit-config.yaml

```yaml
# Source: https://github.com/Yelp/detect-secrets
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: .env.host.example
```

### SQLite schema init (Python)

```python
# engine/db.py
# Source: https://www.sqlite.org/fts5.html
import sqlite3
from engine.paths import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY,
    path        TEXT UNIQUE NOT NULL,
    type        TEXT NOT NULL,
    title       TEXT,
    body        TEXT,
    tags        TEXT,
    created_at  TEXT,
    updated_at  TEXT,
    sensitivity TEXT DEFAULT 'public'
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
    USING fts5(title, body, content=notes, content_rowid=id);

CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body)
      VALUES('delete', old.id, old.title, old.body);
END;
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body)
      VALUES('delete', old.id, old.title, old.body);
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

CREATE TABLE IF NOT EXISTS relationships (
    from_path TEXT NOT NULL,
    to_path   TEXT NOT NULL,
    rel_type  TEXT NOT NULL,
    PRIMARY KEY (from_path, to_path, rel_type)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY,
    path      TEXT NOT NULL,
    operation TEXT NOT NULL,
    ts        TEXT NOT NULL
);
"""

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_schema(conn: sqlite3.Connection, reset: bool = False) -> None:
    if reset:
        conn.executescript("""
            DROP TABLE IF EXISTS notes;
            DROP TABLE IF EXISTS notes_fts;
            DROP TABLE IF EXISTS relationships;
            DROP TABLE IF EXISTS audit_log;
        """)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
```

### /sb-init Drive mount validation

```python
# engine/init_brain.py (partial)
import os
from pathlib import Path
from engine.paths import BRAIN_ROOT, BRAIN_SUBDIRS

def validate_drive_mount(brain_root: Path) -> tuple[bool, str]:
    """Validate that the Drive-synced brain folder is mounted and writable."""
    if not brain_root.is_dir():
        return False, f"Brain root not found: {brain_root}"
    probe = brain_root / ".sb-write-probe"
    try:
        probe.write_text("probe")
        probe.unlink()
        return True, str(brain_root)
    except OSError as e:
        return False, f"Not writable: {e}"

def create_brain_structure(brain_root: Path, force: bool = False) -> dict:
    created = []
    existed = []
    for subdir in BRAIN_SUBDIRS:
        p = brain_root / subdir
        if p.exists():
            existed.append(subdir)
        else:
            p.mkdir(parents=True, exist_ok=True)
            created.append(subdir)
    return {"created": created, "existed": existed}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `git secrets` for pre-commit scanning | `detect-secrets` with baseline | ~2019 | Baseline model prevents false-positive fatigue; audit workflow |
| `pip` for Python package management | `uv` | 2023+ | 10-100x faster install; lockfile support |
| Root user in devcontainer | Non-root user (`vscode` UID 1000) | devcontainer spec best practice | Prevents host file permission corruption |
| `os.path` for path handling | `pathlib.Path` | Python 3.6+ | Cross-platform; object-oriented; no separator bugs |

**Deprecated/outdated:**
- `google-backup-and-sync`: Replaced by Google Drive for Desktop. The old app had extension-level exclusion; new app does not.
- Running devcontainer as root: Still works but causes bind mount ownership problems. Microsoft's official guidance now recommends non-root user.

---

## Open Questions

1. **Windows WSL2 path expansion workaround**
   - What we know: `${localEnv:HOME}` fails or resolves to Windows path on WSL2 (confirmed bug in vscode-remote-release #6287)
   - What's unclear: Whether the user will ever run this on Windows; if yes, exact workaround (separate devcontainer.windows.json vs COMPOSE_CONVERT_WINDOWS_PATHS)
   - Recommendation: For Phase 1, implement on macOS first. Add a TODO in bootstrap.py that explicitly prints "Windows: see README for WSL2 setup" when Windows host is detected. Defer Windows-specific devcontainer override to a separate task if/when needed.

2. **runArgs --env-file behavior when .env.host missing**
   - What we know: Docker hard-fails if `--env-file` references a missing file
   - What's unclear: Whether VS Code's devcontainer extension gives a readable error or a cryptic Docker error
   - Recommendation: Ship `.env.host.example` in the repo; make bootstrap.py check for `~/.config/second-brain/.env.host` existence BEFORE container open is attempted (i.e., bootstrap.py is run on the host, not inside the container).

3. **uv project setup format**
   - What we know: uv supports `pyproject.toml` with `[project]` and `[project.scripts]` for console_scripts
   - What's unclear: Whether `sb-init` and `sb-reindex` should be registered as console scripts or called via `python -m engine.init_brain`
   - Recommendation: Register as `console_scripts` in pyproject.toml so `uv run sb-init` works cleanly.

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (to be installed) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] — Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| FOUND-01 | devcontainer.json has remoteUser=vscode | smoke (config validation) | `python -m pytest tests/test_devcontainer.py::test_remote_user -x` | Wave 0 |
| FOUND-02 | localEnv HOME expansion documented/warned | manual | Manual — run container on macOS, verify brain mount appears | manual-only |
| FOUND-03 | /sb-init creates 9 subdirs | unit | `pytest tests/test_init_brain.py::test_creates_subdirs -x` | Wave 0 |
| FOUND-04 | SQLite schema has all 4 tables + FTS5 + triggers | unit | `pytest tests/test_db.py::test_schema_complete -x` | Wave 0 |
| FOUND-05 | /sb-init validates Drive writable before creating dirs | unit | `pytest tests/test_init_brain.py::test_drive_validation_blocks_on_unwritable -x` | Wave 0 |
| FOUND-06 | /sb-init writes .vscode/settings.json | unit | `pytest tests/test_init_brain.py::test_vscode_settings_generated -x` | Wave 0 |
| FOUND-07 | /sb-reindex walks markdown files and inserts into FTS5 | unit | `pytest tests/test_reindex.py::test_reindex_inserts_all_markdown -x` | Wave 0 |
| FOUND-08 | pre-commit hook blocks commit with mock API key | integration | `pytest tests/test_precommit.py::test_blocks_api_key -x` | Wave 0 |
| FOUND-09 | .env.host not in git status | smoke | `pytest tests/test_gitignore.py::test_env_host_ignored -x` | Wave 0 |
| FOUND-10 | bootstrap.py --dev reports PASS/FAIL per check | unit | `pytest tests/test_bootstrap.py::test_all_checks_reported -x` | Wave 0 |
| FOUND-11 | Fresh install sequence completes without error | integration (macOS) | `pytest tests/test_bootstrap.py::test_fresh_install_sequence -x` | Wave 0 |
| FOUND-12 | No hardcoded path separators in engine/ | static analysis | `pytest tests/test_paths.py::test_no_os_path_join_in_engine -x` | Wave 0 |

**Manual-only justification (FOUND-02):** Windows WSL2 path expansion requires a real Windows + Docker Desktop environment; cannot be meaningfully tested in a Python unit test.

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — package marker
- [ ] `tests/conftest.py` — shared fixtures (tmp_path brain root, in-memory SQLite connection)
- [ ] `tests/test_devcontainer.py` — parses devcontainer.json, checks remoteUser and mounts
- [ ] `tests/test_db.py` — schema init, idempotency, FTS5 triggers
- [ ] `tests/test_init_brain.py` — subdir creation, Drive validation, .vscode/settings.json
- [ ] `tests/test_reindex.py` — markdown walk, FTS5 insert
- [ ] `tests/test_precommit.py` — detect-secrets integration test
- [ ] `tests/test_gitignore.py` — .gitignore coverage check
- [ ] `tests/test_bootstrap.py` — bootstrap.py check reporting
- [ ] `tests/test_paths.py` — static analysis: no `os.path.join` or hardcoded `/workspace/brain` outside paths.py
- [ ] Framework install: `uv pip install pytest pytest-cov`

---

## Sources

### Primary (HIGH confidence)
- [VS Code: Add non-root user](https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user) — Dockerfile vscode user pattern, remoteUser UID remapping
- [containers.dev JSON reference](https://containers.dev/implementors/json_reference/) — mounts syntax, runArgs, remoteUser
- [SQLite FTS5 official docs](https://www.sqlite.org/fts5.html) — content= mode, triggers, rebuild command
- [Yelp/detect-secrets GitHub](https://github.com/Yelp/detect-secrets) — baseline workflow, pre-commit integration, v1.5.0

### Secondary (MEDIUM confidence)
- [VS Code: Environment variables in devcontainers](https://code.visualstudio.com/remote/advancedcontainers/environment-variables) — runArgs --env-file pattern (verified against official docs)
- [VS Code: Add local file mount](https://code.visualstudio.com/remote/advancedcontainers/add-local-file-mount) — bind mount syntax examples
- [Microsoft Engineering Playbook: detect-secrets](https://microsoft.github.io/code-with-engineering-playbook/CI-CD/dev-sec-ops/secrets-management/recipes/detect-secrets/) — workflow best practices

### Tertiary (LOW confidence — flag for validation)
- [VS Code issue #6287](https://github.com/microsoft/vscode-remote-release/issues/6287): localEnv doesn't work with WSL2 — single GitHub issue, no official doc; behavior may have changed in recent VS Code releases. Validate on actual Windows machine.
- Google Drive for Desktop exclusion limitation — confirmed by multiple Google Support forum threads but no official feature announcement; product may change.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Python 3.12 + uv + SQLite + detect-secrets are all confirmed in official docs or already in the Dockerfile
- Architecture: HIGH — devcontainer patterns from official VS Code docs; SQLite FTS5 from sqlite.org
- Pitfalls: MEDIUM-HIGH — remoteUser/bind mount issues from official VS Code docs (HIGH); Windows WSL2 expansion from GitHub issue (MEDIUM); Drive exclusion from community forums (MEDIUM)

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable tooling; devcontainer spec and detect-secrets move slowly)
