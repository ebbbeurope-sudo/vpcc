import asyncio
import logging
import os

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from app import bot as bot_module
from app.core import config
from main import app

logging.basicConfig(level=logging.INFO)


async def run_bot():
    session = None
    if config.WS_PROXY:
        session = AiohttpSession(proxy=config.WS_PROXY)
    bot = Bot(token=config.BOT_TOKEN, session=session)
    bot_module.setup(bot)
    dp = Dispatcher()
    dp.include_router(bot_module.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def main():
    port = int(os.getenv("PORT", config.WS_PORT))
    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info", access_log=False)
    )
    await asyncio.gather(server.serve(), run_bot())


if __name__ == "__main__":
    asyncio.run(main())