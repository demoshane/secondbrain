# Phase 34: GUI Management Productivity - Research

**Researched:** 2026-03-22
**Domain:** React/TypeScript frontend (shadcn/ui + Radix), Flask API, FastMCP
**Confidence:** HIGH

## Summary

Phase 34 is a pure frontend-heavy phase with two thin backend additions (new API endpoints + one MCP tool). The codebase is well-established — patterns exist for everything needed. The main work is extraction (pull ActionItemList out of ActionsPage), extension (add cascade warning to DeleteNoteModal pattern), and wiring (connect new components to existing hooks/contexts).

No greenfield architecture decisions are needed. All decisions are locked in CONTEXT.md. The UI contract is fully specified in 34-UI-SPEC.md. The only new npm deps are `cmdk@1.1.1` and `sonner@2.0.7` — both absent from package.json today.

**Primary recommendation:** Follow the existing modal/component patterns exactly; build new components first, then wire them into existing pages. The backend endpoints (`POST /people`, `DELETE /people/<path>`, `GET /tags`) are the critical path — frontend can't be tested without them.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Action Items (GUI-01, GUI-02)**
- D-01: Build a shared `ActionItemList` component (toggle done, assignee picker) — embed in NoteViewer, IntelligencePage, RightPanel, any other note-context surface. No duplicate per-page implementations.
- D-02: Source note link on ActionsPage: `ExternalLink` icon button (lucide-react), shown conditionally only when `note_path` is present. Clicking opens note in NoteViewer.
- D-03: "Link persons to notes in sidebar" todo folded into scope — covered by ActionItemList + NoteViewer integration.

**Cmd+K Palette (GUI-03)**
- D-04: Add `cmdk` library. Scope: navigation commands (jump to note by title, switch pages) + capture commands (quick-capture, trigger SmartCaptureModal).
- D-05: Trigger: both `Cmd+K` (Mac) and `Ctrl+K` (cross-platform).

**Entity Create/Delete (GUI-04, GUI-07)**
- D-06: Create: modal dialog pattern, consistent with `NewNoteModal`. Required field: name. Optional: role/title for people. People, Meetings, Projects pages all get "New [entity]" button.
- D-07: Delete: cascade warning dialog — show linked data (meeting notes + action items) before confirm. Follows `DeleteNoteModal` structure + adds "linked data" section.
- D-08: `sb_create_person` MCP tool ships alongside GUI create flow, using the same backend endpoint.

**Tag Autocomplete (GUI-06)**
- D-09: Dropdown while typing in tag input in NoteViewer. Pulls from `note_tags` junction table (Phase 32). Keyboard-navigable (arrow keys + Enter). Dismiss on Escape or click-outside.

**Intelligence Actionable Items (GUI-05)**
- D-10: Intelligence page action items rendered via shared `ActionItemList` — interactive (toggle, assignee) in-place, not read-only text.

**Toasts + Inbox Polish (GUI-05, GUI-06)**
- D-11: Toast feedback on mutations: action item toggle, entity create/delete, tag save. `sonner` library.
- D-12: Inbox polish: Claude's discretion on specific improvements.

### Claude's Discretion
- Toast library choice (sonner vs Radix Toast — sonner chosen per UI-SPEC)
- Exact optional fields in entity create modals beyond required name field
- Inbox-specific UI improvements
- Tag autocomplete positioning and max visible suggestions count

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.
- Add tests for git hooks — deferred
- Fix sb_edit wiping YAML frontmatter — separate hotfix
- Fix sb-recap returning nothing — separate hotfix
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GUI-01 | Interactive action items embedded in all note-context surfaces via shared component | ActionItemList extracted from ActionsPage; embed in NoteViewer, IntelligencePage, RightPanel |
| GUI-02 | Actions page shows source note link (icon button) per action item | ExternalLink icon in ActionsPage, conditionally when note_path present; `note_path` already on ActionItem type |
| GUI-03 | Cmd+K command palette for navigation and capture | cmdk@1.1.1 not yet in package.json; pattern defined in UI-SPEC |
| GUI-04 | Entity create flow from People/Meetings/Projects pages | NewEntityModal pattern; backend endpoints POST /people, /meetings, /projects needed |
| GUI-05 | Intelligence page action items interactive, not read-only | ActionItemList replaces static list in IntelligencePage; IntelligencePage currently has no action items section at all — needs fetch + ActionItemList |
| GUI-06 | Tag autocomplete in NoteViewer; toast feedback on mutations | GET /tags endpoint needed; note_tags table exists (Phase 32); sonner@2.0.7 needed |
| GUI-07 | sb_create_person MCP tool | New tool in mcp_server.py; calls same backend endpoint as GUI create flow |
</phase_requirements>

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| React | 19.2.4 | UI framework | Already installed |
| shadcn/ui | n/a (components) | Component primitives | Already initialized — slate base, CSS vars |
| @radix-ui/react-dialog | 1.1.15 | Modal dialogs | Already installed |
| @radix-ui/react-checkbox | 1.3.3 | Checkbox primitive | Already installed |
| @radix-ui/react-select | 2.2.6 | Select primitive | Already installed |
| lucide-react | 0.577.0 | Icon library | Already installed; ExternalLink, Plus available |
| TypeScript | 5.9.3 | Type safety | Already installed |

### New deps required this phase
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| cmdk | 1.1.1 | Command palette primitive | Standard in shadcn/ui ecosystem; used by Vercel, Linear |
| sonner | 2.0.7 | Toast notifications | shadcn-recommended; fits Radix/Tailwind stack |

**Installation:**
```bash
cd /Users/tuomasleppanen/second-brain/frontend && npm install cmdk@1.1.1 sonner@2.0.7
```

**Version verification:** Confirmed via `npm view` — cmdk@1.1.1, sonner@2.0.7 as of 2026-03-22.

---

## Architecture Patterns

### Recommended Component Structure (new files)
```
frontend/src/components/
├── ActionItemList.tsx       # shared; extracted from ActionsPage
├── CommandPalette.tsx       # cmdk-based; mounted globally in App.tsx
├── NewEntityModal.tsx       # follows NewNoteModal.tsx exactly
├── DeleteEntityModal.tsx    # extends DeleteNoteModal.tsx + cascade section
└── TagAutocomplete.tsx      # wraps tag input in NoteViewer
```

### Pattern 1: Shared ActionItemList extraction
**What:** Pull `toggleDone` + `assignTo` + the table rows out of ActionsPage into a self-contained `ActionItemList` component that accepts `actions: ActionItem[]`, `people: Note[]`, `onToggle`, `onAssign` as props.
**When to use:** Anywhere a note-context surface needs to show interactive action items.

Existing ActionsPage code to extract (confirmed from source):
```typescript
// Source: frontend/src/components/ActionsPage.tsx
const toggleDone = async (action: ActionItem) => {
  await fetch(`${getAPI()}/actions/${action.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ done: !action.done }),
  })
  loadActions()
}

const assignTo = async (action: ActionItem, assigneePath: string) => {
  await fetch(`${getAPI()}/actions/${action.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assignee_path: assigneePath === 'none' ? null : assigneePath }),
  })
  loadActions()
}
// Assignee select: h-7 w-36 text-xs (keep these exact dimensions)
```

### Pattern 2: Modal creation (NewNoteModal contract)
**What:** Dialog + DialogContent + DialogHeader + DialogTitle + Input (Enter submits) + button pair (outline Discard + primary Create/Creating…).
**Confirmed in source:** NewNoteModal.tsx — exact pattern to follow for NewEntityModal.

### Pattern 3: Modal deletion (DeleteNoteModal contract)
**What:** Same Dialog structure + outline dismiss button + destructive Delete/Deleting… button. Extend by adding a "linked data" `<p className="text-sm text-muted-foreground">` section between title and buttons when counts > 0.
**Confirmed in source:** DeleteNoteModal.tsx — uses `useNoteActions()` hook; entity delete will call new API endpoints directly.

### Pattern 4: API fetch
**What:** `fetch(getAPI() + '/endpoint', { method, headers, body })` — consistent across all components.
**Confirmed in source:** ActionsPage, NoteViewer, PeoplePage all use this pattern.

### Pattern 5: cmdk CommandPalette
**What:** Global `<Command>` overlay mounted once in App.tsx. Keydown listener: `(e.metaKey || e.ctrlKey) && e.key === 'k'`. Groups: Navigation + Capture.
**Key:** cmdk handles keyboard navigation natively — no manual arrow key management needed inside the palette.

### Pattern 6: Tag autocomplete (TagAutocomplete)
**What:** Wraps existing tag `<input>` in NoteViewer. On first keystroke: fetch `GET /tags` once, filter client-side for subsequent chars. Absolute-positioned `<ul>` dropdown below input.
**Note:** NoteViewer currently has two tag input paths (editing existing tag inline + adding new tag). TagAutocomplete wraps the "adding new tag" input (`addingTag` state path) specifically.

### Pattern 7: sonner Toaster
**What:** Mount `<Toaster />` once in App.tsx (bottom-right, 3000ms). Call `toast.success()` / `toast.error()` after any mutation.
**Key import:** `import { toast } from 'sonner'` in components; `import { Toaster } from 'sonner'` in App.tsx.

### Anti-Patterns to Avoid
- **Duplicate toggle/assign implementations:** Do NOT keep a separate implementation in ActionsPage after extracting ActionItemList — ActionsPage must use the shared component.
- **Hardcoded entity type strings in NewEntityModal:** Accept `entityType` prop; derive modal title and dismiss copy from it — don't fork the component per entity type.
- **Fetching people list multiple times:** ActionItemList will need the people list for the assignee picker — pass it as a prop from the parent rather than fetching inside ActionItemList (parent already has it).
- **`note_path` type mismatch:** `ActionItem.note_path` is typed as `string` in types.ts — it is always present (never null) based on DB schema; the ExternalLink button is shown conditionally when the value is non-empty.

---

## Backend: New Endpoints Required

| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `GET /tags` | GET | Return all unique tags for autocomplete | Query `note_tags` table (Phase 32 — confirmed exists in db.py) |
| `POST /people` | POST | Create a new person note | Body: `{name, role?}` — returns `{path}` |
| `DELETE /people/<path>` | DELETE | Delete a person note + cascade | Cascade: unassign action items, remove from note_people; returns `{}` |
| `POST /meetings` | POST | Create a new meeting note | Body: `{name}` — returns `{path}` |
| `DELETE /meetings/<path>` | DELETE | Delete a meeting note | Returns `{}` |
| `POST /projects` | POST | Create a new project note | Body: `{name}` — returns `{path}` |
| `DELETE /projects/<path>` | DELETE | Delete a project note | Returns `{}` |

**Pre-delete cascade query (for DeleteEntityModal warning):**
Entity pages need to fetch linked counts before showing the delete modal. A new `GET /people/<path>/links` (or inline in the delete response) should return `{meeting_count, action_count}`. Simplest approach: add a `GET /<entity_type>/<path>/links` endpoint returning counts.

**`sb_create_person` MCP tool:** Calls the same `POST /people` backend endpoint. No separate persistence path — MCP tool is a thin wrapper.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Command palette keyboard nav | Custom keydown state machine | `cmdk` Command primitive | cmdk handles focus, arrow keys, Enter, groups, filtering natively |
| Toast positioning + animation | CSS + manual state | `sonner` Toaster | Battle-tested, auto-dismiss, stacking, accessible |
| Dialog accessibility | Manual focus trap, aria attrs | Radix Dialog (already installed) | Focus trap, escape, aria-modal all built in |
| Tag filtering | Server-side search per keystroke | Fetch once, filter client-side | GET /tags returns small payload; client filter is instant |

---

## Common Pitfalls

### Pitfall 1: Deploy pipeline not run after frontend changes
**What goes wrong:** Frontend source changes are invisible in the running GUI.
**Why it happens:** GUI is served by the installed `uv tool` binary, not source. Three caches must be updated.
**How to avoid:** Every plan touching `frontend/src/**` MUST include the full deploy pipeline:
```bash
cd /Users/tuomasleppanen/second-brain/frontend && npm run build
cd /Users/tuomasleppanen/second-brain && /Users/tuomasleppanen/.local/bin/uv tool install . --reinstall
kill $(lsof -ti :37491) 2>/dev/null; sleep 1
/Users/tuomasleppanen/.local/bin/sb-api > /tmp/sb-api.log 2>&1 &
sleep 3
```
**Warning signs:** Changes exist in source but GUI behavior is unchanged.

### Pitfall 2: ActionItemList people list double-fetch
**What goes wrong:** ActionItemList fetches `/notes` internally to get the people list, causing N fetches when embedded in multiple surfaces simultaneously.
**Why it happens:** Component is self-contained but parent already has the list.
**How to avoid:** `people` list is a required prop; parent fetches once and passes down.

### Pitfall 3: cmdk not yet in package.json
**What goes wrong:** Import error at build time — `cmdk` is not installed.
**Why it happens:** It's a net-new dependency; confirmed absent from `frontend/package.json`.
**How to avoid:** First task in the Cmd+K plan must `npm install cmdk@1.1.1 sonner@2.0.7`.

### Pitfall 4: IntelligencePage has no action items section today
**What goes wrong:** Plan assumes ActionItemList is a drop-in replacement for existing code in IntelligencePage; there is nothing to replace.
**Why it happens:** IntelligencePage (confirmed from source, lines 31–80) fetches nudges and health but has no action items fetch or section.
**How to avoid:** Plan must add: (1) fetch `/actions` in IntelligencePage, (2) render ActionItemList with the result.

### Pitfall 5: PeoplePage "Open Actions" section is static checkboxes (not shared component)
**What goes wrong:** Assuming the shared ActionItemList is already used in PeoplePage.
**Why it happens:** PeoplePage (confirmed from source, lines 209–229) renders a plain `<ul>` with `<input type="checkbox" disabled>` — read-only and not wired to toggle.
**How to avoid:** The ActionItemList integration in PeoplePage replaces this entire static section with the interactive shared component.

### Pitfall 6: note_tags table populated by Phase 32 migration only
**What goes wrong:** GET /tags returns empty on a fresh or old DB that hasn't run the migration.
**Why it happens:** `migrate_add_note_tags_table` populates from JSON tags column during migration; if migration never ran, table exists but is empty.
**How to avoid:** The `GET /tags` endpoint falls back to querying the JSON `tags` column if `note_tags` returns nothing — or document that `sb-reindex` must be run after Phase 32.

### Pitfall 7: Entity delete cascade must clear action item assignee_path
**What goes wrong:** Deleting a person leaves orphaned `assignee_path` references in `action_items`.
**Why it happens:** No FK cascade on `action_items.assignee_path` (confirmed — Phase 32 architecture notes).
**How to avoid:** The DELETE /people/<path> endpoint must `UPDATE action_items SET assignee_path = NULL WHERE assignee_path = ?` before deleting the note.

---

## Code Examples

### cmdk CommandPalette skeleton
```typescript
// Source: cmdk docs (https://cmdk.paco.me), confirmed pattern in 34-UI-SPEC.md
import { Command } from 'cmdk'

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <div className={cn('fixed inset-0 z-50 bg-black/50', !open && 'hidden')} onClick={onClose}>
      <div className="fixed left-1/2 top-1/3 -translate-x-1/2 w-full max-w-lg" onClick={e => e.stopPropagation()}>
        <Command className="border shadow-md rounded-lg bg-popover">
          <Command.Input placeholder="Type a command or search…" />
          <Command.List>
            <Command.Empty>No matching notes or commands.</Command.Empty>
            <Command.Group heading="Navigation">
              {/* navigation items */}
            </Command.Group>
            <Command.Group heading="Capture">
              {/* capture items */}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  )
}
```

### sonner Toaster mount (App.tsx addition)
```typescript
// Source: sonner docs (https://sonner.emilkowal.ski)
import { Toaster } from 'sonner'
// Inside App return:
<Toaster position="bottom-right" duration={3000} />
// Usage in components:
import { toast } from 'sonner'
toast.success("Marked complete")
toast.error("Something went wrong — try again")
```

### GET /tags backend endpoint
```python
# engine/api.py — new endpoint
@app.get("/tags")
def list_tags():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT tag FROM note_tags ORDER BY tag"
        ).fetchall()
    return jsonify({"tags": [r[0] for r in rows]})
```

### sb_create_person MCP tool skeleton
```python
# engine/mcp_server.py — new tool
@mcp.tool()
def sb_create_person(name: str, role: str = "") -> dict:
    """Create a new person note."""
    # calls same logic as POST /people endpoint
    from engine.capture import capture_note
    result = capture_note(title=name, note_type="people", body=f"Role: {role}" if role else "")
    return {"path": str(result["path"]), "title": name}
```

---

## Environment Availability

Step 2.6: No new external runtime dependencies. All required runtimes confirmed active:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js + npm | Frontend build | Yes | via nvm | — |
| uv | Python env + install | Yes | installed at ~/.local/bin/uv | — |
| sb-api (port 37491) | GUI testing | Yes (running) | current | restart per LEARNINGS.md |
| cmdk | CommandPalette | No (not installed) | 1.1.1 available | — must install |
| sonner | Toast | No (not installed) | 2.0.7 available | — must install |

**Missing dependencies with no fallback:**
- `cmdk` and `sonner` — must be installed as first task in their respective plans.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend); vitest (frontend) |
| Config file | `pyproject.toml` (pytest); `vite.config.ts` (vitest via `test` script) |
| Quick run command | `cd /Users/tuomasleppanen/second-brain && uv run pytest tests/test_api.py tests/test_people.py -q` |
| Full suite command | `cd /Users/tuomasleppanen/second-brain && uv run pytest tests/ -q` |
| Frontend test command | `cd /Users/tuomasleppanen/second-brain/frontend && npm test -- --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUI-01 | ActionItemList renders actions, toggles done, assigns person | unit (vitest) | `npm test -- --run ActionItemList` | ❌ Wave 0 |
| GUI-01 | PUT /actions/:id updates done state | integration (pytest) | `uv run pytest tests/test_api.py -k "action" -x` | ✅ |
| GUI-02 | ExternalLink button present when note_path set, absent otherwise | unit (vitest) | `npm test -- --run ActionsPage` | ❌ Wave 0 |
| GUI-03 | CommandPalette opens on Cmd+K, closes on Escape | unit (vitest) | `npm test -- --run CommandPalette` | ❌ Wave 0 |
| GUI-04 | POST /people creates person note, returns path | integration (pytest) | `uv run pytest tests/test_people.py -k "create" -x` | ✅ (needs test added) |
| GUI-04 | DELETE /people/<path> cascades action item assignee_path | integration (pytest) | `uv run pytest tests/test_people.py -k "delete" -x` | ✅ (needs test added) |
| GUI-05 | IntelligencePage fetches and renders ActionItemList | unit (vitest) | `npm test -- --run IntelligencePage` | ❌ Wave 0 |
| GUI-06 | GET /tags returns distinct tags from note_tags | integration (pytest) | `uv run pytest tests/test_api_tags.py -x` | ✅ |
| GUI-06 | TagAutocomplete shows dropdown, keyboard-navigable | unit (vitest) | `npm test -- --run TagAutocomplete` | ❌ Wave 0 |
| GUI-07 | sb_create_person creates person note via MCP | integration (pytest) | `uv run pytest tests/test_mcp.py -k "create_person" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api.py tests/test_people.py tests/test_api_tags.py -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_people.py` — add `test_create_person` and `test_delete_person_cascade` (file exists, needs new test functions)
- [ ] `tests/test_mcp.py` — add `test_sb_create_person` (file exists, needs new test function)
- [ ] `frontend/src/components/ActionItemList.test.tsx` — covers GUI-01
- [ ] `frontend/src/components/CommandPalette.test.tsx` — covers GUI-03
- [ ] `frontend/src/components/TagAutocomplete.test.tsx` — covers GUI-06
- [ ] `frontend/src/components/ActionsPage.test.tsx` — covers GUI-02 (ExternalLink conditional)
- [ ] `frontend/src/components/IntelligencePage.test.tsx` — covers GUI-05

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 34 |
|-----------|-------------------|
| Never commit automatically — only on explicit ask | Plans must not include auto-commit steps |
| Use `/usr/bin/git -C /path` — bare git broken by scm_breeze | All git commands in plans must use absolute path form |
| Never use WebFetch — use mcp context-mode fetch | Research tool constraint only |
| Large command output (>20 lines) via batch_execute | Verification steps producing large output must use batch_execute |
| Frontend changes require full deploy pipeline | Every plan with frontend changes must include: npm build → uv tool install --reinstall → kill/restart sb-api |
| uv tool install . --reinstall after frontend commit | Mandatory step; stale installed binary silently serves old bundle |
| GUI URL is http://localhost:37491/ui (NOT port 5001) | Playwright tests and manual verify must use port 37491 |
| Intel Mac, Python 3.13 pinned | No M-chip assumptions; no Python version changes |
| Devcontainer: code + pytest only; no GUI/sb-api | If in devcontainer, write VERIFY-HOST.md; label steps [CONTAINER]/[HOST] |
| Read LEARNINGS.md before implementation | Executor agents must read `.claude/LEARNINGS.md` first |

---

## Sources

### Primary (HIGH confidence)
- Direct source read: `frontend/src/components/ActionsPage.tsx` — toggleDone/assignTo patterns
- Direct source read: `frontend/src/components/NewNoteModal.tsx` — modal creation contract
- Direct source read: `frontend/src/components/DeleteNoteModal.tsx` — modal deletion contract
- Direct source read: `frontend/src/components/NoteViewer.tsx` — tag editing patterns
- Direct source read: `frontend/src/components/PeoplePage.tsx` — static actions section (to be replaced)
- Direct source read: `frontend/src/components/IntelligencePage.tsx` — no action items section confirmed
- Direct source read: `frontend/src/App.tsx` — modal mounting pattern
- Direct source read: `frontend/package.json` — confirmed cmdk + sonner absent
- Direct source read: `frontend/src/types.ts` — ActionItem.note_path confirmed as string (not nullable)
- Direct source read: `engine/db.py` — note_tags table confirmed (migrate_add_note_tags_table)
- Direct grep: `engine/api.py` — no create_person/delete_person/list_tags endpoints confirmed absent
- Direct grep: `engine/mcp_server.py` — sb_create_person confirmed absent
- `npm view cmdk version` → 1.1.1 (2026-03-22)
- `npm view sonner version` → 2.0.7 (2026-03-22)

### Secondary (MEDIUM confidence)
- 34-UI-SPEC.md — full design/interaction contract, approved status: draft (checker sign-off pending)
- 34-CONTEXT.md — all implementation decisions locked

### Tertiary (LOW confidence)
- cmdk API shape (Command, CommandInput, CommandList, CommandGroup, CommandItem, CommandEmpty) — based on training knowledge of cmdk v1.x; verify against installed version

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps confirmed from package.json source read and npm view
- Architecture: HIGH — all patterns confirmed from live source reads; no assumptions
- Pitfalls: HIGH — derived from actual source observations (IntelligencePage missing section, PeoplePage static checkboxes, deploy pipeline from LEARNINGS.md)
- Backend endpoints: HIGH — confirmed absent via grep; schema confirmed present

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable stack; npm deps are pinned versions)
