"""Pass 3: classify URL-stripped content with conversation-format signal boost."""
import re

from engine.typeclassifier import classify_note_type

# Unicode-aware Name [HH:MM] pattern — covers Finnish/Nordic names (Päivi, Mäkinen).
# Matches start-of-line: one word-char, up to 30 more word/space/hyphen chars, [HH:MM].
_CONVO_TURN_PAT = re.compile(r'^\w[\w\s\-]{1,30}\s*\[\d{1,2}:\d{2}\]', re.MULTILINE)


def _conversation_boost(body: str) -> float:
    """Return 0.85 if >= 2 conversation turns (Name [HH:MM]) are detected, else 0.0."""
    turns = _CONVO_TURN_PAT.findall(body)
    return 0.85 if len(turns) >= 2 else 0.0


def classify_content(title: str, body: str) -> tuple[str, float]:
    """Classify URL-stripped content into a note type with confidence.

    Applies D-11 conversation boost: if >= 2 Name [HH:MM] turns are found,
    the result is overridden to ("meeting", 0.85) unless the classifier
    already returned ("meeting", >= 0.85).
    """
    note_type, confidence = classify_note_type(title, body)
    boost = _conversation_boost(body)
    if boost > 0.0 and (note_type != "meeting" or confidence < boost):
        return ("meeting", boost)
    return (note_type, confidence)
