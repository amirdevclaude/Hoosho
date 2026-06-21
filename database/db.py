"""
database/db.py
Async SQLite data access layer built on aiosqlite.

A single module-level connection is opened on startup (init_db) and reused
for the lifetime of the process. All public functions are coroutine
functions and safe to call concurrently from different handlers because
aiosqlite serializes access internally and we additionally guard writes
with an asyncio.Lock.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import aiosqlite

logger = logging.getLogger(__name__)

_connection: Optional[aiosqlite.Connection] = None
_lock = asyncio.Lock()


async def init_db(db_path: str) -> None:
    """Open the database connection and create tables if they do not exist."""
    global _connection
    _connection = await aiosqlite.connect(db_path)
    _connection.row_factory = aiosqlite.Row

    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS warns (
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            reason TEXT,
            updated_at TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
        """
    )

    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mutes (
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            until TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
        """
    )

    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """
    )

    await _connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_history_user "
        "ON chat_history (chat_id, user_id, created_at)"
    )

    await _connection.commit()
    logger.info("Database initialized at %s", db_path)


async def close_db() -> None:
    """Close the database connection gracefully."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("Database connection closed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_conn() -> aiosqlite.Connection:
    if _connection is None:
        raise RuntimeError("Database is not initialized. Call init_db() first.")
    return _connection


# ────────────────────────────────────────────────────────────
# Warns
# ────────────────────────────────────────────────────────────

async def add_warn(user_id: int, chat_id: int, reason: str) -> int:
    """Increment the warn counter for a user in a chat and return the new count."""
    conn = _require_conn()
    async with _lock:
        cursor = await conn.execute(
            "SELECT count FROM warns WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            new_count = 1
            await conn.execute(
                "INSERT INTO warns (user_id, chat_id, count, reason, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, chat_id, new_count, reason, _now()),
            )
        else:
            new_count = row["count"] + 1
            await conn.execute(
                "UPDATE warns SET count = ?, reason = ?, updated_at = ? "
                "WHERE user_id = ? AND chat_id = ?",
                (new_count, reason, _now(), user_id, chat_id),
            )

        await conn.commit()
        return new_count


async def get_warns(user_id: int, chat_id: int) -> int:
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT count FROM warns WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row["count"] if row else 0


async def reset_warns(user_id: int, chat_id: int) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "DELETE FROM warns WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        await conn.commit()


async def count_total_warns(chat_id: int) -> int:
    """Sum of all warn counts ever given in a chat (used for /stats)."""
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT COALESCE(SUM(count), 0) AS total FROM warns WHERE chat_id = ?",
        (chat_id,),
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row["total"] if row else 0


# ────────────────────────────────────────────────────────────
# Mutes
# ────────────────────────────────────────────────────────────

async def set_mute(user_id: int, chat_id: int, until_iso: str) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "INSERT INTO mutes (user_id, chat_id, until) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, chat_id) DO UPDATE SET until = excluded.until",
            (user_id, chat_id, until_iso),
        )
        await conn.commit()


async def clear_mute(user_id: int, chat_id: int) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "DELETE FROM mutes WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        await conn.commit()


async def get_mute(user_id: int, chat_id: int) -> Optional[str]:
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT until FROM mutes WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row["until"] if row else None


# ────────────────────────────────────────────────────────────
# Chat history (used as AI conversation context)
# ────────────────────────────────────────────────────────────

async def add_history_message(chat_id: int, user_id: int, role: str, content: str) -> None:
    """Append a message to chat_history and prune old rows beyond the last 5
    for that (chat_id, user_id) pair."""
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "INSERT INTO chat_history (chat_id, user_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, role, content, _now()),
        )
        await conn.commit()

        cursor = await conn.execute(
            "SELECT id FROM chat_history WHERE chat_id = ? AND user_id = ? "
            "ORDER BY id DESC LIMIT -1 OFFSET 5",
            (chat_id, user_id),
        )
        stale_rows = await cursor.fetchall()
        await cursor.close()

        if stale_rows:
            stale_ids = [r["id"] for r in stale_rows]
            placeholders = ",".join("?" for _ in stale_ids)
            await conn.execute(
                f"DELETE FROM chat_history WHERE id IN ({placeholders})",
                stale_ids,
            )
            await conn.commit()


async def get_recent_history(chat_id: int, user_id: int, limit: int = 5) -> List[Tuple[str, str]]:
    """Return up to `limit` most recent (role, content) pairs, oldest first."""
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT role, content FROM chat_history WHERE chat_id = ? AND user_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (chat_id, user_id, limit),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    rows = list(reversed(rows))
    return [(r["role"], r["content"]) for r in rows]


async def clear_history(chat_id: int, user_id: int) -> None:
    """Delete all stored chat_history rows for this (chat_id, user_id) pair.
    Used by the /reset command to start a fresh conversation."""
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "DELETE FROM chat_history WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        await conn.commit()