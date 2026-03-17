"""Wave 0 test stubs for engine/entities.py extract_entities().

All tests are xfail (strict=False) until Wave 2 implements engine/entities.py.
They will auto-promote to PASS once the module ships.
"""
import pytest


@pytest.mark.xfail(strict=False, reason="Wave 2: engine/entities.py not yet implemented")
def test_extract_entities_people():
    """extract_entities() identifies named people in body text."""
    from engine.entities import extract_entities

    result = extract_entities(
        "Meeting Notes",
        "Alice Johnson and Bob Smith attended the meeting",
    )
    assert "Alice Johnson" in result["people"]
    assert "Bob Smith" in result["people"]


@pytest.mark.xfail(strict=False, reason="Wave 2: engine/entities.py not yet implemented")
def test_extract_entities_topics():
    """extract_entities() identifies #hashtag-style topics in body text."""
    from engine.entities import extract_entities

    result = extract_entities(
        "Architecture Discussion",
        "We discussed #python and #architecture at length",
    )
    assert "python" in result["topics"]
    assert "architecture" in result["topics"]


@pytest.mark.xfail(strict=False, reason="Wave 2: engine/entities.py not yet implemented")
def test_extract_entities_places():
    """extract_entities() identifies place names in body text."""
    from engine.entities import extract_entities

    result = extract_entities(
        "Sprint Planning",
        "The team met in Helsinki for the sprint",
    )
    assert "Helsinki" in result["places"]


@pytest.mark.xfail(strict=False, reason="Wave 2: engine/entities.py not yet implemented")
def test_extract_entities_never_raises():
    """extract_entities('', '') returns empty lists and never raises."""
    from engine.entities import extract_entities

    result = extract_entities("", "")
    assert result == {"people": [], "places": [], "topics": []}
