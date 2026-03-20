"""Entity-based PII classifier for smart capture.

Uses regex pattern matching only — no keyword scanning, no AI calls.
Never-downgrade rule: detected level always wins over user-supplied level.
"""
import re

# ---------------------------------------------------------------------------
# PII patterns — ordered by specificity
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # US Social Security Number: 123-45-6789
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "SSN"),
    # Finnish hetu (henkilötunnus): 010101-123A or 010101+123A or 010101A123A
    (re.compile(r'\b\d{6}[+\-A]\d{3}[A-Z0-9]\b'), "Finnish hetu"),
    # Credit card — Visa (16 digits starting with 4) or MC (16 digits starting with 51-55)
    (re.compile(r'\b4\d{15}\b|\b5[1-5]\d{14}\b'), "credit card"),
    # Email address
    (re.compile(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b', re.IGNORECASE), "email"),
    # Phone: flexible international/national format, 10-15 chars, at least 7 digits
    (re.compile(r'\+?[\d\s\-()]{10,15}'), "phone number"),
]

# Sensitivity level ordering for never-downgrade rule
_LEVEL_ORDER = {"public": 0, "private": 1, "pii": 2}


def _count_digits(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


def classify_smart(body: str, user_sensitivity: str = "public") -> tuple[str, str | None]:
    """Classify content sensitivity using entity-based PII pattern matching.

    Never downgrades: if detected level > user-supplied level, detected level wins.

    Args:
        body: Note content to scan.
        user_sensitivity: Caller-supplied level ('public' | 'private' | 'pii').

    Returns:
        (level, reason) — reason is None if no PII upgrade, else e.g. "detected: phone number"
    """
    detected_level = user_sensitivity
    detected_reason: str | None = None

    for pattern, label in _PII_PATTERNS:
        for match in pattern.finditer(body):
            text = match.group(0)
            # Phone validation: require at least 7 digits to avoid false positives
            if label == "phone number" and _count_digits(text) < 7:
                continue
            # Upgrade if detected level is higher
            if _LEVEL_ORDER.get("pii", 2) > _LEVEL_ORDER.get(detected_level, 0):
                detected_level = "pii"
                detected_reason = f"detected: {label}"
                break  # No need to scan further once pii is determined
        if detected_level == "pii":
            break

    # Never-downgrade: take the max of user-supplied and detected
    final_level = max(user_sensitivity, detected_level, key=lambda x: _LEVEL_ORDER.get(x, 0))

    # Reason only applies when we upgraded due to pattern detection
    if final_level == "pii" and detected_reason:
        return final_level, detected_reason
    if final_level == user_sensitivity:
        return final_level, None
    return final_level, detected_reason
