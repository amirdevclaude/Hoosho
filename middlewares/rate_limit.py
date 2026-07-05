"""
middlewares/rate_limit.py
In-memory anti-spam middleware for aiogram 3.x.

Per user_id rules:
- Max N messages per `message_window_seconds` -> excess messages are
  silently dropped (handler is not called).
- Max M AI requests per `ai_window_seconds` -> exposed via
  is_ai_request_allowed(), which handlers call explicitly before calling
  the AI (see chat.py), since only the chat handler knows whether a given
  message is actually an AI request.
- If the same user sends the identical text 3 times in a row, the
  middleware flags it via data["is_repeated_spam"] = True so the chat
  handler can delete the message and issue a warning.
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)


class _UserState:
    __slots__ = ("timestamps", "ai_timestamps", "last_msg", "repeat_count")

    def __init__(self) -> None:
        self.timestamps: List[float] = []
        self.ai_timestamps: List[float] = []
        self.last_msg: str = ""
        self.repeat_count: int = 0


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        max_messages_per_window: int = 5,
        message_window_seconds: int = 10,
        max_ai_requests_per_window: int = 3,
        ai_window_seconds: int = 60,
        repeat_message_threshold: int = 3,
    ) -> None:
        super().__init__()
        self._max_messages = max_messages_per_window
        self._message_window = message_window_seconds
        self._max_ai = max_ai_requests_per_window
        self._ai_window = ai_window_seconds
        self._repeat_threshold = repeat_message_threshold
        self._state: Dict[int, _UserState] = {}

    def _get_state(self, user_id: int) -> _UserState:
        state = self._state.get(user_id)
        if state is None:
            state = _UserState()
            self._state[user_id] = state
        return state

    def is_ai_request_allowed(self, user_id: int) -> bool:
        """Check and record an AI request for this user. Returns False (and
        does NOT record) if the user is over the AI rate limit."""
        state = self._get_state(user_id)
        now = time.monotonic()
        state.ai_timestamps = [
            ts for ts in state.ai_timestamps if now - ts < self._ai_window
        ]
        if len(state.ai_timestamps) >= self._max_ai:
            return False
        state.ai_timestamps.append(now)
        return True

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if event.from_user is None:
            return await handler(event, data)

        user_id = event.from_user.id
        state = self._get_state(user_id)
        now = time.monotonic()

        # 1) Flood control: drop messages beyond the allowed rate.
        state.timestamps = [
            ts for ts in state.timestamps if now - ts < self._message_window
        ]
        state.timestamps.append(now)
        if len(state.timestamps) > self._max_messages:
            logger.info("Dropping flooded message from user_id=%s", user_id)
            return None

        # 2) Repeated identical message detection.
        text = (event.text or event.caption or "").strip()
        is_repeated_spam = False
        if text:
            if text == state.last_msg:
                state.repeat_count += 1
            else:
                state.repeat_count = 1
                state.last_msg = text

            if state.repeat_count >= self._repeat_threshold:
                is_repeated_spam = True
                state.repeat_count = 0  # reset so we don't re-flag every message after

        data["is_repeated_spam"] = is_repeated_spam
        data["rate_limiter"] = self

        return await handler(event, data)
