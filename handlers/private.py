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
from services.metrics import metrics
from utils.filters import IsPrivateChat
from utils.helpers import random_joke

logger = logging.getLogger(__name__)

router = Router(name="private")
router.message.filter(IsPrivateChat())

WELCOME_TEXT = (
    "سلام! من هوشو👾 هستم 🤖\n\n"
    "اینجا توی پیوی می‌تونی هر چی دوست داری بپرسی، با هم چت کنیم. "
    "لازم نیست چیز خاصی بنویسی یا منشن کنی، فقط پیام بده!\n\n"
    "دستورهای مفید:\n"
    "/about — درباره من و امکانات‌ام\n"
    "/joke — یه جوک بگم 😄\n"
    "/reset — تاریخچه‌ی چتمون رو پاک کن و از اول شروع کن\n"
    "/help — راهنما\n"
    "/stats — آمار سرویس‌های من"
)

ABOUT_TEXT = (
    "👋 <b>درباره من</b>\n\n"
    "من <b>هوشو👾</b> هستم، یک دستیار هوشمند مبتنی بر هوش مصنوعی.\n\n"
    "<b>🚀 امکانات:</b>\n"
    "• چت هوشمند به فارسی (Groq + Gemini)\n"
    "• مدیریت گروه‌های تلگرام\n"
    "• حذف خودکار پیام‌های ممنوعه و لینک‌ها\n"
    "• سیستم اخطار و بن خودکار\n"
    "• یادآورهای شخصی\n"
    "• خلاصه‌سازی گفتگو\n"
    "• جوک‌های فارسی\n\n"
    "<b>🤖 تکنولوژی:</b>\n"
    "• Python 3.11+\n"
    "• aiogram 3.7\n"
    "• Groq API (Fast LLM)\n"
    "• Google Gemini\n"
    "• SQLite Database\n\n"
    "<b>⚙️ حالت‌های فعال:</b>\n"
    f"• درخواست‌های AI: {metrics.ai_requests}\n"
    f"• خطاها: {metrics.ai_errors}\n"
    f"• میانگین تأخیر: {round(sum(metrics.ai_latencies) / max(len(metrics.ai_latencies), 1), 2)}ms\n\n"
    "<b>💡 نکته:</b> من رایگان هستم و همیشه آماده کمک!"
)

HELP_TEXT = (
    "📋 راهنمای استفاده در پیوی:\n\n"
    "• هر پیامی بفرستی، باهات چت می‌کنم\n"
    "• /reset — حافظه‌ی مکالمه رو پاک می‌کنه\n"
    "• /joke — یه جوک تصادفی\n"
    "• /about — درباره من\n"
    "• /stats — آمار سرویس‌های من\n\n"
    "من رو همچنین می‌تونی به یه گروه اضافه کنی تا اونجا هم مدیریت گروه و چت AI رو انجام بدم."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode="HTML")


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    """Show about information with current metrics."""
    await message.answer(ABOUT_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("joke"))
async def cmd_joke(message: Message) -> None:
    await message.answer(random_joke())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show service metrics."""
    stats = metrics.get_stats()
    text = (
        "📊 <b>آمار سرویس‌های هوشو👾</b>\n\n"
        f"<b>درخواست‌های AI:</b>\n"
        f"• کل: {stats['total_ai_requests']}\n"
        f"• خطا: {stats['ai_errors']}\n"
        f"• Timeout: {stats['ai_timeouts']}\n"
        f"• نرخ خطا: {stats['error_rate_percent']}%\n\n"
        f"<b>سرعت (Latency):</b>\n"
        f"• میانگین: {stats['avg_latency_ms']}ms\n"
        f"• حداقل: {stats['min_latency_ms']}ms\n"
        f"• حداکثر: {stats['max_latency_ms']}ms\n\n"
        f"<b>Groq:</b>\n"
        f"• درخواست: {stats['groq_requests']}\n"
        f"• موفقیت: {stats['groq_success_rate_percent']}%\n\n"
        f"<b>Gemini:</b>\n"
        f"• درخواست: {stats['gemini_requests']}\n"
        f"• موفقیت: {stats['gemini_success_rate_percent']}%\n\n"
        f"<b>⏱ آپ‌تایم:</b> {stats['uptime_since']}"
    )
    await message.answer(text, parse_mode="HTML")


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
