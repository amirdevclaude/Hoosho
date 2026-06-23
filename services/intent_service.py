"""
services/intent_service.py
تشخیص قصد (intent detection) برای مدیریت طبیعی گروه.
ادمین می‌تونه به‌جای دستور مستقیم، به زبان طبیعی بگه:
"این رو بن کن"، "سکوتش کن ۳۰ دقیقه"، "اخراجش کن" و...
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# کلمات کلیدی برای هر action — بدون نیاز به AI برای موارد ساده
_BAN_KEYWORDS = ["بن کن", "بنش کن", "بن کنش", "بلاکش کن", "بلاک کن"]
_KICK_KEYWORDS = ["اخراجش کن", "اخراج کن", "kickش کن", "بیرونش کن", "بندازش بیرون"]
_MUTE_KEYWORDS = ["سکوتش کن", "میوتش کن", "میوت کن", "ساکتش کن", "سکوت بزن"]
_UNMUTE_KEYWORDS = ["آنمیوتش کن", "آنمیوت کن", "سکوتشو بردار", "بذار حرف بزنه"]
_WARN_KEYWORDS = ["اخطارش بده", "اخطار بده", "وارنش کن", "هشدارش بده"]
_DEL_KEYWORDS = ["پیامشو پاک کن", "حذفش کن", "پاکش کن", "این پیامو پاک کن", "delش کن"]

_DURATION_MAP = {
    "یه دقیقه": 1, "یک دقیقه": 1,
    "۵ دقیقه": 5, "پنج دقیقه": 5,
    "۱۰ دقیقه": 10, "ده دقیقه": 10,
    "۱۵ دقیقه": 15, "ربع ساعت": 15,
    "۲۰ دقیقه": 20, "بیست دقیقه": 20,
    "نیم ساعت": 30, "۳۰ دقیقه": 30, "سی دقیقه": 30,
    "یه ساعت": 60, "یک ساعت": 60, "۱ ساعت": 60,
    "دو ساعت": 120, "۲ ساعت": 120,
    "سه ساعت": 180, "۳ ساعت": 180,
    "شش ساعت": 360, "۶ ساعت": 360,
    "۱۲ ساعت": 720, "دوازده ساعت": 720,
    "یه روز": 1440, "یک روز": 1440, "۱ روز": 1440,
    "دو روز": 2880, "۲ روز": 2880,
    "یه هفته": 10080, "یک هفته": 10080,
}


@dataclass
class Intent:
    action: Optional[str]
    duration_minutes: Optional[int]
    reason: Optional[str]
    is_actionable: bool


class IntentService:
    def __init__(self, groq_service=None) -> None:
        self._groq = groq_service

    async def parse(self, text: str) -> Intent:
        """تشخیص قصد از متن پیام ادمین."""
        if not text or not text.strip():
            return Intent(action=None, duration_minutes=None, reason=None, is_actionable=False)

        lowered = text.strip().lower()

        # تشخیص action با keyword matching
        action = self._detect_action(lowered)
        if action is None:
            return Intent(action=None, duration_minutes=None, reason=None, is_actionable=False)

        duration = self._detect_duration(lowered) if action == "mute" else None

        return Intent(
            action=action,
            duration_minutes=duration,
            reason=text.strip(),
            is_actionable=True,
        )

    def _detect_action(self, text: str) -> Optional[str]:
        for kw in _BAN_KEYWORDS:
            if kw in text:
                return "ban"
        for kw in _KICK_KEYWORDS:
            if kw in text:
                return "kick"
        for kw in _UNMUTE_KEYWORDS:
            if kw in text:
                return "unmute"
        for kw in _MUTE_KEYWORDS:
            if kw in text:
                return "mute"
        for kw in _WARN_KEYWORDS:
            if kw in text:
                return "warn"
        for kw in _DEL_KEYWORDS:
            if kw in text:
                return "del"
        return None

    def _detect_duration(self, text: str) -> Optional[int]:
        for phrase, minutes in _DURATION_MAP.items():
            if phrase in text:
                return minutes
        # پیش‌فرض برای میوت: ۶۰ دقیقه
        return 60