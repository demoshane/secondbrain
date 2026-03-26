"""ANN (Approximate Nearest Neighbour) index module using hnswlib.

Provides a persistent hnswlib index over note embeddings for fast cosine-
similarity lookups at 100K-note scale, where sqlite-vec KNN becomes too slow.

Files written to BRAIN_ROOT/.meta/:
  brain.hnsw      — hnswlib index (binary)
  label_map.json  — JSON dict mapping str(rowid) -> note_path

Usage:
  from engine.ann_index import load_or_build_index, knn_query, add_to_index, rebuild_index
"""

import json
import logging
import struct
from pathlib import Path
from typing import Optional

import numpy as np

from engine.paths import BRAIN_ROOT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIM = 768                     # nomic-embed-text embedding dimension
HNSW_FILENAME = "brain.hnsw"
LABEL_MAP_FILENAME = "label_map.json"

# Module-level singleton cache: dict with keys "index" and "label_map", or None.
_singleton: Optional[dict] = None


# ---------------------------------------------------------------------------
# Path helpers (module-level functions so tests can patch them)
# ---------------------------------------------------------------------------

def _index_path() -> Path:
    """Absolute path to the hnswlib index file."""
    return BRAIN_ROOT / ".meta" / HNSW_FILENAME


def _label_map_path() -> Path:
    """Absolute path to the label_map JSON file."""
    return BRAIN_ROOT / ".meta" / LABEL_MAP_FILENAME


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rebuild_index(conn, max_elements: int = 200_000):
    """Build hnswlib index from all embeddings in note_embeddings table.

    Args:
        conn: Active sqlite3.Connection with note_embeddings table.
        max_elements: Maximum capacity of the index.

    Returns:
        Tuple (index, label_map) where:
          - index is a loaded hnswlib.Index
          - label_map is a dict mapping str(rowid) -> note_path
    """
    global _singleton

    import hnswlib

    rows = conn.execute(
        "SELECT rowid, note_path, embedding FROM note_embeddings WHERE embedding IS NOT NULL"
    ).fetchall()

    index = hnswlib.Index(space="cosine", dim=DIM)
    index.init_index(max_elements=max(max_elements, len(rows) + 1), ef_construction=200, M=16)
    index.set_ef(50)

    label_map: dict[str, str] = {}  # str(rowid) -> note_path

    if rows:
        vecs = []
        labels = []
        for rowid, note_path, blob in rows:
            vec = np.frombuffer(blob, dtype=np.float32)
            if len(vec) != DIM:
                logger.warning("Skipping %s: expected %d dims, got %d", note_path, DIM, len(vec))
                continue
            vecs.append(vec)
            labels.append(rowid)
            label_map[str(rowid)] = note_path

        if vecs:
            vecs_np = np.array(vecs, dtype=np.float32)
            labels_np = np.array(labels, dtype=np.uint64)
            index.add_items(vecs_np, labels_np)

    # Persist to disk
    idx_path = _index_path()
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    index.save_index(str(idx_path))

    lm_path = _label_map_path()
    lm_path.write_text(json.dumps(label_map, ensure_ascii=False), encoding="utf-8")

    _singleton = {"index": index, "label_map": label_map}
    return index, label_map


def load_or_build_index(conn=None, max_elements: int = 200_000):
    """Load existing hnswlib index from disk, or build it if missing.

    Args:
        conn: Optional sqlite3.Connection. Required if index file does not exist.
        max_elements: Passed to rebuild_index() if building from scratch.

    Returns:
        Tuple (index, label_map) on success.
        None if the index file does not exist and no conn was provided.
    """
    global _singleton

    # Return cached singleton if available
    if _singleton is not None:
        return _singleton["index"], _singleton["label_map"]

    idx_path = _index_path()
    lm_path = _label_map_path()

    if idx_path.exists() and lm_path.exists():
        # Load from disk
        import hnswlib
        index = hnswlib.Index(space="cosine", dim=DIM)
        index.load_index(str(idx_path), max_elements=max_elements)
        index.set_ef(50)
        label_map = json.loads(lm_path.read_text(encoding="utf-8"))
        _singleton = {"index": index, "label_map": label_map}
        return index, label_map

    if idx_path.exists() and not lm_path.exists():
        logger.warning("ANN index exists but label_map.json is missing — rebuilding from DB")
        if conn is not None:
            return rebuild_index(conn, max_elements)
        return None

    if conn is not None:
        # Build fresh from DB
        return rebuild_index(conn, max_elements)

    # No file and no conn — caller must handle fallback
    logger.warning("ANN index not found and no DB connection provided — fallback to sqlite-vec")
    return None


def add_to_index(rowid: int, note_path: str, embedding_blob: bytes) -> None:
    """Add or update a single embedding in the ANN index.

    Loads the singleton (or builds it if absent). Adds the vector, updates
    the label_map, and persists both to disk.

    Args:
        rowid: Integer rowid from note_embeddings table (used as hnswlib label).
        note_path: Path string for the note (stored in label_map).
        embedding_blob: Raw float32 bytes (len must equal DIM * 4).
    """
    global _singleton

    result = load_or_build_index(conn=None)
    if result is None:
        logger.warning("ANN add_to_index: no existing index and no conn — skipping")
        return

    index, label_map = result

    vec = np.frombuffer(embedding_blob, dtype=np.float32)
    if len(vec) != DIM:
        logger.warning("add_to_index: expected %d dims, got %d — skipping", DIM, len(vec))
        return

    index.add_items(
        np.array([vec], dtype=np.float32),
        np.array([rowid], dtype=np.uint64),
    )
    label_map[str(rowid)] = note_path

    # Persist
    idx_path = _index_path()
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    index.save_index(str(idx_path))

    lm_path = _label_map_path()
    lm_path.write_text(json.dumps(label_map, ensure_ascii=False), encoding="utf-8")

    _singleton = {"index": index, "label_map": label_map}


def knn_query(query_blob: bytes, k: int = 20, conn=None) -> list:
    """Query the ANN index for k nearest neighbours.

    Args:
        query_blob: Raw float32 bytes for the query vector.
        k: Number of results to return.
        conn: Optional sqlite3.Connection used to build the index if it doesn't exist.

    Returns:
        List of (note_path, distance) tuples sorted by ascending distance.
        Returns [] if index unavailable or query fails.
    """
    result = load_or_build_index(conn=conn)
    if result is None:
        logger.warning("knn_query: ANN index unavailable — returning empty results")
        return []

    index, label_map = result

    vec = np.frombuffer(query_blob, dtype=np.float32)
    if len(vec) != DIM:
        logger.warning("knn_query: expected %d dims, got %d", DIM, len(vec))
        return []

    actual_k = min(k, index.element_count)
    if actual_k == 0:
        return []

    labels, distances = index.knn_query(vec.reshape(1, -1), k=actual_k)

    results = []
    for label, dist in zip(labels[0], distances[0]):
        path = label_map.get(str(label)) or label_map.get(label)
        if path is None:
            logger.debug("knn_query: stale label %d not in label_map — skipping", label)
            continue
        results.append((path, float(dist)))

    results.sort(key=lambda x: x[1])
    return results


def invalidate_cache() -> None:
    """Clear the module-level singleton cache. Useful in tests."""
    global _singleton
    _singleton = None
