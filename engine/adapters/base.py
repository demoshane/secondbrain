"""Abstract base class for AI model adapters (AI-06).

New adapters (OpenAI, Gemini, etc.) extend BaseAdapter without touching core logic.
"""
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    @abstractmethod
    def generate(self, user_content: str, system_prompt: str = "") -> str:
        """Send a prompt to the model; return the text response.

        Args:
            user_content: The note content or question.
                user_content is never to be passed inside system_prompt (AI-10).
            system_prompt: Static instructions — never includes user content (AI-10).
        """
        ...
