# Phase 45 — Host Verification Plan

## Environment: HOST only

Run these steps on your host machine (not devcontainer).

---

## Step 1: Build + reinstall + restart services

```bash
cd ~/second-brain
make dev
```

Expected: builds frontend, reinstalls uv tool, restarts sb-api (port 37491).

---

## Step 2: Generate first benchmark result

```bash
sb-perf --json | head -5
```

Expected: JSON output with `run_at` and `tool_results` keys. No crash, exits 0.

---

## Step 3: Open GUI

Open http://localhost:37491/ui in your browser.

---

## Step 4: Verify Performance tab placement

- Look at TabBar across the top
- Confirm: Notes | Actions | People | Meetings | Projects | Intelligence | **Performance** | Inbox | Links
- Performance (Gauge icon) must be AFTER Intelligence and BEFORE Inbox

---

## Step 5: Click Performance tab

- Summary table should appear with columns: Tool | Latest | Previous | Delta | Limit | Status
- Status badges should be green (✓ pass), amber (⚠ warn), or red (✗ error)
- Delta column shows `--` on first run (no previous)

---

## Step 6: Generate second run + verify delta

```bash
sb-perf
```

Then refresh the GUI. The Delta column should now show `+Xms` or `-Xms` values.

---

## Step 7: Verify 30-Day Trend section

- After 2+ runs: sparkline charts should appear in the "30-Day Trend" section
- After 1 run: "Not enough data for trends" shown (only 1 data point per tool)

---

## Pass criteria

- [ ] Performance tab visible in TabBar after Intelligence
- [ ] Summary table shows all tool results with correct columns
- [ ] Status coloring correct (green/amber/red)
- [ ] Delta shows `--` on first run, `+/-Xms` on second run
- [ ] 30-Day Trend section renders (sparklines or "Not enough data")
- [ ] No JavaScript errors in browser console

---

## Report back

Type "approved" to close the checkpoint, or describe any issues.
