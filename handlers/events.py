"""
handlers/events.py
Handles group membership events: member joins and member leaves.
"""

import logging

from aiogram import Router
from aiogram.types import Message

from utils.filters import IsGroupChat
from utils.helpers import mention_html, random_goodbye, random_welcome

logger = logging.getLogger(__name__)

router = Router(name="events")
router.message.filter(IsGroupChat())


@router.message(lambda message: bool(message.new_chat_members))
async def on_member_join(message: Message) -> None:
    for new_member in message.new_chat_members:
        if new_member.is_bot:
            continue
        text = random_welcome(mention_html(new_member))
        await message.answer(text, parse_mode="HTML")


@router.message(lambda message: message.left_chat_member is not None)
async def on_member_leave(message: Message) -> None:
    left_member = message.left_chat_member
    if left_member is None or left_member.is_bot:
        return
    text = random_goodbye(mention_html(left_member))
    await message.answer(text, parse_mode="HTML")