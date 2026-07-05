"""
handlers/group_features.py
فاز ۲ بخش دو:
  - فیلتر خودکار کلمات ممنوعه و لینک‌های خارجی
  - /summary — خلاصه‌ی ۵۰ پیام آخر گروه با AI
  - /remind — یادآور شخصی با تایمر
  - لاگ پیام‌های گروه (برای /summary)
"""

import asyncio
import logging
import re
from datetime import timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import database.db as db
import services.moderation_actions as actions
from config import config
from services.ai_router import AIRouter
from utils.filters import IsAdminOrOwner, IsGroupChat
from utils.helpers import mention_html, parse_duration, utc_now

logger = logging.getLogger(__name__)

router = Router(name="group_features")
router.message.filter(IsGroupChat())

_URL_RE = re.compile(
    r"(https?://|t\.me/|@\w{5,}|bit\.ly|tinyurl\.com)",
    re.IGNORECASE,
)

_is_admin_check = IsAdminOrOwner(config.admin_ids)


@router.message(F.text)
async def log_group_message(
    message: Message,
) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return

    text = message.text or ""
    user_name = message.from_user.full_name or message.from_user.first_name or "کاربر"

    settings = await db.get_group_settings(message.chat.id)

    # فیلتر کلمات ممنوعه
    if settings["filter_bad_words"]:
        banned = await db.get_banned_words(message.chat.id)
        lowered = text.lower()
        for word in banned:
            if word in lowered:
                try:
                    await message.delete()
                except (TelegramBadRequest, TelegramForbiddenError):
                    pass
                warn_count = await db.add_warn(
                    message.from_user.id, message.chat.id, f"کلمه‌ی ممنوعه: {word}"
                )
                notice = await message.answer(
                    f"⚠️ {mention_html(message.from_user)} پیامت حاوی کلمه‌ی ممنوعه بود و حذف شد.\n"
                    f"اخطار: {warn_count}/{config.max_warns_before_ban}",
                    parse_mode="HTML",
                )
                await asyncio.sleep(5)
                try:
                    await notice.delete()
                except Exception:
                    pass
                return

    # فیلتر لینک
    if settings["filter_links"] and not await _is_admin_check(message):
        if _URL_RE.search(text):
            try:
                await message.delete()
            except (TelegramBadRequest, TelegramForbiddenError):
                pass
            warn_count = await db.add_warn(
                message.from_user.id, message.chat.id, "ارسال لینک ممنوعه"
            )
            notice = await message.answer(
                f"🔗 {mention_html(message.from_user)} ارسال لینک در این گروه مجاز نیست.\n"
                f"اخطار: {warn_count}/{config.max_warns_before_ban}",
                parse_mode="HTML",
            )
            await asyncio.sleep(5)
            try:
                await notice.delete()
            except Exception:
                pass
            return

    # لاگ پیام برای /summary
    if text.strip():
        await db.add_group_log(
            message.chat.id,
            message.from_user.id,
            user_name,
            text.strip(),
        )


@router.message(Command("summary"))
async def cmd_summary(message: Message, ai_router: AIRouter) -> None:
    logs = await db.get_recent_group_log(message.chat.id, limit=50)

    if not logs or len(logs) < 5:
        await message.reply("🛭 پیام‌های کافی برای خلاصه کردن وجود نداره (حداقل ۵ تا).")
        return

    transcript = "\n".join(f"{name}: {content}" for name, content in logs)
    prompt = (
        f"این مکالمه‌ی یه گروه تلگرامیه. لطفاً یه خلاصه‌ی کوتاه و مفید "
        f"به فارسی بده که بگه چه موضوعاتی مطرح شده:\n\n{transcript}"
    )

    processing_msg = await message.reply("⏳ در حال خلاصه کردن گفتگوها...")
    summary = await ai_router.get_ai_response(prompt, [])

    try:
        await processing_msg.delete()
    except Exception:
        pass

    await message.reply(
        f"📋 <b>خلاصه‌ی {len(logs)} پیام آخر:</b>\n\n{summary}",
        parse_mode="HTML",
    )


@router.message(Command("remind"))
async def cmd_remind(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip()
    if not args:
        await message.reply(
            "❎️ فرمت درست:\n"
            "<code>/remind 30m متن یادآور</code>\n"
            "<code>/remind 2h سر زدن به پروژه</code>\n"
            "<code>/remind 1d جلسه با تیم</code>",
            parse_mode="HTML",
        )
        return

    parts = args.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            "❎️ متن یادآور رو هم بنویس.\n"
            "مثال: <code>/remind 1h بررسی پروژه</code>",
            parse_mode="HTML",
        )
        return

    duration_str, reminder_text = parts[0], parts[1].strip()
    delta = parse_duration(duration_str)

    if delta is None:
        await message.reply(
            "❎️ فرمت زمان نادرسته.\n"
            "مثال‌های درست: <code>30m</code>ی ۲h</code>ی <code>1d</code>",
            parse_mode="HTML",
        )
        return

    if delta > timedelta(days=30):
        await message.reply("❎️ حداکثر مدت یادآور ۳۰ روزه.")
        return

    due_at = utc_now() + delta
    await db.add_reminder(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text=reminder_text,
        due_at_iso=due_at.isoformat(),
    )

    from utils.helpers import format_duration
    await message.reply(
        f"⏰ یادآور ثبت شد!\n"
        f"📝 موضوع: {reminder_text}\n"
        f"📋 بعد از: {format_duration(delta)}",
    )
