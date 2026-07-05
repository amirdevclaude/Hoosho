"""
services/ai_router.py
Routes AI requests to Groq first, falling back to Gemini on any failure.
Includes a simple 60 second in-memory cache for identical prompts.
Now with retry logic and metrics collection.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

from services.gemini_service import GeminiService
from services.groq_service import GroqService
from services.metrics import metrics
from config import config

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
        """Get an AI response for `prompt`, trying Groq with retries then Gemini.

        history is a list of (role, content) tuples, oldest first, role is
        "user" or "assistant". Returns the final fallback Persian message
        if both providers fail or are not configured.
        """
        history = history or []
        key = self._cache_key(prompt, history)

        cached = self._get_cached(key)
        if cached is not None:
            logger.info("AI cache hit")
            metrics.ai_requests += 1
            return cached

        start_time = time.time()
        
        # Try Groq with retries
        if self._groq is not None:
            for attempt in range(config.ai_max_retries):
                try:
                    logger.info(f"Attempting Groq request (attempt {attempt + 1}/{config.ai_max_retries})")
                    text = await self._groq.get_response(prompt, history)
                    latency_ms = (time.time() - start_time) * 1000
                    metrics.record_ai_request(latency_ms, provider="groq")
                    self._set_cached(key, text)
                    return text
                except asyncio.TimeoutError:
                    logger.warning(f"Groq timeout on attempt {attempt + 1}")
                    metrics.record_ai_timeout()
                    if attempt < config.ai_max_retries - 1:
                        await asyncio.sleep(config.ai_retry_delay_seconds)
                except Exception as exc:
                    logger.warning(f"Groq failed on attempt {attempt + 1}: {exc}")
                    metrics.record_ai_error(provider="groq")
                    if attempt < config.ai_max_retries - 1:
                        await asyncio.sleep(config.ai_retry_delay_seconds)

        # Try Gemini
        if self._gemini is not None:
            try:
                logger.info("Attempting Gemini request")
                text = await self._gemini.get_response(prompt, history)
                latency_ms = (time.time() - start_time) * 1000
                metrics.record_ai_request(latency_ms, provider="gemini")
                self._set_cached(key, text)
                return text
            except Exception as exc:
                logger.warning(f"Gemini also failed: {exc}")
                metrics.record_ai_error(provider="gemini")

        logger.error("All AI providers failed")
        return FALLBACK_MESSAGE
