---
created: 2026-03-16T13:46:41.990Z
title: Fix sb_edit wiping YAML frontmatter
area: general
files: []
---

## Problem

`mcp__second-brain__sb_edit` replaces the entire file when called with a `body` parameter, overwriting existing YAML frontmatter with an empty `{}`. This caused the Olli Erinko person note to lose its `title`, `type`, `dates`, `people`, and `tags` fields — rendering as "Object object" in the sidebar. Subsequent `sb_edit` calls to repair the affected file return `IntegrityError`.

## Solution

- Read and merge existing frontmatter before writing, OR
- Expose separate `body` / `metadata` edit parameters so callers can update each independently, OR
- At minimum, validate that frontmatter is never written as `{}` (guard against data loss).
