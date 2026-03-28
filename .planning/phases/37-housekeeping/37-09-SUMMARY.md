---
plan: 37-09
status: complete
---

## Changes

- `frontend/src/components/ActionItemList.tsx`: widened `people` prop from `Note[]` to `{ path: string; title: string }[]`; removed `Note` import.
- `frontend/src/components/PeoplePage.tsx`: removed `peopleNotes` state and `/notes` fetch; changed `people={peopleNotes}` → `people={people}` (uses `/persons` API response directly); added `setDueDate` handler; wired `onSetDueDate={setDueDate}` into ActionItemList.

## Outcome

Action items on PeoplePage no longer vanish after assigning a person — the people dropdown is now sourced from `/persons` (full list), not the capped `/notes` endpoint. Date picker is wired. TypeScript compiles clean.
