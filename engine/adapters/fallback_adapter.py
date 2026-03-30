"""FallbackAdapter — wraps a primary adapter with a fallback (AI-06).

If the primary adapter raises any exception (quota, CLI not found, timeout, etc.),
the fallback adapter is tried automatically. Both failures propagate as RuntimeError.
"""
import logging

from engine.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class FallbackAdapter(BaseAdapter):
    """Tries primary adapter; on any exception falls back to secondary.

    Tracks which adapter was actually used via the `used_fallback` attribute (D-11).
    """

    def __init__(self, primary: BaseAdapter, fallback: BaseAdapter) -> None:
        self._primary = primary
        self._fallback = fallback
        self.used_fallback: bool = False

    def generate(self, user_content: str, system_prompt: str = "") -> str:
        try:
            result = self._primary.generate(user_content, system_prompt)
            self.used_fallback = False
            return result
        except Exception as exc:
            logger.warning(
                "Primary adapter %s failed (%s) — falling back to %s",
                type(self._primary).__name__,
                exc,
                type(self._fallback).__name__,
            )
            self.used_fallback = True
            return self._fallback.generate(user_content, system_prompt)
