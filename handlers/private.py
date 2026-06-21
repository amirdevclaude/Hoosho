"""
handlers/private.py
Handles 1-on-1 private chat with the bot. Unlike groups, the AI replies
to EVERY message here (no mention/trigger keyword needed), making the
bot work as a general-purpose personal assistant in DMs.
"""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import database.db as db
from config import config
from middlewares.rate_limit import RateLimitMiddleware
from services.ai_router import AIRouter
from utils.filters import IsPrivateChat
from utils.helpers import random_joke

logger = logging.getLogger(__name__)

router = Router(name="private")
router.message.filter(IsPrivateChat())

WELCOME_TEXT = (
    "سلام! من هوشو هستم 🤖\n\n"
    "اینجا توی پیوی می‌تونی هر چی دوست داری بپرسی، با هم چت کنیم. "
    "لازم نیست چیز خاصی بنویسی یا منشن کنی، فقط پیام بده!\n\n"
    "دستورهای مفید:\n"
    "/joke — یه جوک بگم 😄\n"
    "/reset — تاریخچه‌ی چتمون رو پاک کن و از اول شروع کن\n"
    "/help — راهنما"
)

HELP_TEXT = (
    "📋 راهنمای استفاده در پیوی:\n\n"
    "• هر پیامی بفرستی، باهات چت می‌کنم\n"
    "• /reset — حافظه‌ی مکالمه رو پاک می‌کنه\n"
    "• /joke — یه جوک تصادفی\n\n"
    "من رو همچنین می‌تونی به یه گروه اضافه کنی تا اونجا هم مدیریت گروه و چت AI رو انجام بدم."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("joke"))
async def cmd_joke(message: Message) -> None:
    await message.answer(random_joke())


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    if message.from_user is None:
        return
    await db.clear_history(message.chat.id, message.from_user.id)
    await message.answer("✅ حافظه‌ی مکالمه پاک شد. از اول شروع می‌کنیم!")


@router.message()
async def handle_private_message(
    message: Message,
    ai_router: AIRouter,
    rate_limiter: RateLimitMiddleware,
    is_repeated_spam: bool = False,
) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return

    text = message.text or ""
    if not text.strip():
        return

    if not rate_limiter.is_ai_request_allowed(message.from_user.id):
        await message.answer(
            "⏳ یکم آروم‌تر! بذار نفس بکشم، چند ثانیه دیگه دوباره امتحان کن."
        )
        return

    history = await db.get_recent_history(
        message.chat.id, message.from_user.id, config.history_limit
    )

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    response_text = await ai_router.get_ai_response(text, history)

    await db.add_history_message(message.chat.id, message.from_user.id, "user", text)
    await db.add_history_message(
        message.chat.id, message.from_user.id, "assistant", response_text
    )

    await message.answer(response_text)