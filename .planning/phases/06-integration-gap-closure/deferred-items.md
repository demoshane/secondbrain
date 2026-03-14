# Deferred Items — Phase 06

## Pre-existing XPASS in test_reindex.py

**Discovered during:** Plan 06-02, Task 1
**File:** tests/test_reindex.py — `test_reindex_stores_absolute_paths`
**Issue:** Test marked `xfail(strict=True, reason="SEARCH-01 path fix not applied yet")` but the underlying SEARCH-01 fix was already applied in a prior session. The xfail marker needs to be removed so the test can pass normally.
**Action needed:** Remove `@pytest.mark.xfail` from `test_reindex_stores_absolute_paths` in tests/test_reindex.py.
**Impact:** Full suite currently fails with XPASS(strict) when run with -x. Individual module runs are unaffected.
