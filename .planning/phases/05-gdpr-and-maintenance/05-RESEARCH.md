# Phase 5: GDPR and Maintenance - Research

**Researched:** 2026-03-14
**Domain:** SQLite FTS5 content-addressed deletion, passphrase access control, Python CLI
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GDPR-01 | `/sb-forget <person>` deletes: person's markdown file, all meeting notes that reference ONLY that person, FTS5 shadow table entries (explicit purge), audit log entries, backlinks in other notes | Erasure cascade pattern documented; FTS5 content table delete trigger already in schema |
| GDPR-02 | After `/sb-forget`, FTS5 index is rebuilt (`INSERT INTO notes_fts(notes_fts) VALUES('rebuild')`) to ensure no content fragments remain | Rebuild call already exists in `reindex.py:reindex_brain()`; must be replicated in forget module |
| GDPR-04 | Access control: notes with `content_sensitivity: pii` require passphrase confirmation before displaying content in CLI | `getpass.getpass()` pattern; passphrase stored in `.env.host`; check in display path only |
</phase_requirements>

---

## Summary

Phase 5 implements two fully independent features: (1) a right-to-erasure cascade via `sb-forget`, and (2) a passphrase gate on PII note display via `sb-read`. Both are greenfield additions — no existing engine module needs modification, only extension via new modules and entry points.

The erasure cascade is the harder of the two. FTS5 with `content=notes` is a "content table" configuration — the shadow tables (`%_data`, `%_idx`, `%_docsize`, `%_config`, `%_content`) do NOT store full text redundantly in normal operation, but FTS5 does maintain a docsize and term-frequency index. The `notes_ad` trigger in `db.py` already emits the correct FTS5 delete signal when a row is removed from `notes`. However the `notes_fts` shadow tables can retain stale segments until a merge or explicit rebuild. GDPR-02 mandates the explicit rebuild after every forget, which flushes all segments. This pattern is already proven in `reindex.py`.

The passphrase gate for GDPR-04 is a display-time guard only. The `sensitivity` column is already stored in the `notes` table and populated from `content_sensitivity` frontmatter. The gate reads the passphrase from the environment (`.env.host` sets `SB_PII_PASSPHRASE`) and uses `getpass.getpass()` as the interactive prompt. No encryption is added in v1 — content is stored in plaintext; the gate is an access-confirmation UX control, not cryptographic protection.

**Primary recommendation:** Implement `engine/forget.py` (erasure cascade + FTS5 rebuild) and `engine/read.py` (display with PII gate). Wire both as new CLI entry points `sb-forget` and `sb-read` in `pyproject.toml`. New test file `tests/test_gdpr.py` covers all three requirements.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | stdlib | DB deletion, FTS5 rebuild | Already used throughout codebase |
| `python-frontmatter` | >=1.0 | Read people list from meeting notes to detect sole-reference | Already a dependency |
| `getpass` | stdlib | Passphrase prompt without echo | Standard secure input on all platforms |
| `os.environ` | stdlib | Read `SB_PII_PASSPHRASE` from `.env.host`-injected env | Consistent with existing secrets pattern |
| `pathlib.Path` | stdlib | All file operations (FOUND-12 enforced) | Hard project constraint |

### No New Dependencies
Phase 5 requires zero new `pyproject.toml` dependencies. Everything is already present.

**Installation:**
```bash
# No new packages needed
uv sync
```

---

## Architecture Patterns

### Recommended Module Structure
```
engine/
├── forget.py        # GDPR-01 + GDPR-02: erasure cascade + FTS5 rebuild
├── read.py          # GDPR-04: note display with PII passphrase gate
tests/
├── test_gdpr.py     # all three requirements, Wave 0 stubs → Wave 1 passing
```

### Pattern 1: Erasure Cascade (GDPR-01)

**What:** `forget_person(person_slug, brain_root, conn)` — one function, strict deletion order.

**Deletion order matters** (FK-safe even without FK enforcement):
1. Delete `relationships` rows where `source_path` or `target_path` contains the person slug.
2. Remove backlink lines from any note that references the person file.
3. Identify sole-reference meeting notes: meeting files whose `people` frontmatter list, after removing the target person, is empty.
4. Delete sole-reference meeting files from disk.
5. Delete the person's markdown file from disk.
6. `DELETE FROM notes WHERE path LIKE '%<slug>%'` — removes person row and sole-reference meeting rows from DB; `notes_ad` trigger fires and emits FTS5 delete signals.
7. Delete audit log entries for the person's path.
8. Execute `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` — GDPR-02.
9. `conn.commit()`.
10. Append `forget` event to audit log (GDPR-03 compliance — we log the erasure itself, not the erased content).

**When to use:** Called exclusively by `sb-forget` CLI entry point.

**Example:**
```python
# engine/forget.py
import frontmatter
import json
from pathlib import Path
import sqlite3

def forget_person(slug: str, brain_root: Path, conn: sqlite3.Connection) -> dict:
    """Erase all traces of a person from brain and index.

    Returns dict: {deleted_files: list[str], cleaned_backlinks: list[str], errors: list[str]}
    """
    person_file = brain_root / "people" / f"{slug}.md"
    deleted_files = []
    cleaned_backlinks = []
    errors = []

    # 1. Find sole-reference meeting notes
    meetings_dir = brain_root / "meetings"
    sole_ref_meetings: list[Path] = []
    if meetings_dir.exists():
        for md in meetings_dir.glob("*.md"):
            try:
                post = frontmatter.load(str(md))
                people = post.get("people", [])
                # Normalize: remove target person
                remaining = [
                    p for p in people
                    if p.strip().lower().replace(" ", "-") != slug
                ]
                if len(people) > 0 and len(remaining) == 0:
                    sole_ref_meetings.append(md)
            except Exception as e:
                errors.append(f"Could not parse {md}: {type(e).__name__}")

    # 2. Remove backlink lines from notes that reference person file
    for md in brain_root.rglob("*.md"):
        if md == person_file or md in sole_ref_meetings:
            continue
        try:
            text = md.read_text(encoding="utf-8")
            if slug in text:
                new_text = "\n".join(
                    line for line in text.splitlines()
                    if slug not in line
                )
                md.write_text(new_text, encoding="utf-8")
                cleaned_backlinks.append(str(md))
        except Exception as e:
            errors.append(f"Could not clean {md}: {type(e).__name__}")

    # 3. Delete sole-reference meeting files
    for md in sole_ref_meetings:
        try:
            md.unlink()
            deleted_files.append(str(md))
        except Exception as e:
            errors.append(f"Could not delete {md}: {type(e).__name__}")

    # 4. Delete person file
    if person_file.exists():
        try:
            person_file.unlink()
            deleted_files.append(str(person_file))
        except Exception as e:
            errors.append(f"Could not delete person file: {type(e).__name__}")

    # 5. Remove from DB (notes_ad trigger fires FTS5 delete signals)
    person_path_pattern = f"%{slug}%"
    conn.execute("DELETE FROM notes WHERE path LIKE ?", (person_path_pattern,))

    # 6. Remove relationships
    conn.execute(
        "DELETE FROM relationships WHERE source_path LIKE ? OR target_path LIKE ?",
        (person_path_pattern, person_path_pattern),
    )

    # 7. Remove audit log entries for this person (erasure of personal data records)
    conn.execute("DELETE FROM audit_log WHERE note_path LIKE ?", (person_path_pattern,))

    # 8. FTS5 explicit rebuild (GDPR-02) — flushes all shadow table segments
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    # 9. Log the erasure event itself (we record that erasure happened, not what was erased)
    import datetime
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        ("forget", None, f"person:{slug}", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()

    return {"deleted_files": deleted_files, "cleaned_backlinks": cleaned_backlinks, "errors": errors}


def main() -> None:
    """CLI entry point for sb-forget."""
    import argparse
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT

    parser = argparse.ArgumentParser(description="Erase all traces of a person (GDPR right to erasure)")
    parser.add_argument("person", help="Person slug (e.g. 'alice-smith') or name (e.g. 'Alice Smith')")
    args = parser.parse_args()

    slug = args.person.strip().lower().replace(" ", "-")

    conn = get_connection()
    init_schema(conn)
    result = forget_person(slug, BRAIN_ROOT, conn)
    conn.close()

    print(f"Deleted {len(result['deleted_files'])} file(s):")
    for f in result["deleted_files"]:
        print(f"  - {f}")
    print(f"Cleaned backlinks in {len(result['cleaned_backlinks'])} note(s).")
    if result["errors"]:
        print(f"Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  ! {e}")
    print("FTS5 index rebuilt. Erasure complete.")
```

### Pattern 2: PII Passphrase Gate (GDPR-04)

**What:** `read_note(path, conn)` — reads frontmatter, checks `content_sensitivity`. If `pii`, prompt for passphrase before printing body.

**Passphrase source:** `os.environ.get("SB_PII_PASSPHRASE", "")` — set in `.env.host`. If env var is empty, fall back to `getpass.getpass()` prompt. This matches the existing `.env.host` injection pattern.

**When to use:** `sb-read <path>` entry point. The capture and search commands never display body content — only `sb-read` does. Gate is display-time only.

**Example:**
```python
# engine/read.py
import getpass
import os
import sys
from pathlib import Path
import sqlite3
import frontmatter


_ACCESS_DENIED = "Access denied: passphrase required for PII note."


def read_note(path: Path, conn: sqlite3.Connection) -> int:
    """Display note content, gating PII notes behind passphrase.

    Returns 0 on success, 1 on access denied.
    Error messages never include note content (GDPR-05).
    """
    if not path.exists():
        print(f"Note not found: {path.name}", file=sys.stderr)
        return 1

    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        print(f"Could not read note: {type(e).__name__}", file=sys.stderr)
        return 1

    sensitivity = post.get("content_sensitivity", "public")

    if sensitivity == "pii":
        expected = os.environ.get("SB_PII_PASSPHRASE", "")
        if expected:
            # Non-interactive path (e.g. tests, scripts): use env var directly
            entered = os.environ.get("SB_PII_PASSPHRASE_INPUT", "")
            if not entered:
                try:
                    entered = getpass.getpass("Passphrase: ")
                except (EOFError, KeyboardInterrupt):
                    print(_ACCESS_DENIED)
                    return 1
        else:
            # No passphrase configured — deny by default
            print(_ACCESS_DENIED)
            return 1

        if entered != expected:
            print(_ACCESS_DENIED)
            return 1

    # Log access in audit log (GDPR-03)
    import datetime
    try:
        conn.execute(
            "INSERT INTO audit_log (event_type, note_path, created_at) VALUES (?, ?, ?)",
            ("read", str(path), datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
        conn.commit()
    except Exception:
        pass  # audit is best-effort; never blocks read

    print(f"---")
    print(f"title: {post.get('title', '')}")
    print(f"type:  {post.get('type', '')}")
    print(f"sensitivity: {sensitivity}")
    print(f"---")
    print(post.content)
    return 0


def main() -> None:
    """CLI entry point for sb-read."""
    import argparse
    from engine.db import get_connection, init_schema

    parser = argparse.ArgumentParser(description="Display a brain note (with PII gate)")
    parser.add_argument("path", help="Path to the note file")
    args = parser.parse_args()

    conn = get_connection()
    init_schema(conn)
    code = read_note(Path(args.path), conn)
    conn.close()
    sys.exit(code)
```

### Pattern 3: FTS5 Shadow Table Semantics

**What:** With `content=notes` (content table), FTS5 shadow tables store term frequencies against rowids. The `notes_ad` trigger already emits the correct `DELETE` signal to FTS5 when a row is deleted from `notes`. However, FTS5 uses a log-structured merge approach — deleted entries are marked as tombstones, not immediately removed from `%_data` segments.

**Why explicit rebuild is mandatory for GDPR:** Without rebuild, a substring of the deleted content may remain in an unmounted segment in `notes_fts_%_data` — not queryable via `MATCH`, but potentially visible via raw sqlite byte inspection. `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` rewrites all segments from scratch using only live rows, guaranteed to contain no tombstone data.

**Confidence:** HIGH — confirmed in SQLite FTS5 documentation under "FTS5 integrity-check and rebuild commands".

### Anti-Patterns to Avoid

- **Relying on trigger alone for GDPR:** The `notes_ad` trigger marks tombstones in FTS5 but does not purge shadow segment files. Always follow with explicit rebuild. (GDPR-02 exists for exactly this reason.)
- **Checking for sole-reference by DB query only:** The `people` column in `notes` is a JSON array. Query via `json_each()` is possible but the file frontmatter is the source of truth — always parse the file. Stale DB rows must not decide who gets deleted.
- **Prompting getpass in test code:** Tests must mock the passphrase via `SB_PII_PASSPHRASE` env var or monkeypatch `getpass.getpass`. Never invoke the real `getpass` in tests (blocks on stdin).
- **Deleting audit log entries that log the forget itself:** Delete audit rows for the erased person's note paths only; preserve the `forget` event row itself (accountability record, no personal content).
- **LIKE '%slug%' matching too broadly:** If a slug like `al` matches unrelated paths, deletions will be wrong. Confirm match against `people/` subdirectory prefix or full path pattern `%/people/<slug>.md`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secure passphrase input | Custom terminal echo suppression | `getpass.getpass()` | Cross-platform, handles TTY edge cases |
| FTS5 segment compaction | Custom shadow table surgery | `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` | Only official safe API; shadow table schema is internal and version-dependent |
| Frontmatter parsing in forget | Custom YAML split | `python-frontmatter` (already dep) | Handles multi-doc, encoding, edge cases |

---

## Common Pitfalls

### Pitfall 1: FTS5 Rebuild After Partial Delete
**What goes wrong:** Deleting `notes` rows removes them from BM25 search results but does not flush FTS5 data segments. A raw `SELECT hex(block) FROM notes_fts_%_data` can still show term tokens from deleted content.
**Why it happens:** FTS5 is log-structured; deletes write tombstones, not in-place erasure. Compaction only happens on automerge thresholds.
**How to avoid:** Always call `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` immediately after the `DELETE FROM notes` calls in `forget_person()`, before `conn.commit()`.
**Warning signs:** `sb-search <person>` returns zero rows, but sqlite3 CLI `SELECT hex(block) FROM notes_fts_data` output contains the person's name as plaintext bytes.

### Pitfall 2: Sole-Reference Detection Misses Multi-Person Meetings
**What goes wrong:** A meeting note with `people: [alice, bob]` should NOT be deleted when forgetting Alice — Bob still has legitimate interest in the record.
**Why it happens:** Naive "delete all meetings referencing alice" ignores shared attendance.
**How to avoid:** After removing the target slug from the people list, delete the meeting file only if the remaining list is empty. The requirement says "referencing ONLY that person".
**Warning signs:** Test with a meeting that has two attendees — the file must survive forget of one attendee.

### Pitfall 3: Backlink Cleanup Leaves Orphan Sections
**What goes wrong:** Removing `- [[path/to/alice.md]]` lines from other notes can leave a `## Backlinks` section header with no items.
**Why it happens:** `add_backlinks` in `links.py` appends lines but the section header is written by `ensure_person_profile`.
**How to avoid:** After removing backlink lines, check if the resulting `## Backlinks` section is empty and remove or retain it. Cosmetic issue only — not a data correctness risk — but plan for it in the cleanup pass.
**Warning signs:** Notes display empty `## Backlinks\n` section after forget.

### Pitfall 4: `getpass` Blocks in Non-TTY Environments
**What goes wrong:** `getpass.getpass()` raises `GetPassWarning` or blocks when stdin is not a TTY (CI, piped input, test).
**Why it happens:** `getpass` tries to open `/dev/tty` directly; when unavailable it falls back to stdin which may be a pipe.
**How to avoid:** In tests, monkeypatch `getpass.getpass` to return a fixed string, or set `SB_PII_PASSPHRASE_INPUT` env var. In production code, wrap in `try/except (EOFError, KeyboardInterrupt)` and deny on failure.
**Warning signs:** Tests hang or produce `GetPassWarning: Can not control echo on the terminal`.

### Pitfall 5: LIKE Pattern Too Broad
**What goes wrong:** `DELETE FROM notes WHERE path LIKE '%alice%'` matches notes titled "Alice in Wonderland" captured by other users, or a path like `coding/alice-service-architecture.md`.
**Why it happens:** Slug-based LIKE is not path-scoped.
**How to avoid:** Scope LIKE to the people subdirectory: `path LIKE '%/people/alice-smith.md'` and enumerate sole-reference meetings explicitly by path before deletion, then delete each by exact path.
**Warning signs:** More rows deleted than expected in test assertions.

---

## Code Examples

### FTS5 Rebuild (already proven in reindex.py)
```python
# Source: engine/reindex.py line 82 — confirmed working pattern
conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
conn.commit()
```

### FTS5 Trigger-Based Delete (already in db.py)
```python
# Source: engine/db.py lines 31-33
# notes_ad trigger fires automatically on DELETE FROM notes — emits FTS5 tombstone
# This is NOT sufficient alone for GDPR; explicit rebuild must follow
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
END;
```

### Sole-Reference Meeting Detection
```python
# Frontmatter-based people check (source of truth = file, not DB)
import frontmatter
post = frontmatter.load(str(meeting_path))
people = post.get("people", [])
remaining = [p for p in people if p.strip().lower().replace(" ", "-") != slug]
is_sole_reference = len(people) > 0 and len(remaining) == 0
```

### Passphrase Gate (non-interactive fallback)
```python
# For tests: monkeypatch getpass.getpass or set env vars
import getpass
from unittest.mock import patch
with patch("engine.read.getpass.getpass", return_value="correct-passphrase"):
    result = read_note(path, conn)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual FTS5 segment deletion | `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` | SQLite 3.9+ (FTS5 introduced) | Official safe API; no internal schema knowledge needed |
| `raw_input()` for passphrase | `getpass.getpass()` | Python 3 | Cross-platform echo suppression |

---

## Open Questions

1. **Passphrase storage and comparison**
   - What we know: `.env.host` injects env vars; `SB_PII_PASSPHRASE` is the natural key
   - What's unclear: Should passphrase be hashed (bcrypt) or compared in plaintext? v1 requirement says "passphrase confirmation before display" — no encryption requirement is stated
   - Recommendation: Store and compare plaintext in v1. This is a UX confirmation gate, not cryptographic protection. Document the limitation clearly in the CLI help text.

2. **Partial-reference meeting handling**
   - What we know: Meetings with multiple attendees survive; only sole-reference meetings are deleted
   - What's unclear: Should Alice be removed from the `people` list in surviving multi-person meetings? GDPR-01 says "backlinks in other notes" are removed — this implies yes
   - Recommendation: For multi-person meetings, remove the person's name from the `people` frontmatter array and remove backlink lines. Do not delete the file.

3. **Audit log erasure scope**
   - What we know: GDPR-01 says "audit log entries" are deleted; GDPR-03 requires logging operations
   - What's unclear: Delete ALL audit rows for the person's path, or only `create`/`read`/`update` rows (preserving the `forget` event)?
   - Recommendation: Delete rows where `note_path LIKE '%<slug>%'` (person's own records), but the `forget` event row logged by forget_person itself uses `note_path = NULL` (consistent with search audit rows in search.py) so it is automatically preserved.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 7.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --no-project --with pytest pytest tests/test_gdpr.py -q` |
| Full suite command | `uv run --no-project --with pytest pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GDPR-01 | `forget_person()` deletes person file | unit | `pytest tests/test_gdpr.py::test_forget_deletes_person_file -x` | Wave 0 |
| GDPR-01 | `forget_person()` deletes sole-reference meeting | unit | `pytest tests/test_gdpr.py::test_forget_deletes_sole_reference_meeting -x` | Wave 0 |
| GDPR-01 | `forget_person()` spares multi-person meeting | unit | `pytest tests/test_gdpr.py::test_forget_spares_shared_meeting -x` | Wave 0 |
| GDPR-01 | `forget_person()` removes backlinks from surviving notes | unit | `pytest tests/test_gdpr.py::test_forget_cleans_backlinks -x` | Wave 0 |
| GDPR-01 | `sb-search <person>` returns zero results after forget | integration | `pytest tests/test_gdpr.py::test_search_zero_after_forget -x` | Wave 0 |
| GDPR-02 | FTS5 rebuild executed after forget | unit | `pytest tests/test_gdpr.py::test_fts5_rebuild_after_forget -x` | Wave 0 |
| GDPR-04 | PII note denied without passphrase | unit | `pytest tests/test_gdpr.py::test_pii_note_denied_no_passphrase -x` | Wave 0 |
| GDPR-04 | PII note denied with wrong passphrase | unit | `pytest tests/test_gdpr.py::test_pii_note_denied_wrong_passphrase -x` | Wave 0 |
| GDPR-04 | PII note displayed with correct passphrase | unit | `pytest tests/test_gdpr.py::test_pii_note_shown_correct_passphrase -x` | Wave 0 |
| GDPR-04 | Non-PII note displayed without passphrase | unit | `pytest tests/test_gdpr.py::test_non_pii_note_no_gate -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run --no-project --with pytest pytest tests/test_gdpr.py -q`
- **Per wave merge:** `uv run --no-project --with pytest pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_gdpr.py` — covers all 10 tests above (stubs with `pytest.mark.xfail` or `pass`)
- [ ] `engine/forget.py` — stub with `def forget_person(...): pass` and `def main(): pass`
- [ ] `engine/read.py` — stub with `def read_note(...): pass` and `def main(): pass`
- [ ] `pyproject.toml` — add `sb-forget = "engine.forget:main"` and `sb-read = "engine.read:main"` to `[project.scripts]`

---

## Sources

### Primary (HIGH confidence)
- SQLite FTS5 documentation — "FTS5 rebuild and integrity-check" commands — `INSERT INTO t(t) VALUES('rebuild')` behavior and segment compaction guarantees
- `engine/db.py` — `notes_ad` trigger confirming FTS5 delete signal already present
- `engine/reindex.py` line 82 — `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` already used in codebase
- `engine/capture.py` — `sensitivity` column population, `people` frontmatter pattern
- `engine/links.py` — `ensure_person_profile`, `add_backlinks` patterns for understanding what must be reversed
- Python stdlib `getpass` module documentation — `getpass.getpass()` cross-platform behavior

### Secondary (MEDIUM confidence)
- SQLite FTS5 shadow table documentation — tombstone vs. immediate deletion semantics (confirmed by FTS5 source code comments)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already present in codebase; no new deps
- Architecture: HIGH — erasure cascade pattern derived directly from existing schema and trigger code
- Pitfalls: HIGH — FTS5 shadow table semantics and LIKE-scoping pitfalls verified against existing codebase patterns
- Passphrase gate: HIGH — `getpass` stdlib, env var injection already established by `.env.host` pattern

**Research date:** 2026-03-14
**Valid until:** 2026-09-14 (SQLite FTS5 API is stable; Python stdlib `getpass` is stable)
