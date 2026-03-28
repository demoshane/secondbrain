# Intelligence Page

## Intent
The brain's health and awareness dashboard. Surfaces three things: (1) a generated recap of recent activity, (2) brain health issues requiring attention (orphans, broken links, duplicates, empty notes), (3) stale notes that haven't been touched in a while. Secondary: action items and Chrome extension setup. Think of it as "what does my brain need from me right now?"

## Layout
Single scrollable column. Sections stacked vertically as bordered cards.

## Components

### Recap section
- **Generate Recap button** — triggers AI-generated summary of recent brain activity. Displayed as rendered markdown. Empty state prompts user to generate.

### Brain Health section
- **Score** — large number /100. Computed from orphan ratio, broken link ratio, duplicate ratio.
- **Orphaned Notes** (collapsible) — notes with no incoming links and no tags/people. Count badge. Each title is a clickable link → opens note in Notes view.
- **Empty Notes** (collapsible) — notes with no body content. Each title clickable.
- **Broken Links** (collapsible) — relationship entries pointing to missing files. Shows `source filename → target filename` (source is clickable, target shown in muted red). "Repair all broken links" button runs all three repair actions (self-links, dangling, stale person backlinks).
- **Duplicate Candidates** (collapsible) — pairs of notes with high embedding similarity. Shows `filename / filename (similarity%)`. Both filenames are clickable. Per-pair Merge and Smart Merge buttons. "Smart Merge All" bulk button.

### Stale Notes section
- List of notes not updated recently. Title + last-updated date. Titles are clickable.

### Action Items section
- Open action items across the brain (subset — same ActionItemList component used elsewhere).

### Chrome Extension section
- API reachability status dot + installation instructions (expandable).

## Known issues
- The page mixes health/maintenance concerns (brain health) with daily workflow concerns (action items, recap) without clear visual hierarchy — the most important thing is not obvious.
- Brain health score is prominent but doesn't tell the user what to do next.
- Section collapse state resets on every page visit.
- Chrome Extension section feels out of place here — it's a one-time setup item mixed with daily-use content.
