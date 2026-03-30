"""Tests for engine/typeclassifier.py — note type classification with confidence."""
import pytest
from engine.typeclassifier import classify_note_type, CONFIDENCE_THRESHOLD


class TestClassifyNoteType:
    """Core type + confidence checks."""

    # --- link ---
    def test_url_gives_link(self):
        # URL-dominant body (stripped text < 50 chars) still classifies as link
        t, c = classify_note_type("Check this", "https://example.com is the resource.")
        assert t == "link"
        assert c >= CONFIDENCE_THRESHOLD

    def test_meeting_with_url_classifies_as_meeting(self):
        body = (
            "Meeting with Alice\n"
            "Attendees: Bob, Carol\n"
            "Agenda: Q1 review\n"
            "https://zoom.us/j/123456"
        )
        t, _c = classify_note_type("Meeting Notes", body)
        assert t == "meeting"

    def test_url_only_body_classifies_as_link(self):
        # Short surrounding text + URL → URL is the primary content
        t, c = classify_note_type("", "https://example.com/article interesting read")
        assert t == "link"
        assert c >= CONFIDENCE_THRESHOLD

    # --- meeting ---
    def test_strong_meeting_keyword(self):
        t, c = classify_note_type("Q1 Planning Meeting", "")
        assert t == "meeting"
        assert c >= CONFIDENCE_THRESHOLD

    def test_meeting_from_body(self):
        t, c = classify_note_type("Notes", "Meeting attendees: Alice, Bob. Agenda: Q2 roadmap.")
        assert t == "meeting"
        assert c >= CONFIDENCE_THRESHOLD

    # --- person ---
    def test_person_name_only(self):
        t, c = classify_note_type("Alice Johnson", "")
        assert t == "person"
        assert c >= 0.75

    def test_person_name_with_contact(self):
        t, c = classify_note_type("Alice Johnson", "Role: CTO at Acme. Contact: alice@acme.com.")
        assert t == "person"
        assert c >= CONFIDENCE_THRESHOLD

    def test_product_name_not_person(self):
        """Title-case product names must NOT be classified as person."""
        for title in ["Mac App", "Harvest Timer", "Voice-Controlled Harvest", "Task Manager"]:
            t, _c = classify_note_type(title, "Some description of the tool.")
            assert t != "person", f"{title!r} wrongly classified as person"

    def test_single_word_title_not_person(self):
        t, _c = classify_note_type("Notion", "A productivity app I use daily.")
        assert t != "person"

    # --- coding ---
    def test_code_block_gives_coding(self):
        t, c = classify_note_type("Refactor notes", "Here is the code:\n```python\ndef foo(): pass\n```")
        assert t == "coding"
        assert c >= CONFIDENCE_THRESHOLD

    def test_coding_keywords(self):
        t, c = classify_note_type("Bug fix", "Fixed a bug in the refactor. Added a test. Deployed via CI.")
        assert t == "coding"
        assert c >= CONFIDENCE_THRESHOLD

    # --- project ---
    def test_project_keywords(self):
        t, c = classify_note_type("Project Alpha", "Milestone: ship by April. Sprint 1. Roadmap aligned.")
        assert t == "project"
        assert c >= CONFIDENCE_THRESHOLD

    # --- strategy ---
    def test_strategy_keywords(self):
        t, c = classify_note_type("Q2 Strategy", "Our OKRs for the quarter. Vision: market leadership. KPIs defined.")
        assert t == "strategy"
        assert c >= CONFIDENCE_THRESHOLD

    # --- idea ---
    def test_idea_keywords(self):
        t, c = classify_note_type("Idea: AI suggestions", "What if we added AI? Consider using embeddings. Brainstorm.")
        assert t == "idea"
        assert c >= CONFIDENCE_THRESHOLD

    # --- personal ---
    def test_personal_keywords(self):
        t, c = classify_note_type("Personal reflection", "Today I felt grateful. Mood was good. Journal entry.")
        assert t == "personal"
        assert c >= CONFIDENCE_THRESHOLD

    # --- note fallback ---
    def test_generic_text_falls_back_to_note(self):
        t, c = classify_note_type("Tech notes", "Some random content with no strong signals.")
        assert t == "note"
        assert c >= CONFIDENCE_THRESHOLD

    # --- confidence threshold ---
    def test_low_confidence_below_threshold(self):
        """A vague title with a single weak keyword should be below CONFIDENCE_THRESHOLD."""
        _t, c = classify_note_type("Random idea about stuff", "")
        assert c < CONFIDENCE_THRESHOLD

    def test_high_confidence_at_or_above_threshold(self):
        _t, c = classify_note_type("Weekly Standup", "")
        assert c >= CONFIDENCE_THRESHOLD
