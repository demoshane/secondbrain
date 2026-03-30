"""Ollama adapter — routes to a local Ollama instance (AI-03)."""
import httpx
import ollama

from engine.adapters.base import BaseAdapter


class OllamaAdapter(BaseAdapter):
    """Adapter for Ollama models running on the host machine.

    Default host uses host.docker.internal for DevContainer compatibility (macOS).
    On Linux DevContainers, add --add-host=host.docker.internal:host-gateway to devcontainer.json.
    """

    def __init__(self, model: str, host: str = "http://host.docker.internal:11434", timeout: float = 30.0) -> None:
        self._model = model
        self._client = ollama.Client(host=host, timeout=httpx.Timeout(timeout))

    def generate(self, user_content: str, system_prompt: str = "") -> str:
        """Send prompt to Ollama model; return text response.

        AI-10: user_content is passed as a user role message, never in system_prompt.
        """
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})
        response = self._client.chat(model=self._model, messages=messages)
        return response.message.content
