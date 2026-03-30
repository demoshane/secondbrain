---
status: partial
phase: 44-ai-provider-settings-groq-api-key-via-macos-keychain-all-local-ollama-toggle-auto-routing-logic-settings-ui
source: [44-VERIFICATION.md]
started: 2026-03-30T00:00:00Z
updated: 2026-03-30T00:00:00Z
---

## Current Test

[awaiting human testing — run `make dev` first]

## Tests

### 1. AI Provider section renders in Settings modal
expected: Open Settings modal → "AI Provider" section visible with Groq key input (unconfigured state) and all-local toggle
result: [pending]

### 2. Key save triggers auto-connectivity test and shows configured badge
expected: Paste a `gsk_...` key, click Save → auto-test runs, green "Configured" badge + connectivity result appears
result: [pending]

### 3. All-local toggle visually disables feature toggles
expected: Enable "All-local mode" toggle → the 4 Groq feature toggles become `opacity-50 pointer-events-none` (grayed out, unclickable)
result: [pending]

### 4. Fallback toast end-to-end
expected: When Groq is configured but fails (e.g. wrong key), Ask Brain falls back to Claude and shows amber toast "Groq unavailable — used fallback model"
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
