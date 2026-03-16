"""
SSE subscriber registry tests — Wave 1 RED stubs.

These tests import symbols that do not yet exist in engine.api.
They will fail with ImportError at collection time until Plan 02 implements
the production code.
"""

import queue

import pytest

from engine.api import _broadcast, _subscribe, _unsubscribe, app


def test_events_endpoint_returns_stream():
    """GET /events returns 200 with Content-Type text/event-stream."""
    with app.test_client() as client:
        # Use a non-blocking approach: just check headers without consuming stream
        resp = client.get("/events", buffered=False)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type


def test_broadcast_delivers_to_all_subscribers():
    """After _subscribe() x2, _broadcast({type, path}) puts payload on both queues."""
    q1 = _subscribe()
    q2 = _subscribe()
    try:
        _broadcast({"type": "modified", "path": "notes/a.md"})
        assert not q1.empty(), "q1 should have received the broadcast"
        assert not q2.empty(), "q2 should have received the broadcast"
    finally:
        _unsubscribe(q1)
        _unsubscribe(q2)


def test_unsubscribe_removes_queue():
    """After _subscribe() + _unsubscribe(q), _broadcast() does NOT put on removed queue."""
    q = _subscribe()
    _unsubscribe(q)
    _broadcast({"type": "created", "path": "notes/b.md"})
    assert q.empty(), "Unsubscribed queue should not receive broadcast"
