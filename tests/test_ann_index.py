"""Tests for engine/ann_index.py — ANN (hnswlib) index lifecycle.

TDD: written before implementation. Tests verify build, query, add, load, and
label_map round-trip behaviour.

Test isolation: patches _index_path() and _label_map_path() to point at
tmp_path so no files are written to the real brain .meta dir.
"""
import json
import sqlite3
import struct
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIM = 768  # nomic-embed-text dimension


def _make_blob(seed: int) -> bytes:
    """Deterministic 768-dim float32 BLOB."""
    rng = np.random.default_rng(seed)
    vec = rng.random(DIM).astype(np.float32)
    return vec.tobytes()


def _make_db(tmp_path: Path, n: int = 3) -> sqlite3.Connection:
    """In-memory SQLite DB with n fake note_embeddings rows."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE note_embeddings (
            note_path    TEXT PRIMARY KEY,
            embedding    BLOB,
            content_hash TEXT,
            stale        BOOL NOT NULL DEFAULT 0
        )"""
    )
    for i in range(n):
        conn.execute(
            "INSERT INTO note_embeddings (note_path, embedding, content_hash) VALUES (?, ?, ?)",
            (f"coding/note_{i:04d}.md", _make_blob(i), f"hash_{i}"),
        )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_index_paths(tmp_path, monkeypatch):
    """Redirect index + label_map file I/O to tmp_path for every test."""
    hnsw_path = tmp_path / "brain.hnsw"
    label_map_path = tmp_path / "label_map.json"
    monkeypatch.setattr("engine.ann_index._index_path", lambda: hnsw_path)
    monkeypatch.setattr("engine.ann_index._label_map_path", lambda: label_map_path)
    yield hnsw_path, label_map_path


@pytest.fixture(autouse=True)
def clear_singleton():
    """Ensure module-level cache is cleared before each test."""
    import engine.ann_index as m
    m._singleton = None
    yield
    m._singleton = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildHnswIndex:
    """build_hnsw_index / rebuild_index creates .hnsw file + label_map.json."""

    def test_rebuild_creates_hnsw_file(self, tmp_path, patch_index_paths):
        hnsw_path, _ = patch_index_paths
        from engine.ann_index import rebuild_index
        conn = _make_db(tmp_path)
        rebuild_index(conn)
        assert hnsw_path.exists(), "Expected .hnsw file to be created"

    def test_rebuild_creates_label_map(self, tmp_path, patch_index_paths):
        _, label_map_path = patch_index_paths
        from engine.ann_index import rebuild_index
        conn = _make_db(tmp_path)
        rebuild_index(conn)
        assert label_map_path.exists(), "Expected label_map.json to be created"
        data = json.loads(label_map_path.read_text())
        assert len(data) == 3, "label_map should have 3 entries"

    def test_rebuild_returns_index_and_map(self, tmp_path, patch_index_paths):
        from engine.ann_index import rebuild_index
        conn = _make_db(tmp_path)
        index, label_map = rebuild_index(conn)
        assert index is not None
        assert isinstance(label_map, dict)
        assert len(label_map) == 3


class TestKnnQuery:
    """knn_query returns closest match by cosine similarity."""

    def test_knn_returns_note_path(self, tmp_path, patch_index_paths):
        from engine.ann_index import rebuild_index, knn_query
        conn = _make_db(tmp_path)
        rebuild_index(conn)
        # Query with the same vector as note_0 — it should be the top result
        query_blob = _make_blob(0)
        results = knn_query(query_blob, k=3, conn=conn)
        assert len(results) > 0
        paths = [r[0] for r in results]
        assert "coding/note_0000.md" in paths

    def test_knn_returns_distances(self, tmp_path, patch_index_paths):
        from engine.ann_index import rebuild_index, knn_query
        conn = _make_db(tmp_path)
        rebuild_index(conn)
        query_blob = _make_blob(0)
        results = knn_query(query_blob, k=2, conn=conn)
        # Results should be (path, distance) tuples with non-negative distances
        for path, dist in results:
            assert isinstance(path, str)
            assert dist >= 0.0

    def test_knn_respects_k(self, tmp_path, patch_index_paths):
        from engine.ann_index import rebuild_index, knn_query
        conn = _make_db(tmp_path, n=3)
        rebuild_index(conn)
        query_blob = _make_blob(1)
        results = knn_query(query_blob, k=2, conn=conn)
        assert len(results) <= 2


class TestLoadOrBuildIndex:
    """load_or_build_index loads existing .hnsw without rebuild."""

    def test_load_existing_index(self, tmp_path, patch_index_paths):
        hnsw_path, _ = patch_index_paths
        from engine.ann_index import rebuild_index, load_or_build_index
        conn = _make_db(tmp_path)
        # Build first
        rebuild_index(conn)
        assert hnsw_path.exists()
        # Clear singleton so load_or_build_index must re-load from disk
        import engine.ann_index as m
        m._singleton = None
        # Load — should not call rebuild (file already exists)
        index, label_map = load_or_build_index(conn=None)
        assert index is not None
        assert isinstance(label_map, dict)
        assert len(label_map) == 3

    def test_missing_file_with_conn_triggers_build(self, tmp_path, patch_index_paths):
        hnsw_path, _ = patch_index_paths
        assert not hnsw_path.exists()
        from engine.ann_index import load_or_build_index
        conn = _make_db(tmp_path)
        index, label_map = load_or_build_index(conn=conn)
        # Should have built the index
        assert index is not None
        assert hnsw_path.exists()

    def test_missing_file_without_conn_returns_none(self, tmp_path, patch_index_paths):
        hnsw_path, _ = patch_index_paths
        assert not hnsw_path.exists()
        from engine.ann_index import load_or_build_index
        result = load_or_build_index(conn=None)
        assert result is None


class TestAddToIndex:
    """add_to_index adds a new embedding and persists (saved index has +1 element)."""

    def test_add_increases_element_count(self, tmp_path, patch_index_paths):
        hnsw_path, _ = patch_index_paths
        from engine.ann_index import rebuild_index, add_to_index, load_or_build_index
        conn = _make_db(tmp_path, n=3)
        index, label_map = rebuild_index(conn)
        initial_count = index.element_count

        # Add a 4th embedding (rowid 999 — not in DB, just testing the mechanic)
        new_blob = _make_blob(42)
        add_to_index(999, "ideas/new-note.md", new_blob)

        # Clear singleton and reload from disk
        import engine.ann_index as m
        m._singleton = None
        reloaded_index, reloaded_map = load_or_build_index(conn=None)
        assert reloaded_index.element_count == initial_count + 1
        assert "999" in reloaded_map or 999 in reloaded_map or "ideas/new-note.md" in reloaded_map.values()


class TestLabelMapRoundTrip:
    """label_map round-trip — save then load recovers {rowid: path} mapping."""

    def test_label_map_round_trip(self, tmp_path, patch_index_paths):
        _, label_map_path = patch_index_paths
        from engine.ann_index import rebuild_index, load_or_build_index
        conn = _make_db(tmp_path, n=3)
        _, original_map = rebuild_index(conn)

        # Clear singleton and reload
        import engine.ann_index as m
        m._singleton = None
        _, reloaded_map = load_or_build_index(conn=None)

        # Note paths should survive the round-trip
        original_paths = set(original_map.values())
        reloaded_paths = set(reloaded_map.values())
        assert original_paths == reloaded_paths
