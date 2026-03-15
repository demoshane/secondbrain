---
phase: 11-gdpr-scope-expansion
verified: 2026-03-15T12:00:00Z
status: human_needed
score: 14/15 must-haves verified
re_verification: false
human_verification:
  - test: "Run sb-init on a fresh tmp dir without --yes flag; verify consent notice appears and prompt blocks for input; type 'no'; verify exits non-zero; run again, type 'yes'; verify brain structure created"
    expected: "Consent notice printed, prompt blocks, 'no' returns exit code 1 with no brain creation, 'yes' proceeds to create brain structure"
    why_human: "Interactive TTY behavior — monkeypatched in tests but real terminal blocking cannot be automated"
  - test: "Run sb-init --yes on a fresh tmp dir; verify .meta/consent.json is created; run sb-init --yes again; verify no second prompt appears"
    expected: "--yes writes sentinel silently; second run skips consent entirely (idempotent)"
    why_human: "Idempotent sentinel behavior requires a real brain root on disk, not fully covered by unit tests alone"
notes:
  - "GDPR-02/GDPR-03/GDPR-06 in ROADMAP Phase 11 are re-uses of existing REQUIREMENTS.md IDs for 'expanded' capabilities. The existing IDs cover different behaviors (FTS5 rebuild after forget, audit log, detect-secrets). The new capabilities (export, anonymize, consent) have no dedicated requirement IDs in REQUIREMENTS.md. This is a documentation gap, not a code gap."
  - "VALIDATION.md frontmatter has nyquist_compliant: false and wave_0_complete: false — these were never updated to reflect phase completion. Stale metadata only."
---

# Phase 11: GDPR Scope Expansion Verification Report

**Phase Goal:** Implement the three GDPR capabilities that v1.5 scoped narrower than standard: sb-export CLI (data portability), runtime anonymize() function, and first-run consent prompt
**Verified:** 2026-03-15T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `export_brain()` writes a JSON file containing all notes rows | VERIFIED | `engine/export.py:17-41` — SELECT all columns FROM notes, writes JSON with indent=2 |
| 2 | PII-sensitivity notes are included in the export (not filtered out) | VERIFIED | No WHERE filter on sensitivity; test_export_includes_pii_notes confirms pii notes present |
| 3 | An 'export' row appears in audit_log after every call | VERIFIED | `engine/export.py:44-48` — INSERT INTO audit_log event_type='export' before commit |
| 4 | `export_brain()` returns the integer count of exported notes | VERIFIED | `engine/export.py:37,50` — `count = len(notes)`, returned at end |
| 5 | sb-export CLI exits 0 and prints output path | VERIFIED | `engine/export.py:86-87` — `print(f"Exported {count} notes to {output_path}")`, `sys.exit(0)` |
| 6 | `anonymize_note()` replaces all occurrences of token in note body with [REDACTED] | VERIFIED | `engine/anonymize.py:68-73` — re.sub with re.escape, flags=re.IGNORECASE |
| 7 | Replacement is case-insensitive | VERIFIED | `engine/anonymize.py:69` — `flags=re.IGNORECASE`; test_anonymize_case_insensitive confirms |
| 8 | notes.body, notes.title, notes.sensitivity, notes.updated_at updated in DB after call | VERIFIED | `engine/anonymize.py:114-117` — UPDATE notes SET body,title,sensitivity,updated_at WHERE path=? |
| 9 | audit_log records event_type='anonymize' for every call | VERIFIED | `engine/anonymize.py:118-122` — INSERT INTO audit_log event_type='anonymize' |
| 10 | When no token matches, returns redacted_count=0 with no error | VERIFIED | `anonymize_note()` returns after file write with redacted_count=0 when no match; test_anonymize_noop confirms |
| 11 | sb-init --yes writes .meta/consent.json and proceeds without prompting | VERIFIED | `engine/init_brain.py:42-44` — yes=True branch calls write_consent_sentinel and returns True; main() at line 136 gates on result |
| 12 | sb-init on second run skips consent prompt when .meta/consent.json exists | VERIFIED | `engine/init_brain.py:40-41` — check_consent() short-circuits at top of prompt_consent(); test_consent_skips_when_sentinel_exists confirms |
| 13 | prompt_consent() returns False on 'no' or EOFError | VERIFIED | `engine/init_brain.py:47-53` — EOFError caught, 'yes' check strict, anything else returns False |
| 14 | prompt_consent() returns True and writes sentinel on 'yes' | VERIFIED | `engine/init_brain.py:50-52` — writes sentinel then returns True |
| 15 | Interactive consent prompt displays and blocks for user input on a real TTY | UNCERTAIN | Automated tests monkeypatch `builtins.input`; real TTY behavior requires human verification |

**Score:** 14/15 truths verified (1 needs human)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/export.py` | export_brain() + main() fully implemented | VERIFIED | 88 lines, no stubs, full SELECT/JSON/audit_log/argparse implementation |
| `engine/anonymize.py` | anonymize_note() full implementation | VERIFIED | 173 lines, re.escape + atomic write + DB UPDATE + audit_log, no stubs |
| `engine/init_brain.py` | prompt_consent(), check_consent(), write_consent_sentinel(), main() wired | VERIFIED | All three functions implemented (lines 17-54); main() wired at line 136 before validate_drive_mount |
| `tests/test_export.py` | 4 passing tests (no xfail) | VERIFIED | 65 lines, 4 tests, no xfail markers, export_db fixture present |
| `tests/test_anonymize.py` | 6 passing tests (no xfail) | VERIFIED | 123 lines, 6 tests, no xfail markers, _write_note + _seed_note helpers |
| `tests/test_consent.py` | 5 passing tests (no xfail) | VERIFIED | 47 lines, 5 tests, no xfail markers, monkeypatch injection pattern |
| `pyproject.toml` | sb-export entry point wired | VERIFIED | Line 29: `sb-export = "engine.export:main"` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml` | `engine/export.py` | `sb-export = "engine.export:main"` | WIRED | Confirmed at pyproject.toml:29 |
| `engine/export.py` | notes table | `SELECT path,type,title,body,tags,people,created_at,updated_at,sensitivity FROM notes` | WIRED | Lines 17-20, exact column list matches requirement |
| `engine/export.py` | audit_log table | `INSERT INTO audit_log event_type='export'` | WIRED | Lines 44-47 |
| `engine/anonymize.py` | notes table | `UPDATE notes SET body,title,sensitivity,updated_at WHERE path=?` | WIRED | Lines 114-117 |
| `engine/anonymize.py` | audit_log | `INSERT INTO audit_log event_type='anonymize'` | WIRED | Lines 118-121 |
| `engine/anonymize.py` | notes_fts | notes_au trigger fires automatically on UPDATE notes | WIRED | No manual rebuild needed; trigger defined in db.py; consistent with plan intent |
| `engine/init_brain.py main()` | `prompt_consent()` | called before create_brain_structure(); exits sys.exit(1) on False | WIRED | Line 136: `if not prompt_consent(BRAIN_ROOT, yes=args.yes): sys.exit(1)` — placed BEFORE validate_drive_mount at line 139 |
| `prompt_consent()` | `.meta/consent.json` | write_consent_sentinel() writes JSON sentinel | WIRED | Lines 43, 51 call write_consent_sentinel(); sentinel path at brain_root/.meta/consent.json |

---

### Requirements Coverage

| Requirement | Source Plan | REQUIREMENTS.md Definition | Phase 11 Implementation | Status |
|-------------|------------|----------------------------|------------------------|--------|
| GDPR-02 | 11-01 | "After /sb-forget, FTS5 index rebuilt" (Phase 5 Complete) | export_brain() — data portability export | MISMATCH (see note) |
| GDPR-03 | 11-02 | "Every note creation/access/modification in audit log" (Phase 2 Complete) | anonymize_note() — runtime token scrubbing | MISMATCH (see note) |
| GDPR-06 | 11-03 | "Engine passes detect-secrets scan" (Phase 2 Complete) | prompt_consent() — first-run consent gate | MISMATCH (see note) |

**Requirements mismatch note:** The three requirement IDs (GDPR-02, GDPR-03, GDPR-06) reused in Phase 11's ROADMAP entry and PLAN frontmatter map to existing REQUIREMENTS.md definitions that were already satisfied in earlier phases (Phases 2 and 5). Phase 11 implements distinct new capabilities (data portability export, runtime anonymization, first-run consent) that have no dedicated requirement IDs in REQUIREMENTS.md. The implementations themselves are real and substantive — this is a documentation gap in REQUIREMENTS.md, not a code gap. The three new capabilities are observable in the codebase and fully tested.

**Orphaned behaviors:** The following Phase 11 capabilities have no REQUIREMENTS.md entries:
- Data portability export (GDPR Article 20) — `engine/export.py`
- Runtime PII token scrubbing (GDPR Article 17 partial anonymization) — `engine/anonymize.py`
- First-run consent gate (GDPR Article 7) — `prompt_consent()` in `engine/init_brain.py`

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/phases/11-gdpr-scope-expansion/11-VALIDATION.md` | 5-6 | `nyquist_compliant: false`, `wave_0_complete: false` | Info | Stale metadata — phase is complete but VALIDATION.md frontmatter was never updated. No code impact. |

No code-level anti-patterns found. All three implementation files are free of:
- `NotImplementedError` stubs
- `TODO`/`FIXME`/`PLACEHOLDER` comments
- `xfail` markers in test files
- Empty return values (`return null`, `return {}`, `return []`)

---

### Human Verification Required

#### 1. Interactive consent TTY behavior

**Test:** Create a fresh tmp dir. Run `sb-init` without `--yes`. Verify the consent notice prints and the prompt blocks for user input. Type 'no' — verify process exits with non-zero code and no brain structure is created. Run again, type 'yes' — verify brain structure is created and `.meta/consent.json` is written.
**Expected:** Full interactive flow works; 'no' aborts cleanly; 'yes' proceeds to Drive mount check and brain creation.
**Why human:** Automated tests monkeypatch `builtins.input`. Real TTY blocking behavior (that the prompt actually suspends the process and waits) cannot be verified programmatically.

#### 2. Idempotent second-run behavior

**Test:** After running `sb-init --yes` (which creates `.meta/consent.json`), run `sb-init --yes` a second time. Verify no second consent prompt appears and the command completes normally.
**Expected:** Silent skip of consent check on second run; output goes straight to Drive mount validation.
**Why human:** Requires a real brain root on disk with persistent `.meta/consent.json`.

---

### Gaps Summary

No code gaps. All three features are fully implemented, substantive, and wired. The only item requiring human verification is the interactive TTY behavior of the consent prompt — which is inherently untestable without a real terminal.

The requirements traceability mismatch (reusing GDPR-02/03/06 IDs for new capabilities) is a documentation issue. REQUIREMENTS.md should ideally have new IDs (e.g., GDPR-07 data portability, GDPR-08 runtime anonymization, GDPR-09 consent gate) to represent the Phase 11 work. This does not affect the correctness of the implementation.

---

_Verified: 2026-03-15T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
