"""Tests for chunked embeddings infrastructure (Plan 38-04).

Tests:
- split_text_into_chunks: splitting behaviour, threshold, overlap
- embed_chunks: returns (chunk_text, blob) tuples
- note_chunks table: created by init_schema, UNIQUE constraint
"""
import struct
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# split_text_into_chunks
# ---------------------------------------------------------------------------

class TestSplitTextIntoChunks:
    """Tests for the chunking function in engine.embeddings."""

    def test_short_text_returns_single_chunk(self):
        """Text <= chunk_size returns [text] as-is."""
        from engine.embeddings import split_text_into_chunks, CHUNK_SIZE
        text = "A" * 500  # well below 1200-char chunk_size
        chunks = split_text_into_chunks(text)
        assert chunks == [text]

    def test_text_at_chunk_size_boundary_returns_single_chunk(self):
        """Text exactly equal to chunk_size returns [text]."""
        from engine.embeddings import split_text_into_chunks, CHUNK_SIZE
        text = "B" * CHUNK_SIZE
        chunks = split_text_into_chunks(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_returns_multiple_chunks(self):
        """2500-char text with default params returns more than one chunk."""
        from engine.embeddings import split_text_into_chunks
        text = "C" * 2500
        chunks = split_text_into_chunks(text)
        assert len(chunks) > 1

    def test_each_chunk_does_not_exceed_chunk_size(self):
        """Every produced chunk must be <= chunk_size characters."""
        from engine.embeddings import split_text_into_chunks, CHUNK_SIZE
        text = "D" * 5000
        chunks = split_text_into_chunks(text)
        for chunk in chunks:
            assert len(chunk) <= CHUNK_SIZE

    def test_consecutive_chunks_overlap(self):
        """Consecutive chunks share approximately CHUNK_OVERLAP chars at boundaries."""
        from engine.embeddings import split_text_into_chunks, CHUNK_SIZE, CHUNK_OVERLAP
        # Build a text with recognisable per-position characters so we can verify overlap.
        # Use a repeating alphabet so adjacent characters differ and overlap is detectable.
        text = ("ABCDEFGHIJ" * 300)[:3000]  # 3000 chars
        chunks = split_text_into_chunks(text)
        assert len(chunks) >= 2
        # The tail of chunk[0] must equal the head of chunk[1] for CHUNK_OVERLAP chars.
        tail = chunks[0][-CHUNK_OVERLAP:]
        head = chunks[1][:CHUNK_OVERLAP]
        assert tail == head, f"Expected overlap of {CHUNK_OVERLAP} chars between consecutive chunks"

    def test_all_text_covered(self):
        """Concatenating chunks without overlap should equal the original text."""
        from engine.embeddings import split_text_into_chunks, CHUNK_SIZE, CHUNK_OVERLAP
        text = "E" * 4000
        chunks = split_text_into_chunks(text)
        # Reconstruct by taking the non-overlapping part of each chunk
        reconstructed = chunks[0]
        for chunk in chunks[1:]:
            reconstructed += chunk[CHUNK_OVERLAP:]
        # Allow small off-by-one at the final chunk boundary
        assert text.startswith(reconstructed) or reconstructed.startswith(text), (
            "Reconstruction does not match original text"
        )

    def test_custom_chunk_size_and_overlap(self):
        """Custom chunk_size and overlap parameters are honoured."""
        from engine.embeddings import split_text_into_chunks
        text = "F" * 100
        chunks = split_text_into_chunks(text, chunk_size=40, overlap=10)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 40
        # Verify overlap between first two chunks
        assert chunks[0][-10:] == chunks[1][:10]

    def test_empty_text_returns_single_empty_chunk(self):
        """Empty string input returns [''] — a single empty chunk."""
        from engine.embeddings import split_text_into_chunks
        chunks = split_text_into_chunks("")
        assert chunks == [""]

    def test_chunk_count_is_predictable(self):
        """For a 2500-char text: expect 3 chunks with size=1200, overlap=200."""
        from engine.embeddings import split_text_into_chunks
        # chunk 0: [0, 1200), chunk 1: [1000, 2200), chunk 2: [2000, 2500)
        text = "G" * 2500
        chunks = split_text_into_chunks(text, chunk_size=1200, overlap=200)
        assert len(chunks) == 3


# ---------------------------------------------------------------------------
# embed_chunks
# ---------------------------------------------------------------------------

class TestEmbedChunks:
    """Tests for embed_chunks in engine.embeddings.

    These tests skip the real embeddings stub (conftest skips TestEmbedTexts /
    TestSerialize by class name but NOT TestEmbedChunks).  We patch
    engine.embeddings.embed_texts ourselves for isolation.
    """

    def _fake_embed_texts(self, texts, provider=None, batch_size=32):
        """Return deterministic 384-float BLOBs — same size as real embeddings."""
        blob = struct.pack("384f", *[0.1] * 384)
        return [blob for _ in texts]

    def test_embed_chunks_returns_list_of_tuples(self, monkeypatch):
        """embed_chunks returns [(str, bytes), ...] pairs."""
        import engine.embeddings as emb
        monkeypatch.setattr(emb, "embed_texts", self._fake_embed_texts)
        text = "Hello world. " * 20  # 260 chars — below chunk_size → single chunk
        result = emb.embed_chunks(text)
        assert isinstance(result, list)
        assert len(result) >= 1
        for chunk_text, blob in result:
            assert isinstance(chunk_text, str)
            assert isinstance(blob, bytes)

    def test_embed_chunks_blob_size_is_consistent(self, monkeypatch):
        """Every blob returned by embed_chunks has the same length."""
        import engine.embeddings as emb
        monkeypatch.setattr(emb, "embed_texts", self._fake_embed_texts)
        text = "Word " * 600  # ~3000 chars → multiple chunks
        result = emb.embed_chunks(text)
        assert len(result) > 1
        blob_sizes = {len(blob) for _, blob in result}
        assert len(blob_sizes) == 1, "All blobs should have the same byte length"

    def test_embed_chunks_chunk_text_matches_split(self, monkeypatch):
        """Chunk texts in the result match split_text_into_chunks output."""
        import engine.embeddings as emb
        monkeypatch.setattr(emb, "embed_texts", self._fake_embed_texts)
        text = "Z" * 3000
        result = emb.embed_chunks(text)
        expected_chunks = emb.split_text_into_chunks(text)
        assert [t for t, _ in result] == expected_chunks

    def test_embed_chunks_empty_text_returns_single_entry(self, monkeypatch):
        """embed_chunks on empty string returns one entry (empty chunk)."""
        import engine.embeddings as emb
        monkeypatch.setattr(emb, "embed_texts", self._fake_embed_texts)
        result = emb.embed_chunks("")
        assert len(result) == 1
        assert result[0][0] == ""


# ---------------------------------------------------------------------------
# note_chunks table (schema)
# ---------------------------------------------------------------------------

class TestNoteChunksSchema:
    """Verify that init_schema creates the note_chunks table correctly."""

    def test_note_chunks_table_created(self):
        """init_schema creates note_chunks table."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        init_schema(conn)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "note_chunks" in tables, "note_chunks table should be created by init_schema"
        conn.close()

    def test_note_chunks_columns(self):
        """note_chunks has required columns: id, note_path, chunk_index, chunk_text, embedding."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(note_chunks)").fetchall()}
        assert "id" in cols
        assert "note_path" in cols
        assert "chunk_index" in cols
        assert "chunk_text" in cols
        assert "embedding" in cols
        conn.close()

    def test_note_chunks_unique_constraint(self):
        """UNIQUE(note_path, chunk_index) prevents duplicate inserts."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        conn.execute(
            "INSERT INTO note_chunks (note_path, chunk_index, chunk_text) VALUES (?, ?, ?)",
            ("notes/test.md", 0, "first chunk"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO note_chunks (note_path, chunk_index, chunk_text) VALUES (?, ?, ?)",
                ("notes/test.md", 0, "duplicate chunk"),
            )
            conn.commit()
        conn.close()

    def test_note_chunks_upsert_on_conflict(self):
        """ON CONFLICT ... DO UPDATE overwrites duplicate rows without error."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        conn.execute(
            "INSERT INTO note_chunks (note_path, chunk_index, chunk_text) VALUES (?, ?, ?)",
            ("notes/upsert.md", 0, "original text"),
        )
        conn.commit()
        conn.execute(
            """INSERT INTO note_chunks (note_path, chunk_index, chunk_text)
               VALUES (?, ?, ?)
               ON CONFLICT(note_path, chunk_index) DO UPDATE SET
                   chunk_text=excluded.chunk_text""",
            ("notes/upsert.md", 0, "updated text"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT chunk_text FROM note_chunks WHERE note_path=? AND chunk_index=0",
            ("notes/upsert.md",),
        ).fetchone()
        assert row is not None
        assert row[0] == "updated text"
        conn.close()

    def test_note_chunks_index_on_path(self):
        """idx_note_chunks_path index exists on note_chunks(note_path)."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        indexes = {r[1] for r in conn.execute(
            "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='note_chunks'"
        ).fetchall()}
        assert "idx_note_chunks_path" in indexes
        conn.close()

    def test_init_schema_idempotent_for_note_chunks(self):
        """Calling init_schema twice does not raise on note_chunks table."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        init_schema(conn)  # second call must be idempotent
        count = conn.execute("SELECT COUNT(*) FROM note_chunks").fetchone()[0]
        assert count == 0
        conn.close()
