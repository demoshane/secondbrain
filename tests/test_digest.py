"""Wave 0 RED stubs for Phase 16 digest generation (DIAG-01 through DIAG-04)."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from engine.digest import generate_digest


class TestDigestWrite:
    def test_digest_written_to_correct_path(self, tmp_path):
        """generate_digest writes a file to the correct weekly path — fails RED (NotImplementedError)."""
        # Will raise NotImplementedError until Plan 04 implements this
        result = generate_digest(None, tmp_path)  # raises — test fails
        assert (tmp_path / "digests").exists()


class TestDigestIdempotent:
    def test_second_run_skips(self, tmp_path):
        """generate_digest called twice in same week does not overwrite existing file — fails RED."""
        # Will raise NotImplementedError until Plan 04 implements this
        result1 = generate_digest(None, tmp_path)  # raises — test fails
        result2 = generate_digest(None, tmp_path)
        assert result1 == result2


class TestDigestSections:
    def test_all_four_sections_present(self, tmp_path):
        """generate_digest output contains Key Themes, Open Actions, Stale Notes, Captures This Week — fails RED."""
        # Will raise NotImplementedError until Plan 04 implements this
        digest_path = generate_digest(None, tmp_path)  # raises — test fails
        content = Path(digest_path).read_text()
        assert "Key Themes" in content
        assert "Open Actions" in content
        assert "Stale Notes" in content
        assert "Captures This Week" in content


class TestDigestPIIRouting:
    def test_pii_notes_use_ollama(self, tmp_path):
        """generate_digest routes PII notes through Ollama adapter — fails RED (NotImplementedError)."""
        from engine import digest as d
        mock_router = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "Digest summary."
        mock_router.get_adapter.return_value = mock_adapter
        # Will raise NotImplementedError until Plan 04 implements this
        result = generate_digest(None, tmp_path)  # raises — test fails
        calls = mock_router.get_adapter.call_args_list
        assert any(c[0][0] == "pii" for c in calls), "Expected Ollama adapter called with pii sensitivity"
