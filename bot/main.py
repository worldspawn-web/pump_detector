import asyncio
import logging
from aiogram import Bot, Dispatcher
from data.config import TELEGRAM_BOT_TOKEN
from bot import handlers

logging.basicConfig(level=logging.INFO)

async def start_bot():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(handlers.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
