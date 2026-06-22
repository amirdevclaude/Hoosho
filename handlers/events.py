"""
handlers/events.py
فاز ۲: پشتیبانی از پیام خوش‌آمد سفارشی + دکمه‌های inline.
"""

import logging

from aiogram import Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import database.db as db
from utils.filters import IsGroupChat
from utils.helpers import mention_html, random_goodbye, random_welcome

logger = logging.getLogger(__name__)

router = Router(name="events")
router.message.filter(IsGroupChat())


def _welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 قوانین گروه", callback_data="show_rules"),
                InlineKeyboardButton(text="🤖 راهنمای ربات", callback_data="show_help"),
            ]
        ]
    )


@router.message(lambda message: bool(message.new_chat_members))
async def on_member_join(message: Message) -> None:
    for new_member in message.new_chat_members:
        if new_member.is_bot:
            continue
        mention = mention_html(new_member)
        custom = await db.get_welcome_message(message.chat.id)
        if custom:
            text = custom.replace("{name}", mention)
        else:
            text = random_welcome(mention)
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=_welcome_keyboard(),
        )


@router.message(lambda message: message.left_chat_member is not None)
async def on_member_leave(message: Message) -> None:
    left_member = message.left_chat_member
    if left_member is None or left_member.is_bot:
        return
    text = random_goodbye(mention_html(left_member))
    await message.answer(text, parse_mode="HTML")