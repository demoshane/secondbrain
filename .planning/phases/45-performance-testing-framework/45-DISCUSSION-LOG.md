# Phase 45: Performance Testing Framework — Discussion Log

**Date:** 2026-03-30
**Mode:** discuss-phase (interactive)

---

## Gray Areas Selected

All four areas selected by user: Soft limits per tool, Synthetic fixture strategy, CLI invocation options, GUI Performance page design.

---

## Area 1: Soft Limits

**Q: Where should soft limits be defined?**
Options: Hardcoded defaults / Config-first in config.toml / You decide
→ **Selected:** Hardcoded defaults in `engine/perf.py` (recommended)

**Q: Default limit for read-only MCP tools?**
Options: 2 seconds / 1 second / 5 seconds
→ **Selected:** 2 seconds

**Q: Default limit for AI-heavy tools?**
Options: Tiered (ask_brain ≤5s, recap ≤30s, digest ≤60s) / All AI ≤5s / You decide per tool
→ **Selected (with override):** ask_brain ≤5s, recap ≤20s, digest ≤30s
*User note: "ask brain 5 secs, recap 20, digest 30"*

**Q: Default limit for write-path tools?**
Options: 5 seconds / 3 seconds / You decide
→ **Selected:** 5 seconds

---

## Area 2: Synthetic Fixture Strategy

**Q: How to identify fixtures for cleanup?**
Options: `__perf_test__` title prefix / `_perf_test` tag / Temp directory
→ **Selected:** Title prefix `__perf_test__` (recommended)

**Q: How many fixtures per test?**
Options: 1 note per tool / 5 notes per tool / You decide
→ **Selected:** 1 note per tool test (recommended)

**Q: What if run crashes mid-way?**
Options: `sb-perf --cleanup` flag / Document it / `sb-health` orphan detection
→ **Selected:** `sb-perf --cleanup` flag; also runs automatically at start of each run

---

## Area 3: CLI Invocation

**Q: Subset filtering?**
Options: Full suite + `--tool` filter / Always full suite / Named groups
→ **Selected:** Full suite by default, `--tool` filter for targeted runs

**Q: Exit code on breach?**
Options: Always exit 0 / Exit 1 on any breach / `--strict` flag
→ **Selected:** Always exit 0 — warnings are informational only

**Q: JSON output?**
Options: Yes `--json` flag / No, table only
→ **Selected:** Yes, `--json` flag

---

## Area 4: GUI Performance Page

**Q: Nav location?**
Options: New TabBar tab / Section in IntelligencePage / Settings only
→ **Selected:** New tab in TabBar (recommended)

**Q: Page content?**
Options: Table only / History chart only / Both table + charts
→ **Selected:** Both — summary table at top + history chart per tool below

**Q: GUI trigger?**
Options: CLI-only, GUI view only / GUI "Run" button with SSE / You decide
→ **Selected:** CLI-only for running, GUI for viewing results only

---

## Closing Note (user)

*"The cleanup functionality should be similar for any existing or future tests so that we don't end up with junk from tests. We could extend to unify."*

**Decision captured:** `engine/test_utils.py` with a generic `cleanup_test_notes(prefix: str)` function — extensible for perf tests, pytest, and any future test type.
