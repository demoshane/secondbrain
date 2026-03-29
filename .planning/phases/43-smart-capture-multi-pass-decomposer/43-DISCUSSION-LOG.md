# Phase 43: Smart Capture Multi-Pass Decomposer — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 43-smart-capture-multi-pass-decomposer
**Areas discussed:** engine/passes/ API shape, URL extraction behavior, Action item save timing, GUI/MCP parity scope, Capture path scope

---

## engine/passes/ API shape

**Q:** What should the top-level interface look like?
- Options: `decompose(content) → result` / Pipeline class / Individual pass functions + orchestrator
- **Selected:** `decompose(content) → result` (single entry point, modular internals)

**Q:** Should `segment_blob()` become a thin wrapper or be deleted?
- Options: Thin wrapper (keep for compat) / Delete and update all callers
- **Selected:** Delete `segment_blob()`, update all callers directly

---

## URL extraction behavior (Pass 2)

**Q:** When a blob has a URL plus substantial text, what happens?
- Options: Always extract URL as separate link note / URL into frontmatter url: field / Only split if text is dominant
- **Selected:** Always extract URL as a separate link note, classify the rest independently

**Q:** What if the URL IS the primary content?
- Options: Still extract as link note / Keep as whole link note
- **Selected:** Still extract as link note — same code path, no special case

---

## Action item save timing (Pass 4)

**Q:** Where do extracted action items go?
- Options: Write to action_items DB at capture time / Return as metadata only / Intelligence layer async
- **Selected:** Write to action_items DB table at capture time

**Q:** What extraction approach for Pass 4?
- User noted pure regex too rigid: "how would it capture 'tuomas would call the fastly'?"
- User also wants configurable markers like "AP" for action point
- **Selected:** Two-layer: (a) configurable keyword markers, (b) intelligence.py for intent-based extraction

**Q:** Where are custom markers configured?
- Options: config.toml only / GUI settings panel in this phase
- **Selected:** GUI settings panel in this phase

---

## GUI/MCP parity scope

**Q:** Should POST /smart-capture create person stubs?
- Options: Full behavioral parity (auto-create silently) / Show proposed stubs for confirmation / Code-level parity only
- **Selected:** Full behavioral parity — GUI auto-creates stubs silently, stubs shown in response

---

## Capture path scope

**Q:** Should extraction passes also run for regular sb_capture calls?
- User raised: "Are we covering smart capture for all note types? It needs to cover all areas of smart capturing."
- Options: Smart capture only (keep Phase 43 scoped) / All capture paths
- Initial selection: All capture paths
- **Scope check raised:** This becomes two phases of work in one
- **Final decision:** Keep Phase 43 scoped to decomposer refactor only; extraction on all capture paths deferred to a new follow-on phase (user: "this is critical core functionality")
