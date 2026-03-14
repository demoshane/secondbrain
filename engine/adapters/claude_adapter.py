"""Claude adapter — routes to Claude via 'claude -p' subprocess (AI-04).

Uses the active Claude Code Max plan session. No API key required.
Never imports anthropic SDK.
"""
import shutil
import subprocess

from engine.adapters.base import BaseAdapter


class ClaudeAdapter(BaseAdapter):
    """Routes to Claude via 'claude -p' subprocess (Max plan, no API key needed).

    The model param is accepted for config consistency but the claude CLI
    uses its own default model from the user's session.
    """

    def __init__(self, model: str = "") -> None:
        # model param accepted for config consistency; claude CLI picks model from session
        self._model = model

    def generate(self, user_content: str, system_prompt: str = "") -> str:
        """Send prompt to Claude via subprocess; return text response.

        AI-10: user_content is NEVER interpolated into system_prompt string.
            system_prompt + separator + user_content in full_prompt.

        Raises:
            RuntimeError: If claude CLI not found on PATH or subprocess returns non-zero.
        """
        if shutil.which("claude") is None:
            raise RuntimeError(
                "ClaudeAdapter: claude CLI not found — run sb-capture from the host"
                " or install claude inside the container"
            )

        # Build full_prompt: system instructions come first, then user content
        # AI-10: user_content is never interpolated into system_prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{user_content}"
        else:
            full_prompt = user_content

        result = subprocess.run(
            ["claude", "-p", full_prompt, "--allowedTools", ""],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ClaudeAdapter: subprocess returned {result.returncode}"
            )
        return result.stdout.strip()
