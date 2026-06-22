"""
database/db.py
Async SQLite data access layer built on aiosqlite.
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

    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS group_settings (
            chat_id INTEGER PRIMARY KEY,
            is_locked INTEGER NOT NULL DEFAULT 0,
            filter_links INTEGER NOT NULL DEFAULT 0,
            filter_bad_words INTEGER NOT NULL DEFAULT 0,
            welcome_message TEXT
        )
        """
    )

    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS banned_words (
            chat_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            PRIMARY KEY (chat_id, word)
        )
        """
    )

    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            due_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL,
            fired INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    await _connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_reminders_due "
        "ON reminders (fired, due_at)"
    )

    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS group_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """
    )

    await _connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_group_log_chat "
        "ON group_log (chat_id, created_at)"
    )

    await _connection.commit()
    logger.info("Database initialized at %s", db_path)


async def close_db() -> None:
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
# Chat history
# ────────────────────────────────────────────────────────────

async def add_history_message(chat_id: int, user_id: int, role: str, content: str) -> None:
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
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "DELETE FROM chat_history WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        await conn.commit()


# ────────────────────────────────────────────────────────────
# Group settings
# ────────────────────────────────────────────────────────────

async def _ensure_group_settings_row(chat_id: int) -> None:
    conn = _require_conn()
    await conn.execute(
        "INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)",
        (chat_id,),
    )


async def get_group_settings(chat_id: int) -> dict:
    conn = _require_conn()
    async with _lock:
        await _ensure_group_settings_row(chat_id)
        await conn.commit()

    cursor = await conn.execute(
        "SELECT is_locked, filter_links, filter_bad_words FROM group_settings "
        "WHERE chat_id = ?",
        (chat_id,),
    )
    row = await cursor.fetchone()
    await cursor.close()
    if row is None:
        return {"is_locked": False, "filter_links": False, "filter_bad_words": False}
    return {
        "is_locked": bool(row["is_locked"]),
        "filter_links": bool(row["filter_links"]),
        "filter_bad_words": bool(row["filter_bad_words"]),
    }


async def set_group_lock(chat_id: int, locked: bool) -> None:
    conn = _require_conn()
    async with _lock:
        await _ensure_group_settings_row(chat_id)
        await conn.execute(
            "UPDATE group_settings SET is_locked = ? WHERE chat_id = ?",
            (1 if locked else 0, chat_id),
        )
        await conn.commit()


async def set_group_filter(chat_id: int, filter_name: str, enabled: bool) -> None:
    if filter_name not in ("filter_links", "filter_bad_words"):
        raise ValueError(f"Invalid filter_name: {filter_name}")
    conn = _require_conn()
    async with _lock:
        await _ensure_group_settings_row(chat_id)
        await conn.execute(
            f"UPDATE group_settings SET {filter_name} = ? WHERE chat_id = ?",
            (1 if enabled else 0, chat_id),
        )
        await conn.commit()


async def set_welcome_message(chat_id: int, text: str) -> None:
    conn = _require_conn()
    async with _lock:
        await _ensure_group_settings_row(chat_id)
        await conn.execute(
            "UPDATE group_settings SET welcome_message = ? WHERE chat_id = ?",
            (text, chat_id),
        )
        await conn.commit()


async def get_welcome_message(chat_id: int) -> Optional[str]:
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT welcome_message FROM group_settings WHERE chat_id = ?",
        (chat_id,),
    )
    row = await cursor.fetchone()
    await cursor.close()
    if row is None:
        return None
    return row["welcome_message"]


# ────────────────────────────────────────────────────────────
# Banned words
# ────────────────────────────────────────────────────────────

async def add_banned_word(chat_id: int, word: str) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "INSERT OR IGNORE INTO banned_words (chat_id, word) VALUES (?, ?)",
            (chat_id, word.strip().lower()),
        )
        await conn.commit()


async def remove_banned_word(chat_id: int, word: str) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "DELETE FROM banned_words WHERE chat_id = ? AND word = ?",
            (chat_id, word.strip().lower()),
        )
        await conn.commit()


async def get_banned_words(chat_id: int) -> List[str]:
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT word FROM banned_words WHERE chat_id = ? ORDER BY word",
        (chat_id,),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [r["word"] for r in rows]


# ────────────────────────────────────────────────────────────
# Reminders
# ────────────────────────────────────────────────────────────

async def add_reminder(chat_id: int, user_id: int, text: str, due_at_iso: str) -> int:
    conn = _require_conn()
    async with _lock:
        cursor = await conn.execute(
            "INSERT INTO reminders (chat_id, user_id, text, due_at, created_at, fired) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (chat_id, user_id, text, due_at_iso, _now()),
        )
        await conn.commit()
        return cursor.lastrowid


async def get_due_reminders(now_iso: str) -> List[dict]:
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT id, chat_id, user_id, text, due_at FROM reminders "
        "WHERE fired = 0 AND due_at <= ?",
        (now_iso,),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [
        {
            "id": r["id"],
            "chat_id": r["chat_id"],
            "user_id": r["user_id"],
            "text": r["text"],
            "due_at": r["due_at"],
        }
        for r in rows
    ]


async def mark_reminder_fired(reminder_id: int) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "UPDATE reminders SET fired = 1 WHERE id = ?",
            (reminder_id,),
        )
        await conn.commit()


# ────────────────────────────────────────────────────────────
# Group log (برای /summary)
# ────────────────────────────────────────────────────────────

async def add_group_log(chat_id: int, user_id: int, user_name: str, content: str) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "INSERT INTO group_log (chat_id, user_id, user_name, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, user_name, content, _now()),
        )
        await conn.commit()

        cursor = await conn.execute(
            "SELECT id FROM group_log WHERE chat_id = ? "
            "ORDER BY id DESC LIMIT -1 OFFSET 200",
            (chat_id,),
        )
        stale_rows = await cursor.fetchall()
        await cursor.close()

        if stale_rows:
            stale_ids = [r["id"] for r in stale_rows]
            placeholders = ",".join("?" for _ in stale_ids)
            await conn.execute(
                f"DELETE FROM group_log WHERE id IN ({placeholders})",
                stale_ids,
            )
            await conn.commit()


async def get_recent_group_log(chat_id: int, limit: int = 50) -> List[Tuple[str, str]]:
    conn = _require_conn()
    cursor = await conn.execute(
        "SELECT user_name, content FROM group_log WHERE chat_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (chat_id, limit),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    rows = list(reversed(rows))
    return [(r["user_name"], r["content"]) for r in rows]