---
created: 2026-03-16T13:46:41.990Z
title: Link persons to notes in sidebar
area: ui
files:
  - engine/gui/static/
---

## Problem

No way to associate person notes with a regular note from the GUI. Connections between people and content exist in the second brain data model (via `people` frontmatter field) but are not surfaced or editable in the sidebar.

## Solution

Add a "People" section to the note sidebar that:
- Shows any person notes already linked in the note's frontmatter `people` field
- Allows adding/removing person links via search-and-select UI
- Renders each linked person as a clickable chip/tag that navigates to their person note
- Writes changes back to frontmatter `people` list following second brain conventions (slug or title references)
- Follows the same linking model used elsewhere in the brain (wiki-links / frontmatter arrays)
