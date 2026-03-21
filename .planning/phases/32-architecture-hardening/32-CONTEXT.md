# Phase 32: Architecture Hardening - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix structural issues that will cause data loss or pain as the brain grows: relative path storage, FK cascade, connection leak safety, tags/people junction tables, action item lifecycle management, security/consistency fixes. 16 ARCH requirements derived primarily from Phase 30 review findings.

</domain>

<decisions>
## Implementation Decisions

### Migration Safety
- Auto-migrate on startup via init_schema() — same pattern as existing ALTER TABLE ADD COLUMN migrations
- Each migration wrapped in a single SQLite transaction (all-or-nothing)
- Sequential migration order in one init_schema() call: 1) relative paths, 2) junction tables, 3) FK cascade — FK goes last because it needs clean paths
- Migration progress logged via Python logging.info() with counts (e.g., "Migrated 342 paths to relative") — silent in normal operation, visible with -v

### Action Items Archival (ARCH-06)
- 90-day threshold for archiving completed action items
- Archive table includes `archived_at` timestamp + `archived_reason` column for GDPR audit trail
- Archived items visible only in sb-health report (count only) — not in GUI, CLI, or MCP list endpoints
- Archival runs as part of sb-health — no new daemon or startup cost
- Archived items included in sb-export for GDPR data portability

### Data Loss Risk Tolerance
- forget_person() cascade: dry-run first showing affected notes, then two-step token confirmation (same pattern as sb_forget)
- Structured fields only — remove person from frontmatter people/entities fields and DB columns; body text untouched (sb-anonymize handles full text redaction separately)
- DB first, then files — single DB transaction commits, then update frontmatter on disk; if file writes fail, sb-reindex fixes the inconsistency
- FK cascade (ARCH-02): enable DB-level ON DELETE CASCADE AND keep existing app-level cascade in forget.py as safety net — remove app cascade in a future cleanup phase once proven

### Breaking Change Handling
- Junction tables (note_tags, note_people): write to BOTH junction table and JSON column; read queries use junction table (indexed). JSON columns kept for backward compat and raw DB querying. Drop JSON in a future phase.
- No version bump — this is internal hardening within v4.0 milestone. Schema changes are forward-only with idempotent migrations.
- Relative path resolution: helper functions in paths.py — `resolve_path(rel)` → absolute, `store_path(abs)` → relative. Called at DB read/write boundaries. Clean, DRY, greppable.
- _SlashNormMiddleware removal: fix test fixtures that produce double slashes + run one-time migration to normalize any double-slash paths in DB, then remove middleware

### Claude's Discretion
- Exact migration detection logic (column existence checks, table introspection)
- Junction table index design (single-column vs composite)
- LIKE escape helper implementation details (ARCH-14)
- PERSON_TYPES constant placement and import pattern (ARCH-16)
- Connection leak fix approach in api.py (ARCH-03) — try/finally vs context manager
- File upload size cap enforcement method (ARCH-04)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/db.py`: init_schema() with existing ALTER TABLE ADD COLUMN migration pattern (try/except for idempotency)
- `engine/paths.py`: BRAIN_ROOT, DB_PATH — natural home for resolve_path/store_path helpers
- `engine/forget.py`: existing app-level cascade — keep as safety net alongside new FK cascade
- `engine/api.py`: 63 get_connection/conn.close pairs — all need try/finally wrapping (ARCH-03)

### Established Patterns
- `ALTER TABLE ADD COLUMN` migrations in db.py with try/except OperationalError for idempotency
- `json.dumps()/json.loads()` with `[]` fallback for tags/people columns
- Two-step token confirmation for destructive MCP ops (_issue_token/_consume_token)
- `get_connection(db_path)` parameter for test isolation

### Integration Points
- `engine/db.py` init_schema(): migration entry point — add sequential migration calls
- `engine/paths.py`: add resolve_path/store_path helpers
- `engine/brain_health.py`: add archive trigger and archive count reporting
- Every module that reads note paths from DB: needs resolve_path() calls
- `engine/capture.py` + `engine/mcp_server.py`: write to junction tables alongside JSON columns

</code_context>

<specifics>
## Specific Ideas

- Migrations should feel invisible — auto-detect and run without user intervention
- Trust SQLite transactions for atomicity — no manual backup step needed
- forget_person dry-run mimics existing sb_forget two-step pattern — consistency across destructive ops
- Junction tables are a stepping stone — JSON columns stay for now, get dropped when proven unnecessary
- "DB first, files second" for forget cascade — db-reindex can always fix file↔DB inconsistency

</specifics>

<deferred>
## Deferred Ideas

- Drop JSON tags/people columns after junction tables proven stable — future cleanup phase
- Remove app-level cascade code after FK cascade proven reliable — future cleanup phase
- Schema version tracking table — not needed now but consider if migrations grow more complex
- sb-migrate standalone command — unnecessary with auto-migrate, but could be useful for manual control later

</deferred>

---

*Phase: 32-architecture-hardening*
*Context gathered: 2026-03-21*
