# Phase 13: Nyquist Completion - Research

**Researched:** 2026-03-15
**Domain:** GSD workflow compliance — VALIDATION.md sign-off for Phases 10 and 11
**Confidence:** HIGH

---

## Summary

Phase 13 is a pure documentation phase. Two phases completed implementation but were never
given `nyquist_compliant: true` in their VALIDATION.md files:

- **Phase 10** (`10-VALIDATION.md`): Has `nyquist_compliant: false`, `status: draft`,
  `wave_0_complete: false`. Phase 10 is fully verified (VERIFICATION.md status: passed,
  3/3 truths confirmed, no gaps). Both tech-debt fixes are in the codebase and the full
  test suite is green. The VALIDATION.md just was never signed off.

- **Phase 11** (`11-VALIDATION.md`): Has `nyquist_compliant: false`, `status: draft`,
  `wave_0_complete: false`. Phase 11 is verified (VERIFICATION.md status: human_needed,
  14/15 truths confirmed, 1 manual TTY item). All code is shipped. The VALIDATION.md
  was never updated; the VERIFICATION.md itself explicitly notes: "VALIDATION.md
  frontmatter has nyquist_compliant: false and wave_0_complete: false — these were
  never updated to reflect phase completion. Stale metadata only."

The work is to edit two existing VALIDATION.md files and then run `/gsd:audit-milestone`
to confirm all phases 1–13 are `nyquist_compliant: true`.

**Primary recommendation:** Edit Phase 10 VALIDATION.md and Phase 11 VALIDATION.md
directly — update frontmatter, per-task status column, checklist, and Approval line.
Then run `/gsd:audit-milestone` to confirm a clean pass across all phases.

---

## Standard Stack

No new libraries or tooling. This phase uses only the git and file editing already in place.

| Tool | Purpose |
|------|---------|
| Write/Edit (file tool) | Update VALIDATION.md frontmatter and body |
| `/gsd:audit-milestone` | Confirm all phases reach `nyquist_compliant: true` |
| `uv run --no-project --with pytest tests/ -x -q` | Confirm test suite still green before audit |

---

## Architecture Patterns

### The Three Frontmatter Fields

Every VALIDATION.md has these three fields that must all be updated together:

```yaml
# Before (current state of both Phase 10 and 11)
status: draft
nyquist_compliant: false
wave_0_complete: false

# After (target state for both)
status: complete
nyquist_compliant: true
wave_0_complete: true
```

Never update only `nyquist_compliant` in isolation — all three travel together.

### Per-Task Status Column Update Pattern

Automated task rows: change `⬜ pending` → `✅ green`

```
# Before
| 10-00-02 | 00 | 1 | tech debt | integration | `uv run ... tests/test_forget.py::...` | ✅ | ⬜ pending |

# After
| 10-00-02 | 00 | 1 | tech debt | integration | `uv run ... tests/test_forget.py::...` | ✅ | ✅ green |
```

Manual-only task rows: change `⬜ pending` → `manual-only`

```
# Before
| 10-00-01 | 00 | 1 | tech debt | manual | n/a (docstring review) | ✅ | ⬜ pending |

# After
| 10-00-01 | 00 | 1 | tech debt | manual | n/a (docstring review) | ✅ | manual-only |
```

For Phase 11, row 11-03-05 (interactive TTY) stays `manual-only`.

### Checklist Completion Pattern

```markdown
## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
```

### Phase 11 Special Case: human_needed Verification

Phase 11's VERIFICATION.md status is `human_needed` (14/15 — the interactive TTY consent
prompt cannot be automated). The precedent from Phase 9 research is explicit:

> "Sign off automated items as green; annotate human-needed items with `manual-only` status.
> The checklist item 'All tasks have automated verify or Wave 0 dependencies' is about
> coverage design, not about manual items being executed — manual items are acceptable
> when labeled as such."

So Phase 11 CAN be signed off `nyquist_compliant: true`. Row 11-03-05 stays `manual-only`
in the Status column, not `✅ green`. The Approval line should note the human item is
documented but deferred.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Confirming all-phases compliance | Manual per-phase audit | `/gsd:audit-milestone` |
| Knowing what sign-off looks like | Re-deriving format | Phase 9 RESEARCH.md code examples (in codebase) |

---

## Common Pitfalls

### Pitfall 1: Updating Only `nyquist_compliant`, Skipping Other Two Fields

**What goes wrong:** `status` stays `draft` and `wave_0_complete` stays `false`.
**Why it happens:** `nyquist_compliant` is the headline flag; the others feel secondary.
**How to avoid:** Always update all three in one edit: `status`, `nyquist_compliant`,
`wave_0_complete`.

### Pitfall 2: Marking Phase 11 TTY Row as `✅ green`

**What goes wrong:** Row 11-03-05 (interactive TTY consent behavior) is marked green when
no human actually ran the prompt in a real terminal.
**Why it happens:** Sign-off checklist pressure makes unchecked items feel like blockers.
**How to avoid:** That row is permanently `manual-only`. The phase sign-off is still valid —
the checklist item about coverage design is satisfied because all other rows have automated
commands.

### Pitfall 3: Forgetting the Approval Line

**What goes wrong:** Checklist boxes are ticked but `**Approval:** pending` is left
unchanged.
**Why it happens:** The Approval line sits below the checklist and is easy to miss.
**How to avoid:** The Approval line is part of the sign-off block — update it to `approved`
in the same edit.

### Pitfall 4: Creating a New VALIDATION.md for Phase 10 Instead of Editing the Existing One

**What goes wrong:** Phase description says "Write Phase 10 VALIDATION.md" — this could be
misread as creating a new file.
**Why it happens:** Ambiguous phrasing in the phase goal.
**Reality:** `10-VALIDATION.md` already exists at
`.planning/phases/10-quick-code-fixes/10-VALIDATION.md` with a complete structure. The task
is to sign it off (edit it), not create it from scratch. The file already has all the
correct content — only the status values need updating.

---

## Exact Changes Required

### Phase 10 VALIDATION.md Changes

**File:** `.planning/phases/10-quick-code-fixes/10-VALIDATION.md`

Frontmatter (lines 1–8):
```yaml
# Change:
status: draft  →  status: complete
nyquist_compliant: false  →  nyquist_compliant: true
wave_0_complete: false  →  wave_0_complete: true
```

Per-Task Verification Map — two rows:
- Row `10-00-01` (manual docstring review): `⬜ pending` → `manual-only`
- Row `10-00-02` (integration test): `⬜ pending` → `✅ green`

Validation Sign-Off checklist — tick all 6 boxes (change `[ ]` → `[x]`).

Approval line: `pending` → `approved`

### Phase 11 VALIDATION.md Changes

**File:** `.planning/phases/11-gdpr-scope-expansion/11-VALIDATION.md`

Frontmatter (lines 1–8):
```yaml
# Change:
status: draft  →  status: complete
nyquist_compliant: false  →  nyquist_compliant: true
wave_0_complete: false  →  wave_0_complete: true
```

Per-Task Verification Map — 17 rows:
- Rows `11-00-01` through `11-00-03` (Wave 0 stubs): `⬜ pending` → `✅ green`
- Rows `11-01-01` through `11-01-04` (export tests): `⬜ pending` → `✅ green`
- Rows `11-02-01` through `11-02-05` (anonymize tests): `⬜ pending` → `✅ green`
- Rows `11-03-01` through `11-03-04` (consent unit tests): `⬜ pending` → `✅ green`
- Row `11-03-05` (TTY manual): `⬜ pending` → `manual-only`

Wave 0 Requirements checklist — tick all 7 boxes (all Wave 0 files were created).

Validation Sign-Off checklist — tick all 6 boxes.

Approval line: `pending` → `approved (automated: 16/17 green; 11-03-05 manual-only — TTY
behavior inherently untestable without real terminal)`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via uv run --no-project --with pytest) |
| Config file | pyproject.toml |
| Quick run command | `uv run --no-project --with pytest tests/ -x -q` |
| Full suite command | `uv run --no-project --with pytest tests/ -x -q` |

### Phase Requirements → Test Map

Phase 13 is tech debt — no new requirement IDs. The only "test" is the audit tool itself.

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Test suite still green after doc edits | regression | `uv run --no-project --with pytest tests/ -x -q` | Yes |
| All phases 1–13 nyquist_compliant | audit | `/gsd:audit-milestone` | n/a (command) |

### Sampling Rate
- **Per task commit:** `uv run --no-project --with pytest tests/ -x -q`
- **Per wave merge:** Same
- **Phase gate:** Full suite green + `/gsd:audit-milestone` clean pass

### Wave 0 Gaps

None — this phase edits existing files. No new test files or infrastructure needed.

---

## Open Questions

1. **Does `/gsd:audit-milestone` auto-check `nyquist_compliant` frontmatter, or does it run
   tests too?**
   - What we know: It is the prescribed final confirmation step
   - What's unclear: Whether it re-runs tests or reads frontmatter only
   - Recommendation: Run full test suite separately before calling the audit command to
     ensure nothing is assumed

2. **Phase 11's VERIFICATION.md status is `human_needed` — does the audit tool flag this
   as non-compliant?**
   - What we know: Phase 9 precedent says human_needed phases CAN reach `nyquist_compliant:
     true` when automated items are green and manual items are labeled
   - Recommendation: Sign off as described; if audit flags it, add a note to the
     VALIDATION.md Approval line documenting the human-needed caveat

---

## Sources

### Primary (HIGH confidence)

- Direct inspection: `.planning/phases/10-quick-code-fixes/10-VALIDATION.md` — current
  state: `nyquist_compliant: false`, all rows `⬜ pending`
- Direct inspection: `.planning/phases/11-gdpr-scope-expansion/11-VALIDATION.md` — current
  state: `nyquist_compliant: false`, all rows `⬜ pending`
- Direct inspection: `.planning/phases/10-quick-code-fixes/10-VERIFICATION.md` — status:
  passed, 3/3 verified, no gaps
- Direct inspection: `.planning/phases/11-gdpr-scope-expansion/11-VERIFICATION.md` — status:
  human_needed, 14/15 verified; explicitly notes VALIDATION.md stale metadata
- Direct inspection: `.planning/phases/09-nyquist-sign-off/09-RESEARCH.md` — sign-off
  process, patterns, pitfalls (directly applicable precedent)
- Direct inspection: `.planning/config.json` — `nyquist_validation: true` (section
  required)

### Secondary (MEDIUM confidence)

- STATE.md Phase 12 decision: "VALIDATION.md frontmatter has nyquist_compliant: false and
  wave_0_complete: false — these were never updated to reflect phase completion. Stale
  metadata only." (confirmed by verifier note in 11-VERIFICATION.md)

---

## Metadata

**Confidence breakdown:**
- Current state of VALIDATION.md files: HIGH — directly inspected
- Required edits: HIGH — format established in Phase 9, files have identical structure
- Phase 11 human_needed handling: HIGH — explicit precedent in Phase 9 research

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable — pure doc process, no moving parts)
