"""
handlers/callbacks.py
هندلر دکمه‌های inline keyboard.
"""

import logging

from aiogram import Router
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

router = Router(name="callbacks")


@router.callback_query(lambda c: c.data == "show_rules")
async def cb_show_rules(callback: CallbackQuery) -> None:
    await callback.answer(
        "قوانین گروه رو از ادمین‌ها بخواه یا پیام پین‌شده‌ی گروه رو چک کن! 📋",
        show_alert=True,
    )


@router.callback_query(lambda c: c.data == "show_help")
async def cb_show_help(callback: CallbackQuery) -> None:
    text = (
        "🤖 راهنمای هوشو:\n\n"
        "• @mention کن یا ریپلای کن تا باهات چت کنم\n"
        "• /joke — جوک تصادفی\n"
        "• /stats — آمار گروه\n"
        "• /adminlist — لیست ادمین‌ها\n"
        "• /id — آیدی گروه و خودت\n\n"
        "ادمین‌ها:\n"
        "• /ban /kick /mute /unmute /warn\n"
        "• /pin /unpin — پین پیام\n"
        "• /ro /unro — قفل/بازکردن گروه\n"
        "• /purge — حذف دسته‌ای\n"
        "• /setwelcome — پیام خوش‌آمد سفارشی\n"
        "• /addfilter /rmfilter /filters — فیلتر کلمات\n"
        "• /filterlinks on|off — فیلتر لینک"
    )
    await callback.answer(text, show_alert=True)