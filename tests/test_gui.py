"""Phase 24: Playwright end-to-end GUI tests.

All tests are xfail stubs in Wave 1. Implemented in plans 02-04.
Run: uv run pytest tests/test_gui.py -v
"""
import pytest


def test_markdown_renders_as_html(page, live_server_url, gui_brain, seed_note_fn):
    """SC-2: note with headings/bold/lists renders as HTML — no raw # ** - in DOM."""
    seed_note_fn(gui_brain, "MD Note", "# My Heading\n\n**bold text**\n\n- list item")
    page.goto("/ui")
    page.wait_for_selector("#sidebar-loading", state="hidden", timeout=5000)
    page.locator("#note-list li[data-path]").first.click()
    page.locator("#viewer").wait_for(state="visible", timeout=5000)
    text = page.locator("#viewer").inner_text()
    assert "#" not in text
    assert "**" not in text
    assert page.locator("#viewer h1").count() > 0
    assert page.locator("#viewer strong").count() > 0
    assert page.locator("#viewer li").count() > 0


def test_viewer_scroll(page, live_server_url, gui_brain, seed_note_fn):
    """SC-3: viewer scrollTop changes when scripted (regression for scroll-lock bug)."""
    seed_note_fn(gui_brain, "Long Note", "\n".join(f"Line {i}: " + "x" * 80 for i in range(50)))
    page.goto("/ui")
    page.wait_for_selector("#sidebar-loading", state="hidden", timeout=5000)
    page.locator("#note-list li[data-path]", has_text="Long Note").first.click()
    page.locator("#viewer").wait_for(state="visible", timeout=5000)
    scroll_top = page.evaluate(
        "document.getElementById('viewer').scrollTop = 200; document.getElementById('viewer').scrollTop"
    )
    assert scroll_top > 0


def test_title_sync(page, live_server_url, gui_brain, seed_note_fn):
    """SC-4: editing note title via API + SSE refresh updates sidebar; reopen shows new h1."""
    import requests
    import urllib.parse

    note_path = seed_note_fn(gui_brain, "Original Title", "# Original Title\n\nbody content")

    page.goto("/ui")
    page.wait_for_selector("#sidebar-loading", state="hidden", timeout=5000)

    # Click the note to open it
    page.locator("#note-list li[data-path]", has_text="Original Title").first.click()
    page.locator("#viewer").wait_for(state="visible", timeout=5000)

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
    page.locator("#note-list li[data-path]", has_text="Updated Title").first.wait_for(
        state="visible", timeout=5000
    )

    # Click the updated note to load it in viewer — h1 should reflect new title
    page.locator("#note-list li[data-path]", has_text="Updated Title").first.click()
    page.locator("#viewer h1", has_text="Updated Title").wait_for(
        state="visible", timeout=5000
    )


@pytest.mark.xfail(reason="Wave 3: not yet implemented")
def test_sse_live_refresh(page, live_server_url, gui_brain, seed_note_fn):
    """SC-5: POST /notes broadcasts SSE; sidebar shows new note within 3s."""
    pytest.skip("Wave 3")


@pytest.mark.xfail(reason="Wave 3: not yet implemented")
def test_delete_flow(page, live_server_url, gui_brain, seed_note_fn):
    """SC-6: delete shows modal; confirm removes; cancel keeps."""
    pytest.skip("Wave 3")


@pytest.mark.xfail(reason="Wave 4: not yet implemented")
def test_tag_editing(page, live_server_url, gui_brain, seed_note_fn):
    """SC-7: double-click tag chip, type new tag, Enter saves to DOM + API."""
    pytest.skip("Wave 4")


@pytest.mark.xfail(reason="Wave 4: not yet implemented")
def test_tag_filtering(page, live_server_url, gui_brain, seed_note_fn):
    """SC-8: click tag chip filters sidebar; clear restores all notes."""
    pytest.skip("Wave 4")


@pytest.mark.xfail(reason="Wave 4: not yet implemented")
def test_collapsible_sections(page, live_server_url, gui_brain, seed_note_fn):
    """SC-9: clicking folder-header toggles .collapsed on .folder-section."""
    pytest.skip("Wave 4")


@pytest.mark.xfail(reason="Wave 4: not yet implemented")
def test_path_traversal_guard(page, live_server_url):
    """SC-10: fetch('/api/notes/../../../etc/passwd') from page context returns 403."""
    pytest.skip("Wave 4")
