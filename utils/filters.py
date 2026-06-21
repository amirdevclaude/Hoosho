"""
utils/filters.py
Custom aiogram 3.x filters used across handlers.
"""

from typing import List, Optional

from aiogram.filters import BaseFilter
from aiogram.types import Message, ChatMemberAdministrator, ChatMemberOwner


class IsGroupChat(BaseFilter):
    """Allow the update only inside groups or supergroups (not private chats)."""

    async def __call__(self, message: Message) -> bool:
        return message.chat.type in ("group", "supergroup")


class IsPrivateChat(BaseFilter):
    """Allow the update only inside a private (1-on-1) chat with the bot."""

    async def __call__(self, message: Message) -> bool:
        return message.chat.type == "private"


class IsAdminOrOwner(BaseFilter):
    """Allow the update only if the sender is a Telegram chat admin/owner OR
    their user_id is listed in the bot's ADMIN_IDS config."""

    def __init__(self, admin_ids: Optional[List[int]] = None) -> None:
        self.admin_ids = admin_ids or []

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return False

        if message.from_user.id in self.admin_ids:
            return True

        member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
        )
        return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))


class HasReply(BaseFilter):
    """Allow the update only if the message is a reply to another message."""

    async def __call__(self, message: Message) -> bool:
        return message.reply_to_message is not None