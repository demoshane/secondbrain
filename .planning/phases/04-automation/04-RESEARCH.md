# Phase 4: Automation - Research

**Researched:** 2026-03-14
**Domain:** File watching, git hooks, people/meetings/work features, link checking, RAG-lite retrieval
**Confidence:** HIGH (watchdog, git hooks, FTS5 patterns) / MEDIUM (RAG-lite injection pattern)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAP-04 | File watcher detects new files in `files/` and triggers AI categorization prompt with debounce | `watchdog` Observer + `threading.Timer` debounce + existing `RateLimiter`; `engine/watcher.py` daemon process |
| CAP-05 | Git commit hook fires in project dirs; AI summarizes commit and offers to link it to a brain entry | `.githooks/post-commit` shell wrapper → `engine/hooks/post_commit.py`; `git log -1 --stat HEAD` + `git diff HEAD~1 HEAD` for diff; ClaudeAdapter for summary |
| PEOPLE-01 | `brain/people/<name>.md` profile created via `/sb-capture --type people` | Already works via existing `capture_note()` — needs people-specific template in `.meta/templates/people.md` with role/notes/growth fields |
| PEOPLE-02 | Meeting notes captured to `brain/meetings/` with attendees list referencing `people/` entries | Already works via `--type meeting --people "Alice,Bob"` — needs meeting template with attendees section; `people` frontmatter field already stored |
| PEOPLE-03 | Meeting note creation auto-updates each attendee's profile with a backlink | `engine/links.py` — reads `people` frontmatter on new meeting note; appends backlink line to each person's `.md`; updates `relationships` table |
| PEOPLE-04 | `/sb-check-links` validates all people↔meetings↔projects bidirectional links and reports orphans | `engine/links.py` `check_links()` — queries `relationships` table + scans markdown files for missing reciprocal entries; `sb-check-links` CLI entry point |
| PEOPLE-05 | `/sb-search --type people <name>` returns all notes, meetings, and projects referencing that person | Already works via existing `search_notes(conn, name, note_type="people")` — `--type people` filter is implemented; cross-type search needs union query or no-filter search |
| WORK-01 | `brain/strategy/` supports OKR notes with structured template | Template file `.meta/templates/strategy.md` with objective/key-results/status/linked-initiatives sections; no new engine code needed |
| WORK-02 | `brain/projects/` supports client/account notes with client name, key contacts, status, meeting history | Template file `.meta/templates/projects.md`; `--type projects` already a valid brain subdir |
| WORK-03 | `brain/coding/` supports ADR and project notes with GitHub repo links | Template file `.meta/templates/coding.md` with ADR sections; `--type coding` already supported |
| WORK-04 | `brain/ideas/` — on capture AI asks 2-3 elaboration questions | Already works via existing `ask_followup_questions()` in Phase 3 — `ideas` system prompt is defined; needs `idea` added as a valid `--type` if not already, and template |
| SEARCH-03 | `/sb-check-links` reports all orphaned bidirectional links | `engine/links.py` `check_links()` — see PEOPLE-04 above; standalone CLI `sb-check-links` |
| SEARCH-04 | AI queries automatically retrieve relevant notes via FTS5 as context before generating responses (RAG-lite) | `engine/rag.py` `retrieve_context(query, conn, limit=5)` — calls `search_notes()`; injects top-N note bodies as quoted user context in adapter call; visible in `--debug` output |
</phase_requirements>

---

## Summary

Phase 4 adds four distinct capabilities to the existing engine, all building directly on the tested Phase 1–3 foundation. None require new AI infrastructure — they reuse the existing `ClaudeAdapter`, `RateLimiter`, `search_notes()`, and `capture_note()` functions.

The two automation pieces (file watcher and git hook) are daemon/sidecar concerns that run outside the main CLI. The file watcher (`watchdog` observer) runs as a long-lived process and calls back into the existing capture pipeline. The git post-commit hook is a shell script (following the `.githooks/` pattern already established) that delegates to a Python helper.

The people/meetings/work features are largely template additions — the underlying capture, indexing, and search infrastructure already handles them. The main new engine code is `engine/links.py` for bidirectional backlink maintenance and orphan checking.

RAG-lite (SEARCH-04) is a thin wrapper: retrieve top-N FTS5 results for a query, prepend them as quoted context blocks to the user content in the adapter call. No vector embeddings needed — BM25 is sufficient for this project's scale.

**Primary recommendation:** Build in this order — Wave 0 (test stubs) → templates (WORK-01–04) → link engine (PEOPLE-03, PEOPLE-04, SEARCH-03) → RAG-lite (SEARCH-04) → file watcher (CAP-04) → git hook (CAP-05). Templates are zero-risk; link engine and RAG-lite use known patterns; watcher/hook are the most operationally complex.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `watchdog` | 6.0.0 | Cross-platform file system events (macOS FSEvents, Linux inotify) | Standard Python file watching library; handles platform differences; `Observer` + `FileSystemEventHandler` API is stable |
| `threading.Timer` | stdlib | Debounce rapid file events | Standard pattern; cancel/restart on each new event; no extra dep |
| `subprocess` | stdlib | Git data extraction in post-commit hook (`git log`, `git diff`) | Already used by `ClaudeAdapter`; consistent with project pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-frontmatter` | >=1.0 | Read/write frontmatter on existing notes (backlink injection) | Already a dependency; used to append backlinks to person profiles |
| `pathlib.Path` | stdlib | All file paths (FOUND-12 mandate) | Already enforced throughout engine |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `watchdog` | `watchfiles` | `watchfiles` is faster/leaner but Rust extension dep; `watchdog` is pure-Python + optional C extension and is the established standard |
| `watchdog` | Raw `inotify`/`FSEvents` | Platform-specific; `watchdog` abstracts this cleanly |
| `threading.Timer` debounce | `asyncio`-based debounce | Async would require rewriting sync capture pipeline; `threading.Timer` fits the existing sync architecture |
| FTS5 BM25 RAG | Vector embeddings (sqlite-vec) | Embeddings require a model call to generate; FTS5 BM25 is already built, zero added deps, sufficient for single-user knowledge base at this scale |

**New package needed:** `watchdog`. Add to `pyproject.toml` dependencies.

**Installation:**
```bash
uv add watchdog
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 4 additions)

```
engine/
├── watcher.py          # File watcher daemon (CAP-04)
├── links.py            # Backlink maintenance + orphan check (PEOPLE-03, PEOPLE-04, SEARCH-03)
├── rag.py              # RAG-lite context retrieval (SEARCH-04)
└── hooks/
    └── post_commit.py  # Git hook helper (CAP-05)

.githooks/
└── post-commit         # Shell wrapper → engine/hooks/post_commit.py

brain/.meta/templates/
├── people.md           # PEOPLE-01 template
├── meeting.md          # PEOPLE-02 template (already exists or extend)
├── strategy.md         # WORK-01 OKR template
├── projects.md         # WORK-02 client/account template
├── coding.md           # WORK-03 ADR template
└── ideas.md            # WORK-04 idea template (already exists or extend)

tests/
├── test_watcher.py
├── test_links.py
├── test_rag.py
└── test_hooks.py
```

### Pattern 1: File Watcher with Debounce (CAP-04)

**What:** `watchdog` Observer watches `brain/files/`. On `FileCreatedEvent`, a `threading.Timer` fires after debounce window. `RateLimiter` (already in `engine/ratelimit.py`) gates AI calls. AI categorization prompt uses `ClaudeAdapter`.

**Critical constraints from AI-09 (already implemented):** min 5s debounce; max 1 prompt per 5 seconds across bulk drops.

```python
# engine/watcher.py
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from engine.ratelimit import RateLimiter

DEBOUNCE_SECONDS = 5.0

class FilesDropHandler(FileSystemEventHandler):
    """Watch brain/files/ for new files; debounce + rate-limit AI categorization."""

    def __init__(self, on_new_file, rate_limiter: RateLimiter):
        self._on_new_file = on_new_file
        self._rate_limiter = rate_limiter
        self._pending: dict[str, threading.Timer] = {}

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        path = event.src_path
        # Cancel any pending timer for this path (debounce)
        if path in self._pending:
            self._pending[path].cancel()
        timer = threading.Timer(DEBOUNCE_SECONDS, self._fire, args=[path])
        self._pending[path] = timer
        timer.start()

    def _fire(self, path: str) -> None:
        self._pending.pop(path, None)
        if self._rate_limiter.allow():
            self._on_new_file(Path(path))
        # else: silently skip — rate limit exceeded


def start_watcher(watch_dir: Path, on_new_file) -> Observer:
    """Start a watchdog Observer for watch_dir. Returns the Observer (call .stop() to stop)."""
    rate_limiter = RateLimiter(max_calls=1, window_seconds=5.0)
    handler = FilesDropHandler(on_new_file, rate_limiter)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()
    return observer
```

**CLI entry point** (`sb-watch`): run as daemon; `observer.join()` in main loop; clean shutdown on `KeyboardInterrupt`.

### Pattern 2: Git Post-Commit Hook (CAP-05)

**What:** Shell wrapper in `.githooks/post-commit` delegates to Python. Python reads commit info via `git log -1`, gets diff via `git diff HEAD~1 HEAD --stat`, passes to `ClaudeAdapter` for summary. Prints summary and asks user to confirm linking to a brain entry.

**Important:** Post-commit hook runs in the project's git repo directory, NOT the brain repo. The hook must know the brain DB path — use `BRAIN_ROOT` from `engine/paths.py`. The hook is installed per-project (user runs `git config core.hooksPath /path/to/brain/.githooks`).

```sh
# .githooks/post-commit
#!/usr/bin/env sh
# Fires after every git commit in any repo that has core.hooksPath pointing here.
# Delegates to Python for AI summarization.
set -e
if command -v uv >/dev/null 2>&1; then
    uv run --no-project python -m engine.hooks.post_commit "$@"
else
    python -m engine.hooks.post_commit "$@"
fi
```

```python
# engine/hooks/post_commit.py
import subprocess
from pathlib import Path
from engine.paths import CONFIG_PATH
from engine.router import get_adapter

def get_commit_info() -> dict:
    """Extract commit message and stat diff from HEAD."""
    msg = subprocess.run(
        ["git", "log", "-1", "--format=%s", "HEAD"],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    stat = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--stat"],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    repo = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    return {"message": msg, "stat": stat, "repo": Path(repo).name}

def main() -> None:
    info = get_commit_info()
    adapter = get_adapter("public", CONFIG_PATH)
    system = "You are a commit summarizer. Given a git commit message and file stat, write a 1-sentence plain-English summary. Output only the summary sentence."
    user_content = f"Commit: {info['message']}\n\nFiles changed:\n{info['stat']}"
    try:
        summary = adapter.generate(user_content=user_content, system_prompt=system)
    except Exception as e:
        print(f"[sb-hook] AI summary unavailable: {type(e).__name__}")
        return
    print(f"\n[second-brain] Commit summary: {summary}")
    answer = input("Link this commit to a brain entry? [y/N]: ").strip().lower()
    if answer == "y":
        title = input("Brain entry title (or press Enter to skip): ").strip()
        if title:
            # Delegate to capture pipeline
            from engine.capture import capture_note
            from engine.db import get_connection, init_schema
            conn = get_connection()
            init_schema(conn)
            capture_note("coding", title, summary, [], [], "public",
                         __import__("engine.paths", fromlist=["BRAIN_ROOT"]).BRAIN_ROOT, conn)
            conn.close()
            print("[second-brain] Brain entry created.")
```

**Installation:** User runs once per project: `git config core.hooksPath /path/to/brain/.githooks`

**CRITICAL:** First commit in a fresh repo has no `HEAD~1`. Guard: if `git diff HEAD~1 HEAD` fails, fall back to `git show --stat HEAD`.

### Pattern 3: Backlink Maintenance (PEOPLE-03)

**What:** After a meeting note is written (or any note with `people` frontmatter), read the `people` list, find each person's `.md` file in `brain/people/`, append a `- [[meeting-note-path]]` backlink line, and insert a row into the `relationships` table.

**Where to call it:** In `capture_note()` in `engine/capture.py`, after `write_note_atomic()` succeeds. Pass it the note path and `people` list.

```python
# engine/links.py
import frontmatter
from pathlib import Path
import sqlite3
import datetime

def add_backlinks(
    note_path: Path,
    people: list[str],
    brain_root: Path,
    conn: sqlite3.Connection,
) -> None:
    """For each person in people, append a backlink to their profile and record in relationships table.

    Args:
        note_path: The meeting/note that references these people.
        people: List of person slugs (e.g. ["alice-smith", "bob-jones"]).
        brain_root: Root of brain directory.
        conn: Open SQLite connection.
    """
    for person_slug in people:
        # Normalize: strip whitespace, lowercase, replace spaces with hyphens
        slug = person_slug.strip().lower().replace(" ", "-")
        person_file = brain_root / "people" / f"{slug}.md"
        if not person_file.exists():
            continue  # Person profile doesn't exist yet — skip silently

        # Append backlink to person profile
        text = person_file.read_text(encoding="utf-8")
        backlink = f"\n- [[{note_path}]]"
        if str(note_path) not in text:  # idempotent
            person_file.write_text(text + backlink, encoding="utf-8")

        # Record in relationships table (idempotent via PRIMARY KEY conflict)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type, created_at)"
                " VALUES (?, ?, ?, ?)",
                (str(person_file), str(note_path), "backlink",
                 datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
            )
            conn.commit()
        except Exception:
            pass  # Relationship record is best-effort; never blocks capture
```

### Pattern 4: Link Orphan Checker (PEOPLE-04, SEARCH-03)

**What:** `check_links()` queries the `relationships` table and verifies both files exist and each has a reference to the other. Reports orphans (one-way links or missing files).

```python
# engine/links.py (continued)
def check_links(brain_root: Path, conn: sqlite3.Connection) -> list[dict]:
    """Return list of orphaned link dicts: {source, target, issue}.

    An orphan is:
    - A relationship row where source or target file does not exist on disk
    - A relationship row where target does not contain a reference back to source
      (bidirectional check for people<->meetings)
    """
    orphans = []
    rows = conn.execute("SELECT source_path, target_path, rel_type FROM relationships").fetchall()
    for source_str, target_str, rel_type in rows:
        source = Path(source_str)
        target = Path(target_str)
        if not source.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "source missing"})
            continue
        if not target.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "target missing"})
            continue
        # For backlinks: verify target content references source (bidirectional)
        if rel_type == "backlink":
            target_text = target.read_text(encoding="utf-8")
            if source_str not in target_text and source.stem not in target_text:
                orphans.append({
                    "source": source_str, "target": target_str,
                    "issue": "target does not reference source"
                })
    return orphans


def main_check_links() -> None:
    """CLI entry point for sb-check-links."""
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT
    conn = get_connection()
    init_schema(conn)
    orphans = check_links(BRAIN_ROOT, conn)
    conn.close()
    if not orphans:
        print("No orphaned links found.")
        return
    print(f"Found {len(orphans)} orphaned link(s):")
    for o in orphans:
        print(f"  {o['source']} -> {o['target']}: {o['issue']}")
```

### Pattern 5: RAG-lite Context Retrieval (SEARCH-04)

**What:** Before an AI query response is generated, retrieve the top-N FTS5 matches for the query. Prepend them as labeled context blocks to the `user_content` argument. The note content is NEVER in `system_prompt` (AI-10 compliance).

```python
# engine/rag.py
from pathlib import Path
import sqlite3
from engine.search import search_notes

CONTEXT_HEADER = "=== RETRIEVED CONTEXT (from second brain FTS5 search) ==="
CONTEXT_FOOTER = "=== END RETRIEVED CONTEXT ==="

def retrieve_context(
    query: str,
    conn: sqlite3.Connection,
    limit: int = 5,
    debug: bool = False,
) -> str:
    """Return a formatted context block of top-N FTS5 results for injection into AI prompt.

    Args:
        query: Search query (same as user's question).
        conn: Open SQLite connection.
        limit: Max notes to include.
        debug: If True, print retrieved notes to stdout.

    Returns:
        Formatted string ready to prepend to user_content in adapter.generate() call.
        Returns empty string if no results found.
    """
    results = search_notes(conn, query, limit=limit)
    if not results:
        return ""

    blocks = [CONTEXT_HEADER]
    for r in results:
        note_path = Path(r["path"])
        try:
            body = note_path.read_text(encoding="utf-8")[:500]  # truncate long notes
        except OSError:
            body = "[note file not readable]"
        blocks.append(f"\n[{r['title']}] ({r['path']})\n{body}")
        if debug:
            print(f"[RAG] Retrieved: {r['title']} (score={r['score']:.4f})")
    blocks.append(CONTEXT_FOOTER)
    return "\n".join(blocks)


def augment_prompt(query: str, conn: sqlite3.Connection, debug: bool = False) -> str:
    """Return user_content with RAG context prepended.

    Usage in AI query flow:
        user_content = augment_prompt(user_question, conn, debug=True)
        response = adapter.generate(user_content=user_content, system_prompt=static_system)
    """
    context = retrieve_context(query, conn, debug=debug)
    if context:
        return f"{context}\n\n---\n\n{query}"
    return query
```

**AI-10 compliance:** context blocks are prepended to `user_content`, never to `system_prompt`. The `system_prompt` remains a static instruction string.

### Pattern 6: Work-Domain Templates (WORK-01 through WORK-04)

Templates are Markdown files in `brain/.meta/templates/`. The existing `engine/templates.py` `load_template()` function reads them. No new engine code needed — just new template files.

**OKR template** (`.meta/templates/strategy.md`):
```markdown
---
type: strategy
title: "{{title}}"
---

## Objective

## Key Results

- KR1:
- KR2:
- KR3:

## Status

## Linked Initiatives
```

**People profile template** (`.meta/templates/people.md`):
```markdown
---
type: people
title: "{{title}}"
---

## Role

## Notes

## Growth Discussion History

## Meetings & References
```

**ADR/Coding template** (`.meta/templates/coding.md`):
```markdown
---
type: coding
title: "{{title}}"
---

## Context

## Decision

## Alternatives Considered

## Consequences

## GitHub Repo
```

**Project/Client template** (`.meta/templates/projects.md`):
```markdown
---
type: projects
title: "{{title}}"
---

## Client / Account

## Key Contacts
<!-- link to people/ entries -->

## Status

## Meeting History
```

### Anti-Patterns to Avoid

- **Starting the watchdog Observer in the main CLI process.** The watcher is a daemon; run it as `sb-watch` (separate entry point). If watcher crashes, it must not take down `sb-capture`.
- **Calling `add_backlinks()` before `write_note_atomic()` commits.** Backlinks must only be written if the note was successfully committed to disk and DB. Call `add_backlinks()` after `write_note_atomic()` returns without exception.
- **Watching `brain/` recursively for the file watcher.** Only watch `brain/files/` (`recursive=False`). Watching the whole brain recursively would fire events on every note capture, creating a feedback loop.
- **Writing backlinks by overwriting the person file entirely.** Use append-to-existing text, not `write_note_atomic()`, for backlink injection — the person file already exists and the atomic two-phase write would re-index it with stale content.
- **Injecting retrieved context into `system_prompt`.** RAG context goes in `user_content` only (AI-10). The `system_prompt` contains only static instructions.
- **`git diff HEAD~1 HEAD` on the first commit in a repo.** There is no `HEAD~1` on the initial commit. Guard: catch the non-zero return code and fall back to `git show --stat HEAD`.
- **Installing the post-commit hook in the brain's `.git/hooks/`.** The brain repo already uses `.githooks/pre-commit` for secret scanning. The post-commit hook for CAP-05 is installed by the USER in their project repos, not in the brain repo itself.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File system events | Polling loop with `os.stat()` / `os.scandir()` | `watchdog.Observer` | Polling is CPU-wasteful and misses rapid events; `watchdog` uses native OS APIs (FSEvents/inotify) |
| Debounce timer | Custom `time.sleep()` loop | `threading.Timer` cancel/restart pattern | Sleep loop blocks the handler thread; Timer runs independently and is cancellable |
| Rate limiting | Custom counter + timestamp | Existing `engine.ratelimit.RateLimiter` | Already built and tested in Phase 3 (AI-09); sliding window, not fixed window |
| Git commit info | Parsing `.git/COMMIT_EDITMSG` directly | `git log -1 --format=%s HEAD` via subprocess | `COMMIT_EDITMSG` is not reliable; `git log` is the canonical way |
| Bidirectional link index | Scanning all markdown files on every check | `relationships` table in existing SQLite schema | Schema already has `relationships` table with `(source_path, target_path, rel_type)` primary key; use it |
| RAG embeddings | Generating vector embeddings with a model | FTS5 BM25 via existing `search_notes()` | Embeddings require a model call to generate and `sqlite-vec` extension; BM25 is already live, zero new deps, sufficient quality for single-user personal knowledge base |

---

## Common Pitfalls

### Pitfall 1: FSEvents Emitting Historic Events on macOS

**What goes wrong:** The `watchdog` Observer fires events for files that already existed before the watcher started (up to 30 seconds of history).

**Why it happens:** macOS FSEvents API has a `suppress_history=False` default. Watchdog 6.0.0 documents this behavior.

**How to avoid:** In `FilesDropHandler.on_created`, check `Path(event.src_path).stat().st_ctime` against `observer_start_time`. Skip files older than watcher start time + 1 second. Or: record the set of files present at start; skip events for paths already in that set.

**Warning signs:** Categorization prompts fire for files already in `brain/files/` when the watcher starts.

### Pitfall 2: Post-Commit Hook Blocks Interactive Git

**What goes wrong:** `input()` inside the post-commit hook hangs in non-interactive contexts (CI, git GUIs, `git commit --no-edit`).

**Why it happens:** `sys.stdin` may not be a TTY inside the hook environment.

**How to avoid:** Check `sys.stdin.isatty()` before calling `input()`. If not a TTY, print the summary and skip the interactive linking prompt. Log to stderr: `[sb-hook] non-interactive: skipping brain link prompt`.

**Warning signs:** `git commit` hangs with no output in CI or some GUI clients.

### Pitfall 3: Backlink Appended Multiple Times

**What goes wrong:** Running `/sb-capture` for the same meeting twice appends duplicate backlinks to the person profile.

**Why it happens:** `add_backlinks()` appends unconditionally.

**How to avoid:** Check if `str(note_path)` already appears in the person file text before appending. The pattern in the code above already includes this idempotency guard: `if str(note_path) not in text`.

### Pitfall 4: People Slug Mismatch

**What goes wrong:** `--people "Alice Smith"` does not find `brain/people/alice-smith.md` because the file was created with a different slug (e.g. `alice.md` or `alice-smith-2024-01-15.md`).

**Why it happens:** `capture_note()` generates slugs with date prefixes: `2024-01-15-alice-smith.md`. But `add_backlinks()` looks for `alice-smith.md`.

**How to avoid:** `add_backlinks()` must search `brain/people/` for files whose basename contains the slug, not exact match. Use `list(brain_root.glob(f"people/*{slug}*.md"))` and take the first match. Document in the people template that the slug should match the `--people` value.

### Pitfall 5: RAG Context Exceeds Adapter Token Limit

**What goes wrong:** 5 notes × 500 chars each = 2500 chars of context prepended to the query, possibly exceeding the model's context window or making the prompt very expensive.

**Why it happens:** Notes can be long; truncation at 500 chars per note helps but 5 notes is still additive.

**How to avoid:** `retrieve_context()` truncates each note body to 500 chars (already in the pattern). Default `limit=5`. Make both configurable in `config.toml` under `[rag]` section. If adapter call fails with a context-too-long error, retry with `limit=2`.

### Pitfall 6: Watcher Process Not Started / Not Running

**What goes wrong:** User drops a file in `brain/files/` but nothing happens because `sb-watch` is not running.

**Why it happens:** The watcher is a separate daemon process; it is not auto-started.

**How to avoid:** Document that `sb-watch` must be started (e.g., in a tmux pane or as a login item). Add a status check to `bootstrap.py --dev`: `pgrep -f sb-watch` and print a warning if not running.

---

## Code Examples

### Watchdog Observer Start/Stop Lifecycle

```python
# Source: https://pypi.org/project/watchdog/ — standard Observer pattern
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"New file: {event.src_path}")

observer = Observer()
observer.schedule(MyHandler(), path="/watch/this", recursive=False)
observer.start()
try:
    while observer.is_alive():
        observer.join(timeout=1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

### threading.Timer Debounce Pattern

```python
# Source: Python stdlib threading docs + watchdog community pattern
import threading

class DebouncedHandler:
    def __init__(self, delay_seconds: float, callback):
        self._delay = delay_seconds
        self._callback = callback
        self._timers: dict[str, threading.Timer] = {}

    def on_event(self, key: str, *args):
        if key in self._timers:
            self._timers[key].cancel()
        t = threading.Timer(self._delay, self._callback, args=args)
        self._timers[key] = t
        t.start()
```

### Git Log Extraction in Post-Commit Hook

```python
# Source: git-scm.com/docs/githooks — post-commit receives no args; use git log
import subprocess

def get_last_commit_message() -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s", "HEAD"],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()

def get_commit_stat() -> str:
    # Guard against initial commit (no HEAD~1)
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--stat"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        # Initial commit: fall back to git show
        result = subprocess.run(
            ["git", "show", "--stat", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    return result.stdout.strip()
```

### RAG Context Injection (AI-10 Compliant)

```python
# Correct: context in user_content, static instructions in system_prompt
from engine.rag import augment_prompt
from engine.router import get_adapter
from engine.paths import CONFIG_PATH

user_question = "What did we decide about the Q2 roadmap?"
adapter = get_adapter("public", CONFIG_PATH)

# RAG: retrieve context and prepend to user_content
user_content = augment_prompt(user_question, conn, debug=True)
system = "You are a knowledge assistant. Answer based on the provided context from the user's notes."

response = adapter.generate(user_content=user_content, system_prompt=system)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling loop for file changes | `watchdog` native OS event API | Library stable since 2012, v6.0 2024 | Zero CPU polling; immediate events |
| Hook scripts in `.git/hooks/` (not version-controlled) | Versioned hooks in `.githooks/` with `core.hooksPath` | Git 2.9+ (2016) | Hooks are version-controlled; established in Phase 1 of this project |
| Manual backlink maintenance | `relationships` SQLite table + `add_backlinks()` | Project design | Automated, queryable, auditable |
| Full-corpus scanning for orphans | Query `relationships` table | Project design | O(rows in table) vs O(all files) |
| Vector RAG | BM25 FTS5 RAG | Project scope decision | Zero embedding model calls; no new deps; BM25 is sufficient for sub-1000-note personal corpus |

**Deprecated/outdated for this project:**
- Installing hooks in `.git/hooks/` directly — project uses `.githooks/` with `core.hooksPath`
- `watchfiles` — viable but adds Rust extension dependency; `watchdog` chosen for pure-Python fallback path

---

## Open Questions

1. **`projects` as a note type in `--type` choices**
   - What we know: `capture.py` `--type` choices are `["note", "meeting", "people", "coding", "strategy", "idea"]`. The brain has a `projects/` subdir (FOUND-03) but `projects` is not a valid `--type`.
   - What's unclear: Should `projects` and `personal` be added as `--type` choices? The WORK-02 requirement implies yes.
   - Recommendation: Add `"projects"`, `"personal"` to the `--type` choices in `capture.py` and `QUESTION_SYSTEM_PROMPTS` in `engine/ai.py`. This is a one-line change per location.

2. **`ideas` vs `idea` as note type slug**
   - What we know: The brain subdir is `ideas/` (plural) but the `--type` choices include `"idea"` (singular). `capture_note()` uses `note_type` as the subdir name directly: `brain_root / note_type / f"{slug}.md"`. So `--type idea` would create files in `brain/idea/` (missing the `s`).
   - What's unclear: Was this inconsistency already handled, or is there a mapping layer?
   - Recommendation: Audit `capture_note()` — add a `TYPE_TO_DIR` mapping dict if needed: `{"idea": "ideas", "people": "people", ...}`.

3. **Person profile slug vs. date-prefixed capture slug**
   - What we know: `capture_note()` generates `{date}-{title-slug}.md`. A person "Alice Smith" captured on 2026-03-14 becomes `2026-03-14-alice-smith.md`. But `--people "alice-smith"` in another note needs to find this file.
   - What's unclear: The `add_backlinks()` glob approach (`people/*alice-smith*.md`) handles this, but what if two people have similar names?
   - Recommendation: Consider a `people/` naming convention without date prefix for person profiles: override the slug generation in `capture_note()` when `note_type == "people"` to use `{title-slug}.md` only (no date). This makes person profiles predictably addressable.

4. **File watcher as daemon: auto-start mechanism**
   - What we know: The watcher is a separate process (`sb-watch`). macOS has `launchd` for auto-start; Linux has `systemd`.
   - What's unclear: Is auto-start in scope for Phase 4, or is manual `sb-watch` start sufficient?
   - Recommendation: Out of scope for Phase 4 — document that the user must start `sb-watch` manually. Add a check in `bootstrap.py --dev` that warns if the watcher is not running.

5. **`sb-watch` command in pyproject.toml**
   - What we know: `[project.scripts]` currently has `sb-init`, `sb-reindex`, `sb-capture`, `sb-search`. `sb-check-links` and `sb-watch` need to be added.
   - Recommendation: Add both to `pyproject.toml` scripts in Wave 0.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x (already in pyproject.toml dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --no-project --with pytest pytest tests/ -x -q` |
| Full suite command | `uv run --no-project --with pytest pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAP-04 | `FilesDropHandler.on_created` fires callback after debounce delay | unit (mock timer) | `pytest tests/test_watcher.py::test_debounce_fires_after_delay -x` | Wave 0 |
| CAP-04 | Bulk-dropping 5 files in <5s fires callback only once per file (debounce) | unit | `pytest tests/test_watcher.py::test_bulk_drop_debounce -x` | Wave 0 |
| CAP-04 | RateLimiter gates: 2nd call within 5s is suppressed | unit (uses existing RateLimiter) | `pytest tests/test_watcher.py::test_rate_limit_gates_ai_call -x` | Wave 0 |
| CAP-05 | `get_commit_info()` returns message, stat, repo name from mocked git subprocess | unit (mock subprocess) | `pytest tests/test_hooks.py::test_get_commit_info -x` | Wave 0 |
| CAP-05 | `get_commit_stat()` falls back to `git show` when `HEAD~1` does not exist | unit (mock subprocess returncode=128) | `pytest tests/test_hooks.py::test_initial_commit_fallback -x` | Wave 0 |
| PEOPLE-03 | `add_backlinks()` appends `[[note_path]]` to person profile file | unit (tmp_path) | `pytest tests/test_links.py::test_add_backlink_appended -x` | Wave 0 |
| PEOPLE-03 | `add_backlinks()` is idempotent — second call does not duplicate backlink | unit (tmp_path) | `pytest tests/test_links.py::test_add_backlink_idempotent -x` | Wave 0 |
| PEOPLE-03 | `add_backlinks()` inserts row into relationships table | unit (in-memory SQLite) | `pytest tests/test_links.py::test_relationship_row_inserted -x` | Wave 0 |
| PEOPLE-03 | `add_backlinks()` skips silently if person file does not exist | unit | `pytest tests/test_links.py::test_missing_person_skipped -x` | Wave 0 |
| PEOPLE-04 | `check_links()` returns orphan when target file is missing | unit (tmp_path) | `pytest tests/test_links.py::test_orphan_missing_target -x` | Wave 0 |
| PEOPLE-04 | `check_links()` returns empty list for correctly linked brain | unit | `pytest tests/test_links.py::test_no_orphans_clean_brain -x` | Wave 0 |
| SEARCH-03 | `sb-check-links` CLI prints "No orphaned links" for clean brain | unit (mock check_links) | `pytest tests/test_links.py::test_cli_no_orphans -x` | Wave 0 |
| SEARCH-04 | `retrieve_context()` returns formatted block with top-N results | unit (seeded in-memory SQLite) | `pytest tests/test_rag.py::test_retrieve_context_returns_block -x` | Wave 0 |
| SEARCH-04 | `augment_prompt()` prepends context to user_content, not to system | unit | `pytest tests/test_rag.py::test_augment_prompt_in_user_content -x` | Wave 0 |
| SEARCH-04 | `retrieve_context()` returns empty string when no FTS5 results | unit | `pytest tests/test_rag.py::test_retrieve_context_empty -x` | Wave 0 |
| WORK-01–04 | Template files exist and contain required section headers | unit (file existence + grep) | `pytest tests/test_links.py::test_work_templates_exist -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run --no-project --with pytest pytest tests/ -x -q`
- **Per wave merge:** `uv run --no-project --with pytest pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_watcher.py` — covers CAP-04
- [ ] `tests/test_hooks.py` — covers CAP-05
- [ ] `tests/test_links.py` — covers PEOPLE-03, PEOPLE-04, SEARCH-03, WORK-01–04 template existence
- [ ] `tests/test_rag.py` — covers SEARCH-04
- [ ] `pyproject.toml` — add `sb-watch` and `sb-check-links` entry points
- [ ] `pyproject.toml` — add `watchdog>=6.0` to dependencies
- [ ] `engine/watcher.py`, `engine/links.py`, `engine/rag.py`, `engine/hooks/post_commit.py` — stub files so imports do not fail during `pytest --collect-only`

*(PEOPLE-01, PEOPLE-02, WORK-01–04: covered by existing capture + template tests; no new test files needed beyond template existence checks)*

---

## Sources

### Primary (HIGH confidence)

- [watchdog PyPI](https://pypi.org/project/watchdog/) — version 6.0.0, Python 3.9+, Observer/FileSystemEventHandler API confirmed
- [watchdog GitHub gorakhargosh/watchdog](https://github.com/gorakhargosh/watchdog) — FSEvents macOS notes, `suppress_history` behavior, Observer scheduling API
- [git-scm.com/docs/githooks](https://git-scm.com/docs/githooks) — post-commit hook: no parameters, `git log -1 HEAD` pattern, placement in hooks directory
- Existing project code (`engine/ratelimit.py`, `engine/search.py`, `engine/db.py`, `engine/capture.py`, `engine/paths.py`) — HIGH confidence on what already exists and what interfaces Phase 4 must match

### Secondary (MEDIUM confidence)

- WebSearch: `threading.Timer` debounce pattern for watchdog — multiple sources confirm cancel/restart pattern as standard; stdlib Timer docs are authoritative
- WebSearch: FTS5 BM25 for RAG-lite — multiple 2025 projects confirm FTS5 is a viable and common approach for small-corpus RAG without vector embeddings
- WebSearch: `git diff HEAD~1 HEAD --stat` initial-commit edge case — multiple sources confirm `HEAD~1` fails on initial commit; `git show` as fallback confirmed by git-scm docs

### Tertiary (LOW confidence — flag for validation)

- People slug convention (no-date-prefix for people profiles) — project decision needed, not verified against existing code behavior; audit `capture_note()` at implementation time
- `projects` and `personal` as `--type` choices — implied by WORK-02 and brain subdir structure but not explicitly confirmed in existing `capture.py`; verify before implementing

---

## Metadata

**Confidence breakdown:**
- Standard stack (watchdog, threading.Timer, subprocess): HIGH — PyPI, stdlib, official git docs
- Architecture (watcher daemon, hook pattern, link engine, RAG-lite): HIGH — consistent with existing project patterns; no novel dependencies
- Pitfalls: HIGH — FSEvents history issue documented in watchdog source; git initial-commit edge case is a known gotcha
- Open questions (slug convention, type choices): LOW — require code audit at planning time

**Research date:** 2026-03-14
**Valid until:** 2026-05-14 (watchdog 6.x API stable; stdlib patterns; git hooks interface is decades-stable)
