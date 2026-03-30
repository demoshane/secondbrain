"""Pass 4: keyword-based action item extraction. No LLM, no DB."""
import re

from engine.passes import ActionItem

DEFAULT_MARKERS = ["TODO", "AP", "action:", "@owner", "Action Point"]

# Pre-compiled pattern for @mention owner extraction: @word rest-of-line
_AT_PAT = re.compile(r'^@(\w+)\s+(.+)', re.IGNORECASE)


def extract_keyword_actions(body: str, custom_markers: list[str] | None = None) -> list[ActionItem]:
    """Extract action items from body text by matching keyword markers.

    Recognises DEFAULT_MARKERS plus any custom_markers from config.toml
    [action_items] section (loaded fresh each call when custom_markers is None).

    Returns a list of ActionItem objects with source="keyword". No LLM, no DB.
    """
    if custom_markers is None:
        from engine.config_loader import load_config
        from engine.paths import CONFIG_PATH
        config = load_config(CONFIG_PATH)
        custom_markers = config.get("action_items", {}).get("custom_markers", [])

    all_markers = DEFAULT_MARKERS + list(custom_markers)

    results: list[ActionItem] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for marker in all_markers:
            if marker.startswith("@"):
                # @owner pattern: capture owner name and remaining text
                m = _AT_PAT.match(stripped)
                if m:
                    results.append(ActionItem(
                        text=m.group(2).strip(),
                        owner=m.group(1),
                        due_date=None,
                        source="keyword",
                    ))
                    break
            else:
                pat = re.compile(re.escape(marker) + r'\s*[:\-]?\s*(.+)', re.IGNORECASE)
                m = pat.match(stripped)
                if m:
                    results.append(ActionItem(
                        text=m.group(1).strip(),
                        owner=None,
                        due_date=None,
                        source="keyword",
                    ))
                    break
    return results
