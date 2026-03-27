# Phase 40: UI Feature Completeness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28

---

## Area 1: Brain Insight

**Q: What should the AI insight contain, and should it cache?**

Options presented:
- Structured stats only (factual, no LLM)
- AI narrative (LLM synthesis of all notes mentioning person)
- Hybrid (stats + short AI paragraph)

**Selected:** AI narrative (overview summary + recent activities). Cache with 24h TTL. Use Ollama (local, free). Regenerate on view if cache is stale.

---

## Area 2: Project Status Storage

**Q: DB column (migration) or frontmatter?**

Options presented:
- DB column via `ALTER TABLE ADD COLUMN` migration
- Frontmatter (parsed from markdown on read, written back on update)

**Selected:** DB column. Consistent with how tags, people, type are handled in this codebase.

---

## Area 3: Meeting Participants as Objects

**Q: How to resolve participant names to paths?**

Options presented:
- Best-effort name match (`SELECT path WHERE type='person' AND title=?`)
- note_people junction table (same resolution problem)
- Return `{name, path}` with nullable path

**Selected:** Nullable `{name, path}` objects via best-effort title match. Path is null if no person note exists for that name.

---

## Area 4: Linked Meetings on Projects

**Q: Linkage mechanism? And read-only or also write endpoint in Phase 40?**

Options presented:
- Relationships table (explicit, clean)
- Shared people heuristic (brittle)
- Tag-based (brittle)

**Selected:** Relationships table for read side. Write endpoint (`POST /projects/<path>/meetings`) deferred to Phase 41.

---

## Area 5: Actions Grouped-by-Source

**Q: `?grouped=true` query param or separate endpoint?**

Options presented:
- `?grouped=true` on existing `/actions`
- New `GET /actions/grouped` endpoint

**Selected:** Separate endpoint. Consistent with codebase style (separate routes for distinct response shapes).
