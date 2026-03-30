"""Pass 1: extract all entities unconditionally from content."""
from engine.entities import extract_entities


def extract_all_entities(content: str) -> dict:
    """Extract people, topics, places, orgs from content.

    Title is not yet derived at Pass 1 time, so an empty string is passed.
    Returns the entities dict produced by extract_entities().
    """
    return extract_entities("", content)
