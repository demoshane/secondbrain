# Links Page

## Intent
Library of saved web links — URLs captured via the Chrome extension or `sb_capture_link` MCP tool. Separate from general notes because links have web-specific metadata (domain, URL, description). Primary use: find a saved article or resource, read the captured summary, and open the original URL.

## Layout
Two-column split: link list (left, fixed 320px) + link detail (right, flex).

## Components

### Left column — Link list
- **Search input** — filters by title and description as you type.
- **Active tag filter badge** — shown below search when a tag filter is active; clicking removes it.
- **Link list** — each item shows: title · domain · date · description (truncated) · tag badges. Clicking a tag badge sets the tag filter. Clicking the row opens the detail panel.

### Right column — Link detail
Empty state: "Select a link to view details."

When selected:
- **Title heading** + domain + date.
- **Visit Link button** — opens original URL in new tab.
- **Tag badges** — read-only display of tags.
- **Body** — captured content/summary displayed as `<pre>` (plain text, not markdown).

## Known issues
- Body is rendered as `<pre>` plain text, not markdown — formatting is lost even when the captured content has structure.
- No way to edit a link's title, tags, or body from this page.
- No way to delete a link from this page.
- No "open as note" button — can't navigate to the underlying note file.
- Empty state when no links exist references MCP tool by internal name (`sb_capture_link`) — not user-friendly.
- Tag filter only supports single active tag — no multi-tag filtering.
