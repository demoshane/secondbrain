# Phase 56: Co-capture Grouping — Temporal Proximity + MCP Tool Nudges

**Gathered:** 2026-04-17
**Status:** Ready for planning (depends on 54, benefits from 50-53)

<domain>
## Phase Boundary

Make co-capture relationships work automatically even when Claude makes separate
`sb_capture` calls instead of a single `sb_capture_smart` call. Add temporal proximity
detection so notes captured within a time window are linked. Surface recent capture
context as MCP nudges so Claude and the user can see what was just captured.

### Problem

Co-captured relationships currently only work inside `sb_capture_smart` — it calls
`itertools.combinations()` over all notes in the batch and inserts `co-captured`
relationship rows. But when Claude makes 3 separate `sb_capture()` calls in one
conversation (the most common pattern), each note is isolated. No co-captured
relationships are created, no temporal grouping exists, and the notes appear unrelated
in the graph.

Additionally:
1. **Capture sessions are ephemeral** — a UUID is generated per batch but never stored
   in the DB. There's no way to retrieve "all notes from this conversation" later.
2. **No temporal proximity detection** — clustering in `cluster_recent_notes()` uses
   shared people/tags within a 7-day window, not time distance between captures.
3. **No capture context nudges** — when capturing, the MCP tool doesn't surface
   what was recently captured, missing an opportunity to suggest grouping.
4. **Known bug**: `/smart-capture/confirm` handler (api.py ~line 2527) still uses raw
   paths instead of `store_path()` for co-captured relationship inserts.

### Scope
- Persist `capture_session` in the notes table for later retrieval
- New `find_temporal_neighbors()` function: find notes captured within N minutes
- Auto-create co-captured relationships for temporally proximate captures
- Return temporal context (recent captures) as nudges in MCP capture responses
- Optional `session_id` param on `sb_capture` for explicit conversation grouping
- Fix the `/smart-capture/confirm` absolute path bug
- Tests for all paths
</domain>

<decisions>
## Implementation Decisions

### Capture session persistence

Add `capture_session TEXT` column to the `notes` table. Nullable — old notes won't have it.
Migration via the existing add-column pattern in `db.py`.

Populate in `capture_note()`: accept optional `capture_session` param, write to DB.
`sb_capture_smart` and `sb_capture_batch` already generate UUIDs — just pass them through.
`sb_capture` gets a new optional `session_id` param; if provided, reuse it across calls
in the same conversation.

### Temporal proximity window

Default: **15 minutes**. Notes captured within 15 minutes of each other are candidates
for co-captured relationships.

```python
def find_temporal_neighbors(
    conn, reference_time: str, window_minutes: int = 15, exclude_path: str | None = None
) -> list[dict]:
    """Find notes captured within window_minutes of reference_time."""
```

Returns: `[{"path": str, "title": str, "type": str, "created_at": str, "delta_seconds": int}]`

### Auto co-capture for separate calls

After each `sb_capture()` call:
1. Call `find_temporal_neighbors()` with the new note's `created_at`
2. For each neighbor: INSERT OR IGNORE a `co-captured` relationship (both directions)
3. If the neighbor has a `capture_session` and the new note doesn't, inherit it
4. Return the neighbors as context in the response

This means if Claude calls `sb_capture` 3 times in 5 minutes:
- Call 1: no neighbors → normal capture
- Call 2: finds Call 1's note → creates co-captured link, returns it as context
- Call 3: finds both previous notes → creates co-captured links to both

### MCP nudge format

Extend capture response with a `recent_context` field:

```python
{
    "status": "created",
    "path": "...",
    "recent_context": [
        {"path": "meetings/standup.md", "title": "Daily Standup", "minutes_ago": 3},
        {"path": "people/alice.md", "title": "Alice Smith", "minutes_ago": 7}
    ],
    "co_captured_with": ["meetings/standup.md", "people/alice.md"],
    "nudge": "Auto-linked with 2 recent captures from this session."
}
```

The nudge text is informational — Claude sees it in the tool response and can mention
it to the user or use it for context.

### Session grouping via sb_capture

New optional parameter on `sb_capture`:

```python
def sb_capture(
    title: str,
    body: str,
    ...,
    session_id: str = "",  # NEW: reuse across calls to group them
) -> dict
```

If `session_id` is provided:
- Store it as `capture_session` in the DB
- Use it to find other notes with the same session (stronger grouping than temporal proximity)
- Claude can generate one UUID at conversation start and pass it to all captures

If not provided:
- Fall back to temporal proximity auto-linking (the default behavior)

### Confirm handler bug fix

`/smart-capture/confirm` (api.py ~line 2527) uses raw paths for co-captured INSERTs.
Apply the same `store_path()` normalization pattern used in the main `/smart-capture`
handler.

### Where it plugs in

1. `engine/db.py` — migration: `capture_session TEXT` column on notes
2. `engine/capture.py` — `capture_note()` accepts and stores `capture_session`
3. `engine/intelligence.py` — `find_temporal_neighbors()` function
4. `engine/mcp_server.py` — wire temporal neighbor check into `sb_capture`, `sb_capture_batch`;
   add `session_id` param to `sb_capture`; return `recent_context` in responses
5. `engine/api.py` — fix `/smart-capture/confirm` path bug; wire temporal neighbors
   into `/capture` and `/smart-capture` API routes
</decisions>

<canonical_refs>
## Canonical References

### Source files to modify
- `engine/db.py` — add capture_session column migration
- `engine/capture.py` — accept/store capture_session in capture_note()
- `engine/intelligence.py` — add find_temporal_neighbors()
- `engine/mcp_server.py` — wire auto-linking + nudges into sb_capture, sb_capture_batch
- `engine/api.py` — fix confirm handler bug, wire temporal context into API routes

### Source files to read
- `engine/mcp_server.py` — sb_capture (line 248), sb_capture_smart (line 905), sb_capture_batch (line 339)
- `engine/api.py` — /smart-capture (line 2313), /smart-capture/confirm (~line 2481)
- `engine/intelligence.py` — cluster_recent_notes (line 575), find_similar (line 413)
- `engine/capture.py` — capture_note() signature and return format
- `engine/db.py` — notes table schema, relationships table, migration pattern
- `engine/paths.py` — store_path() for path normalization

### Dependencies
- Phase 54: consolidation layer (must be complete — we extend nightly clustering)
- Phase 50: access tracking (optional — capture_session can inform access patterns)
</canonical_refs>

<deferred>
## Deferred Ideas

- Conversation-level session tracking: link all captures from a Claude conversation automatically (requires MCP protocol extension or heuristic) → future
- Visual session timeline in GUI: show captures grouped by session → future
- Session replay: "show me everything from that conversation about project X" → Phase 57 or later
- Cross-tool session awareness: link captures to searches in the same session → future
</deferred>

---

*Phase: 56-co-capture-grouping-temporal-proximity-mcp-tool-nudges*
*Context gathered: 2026-04-17*
