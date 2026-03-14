"""PII classifier — local-only, no network calls (AI-02).

Frontmatter ``content_sensitivity`` field takes priority over keyword scan.
Never passes content to any model.
"""
import re

SENSITIVITY_VALUES: frozenset = frozenset({"pii", "private", "public"})

PII_KEYWORDS: list[str] = [
    r"\b\d{3}-\d{2}-\d{4}\b",   # SSN pattern
    r"\b\d{16}\b",               # 16-digit credit card
    r"\bpassword\b",
    r"\bpasswd\b",
    r"\bsalary\b",
    r"\bcompensation\b",
    r"\bhealth\b",
    r"\bmedical\b",
    r"\bdiagnosis\b",
    r"\bpersonal address\b",
]

_PII_RE = re.compile("|".join(PII_KEYWORDS), re.IGNORECASE)


def classify(content_sensitivity: str, body: str) -> str:
    """Return sensitivity level: one of 'pii', 'private', 'public'.

    Frontmatter explicit declaration wins over keyword scan.
    Never makes network calls.

    Args:
        content_sensitivity: Value from note frontmatter ``content_sensitivity`` field.
        body: Full note body text for keyword scanning.
    """
    # Frontmatter explicit declaration wins
    if content_sensitivity in SENSITIVITY_VALUES:
        return content_sensitivity
    # Keyword scan fallback
    if _PII_RE.search(body):
        return "pii"
    return "public"
