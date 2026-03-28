"""Entity extraction from note text using regex heuristics. Zero AI calls, zero external deps."""
import re

# ---------------------------------------------------------------------------
# Person-context signals — document must contain at least one of these before
# any name extraction is attempted.  This gates the whole sliding-window
# bigram extraction: product/tech notes never have these signals; meeting
# notes, bios, and contact notes always do.
# ---------------------------------------------------------------------------
_PERSON_CONTEXT_SIGNALS = re.compile(
    r'(?:'
    # Honorifics
    r'\b(?:mr|ms|mrs|dr|prof)\b'
    r'|'
    # Job titles / roles
    r'\b(?:ceo|cto|coo|cpo|cfo|vp|svp|evp|gm|'
    r'director|manager|engineer|developer|designer|'
    r'founder|partner|consultant|analyst|specialist|advisor|'
    r'coordinator|lead|head|chief|principal|officer|'
    r'recruiter|researcher|architect|scientist|intern|'
    r'stakeholder|stakeholders|colleague|coworker|'
    r'attendee|attendees|participant|participants|'
    r'contact|contacts|assignee|reviewer|owner)\b'
    r'|'
    # Contact / profile keywords
    r'\b(?:email|phone|linkedin|role|title|works\s+at|joined)\b'
    r'|'
    # Person-action verbs (past or present tense)
    r'\b(?:said|asked|told|mentioned|wrote|sent|emailed|called|'
    r'messaged|texted|pinged|presented|joined|hired|invited|'
    r'attended|assigned|delegated|escalated|approved|confirmed|'
    r'responded|replied|reviewed|facilitated|chaired|hosted|'
    r'organized|spoke|talked|discussed|met|reached|'
    r'led|leads|lead|ran|runs|owns|owned|manages|managed|'
    r'works|worked|reported|introduced|recommended|suggested)\b'
    r'|'
    # @mentions
    r'@\w+'
    r')',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# English stop words — tokens that look like proper nouns but aren't names
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset([
    "The", "This", "When", "With", "From", "That", "Then", "These",
    "Those", "Their", "There", "Here", "Just", "Also", "Some", "More",
    "Such", "Each", "Very", "Both", "Into", "Over", "Under", "After",
    "Before", "During", "While", "Since", "Until", "About", "Above",
    "Below", "Between", "Through", "Within",
    # Common heading-prefix words that look like first names
    "Key", "Core", "Main", "Next", "Last", "New", "Old", "Good", "Bad",
    "Top", "Best", "Big", "High", "Low", "Raw", "Net", "Hot", "Cold",
    # Tech/AI terms that appear title-cased in notes
    "Agent", "Model", "Tool", "Data", "Code", "Test", "Task", "User",
    "Note", "Item", "Type", "Mode", "Node", "Step", "Phase", "Stage",
    # Common verbs/nouns that appear in Title Case headings but are never names
    "Build", "Workflow", "Health", "Template", "Update", "Setup",
    "Launch", "Deploy", "Release", "Status", "Report", "Summary",
    "Overview", "Result", "Output", "Input", "Files", "Maintenance",
    "Review", "Design", "Feature", "Issue", "Request", "Response",
    "Service", "Process", "Config", "Session", "Change", "Version",
    # Meeting/calendar terms that appear in Title Case
    "Sync", "Call", "Chat", "Weekly", "Daily", "Monthly", "Quarterly",
    "Sprint", "Retro", "Demo", "Standup", "Kickoff",
    # Product / app / tech terms that appear in Title Case but are never human names
    "App", "Apps", "Timer", "Timers", "Watch", "Watches",
    "Shortcut", "Shortcuts", "Plugin", "Plugins",
    "Bot", "Bots", "Extension", "Extensions",
    "Platform", "Dashboard", "Widget", "Widgets",
    "Hub", "Kit", "Bar", "Card", "Board", "Grid", "Flow",
    "Library", "Framework", "Module", "Component",
    "Integration", "Integrations",
    "Manager", "Tracker", "Monitor", "Analyzer",
    "Builder", "Runner", "Handler", "Generator",
    "Assistant", "Project", "Projects", "Idea", "Ideas",
    "Alert", "Alerts", "Notification", "Notifications", "Preview",
    # Adjective forms common in product names
    "Controlled", "Powered", "Based", "Driven", "Enabled",
    "Voice", "Quick", "Smart", "Easy", "Fast",
    "Pro", "Plus", "Mini", "Lite", "Air",
])

# ---------------------------------------------------------------------------
# Finnish stop words — common Finnish words that appear Title Case mid-sentence
# ---------------------------------------------------------------------------
_FINNISH_STOPS = frozenset([
    "Olen", "Olet", "Meill\u00e4", "Teil\u00e4", "Heill\u00e4", "Minulla", "Sinulla",
    "T\u00e4m\u00e4", "T\u00e4ss\u00e4", "Siell\u00e4", "T\u00e4\u00e4ll\u00e4", "Miss\u00e4",
    "Kun", "Jos", "Ett\u00e4", "Mutta", "Koska", "Vaikka", "Jotta", "Sek\u00e4", "My\u00f6s",
])

_ALL_STOPS = _STOP_WORDS | _FINNISH_STOPS

# ---------------------------------------------------------------------------
# Unicode-aware character classes for Extended Latin
# Covers: Basic Latin + Latin-1 Supplement + Latin Extended-A/B
# Handles Finnish (ä, ö), Nordic (å, ø, æ), French (é, è, ê), German (ü), etc.
# ---------------------------------------------------------------------------
_UC = (
    r'[A-Z'
    r'\u00c0-\u00d6'   # À-Ö (Latin-1 uppercase, excl. × at D7)
    r'\u00d8-\u00de'   # Ø-Þ
    r'\u0100-\u0136'   # Ā-Ķ (Latin Extended-A uppercase)
    r'\u0139-\u0148'   # Ĺ-Ň
    r'\u014c-\u0178'   # Ō-Ÿ
    r'\u0179-\u017e'   # Ź-ž (some are uppercase: Ź Ż Ž)
    r']'
)

_LC = (
    r'[a-z'
    r'\u00e0-\u00f6'   # à-ö (Latin-1 lowercase, excl. ÷ at F7)
    r'\u00f8-\u00ff'   # ø-ÿ
    r'\u0101-\u0137'   # ā-ķ (Latin Extended-A lowercase)
    r'\u013a-\u0149'   # ĺ-ŉ
    r'\u014d-\u017c'   # ō-ż
    r']'
)

# One "word" segment: uppercase letter followed by one or more lowercase letters
_WORD = rf'{_UC}{_LC}+'

# An apostrophe-name: Uppercase + apostrophe/right-quote + WORD (O'Brien, O'Neill)
_APOSTROPHE_NAME = rf"{_UC}['\u2019]{_WORD}"

# A name segment: a WORD optionally followed by hyphen+WORD (Maki-Petaja)
# Also matches apostrophe-style names (O'Brien) in either first or last position
_NAME_SEG = rf'(?:{_APOSTROPHE_NAME}|{_WORD}(?:-{_WORD})*)'

# First name: same as name segment
_FIRST = _NAME_SEG

# Optional compound last-name prefix: van, von, de, di, la, el
# Also handles two-word prefixes: van der, van den, van de, de la, etc.
_PREFIX = r'(?:(?:van|von|de|di|la|el)(?:\s+(?:der?|den|la|el|le|les|los|las))?\s+)?'

# Full two-word name pattern: FirstName [optional prefix] LastName[-Suffix]
_NAME_PAT = re.compile(
    rf'\b({_FIRST})\s+{_PREFIX}({_NAME_SEG})\b'
)

# ---------------------------------------------------------------------------
# Organization extraction — suffix-based only (no pure acronyms)
# ---------------------------------------------------------------------------
_ORG_SUFFIXES = (
    r'Ltd', r'Oy', r'GmbH', r'Inc', r'Corp', r'AB', r'AS', r'SA',
    r'LLC', r'plc', r'Group', r'Agency', r'Studio', r'Partners',
    r'Solutions', r'Services', r'Technologies',
)
# Org pattern: one or more consecutive Title Case words, ending with a known suffix.
# Using [A-Z][A-Za-z]* to match each Title Case word (no lowercase connecting words).
# This prevents "I work at Wunder Oy" from matching as "I work at Wunder Oy".
_ORG_SUFFIX_PAT = re.compile(
    rf'\b([A-Z][A-Za-z\u00c0-\u017e]*(?:\s+[A-Z][A-Za-z\u00c0-\u017e]*)*\s+(?:{"|".join(_ORG_SUFFIXES)}))\b'
)


def extract_entities(title: str, body: str) -> dict:
    """Best-effort entity extraction. Never raises.

    Returns:
        {"people": [...], "places": [...], "topics": [...], "orgs": [...]}
        All lists are deduplicated and sorted.
    """
    try:
        # Process title and body separately to avoid cross-boundary bigrams
        # (e.g. "... Wonderland" title + "Alice ..." body must not yield "Wonderland Alice")
        title_text = title or ""
        body_text = body or ""
        # Person-context signals are checked against the combined text so that
        # a name in the title ("Alice Johnson") is still extracted when signals
        # are only in the body ("Role: CTO...").
        combined_text = f"{title_text}\n{body_text}"
        people = list(set(_extract_people(title_text, combined_text)) | set(_extract_people(body_text, combined_text)))
        topics = list(set(_extract_topics(title_text)) | set(_extract_topics(body_text)))
        places = list(set(_extract_places(title_text, people)) | set(_extract_places(body_text, people)))
        orgs = list(set(_extract_organizations(title_text)) | set(_extract_organizations(body_text)))
        return {
            "people": sorted(set(people)),
            "places": sorted(set(places)),
            "topics": sorted(set(topics)),
            "orgs": sorted(set(orgs)),
        }
    except Exception:
        return {"people": [], "places": [], "topics": [], "orgs": []}



# Suffixes that indicate abstract nouns or gerunds — not valid last names.
# Gerunds: -ing, -ings. Abstract nouns: -tion, -sion, -ness, -ment, -ity, -ery, -ory, -ary.
# Past participles: -ated. Analysis-style: -sis.
_ABSTRACT_SUFFIXES = (
    "ing", "ings",
    "tion", "sion",
    "ness", "ment",
    "ity", "ery", "ory", "ary",
    "ism",
    "ated", "sis",
)


def _is_abstract_noun(word: str) -> bool:
    """Return True if word looks like an abstract noun rather than a name.

    Also checks the de-pluralised form (strip trailing 's') so that plural
    abstract nouns like 'Presentations' are caught alongside 'Presentation'.
    """
    lower = word.lower()
    if any(lower.endswith(s) for s in _ABSTRACT_SUFFIXES):
        return True
    # Plural form: strip trailing 's' (but not "ss" endings like "lass")
    if lower.endswith("s") and not lower.endswith("ss") and len(lower) > 3:
        singular = lower[:-1]
        if any(singular.endswith(s) for s in _ABSTRACT_SUFFIXES):
            return True
    return False


# Pattern for a single name-like token (same character class as _NAME_SEG)
_TOKEN_PAT = re.compile(rf'\b{_NAME_SEG}\b')
# Allowed gap between first and last name: whitespace + optional compound prefix
_GAP_PAT = re.compile(rf'^\s+{_PREFIX}$')


def _extract_people(text: str, signal_text: str | None = None) -> list[str]:
    """Extract two-word names using a sliding window over capitalized tokens.

    Requires at least one person-context signal (role title, action verb,
    @mention, contact keyword) in `signal_text` (defaults to `text`) before
    attempting extraction.  This prevents product/tech names from being
    classified as people — product descriptions never contain these signals.

    `signal_text` should be the full title+body combined so that a name in
    the title is still detected when signals are only in the body, while name
    extraction itself still runs on `text` to avoid cross-boundary bigrams.

    Uses a sliding window instead of non-overlapping findall so that
    consecutive names like "Met Anna Korhonen" yield both ("Met","Anna")
    and ("Anna","Korhonen") — the latter being the real name.

    Filters out English and Finnish stop words and abstract noun suffixes
    (gerunds, -tion, -ness, etc.) that commonly appear in title-cased headings.
    Supports compound prefixes (van, von, de, di, la, el) and hyphenated last names.
    """
    # Document-level gate: skip name extraction entirely if there are no
    # person-context signals.  This is the primary defence against false
    # positives from product names, tech terms, and heading bigrams.
    check_text = signal_text if signal_text is not None else text
    if not _PERSON_CONTEXT_SIGNALS.search(check_text):
        return []

    tokens = [(m.group(), m.start(), m.end()) for m in _TOKEN_PAT.finditer(text)]
    results = []
    for i in range(len(tokens) - 1):
        first, f_start, f_end = tokens[i]
        last, l_start, _ = tokens[i + 1]
        gap = text[f_end:l_start]
        if not _GAP_PAT.match(gap):
            continue
        # Hyphenated tokens (e.g. "Voice-Controlled") — check each part against stops
        first_parts = first.split("-")
        last_parts = last.split("-")
        if (not any(p in _ALL_STOPS for p in first_parts)
                and not any(p in _ALL_STOPS for p in last_parts)
                and not _is_abstract_noun(first)
                and not _is_abstract_noun(last)):
            results.append(f"{first} {last}")
    return list(dict.fromkeys(results))


def _extract_organizations(text: str) -> list[str]:
    """Extract organization names using known suffix patterns.

    Only matches organizations with recognized legal suffixes (Ltd, Oy, GmbH, etc.)
    to avoid false positives from acronyms (API, MCP, IT, etc.).
    """
    matches = _ORG_SUFFIX_PAT.findall(text)
    return [m.strip() for m in matches if m.strip()]


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
