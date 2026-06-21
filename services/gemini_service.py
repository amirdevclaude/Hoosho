"""
services/gemini_service.py
Thin async wrapper around the Gemini (google-generativeai) API.
Used as the fallback AI provider when Groq fails or times out.
"""

import logging
from typing import List, Tuple

import google.generativeai as genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "تو یک دستیار گروه تلگرامی هستی.\n"
    "به فارسی پاسخ بده.\n"
    "لحن: دوستانه و کمی طنازانه.\n"
    "پاسخ‌هایت کوتاه باشند مگر سوال پیچیده باشد.\n"
    "از محتوای سیاسی یا توهین‌آمیز اجتناب کن."
)


class GeminiService:
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT,
        )

    async def get_response(self, prompt: str, history: List[Tuple[str, str]]) -> str:
        """Send `prompt` to Gemini with `history` as prior conversation turns.

        history is a list of (role, content) tuples where role is either
        "user" or "assistant". Raises RuntimeError on any failure so the
        caller can return the final fallback message.
        """
        gemini_history = []
        for role, content in history:
            gemini_role = "model" if role == "assistant" else "user"
            gemini_history.append({"role": gemini_role, "parts": [content]})

        try:
            chat = self._model.start_chat(history=gemini_history)
            response = await chat.send_message_async(prompt)
        except Exception as exc:
            logger.warning("Gemini request failed: %s", exc)
            raise RuntimeError("gemini_error") from exc

        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise RuntimeError("gemini_empty_response")

        return text.strip()