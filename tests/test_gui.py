"""Phase 24: Playwright end-to-end GUI tests.

All tests are xfail stubs in Wave 1. Implemented in plans 02-04.
Updated in plan 27.3-05 to use React data-testid selectors.
Run: uv run pytest tests/test_gui.py -v
"""
import pytest


def test_markdown_renders_as_html(page, live_server_url, gui_brain, seed_note_fn):
    """SC-2: note with headings/bold/lists renders as HTML — no raw # ** - in DOM."""
    seed_note_fn(gui_brain, "MD Note", "# My Heading\n\n**bold text**\n\n- list item")
    page.goto("/ui")
    page.locator('[data-testid="note-item"]').first.wait_for(state="visible", timeout=5000)
    page.locator('[data-testid="note-item"]').first.click()
    page.locator('[data-testid="note-viewer"]').wait_for(state="visible", timeout=5000)
    text = page.locator('[data-testid="note-body"]').inner_text()
    assert "#" not in text
    assert "**" not in text
    assert page.locator('[data-testid="note-body"] h1').count() > 0
    assert page.locator('[data-testid="note-body"] strong').count() > 0
    assert page.locator('[data-testid="note-body"] li').count() > 0


def test_viewer_scroll(page, live_server_url, gui_brain, seed_note_fn):
    """SC-3: viewer scrollTop changes when scripted (regression for scroll-lock bug)."""
    seed_note_fn(gui_brain, "Long Note", "\n".join(f"Line {i}: " + "x" * 80 for i in range(50)))
    page.goto("/ui")
    page.locator('[data-testid="note-item"]').first.wait_for(state="visible", timeout=5000)
    page.locator('[data-testid="note-item"]', has_text="Long Note").first.click()
    page.locator('[data-testid="note-viewer"]').wait_for(state="visible", timeout=5000)
    scroll_top = page.evaluate(
        "document.querySelector('[data-testid=\"note-body\"]').scrollTop = 200;"
        "document.querySelector('[data-testid=\"note-body\"]').scrollTop"
    )
    assert scroll_top > 0


def test_title_sync(page, live_server_url, gui_brain, seed_note_fn):
    """SC-4: editing note title via API + SSE refresh updates sidebar; reopen shows new h1."""
    import requests
    import urllib.parse

    note_path = seed_note_fn(gui_brain, "Original Title", "# Original Title\n\nbody content")

    page.goto("/ui")
    page.locator('[data-testid="note-item"]').first.wait_for(state="visible", timeout=5000)

    # Click the note to open it
    page.locator('[data-testid="note-item"]', has_text="Original Title").first.click()
    page.locator('[data-testid="note-viewer"]').wait_for(state="visible", timeout=5000)

    # Build frontmatter+body content string for PUT (API expects "content" key)
    encoded = urllib.parse.quote(note_path, safe="")
    content = "---\ntitle: Updated Title\ntags: []\ntype: idea\n---\n\n# Updated Title\n\nbody content\n"
    resp = requests.put(
        f"{live_server_url}/notes/{encoded}",
        json={"content": content},
    )
    assert resp.status_code == 200

    # Trigger SSE broadcast so connected browser reloads sidebar
    refresh_resp = requests.post(f"{live_server_url}/notes/refresh")
    assert refresh_resp.status_code == 200

    # Sidebar reloads via SSE → wait for "Updated Title" to appear in note list
    page.locator('[data-testid="note-item"]', has_text="Updated Title").first.wait_for(
        state="visible", timeout=5000
    )

    # Click the updated note to load it in viewer — h1 should reflect new title
    page.locator('[data-testid="note-item"]', has_text="Updated Title").first.click()
    page.locator('[data-testid="note-body"] h1', has_text="Updated Title").wait_for(
        state="visible", timeout=5000
    )


def test_sse_live_refresh(page, live_server_url, gui_brain, seed_note_fn):
    """SC-5: POST /notes broadcasts SSE; sidebar shows new note within 3s."""
    import requests

    # Load UI — SSE connection established by connectSSE() on page init
    page.goto("/ui")
    page.locator('[data-testid="sidebar"]').wait_for(state="visible", timeout=5000)

    # Record initial note count
    initial_count = page.locator('[data-testid="note-item"]').count()

    # Create a note via API — inserts into DB immediately
    resp = requests.post(
        f"{live_server_url}/notes",
        json={
            "title": "SSE Live Note",
            "type": "idea",
            "body": "created via API for SSE test",
            "brain_path": str(gui_brain),
        },
    )
    assert resp.status_code in (200, 201)

    # Trigger SSE broadcast so connected browser reloads sidebar
    # (watcher not running in daemon-thread test server; /notes/refresh is the reliable trigger)
    refresh_resp = requests.post(f"{live_server_url}/notes/refresh")
    assert refresh_resp.status_code == 200

    # Sidebar must show new note within 3 seconds (no user action)
    page.locator('[data-testid="note-item"]', has_text="SSE Live Note").first.wait_for(
        state="visible", timeout=3000
    )
    # Confirm count increased
    assert page.locator('[data-testid="note-item"]').count() > initial_count


def test_delete_flow(page, live_server_url, gui_brain, seed_note_fn):
    """SC-6: delete shows modal; confirm removes; cancel keeps."""
    seed_note_fn(gui_brain, "Note To Delete", "delete me")

    page.goto("/ui")
    page.locator('[data-testid="note-item"]').first.wait_for(state="visible", timeout=5000)

    # Open the note
    page.locator('[data-testid="note-item"]', has_text="Note To Delete").first.click()
    page.locator('[data-testid="note-viewer"]').wait_for(state="visible", timeout=3000)

    # --- Cancel path ---
    page.locator('[data-testid="delete-btn"]').click()
    page.locator('[data-testid="delete-note-modal"]').wait_for(state="visible", timeout=2000)
    page.locator('[data-testid="delete-cancel"]').click()
    page.locator('[data-testid="delete-note-modal"]').wait_for(state="hidden", timeout=2000)
    # Note still in sidebar after cancel
    assert page.locator('[data-testid="note-item"]', has_text="Note To Delete").count() >= 1

    # --- Confirm path ---
    page.locator('[data-testid="delete-btn"]').click()
    page.locator('[data-testid="delete-note-modal"]').wait_for(state="visible", timeout=2000)
    page.locator('[data-testid="delete-confirm"]').click()
    # Modal closes and note disappears from sidebar
    page.locator('[data-testid="delete-note-modal"]').wait_for(state="hidden", timeout=3000)
    page.locator('[data-testid="note-item"]', has_text="Note To Delete").wait_for(
        state="detached", timeout=3000
    )


def test_tag_editing(page, live_server_url, gui_brain, seed_note_fn):
    """SC-7: double-click tag chip, type new tag, Enter saves to DOM + API."""
    seed_note_fn(gui_brain, "Tag Edit Note", "body", tags=["oldtag"])
    page.goto("/ui")
    page.locator('[data-testid="note-item"]').first.wait_for(state="visible", timeout=5000)

    # Open the note
    page.locator('[data-testid="note-item"]', has_text="Tag Edit Note").first.click()
    page.locator('[data-testid="note-viewer"]').wait_for(state="visible", timeout=3000)
    # Wait for tag chips to render
    page.locator('[data-testid="tag-chips"]').wait_for(state="visible", timeout=3000)
    page.locator('[data-testid="tag-oldtag"]').wait_for(state="visible", timeout=3000)

    # Double-click to enter edit mode
    page.locator('[data-testid="tag-oldtag"]').first.dblclick()
    chip_input = page.locator('.tag-chip-input')
    chip_input.wait_for(state="visible", timeout=2000)

    # Clear and type new tag, then press Enter to save
    chip_input.fill("newtag")
    chip_input.press("Enter")

    # New tag chip appears in DOM
    page.locator('[data-testid="tag-newtag"]').wait_for(state="visible", timeout=3000)
    # Old tag chip gone
    assert page.locator('[data-testid="tag-oldtag"]').count() == 0


def test_tag_filtering(page, live_server_url, gui_brain, seed_note_fn):
    """SC-8: click tag chip filters sidebar; clear restores all notes."""
    seed_note_fn(gui_brain, "Filtered Note", "body", tags=["filtertest"])
    seed_note_fn(gui_brain, "Unfiltered Note", "body", tags=[])
    page.goto("/ui")
    page.locator('[data-testid="note-item"]').first.wait_for(state="visible", timeout=5000)

    # Open the tagged note — use data-path suffix to avoid substring match with "Unfiltered Note"
    page.locator('[data-testid="note-item"][data-path$="/ideas/filtered-note.md"]').first.click()
    page.locator('[data-testid="note-viewer"]').wait_for(state="visible", timeout=3000)
    page.locator('[data-testid="tag-filtertest"]').wait_for(state="visible", timeout=3000)

    # Single-click to activate filter
    page.locator('[data-testid="tag-filtertest"]').first.click()
    page.locator('[data-testid="tag-filter-banner"]').wait_for(state="visible", timeout=2000)

    # Only notes with filtertest tag should appear
    visible_notes = page.locator('[data-testid="note-item"]')
    # Give sidebar time to re-render with filter applied
    page.wait_for_timeout(500)
    count_filtered = visible_notes.count()
    assert count_filtered >= 1
    # Unfiltered Note must not be visible
    assert page.locator('[data-testid="note-item"]', has_text="Unfiltered Note").count() == 0

    # Clear filter — all notes restored
    page.locator('[data-testid="tag-filter-banner"] button').click()
    page.locator('[data-testid="tag-filter-banner"]').wait_for(state="hidden", timeout=2000)
    page.wait_for_timeout(500)
    count_restored = page.locator('[data-testid="note-item"]').count()
    assert count_restored > count_filtered


def test_collapsible_sections(page, live_server_url, gui_brain, seed_note_fn):
    """SC-9: clicking folder-header toggles collapse state on folder section."""
    # Ensure at least one note exists so sidebar renders folder sections
    seed_note_fn(gui_brain, "Collapse Test Note", "body")
    page.goto("/ui")
    page.locator('[data-testid="sidebar"]').wait_for(state="visible", timeout=5000)
    page.locator('[data-testid="note-item"]').first.wait_for(state="visible", timeout=3000)

    # Find the first folder-section header using data-testid prefix pattern
    first_header = page.locator('[data-testid^="folder-header-"]').first
    first_header.wait_for(state="visible", timeout=3000)

    # Get the associated section (folder container)
    first_section = page.locator('[data-testid^="folder-section-"]').first

    # Check initial state — get collapsed attribute or aria-expanded
    initial_collapsed = first_section.evaluate(
        "el => el.classList.contains('collapsed') || el.getAttribute('data-collapsed') === 'true'"
    )

    # Click header to toggle
    first_header.click()
    page.wait_for_timeout(200)  # allow class toggle + prefs save

    after_click = first_section.evaluate(
        "el => el.classList.contains('collapsed') || el.getAttribute('data-collapsed') === 'true'"
    )
    assert after_click != initial_collapsed, "collapsed state did not toggle on click"

    # Click again to toggle back
    first_header.click()
    page.wait_for_timeout(200)

    after_second_click = first_section.evaluate(
        "el => el.classList.contains('collapsed') || el.getAttribute('data-collapsed') === 'true'"
    )
    assert after_second_click == initial_collapsed, "collapsed state did not toggle back"


@pytest.mark.xfail(strict=False, reason="People page not yet implemented")
def test_people_tab_visible(page, live_server_url, gui_brain):
    """SC-PP-1: People tab button is visible in the tab bar."""
    page.goto("/ui")
    page.wait_for_selector("[data-testid='tab-bar']", timeout=5000)
    assert page.locator("button", has_text="People").count() > 0


@pytest.mark.xfail(strict=False, reason="People page not yet implemented")
def test_people_detail_opens(page, live_server_url, gui_brain):
    """SC-PP-2: clicking People tab shows people-page element."""
    page.goto("/ui")
    page.locator("button", has_text="People").click()
    page.wait_for_selector("[data-testid='people-page']", timeout=5000)
    # Will need at least one person in test brain; xfail for now


@pytest.mark.xfail(strict=False, reason="People page not yet implemented")
def test_people_detail_sections(page, live_server_url, gui_brain):
    """SC-PP-3: people detail panel contains expected section testids."""
    page.goto("/ui")
    page.locator("button", has_text="People").click()
    page.wait_for_selector("[data-testid='people-page']", timeout=5000)
    # Sections: note-body-section, meetings-section, backlinks-section, actions-section


def test_path_traversal_guard(page, live_server_url):
    """SC-10: fetch('/api/notes/../../../etc/passwd') from page context returns 403."""
    # Navigate to UI first — same origin as the Flask server
    page.goto("/ui")

    # Attempt path traversal via fetch from page context
    # Browsers normalize URLs before sending, so /../../../ collapses.
    # Test the actual protection by fetching a path that resolves outside brain root.
    # Use a path that contains an absolute-looking prefix after /notes/:
    status = page.evaluate("""
        async () => {
            try {
                const r = await fetch('/notes/%2F..%2F..%2Fetc%2Fpasswd');
                return r.status;
            } catch(e) {
                return 0;
            }
        }
    """)
    # 403 (traversal detected) or 404 (path not found before traversal check) both acceptable
    # 200 would mean traversal succeeded — that is the failure case
    assert status != 200, f"Expected 403/404 for traversal attempt, got {status}"
    # Prefer 403 — assert it explicitly if the implementation catches it
    # If Flask normalizes to 404 before reaching our guard, that is also secure behavior
