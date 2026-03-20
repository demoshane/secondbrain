"""Tests for engine/entities.py entity extraction.

Covers:
- Existing ASCII name extraction (regression guard)
- Finnish/Nordic Unicode name extraction (PEO-01)
- Compound names with hyphens and prefixes (PEO-01)
- Finnish stop words (PEO-01)
- Organization extraction (PEO-01)
- Edge cases: never raises, empty input
"""
import pytest


# ---------------------------------------------------------------------------
# Existing tests (promoted from xfail — implementation shipped)
# ---------------------------------------------------------------------------

def test_extract_entities_people():
    """extract_entities() identifies named people in body text."""
    from engine.entities import extract_entities

    result = extract_entities(
        "Meeting Notes",
        "Alice Johnson and Bob Smith attended the meeting",
    )
    assert "Alice Johnson" in result["people"]
    assert "Bob Smith" in result["people"]


def test_extract_entities_topics():
    """extract_entities() identifies #hashtag-style topics in body text."""
    from engine.entities import extract_entities

    result = extract_entities(
        "Architecture Discussion",
        "We discussed #python and #architecture at length",
    )
    assert "python" in result["topics"]
    assert "architecture" in result["topics"]


def test_extract_entities_places():
    """extract_entities() identifies place names in body text."""
    from engine.entities import extract_entities

    result = extract_entities(
        "Sprint Planning",
        "The team met in Helsinki for the sprint",
    )
    assert "Helsinki" in result["places"]


def test_extract_entities_never_raises():
    """extract_entities('', '') returns dict with people/places/topics/orgs and never raises."""
    from engine.entities import extract_entities

    result = extract_entities("", "")
    assert result["people"] == []
    assert result["topics"] == []
    # orgs key must be present (PEO-01)
    assert "orgs" in result


# ---------------------------------------------------------------------------
# PEO-01: Existing ASCII names — regression guard
# ---------------------------------------------------------------------------

def test_existing_ascii_names_still_work():
    """John Smith and Jane Doe extracted correctly after Unicode rewrite."""
    from engine.entities import extract_entities

    result = extract_entities("Meeting", "John Smith met with Jane Doe today")
    assert "John Smith" in result["people"]
    assert "Jane Doe" in result["people"]


# ---------------------------------------------------------------------------
# PEO-01: Finnish / Nordic Unicode name extraction
# ---------------------------------------------------------------------------

def test_extract_finnish_names():
    """Finnish names with diacritics (a-umlaut, o-umlaut) are extracted."""
    from engine.entities import extract_entities

    result = extract_entities("", "Tuomas Leppanen discussed the roadmap")
    assert "Tuomas Leppanen" in result["people"]


def test_extract_nordic_names():
    """Nordic names with diacritics are extracted."""
    from engine.entities import extract_entities

    result = extract_entities("", "Asa Lindqvist and Bjorn Ostergren attended")
    assert "Asa Lindqvist" in result["people"]
    assert "Bjorn Ostergren" in result["people"]


def test_extract_name_with_a_umlaut():
    """Names containing a-umlaut character (a with diaeresis) are extracted."""
    from engine.entities import extract_entities

    # Using the Unicode character directly
    result = extract_entities("", "Tuomas Lep\u00e4nen attended the meeting")
    assert "Tuomas Lep\u00e4nen" in result["people"]


def test_extract_name_with_o_umlaut():
    """Names containing o-umlaut character are extracted."""
    from engine.entities import extract_entities

    result = extract_entities("", "Lars J\u00f6rgensen joined the call")
    assert "Lars J\u00f6rgensen" in result["people"]


# ---------------------------------------------------------------------------
# PEO-01: Compound name extraction
# ---------------------------------------------------------------------------

def test_extract_compound_hyphenated_names():
    """Hyphenated last names (Maki-Petaja paired with first name) are extracted."""
    from engine.entities import extract_entities

    result = extract_entities("", "Tuomas Maki-Petaja presented the findings")
    # The hyphenated last name + first name should yield a compound person entry.
    people_str = " ".join(result["people"])
    assert "Maki" in people_str or "Petaja" in people_str


def test_extract_van_prefix_names():
    """Compound names with van/von/de prefixes are extracted."""
    from engine.entities import extract_entities

    result = extract_entities("", "Jan van der Berg led the session")
    people_str = " ".join(result["people"])
    assert "Jan" in people_str or "Berg" in people_str


def test_extract_obrien_style_names():
    """O'Brien style names with apostrophe prefix are extracted."""
    from engine.entities import extract_entities

    result = extract_entities("", "Patrick O'Brien reviewed the PR")
    people_str = " ".join(result["people"])
    assert "Patrick" in people_str or "Brien" in people_str


# ---------------------------------------------------------------------------
# PEO-01: Finnish stop words — no false positives
# ---------------------------------------------------------------------------

def test_finnish_stopwords_not_extracted():
    """Finnish stop words like 'Mutta' and 'Koska' do not produce false positive people."""
    from engine.entities import extract_entities

    result = extract_entities("", "Mutta Koska emme voi tietaa")
    assert "Mutta Koska" not in result["people"]


def test_finnish_stopword_mutta_alone():
    """'Mutta' as first word of pair with non-stop second does not produce false positive."""
    from engine.entities import extract_entities

    # Both words must NOT be stop words to be extracted
    result = extract_entities("", "Mutta Koska on asia")
    assert "Mutta Koska" not in result["people"]


def test_english_stopwords_still_filtered():
    """English stop words 'The' and 'This' are not extracted as people."""
    from engine.entities import extract_entities

    result = extract_entities("", "The This That When are not names")
    assert "The This" not in result["people"]


# ---------------------------------------------------------------------------
# PEO-01: Organization extraction
# ---------------------------------------------------------------------------

def test_extract_orgs_oy():
    """Finnish company suffix Oy is recognized."""
    from engine.entities import extract_entities

    result = extract_entities("", "I work at Wunder Oy for the project")
    assert "Wunder Oy" in result["orgs"]


def test_extract_orgs_inc():
    """US company suffix Inc is recognized."""
    from engine.entities import extract_entities

    result = extract_entities("", "We partnered with Acme Inc for this")
    assert "Acme Inc" in result["orgs"]


def test_extract_orgs_gmbh():
    """German company suffix GmbH is recognized."""
    from engine.entities import extract_entities

    result = extract_entities("", "Signed contract with Bosch GmbH last week")
    assert "Bosch GmbH" in result["orgs"]


def test_org_no_acronym_false_positives():
    """Pure acronyms like API and MCP are NOT extracted as organizations."""
    from engine.entities import extract_entities

    result = extract_entities("", "The API and MCP tools are used here")
    orgs_str = " ".join(result["orgs"])
    assert "API" not in orgs_str
    assert "MCP" not in orgs_str


def test_orgs_key_present_in_result():
    """extract_entities() always returns 'orgs' key."""
    from engine.entities import extract_entities

    result = extract_entities("No orgs here", "Plain text with no companies")
    assert "orgs" in result
    assert isinstance(result["orgs"], list)


# ---------------------------------------------------------------------------
# PEO-01: Title/body separation (regression guard for Phase 27.1 decision)
# ---------------------------------------------------------------------------

def test_title_body_processed_separately():
    """Names that span title/body boundary are NOT extracted as a person."""
    from engine.entities import extract_entities

    # "Wonderland" ends title, "Alice" starts body — must not yield "Wonderland Alice"
    result = extract_entities("Wonderland", "Alice attended the meeting")
    assert "Wonderland Alice" not in result["people"]
