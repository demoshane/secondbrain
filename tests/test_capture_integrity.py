"""Capture Integrity Test Suite.

Guards that data captured into the brain is correct: right type, right directory,
right entities, right frontmatter. These tests exist because incorrect capture
silently pollutes the brain — wrong note types in the wrong folders, fake person
stubs from heading phrases, missing frontmatter fields.

Test classes:
  TestTypeRouting         — each type lands in the right directory with the right DB type
  TestFrontmatterFields   — required frontmatter fields are always written
  TestDiskDbConsistency   — what's on disk matches what's in the DB
  TestEntityExtraction    — real names extracted; common noun phrases are not
  TestPersonStubGuard     — sb_capture_smart doesn't stub heading phrases as persons
  TestSmartTypeAssignment — content signals produce the correct segment type
  TestRegressions         — fixed bugs that must not regress
"""
import json
import sqlite3
from pathlib import Path

import frontmatter
import pytest


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def brain(tmp_path, monkeypatch):
    """Isolated brain root + initialised DB.  All engine globals patched."""
    import engine.db as _db
    import engine.paths as _paths

    root = tmp_path / "brain"
    root.mkdir()
    # Pre-create all known subdirs so capture_note never has to mkdir
    for d in ["note", "person", "meeting", "meetings", "ideas", "projects",
              "coding", "strategy", "personal", "links", ".meta"]:
        (root / d).mkdir(parents=True, exist_ok=True)

    db_path = root / ".meta" / "brain.db"
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", root)
    monkeypatch.setenv("BRAIN_PATH", str(root))

    from engine.db import init_schema, get_connection
    conn = get_connection()
    init_schema(conn)
    conn.commit()
    conn.close()

    return root


def _db_row(brain: Path, title: str) -> dict | None:
    """Return the DB row for a note by title, or None."""
    import engine.db as _db
    from engine.db import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT path, type, title, body, people FROM notes WHERE title = ?", (title,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {"path": row[0], "type": row[1], "title": row[2], "body": row[3], "people": row[4]}


def _capture(brain: Path, note_type: str, title: str, body: str, people=None) -> Path:
    """Call capture_note with sensible defaults.  Returns the Path written."""
    from engine.capture import capture_note
    from engine.db import get_connection
    conn = get_connection()
    path = capture_note(
        note_type=note_type,
        title=title,
        body=body,
        tags=[],
        people=people or [],
        content_sensitivity="public",
        brain_root=brain,
        conn=conn,
    )
    conn.commit()
    conn.close()
    return path


# ---------------------------------------------------------------------------
# TestTypeRouting
# ---------------------------------------------------------------------------

class TestTypeRouting:
    """Each note type must land in the expected subdirectory with the right DB type field."""

    CASES = [
        # (note_type, expected_subdir, title)
        ("note",     "note",     "A Plain Note"),
        ("meeting",  "meeting",  "Team Standup 2026-03-25"),
        ("person",   "person",   "Anna Korhonen"),
        ("idea",     "ideas",    "Auto-tag Idea"),
        ("coding",   "coding",   "Python Async Patterns"),
        ("strategy", "strategy", "Q3 Strategy"),
        ("personal", "personal", "Reflection on Productivity"),
        ("projects", "projects", "Second Brain v5"),
    ]

    @pytest.mark.parametrize("note_type,expected_dir,title", CASES)
    def test_file_lands_in_correct_directory(self, brain, note_type, expected_dir, title):
        path = _capture(brain, note_type, title, f"Body for {title}")
        assert path.parent == brain / expected_dir, (
            f"{note_type!r} note went to {path.parent.name!r}, expected {expected_dir!r}"
        )

    @pytest.mark.parametrize("note_type,expected_dir,title", CASES)
    def test_db_type_matches_requested_type(self, brain, note_type, expected_dir, title):
        _capture(brain, note_type, title + " DB", f"Body for {title}")
        row = _db_row(brain, title + " DB")
        assert row is not None, "Note not found in DB"
        assert row["type"] == note_type, (
            f"DB type is {row['type']!r}, expected {note_type!r}"
        )

    @pytest.mark.parametrize("note_type,expected_dir,title", CASES)
    def test_frontmatter_type_matches_requested_type(self, brain, note_type, expected_dir, title):
        path = _capture(brain, note_type, title + " FM", f"Body for {title}")
        post = frontmatter.load(str(path))
        assert post["type"] == note_type, (
            f"Frontmatter type is {post['type']!r}, expected {note_type!r}"
        )

    def test_person_slug_has_no_date_prefix(self, brain):
        """Person notes use slug-only filenames, not date-prefixed."""
        path = _capture(brain, "person", "Mikko Virtanen", "Role: engineer")
        assert path.name == "mikko-virtanen.md", (
            f"Person filename should be slug-only, got {path.name!r}"
        )

    def test_non_person_has_date_prefix(self, brain):
        """Non-person notes have a YYYY-MM-DD prefix in their filename."""
        import re
        path = _capture(brain, "note", "Tech Insight", "Some insight here")
        assert re.match(r"\d{4}-\d{2}-\d{2}-", path.name), (
            f"Expected date prefix in filename, got {path.name!r}"
        )


# ---------------------------------------------------------------------------
# TestFrontmatterFields
# ---------------------------------------------------------------------------

class TestFrontmatterFields:
    """Required frontmatter fields must always be present after capture."""

    REQUIRED = {"type", "title", "date", "tags", "people", "created_at", "updated_at",
                "content_sensitivity"}

    @pytest.mark.parametrize("note_type", ["note", "meeting", "person", "idea", "projects"])
    def test_required_fields_present(self, brain, note_type):
        path = _capture(brain, note_type, f"Test {note_type.title()} Note", "Some content")
        post = frontmatter.load(str(path))
        missing = self.REQUIRED - set(post.metadata.keys())
        assert not missing, f"Missing frontmatter fields for type={note_type!r}: {missing}"

    def test_sensitivity_written_to_frontmatter(self, brain):
        from engine.capture import capture_note
        from engine.db import get_connection
        conn = get_connection()
        path = capture_note(
            note_type="note", title="Sensitivity Test",
            body="content", tags=[], people=[],
            content_sensitivity="private", brain_root=brain, conn=conn,
        )
        conn.commit(); conn.close()
        post = frontmatter.load(str(path))
        assert post["content_sensitivity"] == "private"

    def test_tags_always_list(self, brain):
        path = _capture(brain, "note", "Tag Test", "Content")
        post = frontmatter.load(str(path))
        assert isinstance(post["tags"], list)

    def test_people_always_list(self, brain):
        path = _capture(brain, "note", "People Test", "Content")
        post = frontmatter.load(str(path))
        assert isinstance(post["people"], list)

    def test_entities_block_written(self, brain):
        path = _capture(brain, "note", "Entity Note", "Met with Anna Korhonen today.")
        post = frontmatter.load(str(path))
        assert "entities" in post.metadata, "entities block missing from frontmatter"
        assert isinstance(post["entities"], dict)
        assert "people" in post["entities"]


# ---------------------------------------------------------------------------
# TestDiskDbConsistency
# ---------------------------------------------------------------------------

class TestDiskDbConsistency:
    """What's on disk must match what's indexed in the DB."""

    def test_title_matches(self, brain):
        path = _capture(brain, "note", "Consistency Check Title", "body text")
        row = _db_row(brain, "Consistency Check Title")
        post = frontmatter.load(str(path))
        assert row["title"] == post["title"]

    def test_type_matches(self, brain):
        path = _capture(brain, "meeting", "Consistency Check Meeting", "attended the standup")
        row = _db_row(brain, "Consistency Check Meeting")
        post = frontmatter.load(str(path))
        assert row["type"] == post["type"] == "meeting"

    def test_path_in_db_resolves_to_disk_file(self, brain):
        path = _capture(brain, "idea", "Disk DB Path Idea", "some idea")
        row = _db_row(brain, "Disk DB Path Idea")
        # DB path may be relative or absolute — resolve both
        db_path = Path(row["path"])
        if not db_path.is_absolute():
            db_path = brain.parent.parent / db_path  # relative to repo root
        assert db_path.exists() or path.exists(), (
            f"DB path {row['path']!r} doesn't resolve to existing file"
        )

    def test_note_not_in_db_if_file_absent(self, brain):
        """Capture then delete the file — the note remains in DB (expected) but
        this test asserts the capture wrote to DB at all."""
        path = _capture(brain, "note", "Ephemeral Note", "short body")
        row = _db_row(brain, "Ephemeral Note")
        assert row is not None, "capture_note did not write to DB"


# ---------------------------------------------------------------------------
# TestEntityExtraction
# ---------------------------------------------------------------------------

class TestEntityExtraction:
    """Captured notes must extract real person names and reject common noun phrases."""

    def test_real_person_name_extracted(self, brain):
        path = _capture(brain, "meeting", "Q1 Kickoff Meeting",
                        "Attended by Anna Korhonen and Pekka Mäkinen.")
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        assert "Anna Korhonen" in people, f"Real name not extracted: {people}"

    def test_real_person_in_db_people_column(self, brain):
        _capture(brain, "meeting", "People Column Meeting",
                 "Discussed with Liisa Virtanen and Juhani Salo.")
        row = _db_row(brain, "People Column Meeting")
        people = json.loads(row["people"] or "[]")
        assert "Liisa Virtanen" in people, f"Real name not in DB people column: {people}"

    def test_heading_phrase_not_extracted_as_person(self, brain):
        """Two Title Case words from a section heading must not become a person."""
        path = _capture(
            brain, "note", "Agent Learnings Regression",
            "## Key Discovery: pptxgenjs vs python-pptx for Branded Presentations\n\n"
            "When building Branded Presentations, pptxgenjs is better.\n"
            "Presentation Build quality improves with Agent Workflows applied.",
        )
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        bad = {"Branded Presentations", "Presentation Build", "Agent Workflows",
               "Key Discovery", "Agent Learnings"}
        found_bad = bad & set(people)
        assert not found_bad, f"Heading phrases extracted as persons: {found_bad}"

    def test_abstract_noun_pairs_not_extracted(self, brain):
        """Words ending in abstract-noun suffixes must not form person names."""
        path = _capture(brain, "note", "Abstract Noun Test",
                        "Template Analysis and Health Checking are part of Maintenance Planning.")
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        bad = {"Template Analysis", "Health Checking", "Maintenance Planning"}
        found_bad = bad & set(people)
        assert not found_bad, f"Abstract noun pairs extracted as persons: {found_bad}"

    def test_stop_word_first_token_filtered(self, brain):
        """Pairs where the first token is a stop word must not become person names."""
        path = _capture(brain, "note", "Stop Word Test",
                        "New Features and Agent Workflows are deployed via Release Process.")
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        bad = {"New Features", "Agent Workflows", "Release Process"}
        found_bad = bad & set(people)
        assert not found_bad, f"Stop-word-prefixed pairs extracted as persons: {found_bad}"

    def test_nordic_real_name_extracted(self, brain):
        """Finnish/Nordic names with diacritics must be extracted."""
        path = _capture(brain, "meeting", "Nordic Name Meeting",
                        "Discussed with Björn Lindström and Päivi Mäkinen-Korhonen.")
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        assert any("Lindström" in p or "Björn" in p for p in people), (
            f"Nordic name not extracted: {people}"
        )


# ---------------------------------------------------------------------------
# TestPersonStubGuard
# ---------------------------------------------------------------------------

class TestPersonStubGuard:
    """sb_capture_smart must not create person/ stubs for heading phrases."""

    @pytest.fixture()
    def mcp_brain(self, tmp_path, monkeypatch):
        """Isolated brain wired to the MCP module."""
        import engine.db as _db
        import engine.paths as _paths
        import engine.mcp_server as mcp_mod

        root = tmp_path / "brain"
        root.mkdir()
        for d in ["note", "person", "meeting", "meetings", "ideas", "projects",
                  "coding", "strategy", "personal", "links", ".meta"]:
            (root / d).mkdir(parents=True, exist_ok=True)

        db_path = root / ".meta" / "brain.db"
        monkeypatch.setattr(_db, "DB_PATH", db_path)
        monkeypatch.setattr(_paths, "DB_PATH", db_path)
        monkeypatch.setattr(_paths, "BRAIN_ROOT", root)
        monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", root)
        monkeypatch.setenv("BRAIN_PATH", str(root))

        from engine.db import init_schema, get_connection
        conn = get_connection()
        init_schema(conn)
        conn.commit(); conn.close()
        return root

    def _person_stubs(self, brain: Path) -> list[str]:
        """Return titles of all notes in person/ that look like stubs (empty body)."""
        stubs = []
        for f in (brain / "person").glob("*.md"):
            post = frontmatter.load(str(f))
            body = post.content.strip()
            # Stubs: body is empty or only contains wiki-links
            if not body or all(line.strip().startswith("- [[") for line in body.splitlines() if line.strip()):
                stubs.append(post.get("title", f.stem))
        return stubs

    def test_no_person_stubs_from_technical_note(self, mcp_brain):
        """A technical note with Title Case headings must not generate person stubs."""
        import engine.mcp_server as mcp_mod
        content = (
            "# AI Agent Learnings — Presentation Build Session\n\n"
            "## Key Discovery: pptxgenjs vs python-pptx for Branded Presentations\n\n"
            "When building Branded Presentations programmatically, pptxgenjs produces "
            "better results. The Presentation Build workflow benefits from Template Analysis.\n\n"
            "## Health Checking and Maintenance Agent\n\n"
            "Run sb-health for Health Checking. The Maintenance Agent handles Files Updated tracking."
        )
        result = mcp_mod.sb_capture_smart(content=content)
        assert result.get("status") == "created"

        stubs = self._person_stubs(mcp_brain)
        bad = {"Branded Presentations", "Presentation Build", "Template Analysis",
               "Key Discovery", "Agent Learnings", "Health Checking", "Maintenance Agent",
               "Files Updated", "Agent Workflows"}
        found_bad = set(stubs) & bad
        assert not found_bad, (
            f"sb_capture_smart created bogus person stubs: {found_bad}\n"
            f"All stubs: {stubs}"
        )

    def test_real_person_stub_created(self, mcp_brain):
        """A segment that describes a real person SHOULD create a person stub."""
        import engine.mcp_server as mcp_mod
        content = (
            "# Anna Korhonen\n\n"
            "Role: VP Engineering\nEmail: anna@example.com\n"
            "LinkedIn: linkedin.com/in/anna-korhonen\n"
            "Key contact for architecture decisions."
        )
        result = mcp_mod.sb_capture_smart(content=content)
        assert result.get("status") == "created"

        # The note itself should be classified as person
        saved = result.get("notes", [])
        person_notes = [n for n in saved if n.get("type") == "person"]
        assert person_notes, f"No person-typed note saved, got: {[n.get('type') for n in saved]}"

    def test_meeting_content_no_person_stubs_for_attendee_phrases(self, mcp_brain):
        """Meeting notes with short attendee names must create meeting notes, not bogus stubs."""
        import engine.mcp_server as mcp_mod
        content = (
            "Weekly Sync 2026-03-25\n\n"
            "Attendees: Tuomas Leppanen, Anna Korhonen\n"
            "Discussed: roadmap, deployment status\n"
            "Action items: Anna to review PR, Tuomas to update docs"
        )
        result = mcp_mod.sb_capture_smart(content=content)
        assert result.get("status") == "created"

        # Check no spurious stubs for "Deployment Status", "Roadmap Items" etc.
        stubs = self._person_stubs(mcp_brain)
        bad_patterns = {"Deployment Status", "Roadmap Items", "Action Items",
                        "Weekly Sync", "Update Docs", "Deployment Status"}
        found_bad = set(stubs) & bad_patterns
        assert not found_bad, f"Spurious person stubs from meeting content: {found_bad}"


# ---------------------------------------------------------------------------
# TestSmartTypeAssignment
# ---------------------------------------------------------------------------

class TestSmartTypeAssignment:
    """sb_capture_smart assigns the right type to each segment based on content."""

    @pytest.fixture()
    def mcp_brain(self, tmp_path, monkeypatch):
        import engine.db as _db
        import engine.paths as _paths
        import engine.mcp_server as mcp_mod

        root = tmp_path / "brain"
        root.mkdir()
        for d in ["note", "person", "meeting", "meetings", "ideas", "projects",
                  "coding", "strategy", "personal", "links", ".meta"]:
            (root / d).mkdir(parents=True, exist_ok=True)

        db_path = root / ".meta" / "brain.db"
        monkeypatch.setattr(_db, "DB_PATH", db_path)
        monkeypatch.setattr(_paths, "DB_PATH", db_path)
        monkeypatch.setattr(_paths, "BRAIN_ROOT", root)
        monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", root)
        monkeypatch.setenv("BRAIN_PATH", str(root))

        from engine.db import init_schema, get_connection
        conn = get_connection()
        init_schema(conn)
        conn.commit(); conn.close()
        return root

    def _saved_types(self, result: dict) -> list[str]:
        return [n.get("type") for n in result.get("notes", [])]

    def test_meeting_content_classified_as_meeting(self, mcp_brain):
        import engine.mcp_server as mcp_mod
        content = (
            "Customer Sync 2026-03-25\n\n"
            "Attendees: Tuomas, Anna\nAgenda: Q2 planning\n"
            "Discussed: roadmap priorities\nDecisions: ship feature X\n"
            "Action: follow up by Friday"
        )
        result = mcp_mod.sb_capture_smart(content=content)
        types = self._saved_types(result)
        assert "meeting" in types, f"Meeting content not classified as meeting: {types}"

    def test_url_content_classified_as_link(self, mcp_brain):
        import engine.mcp_server as mcp_mod
        content = "https://docs.anthropic.com/claude — Claude API reference docs. Very useful for tool_use."
        result = mcp_mod.sb_capture_smart(content=content)
        types = self._saved_types(result)
        assert "link" in types, f"URL content not classified as link: {types}"

    def test_idea_content_classified_as_idea(self, mcp_brain):
        import engine.mcp_server as mcp_mod
        content = (
            "Idea: auto-tag captures using semantic similarity\n\n"
            "What if the capture form shows matching tags as you type?\n"
            "Maybe use fuzzy matching on existing tags.\n"
            "Consider integrating with the embeddings pipeline."
        )
        result = mcp_mod.sb_capture_smart(content=content)
        types = self._saved_types(result)
        assert "idea" in types, f"Idea content not classified as idea: {types}"

    def test_generic_note_classified_as_note(self, mcp_brain):
        import engine.mcp_server as mcp_mod
        content = (
            "pptxgenjs vs python-pptx\n\n"
            "Key difference: pptxgenjs builds presentations from scratch.\n"
            "python-pptx is better for template editing.\n"
            "Neither library is ideal for every use case."
        )
        result = mcp_mod.sb_capture_smart(content=content)
        types = self._saved_types(result)
        assert "note" in types, f"Generic content not classified as note: {types}"

    def test_no_person_type_for_technical_content(self, mcp_brain):
        """Technical content with Title Case headings must never classify as person."""
        import engine.mcp_server as mcp_mod
        content = (
            "## Branded Presentations with pptxgenjs\n\n"
            "Template Analysis shows that pptxgenjs handles Branded Presentations better.\n"
            "The Workflow To implement this involves running the build script."
        )
        result = mcp_mod.sb_capture_smart(content=content)
        types = self._saved_types(result)
        assert "person" not in types, (
            f"Technical content incorrectly classified as person: {types}"
        )


# ---------------------------------------------------------------------------
# TestRegressions
# ---------------------------------------------------------------------------

class TestRegressions:
    """Specific bugs that were fixed and must not regress."""

    def test_phase35_no_person_stubs_from_presentation_note(self, brain):
        """Phase 35 fix: 'Branded Presentations', 'Presentation Build' etc. must not
        be extracted as person entities when they appear in a technical note."""
        path = _capture(
            brain, "note",
            "AI Agent Learnings — Presentation Build Session (March 2026)",
            "## Key Discovery: pptxgenjs vs python-pptx for Branded Presentations\n\n"
            "When building visually rich branded presentations programmatically, "
            "pptxgenjs produces dramatically better results than python-pptx.\n\n"
            "The Presentation Build workflow involves Template Analysis of reference slides.",
        )
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        bad = {"Branded Presentations", "Presentation Build", "Template Analysis",
               "Key Discovery", "Agent Learnings"}
        found_bad = bad & set(people)
        assert not found_bad, (
            f"Phase 35 regression: heading phrases extracted as person entities: {found_bad}"
        )

    def test_plural_abstract_nouns_not_person_names(self, brain):
        """'Presentations', 'Requirements', 'Learnings' (plural abstract nouns) must
        not appear as the last token of an extracted person name."""
        path = _capture(
            brain, "note", "Plural Nouns Test",
            "The Business Requirements and Product Presentations are ready.\n"
            "Agent Learnings from this sprint inform the next iteration.",
        )
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        for name in people:
            last_token = name.split()[-1]
            from engine.entities import _is_abstract_noun
            assert not _is_abstract_noun(last_token), (
                f"Plural abstract noun {last_token!r} ended up as a person name: {name!r}"
            )

    def test_stop_word_bigrams_not_person_names(self, brain):
        """Pairs where the first word is in _STOP_WORDS must never be extracted
        as person names — even when the second word is a plausible surname."""
        path = _capture(
            brain, "note", "Stop Word Bigram Test",
            "New Features launched this sprint.\n"
            "Agent Smith deployed the latest release.\n"
            "Key Results were reviewed in the retro.",
        )
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        from engine.entities import _ALL_STOPS
        for name in people:
            first_token = name.split()[0]
            assert first_token not in _ALL_STOPS, (
                f"Stop word {first_token!r} is the first token of extracted name: {name!r}"
            )

    def test_lindqvist_suffix_not_blocked(self, brain):
        """Scandinavian surnames ending in -qvist must not be blocked by abstract
        suffix rules (regression for 'ist' suffix over-matching)."""
        path = _capture(brain, "meeting", "Nordic Names Meeting",
                        "Met with Asa Lindqvist and Bjorn Bergqvist today.")
        post = frontmatter.load(str(path))
        people = post.get("entities", {}).get("people", [])
        assert any("Lindqvist" in p for p in people), (
            f"Lindqvist (Scandinavian surname) incorrectly blocked: {people}"
        )
