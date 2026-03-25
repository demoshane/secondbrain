---
created: 2026-03-23T12:00:00.000Z
title: Add action item creation from person note view
area: ui
files:
  - frontend/src/components/PeoplePage.tsx
  - frontend/src/components/RightPanel.tsx
  - engine/api.py
---

## Problem

When viewing a person note in the GUI, there's no way to add a new action item directly for that person. Users have to navigate away or use a different flow.

## Solution

Add an "Add action item" button/input in the person note view (or sidebar when a person note is active) that creates an action item pre-assigned to that person. Should follow the same pattern as existing action item creation but with assignee pre-populated.
