"""Tests for engine/passes/ — decompose() orchestrator and pass functions."""
import pytest
from engine.passes import (
    CONFIDENCE_THRESHOLD,
    ActionItem,
    DecomposedResult,
    LinkNote,
    classify_content,
    decompose,
    extract_all_entities,
    extract_keyword_actions,
    extract_urls,
)


class TestDecomposeShape:
    """decompose() return type and structure."""

    def test_decompose_returns_list(self):
        results = decompose("some text")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_decompose_empty_returns_single_note(self):
        results = decompose("")
        assert len(results) == 1
        assert results[0].primary_type == "note"

    def test_decompose_result_fields(self):
        results = decompose("some content")
        r = results[0]
        assert hasattr(r, "primary_title")
        assert hasattr(r, "primary_type")
        assert hasattr(r, "primary_body")
        assert hasattr(r, "confidence")
        assert hasattr(r, "entities")
        assert hasattr(r, "link_notes")
        assert hasattr(r, "action_items")
        assert hasattr(r, "person_stubs")
        assert hasattr(r, "existing_people")

    def test_decompose_result_is_dataclass(self):
        results = decompose("hello world")
        assert isinstance(results[0], DecomposedResult)


class TestPass1Entities:
    """Pass 1: extract_all_entities()."""

    def test_extracts_people(self):
        result = extract_all_entities(
            "Met with Alice Johnson about the project. Role: engineer."
        )
        assert "Alice Johnson" in result.get("people", [])

    def test_returns_dict_with_expected_keys(self):
        result = extract_all_entities("some content")
        assert isinstance(result, dict)
        for key in ("people", "topics", "places", "orgs"):
            assert key in result

    def test_empty_content_returns_empty_lists(self):
        result = extract_all_entities("")
        assert result.get("people", []) == []

    def test_no_signals_returns_no_people(self):
        # Pure product description — no person-context signals
        result = extract_all_entities("Voice Controlled App Widget Dashboard")
        assert result.get("people", []) == []


class TestPass2Urls:
    """Pass 2: extract_urls()."""

    def test_extracts_url_and_returns_link_note(self):
        _stripped, links = extract_urls("Check https://zoom.us/j/123 for the meeting")
        assert len(links) == 1
        assert links[0].url == "https://zoom.us/j/123"
        assert links[0].title == "zoom.us"

    def test_strips_url_from_content(self):
        stripped, _links = extract_urls("Check https://zoom.us/j/123 for the meeting")
        assert "https://" not in stripped

    def test_no_urls_returns_empty_list_and_original(self):
        stripped, links = extract_urls("No URLs here at all")
        assert links == []
        assert stripped == "No URLs here at all"

    def test_multiple_urls_produce_multiple_link_notes(self):
        content = "See https://example.com and https://zoom.us/j/abc"
        _stripped, links = extract_urls(content)
        assert len(links) == 2

    def test_link_note_body_is_source_line(self):
        content = "Meeting link: https://zoom.us/j/123"
        _stripped, links = extract_urls(content)
        assert links[0].body == "Meeting link: https://zoom.us/j/123"

    def test_returns_tuple_of_two(self):
        result = extract_urls("some text")
        assert isinstance(result, tuple) and len(result) == 2

    def test_link_note_is_dataclass(self):
        _s, links = extract_urls("https://example.com")
        assert isinstance(links[0], LinkNote)

    def test_duplicate_url_produces_one_link_note(self):
        content = "https://example.com and again https://example.com"
        _stripped, links = extract_urls(content)
        assert len(links) == 1


class TestPass3Classify:
    """Pass 3: classify_content()."""

    def test_meeting_keywords_classify_as_meeting(self):
        t, c = classify_content(
            "Meeting",
            "attendees: Alice, Bob\nAgenda: Q1 review\nminutes noted",
        )
        assert t == "meeting"
        assert c >= CONFIDENCE_THRESHOLD

    def test_url_stripped_meeting_classifies_as_meeting_not_link(self):
        # URL already stripped by Pass 2 — should be meeting, not link
        t, _c = classify_content(
            "Meeting notes",
            "Meeting with Alice\nAttendees: Bob, Carol\nAgenda: Q1 review\nDiscussed budget",
        )
        assert t == "meeting"
        assert t != "link"

    def test_returns_tuple_str_float(self):
        t, c = classify_content("title", "body")
        assert isinstance(t, str)
        assert isinstance(c, float)


class TestConversationSignal:
    """D-11: Name [HH:MM] pattern boosts meeting confidence to >= 0.85."""

    def test_two_turns_classify_as_meeting_with_boost(self):
        body = "Alice [14:32] said hello\nBob [14:35] replied"
        t, c = classify_content("Chat", body)
        assert t == "meeting"
        assert c >= 0.85

    def test_one_turn_does_not_boost_to_meeting_0_85(self):
        body = "Alice [14:32] said hello"
        t, c = classify_content("Chat", body)
        # A single turn must NOT produce (meeting, >= 0.85) via the boost alone
        assert not (t == "meeting" and c >= 0.85)

    def test_two_turns_unicode_names(self):
        body = "Päivi [09:15] mentioned the issue\nMäkinen [09:17] agreed"
        t, c = classify_content("Chat", body)
        assert t == "meeting"
        assert c >= 0.85

    def test_strong_meeting_keywords_not_downgraded_by_boost(self):
        # Classifier returns (meeting, 0.95) — boost (0.85) must not override
        body = "attendees: Alice\nAgenda: planning\nminutes: none\nAlice [10:00] spoke\nBob [10:05] replied"
        t, c = classify_content("Weekly Meeting", body)
        assert t == "meeting"
        # Should keep high confidence, not be capped at boost value
        assert c >= 0.85


class TestDecomposeIntegration:
    """End-to-end decompose() with realistic content."""

    def test_meeting_with_zoom_url_classified_correctly(self):
        content = (
            "meeting notes\n"
            "Attended: Alice\n"
            "https://zoom.us/j/123\n"
            "Discussed budget"
        )
        results = decompose(content)
        assert len(results) >= 1
        r = results[0]
        assert r.primary_type == "meeting"
        assert len(r.link_notes) == 1
        assert r.link_notes[0].url == "https://zoom.us/j/123"

    def test_url_not_in_primary_body(self):
        content = "notes\nhttps://example.com\nsome content here and more text"
        results = decompose(content)
        assert "https://" not in results[0].primary_body

    def test_link_notes_list_type(self):
        results = decompose("https://example.com")
        assert isinstance(results[0].link_notes, list)


class TestPass4Actions:
    """Pass 4: extract_keyword_actions()."""

    def test_todo_extracted(self):
        items = extract_keyword_actions("TODO: call Alice\nSome text")
        assert len(items) == 1
        assert "call Alice" in items[0].text
        assert items[0].source == "keyword"

    def test_ap_extracted(self):
        items = extract_keyword_actions("AP: review budget")
        assert len(items) == 1
        assert "review budget" in items[0].text

    def test_action_colon_extracted(self):
        items = extract_keyword_actions("action: send email to Bob")
        assert len(items) == 1
        assert "send email to Bob" in items[0].text

    def test_action_point_extracted(self):
        items = extract_keyword_actions("Action Point: schedule meeting")
        assert len(items) == 1
        assert "schedule meeting" in items[0].text

    def test_multiple_markers(self):
        body = "TODO: call Alice\nSome text\nAP: review budget"
        items = extract_keyword_actions(body)
        assert len(items) == 2

    def test_no_markers_returns_empty(self):
        items = extract_keyword_actions("No action items here at all")
        assert items == []

    def test_at_owner_extracts_owner(self):
        items = extract_keyword_actions("@alice review the spec")
        assert len(items) == 1
        assert items[0].owner == "alice"
        assert "review the spec" in items[0].text

    def test_returns_action_item_instances(self):
        items = extract_keyword_actions("TODO: test this")
        assert isinstance(items[0], ActionItem)

    def test_case_insensitive(self):
        items = extract_keyword_actions("todo: lowercase marker")
        assert len(items) == 1


class TestCustomMarkers:
    """Custom markers from config.toml are recognised by Pass 4."""

    def test_custom_marker_extracted(self):
        items = extract_keyword_actions("DECISION: go with option A", custom_markers=["DECISION"])
        assert len(items) == 1
        assert "go with option A" in items[0].text
        assert items[0].source == "keyword"

    def test_unknown_marker_not_extracted(self):
        items = extract_keyword_actions("DECISION: go with option A", custom_markers=[])
        assert items == []

    def test_custom_marker_combined_with_defaults(self):
        body = "TODO: fix bug\nDECISION: use postgres"
        items = extract_keyword_actions(body, custom_markers=["DECISION"])
        assert len(items) == 2


class TestPass5Assembly:
    """Pass 5: assemble() populates person_stubs and existing_people."""

    @pytest.fixture()
    def isolated_brain(self, tmp_path, monkeypatch):
        import engine.db
        import engine.paths
        brain_root = tmp_path / "brain"
        brain_root.mkdir()
        (brain_root / ".meta").mkdir()
        db_path = brain_root / ".meta" / "brain.db"
        monkeypatch.setattr(engine.db, "DB_PATH", db_path)
        monkeypatch.setattr(engine.paths, "DB_PATH", db_path)
        monkeypatch.setattr(engine.paths, "BRAIN_ROOT", brain_root)
        from engine.db import init_schema, get_connection
        conn = get_connection(str(db_path))
        init_schema(conn)
        conn.close()
        return brain_root

    def test_assemble_populates_stubs(self, isolated_brain):
        from engine.db import get_connection
        from engine.passes.p5_assemble import assemble
        conn = get_connection()
        results = decompose("Met with Alice Johnson about the project. Role: engineer.")
        result = assemble(results, conn, isolated_brain)
        conn.close()
        # Alice Johnson has no existing note → should be a new stub
        all_stubs = [s for r in result for s in r.person_stubs]
        assert any("Alice Johnson" in s.get("name", "") for s in all_stubs)

    def test_decompose_with_conn_runs_pass5(self, isolated_brain):
        from engine.db import get_connection
        conn = get_connection()
        results = decompose(
            "Met with Alice Johnson. Role: engineer.",
            conn=conn,
            brain_root=isolated_brain,
        )
        conn.close()
        assert isinstance(results[0].person_stubs, list)
        assert isinstance(results[0].existing_people, list)


class TestDecomposeWithActions:
    """decompose() produces action_items via Pass 4."""

    def test_action_items_populated(self):
        results = decompose("Project update\nTODO: fix the bug\nSome other content here")
        assert any(len(r.action_items) > 0 for r in results)

    def test_action_items_are_action_item_instances(self):
        results = decompose("TODO: do something important here today")
        items = results[0].action_items
        assert all(isinstance(i, ActionItem) for i in items)
