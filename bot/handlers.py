from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from core.dex import get_dex_price
from core.mexc import get_mexc_price
from core.spread import calculate_spread, evaluate_signal

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я сигнальный бот для MEXC/DEX. Ожидай сигналов!")

    # Примерный адрес токена и символ
    token_address = "example"  # временно, для сингла
    mexc_symbol = "USDTUSDC"  # временно, для сингла

    signal = evaluate_signal(token_address, mexc_symbol)

    if signal:
        await message.answer(
            f"📈 Токен: {mexc_symbol}\n"
            f"🔹 MEXC: {signal['mexc_price']:.6f} USD\n"
            f"🔸 DEX: {signal['dex_price']:.6f} USD\n"
            f"📊 Спред: {signal['spread']:.2f}%\n"
            f"💰 Объём на DEX (24ч): ${signal['dex_volume']:.2f}"
        )
    else:
        await message.answer("Сигналов пока нет (спред < 10% или ошибка загрузки данных).")