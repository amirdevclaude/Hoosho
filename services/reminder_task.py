"""
services/reminder_task.py
تسک بک‌گراند که هر دقیقه یادآورهای سررسیده رو چک می‌کنه و پیام می‌فرسته.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import database.db as db
from utils.helpers import utc_now

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 60


async def reminder_loop(bot: Bot) -> None:
    logger.info("Reminder task started")
    while True:
        try:
            await _fire_due_reminders(bot)
        except Exception as exc:
            logger.error("Reminder loop error: %s", exc, exc_info=True)
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)


async def _fire_due_reminders(bot: Bot) -> None:
    now_iso = utc_now().isoformat()
    due = await db.get_due_reminders(now_iso)

    for reminder in due:
        try:
            await bot.send_message(
                chat_id=reminder["chat_id"],
                text=(
                    f"⏰ <b>یادآور!</b>\n\n"
                    f"📝 {reminder['text']}"
                ),
                parse_mode="HTML",
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning("Failed to send reminder id=%s: %s", reminder["id"], exc)
        except Exception as exc:
            logger.error("Unexpected error sending reminder id=%s: %s", reminder["id"], exc)
        finally:
            await db.mark_reminder_fired(reminder["id"])