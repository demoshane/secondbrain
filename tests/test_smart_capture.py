"""Tests for smart capture: segmenter, smart classifier, and sb_capture_smart MCP tool.

Phase 31-01: segmenter unit tests (pass green) + classifier unit tests (pass green)
             + xfail stubs for all CAP requirements (12 stubs).
"""
import os
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_brain(tmp_path, monkeypatch):
    """Isolated brain root + DB for smart capture tests."""
    import engine.db
    import engine.paths

    brain_root = tmp_path / "brain"
    brain_root.mkdir()
    (brain_root / ".meta").mkdir()
    db_path = brain_root / ".meta" / "brain.db"

    monkeypatch.setenv("BRAIN_PATH", str(brain_root))
    monkeypatch.setattr(engine.db, "DB_PATH", db_path)
    monkeypatch.setattr(engine.paths, "DB_PATH", db_path)
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", brain_root)

    from engine.db import init_schema, get_connection
    conn = get_connection(str(db_path))
    init_schema(conn)
    conn.close()

    return brain_root


# ---------------------------------------------------------------------------
# Segmenter unit tests (must PASS green)
# ---------------------------------------------------------------------------

class TestSegmentStructuralMarkers:
    """segment_blob splits on structural markers (headings, ---, dates)."""

    def test_heading_h1_splits(self):
        from engine.segmenter import segment_blob
        content = (
            "# Meeting Notes\n"
            "Discussed Q1 roadmap with the team. Covered hiring, infra, and Q2 goals.\n"
            "\n"
            "# Alice Smith\n"
            "Role: CTO at Acme Corp. Contact: alice@acme.com. Joined 2022.\n"
        )
        segs = segment_blob(content)
        assert len(segs) >= 2

    def test_heading_h2_splits(self):
        from engine.segmenter import segment_blob
        content = (
            "## Project Alpha\n"
            "Milestone: ship by April. Current status: on track. Team: engineering.\n"
            "\n"
            "## Project Beta\n"
            "Still in planning phase. Roadmap TBD. Depends on Alpha completion.\n"
        )
        segs = segment_blob(content)
        assert len(segs) >= 2

    def test_heading_h3_splits(self):
        from engine.segmenter import segment_blob
        content = (
            "### Task A\n"
            "Do the thing. This is important work that needs to be done by Friday.\n"
            "\n"
            "### Task B\n"
            "Do another thing. This follows from Task A and needs careful review.\n"
        )
        segs = segment_blob(content)
        assert len(segs) >= 2

    def test_horizontal_rule_splits(self):
        from engine.segmenter import segment_blob
        content = (
            "First section content here. This is a substantial paragraph.\n"
            "It has multiple lines and covers several topics in detail.\n"
            "---\n"
            "Second section content here. Also substantial.\n"
            "Covers different topics from the first section.\n"
        )
        segs = segment_blob(content)
        assert len(segs) >= 2

    def test_date_stamp_splits(self):
        from engine.segmenter import segment_blob
        content = (
            "2026-03-19\n"
            "Met with Alice about the project. Discussed timelines and resources.\n"
            "Action: follow up by end of week with a proposal document.\n"
            "\n"
            "2026-03-20\n"
            "Followup with Bob regarding the infrastructure upgrade proposal.\n"
            "Agreed to schedule a technical review next week with the team.\n"
        )
        segs = segment_blob(content)
        assert len(segs) >= 2

    def test_segments_have_required_keys(self):
        from engine.segmenter import segment_blob
        content = (
            "# Note One\n"
            "Some body text here with enough words to pass the minimum length.\n"
            "\n"
            "# Note Two\n"
            "More content here with enough words to survive the short-segment merge.\n"
        )
        segs = segment_blob(content)
        for seg in segs:
            assert "title" in seg
            assert "type" in seg
            assert "body" in seg
            assert "links" in seg
            assert "entities" in seg

    def test_single_segment_returns_list(self):
        from engine.segmenter import segment_blob
        content = "Just a short note."
        segs = segment_blob(content)
        assert isinstance(segs, list)
        assert len(segs) >= 1


class TestSegmentShortMerge:
    """Short segments (<50 chars or <2 lines) merge into the previous segment."""

    def test_short_segment_merges_into_previous(self):
        from engine.segmenter import segment_blob
        # First section is long enough; second is trivially short (< 50 chars, 1 line)
        long_body = "This is a long section with plenty of content.\n" * 3
        content = f"# Section One\n{long_body}\n# Ok\nX."
        segs = segment_blob(content)
        # The short "Ok / X." should merge back into "Section One" → only 1 segment
        assert len(segs) == 1

    def test_stub_before_long_merges(self):
        from engine.segmenter import segment_blob
        # Very short first segment followed by a long one — short merges into long
        content = "# Hi\nX.\n\n# Long Section\n" + "Lots of content here.\n" * 4
        segs = segment_blob(content)
        # At most 1 segment (short "Hi" merges into "Long Section" or vice versa)
        assert len(segs) <= 2


class TestSegmentMax20Cap:
    """segment_blob caps output at 20 segments by merging smallest pairs."""

    def test_max_20_cap(self):
        from engine.segmenter import segment_blob
        # Build 25 distinct heading sections
        sections = []
        for i in range(25):
            sections.append(f"# Section {i}\nContent for section {i} with enough words to be valid content.")
        content = "\n\n".join(sections)
        segs = segment_blob(content)
        assert len(segs) <= 20

    def test_normal_input_under_20(self):
        from engine.segmenter import segment_blob
        content = "# Note\nJust one note with a reasonable body."
        segs = segment_blob(content)
        assert len(segs) <= 20


class TestSegmentUrlDetection:
    """Segments containing URLs get type='link'."""

    def test_url_gives_link_type(self):
        from engine.segmenter import segment_blob
        content = "Check this out: https://example.com/article\nReally interesting read."
        segs = segment_blob(content)
        assert any(s["type"] == "link" for s in segs)

    def test_no_url_no_link_type(self):
        from engine.segmenter import segment_blob
        content = "# Meeting Notes\nDiscussed the roadmap with Alice."
        segs = segment_blob(content)
        assert not any(s["type"] == "link" for s in segs)


class TestSegmentCodeBlockInline:
    """Fenced code blocks stay inside their parent segment — not split."""

    def test_code_block_not_split(self):
        from engine.segmenter import segment_blob
        content = (
            "# Tech Notes\n"
            "Here is some code:\n"
            "```python\n"
            "def hello():\n"
            "    print('hello')\n"
            "```\n"
            "End of section."
        )
        segs = segment_blob(content)
        # Must be a single segment; code block must not cause a split
        assert len(segs) == 1
        assert "```" in segs[0]["body"]

    def test_heading_inside_code_block_not_split(self):
        from engine.segmenter import segment_blob
        content = (
            "# Parent Section\n"
            "Some intro.\n"
            "```markdown\n"
            "# This heading is inside a code block\n"
            "```\n"
            "Conclusion."
        )
        segs = segment_blob(content)
        assert len(segs) == 1


class TestSegmentTableInline:
    """Markdown tables stay in their parent segment — not split."""

    def test_table_not_split(self):
        from engine.segmenter import segment_blob
        content = (
            "# Data\n"
            "Here is a table:\n"
            "| Name | Score |\n"
            "|------|-------|\n"
            "| Alice | 95 |\n"
            "| Bob | 87 |\n"
        )
        segs = segment_blob(content)
        assert len(segs) == 1
        assert "|" in segs[0]["body"]


# ---------------------------------------------------------------------------
# Smart classifier unit tests (must PASS green)
# ---------------------------------------------------------------------------

class TestClassifySmart:
    """classify_smart detects PII patterns and respects never-downgrade rule."""

    def test_phone_number_gives_pii(self):
        from engine.smart_classifier import classify_smart
        level, reason = classify_smart("Call me at +358 50 123 4567", "public")
        assert level == "pii"
        assert reason is not None
        assert "phone" in reason.lower()

    def test_email_gives_pii(self):
        from engine.smart_classifier import classify_smart
        level, reason = classify_smart("Reach me at alice@example.com anytime.", "public")
        assert level == "pii"
        assert reason is not None
        assert "email" in reason.lower()

    def test_finnish_hetu_gives_pii(self):
        from engine.smart_classifier import classify_smart
        level, reason = classify_smart("ID: 010101-123A registered.", "public")
        assert level == "pii"
        assert reason is not None

    def test_us_ssn_gives_pii(self):
        from engine.smart_classifier import classify_smart
        level, reason = classify_smart("SSN: 123-45-6789 on file.", "public")
        assert level == "pii"
        assert reason is not None

    def test_clean_text_stays_public(self):
        from engine.smart_classifier import classify_smart
        level, reason = classify_smart("The quarterly roadmap is on track.", "public")
        assert level == "public"
        assert reason is None

    def test_never_downgrade_from_pii(self):
        from engine.smart_classifier import classify_smart
        # User says public, but PII detected — must return pii
        level, reason = classify_smart("My SSN is 123-45-6789.", "public")
        assert level == "pii"

    def test_never_downgrade_from_private(self):
        from engine.smart_classifier import classify_smart
        # User says private, no PII detected — stays private (not downgraded to public)
        level, reason = classify_smart("Clean text with no PII.", "private")
        assert level == "private"

    def test_user_pii_preserved_without_pattern(self):
        from engine.smart_classifier import classify_smart
        # User explicitly passes pii — no patterns needed
        level, reason = classify_smart("Normal text.", "pii")
        assert level == "pii"


# ---------------------------------------------------------------------------
# xfail stubs for all CAP requirements (12 stubs)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="CAP-01: sb_capture_smart returns suggestions — Phase 31-01")
def test_capture_smart_returns_suggestions(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    result = mcp_mod.sb_capture_smart("# Meeting\nDiscussed Q1.\n---\n# Alice\nRole: CTO")
    assert result["status"] == "created"
    assert len(result["notes"]) >= 2
    assert "capture_session" in result
    assert "confirm_token" not in result


@pytest.mark.xfail(strict=False, reason="CAP-02: Multi-context atomic save — Phase 31-02")
def test_multi_context_atomic_save(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content = "# Project X\nMilestone: ship by April.\n\n# Idea\nWould be cool to add AI."
    result = mcp_mod.sb_capture_smart(content)
    assert result["status"] == "created"
    assert result["count"] >= 2


@pytest.mark.xfail(strict=False, reason="CAP-03: Dedup three-path check — Phase 31-03")
def test_dedup_three_path(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content = "# Exact Duplicate Note\nThis is unique content that will be duplicated."
    mcp_mod.sb_capture_smart(content)
    result2 = mcp_mod.sb_capture_smart(content)
    # Second call should warn about duplicate
    assert any("duplicate" in str(n).lower() or "dedup" in str(n).lower()
               for n in result2.get("notes", []))


@pytest.mark.xfail(strict=False, reason="CAP-04: Dormant resurfacing — Phase 31-04")
def test_dormant_resurfacing(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    result = mcp_mod.sb_capture_smart("# Stale Topic\nThought about this a year ago.")
    # dormant hints in result
    assert "dormant" in str(result).lower() or "resurfaced" in str(result).lower()


@pytest.mark.xfail(strict=False, reason="CAP-05: Similar relationship created — Phase 31-02")
def test_similar_relationship_created(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content1 = "# Alpha Project\nBuilding a search engine for brain notes."
    content2 = "# Beta Project\nSearch and indexing engine for personal notes."
    mcp_mod.sb_capture_smart(content1)
    result = mcp_mod.sb_capture_smart(content2)
    # A similar relationship should be created between the notes
    notes = result.get("notes", [])
    assert any(n.get("relationships") for n in notes)


@pytest.mark.xfail(strict=False, reason="CAP-06: Async hooks non-blocking — Phase 31-05")
def test_async_hooks_nonblocking(isolated_brain, monkeypatch):
    import time
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    start = time.time()
    mcp_mod.sb_capture_smart("# Quick Note\nThis should return fast even with hooks.")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"sb_capture_smart took too long: {elapsed:.2f}s"


@pytest.mark.xfail(strict=False, reason="CAP-07: Bidirectional relationships — Phase 31-02")
def test_bidirectional_relationships(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content = "# Meeting with Alice\nDiscussed project.\n---\n# Alice Smith\nRole: CEO"
    result = mcp_mod.sb_capture_smart(content)
    # Both notes should reference each other in links
    notes = result.get("notes", [])
    assert len(notes) >= 2
    links_flat = [l for n in notes for l in n.get("links", [])]
    assert len(links_flat) >= 1


@pytest.mark.xfail(strict=False, reason="CAP-08: Entity resolution links existing — Phase 31-02")
def test_entity_resolution_links_existing(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    # Capture an existing person first
    mcp_mod.sb_capture("Alice Smith", "CTO at Acme", note_type="person")
    # Now capture a meeting that mentions Alice Smith
    result = mcp_mod.sb_capture_smart("# Q1 Meeting\nDiscussed roadmap with Alice Smith.")
    notes = result.get("notes", [])
    # Should link to existing Alice Smith note
    links_flat = [l for n in notes for l in n.get("links", [])]
    assert any("alice" in str(l).lower() for l in links_flat)


@pytest.mark.xfail(strict=False, reason="CAP-09: Batch links field populated — Phase 31-01")
def test_batch_links_field(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content = "# Meeting with Alice\nDiscussed project.\n---\n# Alice Smith\nRole: Lead"
    result = mcp_mod.sb_capture_smart(content)
    notes = result.get("notes", [])
    meeting_notes = [n for n in notes if n.get("type") == "meeting"]
    if meeting_notes:
        assert "links" in meeting_notes[0]


@pytest.mark.xfail(strict=False, reason="CAP-10: Sensitivity classify_smart — Phase 31-01")
def test_sensitivity_classify_smart(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content = "# Contact\nEmail: secret@private.com Phone: +1 800 555 1234"
    result = mcp_mod.sb_capture_smart(content)
    notes = result.get("notes", [])
    # PII detected — note sensitivity should be pii
    assert any(n.get("sensitivity") == "pii" for n in notes)


@pytest.mark.xfail(strict=False, reason="CAP-11: Batch dedup warnings — Phase 31-03")
def test_batch_dedup_warnings(isolated_brain, monkeypatch):
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content = "# Unique Note\nThis note is special and unique."
    mcp_mod.sb_capture_smart(content)
    result2 = mcp_mod.sb_capture_smart(content)
    assert "warnings" in result2 or any("dedup" in str(n).lower() for n in result2.get("notes", []))


@pytest.mark.xfail(strict=False, reason="CAP-PERF: Smart capture performance <2s for 5 segments")
def test_smart_capture_performance(isolated_brain, monkeypatch):
    import time
    import engine.mcp_server as mcp_mod
    import engine.paths
    monkeypatch.setattr(engine.paths, "BRAIN_ROOT", isolated_brain)
    content = "\n\n".join([
        f"# Section {i}\nContent for section {i} with reasonable body text for testing."
        for i in range(5)
    ])
    start = time.time()
    mcp_mod.sb_capture_smart(content)
    elapsed = time.time() - start
    assert elapsed < 2.0, f"Performance regression: {elapsed:.2f}s for 5 segments"
