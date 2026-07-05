"""
services/cleanup_service.py
Background task for cleaning up old data from database.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import database.db as db
from config import config

logger = logging.getLogger(__name__)

_CLEANUP_INTERVAL_SECONDS = 86400  # Run once per day


async def cleanup_loop() -> None:
    """Periodically clean up old data from database."""
    logger.info("Cleanup task started")
    while True:
        try:
            await _perform_cleanup()
        except Exception as exc:
            logger.error("Cleanup task error: %s", exc, exc_info=True)
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)


async def _perform_cleanup() -> None:
    """Perform all cleanup operations."""
    now = datetime.now(timezone.utc)
    
    # Delete old chat history
    cutoff_history = now - timedelta(days=config.history_retention_days)
    deleted_history = await db.delete_old_history(cutoff_history.isoformat())
    logger.info(f"Cleaned up {deleted_history} old chat history records")
    
    # Delete old group logs
    cutoff_logs = now - timedelta(days=config.group_log_retention_days)
    deleted_logs = await db.delete_old_group_logs(cutoff_logs.isoformat())
    logger.info(f"Cleaned up {deleted_logs} old group log records")
