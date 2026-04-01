# Phase 51: Temporal Decay — Forgetting Curve

**Gathered:** 2026-04-01
**Status:** Ready for planning (depends on Phase 50)

<domain>
## Phase Boundary

Replace the flat recency boost with a proper forgetting curve: notes naturally decay in
relevance over time, but access (from Phase 50) resets the decay clock. Different note
types decay at different rates — decisions persist longer than meeting notes.

### Problem
Current recency boost is creation-time only: `1.0 + 0.1 * exp(-age/43)`. A 2-year-old
decision note that you reference weekly gets no benefit from that usage. Stale detection
is binary (90-day threshold). There's no gradient between "fresh" and "stale", and no
mechanism for access to counteract aging.

### Scope
- Replace `_recency_multiplier()` with `_relevance_decay()` that considers both age AND
  last_accessed_at (from Phase 50)
- Per-type half-lives: decision=180d, person=never, meeting=30d, note=60d, project=120d
- Graduated stale detection: replace binary 90-day threshold with decay score bands
- Optional: expose decay score in search results for transparency
</domain>

<decisions>
## Implementation Decisions

### Dual-axis decay formula
```
base_decay = exp(-age_days / type_half_life)
access_refresh = exp(-days_since_last_access / access_half_life) if last_accessed else 0
multiplier = 1.0 + 0.15 * max(base_decay, access_refresh)
```
- `type_half_life`: per note type (meeting=30, note=60, project=120, decision=180, person=∞)
- `access_half_life`: 60 days (from Phase 50 boost, now unified)
- `max()` means either freshness OR recent access keeps the note relevant
- Person notes: no decay (evergreen by nature)

### Stale detection upgrade
Replace binary threshold with bands:
- relevance > 0.8: fresh (no action)
- relevance 0.4-0.8: aging (candidates for review nudge)
- relevance < 0.4: stale (surface in health check)
Note: `detect_stale_notes()` in intelligence.py currently uses 90-day binary check.
Bands will be computed from the same decay formula used in search.

### Backward compatibility
- `_recency_multiplier()` is called in 3 places in search.py — replace all with `_relevance_decay()`
- Existing stale note detection callers (`sb_recap`, health checks) get graduated scores
- No external API change — search results just rank differently
</decisions>

<canonical_refs>
## Canonical References

### Source files to modify
- `engine/search.py` — replace `_recency_multiplier()` with `_relevance_decay()`
- `engine/intelligence.py` — upgrade `detect_stale_notes()` to use graduated decay bands

### Source files to read
- `engine/search.py:12-33` — current `_recency_multiplier()` formula
- `engine/intelligence.py:306-348` — current `detect_stale_notes()` logic
- `engine/db.py` — notes table schema (type column, timestamp columns)

### Dependency
- Phase 50 must be complete: `last_accessed_at` and `access_count` columns must exist
</canonical_refs>

<deferred>
## Deferred Ideas

- User-configurable decay rates per note type → future
- "Pin" mechanism to exempt specific notes from decay → future
- Decay visualization in GUI (heatmap of note freshness) → future
</deferred>

---

*Phase: 51-temporal-decay-forgetting-curve*
*Context gathered: 2026-04-01*
