"""Phase 24: Playwright end-to-end GUI tests.

All tests are xfail stubs in Wave 1. Implemented in plans 02-04.
Run: uv run pytest tests/test_gui.py -v
"""
import pytest


@pytest.mark.xfail(reason="Wave 2: not yet implemented")
def test_markdown_renders_as_html(page, live_server_url, gui_brain, seed_note_fn):
    """SC-2: note with headings/bold/lists renders as HTML — no raw # ** - in DOM."""
    pytest.skip("Wave 2")


@pytest.mark.xfail(reason="Wave 2: not yet implemented")
def test_viewer_scroll(page, live_server_url, gui_brain, seed_note_fn):
    """SC-3: viewer scrollTop changes when scripted (regression for scroll-lock bug)."""
    pytest.skip("Wave 2")


@pytest.mark.xfail(reason="Wave 2: not yet implemented")
def test_title_sync(page, live_server_url, gui_brain, seed_note_fn):
    """SC-4: editing note title via API updates sidebar + viewer heading."""
    pytest.skip("Wave 2")


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
