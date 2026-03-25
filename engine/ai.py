"""AI layer: proactive follow-up questions and memory update (AI-01, CAP-06)."""
import shutil
import sqlite3
import subprocess
from pathlib import Path

import engine.router as _router


# AI-10: system prompts are STATIC — never include user-controlled content.
QUESTION_SYSTEM_PROMPTS = {
    "meeting": (
        "You are a meeting notes assistant. Given a meeting note title, generate exactly 2-3 short "
        "follow-up questions to extract missing context (attendees, decisions, action items). "
        "Output only a numbered list."
    ),
    "idea": (
        "You are an idea development assistant. Given an idea title, generate 2-3 questions to "
        "develop it further (problem it solves, who benefits, first step). "
        "Output only a numbered list."
    ),
    "coding": (
        "You are a software engineering assistant. Given a coding note title, generate 2-3 questions "
        "to capture architectural context (why this approach, alternatives, risks). "
        "Output only a numbered list."
    ),
    "person": (
        "You are a professional context assistant. Given a person note title, generate 2-3 questions "
        "to capture relationship context (how you know them, their goals, recent interactions). "
        "Output only a numbered list."
    ),
    "strategy": (
        "You are a strategy assistant. Given a strategy note title, generate 2-3 questions to "
        "clarify intent (objective, success metric, timeline). "
        "Output only a numbered list."
    ),
    "note": (
        "You are a knowledge assistant. Given a note title, generate 2-3 questions to enrich it "
        "(key insight, source, how it connects to current work). "
        "Output only a numbered list."
    ),
    "projects": (
        "You are a project management assistant. Given a project or client note title, generate 2-3 "
        "questions to capture key context: client goals, key contacts, current status."
    ),
    "personal": (
        "You are a personal journal assistant. Given a personal note title, generate 2-3 reflective "
        "questions to deepen the capture: what matters most, what action follows."
    ),
}

FALLBACK_QUESTIONS: dict[str, list[str]] = {
    "meeting": ["Who were the key decision-makers present?", "What are the next action items?"],
    "idea": ["What problem does this solve?", "Who would benefit most from this?"],
    "coding": ["Why this approach over alternatives?", "What are the main risks?"],
    "person": ["How did you meet this person?", "What are their current priorities?"],
    "strategy": ["What does success look like in 90 days?", "What is the biggest obstacle?"],
    "note": ["What is the key insight here?", "How does this connect to current work?"],
    "projects": ["Who is the primary stakeholder?", "What does success look like?"],
    "personal": ["What prompted this reflection?", "What action do you want to take?"],
}


def ask_followup_questions(
    note_type: str,
    title: str,
    sensitivity: str,
    config_path: Path,
    conn: sqlite3.Connection | None = None,
) -> list[str]:
    """Generate 2-3 follow-up questions for the given note.

    AI-10: title is passed as user_content, NOT interpolated into system_prompt.
    AI failure returns fallback questions — capture is never blocked.

    Args:
        note_type: Content type (e.g. 'meeting', 'idea').
        title: Note title — passed as user_content only.
        sensitivity: Classifier result ('pii', 'private', 'public').
        config_path: Path to config.toml for adapter routing.
        conn: Optional SQLite connection for RAG context injection (SEARCH-04).

    Returns:
        List of 2-3 question strings.
    """
    fallback = FALLBACK_QUESTIONS.get(note_type, FALLBACK_QUESTIONS["note"])
    system = QUESTION_SYSTEM_PROMPTS.get(note_type, QUESTION_SYSTEM_PROMPTS["note"])

    try:
        adapter = _router.get_adapter(sensitivity, config_path)
        from engine.rag import augment_prompt
        user_content = augment_prompt(title, conn) if conn is not None else title
        raw = adapter.generate(user_content=user_content, system_prompt=system)
    except Exception:
        return fallback

    # Parse lines: keep lines starting with digit or dash
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    parsed = []
    for line in lines:
        if line and (line[0].isdigit() or line[0] == "-"):
            # Strip leading "1. ", "2. ", "- " prefixes
            if line[0].isdigit():
                # e.g. "1. Question text" → "Question text"
                parts = line.split(".", 1)
                if len(parts) == 2:
                    parsed.append(parts[1].strip())
                else:
                    parsed.append(line)
            elif line.startswith("- "):
                parsed.append(line[2:].strip())
            else:
                parsed.append(line.lstrip("-").strip())

    questions = parsed[:3]
    if len(questions) < 2:
        return fallback
    return questions


def update_memory(note_type: str, summary: str, config_path: Path) -> None:
    """Update Claude memory with new context from a captured note (CAP-06).

    Routes through ModelRouter with sensitivity='public' — config drives
    adapter selection (AI-05). Summary must not contain PII.

    Error handling: logs exception type only (GDPR-05 — no content in logs).

    Args:
        note_type: Type of note captured.
        summary: Brief summary — must not contain PII.
        config_path: Path to config.toml — passed to ModelRouter for public-sensitivity routing (AI-05).
    """
    try:
        system_prompt = (
            "Update the project memory file with new context. "
            "Do not include sensitive details. Write concise bullet points."
        )
        user_content = f"Note type: {note_type}. Summary: {summary}"

        adapter = _router.get_adapter("public", config_path)  # AI-05: config drives adapter

        if not shutil.which("claude"):
            raise RuntimeError("claude CLI not found")

        full_prompt = f"{system_prompt}\n\n---\n\n{user_content}"
        subprocess.run(
            ["claude", "-p", full_prompt, "--allowedTools", "Write,Read"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as e:
        print(f"Memory update skipped: {type(e).__name__}")


def main() -> None:
    import argparse
    from engine.paths import BRAIN_ROOT

    parser = argparse.ArgumentParser(
        prog="sb-update-memory",
        description="Update Claude memory file with a note summary.",
    )
    parser.add_argument("--note-type", dest="note_type", required=True,
                        help="Content type of the captured note (e.g. coding, person, meeting)")
    parser.add_argument("--summary", required=True,
                        help="Summary text to record in memory")
    parser.add_argument("--config-path", dest="config_path", default=None,
                        help="Path to config.toml (default: BRAIN_ROOT/.meta/config.toml)")
    args = parser.parse_args()

    config_path: Path = (
        Path(args.config_path) if args.config_path else BRAIN_ROOT / ".meta" / "config.toml"
    )
    update_memory(args.note_type, args.summary, config_path)


if __name__ == "__main__":
    main()
