# Phase 6: Integration Gap Closure + Claude Interface Wiring - Research

**Researched:** 2026-03-15
**Domain:** Python wiring, Claude subagent spec, filesystem configuration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Memory update scope (CAP-06)**
- `update_memory()` fires for all non-PII captures — every note routed to ClaudeAdapter triggers a memory update
- Content written: AI-generated summary of the captured note (not just title/date)
- Memory destination: `~/.claude/projects/-Users-tuomasleppanen-second-brain/memory/` — the GSD memory system
- Smart merge: if related memory entry exists, auto-update silently; if new context with no existing entry, prompt user
- Failure mode: fail silently, log warning — capture is primary and must not be blocked

**Watcher PII fix (AI-02)**
- Fix scope: all files — text and binary dropped into brain/ go through `classify()` before `get_adapter()`
- Binary files that can't be read as text: default to 'private' adapter, log warning
- `get_adapter()` call moves from daemon startup into `on_new_file()` — resolved per-file, not per-daemon

**Reindex path fix (SEARCH-01/AI-08)**
- `reindex.py:43` — replace `md_path.relative_to(brain_root)` with `md_path` (absolute path)
- Matches how `capture.py:109` already writes paths — single source of truth for path format

**Proactive capture UX (CAP-09)**
- Trigger: high-value content types only — decisions, people discussions, meetings, project context; not casual chat or code snippets
- Offer phrasing: "I noticed a [decision/meeting/person/project context] — capture it?"
- Re-offer policy: one offer per topic by default; re-offer once if significantly more detail emerges
- Instructions live in `~/.claude/CLAUDE.md` — not in per-project files

**Subagent spec completeness (CAP-08)**
- Spec lives in one file: `.claude/agents/second-brain.md` (expand existing file)
- Detail level: rich — each command documents: what it does, its arguments, one real usage example, and which content types it's relevant to
- Coverage: all sb-* commands (`sb-capture`, `sb-search`, `sb-forget`, `sb-read`, `sb-check-links`) + Claude Cowork equivalence section
- Claude Cowork documented in the same file — a section noting invocation equivalence, not a separate document

### Claude's Discretion
- Exact AI-generated summary format for `update_memory()` (length, structure)
- How to detect "significantly more detail emerged" for re-offer policy
- Test coverage approach for the 5 gaps

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAP-06 | AI automatically updates Claude memory when relevant project/people context is captured | `update_memory()` exists at `engine/ai.py:122`; call site missing in `capture.py:main()` after `capture_note()` returns; guard with `content_sensitivity != 'pii'` |
| CAP-08 | All sb-* commands invocable from Claude Code and Claude Cowork via `second-brain` subagent spec; spec documents every command with usage examples | `.claude/agents/second-brain.md` exists (21 lines); needs expansion to cover sb-search, sb-forget, sb-read, sb-check-links with args and examples |
| CAP-09 | `~/.claude/CLAUDE.md` contains proactive capture instructions — Claude asks before invoking `sb-capture` | `~/.claude/CLAUDE.md` exists (currently 4 sections, no second-brain instructions); append a new section |
| AI-02 (watcher path) | PII classifier runs before any AI API call — watcher hardcodes `get_adapter("private")` at daemon start | `watcher.py:102` is the bug; fix by moving `get_adapter()` into `on_new_file()` after `classify()` call; binary fallback to 'private' |
| SEARCH-01/AI-08 (reindex path) | `/sb-search` returns notes; RAG reads content without "[note file not readable]" fallback | `reindex.py:42-44` writes `rel_path` but `capture.py:109` (via `write_note_atomic`) writes `str(target)` (absolute); fix is one line |
</phase_requirements>

---

## Summary

Phase 6 is entirely wiring work — all five gaps are missing call sites or incomplete configurations in already-implemented, already-tested code. No new modules, no new dependencies, no new architectural patterns are required. The work is surgical: four Python file edits and one CLAUDE.md append.

The highest-risk change is CAP-06 (memory update wiring). `update_memory()` exists and has a passing test (`test_cap06_memory_update_uses_write_tool`), but the call site in `capture.py:main()` is absent. The function runs Claude CLI via `subprocess.run` with `--allowedTools Write,Read`, so it touches the filesystem. It must be placed outside the atomic transaction (after `capture_note()` returns and `conn.close()` runs), and guarded by `sensitivity != 'pii'`.

The reindex path fix is the simplest change (one line). The watcher fix is moderate (add `classify()` call, restructure `on_new_file()` to resolve adapter per file, add binary read-with-fallback). CAP-08 and CAP-09 are documentation-only changes that require no code and have no test infrastructure gap.

**Primary recommendation:** Implement in dependency order — reindex path fix first (isolated, zero risk), then watcher fix, then CAP-06 memory wiring, then CAP-08 subagent expansion, then CAP-09 CLAUDE.md append.

---

## Standard Stack

All existing. No new dependencies.

### Core (already installed)
| Module | Location | Purpose in Phase 6 |
|--------|----------|-------------------|
| `engine.ai.update_memory` | `engine/ai.py:122` | CAP-06 — function exists, needs call site |
| `engine.classifier.classify` | `engine/classifier.py:26` | AI-02 watcher fix — move inside `on_new_file()` |
| `engine.capture.capture_note` | `engine/capture.py:204` | Reference pattern for watcher to mirror |
| `engine.reindex.reindex_brain` | `engine/reindex.py:17` | SEARCH-01 — one-line path fix |
| `.claude/agents/second-brain.md` | repo root | CAP-08 — expand existing spec |
| `~/.claude/CLAUDE.md` | host filesystem | CAP-09 — append second-brain instructions block |

### No New Installs Required
All five gaps are wiring/config. `uv.lock` and `pyproject.toml` are untouched.

---

## Architecture Patterns

### Pattern 1: Capture pipeline call site (CAP-06)

`capture.py:main()` already has this structure:

```python
path = capture_note(args.note_type, args.title, args.body, tags, people, args.sensitivity, BRAIN_ROOT, conn)
conn.close()
print(str(path))
```

The `update_memory()` call inserts between `conn.close()` and `print()`:

```python
path = capture_note(...)
conn.close()
# CAP-06: best-effort memory update for non-PII captures
if sensitivity != "pii":
    from engine.ai import update_memory
    summary = f"{args.note_type} note: {args.title}"
    update_memory(args.note_type, summary, CONFIG_PATH)
print(str(path))
```

**Why after `conn.close()`:** `update_memory()` runs Claude CLI via subprocess and touches the memory filesystem. It is explicitly outside the atomic capture transaction. Running after `conn.close()` ensures the capture is fully committed before the best-effort memory update begins.

**Summary format (Claude's discretion):** `"{note_type} note: {title}"` is sufficient for the `update_memory()` call. The function itself passes this to Claude CLI which generates the memory content. Keeping the summary minimal avoids any risk of PII leaking through the title into memory (titles can contain names).

### Pattern 2: Per-file adapter resolution (AI-02 watcher fix)

Current broken pattern in `watcher.py:main()`:
```python
# BUG: adapter resolved once at daemon start — never classifies per file
adapter = router_mod.get_adapter("private", CONFIG_PATH)

def on_new_file(path: Path) -> None:
    ...
    tags_str = adapter.generate(...)
```

Fixed pattern — mirrors `capture.py`:
```python
def on_new_file(path: Path) -> None:
    from engine.classifier import classify
    # Read content for classification (text files only)
    try:
        text_content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text_content = ""
    # Classify before routing — mirrors capture.py pattern (AI-02)
    sensitivity = classify(path.suffix or "private", text_content) if text_content else "private"
    adapter = router_mod.get_adapter(sensitivity, CONFIG_PATH)
    ...
```

**Binary fallback:** If `path.read_text()` raises (binary file that can't be decoded), `text_content` stays `""` and sensitivity defaults to `"private"`. Log a warning: `print(f"[sb-watch] Cannot read {path.name} as text — defaulting to private")`.

**Important:** The outer `adapter = router_mod.get_adapter("private", CONFIG_PATH)` line at daemon start is removed entirely. The `import engine.router as router_mod` stays at the top of `main()`.

### Pattern 3: Reindex absolute path (SEARCH-01/AI-08)

`reindex.py:41-44` — current code:
```python
try:
    rel_path = str(md_path.relative_to(brain_root))
except ValueError:
    rel_path = str(md_path)
```

Fixed — use absolute path unconditionally:
```python
note_path = str(md_path)
```

The variable name also changes from `rel_path` to `note_path` (or just `str(md_path)` inline) to reflect that it's absolute. The `ON CONFLICT(path)` key in the upsert SQL remains unchanged — it's the column name, not a value.

**Why this fixes RAG:** `retrieve_context()` in `engine/rag.py` reads note bodies from disk via `Path(row["path"]).read_text()`. When `reindex` wrote relative paths, that `Path()` resolved relative to the Python process CWD (unpredictable), causing "note file not readable" fallback. Absolute paths are unambiguous.

### Pattern 4: Subagent spec expansion (CAP-08)

The existing `.claude/agents/second-brain.md` (21 lines) covers only `sb-capture`. The expansion adds four more commands. The YAML frontmatter block stays identical — only the body prose expands.

Structure for each command section:
```
## sb-<command>

**What it does:** one-line description
**Arguments:** list of flags with types
**Content types:** which note types this applies to
**Example:**
  sb-<command> [args]
```

The Claude Cowork equivalence section is a short paragraph at the end noting that all commands are available identically via Claude Cowork's Bash tool invocation.

### Pattern 5: CLAUDE.md proactive capture block (CAP-09)

`~/.claude/CLAUDE.md` currently has four sections (Git, Web/Fetching, Large command output, Learning Habit, Plan Mode). Append a new section:

```markdown
## Second Brain

When you notice high-value content in a session — a decision made, a person discussed, a meeting described, or project context established — offer once: "I noticed a [decision/meeting/person/project context] — capture it?"

If the user says yes, use the `second-brain` subagent or run directly:
  sb-capture --type <type> --title "<title>" --body "<body>" --sensitivity <level>

Content types that warrant an offer: decisions, people discussions, meeting notes, project context.
Content types that do NOT warrant an offer: casual chat, code snippets, debugging sessions, transient questions.

Re-offer policy: offer once per topic. Re-offer a second time only if significantly more detail about the same topic emerges in the same session.
```

### Anti-Patterns to Avoid

- **Calling `update_memory()` inside `capture_note()`:** `capture_note()` is also called from `watcher.py`. Memory update should only fire from the interactive `sb-capture` CLI path, not from the headless watcher.
- **Calling `update_memory()` before `conn.close()`:** Would leave the DB connection open during a 60s subprocess timeout. Capture transaction must be complete before best-effort memory update begins.
- **Putting the watcher `classify()` call on the event path (before debounce):** Classify inside `on_new_file()` only, not in `on_created()`. The debounce/batch machinery must stay unchanged.
- **Writing CLAUDE.md instructions to per-project files:** CAP-09 explicitly targets `~/.claude/CLAUDE.md` (global). Per-project CLAUDE.md would only affect that project's sessions.
- **Changing `reindex.py` to match the old relative-path behavior in `capture.py`:** The fix direction is to make reindex match capture (absolute), not the other way around.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Memory entry deduplication | Custom topic-matching logic | The `update_memory()` function already delegates to Claude CLI with `Write,Read` tools — Claude handles the merge logic |
| Binary file type detection | Custom magic-byte parser | `read_text(errors="ignore")` + empty-string check is sufficient; if content is empty, default to 'private' |
| Subagent spec validation | New test assertion | `test_subagent_frontmatter_valid()` already validates YAML keys; only need to add assertions for new command sections if desired |

---

## Common Pitfalls

### Pitfall 1: update_memory() placed inside the atomic transaction

**What goes wrong:** `conn` may be closed or the DB lock held when Claude CLI subprocess runs for 60 seconds. Capture fails or hangs.
**Why it happens:** Forgetting that `update_memory()` is best-effort and outside the transaction boundary.
**How to avoid:** Always place after `conn.close()` in `capture.py:main()`. The existing code already has a clear `conn.close()` then `print()` sequence — insert between them.
**Warning signs:** Test hangs, or `update_memory()` test mocking doesn't intercept if placed in wrong scope.

### Pitfall 2: Watcher test breaks due to `on_new_file` closure capturing old `adapter`

**What goes wrong:** `test_main_on_new_file_no_input_on_ai_failure` in `test_watcher.py` manually constructs the `on_new_file` closure that mirrors `main()`. If the closure shape changes (adapter now resolved per-file instead of captured from outer scope), the test's manually-constructed closure must also be updated to match.
**Why it happens:** The test constructs a closure that replicates `main()`'s logic — it's not testing `main()` directly.
**How to avoid:** Update the test's closure to match the new per-file adapter resolution pattern when fixing `watcher.py:main()`.

### Pitfall 3: Reindex test `test_reindex_parses_frontmatter_fields` asserts on `path='typed.md'` (relative)

**What goes wrong:** After the reindex fix, the path stored in DB is absolute (`/tmp/.../typed.md`), not relative. The test assertion `WHERE path='typed.md'` will return no row and the test will fail.
**Why it happens:** The existing test was written expecting relative paths — it's testing the current (broken) behavior.
**How to avoid:** Update `test_reindex.py` assertions to check `path LIKE '%typed.md'` or extract the path from the result set rather than querying by exact relative path. Also update `test_reindex_idempotent` which relies on the `ON CONFLICT(path)` key matching.

### Pitfall 4: CAP-09 CLAUDE.md append duplicates existing sections

**What goes wrong:** Running the append twice creates a duplicate "Second Brain" section in `~/.claude/CLAUDE.md`.
**Why it happens:** No idempotency guard on a plain file append.
**How to avoid:** The plan task should check for the presence of "## Second Brain" before appending. A simple `if "Second Brain" not in content` guard is sufficient.

### Pitfall 5: Subagent spec test `test_subagent_frontmatter_valid` checks keys only

**What goes wrong:** Adding body content to `second-brain.md` doesn't break the existing test, but the test won't verify that all five commands are documented. If the planner wants test coverage for CAP-08, a new assertion is needed.
**Why it happens:** Existing test was written for Phase 3 (minimal spec). CAP-08 requires richer content.
**How to avoid:** Add a new test `test_subagent_documents_all_commands` that checks for each `sb-*` command string in the file body. This is CLAUDE's discretion per CONTEXT.md.

---

## Code Examples

### CAP-06: Call site in capture.py:main()

```python
# After capture_note() and conn.close(), before print()
path = capture_note(args.note_type, args.title, args.body, tags, people, args.sensitivity, BRAIN_ROOT, conn)
conn.close()

# CAP-06: best-effort memory update — outside transaction, never blocks capture
if sensitivity != "pii":
    try:
        from engine.ai import update_memory
        update_memory(args.note_type, f"{args.note_type} note: {args.title}", CONFIG_PATH)
    except Exception as e:
        print(f"[sb-capture] Memory update skipped: {type(e).__name__}")

print(str(path))
```

Note: `sensitivity` is already bound earlier in `main()` from `classify(args.sensitivity, args.body)`.

### AI-02: on_new_file() with per-file classification

```python
def on_new_file(path: Path) -> None:
    print(f"[sb-watch] Detected: {path.name}")
    # Read content for PII classification (AI-02) — best-effort text extraction
    try:
        text_content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text_content = ""
        print(f"[sb-watch] Cannot read {path.name} as text — defaulting to private")
    # Classify before adapter selection — mirrors capture.py (AI-02)
    from engine.classifier import classify
    sensitivity = classify("private", text_content) if text_content else "private"
    adapter = router_mod.get_adapter(sensitivity, CONFIG_PATH)
    title = path.stem.replace("-", " ").replace("_", " ").title()
    try:
        tags_str = adapter.generate(
            user_content=f"File: {path.name}",
            system_prompt="Suggest 2-3 comma-separated tags for this file. Output only the tags.",
        )
        tags = [t.strip() for t in tags_str.split(",") if t.strip()][:3]
    except Exception as e:
        print(f"[sb-watch] AI tagging skipped: {type(e).__name__}")
        tags = []
    conn = get_connection()
    init_schema(conn)
    try:
        note_path = capture_note("note", title, f"File: {path}", tags, [], sensitivity, BRAIN_ROOT, conn)
        print(f"[sb-watch] Captured: {path.name} -> {note_path.name}")
    except Exception as e:
        print(f"[sb-watch] Failed to capture {path.name}: {type(e).__name__}: {e}")
    finally:
        conn.close()
```

The outer `adapter = router_mod.get_adapter("private", CONFIG_PATH)` line in `main()` is deleted.

### SEARCH-01: reindex.py path fix (one line)

```python
# BEFORE (line 42-44):
try:
    rel_path = str(md_path.relative_to(brain_root))
except ValueError:
    rel_path = str(md_path)

# AFTER:
note_path = str(md_path)
```

All subsequent references to `rel_path` in the `conn.execute()` call become `note_path`.

---

## State of the Art

| Old State | Fixed State | Gap |
|-----------|-------------|-----|
| `watcher.py` resolves adapter once at daemon start | Resolves per-file inside `on_new_file()` after `classify()` | AI-02 watcher path |
| `reindex.py` writes `notes/note.md` (relative) | Writes `/Users/.../SecondBrain/notes/note.md` (absolute) | SEARCH-01/AI-08 path mismatch |
| `capture.py:main()` never calls `update_memory()` | Calls after `conn.close()`, guarded by `!= 'pii'` | CAP-06 missing call site |
| `second-brain.md` documents only `sb-capture` (21 lines) | Documents all 5 sb-* commands + Cowork equivalence | CAP-08 incomplete spec |
| `~/.claude/CLAUDE.md` has no second-brain section | Has "## Second Brain" proactive capture block | CAP-09 missing instructions |

---

## Open Questions

1. **`update_memory()` summary format**
   - What we know: function accepts `(note_type, summary, config_path)`; summary is passed as `user_content` to Claude CLI
   - What's unclear: optimal summary length — too short loses context, too long risks leaking title PII into memory
   - Recommendation (Claude's discretion): `f"{note_type} note: {title}"` — type gives category context, title is the minimum identifier. Claude CLI generates the actual memory bullet points from this.

2. **Test for CAP-08 subagent completeness**
   - What we know: existing `test_subagent_frontmatter_valid` checks YAML keys only
   - What's unclear: whether a content-coverage test should be added
   - Recommendation: Add `test_subagent_documents_all_commands` that asserts each of `sb-capture`, `sb-search`, `sb-forget`, `sb-read`, `sb-check-links` appears in the file. Simple string membership check, no YAML parsing needed.

3. **`test_watcher.py:test_main_on_new_file_no_input_on_ai_failure` must be updated**
   - What we know: test manually reconstructs the `on_new_file` closure — its shape must match `main()`'s new closure
   - What's unclear: whether the test should also verify PII routing (OllamaAdapter returned for pii content)
   - Recommendation: Update the manual closure to match new per-file adapter resolution. Add a separate `test_watcher_pii_routes_to_ollama` test that patches `classify` to return `"pii"` and asserts `get_adapter` was called with `"pii"`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --no-project --with pytest pytest tests/test_ai.py tests/test_watcher.py tests/test_reindex.py tests/test_subagent.py -x` |
| Full suite command | `uv run --no-project --with pytest pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAP-06 | `update_memory()` called after non-PII capture | unit | `pytest tests/test_capture.py::test_cap06_update_memory_called_after_capture -x` | Wave 0 |
| CAP-06 | `update_memory()` NOT called for PII captures | unit | `pytest tests/test_capture.py::test_cap06_update_memory_skipped_for_pii -x` | Wave 0 |
| AI-02 (watcher) | PII file routes to OllamaAdapter, not ClaudeAdapter | unit | `pytest tests/test_watcher.py::test_watcher_pii_routes_to_ollama -x` | Wave 0 |
| AI-02 (watcher) | Binary unreadable file defaults to 'private' adapter | unit | `pytest tests/test_watcher.py::test_watcher_binary_fallback_to_private -x` | Wave 0 |
| SEARCH-01/AI-08 | After reindex, paths stored are absolute | unit | `pytest tests/test_reindex.py::test_reindex_stores_absolute_paths -x` | Wave 0 |
| CAP-08 | All 5 sb-* commands present in subagent spec | unit | `pytest tests/test_subagent.py::test_subagent_documents_all_commands -x` | Wave 0 |
| CAP-09 | `~/.claude/CLAUDE.md` contains "Second Brain" section | manual | Manual inspection of `~/.claude/CLAUDE.md` | manual-only |

CAP-09 is manual-only because `~/.claude/CLAUDE.md` lives outside the repo and cannot be reliably tested in CI without host filesystem access assumptions.

### Sampling Rate
- **Per task commit:** `uv run --no-project --with pytest pytest tests/test_ai.py tests/test_watcher.py tests/test_reindex.py tests/test_subagent.py tests/test_capture.py -x`
- **Per wave merge:** `uv run --no-project --with pytest pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_capture.py` — add `test_cap06_update_memory_called_after_capture` and `test_cap06_update_memory_skipped_for_pii`
- [ ] `tests/test_watcher.py` — add `test_watcher_pii_routes_to_ollama` and `test_watcher_binary_fallback_to_private`; update `test_main_on_new_file_no_input_on_ai_failure` closure shape
- [ ] `tests/test_reindex.py` — add `test_reindex_stores_absolute_paths`; update `test_reindex_parses_frontmatter_fields` path assertion from exact relative match to `LIKE '%typed.md'`; update `test_reindex_idempotent` similarly
- [ ] `tests/test_subagent.py` — add `test_subagent_documents_all_commands`

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `engine/ai.py`, `engine/capture.py`, `engine/watcher.py`, `engine/reindex.py`, `engine/classifier.py` — all implementation details verified from source
- Direct code inspection: `tests/test_ai.py`, `tests/test_watcher.py`, `tests/test_reindex.py`, `tests/test_subagent.py`, `tests/conftest.py` — all test patterns verified from source
- `.claude/agents/second-brain.md` — current spec content verified
- `~/.claude/CLAUDE.md` — current content verified (no second-brain section present)
- `.planning/phases/06-integration-gap-closure/06-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` accumulated decisions — corroborates patterns (Phase 03 entry: "CAP-06 memory update path confirmed in ClaudeAdapter (03-03)")

### Tertiary (LOW confidence)
- None required — all claims are verified from source code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code verified from source, no external dependencies
- Architecture: HIGH — all patterns derived from existing working code (capture.py is the reference implementation for all wiring patterns)
- Pitfalls: HIGH — all pitfalls identified from direct test inspection (test_reindex relative path assertion, test_watcher closure shape)

**Research date:** 2026-03-15
**Valid until:** Stable indefinitely — no external libraries, all internal code
