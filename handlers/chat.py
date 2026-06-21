"""
handlers/chat.py
Handles AI conversation triggers: bot mention, reply-to-bot, and
trigger keywords. Also exposes the /joke fun command.

AI replies ONLY when:
- The bot is @mentioned in the message
- The message is a reply to one of the bot's own messages
- The message starts with one of the configured TRIGGER_KEYWORDS
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import database.db as db
from config import config
from middlewares.rate_limit import RateLimitMiddleware
from services.ai_router import AIRouter
from utils.filters import IsGroupChat
from utils.helpers import random_joke

logger = logging.getLogger(__name__)

router = Router(name="chat")
router.message.filter(IsGroupChat())


def _strip_mention(text: str, bot_username: str) -> str:
    """Remove a leading @botusername mention from the text, if present."""
    mention = f"@{bot_username}"
    if text.lower().startswith(mention.lower()):
        return text[len(mention):].strip()
    return text.replace(mention, "").strip()


def _starts_with_trigger(text: str) -> bool:
    lowered = text.strip().lower()
    return any(lowered.startswith(keyword) for keyword in config.trigger_keywords)


async def _is_bot_mentioned(message: Message, bot_username: str) -> bool:
    if not message.text or not message.entities:
        return False
    for entity in message.entities:
        if entity.type == "mention":
            mentioned_text = message.text[entity.offset: entity.offset + entity.length]
            if mentioned_text.lower() == f"@{bot_username}".lower():
                return True
    return False


def _is_reply_to_bot(message: Message, bot_id: int) -> bool:
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        return False
    return message.reply_to_message.from_user.id == bot_id


@router.message(Command("joke"))
async def cmd_joke(message: Message) -> None:
    await message.reply(random_joke())


@router.message()
async def handle_ai_trigger(
    message: Message,
    ai_router: AIRouter,
    rate_limiter: RateLimitMiddleware,
    is_repeated_spam: bool = False,
) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return

    if is_repeated_spam:
        try:
            await message.delete()
        except Exception as exc:
            logger.warning("Could not delete spam message: %s", exc)
        new_count = await db.add_warn(
            message.from_user.id, message.chat.id, "اسپم پیام تکراری"
        )
        await message.answer(
            f"🚫 پیام تکراری شناسایی و حذف شد. اخطار: {new_count}/"
            f"{config.max_warns_before_ban}"
        )
        return

    text = message.text or ""
    if not text.strip():
        return

    bot_user = await message.bot.get_me()
    bot_username = bot_user.username or ""

    mentioned = await _is_bot_mentioned(message, bot_username)
    replied_to_bot = _is_reply_to_bot(message, bot_user.id)
    has_trigger = _starts_with_trigger(text)

    if not (mentioned or replied_to_bot or has_trigger):
        return

    if not rate_limiter.is_ai_request_allowed(message.from_user.id):
        await message.reply(
            "⏳ یکم آروم‌تر! بذار نفس بکشم، چند ثانیه دیگه دوباره امتحان کن."
        )
        return

    prompt = _strip_mention(text, bot_username) if mentioned else text
    if has_trigger and not mentioned:
        for keyword in config.trigger_keywords:
            if prompt.strip().lower().startswith(keyword):
                prompt = prompt.strip()[len(keyword):].strip()
                break
    if not prompt:
        prompt = "سلام"

    history = await db.get_recent_history(message.chat.id, message.from_user.id, config.history_limit)

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    response_text = await ai_router.get_ai_response(prompt, history)

    await db.add_history_message(message.chat.id, message.from_user.id, "user", prompt)
    await db.add_history_message(message.chat.id, message.from_user.id, "assistant", response_text)

    await message.reply(response_text)