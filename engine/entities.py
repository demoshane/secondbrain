"""Entity extraction from note text using regex heuristics. Zero AI calls, zero external deps."""
import re

_STOP_WORDS = frozenset([
    "The", "This", "When", "With", "From", "That", "Then", "These",
    "Those", "Their", "There", "Here", "Just", "Also", "Some", "More",
    "Such", "Each", "Very", "Both", "Into", "Over", "Under", "After",
    "Before", "During", "While", "Since", "Until", "About", "Above",
    "Below", "Between", "Through", "Within",
])


def extract_entities(title: str, body: str) -> dict:
    """Best-effort entity extraction. Never raises.

    Returns:
        {"people": [...], "places": [...], "topics": [...]}
        All lists are deduplicated and sorted.
    """
    try:
        # Process title and body separately to avoid cross-boundary bigrams
        # (e.g. "... Wonderland" title + "Alice ..." body must not yield "Wonderland Alice")
        title_text = title or ""
        body_text = body or ""
        people = list(set(_extract_people(title_text)) | set(_extract_people(body_text)))
        topics = list(set(_extract_topics(title_text)) | set(_extract_topics(body_text)))
        places = list(set(_extract_places(title_text, people)) | set(_extract_places(body_text, people)))
        return {
            "people": sorted(set(people)),
            "places": sorted(set(places)),
            "topics": sorted(set(topics)),
        }
    except Exception:
        return {"people": [], "places": [], "topics": []}


def _extract_people(text: str) -> list[str]:
    # Two consecutive Title Case words not in stop words
    pattern = r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'
    matches = re.findall(pattern, text)
    return [
        f"{first} {last}"
        for first, last in matches
        if first not in _STOP_WORDS and last not in _STOP_WORDS
    ]


def _extract_topics(text: str) -> list[str]:
    # Words starting with # (hashtag style)
    return re.findall(r'#(\w+)', text)


def _extract_places(text: str, people: list[str]) -> list[str]:
    # Capitalized tokens preceded by location prepositions
    people_tokens = set()
    for name in people:
        people_tokens.update(name.split())
    pattern = r'\b(?:in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.findall(pattern, text)
    return [
        m for m in matches
        if m not in _STOP_WORDS and m not in people_tokens
    ]
