"""
services/groq_service.py
Thin async wrapper around the Groq chat completions API.
"""

import asyncio
import logging
from typing import List, Tuple

from groq import AsyncGroq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "تو یک دستیار گروه تلگرامی هستی.\n"
    "به فارسی پاسخ بده.\n"
    "لحن: دوستانه و کمی طنازانه.\n"
    "پاسخ‌هایت کوتاه باشند مگر سوال پیچیده باشد.\n"
    "از محتوای سیاسی یا توهین‌آمیز اجتناب کن."
)


class GroqService:
    def __init__(self, api_key: str, model: str, timeout_seconds: int = 8) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def get_response(self, prompt: str, history: List[Tuple[str, str]]) -> str:
        """Send `prompt` to Groq with `history` as prior conversation turns.

        history is a list of (role, content) tuples where role is either
        "user" or "assistant". Raises on any failure (timeout, API error,
        empty response) so the caller (ai_router) can fall back to Gemini.
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for role, content in history:
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        try:
            completion = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=512,
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            logger.warning("Groq request timed out after %ss", self._timeout_seconds)
            raise RuntimeError("groq_timeout") from exc
        except Exception as exc:
            logger.warning("Groq request failed: %s", exc)
            raise RuntimeError("groq_error") from exc

        if not completion.choices:
            raise RuntimeError("groq_empty_response")

        text = completion.choices[0].message.content
        if not text or not text.strip():
            raise RuntimeError("groq_empty_response")

        return text.strip()