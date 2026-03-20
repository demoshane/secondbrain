# Phase 7: Fix Path Format Split - Research

**Researched:** 2026-03-15
**Domain:** SQLite path storage consistency, Python pathlib, pytest unit testing
**Confidence:** HIGH

---

## Summary

Phase 7 is a surgical, one-line bug fix. `engine/capture.py:write_note_atomic()` stores the note path into SQLite as `str(target)`, which resolves to whatever the caller passed — a relative-looking path when `target` is constructed from `BRAIN_ROOT` (an absolute Path) joined with subdirectory parts. However `pathlib.Path.__str__()` on an absolute `Path` already returns the absolute string, so the bug manifests differently: `target` is already absolute at call-site, so `str(target)` should be correct *in production*. The audit evidence is precise: reindex stores `str(md_path)` (also already absolute from `rglob`), and both should match. The actual mismatch appears to be a historical decision that was later reversed — the Phase 06 decision log records "Store str(md_path) absolute path in reindex — not relative_to(brain_root)". This implies capture was *at some point* storing `str(target.relative_to(brain_root))` or a non-resolved variant. Checking the live `capture.py` source confirms line 110 is `str(target)` — which is already an absolute path when `target = brain_root / subdir / f"{slug}.md"` and `brain_root` is absolute. The fix needed is `str(target.resolve())` to guarantee canonicalization even if `brain_root` contains symlinks or is itself a relative path in tests.

The downstream consumers — `rag.py:retrieve_context()` and `forget.py:forget_person()` — both use the stored path string directly: RAG calls `Path(r["path"]).read_text()`, and forget builds `exact_delete_paths` from `str(brain_root / "people" / f"{slug}.md")`. If `brain_root` is a `tmp_path` symlink and capture stored a non-resolved path while forget builds a resolved path (or vice versa), the exact-match DELETE misses the row. `target.resolve()` eliminates this class of failure.

**Primary recommendation:** Change `str(target)` to `str(target.resolve())` on the single line in `write_note_atomic()` (line 110) and the matching audit log call (line 121, `str(target)` — though that path is cosmetic). Verify with three new tests: one confirming absolute path in DB after capture, one confirming RAG reads the file without fallback, one confirming forget deletes the row when `brain_root` is accessed via symlink.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEARCH-01 | `/sb-search` performs FTS5 BM25 search across all notes | Path fix ensures newly captured notes are found and their files are readable post-search |
| SEARCH-04 | AI queries retrieve relevant notes via FTS5 as RAG context | `rag.py:retrieve_context()` calls `Path(r["path"]).read_text()` — absolute/resolved path in DB prevents FileNotFoundError |
| GDPR-01 | `/sb-forget <person>` fully erases person's data | `forget.py` builds exact-match DELETE paths from `brain_root` — path must match what capture stored; `.resolve()` on both sides makes them consistent |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib.Path | stdlib | Path construction and resolution | Already used throughout engine per FOUND-12 |
| sqlite3 | stdlib | DB path storage and retrieval | Already the project's database layer |
| pytest + tmp_path | stdlib / 8.x | Hermetic path tests | Established test pattern in this codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-frontmatter | installed | Read/write note files in tests | Same as existing capture tests |

**Installation:** No new dependencies. Fix is entirely within existing stdlib and project code.

---

## Architecture Patterns

### Recommended Project Structure
No structural change. Single file edit:
```
engine/
└── capture.py        # write_note_atomic(): str(target) → str(target.resolve())
tests/
└── test_capture.py   # 2 new tests: absolute path stored, path is resolved
tests/
└── test_rag.py       # 1 new test: retrieve_context reads file without fallback
tests/
└── test_forget.py    # 1 new test: forget deletes row when path stored via capture
```

### Pattern 1: Path Resolution at Storage Time

**What:** Resolve the path to its canonical absolute form at the moment of DB INSERT, not at read time. All consumers (RAG, forget, search) receive a path they can use directly without knowing `brain_root`.

**When to use:** Any time a filesystem path is stored in a database for later retrieval by a different code path.

**Example:**
```python
# Before (in write_note_atomic, line 110):
str(target)

# After:
str(target.resolve())
```

The `Path.resolve()` call:
- Resolves symlinks in the path
- Makes relative paths absolute (using cwd)
- Is idempotent — calling it on an already-absolute, non-symlink path is a no-op with no performance cost
- Source: Python stdlib pathlib docs (HIGH confidence, stdlib)

### Pattern 2: Forget Path Consistency

**What:** `forget_person()` constructs `person_path = str(brain_root / "people" / f"{slug}.md")`. If `brain_root` contains unresolved symlinks and capture stored `target.resolve()`, these will not match. The fix is to also resolve in forget, or — simpler — rely on capture always storing resolved paths so forget's construction matches when `brain_root` is itself already resolved (which it is in production: `BRAIN_ROOT` is set from an absolute env var).

**When to use:** Verify that `forget.py` path construction matches the resolved capture path in the symlink edge case. In practice, `BRAIN_ROOT` production value does not contain symlinks, but `tmp_path` in tests often does (macOS `/var/folders` → `/private/var/folders`).

**Example:**
```python
# In test: brain_root may be /var/folders/.../brain (symlink)
# capture stores: str(target.resolve()) → /private/var/folders/.../brain/people/alice-smith.md
# forget builds:  str(brain_root / "people" / "alice-smith.md") → /var/folders/.../brain/people/alice-smith.md
# These do NOT match → DELETE silently misses the row

# Fix: ensure forget also resolves, OR (preferred) write a test that uses
# resolved brain_root so both sides agree. Production BRAIN_ROOT is already
# resolved; the test fixture needs updating.
```

### Anti-Patterns to Avoid

- **Resolving at read time instead of write time:** RAG and forget would each need their own resolution logic — fragile and easy to miss in future code paths.
- **Using `str(target.absolute())` instead of `str(target.resolve())`:** `absolute()` does not resolve symlinks; only `resolve()` does.
- **Patching `forget.py` to also resolve paths:** Adds complexity in the wrong place. Single source of truth: store resolved at capture time, all consumers read as-is.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symlink resolution | Custom symlink-walking code | `Path.resolve()` | stdlib handles all edge cases including circular symlinks |
| Path normalization | `os.path.normpath` / string manipulation | `Path.resolve()` | resolve() also handles `..` traversal, not just symlinks |
| DB path comparison | LIKE or GLOB queries | Exact-match `WHERE path = ?` with resolved paths | Already the established pattern in forget.py (Pitfall 5) |

---

## Common Pitfalls

### Pitfall 1: `tmp_path` Symlink on macOS

**What goes wrong:** On macOS, `pytest`'s `tmp_path` returns a path under `/var/folders/...` which is a symlink to `/private/var/folders/...`. If capture calls `target.resolve()`, it stores the `/private/var/...` form. If a test then builds `str(brain_root / "people" / slug)` using the original `tmp_path`, the strings differ and exact-match DB queries fail.

**Why it happens:** macOS `/tmp` and `/var` are symlinks to `/private/tmp` and `/private/var`. Python's `tmp_path` returns the unresolved form.

**How to avoid:** In new tests that verify path matching, construct `brain_root` as `tmp_path.resolve()` OR derive all expected paths via `(brain_root / subdir / file).resolve()` for comparison. Do not hardcode `str(tmp_path / ...)` as the expected DB value.

**Warning signs:** Test passes on Linux CI but fails on macOS developer machine; `assert db_path == str(tmp_path / "people" / "alice.md")` fails.

### Pitfall 2: `str(target)` Already Absolute — Subtle Non-Bug

**What goes wrong:** A reviewer may argue "capture already stores an absolute path because `brain_root` is absolute, so the fix is a no-op." This is true in production but false in the symlink case and in tests where `brain_root` may be unresolved.

**Why it happens:** `pathlib.Path` being "absolute" (starts with `/`) is not the same as being "resolved" (all symlinks followed).

**How to avoid:** The fix is still correct and necessary. Document in the commit message why `.resolve()` is needed over `.absolute()`.

### Pitfall 3: Audit Log Path Inconsistency

**What goes wrong:** `log_audit(conn, "create", str(target))` is called with the pre-resolve path on line 121. If we fix line 110 with `str(target.resolve())` but leave line 121 as `str(target)`, the audit log records a different path than the notes table. GDPR audit queries joining audit_log to notes by path would miss entries.

**How to avoid:** Update both the INSERT on line 110 and the `log_audit` call on line 121 to use the same resolved path string. Extract to a local variable: `resolved_path = str(target.resolve())`, use for both.

### Pitfall 4: Test Isolation — Existing `test_capture.py` Tests

**What goes wrong:** Existing capture tests (`test_capture_writes_note`, etc.) check `target.exists()` and frontmatter content but do NOT assert the DB path value. They will continue to pass after the fix. The new tests must assert the DB value explicitly.

**How to avoid:** New Wave 0 test stubs must query `SELECT path FROM notes WHERE title = ?` and assert the result equals `str(target.resolve())`.

---

## Code Examples

### Current Broken Code (capture.py lines 106-121)
```python
# Source: /engine/capture.py — confirmed from file read
conn.execute(
    "INSERT INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (
        str(target),          # BUG: may not be resolved if brain_root contains symlinks
        ...
    ),
)
log_audit(conn, "create", str(target))  # BUG: same path, also not resolved
```

### Fixed Code Pattern
```python
# Extract resolved path once, use for both INSERT and audit
resolved_path = str(target.resolve())

conn.execute(
    "INSERT INTO notes (path, ...) VALUES (?, ...)",
    (
        resolved_path,        # FIX: canonical absolute path, symlinks resolved
        ...
    ),
)
log_audit(conn, "create", resolved_path)  # FIX: consistent with notes table
```

### RAG Read (rag.py lines 30-34) — No Change Required
```python
# Source: /engine/rag.py — confirmed from file read
note_path = Path(r["path"])
try:
    body = note_path.read_text(encoding="utf-8")[:_BODY_TRUNCATE]
except OSError:
    body = "[note file not readable]"
# With resolved path stored, Path(r["path"]).read_text() will work directly.
```

### Forget Exact-Match Delete (forget.py lines 48-51) — No Change Required in Production
```python
# Source: /engine/forget.py — confirmed from file read
person_path = str(brain_root / "people" / f"{slug}.md")
# In production: brain_root = BRAIN_ROOT which is already absolute and non-symlink.
# In tests: must use brain_root.resolve() to match what capture stores.
```

### Test Pattern for New Absolute-Path Assertion
```python
def test_write_note_atomic_stores_absolute_path(tmp_path, initialized_db):
    from engine.capture import write_note_atomic, build_post

    target_dir = tmp_path.resolve() / "notes"
    target_dir.mkdir()
    target = target_dir / "2026-test-note.md"

    post = build_post("note", "Test Note", "body", [], [], "public")
    write_note_atomic(target, post, initialized_db)

    row = initialized_db.execute(
        "SELECT path FROM notes WHERE title = ?", ("Test Note",)
    ).fetchone()
    assert row is not None
    stored_path = row[0]
    assert stored_path == str(target.resolve())
    assert stored_path.startswith("/"), "DB path must be absolute"
```

### Test Pattern for RAG Path Resolution
```python
def test_retrieve_context_reads_file_for_captured_note(tmp_path, initialized_db):
    from engine.capture import capture_note
    from engine.rag import retrieve_context

    brain_root = tmp_path.resolve() / "brain"
    for subdir in ("notes", "meetings", "people"):
        (brain_root / subdir).mkdir(parents=True)

    capture_note("note", "Unique RAG Topic", "content about rag resolution",
                 [], [], "public", brain_root, initialized_db)

    context = retrieve_context("rag resolution", initialized_db)
    assert "[note file not readable]" not in context
    assert "content about rag resolution" in context or context != ""
```

### Test Pattern for Forget After Capture
```python
def test_forget_removes_row_stored_by_capture(tmp_path, initialized_db):
    from engine.capture import capture_note
    from engine.forget import forget_person

    brain_root = tmp_path.resolve() / "brain"
    for subdir in ("notes", "meetings", "people"):
        (brain_root / subdir).mkdir(parents=True)

    capture_note("people", "Alice Smith", "profile body",
                 [], [], "public", brain_root, initialized_db)

    forget_person("alice-smith", brain_root, initialized_db)

    row = initialized_db.execute(
        "SELECT 1 FROM notes WHERE title = ?", ("Alice Smith",)
    ).fetchone()
    assert row is None, "forget_person must delete row stored by capture"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `str(target)` in capture INSERT | `str(target.resolve())` | Phase 7 (this fix) | RAG FileNotFoundError and forget silent-miss eliminated |
| `str(md_path)` in reindex (already absolute) | unchanged | Phase 6 (06-01-PLAN.md) | reindex was fixed first; capture lagged behind |

**Deprecated/outdated:**
- Any test that seeds the DB with relative paths like `"notes/note_0001.md"` (see `conftest.py:seeded_db`) is a perf/search test only — those are not a regression target for this fix; they test BM25 ranking, not path resolution.

---

## Open Questions

1. **Does `forget.py` need updating for the symlink case in production?**
   - What we know: production `BRAIN_ROOT` is an absolute, non-symlink path (set from `~/.config/second-brain/`). `str(brain_root / "people" / slug)` in forget will equal `str(target.resolve())` from capture because neither contains symlinks.
   - What's unclear: if a user symlinks `~/SecondBrain` → `/data/brain`, would `BRAIN_ROOT` be resolved or not?
   - Recommendation: do not change `forget.py` for now. The fix in `capture.py` is sufficient for the stated failure mode. Add a note in the plan to revisit if BRAIN_ROOT symlink usage surfaces.

2. **Should `log_audit` path also be resolved?**
   - What we know: audit log path is cosmetic for display; GDPR-01 only requires deletion of rows by exact path match, which this plan fixes at the notes table level.
   - What's unclear: whether future queries will join audit_log to notes by path.
   - Recommendation: YES — resolve in both INSERT and log_audit call using a shared `resolved_path` local variable. Zero extra cost, prevents future inconsistency.

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run --no-project --with pytest pytest tests/test_capture.py tests/test_rag.py tests/test_forget.py -x -q` |
| Full suite command | `uv run --no-project --with pytest pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEARCH-01 | `write_note_atomic` stores absolute resolved path in DB | unit | `pytest tests/test_capture.py::test_write_note_atomic_stores_absolute_path -x` | Wave 0 |
| SEARCH-01 | Stored path starts with `/` (is absolute, not relative) | unit | `pytest tests/test_capture.py::test_write_note_atomic_path_is_absolute -x` | Wave 0 |
| SEARCH-04 | `retrieve_context` reads file without `[note file not readable]` fallback for note just captured | unit | `pytest tests/test_rag.py::test_retrieve_context_reads_captured_note -x` | Wave 0 |
| GDPR-01 | `forget_person` deletes DB row for note stored by `capture_note` (no reindex in between) | unit | `pytest tests/test_forget.py::test_forget_removes_row_stored_by_capture -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run --no-project --with pytest pytest tests/test_capture.py tests/test_rag.py tests/test_forget.py -x -q`
- **Per wave merge:** `uv run --no-project --with pytest pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_capture.py::test_write_note_atomic_stores_absolute_path` — covers SEARCH-01 (path value in DB)
- [ ] `tests/test_capture.py::test_write_note_atomic_path_is_absolute` — covers SEARCH-01 (path format guard)
- [ ] `tests/test_rag.py::test_retrieve_context_reads_captured_note` — covers SEARCH-04
- [ ] `tests/test_forget.py::test_forget_removes_row_stored_by_capture` — covers GDPR-01

All 4 tests are new stubs to add in Wave 0. Existing test files exist; only new test functions are needed.

---

## Sources

### Primary (HIGH confidence)
- Python stdlib pathlib docs — `Path.resolve()` behavior, symlink resolution, difference from `absolute()`
- `/Users/tuomasleppanen/second-brain/engine/capture.py` — confirmed `str(target)` on line 110
- `/Users/tuomasleppanen/second-brain/engine/reindex.py` — confirmed `str(md_path)` (already absolute)
- `/Users/tuomasleppanen/second-brain/engine/rag.py` — confirmed `Path(r["path"]).read_text()` call
- `/Users/tuomasleppanen/second-brain/engine/forget.py` — confirmed exact-path DELETE pattern
- `/Users/tuomasleppanen/second-brain/.planning/v1.5-MILESTONE-AUDIT.md` — audit root cause analysis
- `/Users/tuomasleppanen/second-brain/.planning/STATE.md` — Phase 6 decision: "Store str(md_path) absolute path in reindex"

### Secondary (MEDIUM confidence)
- macOS `/var` → `/private/var` symlink behavior: well-known macOS characteristic, consistent with observed pytest `tmp_path` behavior

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new dependencies
- Architecture: HIGH — single-line fix with confirmed call sites from source reading
- Pitfalls: HIGH — macOS symlink trap is a known pytest gotcha; confirmed from source code analysis

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stdlib change risk: negligible)
