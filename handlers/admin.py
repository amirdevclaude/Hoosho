"""
handlers/admin.py
فاز ۲: کامندهای جدید: /pin, /unpin, /ro, /unro, /purge,
/adminlist, /id, /setwelcome, /addfilter, /rmfilter, /filters, /filterlinks
"""

import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import database.db as db
import services.moderation_actions as actions
from config import config
from utils.filters import HasReply, IsAdminOrOwner, IsGroupChat
from utils.helpers import mention_html, parse_duration

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsGroupChat())


async def _resolve_target(message: Message):
    if message.reply_to_message is None:
        await message.reply("❗️ این دستور رو باید روی پیام فرد مورد نظر ریپلای کنی.")
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
    result = await actions.execute_ban(message.bot, message.chat.id, target_message.from_user)
    await message.reply(result, parse_mode="HTML")


@router.message(Command("kick"), IsAdminOrOwner(config.admin_ids))
async def cmd_kick(message: Message) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    result = await actions.execute_kick(message.bot, message.chat.id, target_message.from_user)
    await message.reply(result, parse_mode="HTML")


@router.message(Command("mute"), IsAdminOrOwner(config.admin_ids))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return

    duration_arg = (command.args or "").strip()
    duration_minutes = None
    if duration_arg:
        delta = parse_duration(duration_arg)
        if delta is None:
            await message.reply("❗️ فرمت زمان نامعتبره. مثال: 30m، 1h، 2d")
            return
        duration_minutes = int(delta.total_seconds() // 60)

    result = await actions.execute_mute(
        message.bot, message.chat.id, target_message.from_user, duration_minutes
    )
    await message.reply(result, parse_mode="HTML")


@router.message(Command("unmute"), IsAdminOrOwner(config.admin_ids))
async def cmd_unmute(message: Message) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    result = await actions.execute_unmute(message.bot, message.chat.id, target_message.from_user)
    await message.reply(result, parse_mode="HTML")


@router.message(Command("warn"), IsAdminOrOwner(config.admin_ids))
async def cmd_warn(message: Message, command: CommandObject) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    reason = (command.args or "").strip() or None
    result = await actions.execute_warn(
        message.bot, message.chat.id, target_message.from_user, reason
    )
    await message.reply(result, parse_mode="HTML")


@router.message(Command("warns"))
async def cmd_warns(message: Message) -> None:
    target_message = await _resolve_target(message)
    if target_message is None:
        return
    count = await db.get_warns(target_message.from_user.id, message.chat.id)
    await message.reply(
        f"📋 {mention_html(target_message.from_user)} "
        f"تعداد اخطار: {count}/{config.max_warns_before_ban}",
        parse_mode="HTML",
    )


@router.message(Command("del"), IsAdminOrOwner(config.admin_ids), HasReply())
async def cmd_del(message: Message) -> None:
    error = await actions.execute_delete(
        message.bot, message.chat.id, message.reply_to_message.message_id
    )
    if error:
        await message.reply(error)
        return
    try:
        await message.delete()
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Failed to delete /del command message: %s", exc)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    try:
        member_count = await message.bot.get_chat_member_count(chat_id=message.chat.id)
    except (TelegramBadRequest, TelegramForbiddenError):
        member_count = "نامشخص"

    total_warns = await db.count_total_warns(message.chat.id)
    settings = await db.get_group_settings(message.chat.id)

    text = (
        f"📊 <b>آمار گروه «{message.chat.title}»</b>\n\n"
        f"👥 تعداد اعضا: {member_count}\n"
        f"⚠️ مجموع اخطارهای فعال: {total_warns}\n"
        f"🔒 حالت قفل: {'فعال' if settings['is_locked'] else 'غیرفعال'}\n"
        f"🔗 فیلتر لینک: {'فعال' if settings['filter_links'] else 'غیرفعال'}\n"
        f"🤬 فیلتر کلمات بد: {'فعال' if settings['filter_bad_words'] else 'غیرفعال'}\n"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("pin"), IsAdminOrOwner(config.admin_ids), HasReply())
async def cmd_pin(message: Message) -> None:
    try:
        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
            disable_notification=False,
        )
        await message.reply("📌 پیام پین شد.")
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.reply(f"❗️ خطا در پین کردن: {exc}")


@router.message(Command("unpin"), IsAdminOrOwner(config.admin_ids))
async def cmd_unpin(message: Message) -> None:
    try:
        if message.reply_to_message:
            await message.bot.unpin_chat_message(
                chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id,
            )
        else:
            await message.bot.unpin_chat_message(chat_id=message.chat.id)
        await message.reply("📌 پین برداشته شد.")
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.reply(f"❗️ خطا در آنپین کردن: {exc}")


@router.message(Command("ro"), IsAdminOrOwner(config.admin_ids))
async def cmd_ro(message: Message) -> None:
    try:
        await message.bot.set_chat_permissions(
            chat_id=message.chat.id,
            permissions=actions.MUTED_PERMISSIONS,
        )
        await db.set_group_lock(message.chat.id, True)
        await message.reply("🔒 گروه قفل شد. فقط ادمین‌ها می‌تونن پیام بفرستن.")
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.reply(f"❗️ خطا در قفل کردن گروه: {exc}")


@router.message(Command("unro"), IsAdminOrOwner(config.admin_ids))
async def cmd_unro(message: Message) -> None:
    try:
        await message.bot.set_chat_permissions(
            chat_id=message.chat.id,
            permissions=actions.FULL_PERMISSIONS,
        )
        await db.set_group_lock(message.chat.id, False)
        await message.reply("🔓 قفل گروه برداشته شد.")
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.reply(f"❗️ خطا در باز کردن قفل: {exc}")


@router.message(Command("purge"), IsAdminOrOwner(config.admin_ids), HasReply())
async def cmd_purge(message: Message) -> None:
    start_id = message.reply_to_message.message_id
    end_id = message.message_id
    deleted = 0
    failed = 0

    for msg_id in range(start_id, end_id + 1):
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            deleted += 1
        except (TelegramBadRequest, TelegramForbiddenError):
            failed += 1

    import asyncio
    notice = await message.answer(
        f"🗑 <b>{deleted}</b> پیام حذف شد."
        + (f" ({failed} پیام قابل حذف نبود)" if failed else ""),
        parse_mode="HTML",
    )
    await asyncio.sleep(5)
    try:
        await notice.delete()
    except Exception:
        pass


@router.message(Command("adminlist"))
async def cmd_adminlist(message: Message) -> None:
    try:
        admins = await message.bot.get_chat_administrators(chat_id=message.chat.id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.reply(f"❗️ خطا: {exc}")
        return

    lines = [f"👑 <b>ادمین‌های «{message.chat.title}»</b>\n"]
    for i, admin in enumerate(admins, 1):
        user = admin.user
        if user.is_bot:
            label = "🤖"
        elif admin.status == "creator":
            label = "👑"
        else:
            label = "⭐️"
        name = user.full_name or user.first_name or "بدون اسم"
        username = f" (@{user.username})" if user.username else ""
        lines.append(f"{i}. {label} {name}{username}")

    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    lines = [
        f"💬 <b>Chat ID:</b> <code>{message.chat.id}</code>",
        f"👤 <b>Your ID:</b> <code>{message.from_user.id}</code>",
    ]
    if message.reply_to_message and message.reply_to_message.from_user:
        t = message.reply_to_message.from_user
        lines.append(f"👤 <b>Target ID:</b> <code>{t.id}</code> ({mention_html(t)})")
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("setwelcome"), IsAdminOrOwner(config.admin_ids))
async def cmd_set_welcome(message: Message, command: CommandObject) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.reply(
            "❗️ متن پیام خوش‌آمد رو بعد از دستور بنویس.\n"
            "مثال: <code>/setwelcome سلام {name}! خوش اومدی 🎉</code>\n\n"
            "از <code>{name}</code> برای نام کاربر استفاده کن.",
            parse_mode="HTML",
        )
        return
    await db.set_welcome_message(message.chat.id, text)
    await message.reply(f"✅ پیام خوش‌آمد تنظیم شد:\n\n{text}")


@router.message(Command("addfilter"), IsAdminOrOwner(config.admin_ids))
async def cmd_add_filter(message: Message, command: CommandObject) -> None:
    word = (command.args or "").strip().lower()
    if not word:
        await message.reply("❗️ مثال: <code>/addfilter بدگویی</code>", parse_mode="HTML")
        return
    await db.add_banned_word(message.chat.id, word)
    await message.reply(f"✅ «{word}» به لیست فیلتر اضافه شد.")


@router.message(Command("rmfilter"), IsAdminOrOwner(config.admin_ids))
async def cmd_remove_filter(message: Message, command: CommandObject) -> None:
    word = (command.args or "").strip().lower()
    if not word:
        await message.reply("❗️ مثال: <code>/rmfilter بدگویی</code>", parse_mode="HTML")
        return
    await db.remove_banned_word(message.chat.id, word)
    await message.reply(f"✅ «{word}» از لیست فیلتر حذف شد.")


@router.message(Command("filters"))
async def cmd_list_filters(message: Message) -> None:
    words = await db.get_banned_words(message.chat.id)
    if not words:
        await message.reply("📋 هیچ کلمه‌ی ممنوعه‌ای تنظیم نشده.")
        return
    text = "📋 <b>کلمات ممنوعه:</b>\n" + "\n".join(f"• {w}" for w in words)
    await message.reply(text, parse_mode="HTML")


@router.message(Command("filterlinks"), IsAdminOrOwner(config.admin_ids))
async def cmd_filter_links(message: Message, command: CommandObject) -> None:
    arg = (command.args or "").strip().lower()
    if arg not in ("on", "off"):
        await message.reply(
            "❗️ استفاده: <code>/filterlinks on</code> یا <code>/filterlinks off</code>",
            parse_mode="HTML",
        )
        return
    enabled = arg == "on"
    await db.set_group_filter(message.chat.id, "filter_links", enabled)
    status = "✅ فعال" if enabled else "❌ غیرفعال"
    await message.reply(f"🔗 فیلتر لینک‌های خارجی: {status}")