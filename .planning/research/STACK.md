# Technology Stack

**Project:** Cybernetic Second Brain
**Researched:** 2026-03-14
**Confidence note:** WebSearch and Bash blocked during this session. Recommendations are from training data (cutoff August 2025). Confidence levels reflect this. Verify pinned versions before use.

---

## Recommended Stack

### Core Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11.x | Engine language | 3.11 is LTS-stable, ships in mcr.microsoft.com/devcontainers/python:3.11 base image. 3.12 has minor stdlib changes that break some packages; 3.11 is the safest target for DevContainer cross-platform use as of mid-2025. Do NOT use 3.13 — ecosystem lag. |
| TOML (stdlib) | built-in (3.11+) | Config parsing for `.meta/config.toml` | `tomllib` is stdlib since 3.11. Zero-dependency config parsing. |
| pathlib (stdlib) | built-in | All path operations | Project constraint: no hardcoded separators. `pathlib.Path` throughout. |

**Confidence:** HIGH — 3.11 stdlib facts verified against Python release timeline.

---

### DevContainer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| DevContainer base image | `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye` | Consistent Python 3.11 environment | Microsoft-maintained, updated regularly, includes git, curl, common dev tools. Bullseye (Debian 11) is stable. Avoid `bookworm` (Debian 12) base images — glibc version differences can cause issues with some native Python extensions on older Docker Desktop Windows. |
| Docker Compose | v2 (built-in to Docker Desktop) | Named volume management for SQLite | `docker compose` (v2, no hyphen) is the current standard. Do NOT use `docker-compose` (v1, Python-based, deprecated). |
| Named volume `brain-index-data` | — | Persists SQLite across rebuilds | Declared in `docker-compose.yml`. NOT bind-mounted to host (avoids Drive sync corruption). |
| Host bind mount `~/SecondBrain` → `/workspace/brain` | — | Brain content access | Host-level Google Drive handles sync; container sees it read/write. Use `${localEnv:HOME}/SecondBrain` in `devcontainer.json` — test on Windows WSL2 explicitly (known risk). |
| `remoteUser` | `vscode` | Container user | Set consistently to `vscode` throughout. Never mix `root` and `vscode` — causes permission failures on volume mounts. |

**Confidence:** MEDIUM — Base image tag naming stable as of mid-2025; verify `mcr.microsoft.com/devcontainers/python` tag list before pinning.

---

### CLI Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Typer** | `>=0.12,<1.0` | CLI commands (`sb-capture`, `sb-search`, etc.) | Built on Click. Type-annotated function signatures become CLI arguments — no boilerplate. Auto-generates `--help`. `rich` integration for colored output. Actively maintained by FastAPI author. |
| **Rich** | `>=13.0` | Terminal output formatting | Tables, progress bars, colored output. Typer depends on it. Use directly for `sb-search` result display. |

**Why not argparse:** Too low-level. You'd write 3x the code.
**Why not Click directly:** Typer IS Click with type annotations. Use Typer; drop to Click primitives only if needed.
**Why not click-rich or textual for CLI:** Textual is for TUI apps (future GUI milestone). CLI-first means Typer now, Textual later.

**Confidence:** HIGH — Typer 0.12 released 2024, stable API. Rich 13.x stable.

---

### Markdown Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **python-frontmatter** | `>=1.1.0` | Parse/write YAML frontmatter + body | Purpose-built for exactly this use case. Preserves frontmatter structure on write. Returns `post.metadata` dict + `post.content` string. Round-trip safe. |
| **mistune** | `>=3.0` | Markdown → HTML/AST for indexing | v3 has a clean AST plugin system. Used for extracting wikilinks (`[[note]]`), extracting headings for index, and rendering previews. Lighter than python-markdown. |

**Why not python-markdown:** Plugin architecture is messier than mistune v3. More dependencies.
**Why not marko:** Less community adoption, less documentation.
**Why not markdown-it-py:** Good alternative to mistune v3, comparable. Either works. Mistune v3 is marginally simpler API for AST walking.
**Why not pandoc (subprocess):** Heavy dependency, subprocess calls, not installable via pip cleanly in DevContainer without apt.

**Confidence:** MEDIUM — python-frontmatter 1.x is stable. Mistune 3.x released 2023, maintained. Verify latest patch versions at install time.

---

### SQLite / FTS5

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **sqlite-utils** | `>=3.36` | SQLite schema management, FTS5 index creation, row operations | Simon Willison's library. `db.enable_fts(table, columns)` creates FTS5 virtual table in one call. Built-in support for `populate_fts()`, `rebuild_fts()`, row deletion (critical for GDPR erasure). CLI included (useful for debugging). |
| **Python stdlib `sqlite3`** | built-in | Raw FTS5 queries where sqlite-utils is insufficient | FTS5 `MATCH` queries, `bm25()` ranking, `snippet()` function — drop to raw SQL via `sqlite-utils` db.conn for these. sqlite-utils wraps but doesn't hide the connection. |

**Why not SQLAlchemy:** Massive overkill. Full ORM for a single-user local SQLite is 10x the complexity needed. sqlite-utils gives 90% of the convenience with 5% of the weight.
**Why not peewee:** Another ORM. Same objection.
**Why not raw sqlite3 only:** sqlite-utils's FTS5 management helpers save ~200 lines of boilerplate for schema migration, FTS population, and rebuild.

**FTS5 specifics:**
- Use `content=''` (contentless) FTS5 table for index — note content stays in markdown, index only stores indexed text. Saves disk, avoids duplication.
- Exception: store `file_path`, `title`, `tags`, `content_type` as regular columns for filtering.
- GDPR erasure: `DELETE FROM notes WHERE person_id = ?` + `INSERT INTO notes_fts(notes_fts, rowid, ...) VALUES('delete', ...)` — sqlite-utils handles this via `db['notes'].delete_where()` + `db.populate_fts()`.

**Confidence:** HIGH — sqlite-utils is well-documented, actively maintained. FTS5 is bundled in CPython's sqlite3 since 3.7.

---

### File Watching

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **watchdog** | `>=4.0` | Detect new/modified files in `/workspace/brain` | The standard Python file watching library. Cross-platform (inotify on Linux, FSEvents on Mac, ReadDirectoryChangesW on Windows). Since the engine runs inside a Linux DevContainer watching a bind-mount, inotify is used — reliable for this use case. |

**Critical caveat — bind-mount inotify:** Google Drive modifies files on the host. Inotify events on a bind-mounted directory inside a container DO propagate from host to container on Linux/WSL2 bind mounts, but there are known delays and missed events with some Docker Desktop configurations. **Test this explicitly.** Fallback: polling observer (`watchdog.observers.polling.PollingObserver`) is slower but reliable across all configurations.

**Recommended pattern:**
```python
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
# Use PollingObserver for bind-mounts in DevContainer for reliability
# Configure interval via config.toml: watch_poll_interval_seconds = 2
```

**Why not polling loop (manual):** watchdog handles debouncing, event deduplication, cross-platform differences. Rolling your own is ~150 lines to get wrong.

**Confidence:** MEDIUM — watchdog 4.x released 2024. Bind-mount inotify behavior in DevContainer is a known edge case; polling fallback is the safe default.

---

### AI / LLM Clients

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **anthropic** (official SDK) | `>=0.28` | Claude API calls (primary AI) | Official Anthropic Python SDK. Supports Claude 3.5 Sonnet and above. Streaming responses, tool use, messages API. The only correct client for Claude API. |
| **ollama** (official Python client) | `>=0.2` | Local model calls for PII content | Official Ollama Python library (`import ollama`). Sync and async clients. `ollama.chat()` mirrors the Anthropic messages interface closely enough to build a thin routing layer. |

**Model routing architecture:** Build a `ModelRouter` abstraction with two implementations: `ClaudeClient` and `OllamaClient`, both implementing a common `complete(prompt, context) -> str` interface. The router reads `content_type` from the note's YAML frontmatter and selects the client. **Classification of content type must use local rules (regex/keyword matching on path + frontmatter tags) — never call a cloud API to classify PII content.**

**Why not LangChain/LlamaIndex:** Both are frameworks that abstract over the API clients. For a single-user tool with two specific AI backends, the abstraction costs (version churn, hidden behavior, complex dependencies) outweigh the benefits. Direct SDK calls + a 50-line router is better.
**Why not openai SDK with Ollama compatibility layer:** Ollama does expose an OpenAI-compatible endpoint, but the official `ollama` Python package is purpose-built and cleaner. Use it.

**Confidence:** MEDIUM — anthropic SDK 0.28+ verified against my training data. Ollama Python client 0.2.x is the official package. Verify latest versions; Anthropic SDK releases frequently.

---

### Binary File Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **python-docx** | `>=1.1` | Extract text from `.docx` | Standard library for Word documents. Text extraction only — do not attempt deep formatting parsing. |
| **python-pptx** | `>=0.6.23` | Extract text from `.pptx` | Standard library for PowerPoint. Extract slide text for FTS index. |
| **pypdf** | `>=4.0` | Extract text from `.pdf` | `pypdf` (formerly PyPDF2, renamed in 2023). Text extraction from PDF. Edge case: scanned PDFs are images — text extraction returns empty. Document this limitation; OCR is out of scope for v1. |

**Scoping constraint from PROJECT.md:** "Text extraction only, no deep parsing." All three libraries are used for their `.extract_text()` equivalent methods and nothing else.

**Confidence:** MEDIUM — pypdf rename from PyPDF2 happened in 2023; verify package name is `pypdf` not `PyPDF2` on PyPI.

---

### Configuration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **tomllib** (stdlib) | built-in (3.11+) | Read `.meta/config.toml` | No dependency. TOML is human-editable, more readable than YAML for config. Stdlib since 3.11. Read-only (tomllib cannot write TOML — use `tomli-w` for writes). |
| **tomli-w** | `>=1.0` | Write/update config.toml programmatically | Minimal write companion to tomllib. No other TOML write library needed. |
| **python-dotenv** | `>=1.0` | Load `.env.host` into environment | Standard approach for env file loading. Used in bootstrap/entry point only. |

**Confidence:** HIGH — tomllib stdlib since 3.11 is a fact. python-dotenv 1.x stable.

---

### Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pytest** | `>=8.0` | Test runner | Standard. No alternative to consider. |
| **pytest-cov** | `>=5.0` | Coverage reporting | Standard pytest coverage plugin. |
| **freezegun** | `>=1.4` | Mock datetime for audit trail tests | GDPR audit trail stores timestamps. freezegun lets tests assert exact created_at values without time-based flakiness. |

**Confidence:** HIGH — pytest 8.x released 2024, stable.

---

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pydantic** | `>=2.5` | Schema validation for note frontmatter | Validate YAML frontmatter fields on ingest. `PersonNote`, `MeetingNote`, `CodingNote` as Pydantic models. Pydantic v2 (Rust core) is significantly faster than v1. |
| **rich-click** | avoid | — | Do NOT add — Typer already integrates Rich. Adding rich-click creates conflicts. |
| **click** | transitive via Typer | — | Do not depend on directly unless dropping to Click primitives. |
| **httpx** | `>=0.27` | Async HTTP if needed beyond SDK clients | Only if direct HTTP calls needed. The Anthropic and Ollama SDKs handle their own HTTP. |

---

## DevContainer Base Image Decision

**Recommended:** `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye`

**Reasoning:**
- Microsoft's `devcontainers/python` images are the DevContainer standard — VS Code DevContainer extension expects them.
- The `1-3.11-bullseye` tag floats to the latest patch of Python 3.11 on Debian 11. This is intentional: security patches apply automatically on rebuild.
- `bullseye` (Debian 11) over `bookworm` (Debian 12): glibc 2.31 vs 2.35. On Windows with Docker Desktop using older WSL2 kernels, some native Python extensions (specifically those with C extensions compiled against newer glibc) fail to load. Bullseye is safer for cross-platform compatibility until WSL2 kernel versions stabilize.
- `vscode` user (uid 1000) is pre-created in this image. Set `remoteUser: "vscode"` in `devcontainer.json` and use it consistently everywhere.

**Alternative:** `python:3.11-slim-bullseye` (plain Python Docker image). Use if you need a leaner image and are comfortable configuring dev tooling yourself. Not recommended — you lose all the DevContainer convenience tooling.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI framework | Typer | Click | Typer IS Click + type annotations. No reason to use Click directly. |
| CLI framework | Typer | argparse | 3x boilerplate, no type inference, worse help generation |
| Markdown + frontmatter | python-frontmatter | manual PyYAML parse | python-frontmatter handles edge cases (no frontmatter, empty frontmatter, encoding). Don't reinvent. |
| Markdown AST | mistune v3 | markdown-it-py | Comparable quality. Mistune marginally simpler for AST walking. Either is acceptable. |
| SQLite ORM | sqlite-utils | SQLAlchemy | SQLAlchemy is full ORM. sqlite-utils is purpose-built for SQLite power features (FTS5, upsert, transforms). |
| SQLite ORM | sqlite-utils | peewee | Same objection as SQLAlchemy. |
| File watching | watchdog (PollingObserver) | inotifywait (subprocess) | inotifywait is Linux-only, not available in DevContainer by default, subprocess management is fragile. |
| AI abstraction | Direct SDK + thin router | LangChain | LangChain version churn is notorious. Two SDKs + 50-line router is more maintainable. |
| AI abstraction | Direct SDK + thin router | LlamaIndex | Same objection. LlamaIndex adds significant weight for marginal gain in a 2-model setup. |
| Config format | TOML (tomllib) | YAML | TOML is more human-friendly for config. YAML is the note frontmatter format — separate concerns. |
| Binary PDF | pypdf | pdfplumber | pdfplumber is more powerful but heavier. Text extraction only = pypdf is sufficient. |

---

## Installation

```bash
# Core runtime dependencies
pip install \
  typer[all]>=0.12 \
  rich>=13.0 \
  python-frontmatter>=1.1.0 \
  mistune>=3.0 \
  sqlite-utils>=3.36 \
  watchdog>=4.0 \
  anthropic>=0.28 \
  ollama>=0.2 \
  pydantic>=2.5 \
  python-dotenv>=1.0 \
  tomli-w>=1.0 \
  python-docx>=1.1 \
  python-pptx>=0.6.23 \
  pypdf>=4.0

# Dev/test dependencies
pip install \
  pytest>=8.0 \
  pytest-cov>=5.0 \
  freezegun>=1.4
```

**Pin exact versions in `requirements.txt` / `pyproject.toml` after first successful install.** Use `pip-compile` (from `pip-tools`) to generate locked `requirements.txt` from `requirements.in`.

---

## GDPR-Specific Stack Notes

**Right to erasure (`sb-forget <person>`):**
- `sqlite-utils` `db['notes'].delete_where('person_id = ?', [person_id])` removes index records.
- FTS5 index must be rebuilt after deletion: `db.populate_fts('notes')` or targeted FTS delete via raw SQL `INSERT INTO notes_fts(notes_fts, rowid, content) VALUES('delete', ?, ?)`.
- Markdown source files in `/workspace/brain/people/<person>/` must be deleted from the filesystem (Python `Path.unlink()`). This is the user's responsibility for Drive-synced content — the engine deletes them from the mounted volume.
- Audit trail: separate `audit_log` table (not FTS-indexed) recording operation, timestamp, actor. Never delete audit_log rows — the audit trail IS the evidence of erasure.

**PII routing enforcement:**
- Classification must be entirely local. Use `content_type` field in frontmatter + directory path heuristic (`people/` → always local model). NO cloud API call before classification is complete.
- `ModelRouter.route(note) -> Literal['claude', 'ollama']` is a pure function of `note.content_type` + `note.path`. No I/O.

---

## Sources

**Note:** All recommendations are based on training data (cutoff August 2025). The following should be verified against current PyPI and official documentation before pinning versions:

- python-frontmatter: https://python-frontmatter.readthedocs.io/
- sqlite-utils: https://sqlite-utils.datasette.io/en/stable/
- watchdog: https://python-watchdog.readthedocs.io/en/stable/
- Typer: https://typer.tiangolo.com/
- anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- ollama Python library: https://github.com/ollama/ollama-python
- mistune v3: https://mistune.lepture.com/en/latest/
- pypdf: https://pypdf.readthedocs.io/en/stable/
- DevContainer base images: https://mcr.microsoft.com/v2/devcontainers/python/tags/list
- pydantic v2: https://docs.pydantic.dev/latest/

**Confidence levels by area:**

| Area | Confidence | Reason |
|------|------------|--------|
| Python 3.11 + stdlib (pathlib, tomllib, sqlite3) | HIGH | Stdlib facts, release timeline verified in training data |
| Typer + Rich | HIGH | Stable, well-documented, training data consistent |
| sqlite-utils FTS5 | HIGH | Simon Willison's library, comprehensive docs, stable API |
| pytest stack | HIGH | Industry standard, no surprises |
| python-frontmatter | MEDIUM | Stable but verify 1.1.x is current |
| watchdog PollingObserver | MEDIUM | Behavior in DevContainer bind-mounts is an edge case — test required |
| anthropic SDK version | MEDIUM | Anthropic releases frequently; 0.28+ is floor, verify ceiling |
| ollama Python client | MEDIUM | Official but relatively young library; verify 0.2.x API is stable |
| DevContainer base image tag | MEDIUM | Tag naming convention stable but verify current tag list |
| pypdf (vs PyPDF2) | MEDIUM | Name change verified in training but double-check PyPI |
| mistune v3 vs markdown-it-py | LOW | Both are valid; recommendation based on subjective API preference |
