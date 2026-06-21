"""
config.py
Loads configuration from environment variables (.env file) and exposes
a single Config object used across the whole bot.
"""

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_int_list(raw: str) -> List[int]:
    """Parse a comma separated string of integers into a list of ints.

    Empty / whitespace-only entries are ignored. Non-integer entries are
    skipped silently so a malformed .env value never crashes the bot.
    """
    result: List[int] = []
    if not raw:
        return result
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            result.append(int(chunk))
        except ValueError:
            continue
    return result


def _parse_str_list(raw: str) -> List[str]:
    """Parse a comma separated string into a list of lowercase, trimmed strings."""
    result: List[str] = []
    if not raw:
        return result
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk:
            result.append(chunk.lower())
    return result


@dataclass
class Config:
    bot_token: str
    groq_api_key: str
    gemini_api_key: str
    admin_ids: List[int] = field(default_factory=list)
    trigger_keywords: List[str] = field(default_factory=list)

    db_path: str = "bot_database.sqlite3"

    # Rate limit tuning
    max_messages_per_window: int = 5
    message_window_seconds: int = 10
    max_ai_requests_per_window: int = 3
    ai_window_seconds: int = 60
    repeat_message_threshold: int = 3

    # AI tuning
    groq_model: str = "openai/gpt-oss-20b"
    gemini_model: str = "gemini-2.5-flash-lite"
    groq_timeout_seconds: int = 8
    ai_cache_ttl_seconds: int = 60
    history_limit: int = 5

    default_mute_minutes: int = 60
    max_warns_before_ban: int = 3


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Copy .env.example to .env and fill it in."
        )

    admin_ids = _parse_int_list(os.getenv("ADMIN_IDS", ""))
    trigger_keywords = _parse_str_list(os.getenv("TRIGGER_KEYWORDS", ""))
    db_path = os.getenv("DB_PATH", "bot_database.sqlite3").strip()

    return Config(
        bot_token=bot_token,
        groq_api_key=groq_api_key,
        gemini_api_key=gemini_api_key,
        admin_ids=admin_ids,
        trigger_keywords=trigger_keywords,
        db_path=db_path,
    )


config = load_config()