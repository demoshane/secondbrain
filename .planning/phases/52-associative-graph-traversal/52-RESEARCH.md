# Phase 52: Research — Graph View (52-03 focus)

**Researched:** 2026-04-03
**Focus:** Frontend Graph View page (52-03). Plans 52-01/52-02 already exist.

## RESEARCH COMPLETE

## 1. Frontend Stack

- **Framework:** React 19 + Vite 8 + TypeScript 5.9 + Tailwind CSS 3.4
- **UI:** shadcn/ui (Radix primitives), lucide-react icons, sonner toasts
- **Build:** `tsc -b && vite build` → output to `dist/` served by Flask
- **State:** Context-based (UIContext, NoteContext, SSEContext)
- **No D3 dependency yet** — must be added to `frontend/package.json`

## 2. Page Architecture Pattern

Each "view" follows a consistent pattern:
1. **UIContext.tsx** defines `type View` union — add `'graph'` to it
2. **TabBar.tsx** has a `TABS` array — add graph entry with icon
3. **App.tsx** has view-switching conditional — add `GraphPage` branch
4. Page components are standalone files in `frontend/src/components/`

Pattern: list-detail layout (sidebar list + detail panel), or full-bleed content area.
For the graph view, full-bleed is more appropriate (D3 canvas needs max space).

## 3. API Endpoint Needed

No `/graph` endpoint exists. Need a new Flask route:

```
GET /graph?start=<path>&depth=2&types=<comma-separated>
```

Returns `{ nodes: [...], edges: [...] }` from `traverse_graph()` (Plan 52-01).

For the "full graph" overview (no start node), need:

```
GET /graph/overview
```

Returns all relationships as nodes + edges, limited to a reasonable count.

## 4. D3 Force-Directed Graph Considerations

### Library Choice
- `d3-force` + `d3-selection` + `d3-zoom` (modular D3 imports, not full d3 bundle)
- React integration: Use `useRef` for the SVG container, D3 manages the DOM inside it
- Don't fight React's rendering — let D3 own the SVG, React owns controls/panels

### Layout
- `d3.forceSimulation()` with forces: link, charge (repel), center, collision
- Node radius based on connection count (more connected = larger)
- Edge width based on relationship strength
- Color coding by note type or relationship type

### Interaction
- **Zoom/Pan:** `d3.zoom()` on SVG container
- **Click node:** Show note details in a side panel or tooltip
- **Filter:** By relationship type, note type, depth
- **Search:** Highlight a specific node and its neighborhood

### Performance
- With <5000 notes, force simulation runs fine
- For large graphs: show only neighborhood (start node + N hops), not entire graph
- Canvas rendering (`d3-force` + canvas) if SVG performance is an issue (unlikely at this scale)

## 5. Data Shape (from Plan 52-01)

`traverse_graph()` returns:
```json
{
  "nodes": [{"path": "...", "title": "...", "depth": 0, "activation": 1.0}],
  "edges": [{"source": "...", "target": "...", "type": "wiki-link", "strength": 1.0}]
}
```

This maps directly to D3 force graph data:
- Nodes → `simulation.nodes()`
- Edges → `simulation.force("link").links()`

## 6. No Visily Design Exists

The Graph View is new (not part of the original 8-page Visily redesign).
Per CLAUDE.md: "If no design exists, stop and ask before proceeding."

**Recommendation:** The plan should follow existing dark-palette conventions
(same CSS vars, same shadcn components for controls), with D3 handling the
graph canvas. The page layout should match the full-bleed pattern used by
IntelligencePage/PerformancePage (header + content area, no sidebar list).

## 7. Files to Create/Modify

| File | Action |
|------|--------|
| `frontend/package.json` | Add `d3`, `@types/d3` deps |
| `frontend/src/components/GraphPage.tsx` | New page component |
| `frontend/src/components/GraphCanvas.tsx` | D3 force-directed SVG component |
| `frontend/src/contexts/UIContext.tsx` | Add `'graph'` to View type |
| `frontend/src/components/TabBar.tsx` | Add graph tab |
| `frontend/src/App.tsx` | Add GraphPage view branch |
| `frontend/src/types.ts` | Add GraphNode, GraphEdge types |
| `engine/api.py` | Add `/graph` and `/graph/overview` endpoints |

## Validation Architecture

### Testable Requirements
1. Graph tab visible in TabBar and navigates to graph view
2. D3 force simulation renders nodes and edges in SVG
3. Zoom/pan works via mouse wheel and drag
4. Click node shows detail panel
5. Filter by relationship type works
6. API `/graph/overview` returns valid node/edge JSON
7. API `/graph?start=<path>` returns traversal subgraph
