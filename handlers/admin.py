"""
handlers/admin.py
Admin-only group management commands: /ban, /kick, /mute, /unmute,
/warn, /warns, /del, /stats.
"""

import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions, Message

import database.db as db
from config import config
from utils.filters import HasReply, IsAdminOrOwner, IsGroupChat
from utils.helpers import format_duration, mention_html, parse_duration, utc_now

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsGroupChat())

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


async def _bot_has_permission(message: Message, permission: str) -> bool:
    """Check whether the bot itself has the given admin permission in this chat."""
    bot_member = await message.bot.get_chat_member(
        chat_id=message.chat.id, user_id=message.bot.id
    )
    return bool(getattr(bot_member, permission, False))


async def _resolve_target(message: Message):
    """Return the replied-to message, or None and send an error if there isn't one."""
    if message.reply_to_message is None:
        await message.reply(
            "❗️ این دستور رو باید روی پیام فرد مورد نظر ریپلای کنی."
        )
        return None
    if message.reply_to_message.from_user is None:
        await message.reply("❗️ نمی‌تونم فرستنده‌ی این پیام رو شناسایی کنم.")
        return None
    return message.reply_to_message


@router.message(Command("ban"), IsAdminOrOwner(config.admin_ids))
async def cmd_ban(message: Message) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    target = target_message.from_user

    if not await _bot_has_permission(message, "can_restrict_members"):
        await message.reply("❗️ ربات دسترسی بن کردن اعضا رو نداره. لطفاً دسترسی‌های ادمین رو بررسی کن.")
        return

    try:
        await message.bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to ban user %s: %s", target.id, exc)
        await message.reply(f"❗️ خطا در بن کردن کاربر: {exc}")
        return

    await message.reply(f"🔨 {mention_html(target)} برای همیشه بن شد.", parse_mode="HTML")


@router.message(Command("kick"), IsAdminOrOwner(config.admin_ids))
async def cmd_kick(message: Message) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    target = target_message.from_user

    if not await _bot_has_permission(message, "can_restrict_members"):
        await message.reply("❗️ ربات دسترسی اخراج اعضا رو نداره. لطفاً دسترسی‌های ادمین رو بررسی کن.")
        return

    try:
        await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target.id)
        await message.bot.unban_chat_member(chat_id=message.chat.id, user_id=target.id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to kick user %s: %s", target.id, exc)
        await message.reply(f"❗️ خطا در اخراج کاربر: {exc}")
        return

    await message.reply(f"👢 {mention_html(target)} از گروه اخراج شد (می‌تونه دوباره عضو شه).", parse_mode="HTML")


@router.message(Command("mute"), IsAdminOrOwner(config.admin_ids))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    target = target_message.from_user

    if not await _bot_has_permission(message, "can_restrict_members"):
        await message.reply("❗️ ربات دسترسی محدود کردن اعضا رو نداره. لطفاً دسترسی‌های ادمین رو بررسی کن.")
        return

    duration_arg = (command.args or "").strip()
    if duration_arg:
        delta = parse_duration(duration_arg)
        if delta is None:
            await message.reply(
                "❗️ فرمت زمان نامعتبره. مثال‌های درست: 30m، 1h، 2d"
            )
            return
    else:
        from datetime import timedelta
        delta = timedelta(minutes=config.default_mute_minutes)

    until_dt = utc_now() + delta

    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=MUTED_PERMISSIONS,
            until_date=until_dt,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to mute user %s: %s", target.id, exc)
        await message.reply(f"❗️ خطا در میوت کردن کاربر: {exc}")
        return

    await db.set_mute(target.id, message.chat.id, until_dt.isoformat())

    await message.reply(
        f"🔇 {mention_html(target)} برای مدت {format_duration(delta)} میوت شد.",
        parse_mode="HTML",
    )


@router.message(Command("unmute"), IsAdminOrOwner(config.admin_ids))
async def cmd_unmute(message: Message) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    target = target_message.from_user

    if not await _bot_has_permission(message, "can_restrict_members"):
        await message.reply("❗️ ربات دسترسی لازم رو نداره. لطفاً دسترسی‌های ادمین رو بررسی کن.")
        return

    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=FULL_PERMISSIONS,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to unmute user %s: %s", target.id, exc)
        await message.reply(f"❗️ خطا در آنمیوت کردن کاربر: {exc}")
        return

    await db.clear_mute(target.id, message.chat.id)
    await message.reply(f"🔊 {mention_html(target)} آنمیوت شد.", parse_mode="HTML")


@router.message(Command("warn"), IsAdminOrOwner(config.admin_ids))
async def cmd_warn(message: Message, command: CommandObject) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    target = target_message.from_user

    reason = (command.args or "بدون دلیل").strip()
    new_count = await db.add_warn(target.id, message.chat.id, reason)

    if new_count >= config.max_warns_before_ban:
        if not await _bot_has_permission(message, "can_restrict_members"):
            await message.reply(
                f"⚠️ {mention_html(target)} به {new_count} اخطار رسید اما ربات "
                f"دسترسی بن کردن نداره!",
                parse_mode="HTML",
            )
            return
        try:
            await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target.id)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning("Failed to auto-ban user %s: %s", target.id, exc)
            await message.reply(f"❗️ خطا در بن خودکار: {exc}")
            return

        await db.reset_warns(target.id, message.chat.id)
        await message.reply(
            f"🚫 {mention_html(target)} به {new_count} اخطار رسید و به طور خودکار "
            f"بن شد.",
            parse_mode="HTML",
        )
        return

    await message.reply(
        f"⚠️ {mention_html(target)} اخطار گرفت.\n"
        f"دلیل: {reason}\n"
        f"تعداد اخطار: {new_count}/{config.max_warns_before_ban}",
        parse_mode="HTML",
    )


@router.message(Command("warns"))
async def cmd_warns(message: Message) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    target = target_message.from_user

    count = await db.get_warns(target.id, message.chat.id)
    await message.reply(
        f"📋 {mention_html(target)} تعداد اخطار: {count}/{config.max_warns_before_ban}",
        parse_mode="HTML",
    )


@router.message(Command("del"), IsAdminOrOwner(config.admin_ids), HasReply())
async def cmd_del(message: Message) -> None:
    if not await _bot_has_permission(message, "can_delete_messages"):
        await message.reply("❗️ ربات دسترسی حذف پیام رو نداره.")
        return

    try:
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
        )
        await message.delete()
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to delete message: %s", exc)
        await message.reply(f"❗️ خطا در حذف پیام: {exc}")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    try:
        member_count = await message.bot.get_chat_member_count(chat_id=message.chat.id)
    except (TelegramBadRequest, TelegramForbiddenError):
        member_count = "نامشخص"

    total_warns = await db.count_total_warns(message.chat.id)

    text = (
        f"📊 آمار گروه «{message.chat.title}»\n\n"
        f"👥 تعداد اعضا: {member_count}\n"
        f"⚠️ مجموع اخطارهای فعال: {total_warns}\n"
    )
    await message.reply(text)