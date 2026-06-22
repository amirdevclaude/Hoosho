"""
services/moderation_actions.py
منطق اجرای دستورات مدیریتی: ban, kick, mute, unmute, warn, delete.
"""

import logging
from datetime import timedelta
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatPermissions, User

import database.db as db
from config import config
from utils.helpers import format_duration, mention_html, utc_now

logger = logging.getLogger(__name__)

FULL_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=False,
    can_manage_topics=False,
)

MUTED_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
    can_manage_topics=False,
)


async def bot_has_permission(bot: Bot, chat_id: int, permission: str) -> bool:
    bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
    return bool(getattr(bot_member, permission, False))


async def execute_ban(bot: Bot, chat_id: int, target: User) -> str:
    if not await bot_has_permission(bot, chat_id, "can_restrict_members"):
        return "❗️ ربات دسترسی بن کردن اعضا رو نداره."
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=target.id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to ban user %s: %s", target.id, exc)
        return f"❗️ خطا در بن کردن: {exc}"
    return f"🔨 {mention_html(target)} برای همیشه بن شد."


async def execute_kick(bot: Bot, chat_id: int, target: User) -> str:
    if not await bot_has_permission(bot, chat_id, "can_restrict_members"):
        return "❗️ ربات دسترسی اخراج اعضا رو نداره."
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=target.id)
        await bot.unban_chat_member(chat_id=chat_id, user_id=target.id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to kick user %s: %s", target.id, exc)
        return f"❗️ خطا در اخراج: {exc}"
    return f"👢 {mention_html(target)} از گروه اخراج شد (می‌تونه دوباره عضو شه)."


async def execute_mute(
    bot: Bot, chat_id: int, target: User, duration_minutes: Optional[int] = None
) -> str:
    if not await bot_has_permission(bot, chat_id, "can_restrict_members"):
        return "❗️ ربات دسترسی محدود کردن اعضا رو نداره."

    minutes = duration_minutes if duration_minutes and duration_minutes > 0 else config.default_mute_minutes
    delta = timedelta(minutes=minutes)
    until_dt = utc_now() + delta

    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target.id,
            permissions=MUTED_PERMISSIONS,
            until_date=until_dt,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to mute user %s: %s", target.id, exc)
        return f"❗️ خطا در میوت کردن: {exc}"

    await db.set_mute(target.id, chat_id, until_dt.isoformat())
    return f"🔇 {mention_html(target)} برای مدت {format_duration(delta)} میوت شد."


async def execute_unmute(bot: Bot, chat_id: int, target: User) -> str:
    if not await bot_has_permission(bot, chat_id, "can_restrict_members"):
        return "❗️ ربات دسترسی لازم رو نداره."
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id, user_id=target.id, permissions=FULL_PERMISSIONS
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to unmute user %s: %s", target.id, exc)
        return f"❗️ خطا در آنمیوت کردن: {exc}"

    await db.clear_mute(target.id, chat_id)
    return f"🔊 {mention_html(target)} آنمیوت شد."


async def execute_warn(
    bot: Bot, chat_id: int, target: User, reason: Optional[str] = None
) -> str:
    clean_reason = (reason or "بدون دلیل").strip()
    new_count = await db.add_warn(target.id, chat_id, clean_reason)

    if new_count >= config.max_warns_before_ban:
        if not await bot_has_permission(bot, chat_id, "can_restrict_members"):
            return (
                f"⚠️ {mention_html(target)} به {new_count} اخطار رسید "
                f"اما ربات دسترسی بن کردن نداره!"
            )
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=target.id)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning("Failed to auto-ban user %s: %s", target.id, exc)
            return f"❗️ خطا در بن خودکار: {exc}"

        await db.reset_warns(target.id, chat_id)
        return (
            f"🚫 {mention_html(target)} به {new_count} اخطار رسید "
            f"و به طور خودکار بن شد."
        )

    return (
        f"⚠️ {mention_html(target)} اخطار گرفت.\n"
        f"دلیل: {clean_reason}\n"
        f"تعداد اخطار: {new_count}/{config.max_warns_before_ban}"
    )


async def execute_delete(bot: Bot, chat_id: int, message_id: int) -> Optional[str]:
    if not await bot_has_permission(bot, chat_id, "can_delete_messages"):
        return "❗️ ربات دسترسی حذف پیام رو نداره."
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to delete message: %s", exc)
        return f"❗️ خطا در حذف پیام: {exc}"
    return None