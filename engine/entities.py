"""Entity extraction from note text.

People extraction uses a three-layer strategy (in priority order):
1. LLM (Ollama) — local llama3.2; multilingual, high accuracy; used when available.
2. Bracket parser — [Name] / [Name, Name] notation; always runs; zero false positives.
3. spaCy NER    — en_core_web_sm; fallback when LLM unavailable.
4. Regex bigram — sliding-window fallback when neither LLM nor spaCy is installed.
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

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
    r'|'
    # Chat/Slack transcript timestamps — [10:20 AM], [3:46 PM], [14:30]
    # Presence means this is a conversation where names appear as speakers
    r'\[\d{1,2}:\d{2}(?:\s*[AP]M)?\]'
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
    # Imperative action verbs that appear Title-Cased as action-item labels
    "Ask", "Assign", "Check", "Clarify", "Close", "Confirm", "Contact",
    "Create", "Discuss", "Fix", "Inform", "Investigate", "Merge",
    "Move", "Open", "Perform", "Prepare", "Provide", "Push", "Send",
    "Share", "Upgrade",
    # Tech / domain compound-noun components that look like name tokens
    "Client", "Domain", "Drupal", "Elastic", "Search", "Solar",
    "Strategy", "Ticket",
    # Meeting/calendar terms that appear in Title Case
    "Sync", "Call", "Chat", "Weekly", "Daily", "Monthly", "Quarterly",
    "Sprint", "Retro", "Demo", "Standup", "Kickoff",
    # Slack/chat UI terms that appear Title Case
    "Private", "Canvas", "Huddle", "Channel", "Thread", "Direct",
    # Geographic/institutional qualifiers — never a person name
    "European", "Federal", "National", "International", "Global", "Regional", "Local",
    # Institution type nouns — can follow a name-like word (e.g. "European Institute")
    "Institute", "Foundation", "Commission", "Authority", "Bureau",
    "Council", "Committee", "Association", "Federation", "Union", "Office",
    # Legal/policy document terms — appear Title Case throughout policy docs
    "Directive", "Regulation", "Compliance", "Mandate", "Policy", "Legislation",
    "Act", "Law", "Code", "Standard", "Requirement", "Obligation",
    # HR/equality domain terms that appear as Title Case bigram components
    "Equal", "Equality", "Equity", "Gender", "Diversity", "Inclusion",
    "Pay", "Salary", "Wage", "Compensation", "Transparency", "Reporting",
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
    # Business / role terms that appear in email signatures
    "Sales", "Account", "Marketing", "Finance", "Operations", "Human",
    "Resources", "Representative", "Executive", "President", "Vice",
    "Senior", "Junior", "Intern",
    # E-invoicing / business document terms
    "Electronic", "Business", "Operator", "Invoice", "Invoices",
    # Hardware / OS / platform terms — never a person name
    "Apple", "Silicon", "Intel", "Binary", "Homebrew", "Standalone",
    "Mac", "Linux", "Windows", "Android", "Docker", "Kubernetes",
    "Native", "Virtual", "Remote", "Cloud", "Server", "Cluster",
    "Multiple", "General", "Pattern", "Default", "Custom", "Manual",
    # Adjective forms common in product names
    "Controlled", "Powered", "Based", "Driven", "Enabled",
    "Voice", "Quick", "Smart", "Easy", "Fast",
    "Pro", "Plus", "Mini", "Lite", "Air",
])

# ---------------------------------------------------------------------------
# Finnish stop words — common Finnish words that appear Title Case mid-sentence
# ---------------------------------------------------------------------------
_FINNISH_STOPS = frozenset([
    "Olen", "Olet", "Meillä", "Teilä", "Heillä", "Minulla", "Sinulla",
    "Tämä", "Tässä", "Siellä", "Täällä", "Missä",
    "Kun", "Jos", "Että", "Mutta", "Koska", "Vaikka", "Jotta", "Sekä", "Myös",
    # Colloquial Finnish sentence starters (appear Title-Cased mid-text)
    "Mut", "Nii", "Joo", "Juu", "Okei", "Kyl", "Ei", "On", "Ois", "Oon",
    # Finnish greetings — appear as "Hei Firstname" / "Moi Firstname" in emails
    "Hei", "Moi", "Terve", "Hyvä", "Hyvää", "Huomenta", "Iltaa", "Päivää",
    "Kiitos", "Kiitokset", "Kiitoksena",
    # Finnish sentence starters common in emails
    "Kuten", "Tässä", "Mikäli", "Alkaen", "Jatkossa", "Kuitenkin",
    "Minkälaisia", "Voit", "Sopimuksen", "Kaupungin", "Nimenkirjoittajana",
    "Ystävällisin", "Terveisin", "Parhain",
    # Finnish pronouns and conjunctions that appear Title-Cased at sentence start
    "Meidän", "Teidän", "Heidän", "Minun", "Sinun",
    "Asia", "Lasku", "Virhe", "Tietoja",
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
# Bracket-format people extraction
# Handles: [Alice Johnson] and [Alice Johnson, Bob Smith] action-item notation.
# This is a high-precision path: names inside brackets are structurally unambiguous.
# ---------------------------------------------------------------------------
_BRACKET_PAT = re.compile(r'\[([^\]\n]+)\]')


def _extract_bracket_people(text: str) -> list[str]:
    """Extract names from [Name] and [Name, Name] bracket notation."""
    results = []
    for m in _BRACKET_PAT.finditer(text):
        content = m.group(1).strip()
        for candidate in re.split(r',\s*', content):
            candidate = ' '.join(candidate.split())  # normalise whitespace
            nm = _NAME_PAT.search(candidate)
            if nm and nm.group(0) == candidate:
                results.append(candidate)
    return list(dict.fromkeys(results))


# ---------------------------------------------------------------------------
# spaCy NER — lazy-loaded singleton; replaces the regex bigram scanner when
# en_core_web_sm is available.  Falls back gracefully to regex if not.
# ---------------------------------------------------------------------------
_nlp = None
_spacy_attempted = False


def _get_nlp():
    global _nlp, _spacy_attempted
    if _spacy_attempted:
        return _nlp
    _spacy_attempted = True
    try:
        import spacy  # noqa: PLC0415
        _nlp = spacy.load(
            "en_core_web_sm",
            disable=["tagger", "parser", "senter", "attribute_ruler", "lemmatizer"],
        )
    except (ImportError, OSError):
        _nlp = None
    return _nlp


def _extract_people_spacy(text: str) -> list[str]:
    """Extract PERSON entities via spaCy NER.  Returns [] if model unavailable.

    Applies multiple filters after NER to catch cases where the English-only
    model incorrectly classifies non-English text (e.g. Finnish phrases) as
    person names:
    - Stop-word + abstract-noun filtering
    - Title Case requirement: every word must start with uppercase
    - Max 3 words (real names are 2-3 words; longer spans are phrases)
    - Org suffix filtering: reject names ending with Oy, Ltd, etc.
    """
    nlp = _get_nlp()
    if nlp is None:
        return []
    doc = nlp(text)
    results = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            if " " not in name:
                continue  # single tokens too ambiguous
            words = name.split()
            if len(words) > 3:
                continue  # real names are 2-3 words; longer = phrase
            if not all(w[0].isupper() for w in words):
                continue  # reject lowercase words (Finnish phrases, etc.)
            if any(_is_stop(w) or _is_abstract_noun(w) for w in words):
                continue
            # Reject org-like names (ending with known suffixes)
            if words[-1] in _ORG_SUFFIX_SET:
                continue
            results.append(name)
    return list(dict.fromkeys(results))


# ---------------------------------------------------------------------------
# LLM-based people extraction — Ollama local model (multilingual, high accuracy)
# ---------------------------------------------------------------------------
_LLM_PEOPLE_PROMPT = (
    "You extract person names from text. "
    "Return a JSON array of full human names (first + last). "
    "Include anyone mentioned by name. Exclude company names and job titles. "
    "Return [] if none found. JSON array only, no explanation."
)

_ollama_available: bool | None = None  # None = not checked yet
_ollama_fail_time: float = 0  # monotonic timestamp of last failure
_OLLAMA_RETRY_SECS = 60  # retry after this many seconds


def _extract_people_llm(text: str) -> list[str] | None:
    """Extract person names via local Ollama LLM. Returns None if unavailable.

    Uses llama3.2 (3B) for fast multilingual extraction. Falls back to None
    on any error so callers can use regex/spaCy instead.
    """
    global _ollama_available, _ollama_fail_time
    if _ollama_available is False:
        import time  # noqa: PLC0415
        if (time.monotonic() - _ollama_fail_time) < _OLLAMA_RETRY_SECS:
            return None
        _ollama_available = None  # retry

    try:
        import ollama as _ollama_mod  # noqa: PLC0415
        from engine.config_loader import load_config  # noqa: PLC0415
        from engine.paths import CONFIG_PATH  # noqa: PLC0415

        cfg = load_config(CONFIG_PATH)
        host = cfg.get("ollama", {}).get("host", "http://localhost:11434")

        # Truncate to ~2000 chars to keep LLM calls fast
        truncated = text[:2000] if len(text) > 2000 else text

        import httpx  # noqa: PLC0415
        client = _ollama_mod.Client(host=host, timeout=httpx.Timeout(15.0))
        response = client.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": _LLM_PEOPLE_PROMPT},
                {"role": "user", "content": truncated},
            ],
        )
        raw = response.message.content.strip()
        # Parse JSON array from response — handle markdown fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        names = json.loads(raw)
        if not isinstance(names, list):
            return None
        # Basic validation: only keep strings that look like names (2-3 words, Title Case)
        valid = []
        for n in names:
            if not isinstance(n, str):
                continue
            n = n.strip()
            words = n.split()
            if len(words) < 2 or len(words) > 4:
                continue
            if not all(w[0].isupper() for w in words):
                continue
            valid.append(n)
        _ollama_available = True
        return list(dict.fromkeys(valid))
    except Exception as exc:
        import time  # noqa: PLC0415
        logger.debug("LLM people extraction failed: %s", exc)
        _ollama_available = False
        _ollama_fail_time = time.monotonic()
        return None


# ---------------------------------------------------------------------------
# Organization extraction — suffix-based only (no pure acronyms)
# ---------------------------------------------------------------------------
_ORG_SUFFIXES = (
    r'Ltd', r'Oy', r'GmbH', r'Inc', r'Corp', r'AB', r'AS', r'SA',
    r'LLC', r'plc', r'Group', r'Agency', r'Studio', r'Partners',
    r'Solutions', r'Services', r'Technologies',
)
_ORG_SUFFIX_SET = frozenset(s.replace('\\', '') for s in _ORG_SUFFIXES)
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
        title_text = title or ""
        body_text = body or ""
        combined_text = f"{title_text}\n{body_text}"

        # Try LLM once on combined text (avoids double Ollama call)
        llm_people = _extract_people_llm(combined_text)
        if llm_people is not None:
            # LLM succeeded — use its results + bracket names
            bracket = list(
                set(_extract_bracket_people(title_text))
                | set(_extract_bracket_people(body_text))
            )
            people = list(dict.fromkeys(bracket + llm_people))
        else:
            # Fallback: spaCy/regex per-section (avoids cross-boundary bigrams)
            people = list(
                set(_extract_people(title_text, combined_text))
                | set(_extract_people(body_text, combined_text))
            )

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
# Allowed gap between first and last name: horizontal whitespace only (no newlines) + optional compound prefix
# Newlines are excluded deliberately — "Name\nVerb" should never form a bigram.
_GAP_PAT = re.compile(rf'^[^\S\n]+{_PREFIX}$')


def _is_stop(word: str) -> bool:
    """Return True if word is a stop word, also checking de-pluralised form."""
    if word in _ALL_STOPS:
        return True
    # "Agents" → check "Agent"; "Tickets" → check "Ticket"
    if word.endswith("s") and len(word) > 3 and word[:-1] in _ALL_STOPS:
        return True
    return False


def _extract_people_regex(text: str, signal_text: str | None = None) -> list[str]:
    """Regex bigram fallback — used only when spaCy is unavailable.

    Sliding window over consecutive Title-Case token pairs.  Requires a
    person-context signal in the document to run (defence against false
    positives in pure-product/tech notes).
    """
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
        first_parts = first.split("-")
        last_parts = last.split("-")
        if (not any(_is_stop(p) for p in first_parts)
                and not any(_is_stop(p) for p in last_parts)
                and not _is_abstract_noun(first)
                and not _is_abstract_noun(last)
                and last not in _ORG_SUFFIX_SET):
            results.append(f"{first} {last}")
    return list(dict.fromkeys(results))


def _extract_people(text: str, signal_text: str | None = None) -> list[str]:
    """Extract person names from text.

    Priority order:
    1. Bracket parser — [Name] / [Name, Name]; always runs; zero false positives.
    2. LLM (Ollama)  — local llama3.2; multilingual, highest accuracy.
    3. spaCy NER     — fallback when LLM unavailable.
    4. Regex bigram  — fallback when neither LLM nor spaCy is available.
    """
    bracket = _extract_bracket_people(text)

    # Try LLM first — best quality, handles all languages
    llm_result = _extract_people_llm(text)
    if llm_result is not None:
        return list(dict.fromkeys(bracket + llm_result))

    # Fallback: spaCy + regex
    regex = _extract_people_regex(text, signal_text)
    if _get_nlp() is not None:
        spacy = _extract_people_spacy(text)
        body = list(dict.fromkeys(spacy + regex))
    else:
        body = regex

    return list(dict.fromkeys(bracket + body))


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
    pattern = r'\b(?:in|at|from|to)[^\S\n]+([A-Z][a-z]+(?:[^\S\n]+[A-Z][a-z]+)*)\b'
    matches = re.findall(pattern, text)
    return [
        m for m in matches
        if m not in _STOP_WORDS and m not in people_tokens
    ]
