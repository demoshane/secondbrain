# Phase 31 — Host Verification Plan

## Automated Steps

### 1. Build & Deploy
```bash
source "$HOME/.nvm/nvm.sh"
npm run build --prefix ~/second-brain/frontend
uv tool install ~/second-brain --reinstall
kill $(lsof -ti :37491) 2>/dev/null
~/.local/bin/sb-api > /tmp/sb-api.log 2>&1 &
sleep 3
lsof -i :37491
```

### 2. Run Test Suite
```bash
uv run pytest tests/ -q --tb=short
uv run pytest tests/test_smart_capture.py -v --tb=short
```

### 3. API Verification
```bash
# Smart Capture endpoint
curl -s -X POST http://localhost:37491/smart-capture \
  -H 'Content-Type: application/json' \
  -d '{"content": "# Test Meeting\nDiscussed roadmap with Alice.\n---\n# Alice\nRole: Lead"}' | python3 -m json.tool

# Brain health (verify no regressions)
curl -s http://localhost:37491/brain-health | python3 -m json.tool
```

### 4. Playwright GUI Verification
- Navigate to `http://localhost:37491/ui`
- Click **Sparkles** icon button in topbar (Smart Capture)
- Paste multi-section text into textarea
- Click **Capture** button
- Verify: loading spinner shows, then results list appears with type-colored badges
- Verify: each result shows check icon, type badge (meeting/person/idea/note), and title
- Click **Done** to close modal

### 5. MCP Tool Verification
Call `sb_capture_smart` via Claude Desktop with:
```
Met with Alice Johnson to discuss Q2 roadmap.
Decision: prioritize search feature.
Action: Alice drafts spec by Friday.
---
Alice Johnson — VP Engineering at Acme.
```
Verify response has: `status: created`, `count >= 2`, `capture_session`, `notes` array with titles/types/paths.

## Human Verification Checklist
(Only after all automated checks pass)

1. [ ] Smart Capture modal opens from topbar Sparkles button
2. [ ] Pasting meeting notes and clicking Capture produces segmented results
3. [ ] Result badges show correct colors (meeting=blue, person=green, idea=yellow)
4. [ ] Done button closes modal and resets state
5. [ ] New notes appear in sidebar after capture
6. [ ] Overdue actions appear in sb_recap output (if any overdue items exist)
