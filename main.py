"""
main.py
Application entry point. Wires together config, database, AI services,
middlewares and routers, then starts long polling.
"""

import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import database.db as db
from config import config
from handlers import admin, chat, events
from middlewares.rate_limit import RateLimitMiddleware
from services.ai_router import AIRouter
from services.gemini_service import GeminiService
from services.groq_service import GroqService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def build_ai_router() -> AIRouter:
    groq_service = None
    if config.groq_api_key:
        groq_service = GroqService(
            api_key=config.groq_api_key,
            model=config.groq_model,
            timeout_seconds=config.groq_timeout_seconds,
        )
    else:
        logger.warning("GROQ_API_KEY not set, Groq provider disabled")

    gemini_service = None
    if config.gemini_api_key:
        gemini_service = GeminiService(
            api_key=config.gemini_api_key,
            model=config.gemini_model,
        )
    else:
        logger.warning("GEMINI_API_KEY not set, Gemini provider disabled")

    return AIRouter(
        groq_service=groq_service,
        gemini_service=gemini_service,
        cache_ttl_seconds=config.ai_cache_ttl_seconds,
    )


async def main() -> None:
    logger.info("Starting bot...")

    await db.init_db(config.db_path)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    ai_router = build_ai_router()

    rate_limit_middleware = RateLimitMiddleware(
        max_messages_per_window=config.max_messages_per_window,
        message_window_seconds=config.message_window_seconds,
        max_ai_requests_per_window=config.max_ai_requests_per_window,
        ai_window_seconds=config.ai_window_seconds,
        repeat_message_threshold=config.repeat_message_threshold,
    )

    dp = Dispatcher(ai_router=ai_router)

    dp.message.middleware(rate_limit_middleware)

    dp.include_router(admin.router)
    dp.include_router(events.router)
    dp.include_router(chat.router)

    stop_event = asyncio.Event()

    def _handle_shutdown_signal(*_args: object) -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                loop.add_signal_handler(sig, _handle_shutdown_signal)
            except NotImplementedError:
                # add_signal_handler is not available on some platforms (e.g. Windows)
                pass

    polling_task = asyncio.create_task(dp.start_polling(bot))
    stop_task = asyncio.create_task(stop_event.wait())

    done, pending = await asyncio.wait(
        {polling_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
    )

    if stop_task in done:
        logger.info("Stopping polling...")
        await dp.stop_polling()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    for task in pending:
        task.cancel()

    await bot.session.close()
    await db.close_db()
    logger.info("Bot stopped gracefully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user, exiting.")