---
phase: 30-people-graph-hardening
plan: 04
status: complete
duration: 8 min
tasks_completed: 2
files_modified: 4
---

# 30-04 Summary: Enrich /people API + PeoplePage columns

## What shipped

1. **Enriched `/people` API** — correlated subqueries add `org` (from entities JSON), `last_interaction` (MAX meeting date via people column), `mention_count` (non-person notes referencing via people column). Meeting detection uses `type='meeting'` SQL filter.

2. **Updated `PersonSummary` type** — added `org: string`, `last_interaction: string | null`, `mention_count: number`.

3. **PeoplePage table columns** — Name, Org, Last Interaction, Open Actions (per CONTEXT.md locked decision). Detail pane shows Organization, Last Interaction, Mentions, and Open Actions.

4. **Regression tests** — `test_list_people_enriched` (org + last_interaction + mention_count), `test_person_type_isolation` (both 'person' and 'people' types appear).

5. **VERIFY-HOST.md** written for host-side UAT.

## Decisions

- org extracted in Python from entities JSON after SQL fetch (first org entry)
- mention_count excludes person/people type notes (self-references)
- Mention count shown in detail pane, not table (too many columns)

## Verification

- `tests/test_people.py`: 5/5 pass
- `tests/test_entities.py`: 21/21 pass
- `tests/test_mcp.py`: all pass (2 expected xfail)
- Full non-Playwright suite: all pass across 5 batches
- Playwright/GUI tests: host-only (VERIFY-HOST.md)
