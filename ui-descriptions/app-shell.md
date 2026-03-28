# App Shell

## Intent
The persistent chrome that wraps every view. Provides global navigation, search, capture entry points, and connection status. Users spend no meaningful time "in" the shell — it should be invisible infrastructure.

## Layout
Full-height flex column: Topbar → TabBar → content area (fills remaining height).
Content area is a horizontal flex: optional Sidebar (notes view only) + main content + optional RightPanel (notes view only).

---

## Topbar

**Intent:** Global search and primary capture actions. Always visible.

**Components:**
- **Search input** — text input with magnifier icon; Enter triggers search, Escape clears. Searches note titles and bodies.
- **Search mode selector** — dropdown: Hybrid (default), BM25 (keyword), Semantic (embedding). Most users never touch this.
- **New Note button** — opens NewNoteModal. Primary creation action.
- **Smart Capture button** — sparkles icon, no label. Opens SmartCaptureModal. Purpose unclear without tooltip.
- **Batch Capture button** — folder-sync icon, no label. Opens BatchCaptureModal. Purpose unclear without tooltip.
- **SSE status dot** — green/red dot, top-right. Indicates live connection to backend. Small and unobtrusive is correct.

**Known issues:**
- Smart Capture and Batch Capture are icon-only with no visible label; new users won't know what they do.
- Search mode selector is expert-only noise; should be collapsed or hidden by default.

---

## TabBar

**Intent:** Primary navigation between the app's main sections.

**Tabs (in order):** Notes · Action Items · People · Meetings · Projects · Intelligence · Inbox · Links

**Behavior:** Active tab has a bottom border highlight and bold text. Inactive tabs are muted.

**Known issues:**
- 8 tabs is too many for a single horizontal bar — causes crowding at normal window widths.
- Tab order doesn't reflect frequency of use (Notes and Inbox should be most prominent).
- No icons — pure text tabs are harder to scan quickly.
