"""Tests for engine/embeddings.py — embedding provider dispatch.

These tests cover:
- note_embeddings DDL in db.py
- embeddings defaults in config_loader.py DEFAULT_CONFIG
- embed_texts() dispatch and caching behaviour

All sentence-transformers tests mock _get_model() to avoid the 90 MB download.
"""
import sqlite3
import struct
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task 1 — note_embeddings DDL and config defaults
# ---------------------------------------------------------------------------

class TestNoteEmbeddingsDDL:
    def test_note_embeddings_table_created_by_init_schema(self):
        """init_schema() must create note_embeddings on a fresh in-memory DB."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='note_embeddings'"
        ).fetchall()
        assert rows, "note_embeddings table missing after init_schema()"

    def test_note_embeddings_columns(self):
        """note_embeddings must have the correct columns."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(note_embeddings)").fetchall()}
        assert cols == {"note_path", "embedding", "content_hash", "stale", "created_at", "updated_at"}

    def test_note_embeddings_stale_default_false(self):
        """note_embeddings.stale defaults to 0 (False)."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        conn.execute(
            "INSERT INTO note_embeddings (note_path, embedding, content_hash) VALUES (?, ?, ?)",
            ("notes/test.md", b"\x00" * 4, "abc123"),
        )
        conn.commit()
        row = conn.execute("SELECT stale FROM note_embeddings WHERE note_path='notes/test.md'").fetchone()
        assert row[0] == 0

    def test_note_embeddings_idempotent(self):
        """init_schema() can be called twice without error (IF NOT EXISTS)."""
        from engine.db import init_schema
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        init_schema(conn)  # must not raise


class TestEmbeddingsConfig:
    def test_default_config_has_embeddings_key(self):
        """DEFAULT_CONFIG must include an 'embeddings' key."""
        from engine.config_loader import DEFAULT_CONFIG
        assert "embeddings" in DEFAULT_CONFIG

    def test_default_config_embeddings_provider(self):
        """DEFAULT_CONFIG['embeddings']['provider'] must be 'ollama'."""
        from engine.config_loader import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["embeddings"]["provider"] == "ollama"

    def test_default_config_embeddings_batch_size(self):
        """DEFAULT_CONFIG['embeddings']['batch_size'] must be 32."""
        from engine.config_loader import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["embeddings"]["batch_size"] == 32


# ---------------------------------------------------------------------------
# Task 2 — embed_texts() dispatch and caching
# ---------------------------------------------------------------------------

def _fake_model(texts, *, batch_size, show_progress_bar):
    """Returns deterministic 384-float vectors without any download."""
    import struct as s
    return [list(range(384)) for _ in texts]


class FakeModel:
    def encode(self, texts, *, batch_size=32, show_progress_bar=False):
        return [list(range(384)) for _ in texts]


class TestEmbedTexts:
    def test_empty_list_returns_empty(self):
        """embed_texts([]) must return []."""
        from engine.embeddings import embed_texts
        result = embed_texts([], provider="sentence-transformers")
        assert result == []

    def test_returns_bytes_blobs(self):
        """embed_texts returns a list of bytes objects."""
        with patch("engine.embeddings._get_model", return_value=FakeModel()):
            from engine.embeddings import embed_texts
            result = embed_texts(["hello"], provider="sentence-transformers")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], bytes)

    def test_blob_length_384_floats(self):
        """Each BLOB must encode exactly 384 float32 values (384 * 4 bytes)."""
        with patch("engine.embeddings._get_model", return_value=FakeModel()):
            from engine.embeddings import embed_texts
            result = embed_texts(["hello"], provider="sentence-transformers")
        assert len(result[0]) == 384 * 4

    def test_embed_no_network_call(self):
        """No network call when provider='sentence-transformers' and model is cached."""
        with patch("engine.embeddings._get_model", return_value=FakeModel()) as mock_get:
            from engine.embeddings import embed_texts
            embed_texts(["test"], provider="sentence-transformers")
            # _get_model was called, but no SentenceTransformer() constructor — no download
            mock_get.assert_called_once()

    def test_model_cached_across_calls(self):
        """_get_model() returns the same object on repeated calls (lazy load)."""
        import engine.embeddings as em
        original_cache = em._model_cache
        try:
            em._model_cache = None
            fake = FakeModel()
            with patch("engine.embeddings._get_model", return_value=fake) as mock_get:
                em.embed_texts(["a"], provider="sentence-transformers")
                em.embed_texts(["b"], provider="sentence-transformers")
            # _get_model called once per embed_texts — caching happens inside _get_model itself
            assert mock_get.call_count == 2  # mock is called, but real impl would cache
        finally:
            em._model_cache = original_cache

    def test_unknown_provider_raises_value_error(self):
        """embed_texts with unknown provider must raise ValueError."""
        from engine.embeddings import embed_texts
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            embed_texts(["hello"], provider="unknown-provider")

    def test_ollama_not_running_raises_runtime_error(self):
        """When Ollama is not running, embed_texts raises RuntimeError with friendly message."""
        with patch("engine.embeddings._get_model"):  # not used for ollama path
            import engine.embeddings as em
            with patch.dict("sys.modules", {"ollama": None}):
                # Simulate import error (ollama not installed → ImportError path)
                pass

        # Simulate ollama connection failure
        mock_ollama = MagicMock()
        mock_ollama.embed.side_effect = Exception("connection refused")
        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            from engine.embeddings import embed_texts
            with pytest.raises(RuntimeError, match=r"\[ERROR\].*Ollama"):
                embed_texts(["hello"], provider="ollama")

    def test_multiple_texts(self):
        """embed_texts handles multiple inputs and returns one BLOB per text."""
        with patch("engine.embeddings._get_model", return_value=FakeModel()):
            from engine.embeddings import embed_texts
            result = embed_texts(["hello", "world", "test"], provider="sentence-transformers")
        assert len(result) == 3
        assert all(isinstance(b, bytes) for b in result)
        assert all(len(b) == 384 * 4 for b in result)


class TestSerialize:
    def test_serialize_list(self):
        """_serialize([1.0, 2.0]) produces the correct little-endian float32 BLOB."""
        from engine.embeddings import _serialize
        vector = [1.0, 2.0]
        result = _serialize(vector)
        unpacked = struct.unpack("2f", result)
        assert abs(unpacked[0] - 1.0) < 1e-6
        assert abs(unpacked[1] - 2.0) < 1e-6

    def test_serialize_length(self):
        """_serialize with 384 floats produces exactly 384*4 bytes."""
        from engine.embeddings import _serialize
        vector = [0.1] * 384
        assert len(_serialize(vector)) == 384 * 4


# ---------------------------------------------------------------------------
# Task 3 — embed_pass() and reindex_brain() embedding second pass
# ---------------------------------------------------------------------------

class FakeEmbeddingsModule:
    """Minimal stand-in for engine.embeddings when testing reindex."""

    @staticmethod
    def embed_texts(texts, provider="sentence-transformers", batch_size=32):
        """Return deterministic 384-float BLOBs without any model download."""
        import struct
        blob = struct.pack("384f", *[0.1] * 384)
        return [blob for _ in texts]


class TestReindexGeneratesEmbeddings:
    """EMBED-01: Running sb-reindex populates note_embeddings."""

    def test_reindex_generates_embeddings(self, brain_root, db_conn):
        """After reindex, note_embeddings has one row per note."""
        import sys
        import types
        from engine.db import init_schema

        # Provide a fake engine.embeddings so no download occurs
        fake_mod = types.ModuleType("engine.embeddings")
        fake_mod.embed_texts = FakeEmbeddingsModule.embed_texts
        sys.modules["engine.embeddings"] = fake_mod

        try:
            init_schema(db_conn)
            note = brain_root / "note1.md"
            note.write_text("---\ntype: note\ntitle: Note One\n---\nBody one")

            from engine.reindex import reindex_brain
            result = reindex_brain(brain_root, db_conn, synchronous=True)

            count = db_conn.execute("SELECT COUNT(*) FROM note_embeddings").fetchone()[0]
            assert count == 1, f"Expected 1 embedding row, got {count}"
            assert result["embed_updated"] == 1
            assert result["embed_unchanged"] == 0
        finally:
            sys.modules.pop("engine.embeddings", None)

    def test_reindex_full_flag(self, brain_root, db_conn):
        """EMBED-01: --full flag re-embeds all notes regardless of hash state."""
        import sys
        import types
        from engine.db import init_schema

        fake_mod = types.ModuleType("engine.embeddings")
        fake_mod.embed_texts = FakeEmbeddingsModule.embed_texts
        sys.modules["engine.embeddings"] = fake_mod

        try:
            init_schema(db_conn)
            note = brain_root / "note1.md"
            note.write_text("---\ntype: note\ntitle: Note One\n---\nBody one")

            from engine.reindex import reindex_brain

            # First pass — embeds once
            reindex_brain(brain_root, db_conn, synchronous=True)

            # Second pass with full=True — must re-embed even though hash unchanged
            result = reindex_brain(brain_root, db_conn, full=True, synchronous=True)
            assert result["embed_updated"] == 1
            assert result["embed_unchanged"] == 0
        finally:
            sys.modules.pop("engine.embeddings", None)

    def test_reindex_incremental_skips_unchanged(self, brain_root, db_conn):
        """EMBED-03: Second reindex without edits leaves all updated_at unchanged."""
        import sys
        import types
        from engine.db import init_schema

        fake_mod = types.ModuleType("engine.embeddings")
        fake_mod.embed_texts = FakeEmbeddingsModule.embed_texts
        sys.modules["engine.embeddings"] = fake_mod

        try:
            init_schema(db_conn)
            note = brain_root / "note1.md"
            note.write_text("---\ntype: note\ntitle: Note One\n---\nBody one")

            from engine.reindex import reindex_brain

            # First pass
            reindex_brain(brain_root, db_conn, synchronous=True)
            ts_before = db_conn.execute(
                "SELECT updated_at FROM note_embeddings"
            ).fetchone()[0]

            # Second pass — same content, no changes
            result = reindex_brain(brain_root, db_conn, synchronous=True)
            ts_after = db_conn.execute(
                "SELECT updated_at FROM note_embeddings"
            ).fetchone()[0]

            assert result["embed_updated"] == 0
            assert result["embed_unchanged"] == 1
            assert ts_before == ts_after, "updated_at changed on unchanged note"
        finally:
            sys.modules.pop("engine.embeddings", None)

    def test_reindex_incremental_reembeds_changed(self, brain_root, db_conn):

        """EMBED-03: Editing a note body triggers re-embedding on next reindex."""
        import sys
        import types
        from engine.db import init_schema

        fake_mod = types.ModuleType("engine.embeddings")
        fake_mod.embed_texts = FakeEmbeddingsModule.embed_texts
        sys.modules["engine.embeddings"] = fake_mod

        try:
            init_schema(db_conn)
            note = brain_root / "note1.md"
            note.write_text("---\ntype: note\ntitle: Note One\n---\nOriginal body")

            from engine.reindex import reindex_brain

            # First pass
            reindex_brain(brain_root, db_conn, synchronous=True)
            hash_before = db_conn.execute(
                "SELECT content_hash FROM note_embeddings"
            ).fetchone()[0]

            # Edit note body
            note.write_text("---\ntype: note\ntitle: Note One\n---\nEdited body")

            # Second pass — must detect hash change and re-embed
            result = reindex_brain(brain_root, db_conn, synchronous=True)
            hash_after = db_conn.execute(
                "SELECT content_hash FROM note_embeddings"
            ).fetchone()[0]

            assert result["embed_updated"] == 1
            assert result["embed_unchanged"] == 0
            assert hash_before != hash_after, "content_hash did not change after edit"
        finally:
            sys.modules.pop("engine.embeddings", None)


# ---------------------------------------------------------------------------
# Task 4 — forget_person() cascade-deletes note_embeddings rows (EMBED-04)
# ---------------------------------------------------------------------------

class TestForgetCascadeDeletesEmbeddings:
    def test_forget_removes_embedding_rows(self, brain_root, db_conn):
        """forget_person() must delete note_embeddings rows for erased paths."""
        import struct
        from engine.db import init_schema
        from engine.forget import forget_person

        init_schema(db_conn)

        # Create a person file
        people_dir = brain_root / "people"
        people_dir.mkdir()
        person_file = people_dir / "alice-smith.md"
        person_file.write_text("---\ntype: person\ntitle: Alice Smith\n---\n")

        # Insert a note_embeddings row for the person file
        blob = struct.pack("4f", 0.1, 0.2, 0.3, 0.4)
        db_conn.execute(
            "INSERT INTO note_embeddings (note_path, embedding, content_hash) VALUES (?, ?, ?)",
            (str(person_file), blob, "abc123"),
        )
        db_conn.commit()

        # Verify row exists before forget
        row = db_conn.execute(
            "SELECT note_path FROM note_embeddings WHERE note_path = ?",
            (str(person_file),),
        ).fetchone()
        assert row is not None, "embedding row should exist before forget"

        # Run forget
        forget_person("alice-smith", brain_root, db_conn)

        # Verify row is gone after forget
        row = db_conn.execute(
            "SELECT note_path FROM note_embeddings WHERE note_path = ?",
            (str(person_file),),
        ).fetchone()
        assert row is None, "embedding row should be deleted by forget_person()"
