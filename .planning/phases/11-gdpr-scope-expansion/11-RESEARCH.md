# Phase 11: GDPR Scope Expansion - Research

**Researched:** 2026-03-15
**Domain:** GDPR data portability (Article 20), runtime anonymization, first-run consent UX
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Re-scope for Phase 11 | Research Support |
|----|-------------------------------------|----------------------|-----------------|
| GDPR-02 | After `/sb-forget`, FTS5 index is rebuilt to ensure no content fragments remain | **Expanded:** sb-export CLI — data portability (GDPR Article 20 right to receive personal data in portable format) | JSON/markdown export from SQLite notes table; no new deps needed |
| GDPR-03 | Every note creation, access, modification recorded in audit log | **Expanded:** runtime `anonymize()` function — replace PII tokens in note body with redacted placeholders, non-destructive | String replacement + frontmatter update; `content_sensitivity` downgrade path |
| GDPR-06 | Engine code passes `detect-secrets` scan (zero baseline violations) | **Expanded:** first-run consent prompt — on first `sb-init`, display data processing notice and require explicit acknowledgement before proceeding | `.meta/consent.json` sentinel file; argparse `--yes` flag for non-interactive mode |

Note: GDPR-02, GDPR-03, GDPR-06 are marked "Complete" in REQUIREMENTS.md for their v1 scope. Phase 11 delivers the expanded interpretations described above — standard GDPR Article 20/17/7 capabilities that v1.5 intentionally deferred.
</phase_requirements>

---

## Summary

Phase 11 adds three GDPR capabilities that were explicitly deferred from v1.5: a data export CLI (`sb-export`), a runtime anonymize function, and a first-run consent prompt. None of the three conflict with existing code — they are pure additions to new modules and one modification to `sb-init` flow.

The **sb-export** CLI implements GDPR Article 20 (data portability). It reads all rows from the `notes` table and writes them to a single JSON file (or a directory of markdown files). The existing `notes` table schema already has every field needed: `path`, `type`, `title`, `body`, `tags`, `people`, `created_at`, `updated_at`, `sensitivity`. No schema migration is required. The audit log should record an `export` event.

The **anonymize()** function handles in-place redaction. Given a note path and a list of tokens to redact, it rewrites the note body replacing each token with `[REDACTED]`, updates `updated_at` in the frontmatter, optionally downgrades `content_sensitivity` from `pii` to `private` if the caller requests it, and updates the DB row. This is a non-destructive transform (the original remains in git history, but the live file is clean). It mirrors the pattern of `forget_person` — read frontmatter, modify, write atomically, update DB.

The **first-run consent prompt** gates `sb-init`. On first run, before creating any brain structure, the CLI prints a short data processing notice and requires the user to type `yes` (or pass `--yes`). A sentinel file `.meta/consent.json` is written on acknowledgement. Subsequent `sb-init` runs (idempotent re-runs) skip the prompt when the sentinel exists. This mirrors the existing `init_brain.py` idempotency pattern (`config.toml` seeding never overwrites).

**Primary recommendation:** Three new modules — `engine/export.py`, `engine/anonymize.py`, one modification to `engine/init_brain.py` — plus three new test files and one new pyproject.toml entry (`sb-export`).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | stdlib | Read notes table for export; update row after anonymize | Already used throughout codebase |
| `json` | stdlib | JSON export format for sb-export; consent.json sentinel | Already used in capture.py |
| `pathlib.Path` | stdlib | All file operations (FOUND-12 enforced) | Hard project constraint |
| `python-frontmatter` | >=1.0 | Read/write frontmatter in anonymize() | Already a dependency |
| `datetime` | stdlib | `updated_at` timestamp on anonymize; export timestamp | Already used in capture.py |
| `argparse` | stdlib | `sb-export` CLI and `--yes` flag on `sb-init` | Already used in every engine CLI |

### No New Dependencies
Phase 11 requires zero new `pyproject.toml` dependencies. Everything is already present.

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
├── export.py        # GDPR-02 (expanded): sb-export data portability
├── anonymize.py     # GDPR-03 (expanded): runtime anonymize() function
├── init_brain.py    # GDPR-06 (expanded): first-run consent prompt (MODIFY existing)
tests/
├── test_export.py   # sb-export behaviors
├── test_anonymize.py # anonymize() behaviors
├── test_consent.py  # first-run consent prompt in init_brain
```

Only `init_brain.py` is modified. `export.py` and `anonymize.py` are new greenfield modules.

---

### Pattern 1: Data Export (GDPR-02 expanded)

**What:** `export_brain(brain_root, conn, output_path)` — dumps all notes rows to JSON.

**Format choice:** JSON is the most portable machine-readable format for Article 20. A flat list of objects, one per note, with all frontmatter fields plus body. Output file named `sb-export-<ISO-date>.json`. An optional `--format markdown` flag can dump one `.md` file per note into a directory (same frontmatter already present in source files, so this is essentially a filtered copy).

**Audit requirement:** An `export` event is appended to `audit_log` with `note_path=NULL` and `detail="format:json"` (or `"format:markdown"`). This satisfies GDPR-03 (access is logged).

**Key constraint:** Notes with `sensitivity: pii` MUST be included in the export (Article 20 covers all personal data — excluding PII from the export would defeat the purpose). However the CLI should clearly label them and warn the user. No passphrase gate on export — the user owns their own data.

**Example:**
```python
# engine/export.py
import json
import datetime
from pathlib import Path
import sqlite3


def export_brain(
    brain_root: Path,
    conn: sqlite3.Connection,
    output_path: Path,
    fmt: str = "json",
) -> int:
    """Export all notes to a portable format. Returns count of exported notes.

    GDPR Article 20: data portability — all notes including PII-sensitivity ones.
    Audit event 'export' logged with note_path=NULL (consistent with forget pattern).
    """
    rows = conn.execute(
        "SELECT path, type, title, body, tags, people, created_at, updated_at, sensitivity"
        " FROM notes ORDER BY created_at"
    ).fetchall()

    notes = [
        {
            "path": r[0],
            "type": r[1],
            "title": r[2],
            "body": r[3],
            "tags": r[4],
            "people": r[5],
            "created_at": r[6],
            "updated_at": r[7],
            "content_sensitivity": r[8],
        }
        for r in rows
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"exported_at": datetime.datetime.utcnow().isoformat(), "notes": notes}, indent=2), encoding="utf-8")

    # Audit log — same pattern as forget (note_path=NULL, detail describes operation)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        ("export", None, f"format:{fmt} count:{len(notes)}", now),
    )
    conn.commit()

    return len(notes)
```

---

### Pattern 2: Runtime Anonymize (GDPR-03 expanded)

**What:** `anonymize_note(path, tokens, conn, downgrade_sensitivity)` — replaces each token string in the note body (and title) with `[REDACTED]`, writes the file atomically, updates the DB row.

**Token matching:** Case-insensitive substring replacement. The caller provides the list of tokens (e.g. names, email addresses). This keeps the function simple and avoids NLP (consistent with AI-02 rule: no cloud API call for classification). The `content_sensitivity` downgrade is optional — if `downgrade_sensitivity=True` and the current value is `pii`, it is set to `private` after redaction.

**Atomicity pattern:** Follows `write_note_atomic` — temp file in same directory, write, then `os.replace`. Updates DB `body`, `title`, `sensitivity`, `updated_at` via `UPDATE notes SET ... WHERE path = ?`.

**Important:** `anonymize_note` does NOT delete the original from git history. The docstring must note this limitation — full erasure requires `sb-forget`. Anonymize is a lighter operation for use cases where the note structure should survive but identifying tokens should be scrubbed.

**Example:**
```python
# engine/anonymize.py
import datetime
import os
import sqlite3
import tempfile
from pathlib import Path

import frontmatter


def anonymize_note(
    path: Path,
    tokens: list[str],
    conn: sqlite3.Connection,
    downgrade_sensitivity: bool = False,
) -> dict:
    """Replace tokens with [REDACTED] in note body and title.

    Non-destructive to git history. For full erasure use sb-forget.
    Returns dict: {redacted_count: int, sensitivity_changed: bool, errors: list[str]}
    """
    path = path.resolve()
    errors: list[str] = []

    if not path.exists():
        return {"redacted_count": 0, "sensitivity_changed": False, "errors": [f"File not found: {path.name}"]}

    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        return {"redacted_count": 0, "sensitivity_changed": False, "errors": [type(e).__name__]}

    body = post.content
    title = post.get("title", "")
    redacted_count = 0

    for token in tokens:
        if not token:
            continue
        lower_body = body.lower()
        lower_token = token.lower()
        count = lower_body.count(lower_token)
        if count:
            # Case-insensitive replacement preserving surrounding text
            import re
            body = re.sub(re.escape(token), "[REDACTED]", body, flags=re.IGNORECASE)
            title = re.sub(re.escape(token), "[REDACTED]", title, flags=re.IGNORECASE)
            redacted_count += count

    sensitivity_changed = False
    sensitivity = post.get("content_sensitivity", "public")
    if downgrade_sensitivity and sensitivity == "pii":
        sensitivity = "private"
        sensitivity_changed = True

    post.content = body
    post["title"] = title
    post["content_sensitivity"] = sensitivity
    post["updated_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Atomic write — same pattern as write_note_atomic in capture.py
    tmp_fd = None
    tmp_path = None
    try:
        tmp_fd, tmp_name = tempfile.mkstemp(dir=path.parent)
        tmp_path = Path(tmp_name)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post))
        tmp_fd = None
        os.replace(tmp_name, path)
    except Exception as e:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        errors.append(type(e).__name__)
        return {"redacted_count": redacted_count, "sensitivity_changed": False, "errors": errors}

    # Update DB row
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        conn.execute(
            "UPDATE notes SET body=?, title=?, sensitivity=?, updated_at=? WHERE path=?",
            (body, title, sensitivity, now, str(path)),
        )
        conn.execute(
            "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
            ("anonymize", str(path), f"tokens:{len(tokens)}", now),
        )
        conn.commit()
    except Exception as e:
        errors.append(f"DB update failed: {type(e).__name__}")

    return {"redacted_count": redacted_count, "sensitivity_changed": sensitivity_changed, "errors": errors}
```

---

### Pattern 3: First-Run Consent Prompt (GDPR-06 expanded)

**What:** Before `sb-init` creates any brain structure, it checks for `.meta/consent.json`. If absent, it displays a one-paragraph data processing notice and requires the user to type `yes` or pass `--yes`. On confirmation it writes the sentinel and proceeds. On refusal it exits with code 1.

**Sentinel file location:** `<brain_root>/.meta/consent.json` — inside the brain directory, synced to Drive alongside other `.meta/` files. Content: `{"consented_at": "<ISO timestamp>", "version": "1.0"}`.

**Idempotency:** If `.meta/consent.json` already exists, the prompt is skipped entirely. This is consistent with how `init_brain.py` handles `config.toml` (never overwrites existing). Re-running `sb-init` is safe.

**Non-interactive mode:** `--yes` flag added to `sb-init` argparse. When passed, the sentinel is written without prompting. This is necessary for CI, DevContainer `postCreateCommand`, and test environments.

**Modification site:** `engine/init_brain.py` `main()` function — add consent check before the first `create_brain_structure()` call. The `--yes` flag is added to the argument parser. The `write_consent_sentinel()` helper and `check_consent()` function are best placed as module-level functions in `init_brain.py` (not a separate module — the feature is tightly coupled to init).

**Example:**
```python
# engine/init_brain.py — additions only

CONSENT_NOTICE = """
Second Brain collects and stores the following personal data locally:
  - Notes, meeting records, and people profiles you capture
  - An audit log of create/read/search/forget operations
  - AI-generated summaries (routed per content_sensitivity rules)

All data is stored on your local machine and Google Drive mount.
No data is sent to third parties except as configured in .meta/config.toml.
You may export your data with: sb-export
You may delete your data with: sb-forget <person>

Type 'yes' to acknowledge and continue, or Ctrl-C to cancel.
"""

CONSENT_PATH_RELATIVE = Path(".meta") / "consent.json"


def check_consent(brain_root: Path) -> bool:
    """Return True if consent sentinel exists."""
    return (brain_root / CONSENT_PATH_RELATIVE).exists()


def write_consent_sentinel(brain_root: Path) -> None:
    """Write .meta/consent.json with current timestamp."""
    import json
    sentinel_path = brain_root / CONSENT_PATH_RELATIVE
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_path.write_text(
        json.dumps({"consented_at": datetime.datetime.utcnow().isoformat(), "version": "1.0"}, indent=2),
        encoding="utf-8",
    )


def prompt_consent(brain_root: Path, yes: bool = False) -> bool:
    """Display consent notice and gate on user response. Returns True if consented."""
    if check_consent(brain_root):
        return True
    if yes:
        write_consent_sentinel(brain_root)
        return True
    print(CONSENT_NOTICE)
    try:
        answer = input("Consent (yes/no): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nConsent required. Aborting.")
        return False
    if answer == "yes":
        write_consent_sentinel(brain_root)
        return True
    print("Consent required. Aborting.")
    return False
```

### Anti-Patterns to Avoid

- **Excluding PII notes from sb-export:** Article 20 covers ALL personal data. Excluding high-sensitivity notes breaks the portability guarantee. Include them; label clearly in the JSON output.
- **Blocking re-runs of sb-init with consent prompt:** The consent gate must be idempotent — if `.meta/consent.json` exists, skip silently. Never prompt twice.
- **Anonymize as a synonym for forget:** `anonymize_note` leaves the note file in place with tokens replaced. It does not remove the note from the DB, git history, or audit log. Document this clearly. For full removal, `sb-forget` is the right tool.
- **Regex in anonymize without re.escape:** Raw token strings may contain regex metacharacters (e.g. `john.doe@company.com`). Always `re.escape(token)` before substitution.
- **Writing consent.json to /tmp or outside brain_root:** Consent sentinel must live inside the brain directory so it survives across DevContainer rebuilds (Drive-synced via `.meta/`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON export serialization | Custom serializer | `json.dumps(..., indent=2)` | stdlib; already used in capture.py |
| Atomic file write in anonymize | Direct `path.write_text()` | `tempfile.mkstemp` + `os.replace` | Same-filesystem atomicity — already proven in write_note_atomic |
| Token replacement | Custom loop with str.replace | `re.sub(re.escape(token), "[REDACTED]", body, flags=re.IGNORECASE)` | Handles metacharacters, case-insensitive |
| Consent persistence | In-memory flag | `.meta/consent.json` sentinel file | Survives restarts, Drive-synced, inspectable |

---

## Common Pitfalls

### Pitfall 1: FTS5 Index Not Updated After Anonymize
**What goes wrong:** `anonymize_note` writes new body to file and updates `notes.body` via `UPDATE`, but the FTS5 index still contains the old (unanonymized) tokens. A `sb-search <token>` would still return results.
**Why it happens:** The `notes_au` trigger fires on `UPDATE notes`, which emits a delete + insert to `notes_fts`. BUT: this only works if the UPDATE goes through sqlite3 and the trigger fires. If the DB row is missing (note not yet in DB), the trigger never fires.
**How to avoid:** After the `UPDATE notes` call in `anonymize_note`, verify the rowcount. If 0 rows updated (note not in DB), insert the row, which fires `notes_ai`. Alternatively, call `conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")` after anonymize if the caller processes many notes at once. For single-note anonymize, the trigger is sufficient.
**Warning signs:** `sb-search <redacted-token>` still returns the anonymized note after calling `anonymize_note`.

### Pitfall 2: sb-export Output Path Collision
**What goes wrong:** Running `sb-export` twice in the same second produces the same filename, second run silently overwrites the first export.
**Why it happens:** Default filename includes ISO date but not time.
**How to avoid:** Include time in the default filename: `sb-export-<YYYY-MM-DD>T<HHMMSS>.json`. Or use `--output` argument to let the caller specify. The CLI should print the output path on success.
**Warning signs:** User runs export twice, checks directory, sees only one file.

### Pitfall 3: Consent Prompt Blocks DevContainer postCreateCommand
**What goes wrong:** If `sb-init` is called from `postCreateCommand` in `devcontainer.json` without `--yes`, the build hangs waiting for stdin.
**Why it happens:** `postCreateCommand` has no interactive TTY.
**How to avoid:** DevContainer `postCreateCommand` must use `sb-init --yes`. Document this in `init_brain.py` `--help` text. In tests, always use `--yes` or pre-create the consent sentinel.
**Warning signs:** `docker build` or DevContainer rebuild hangs indefinitely.

### Pitfall 4: Anonymize Leaves Empty Sections After Token Removal
**What goes wrong:** A line like `- Met with Alice Smith about project` becomes `- Met with [REDACTED] about project` — this is correct. But a line that IS entirely the token becomes `- [REDACTED]` — valid, but a section header that was just the person's name becomes `## [REDACTED]` which looks odd.
**Why it happens:** Line-level replacement doesn't distinguish structural Markdown from content.
**How to avoid:** This is acceptable in v1 — the goal is token scrubbing, not perfect document restructuring. Document the limitation. For structural cleanup, `sb-forget` (which removes whole lines) is the right tool.
**Warning signs:** Anonymized notes have `## [REDACTED]` section headers.

### Pitfall 5: Export Includes Audit Log (Unexpected Scope)
**What goes wrong:** User expects `sb-export` to export their notes; instead the output also contains audit log rows (access timestamps, search queries), which may surprise them.
**Why it happens:** Broad interpretation of "all data".
**How to avoid:** `sb-export` exports only the `notes` table. The audit log is operational metadata, not personal content. If the user wants audit log export, that can be a separate `--include-audit` flag in a future phase. Document this scope clearly in CLI help.
**Warning signs:** User opens export JSON and finds search query strings from audit_log mixed with note content.

---

## Code Examples

### FTS5 Trigger on UPDATE (already in db.py — anonymize relies on this)
```python
# Source: engine/db.py lines 34-38
# notes_au trigger fires on UPDATE notes — emits FTS5 delete + reinsert
# anonymize_note UPDATE will trigger this automatically
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
```

### Atomic Write Pattern (from write_note_atomic — replicate in anonymize)
```python
# Source: engine/capture.py — same-filesystem atomic rename
tmp_fd, tmp_name = tempfile.mkstemp(dir=target.parent)  # same dir = same filesystem
tmp_path = Path(tmp_name)
with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
    fh.write(frontmatter.dumps(post))
os.replace(tmp_name, target)  # atomic on POSIX; near-atomic on Windows
```

### Audit Log Pattern (from capture.py and forget.py)
```python
# For export: note_path=NULL (operation-level event, not note-level)
conn.execute(
    "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
    ("export", None, f"format:json count:{count}", now),
)
# For anonymize: note_path=str(path) (note-level event)
conn.execute(
    "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
    ("anonymize", str(path), f"tokens:{len(tokens)}", now),
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GDPR-02 = FTS5 rebuild only | GDPR-02 = sb-export data portability | Phase 11 scope expansion | Article 20 compliance |
| GDPR-03 = audit log only | GDPR-03 = runtime anonymize() | Phase 11 scope expansion | Token scrubbing without full deletion |
| GDPR-06 = detect-secrets scan | GDPR-06 = first-run consent prompt | Phase 11 scope expansion | GDPR Article 7 consent requirement |

**Previously deferred (v2 Requirements — remains out of scope):**
- Automatic PII detection via NLP — rule-based + frontmatter classification is sufficient (per REQUIREMENTS.md Out of Scope)
- Encryption at rest — not a v1 requirement; passphrase gate is access-confirmation UX only

---

## Open Questions

1. **sb-export: include audit log or not?**
   - What we know: Article 20 covers personal data; audit log contains access timestamps and search queries
   - What's unclear: Are audit log rows "personal data" in scope of Article 20 for a single-user local system?
   - Recommendation: Exclude audit log from default export. Add `--include-audit` flag as future work. This keeps the export focused on note content.

2. **anonymize_note: FTS5 after single-note update**
   - What we know: `notes_au` trigger fires on UPDATE — this should keep FTS5 in sync
   - What's unclear: Does the trigger fire correctly when `sensitivity` column changes but `body` does not change (empty token list call)?
   - Recommendation: Always verify rowcount after UPDATE. If 0 rows updated, insert. Add test for the "token not found, no changes" path.

3. **Consent sentinel: should it be gitignored?**
   - What we know: `.meta/` is Drive-synced but not explicitly gitignored
   - What's unclear: Should consent.json be tracked in git (proves consent was given) or gitignored (personal data)?
   - Recommendation: Do not gitignore it — it contains only a timestamp and version, no personal content. Tracking it in git provides an accountability record of when consent was given.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 7.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --no-project --with pytest pytest tests/test_export.py tests/test_anonymize.py tests/test_consent.py -q` |
| Full suite command | `uv run --no-project --with pytest pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GDPR-02 (exp) | `export_brain()` returns count of notes exported | unit | `pytest tests/test_export.py::test_export_returns_note_count -x` | Wave 0 |
| GDPR-02 (exp) | export JSON file contains all notes fields | unit | `pytest tests/test_export.py::test_export_json_contains_all_fields -x` | Wave 0 |
| GDPR-02 (exp) | PII-sensitivity notes ARE included in export | unit | `pytest tests/test_export.py::test_export_includes_pii_notes -x` | Wave 0 |
| GDPR-02 (exp) | export writes audit log entry event_type='export' | unit | `pytest tests/test_export.py::test_export_audit_logged -x` | Wave 0 |
| GDPR-03 (exp) | `anonymize_note()` replaces tokens with [REDACTED] in body | unit | `pytest tests/test_anonymize.py::test_anonymize_replaces_token_in_body -x` | Wave 0 |
| GDPR-03 (exp) | `anonymize_note()` is case-insensitive | unit | `pytest tests/test_anonymize.py::test_anonymize_case_insensitive -x` | Wave 0 |
| GDPR-03 (exp) | `anonymize_note()` updates DB body column | unit | `pytest tests/test_anonymize.py::test_anonymize_updates_db_row -x` | Wave 0 |
| GDPR-03 (exp) | `anonymize_note()` downgrades pii->private when flag set | unit | `pytest tests/test_anonymize.py::test_anonymize_downgrades_sensitivity -x` | Wave 0 |
| GDPR-03 (exp) | `anonymize_note()` writes audit log event_type='anonymize' | unit | `pytest tests/test_anonymize.py::test_anonymize_audit_logged -x` | Wave 0 |
| GDPR-03 (exp) | `anonymize_note()` no-ops gracefully when token not found | unit | `pytest tests/test_anonymize.py::test_anonymize_noop_no_token_match -x` | Wave 0 |
| GDPR-06 (exp) | `prompt_consent()` skips prompt when sentinel exists | unit | `pytest tests/test_consent.py::test_consent_skips_when_sentinel_exists -x` | Wave 0 |
| GDPR-06 (exp) | `prompt_consent(yes=True)` writes sentinel without prompting | unit | `pytest tests/test_consent.py::test_consent_yes_flag_writes_sentinel -x` | Wave 0 |
| GDPR-06 (exp) | `prompt_consent()` writes sentinel when user types 'yes' | unit | `pytest tests/test_consent.py::test_consent_interactive_yes -x` | Wave 0 |
| GDPR-06 (exp) | `prompt_consent()` returns False when user types 'no' | unit | `pytest tests/test_consent.py::test_consent_interactive_no -x` | Wave 0 |
| GDPR-06 (exp) | `prompt_consent()` returns False on EOFError (non-TTY) | unit | `pytest tests/test_consent.py::test_consent_eoferror_returns_false -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run --no-project --with pytest pytest tests/test_export.py tests/test_anonymize.py tests/test_consent.py -q`
- **Per wave merge:** `uv run --no-project --with pytest pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_export.py` — 4 stubs covering GDPR-02 expanded
- [ ] `tests/test_anonymize.py` — 6 stubs covering GDPR-03 expanded
- [ ] `tests/test_consent.py` — 5 stubs covering GDPR-06 expanded
- [ ] `engine/export.py` — `export_brain()` and `main()` stubs
- [ ] `engine/anonymize.py` — `anonymize_note()` and `main()` stubs
- [ ] `engine/init_brain.py` — add `prompt_consent()`, `check_consent()`, `write_consent_sentinel()`, `--yes` flag (MODIFY existing)
- [ ] `pyproject.toml` — add `sb-export = "engine.export:main"` to `[project.scripts]`

---

## Sources

### Primary (HIGH confidence)
- `engine/forget.py` — canonical erasure + FTS5 rebuild + audit log pattern; anonymize and export follow same structure
- `engine/capture.py` `write_note_atomic()` — atomic write pattern (mkstemp + os.replace) replicated in anonymize
- `engine/db.py` — `notes_au` trigger confirms FTS5 stays in sync on UPDATE; schema shows all exportable columns
- `engine/init_brain.py` — idempotency pattern (check-before-write) replicated in consent sentinel
- `engine/read.py` — `SB_PII_PASSPHRASE` / `--yes` env injection pattern; consent uses same non-interactive override approach
- SQLite documentation — `UPDATE` triggers fire `notes_au` which maintains FTS5 index consistency

### Secondary (MEDIUM confidence)
- GDPR Article 20 (data portability) — JSON is an accepted structured machine-readable format
- GDPR Article 7 (conditions for consent) — first-run acknowledgement with timestamp is a standard pattern for local tools

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all patterns proven in existing codebase
- Architecture: HIGH — three features are pure additions; only init_brain.py modified
- Pitfalls: HIGH — FTS5 trigger, atomic write, and consent TTY pitfalls all derived from existing Phase 5/7 learnings
- GDPR interpretation: MEDIUM — Article 20/7 mapping is reasonable for a local single-user tool; not verified against legal counsel

**Research date:** 2026-03-15
**Valid until:** 2026-09-15 (stdlib-only; SQLite FTS5 trigger semantics are stable)
