# Phase 6: Integration Gap Closure + Claude Interface Wiring - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close 5 integration wiring gaps identified in the v1.0 milestone audit. All features exist — the gaps are missing call sites and incomplete wiring. No new capabilities are added in this phase.

The five gaps:
1. **CAP-06**: `update_memory()` exists in `engine/ai.py` but is never called from `capture.py`
2. **AI-02 (watcher path)**: `watcher.py` hardcodes `get_adapter("private")` at daemon start — never classifies per-file
3. **SEARCH-01/AI-08**: `reindex.py` writes relative paths; `capture.py` writes absolute paths — RAG breaks after reindex
4. **CAP-08**: `second-brain` subagent spec exists but doesn't document all sb-* commands with usage examples
5. **CAP-09**: `~/.claude/CLAUDE.md` missing proactive capture instructions

</domain>

<decisions>
## Implementation Decisions

### Memory update scope (CAP-06)
- `update_memory()` fires for **all non-PII captures** — every note routed to ClaudeAdapter (not Ollama) triggers a memory update
- Content written: **AI-generated summary** of the captured note (not just title/date)
- Memory destination: **`~/.claude/projects/-Users-tuomasleppanen-second-brain/memory/`** — the GSD memory system, not CLAUDE.md directly
- Smart merge behavior: if a related memory entry already exists, **auto-update it silently** without asking the user; if new context is detected with no existing memory entry, **prompt the user** ("Should I add this to your second brain?")
- Failure mode: **fail silently, log warning** — memory update is best-effort; capture is the primary operation and must not be blocked

### Watcher PII fix behavior (AI-02)
- Fix scope: **all files** — both text and binary files dropped into brain/ go through `classify()` before `get_adapter()` is called. Mirrors how `capture.py` already works.
- Binary files that can't be read as text: **default to 'private' adapter, log warning** — safe default for work docs; can't classify what can't be read
- `get_adapter()` call moves from daemon startup into `on_new_file()` — resolved per-file, not per-daemon

### Reindex path fix (SEARCH-01/AI-08)
- `reindex.py:43` — replace `md_path.relative_to(brain_root)` with `md_path` (absolute path)
- Matches how `capture.py:109` already writes paths — single source of truth for path format

### Proactive capture UX (CAP-09)
- Trigger: **high-value content types only** — decisions, people discussions, meetings, project context; not casual chat or code snippets
- Offer phrasing: **"I noticed a [decision/meeting/person/project context] — capture it?"**
- Re-offer policy: **one offer per topic by default; re-offer once if significantly more detail emerges** about the same topic in the same session
- Instructions live in `~/.claude/CLAUDE.md` — not in per-project files

### Subagent spec completeness (CAP-08)
- Spec lives in **one file**: `.claude/agents/second-brain.md` (expand existing file)
- Detail level: **rich** — each command documents: what it does, its arguments, one real usage example, and which content types it's relevant to
- Coverage: **all sb-* commands** (`sb-capture`, `sb-search`, `sb-forget`, `sb-read`, `sb-check-links`) + a section documenting Claude Cowork access equivalence (same spec, same commands)
- Claude Cowork documented in the **same file** — a section noting invocation equivalence, not a separate document

### Claude's Discretion
- Exact AI-generated summary format for `update_memory()` (length, structure)
- How to detect "significantly more detail emerged" for re-offer policy
- Test coverage approach for the 5 gaps

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/ai.py:update_memory()` (line 122): function exists and tests pass — only the call site is missing
- `engine/capture.py`: already calls `classify()` before `get_adapter()` — this pattern is the model for the watcher fix
- `.claude/agents/second-brain.md`: exists, needs expansion
- `engine/adapters/`: existing adapter pattern; ClaudeAdapter and OllamaAdapter already implemented

### Established Patterns
- Atomic captures: write-then-index, rollback on failure — `update_memory()` is best-effort and outside this transaction
- PII routing: `classify()` → `get_adapter()` — already correct in `capture.py`; must be replicated in `watcher.py`
- Path convention: absolute paths in `notes.path` column — `capture.py:109` is the reference

### Integration Points
- `capture.py:main()` — add `update_memory()` call after `capture_note()` returns, guarded by `content_sensitivity != 'pii'`
- `watcher.py:on_new_file()` — add `classify()` call, move `get_adapter()` inside handler
- `reindex.py:43` — single-line fix: `str(md_path)` instead of `str(md_path.relative_to(brain_root))`
- `~/.claude/CLAUDE.md` — append proactive capture instructions block
- `.claude/agents/second-brain.md` — expand with full command reference

</code_context>

<specifics>
## Specific Ideas

- Memory update: detect existing memory entry by topic/type match before deciding to auto-update vs. prompt — avoids duplicate memory files
- Watcher fix: the `on_new_file()` fix should extract text content from binary files using the same parsers already used in the watcher (python-docx, pypdf etc.) before passing to `classify()`; if extraction fails, fallback to 'private' + warning log
- Proactive capture phrasing mirrors the existing `sb-capture` skill behavior — the CLAUDE.md instructions should reference the `second-brain` subagent as the capture mechanism

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-integration-gap-closure*
*Context gathered: 2026-03-15*
