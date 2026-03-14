# Architecture Patterns

**Domain:** Local-first AI-augmented Personal Knowledge Management (Second Brain)
**Researched:** 2026-03-14
**Confidence:** HIGH (PROJECT.md decisions + deep training knowledge on all component technologies)

---

## Recommended Architecture

### System Overview

```
HOST MACHINE
├── ~/SecondBrain/          ← Google Drive synced, brain content
│   ├── coding/, people/, meetings/, strategy/, projects/, personal/, ideas/
│   ├── files/              ← binary attachments
│   └── .meta/              ← config.toml, templates, schemas (hidden)
├── .env.host               ← secrets, never synced
└── Docker Engine

DEVCONTAINER (second-brain repo)
├── /workspace/brain        ← bind-mount of ~/SecondBrain
├── /workspace/engine/      ← Python engine code (CLI, AI agent, watcher)
└── brain-index-data/       ← named Docker volume (SQLite lives here)

EXTERNAL SERVICES (optional, PII-gated)
├── Anthropic API           ← cloud AI (non-PII only)
└── Ollama (host or container) ← local AI (PII content)
```

### Five Component Layers

```
┌─────────────────────────────────────────────────────────┐
│  CAPTURE LAYER                                          │
│  CLI (/sb-capture, /sb-init, /sb-search, /sb-forget)   │
│  File watcher (watchdog observer)                       │
│  Git hooks (post-commit)                                │
│  Claude Code subagent interface                         │
└───────────────────┬─────────────────────────────────────┘
                    │ raw input (text, file path, git diff)
┌───────────────────▼─────────────────────────────────────┐
│  AI LAYER                                               │
│  Router (classify content type → model selector)        │
│  Local model adapter (Ollama)                           │
│  Cloud model adapter (Anthropic API)                    │
│  Prompt templates per content type                      │
└───────────────────┬─────────────────────────────────────┘
                    │ enriched note (YAML frontmatter + body)
┌───────────────────▼─────────────────────────────────────┐
│  STORAGE LAYER                                          │
│  Markdown writer (atomic: write then index)             │
│  YAML frontmatter parser/writer (python-frontmatter)   │
│  Binary parser (python-docx, python-pptx, pypdf)        │
└───────────────────┬─────────────────────────────────────┘
                    │ parsed content + metadata
┌───────────────────▼─────────────────────────────────────┐
│  INDEX LAYER                                            │
│  SQLite (FTS5 full-text, relationships, audit log)      │
│  Indexer (incremental + full reindex /sb-reindex)       │
│  Link resolver (people ↔ meetings ↔ projects)           │
└───────────────────┬─────────────────────────────────────┘
                    │ query results
┌───────────────────▼─────────────────────────────────────┐
│  SYNC LAYER (host-level, not in container)              │
│  Google Drive (brain content)                           │
│  GitHub (engine code only)                              │
│  No container involvement — Drive runs on host          │
└─────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Must NOT Do |
|-----------|---------------|-------------------|-------------|
| CLI layer | Parse user commands, route to engine functions | Storage layer, AI layer | Never touch SQLite directly — goes through Index layer |
| File watcher | Detect new/modified files in brain folder | Capture layer (same as CLI entry point) | Never write to brain folder itself |
| AI Router | Classify content type, select model, never send PII to cloud | Both Ollama adapter and Anthropic adapter | Must classify BEFORE any API call |
| Ollama adapter | Wrap local model calls, return structured responses | AI Router | Never make outbound network calls except to localhost |
| Anthropic adapter | Wrap cloud API calls, enforce PII guard | AI Router | Refuse calls if router marks content as PII |
| Markdown writer | Atomic file writes with rollback on index failure | Storage layer, Index layer | Never partial-write (use temp file + rename) |
| SQLite indexer | Maintain FTS5 index, relationship graph, audit log | Index layer only | Never sync to Drive, never contain secrets |
| Link resolver | Maintain bidirectional links (people ↔ meetings) | Index layer | Never modify markdown directly — flag for writer |

---

## Data Flow

### Primary Path: Note Capture

```
1. User runs /sb-capture "had 1:1 with Alice, she's concerned about workload"
         │
         ▼
2. CLI parses input, detects no explicit content type
         │
         ▼
3. AI Router: classify content type
   - Rule-based first (regex: names in people/ → "people" type)
   - Fallback: local Ollama classify (NEVER cloud — classification is pre-guard)
   - Result: content_type = "people", pii = True
         │
         ▼
4. AI Layer selects LOCAL model (Ollama) — PII flag enforced
   - Prompt: "Extract structured context from this note, ask clarifying questions"
   - Returns: enriched content + suggested links + questions for user
         │
         ▼
5. CLI presents AI questions to user, collects answers
         │
         ▼
6. Markdown writer:
   a. Build note: YAML frontmatter + body
   b. Write to temp file (e.g., people/alice-2026-03-14.md.tmp)
   c. Index attempt → if fails, delete temp, raise error
   d. If index succeeds: rename temp → final path (atomic)
         │
         ▼
7. SQLite indexer (within same transaction):
   a. INSERT into notes table
   b. INSERT into notes_fts (FTS5 virtual table)
   c. INSERT into relationships (alice ↔ meeting)
   d. INSERT into audit_log (created, user=tuomas)
         │
         ▼
8. Done. User sees: "Saved people/alice-2026-03-14.md"
```

### Secondary Path: File Drop (watcher)

```
1. User drops alice-growth-plan.docx into ~/SecondBrain/people/
         │
         ▼
2. watchdog Observer detects FileCreatedEvent
         │
         ▼
3. Watcher triggers same capture pipeline at step 3 above
   (binary parser extracts text first → then classification)
         │
         ▼
4. AI questions user via CLI prompt (or queues if user not present)
```

### Query Path: Search + AI Context

```
1. User runs /sb-search "Alice workload concerns"
         │
         ▼
2. SQLite FTS5: SELECT ... FROM notes_fts WHERE notes_fts MATCH 'Alice workload'
         │
         ▼
3. Link resolver: expand results with related notes (meetings, projects)
         │
         ▼
4. AI Router: is any result PII-flagged?
   YES → route to Ollama for synthesis
   NO  → route to Anthropic API for synthesis
         │
         ▼
5. AI returns: summary + suggested actions + related context
         │
         ▼
6. audit_log: accessed_at recorded for all notes surfaced
```

---

## GDPR-Safe AI Routing Architecture

### The Core Problem

Classification must happen BEFORE any API call. If you call a cloud API to classify, you've already leaked PII.

### Solution: Local-First Classification Pipeline

```
Input text
    │
    ▼
Stage 1: Deterministic rules (zero latency, zero network)
    - Path-based: files in people/ → PII=True
    - Keyword regex: person names, "growth", "HR", "salary", "1:1" → PII=True
    - Frontmatter explicit: pii: true in YAML → PII=True
    │
    ├─► PII=True → Ollama only (hard stop, no fallback to cloud)
    │
    └─► PII=False/Unknown
            │
            ▼
        Stage 2: Ollama local classify (optional, for uncertain cases)
            │
            ├─► Classifies as PII → Ollama only
            │
            └─► Non-PII confirmed → Anthropic API permitted
```

### Content Type → Model Routing Table

```toml
# .meta/config.toml
[routing]
people     = "ollama"      # GDPR: always local
personal   = "ollama"      # GDPR: always local
meetings   = "auto"        # depends on attendees present in note
strategy   = "claude"      # non-PII, full capability desired
coding     = "claude-code" # code-specific model
projects   = "claude"      # non-PII client work
ideas      = "claude"      # non-PII
files      = "auto"        # route after content extraction

[pii_keywords]
# Applied at Stage 1 before any API call
patterns = ["growth discussion", "performance review", "salary", "1:1", "personal"]
```

### GDPR Erasure Flow (`/sb-forget <person>`)

```
1. Identify all markdown files referencing person (FTS5 search + link graph)
2. Present list to user for confirmation
3. DELETE from notes WHERE person_ref = ?
4. DELETE from notes_fts WHERE id IN (deleted ids)  -- FTS5 content delete
5. DELETE from relationships WHERE source_id OR target_id in (deleted)
6. INSERT into audit_log: erasure_event, timestamp, scope
7. DELETE or redact markdown files (user choice: delete or anonymize)
8. Run /sb-reindex to verify consistency
```

**Critical:** FTS5 content tables require explicit `DELETE` + `INSERT('delete', ...)` — a simple row delete does not remove from the FTS index.

---

## DevContainer Architecture

### What Lives Where

| Resource | Location | Rationale |
|----------|----------|-----------|
| Engine code (Python) | Container `/workspace/engine/` | Code is in git, container provides consistent runtime |
| Brain content (Markdown, files) | Host `~/SecondBrain/`, bind-mounted at `/workspace/brain/` | Drive sync runs on host; container must not own these files |
| SQLite database | Named Docker volume `brain-index-data` | Persists across container rebuilds; never synced; rebuildable |
| Ollama models | Host (separate Ollama install) or sidecar container | Models are large (3-7GB); keeping on host avoids re-download on rebuild |
| Secrets | Host `.env.host`, injected at container start via `--env-file` | Never in image, never in git |
| Git hooks | Container `/workspace/engine/.git-hooks/` | Installed by bootstrap.py into host repo's `.git/hooks/` |

### DevContainer bind-mount configuration

```json
// devcontainer.json mounts section
"mounts": [
  "source=${localEnv:HOME}/SecondBrain,target=/workspace/brain,type=bind,consistency=cached",
  "source=brain-index-data,target=/workspace/index,type=volume"
]
```

**Windows caveat (MEDIUM confidence):** On Windows with Docker Desktop + WSL2, `${localEnv:HOME}` resolves to the Windows home, but the path inside WSL2 differs. A Windows-specific devcontainer override may be needed: `source=C:/Users/${localEnv:USERNAME}/SecondBrain,...`

### Container vs Host Responsibilities

```
HOST                          CONTAINER
─────────────────────         ────────────────────────────
Google Drive sync             Python engine (CLI + watcher)
Ollama daemon (optional)      SQLite + FTS5 index
File system (brain content)   AI adapters
Docker Engine                 Git hook scripts
.env.host secrets             Bootstrap / reindex scripts
                              All Python dependencies
```

### Why Ollama on Host (not sidecar)

- Models (llama3, mistral) are 3-7GB; re-downloading on every container rebuild is unacceptable
- Ollama's REST API at `http://host.docker.internal:11434` is reachable from container
- Keeps container image small and fast to rebuild
- User may already have Ollama installed
- If sidecar is preferred: add `ollama` service in `docker-compose.yml` with a named volume for models

---

## SQLite Schema Patterns

### Core Schema

```sql
-- Notes table: metadata, routing, GDPR flags
CREATE TABLE notes (
    id          TEXT PRIMARY KEY,          -- UUID v4
    path        TEXT NOT NULL UNIQUE,      -- relative to /workspace/brain
    title       TEXT NOT NULL,
    content_type TEXT NOT NULL,            -- coding/people/meetings/strategy/etc
    pii         INTEGER NOT NULL DEFAULT 0, -- 1 = never send to cloud
    created_at  TEXT NOT NULL,             -- ISO8601
    modified_at TEXT NOT NULL,
    indexed_at  TEXT,
    checksum    TEXT                       -- SHA256 of file content, for change detection
);

-- FTS5 virtual table: full-text search
CREATE VIRTUAL TABLE notes_fts USING fts5(
    title,
    body,
    tags,
    content='notes_content',              -- external content table
    content_rowid='rowid'
);

-- Content table (stores extracted text for FTS5 external content)
CREATE TABLE notes_content (
    rowid       INTEGER PRIMARY KEY,
    note_id     TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    tags        TEXT                       -- space-separated for FTS tokenizer
);

-- Relationships: bidirectional link graph
CREATE TABLE relationships (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_id   TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    rel_type    TEXT NOT NULL,             -- "mentions", "linked_to", "attendee", "related"
    created_at  TEXT NOT NULL,
    UNIQUE(source_id, target_id, rel_type)
);
CREATE INDEX idx_rel_source ON relationships(source_id);
CREATE INDEX idx_rel_target ON relationships(target_id);

-- Audit log: GDPR requirement
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,            -- "created", "accessed", "modified", "erased"
    note_id     TEXT,                     -- NULL for erasure events (note deleted)
    note_path   TEXT,                     -- preserve path even after deletion
    actor       TEXT NOT NULL DEFAULT 'system',
    detail      TEXT,                     -- JSON blob for extra context
    timestamp   TEXT NOT NULL             -- ISO8601
);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_note ON audit_log(note_id);

-- Person index: for /sb-forget lookup
CREATE TABLE people (
    id          TEXT PRIMARY KEY,         -- UUID
    canonical_name TEXT NOT NULL UNIQUE,
    aliases     TEXT,                     -- JSON array of alternate names
    note_id     TEXT REFERENCES notes(id) ON DELETE SET NULL
);
```

### FTS5 Key Patterns

```sql
-- Search with ranking
SELECT n.id, n.path, n.title, n.pii,
       snippet(notes_fts, 1, '<b>', '</b>', '...', 10) AS excerpt,
       bm25(notes_fts) AS rank
FROM notes_fts
JOIN notes n ON notes_fts.rowid = n.rowid
WHERE notes_fts MATCH 'Alice workload'
ORDER BY rank;

-- FTS5 delete (CRITICAL: must do this before deleting row, or use content table triggers)
INSERT INTO notes_fts(notes_fts, rowid, title, body, tags)
VALUES('delete', <rowid>, <old_title>, <old_body>, <old_tags>);

-- Rebuild FTS index from scratch (/sb-reindex)
INSERT INTO notes_fts(notes_fts) VALUES('rebuild');
```

### Schema Versioning

Use a `schema_version` table, not magic pragmas:

```sql
CREATE TABLE schema_version (
    version     INTEGER NOT NULL,
    applied_at  TEXT NOT NULL,
    description TEXT
);
```

Bootstrap checks version on startup, applies migrations sequentially. Simple integer versions (1, 2, 3) — no semver needed for a single-user tool.

---

## File Watcher Patterns

### Recommended: watchdog with Observer + Handler

```python
# HIGH confidence: watchdog is the de-facto standard for Python cross-platform watching
# watchdog 3.x uses OS-native APIs: inotify (Linux), FSEvents (macOS), ReadDirectoryChangesW (Windows)

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

class BrainEventHandler(FileSystemEventHandler):
    IGNORED_PATTERNS = {'.tmp', '.swp', '.DS_Store', '~', '.sb-lock'}

    def on_created(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self._queue_for_processing(event.src_path, 'created')

    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self._queue_for_processing(event.src_path, 'modified')

    def _should_process(self, path):
        return not any(path.endswith(p) for p in self.IGNORED_PATTERNS)

    def _queue_for_processing(self, path, event_type):
        # Use a queue + debounce: editors fire multiple events per save
        # Debounce window: 500ms is standard
        pass
```

### Debounce is Required

Text editors (VS Code, vim) fire 3-10 events per save (create temp, write, rename, delete temp). Without debounce, indexing runs multiple times per keystroke.

```python
# Pattern: dict of {path: scheduled_future}, cancel old, reschedule on each event
import threading

class DebouncedHandler:
    def __init__(self, delay=0.5):
        self._timers = {}
        self._delay = delay

    def trigger(self, path, fn):
        if path in self._timers:
            self._timers[path].cancel()
        t = threading.Timer(self._delay, fn, args=[path])
        self._timers[path] = t
        t.start()
```

### DevContainer Watchdog Caveat

**MEDIUM confidence:** Inside Docker on macOS/Windows, inotify events for bind-mounted volumes may not fire reliably because the host filesystem events do not propagate to the container's inotify. The watchdog `PollingObserver` is the safe fallback:

```python
from watchdog.observers.polling import PollingObserver

# Use PollingObserver when running inside Docker on macOS/Windows
# Polling interval: 2-5 seconds is acceptable for PKM use case (not real-time)
observer = PollingObserver(timeout=2)
```

Detection strategy: check if running in container (`Path('/.dockerenv').exists()`), then use `PollingObserver`; otherwise use `Observer` (native).

### Ignore Patterns

Must ignore:
- Google Drive sync files (`.gdoc`, `.gsheet`, drive conflict copies `*.~conflict*`)
- Temp files from any editor (`.swp`, `~`, `#*#`, `.tmp`)
- The `.meta/` directory (system files, not user content)
- The index volume mount point

---

## Suggested Build Order

Dependencies flow strictly from bottom to top. Each layer must be solid before the next.

```
Phase 1: Foundation (nothing works without this)
├── DevContainer setup (devcontainer.json, Dockerfile, .env.host pattern)
├── Brain folder init (/sb-init: create directory tree, .meta/config.toml)
├── SQLite schema (create tables, FTS5, relationships, audit_log)
└── bootstrap.py (verify environment, create volume, run schema migrations)

Phase 2: Storage + Index (data persistence)
├── Markdown writer (atomic write: temp → rename, YAML frontmatter)
├── Basic indexer (ingest existing markdown → SQLite)
├── /sb-reindex command (full rebuild from markdown source)
└── FTS5 search (/sb-search basic: no AI, just index query)

Phase 3: AI Layer (intelligence, after storage is solid)
├── Content classifier (rule-based + local Ollama — MUST come before any API calls)
├── AI Router (content_type → model selector, PII enforcement)
├── Ollama adapter (local model calls)
├── Anthropic adapter (cloud calls, PII guard enforced)
└── /sb-capture with AI enrichment (questions, tagging, linking suggestions)

Phase 4: Automation (capture without user typing)
├── File watcher (watchdog, PollingObserver fallback)
├── Git hook (post-commit: summarize commit → capture to coding/)
└── Claude Code subagent interface (second-brain skill)

Phase 5: GDPR + Maintenance
├── /sb-forget <person> (erasure: markdown + FTS5 + relationships + audit)
├── Audit log viewer (/sb-audit)
├── Link checker (/sb-check-links: find orphaned references)
└── Schema migration system (version table + migration runner)
```

**Rationale for this order:**
1. Foundation first: you cannot test anything without a working container + initialized brain folder
2. Storage before AI: AI enrichment writes to storage; storage must be correct before trusting AI output
3. Indexer before search: trivially required
4. Classifier before any API adapter: this is the GDPR guard; never build API adapters first
5. Watcher and hooks last: they depend on the full capture pipeline being tested interactively first
6. GDPR tooling after data exists: erasure tooling needs real data to test against

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Classify After API Call

**What:** Call cloud AI to classify content type, then decide routing.
**Why bad:** PII has already left the machine by the time you classify it.
**Instead:** Always classify with deterministic rules + local model FIRST. API call only if PII=False confirmed.

### Anti-Pattern 2: SQLite in Brain Folder (Drive-Synced)

**What:** Put `brain.db` in `~/SecondBrain/`.
**Why bad:** Drive sync + SQLite write = immediate corruption. SQLite WAL mode does not protect against Drive-level file replacement.
**Instead:** Named Docker volume `brain-index-data`. Index is always rebuildable with `/sb-reindex`.

### Anti-Pattern 3: Non-Atomic Note Writes

**What:** Write YAML frontmatter to file, then write body, then call indexer.
**Why bad:** Crash between steps leaves a partial file in the brain folder. Index and filesystem diverge.
**Instead:** Write full note to `.tmp` file, index successfully, then `os.rename()` (atomic on POSIX). On failure: delete `.tmp`, raise error, nothing committed.

### Anti-Pattern 4: FTS5 Row Delete Without Content Table Cleanup

**What:** `DELETE FROM notes WHERE id = ?` and assume FTS5 cleans up.
**Why bad:** FTS5 external content tables are not updated by cascade deletes. Full-text entries become orphaned and return stale results forever.
**Instead:** Always `INSERT INTO notes_fts(notes_fts, rowid, ...) VALUES('delete', ...)` BEFORE the parent row delete, or use `AFTER DELETE` triggers that do this automatically.

### Anti-Pattern 5: inotify-Only Watcher in Docker

**What:** Use watchdog's default `Observer` (inotify on Linux) inside a container watching a bind-mounted directory.
**Why bad:** On macOS/Windows hosts, filesystem events from the host do not propagate to the container's inotify subsystem. The watcher silently never fires.
**Instead:** Detect container environment, use `PollingObserver` as fallback.

### Anti-Pattern 6: Hardcoded Paths

**What:** `open('/home/tuomas/SecondBrain/people/alice.md')` anywhere in the codebase.
**Why bad:** Breaks on any other machine, any other user, any Windows install.
**Instead:** All paths derived from `BRAIN_ROOT` environment variable (set to `/workspace/brain` inside container). Use `pathlib.Path` throughout. Never string-concatenate paths.

---

## Scalability Considerations

This is a single-user local tool. Scalability concerns are about personal data volume, not concurrent users.

| Concern | At 1K notes | At 10K notes | At 100K notes |
|---------|-------------|--------------|---------------|
| FTS5 search latency | <1ms | <5ms | <50ms (still fine) |
| Full reindex time | <5s | <30s | ~5min (acceptable) |
| SQLite file size | ~10MB | ~100MB | ~1GB (fine on local disk) |
| Binary file parsing | negligible | ~minutes for full reindex | --limit flag for partial reindex |
| Watcher polling overhead | negligible | negligible | negligible (file count, not note count) |

SQLite FTS5 handles millions of rows without infrastructure changes. For a personal PKM, the bottleneck will always be the human adding notes, not the database.

---

## Sources

**HIGH confidence (training knowledge, well-established patterns):**
- SQLite FTS5 documentation: https://www.sqlite.org/fts5.html
- watchdog library: https://python-watchdog.readthedocs.io/
- Python `os.rename()` atomicity on POSIX: POSIX standard (rename(2) is atomic)
- GDPR Article 17 (right to erasure): https://gdpr-info.eu/art-17-gdpr/

**HIGH confidence (sourced from PROJECT.md, owner decisions):**
- Two-repo model, Drive sync on host, named Docker volume for SQLite
- Content type routing table, PII rules
- Brain folder structure
- `.env.host` secrets pattern

**MEDIUM confidence (Docker bind-mount inotify behavior — known issue, widely reported):**
- watchdog PollingObserver fallback in Docker: multiple community reports, no single authoritative doc
- Windows `${localEnv:HOME}` devcontainer behavior: flagged in PROJECT.md as needing testing

**LOW confidence (Ollama on host vs sidecar tradeoffs — opinion-based):**
- Model storage size estimates (3-7GB) based on known model sizes as of mid-2025; verify current Ollama model sizes
