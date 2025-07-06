from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from core.spread import scan_market_for_signals

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("🔍 Ищу сигналы по всем парам...")

    signals = await scan_market_for_signals()

    if not signals:
        await message.answer("Пока нет подходящих сигналов (спред < 10% или низкий объём).")
        return

    for signal in signals:
        await message.answer(
            f"📈 Токен: {signal['symbol']}\n"
            f"🔹 MEXC: {signal['mexc_price']:.6f} USD\n"
            f"🔸 DEX: {signal['dex_price']:.6f} USD\n"
            f"📊 Спред: {signal['spread']:.2f}%\n"
            f"💰 Объём на DEX (24ч): ${signal['dex_volume']:.2f}"
        )
