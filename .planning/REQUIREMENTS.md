# Requirements: Second Brain

**Defined:** 2026-03-16
**Milestone:** v3.0 — GUI Overhaul & Polish
**Core Value:** Zero-friction capture that surfaces the right context at the right moment

## v3.0 Requirements

### GUI Fixes (GUIX)

- [x] **GUIX-01**: New notes and edits to existing notes are reflected in the GUI without restarting the application (live refresh)
- [x] **GUIX-02**: Title edits made in the GUI are reflected immediately without restart
- [x] **GUIX-03**: Note content renders as formatted HTML (not raw markdown text)
- [x] **GUIX-04**: User can scroll the note content area with the mouse wheel
- [x] **GUIX-05**: Backlinks display correctly in the note viewer
- [x] **GUIX-06**: User can delete a note from the GUI; deletion cascades to backlinks and FTS5 index

### GUI Navigation & UX (GNAV)

- [x] **GNAV-01**: Sidebar shows collapsible section navigation by note type/folder (replaces flat list)
- [x] **GNAV-02**: User can edit note tags and metadata directly from the GUI
- [x] **GNAV-03**: User can filter notes by tag in search and browse

### GUI Features (GUIF)

- [x] **GUIF-01**: User can capture a file from the GUI or by pointing sb-capture at an external file path (e.g., a presentation created by Claude Code); file saved to files/ and indexed
- [x] **GUIF-02**: User can trigger on-demand weekly recap generation from the Intelligence panel

### Engine / Logic (ENGL)

- [x] **ENGL-01**: A single capture trigger captures all relevant new items in batch (not just the first)
- [x] **ENGL-02**: Search hybrid ranking tuned for improved relevance (RRF weights, query normalization)
- [x] **ENGL-03**: AI recap and action extraction quality improved (better prompts, deduplication, accuracy)
- [x] **ENGL-04**: Brain health dashboard shows orphan notes, broken links, and potential duplicates
- [x] **ENGL-05**: Brain health score visible via CLI (sb-health) or GUI

### GUI Pages (GPAG)

- [x] **GPAG-01**: App has a top tab bar with tabs for Notes, Action Items, and extensible future pages
- [x] **GPAG-02**: Dedicated Action Items page shows all action items with status, due date, and assignee filtering
- [x] **GPAG-03**: Action items can be assigned to a person note (assignee_path column on action_items table)
- [x] **GPAG-04**: Person note view includes a "My Actions" section listing all action items assigned to that person

## Future Requirements (v4.0)

### Platform

- **PLAT-01**: Encryption at rest for brain content (Fernet) and SQLite index (SQLCipher)
- **PLAT-02**: Windows GUI support (pywebview + WebView2 compatibility)
- **PLAT-03**: Mobile read-only access (PWA or React Native companion app)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Obsidian sync | Third-party dependency; no clear benefit over native CLI |
| Calendar sync | OAuth complexity; out of scope |
| Team / shared brain | Single-user system |
| Cloud-hosted brain | Local-first is a hard constraint |
| Real-time collaboration | Single-user |
| Public sharing | Brain content is private by design |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GUIX-01 | Phase 21 | Complete |
| GUIX-02 | Phase 20 | Complete |
| GUIX-03 | Phase 20 | Complete |
| GUIX-04 | Phase 20 | Complete |
| GUIX-05 | Phase 20 | Complete |
| GUIX-06 | Phase 22 | Complete |
| GNAV-01 | Phase 23 | Complete |
| GNAV-02 | Phase 23 | Complete |
| GNAV-03 | Phase 23 | Complete |
| GUIF-01 | Phase 24 | Complete |
| GUIF-02 | Phase 25 | Complete |
| ENGL-01 | Phase 24 | Complete |
| ENGL-02 | Phase 26 | Complete |
| ENGL-03 | Phase 26 | Complete |
| ENGL-04 | Phase 25 | Complete |
| ENGL-05 | Phase 25 | Complete |

| GPAG-01 | Phase 27.2 | Not started |
| GPAG-02 | Phase 27.2 | Not started |
| GPAG-03 | Phase 27.2 | Not started |
| GPAG-04 | Phase 27.2 | Not started |

**Coverage:**
- v3.0 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 — traceability filled in after roadmap creation*
