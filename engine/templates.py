"""Template loading and rendering for per-type note body templates."""
import string
from pathlib import Path

from engine.paths import TEMPLATES_DIR


def load_template(note_type: str, templates_dir: Path | None = None) -> str:
    """Load the body template for the given note type.

    Falls back to a minimal template if the file is not found.
    Uses pathlib only (FOUND-12).

    Args:
        note_type: The type of note (e.g. 'meeting', 'note', 'coding').
        templates_dir: Override the default TEMPLATES_DIR (used in tests).

    Returns:
        Raw template string with ${variable} placeholders.
    """
    base_dir = templates_dir if templates_dir is not None else TEMPLATES_DIR
    template_path = base_dir / f"{note_type}.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    # Minimal fallback — safe_substitute leaves unknown placeholders as-is
    return "## ${title}\n\n${body}\n"


def render_template(template_str: str, substitutions: dict) -> str:
    """Render a template string using safe_substitute.

    Missing keys are left as-is (not raised as errors).

    Args:
        template_str: Raw template with ${variable} placeholders.
        substitutions: Mapping of variable names to replacement values.

    Returns:
        Rendered string.
    """
    return string.Template(template_str).safe_substitute(substitutions)
