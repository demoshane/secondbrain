"""Note type classification with confidence scoring.

classify_note_type(title, body) -> (note_type, confidence)

Confidence tiers:
  >= CONFIDENCE_THRESHOLD  auto-assign (no prompt needed)
  0.50 – threshold-1       suggest, ask user to confirm
  < 0.50                   completely unknown, ask user to pick

Rules are keyword-based and order-independent — every type is scored and
the highest-confidence winner is returned.  "note" is the unconditional
fallback at 0.50.
"""
import re

# Callers should import this constant rather than hard-coding 0.75.
CONFIDENCE_THRESHOLD = 0.75

# ---------------------------------------------------------------------------
# Compiled patterns (module-level for performance)
# ---------------------------------------------------------------------------

_URL_PAT = re.compile(r'https?://\S+')

# Words that appear in title-cased product/app names but never in human names.
# Used to rule out false-positive person detection.
_PRODUCT_WORDS = re.compile(
    r'\b(app|apps|timer|timers|watch|watches|shortcut|shortcuts|tool|tools|'
    r'plugin|plugins|api|sdk|bot|bots|extension|extensions|service|services|'
    r'framework|library|platform|dashboard|widget|widgets|system|server|client|'
    r'module|component|integration|integrations|feature|features|'
    r'voice|controlled|powered|based|driven|enabled|'
    r'assistant|agent|agents|manager|tracker|monitor|analyzer|'
    r'generator|builder|runner|handler|'
    r'idea|ideas|project|projects|note|notes|task|tasks|'
    r'request|requests|report|reports|update|updates|'
    r'review|reviews|alert|alerts|preview|notification|notifications|'
    r'hub|kit|pad|bar|card|view|board|list|grid|flow|'
    r'pro|plus|max|mini|lite|air|quick|smart|easy|fast)\b',
    re.IGNORECASE,
)

# Strict person-name pattern: one or more Title-Case segments separated by
# space or hyphen.  Must be the *entire* title — no extra words.
_PERSON_NAME_PAT = re.compile(r'^[A-Z][a-z]+(?:[\- ][A-Z][a-z]+)+$')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_note_type(title: str, body: str) -> tuple[str, float]:
    """Classify a note into a type with a confidence score.

    Args:
        title: Note title or first heading (may be the only input for CLI).
        body:  Note body text.  Pass "" for title-only classification.

    Returns:
        (note_type, confidence) where confidence is in [0.0, 1.0].
        note_type is one of: note, meeting, person, coding, project,
        strategy, idea, personal, link.
    """
    # Combine so keyword searches work on both title and body simultaneously.
    combined = f"{title}\n{body}"
    low = combined.lower()
    title_low = title.lower()

    # link — URL presence is deterministic, always wins
    if _URL_PAT.search(combined):
        return ("link", 1.0)

    scores: dict[str, float] = {}

    # ------------------------------------------------------------------ meeting
    strong_kws = len(re.findall(
        r'\b(meeting|attendees|agenda|standup|stand-up|retro|retrospective|minutes)\b', low
    ))
    weak_kws = len(re.findall(
        r'\b(discussed|sync|action items|follow.?up|decisions)\b', low
    ))
    title_hit = bool(re.search(
        r'\b(meeting|standup|stand-up|sync|retro|1:1|catch.?up|debrief)\b', title_low
    ))
    s = 0.0
    if strong_kws >= 2:
        s = 0.90
    elif strong_kws == 1:
        s = 0.82
    elif weak_kws >= 2:
        s = 0.70
    elif weak_kws == 1:
        s = 0.58
    if title_hit:
        s = min(s + 0.10, 0.95) if s > 0 else 0.85
    scores["meeting"] = s

    # ------------------------------------------------------------------ person
    is_name_title = bool(_PERSON_NAME_PAT.match(title.strip()))
    has_product = bool(_PRODUCT_WORDS.search(title))
    contact_kws = len(re.findall(
        r'\b(role|contact|email|phone|linkedin|title|works at|joined|'
        r'cto|ceo|coo|vp|director|head of|engineer|designer|consultant|'
        r'founder|partner|colleague|coworker)\b', low
    ))
    s = 0.0
    if is_name_title and not has_product:
        s = 0.80
        if contact_kws >= 1:
            s = min(0.80 + 0.05 * contact_kws, 0.95)
    elif contact_kws >= 3 and not has_product:
        # Strong contact signals even without a clear name title (e.g. "# Contact")
        s = 0.80
    elif contact_kws >= 2 and not has_product:
        # Moderate contact signals
        s = 0.62
    scores["person"] = s

    # ------------------------------------------------------------------ coding
    has_fence = "```" in combined or "~~~" in combined
    code_kws = len(re.findall(
        r'\b(function|class|def |import |from \w|git |commit|pull request|'
        r'refactor|bug|debug|stack trace|exception|endpoint|'
        r'query|lint|build|docker|kubernetes|ci.?cd|pr |diff|branch|merge)\b', low
    ))
    title_hit = bool(re.search(
        r'\b(fix|bug|refactor|implement|code|test|deploy|pr|patch|release|hotfix)\b',
        title_low,
    ))
    s = 0.0
    if has_fence:
        s = 0.92
    elif code_kws >= 4:
        s = 0.85
    elif code_kws >= 2:
        s = 0.75
    elif code_kws == 1:
        s = 0.58
    if title_hit and s > 0:
        s = min(s + 0.07, 0.95)
    scores["coding"] = s

    # ------------------------------------------------------------------ project
    proj_kws = len(re.findall(
        r'\b(project|milestone|deadline|sprint|roadmap|deliverable|scope|'
        r'stakeholder|launch|release|phase|timeline|epic|backlog)\b', low
    ))
    title_hit = bool(re.search(
        r'\b(project|milestone|sprint|roadmap|launch|phase)\b', title_low
    ))
    s = 0.0
    if proj_kws >= 3:
        s = 0.85
    elif proj_kws >= 2:
        s = 0.77
    elif proj_kws == 1:
        s = 0.62
    if title_hit and s > 0:
        s = min(s + 0.08, 0.90)
    scores["project"] = s

    # ---------------------------------------------------------------- strategy
    strat_kws = len(re.findall(
        r'\b(strategy|strategic|okr|kpi|objective|vision|quarterly|annual|'
        r'q[1-4]|mission|competitive|positioning|market|north star|initiative)\b', low
    ))
    title_hit = bool(re.search(
        r'\b(strategy|strategic|okr|vision|q[1-4]|annual|quarterly)\b', title_low
    ))
    s = 0.0
    if strat_kws >= 3:
        s = 0.85
    elif strat_kws >= 2:
        s = 0.77
    elif strat_kws == 1:
        s = 0.58
    if title_hit:
        s = min(s + 0.10, 0.92) if s > 0 else 0.80
    scores["strategy"] = s

    # -------------------------------------------------------------------- idea
    idea_kws = len(re.findall(
        r'\b(idea|what if|maybe|consider|brainstorm|proposal|concept|'
        r'experiment|hypothesis|could we|should we|imagine)\b', low
    ))
    title_hit = bool(re.search(r'\b(idea|concept|proposal|hypothesis)\b', title_low))
    s = 0.0
    if idea_kws >= 3:
        s = 0.83
    elif idea_kws >= 2:
        s = 0.75
    elif idea_kws == 1:
        s = 0.58
    if title_hit:
        s = min(s + 0.10, 0.92) if s > 0 else 0.78
    scores["idea"] = s

    # ---------------------------------------------------------------- personal
    pers_kws = len(re.findall(
        r'\b(today i|feeling|mood|personal|diary|journal|reflection|'
        r'anxiety|grateful|frustrated|excited|worried|proud|sad|happy)\b', low
    ))
    title_hit = bool(re.search(
        r'\b(personal|journal|diary|reflection|mood)\b', title_low
    ))
    s = 0.0
    if pers_kws >= 3:
        s = 0.85
    elif pers_kws >= 2:
        s = 0.77
    elif pers_kws == 1:
        s = 0.60
    if title_hit:
        s = min(s + 0.10, 0.92) if s > 0 else 0.80
    scores["personal"] = s

    # ---------------------------------------------------------------- pick best
    best_type = max(scores, key=lambda t: scores[t])
    best_score = scores[best_type]

    if best_score < 0.50:
        return ("note", 0.90)

    return (best_type, best_score)
