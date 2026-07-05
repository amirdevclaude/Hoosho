"""
utils/helpers.py
Small stateless helper functions shared across handlers.
"""

import random
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram.types import User

_DURATION_RE = re.compile(r"^(\d+)\s*([mhd])$", re.IGNORECASE)

_DURATION_UNITS = {
    "m": "minutes",
    "h": "hours",
    "d": "days",
}


def parse_duration(raw: str) -> Optional[timedelta]:
    """Parse a duration string like '30m', '2h', '1d' into a timedelta.

    Returns None if the string doesn't match the expected format.
    """
    if not raw:
        return None
    match = _DURATION_RE.match(raw.strip())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2).lower()
    if amount <= 0:
        return None
    kwargs = {_DURATION_UNITS[unit]: amount}
    return timedelta(**kwargs)


def format_duration(td: timedelta) -> str:
    """Human readable duration, e.g. '1h', '2d 3h', '30m'."""
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"


def mention_html(user: User) -> str:
    """Build an HTML mention link for a user that works even without a username."""
    name = user.full_name or user.first_name or "کاربر"
    safe_name = (
        name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return f'<a href="tg://user?id={user.id}">{safe_name}</a>'


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


WELCOME_MESSAGES = [
    "به جمع ما خوش اومدی {mention}! امیدوارم بهمو خوش بگذره 🎉",
    "سلام {mention} عزیز! خوشحالیم که بهمو پیوستی 🌟",
    "هورا! {mention} اومد. یه دور تشویق میخوایم 👏",
    "{mention} عزیز خوش اومدی، قانون اول گروه: خوش بگذرون 😄",
    "یه عضو جدید داریم! سلام {mention}، خوش اومدی ✨",
    "{mention} وارد شد! امیدواریم جای خوبی باشه برات 👋",
]

GOODBYE_MESSAGES = [
    "{mention} از گروه رفت. بدرود و موفق باشی 👋",
    "خداحافظ {mention}، جات خالی میشه 😢",
    "{mention} ما رو ترک کرد. هر وقت خاستی برگرد 😚",
    "بدرود {mention}! امیدواریم بازم ببینیمت 🌙",
]

JOKES = [
    "چرا کامپیوترا سرما نمیخورن? چون ویندوز دارن! 🤪",
    "یارو میره دکتر میگه دکتر من فراموشکارم، دکتر میگه از کی? میگه از کی چی? 😂",
    "چرا برنامه‌نویسا عاشق طبیعتن? چون فضای زیادی دارن! 🌳",
    "به سوسک میگن چرا نمیمیری? میگه مگه زندم میذارین? 🚫",
    "یارو رفته فست‌فود میگه یه پیتزای نیمه‌گرسنه میخوام! 🝕",
    "چرا ربات‌ها هیچوقت عصبانی نمیشن? چون همیشه ریست میشن! 🤖",
    "دو تا آهنربا دارن صحبت میکنن، یکیش میگه عاشقتم نمیتونم ولت کن! 🧲",
    "یارو به دوستش میگه دیشب خواب دیدم دارم فوتبال بازی میکنم، صبح بیدار شدم دیدم تشک نیست، رفته گل بزنه! ⚽",
    "چرا ماهی‌ها هیچوقت پول قرض نمیدن? چون میترسن زیر آب برن! 🐠",
    "یارو رفته نونوایی میگه یه نون داغ میخوام، نونوا میگه داغشو نداریم سردشو داریم بذار زیر بغلت داغ میشه! 🜞",
    "دکتر به بیمار میگه باید رژیم بگیری، بیمار میگه باشه از فردا شروع میکنم، امروز رو مهمونتم! 🝴",
]


def random_welcome(mention: str) -> str:
    template = random.choice(WELCOME_MESSAGES)
    return template.format(mention=mention)


def random_goodbye(mention: str) -> str:
    template = random.choice(GOODBYE_MESSAGES)
    return template.format(mention=mention)


def random_joke() -> str:
    return random.choice(JOKES)
