"""
services/ai_router.py
Routes AI requests to Groq first, falling back to Gemini on any failure.
Includes a simple 60 second in-memory cache for identical prompts.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from services.gemini_service import GeminiService
from services.groq_service import GroqService

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "در حال حاضر AI در دسترس نیست. بعداً امتحان کن! 🤖"


class AIRouter:
    def __init__(
        self,
        groq_service: Optional[GroqService],
        gemini_service: Optional[GeminiService],
        cache_ttl_seconds: int = 60,
    ) -> None:
        self._groq = groq_service
        self._gemini = gemini_service
        self._cache_ttl_seconds = cache_ttl_seconds
        # cache key -> (timestamp, response_text)
        self._cache: Dict[str, Tuple[float, str]] = {}

    def _cache_key(self, prompt: str, history: List[Tuple[str, str]]) -> str:
        history_part = "|".join(f"{role}:{content}" for role, content in history)
        return f"{prompt.strip().lower()}::{history_part}"

    def _get_cached(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        timestamp, text = entry
        if time.monotonic() - timestamp > self._cache_ttl_seconds:
            del self._cache[key]
            return None
        return text

    def _set_cached(self, key: str, text: str) -> None:
        self._cache[key] = (time.monotonic(), text)
        # Opportunistic cleanup so the cache dict doesn't grow unbounded.
        if len(self._cache) > 500:
            now = time.monotonic()
            expired = [
                k for k, (ts, _) in self._cache.items()
                if now - ts > self._cache_ttl_seconds
            ]
            for k in expired:
                del self._cache[k]

    async def get_ai_response(
        self,
        prompt: str,
        history: Optional[List[Tuple[str, str]]] = None,
    ) -> str:
        """Get an AI response for `prompt`, trying Groq then Gemini.

        history is a list of (role, content) tuples, oldest first, role is
        "user" or "assistant". Returns the final fallback Persian message
        if both providers fail or are not configured.
        """
        history = history or []
        key = self._cache_key(prompt, history)

        cached = self._get_cached(key)
        if cached is not None:
            logger.info("AI cache hit")
            return cached

        if self._groq is not None:
            try:
                text = await self._groq.get_response(prompt, history)
                self._set_cached(key, text)
                return text
            except Exception as exc:
                logger.warning("Groq failed, falling back to Gemini: %s", exc)

        if self._gemini is not None:
            try:
                text = await self._gemini.get_response(prompt, history)
                self._set_cached(key, text)
                return text
            except Exception as exc:
                logger.warning("Gemini also failed: %s", exc)

        return FALLBACK_MESSAGE