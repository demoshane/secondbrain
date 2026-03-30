"""GroqAdapter — calls Groq REST API (OpenAI-compatible) via httpx (D-01, D-02).

API key is retrieved from macOS Keychain at call time (never cached in memory).
"""
import httpx
import keyring

from engine.adapters.base import BaseAdapter

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
KEYCHAIN_SERVICE = "second-brain"
KEYCHAIN_ACCOUNT = "groq_api_key"


class GroqAdapter(BaseAdapter):
    """Sends prompts to Groq via REST API using key from macOS Keychain."""

    def generate(self, user_content: str, system_prompt: str = "") -> str:
        """Post to Groq chat completions; return text response.

        Args:
            user_content: The user message (never used as system prompt — AI-10).
            system_prompt: Static instructions only.

        Raises:
            RuntimeError: If no API key is configured in Keychain.
            httpx.HTTPError: On HTTP errors from Groq API.
        """
        api_key = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        if not api_key:
            raise RuntimeError("GroqAdapter: no API key in Keychain — configure via Settings")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})

        resp = httpx.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
