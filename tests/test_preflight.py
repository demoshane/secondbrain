"""Phase 27.7: Pre-flight smoke tests.

Validates all core API endpoints return 200 and the GUI renders before
the full Playwright suite runs. Alphabetical ordering ensures this file
runs before test_gui.py.

If any test here fails, it indicates a startup regression (e.g. /brain-health
returning 500 due to wrong kwarg) that will cause the full suite to fail noisily.

Run: uv run pytest tests/test_preflight.py -v
"""
import pytest
import requests


# ---------------------------------------------------------------------------
# API endpoint smoke tests
# ---------------------------------------------------------------------------

def test_preflight_health(live_server_url):
    """GET /health returns 200 — basic liveness check."""
    r = requests.get(f"{live_server_url}/health", timeout=5)
    assert r.status_code == 200, f"Pre-flight failed: /health returned {r.status_code}"


def test_preflight_brain_health(live_server_url):
    """GET /brain-health returns 200 — regression guard for startup 500 (wrong kwarg bug).

    Historical: compute_health_score() called with empty= instead of orphans=.
    This test catches that class of regression before the full suite runs.
    """
    r = requests.get(f"{live_server_url}/brain-health", timeout=5)
    assert r.status_code == 200, (
        f"Pre-flight failed: /brain-health returned {r.status_code} — "
        "check BRAIN_PATH env var and both engine.db.DB_PATH / engine.paths.DB_PATH"
    )


def test_preflight_notes_list(live_server_url):
    """GET /notes returns 200 — notes list endpoint is operational."""
    r = requests.get(f"{live_server_url}/notes", timeout=5)
    assert r.status_code == 200, f"Pre-flight failed: /notes returned {r.status_code}"


def test_preflight_people_list(live_server_url):
    """GET /people returns 200 — people list endpoint is operational."""
    r = requests.get(f"{live_server_url}/people", timeout=5)
    assert r.status_code == 200, f"Pre-flight failed: /people returned {r.status_code}"


def test_preflight_meetings_list(live_server_url):
    """GET /meetings returns 200 — meetings list endpoint is operational."""
    r = requests.get(f"{live_server_url}/meetings", timeout=5)
    assert r.status_code == 200, f"Pre-flight failed: /meetings returned {r.status_code}"


def test_preflight_projects_list(live_server_url):
    """GET /projects returns 200 — projects list endpoint is operational."""
    r = requests.get(f"{live_server_url}/projects", timeout=5)
    assert r.status_code == 200, f"Pre-flight failed: /projects returned {r.status_code}"


# ---------------------------------------------------------------------------
# GUI render smoke test
# ---------------------------------------------------------------------------

def test_preflight_ui_renders(page, live_server_url):
    """GET /ui renders the React GUI — tab bar is visible within 5 seconds.

    If this fails, the static bundle is broken or not being served correctly.
    """
    page.goto("/ui")
    page.locator('[data-testid="tab-bar"]').wait_for(state="visible", timeout=5000)
