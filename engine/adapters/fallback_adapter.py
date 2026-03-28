"""FallbackAdapter — wraps a primary adapter with a fallback (AI-06).

If the primary adapter raises any exception (quota, CLI not found, timeout, etc.),
the fallback adapter is tried automatically. Both failures propagate as RuntimeError.
"""
import logging

from engine.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class FallbackAdapter(BaseAdapter):
    """Tries primary adapter; on any exception falls back to secondary."""

    def __init__(self, primary: BaseAdapter, fallback: BaseAdapter) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate(self, user_content: str, system_prompt: str = "") -> str:
        try:
            return self._primary.generate(user_content, system_prompt)
        except Exception as exc:
            logger.warning(
                "Primary adapter %s failed (%s) — falling back to %s",
                type(self._primary).__name__,
                exc,
                type(self._fallback).__name__,
            )
            return self._fallback.generate(user_content, system_prompt)
