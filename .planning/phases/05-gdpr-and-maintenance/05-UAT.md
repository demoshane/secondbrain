---
status: complete
phase: 05-gdpr-and-maintenance
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md]
started: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. sb-forget deletes person file and sole-reference meeting
expected: Run sb-forget alice-smith. Person file deleted, sole-ref meeting deleted, shared meeting survives.
result: pass

### 2. sb-forget cleans backlinks from surviving notes
expected: Lines containing the slug are removed from surviving note bodies.
result: pass

### 3. sb-search returns zero results after forget
expected: sb-search alice-smith returns no results after erasure.
result: pass

### 4. sb-forget logs erasure event in audit_log
expected: audit_log has event_type=forget, detail=person:alice-smith, note_path=NULL.
result: pass

### 5. sb-read denied without passphrase
expected: sb-read on PII note with SB_PII_PASSPHRASE unset prints "Access denied" and exits 1.
result: pass

### 6. sb-read denied with wrong passphrase
expected: Wrong passphrase at prompt prints "Access denied" and exits 1.
result: pass

### 7. sb-read granted with correct passphrase
expected: Correct passphrase prints note content and exits 0.
result: pass

### 8. sb-read on public note needs no passphrase
expected: Public note prints immediately, no prompt, exits 0.
result: pass

### 9. sb-read logs read event in audit_log on success
expected: Successful PII read writes event_type=read with note path to audit_log.
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
