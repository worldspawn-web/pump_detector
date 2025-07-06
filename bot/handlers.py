from aiogram import Router, types
from aiogram.types import Message
from aiogram.filters import CommandStart

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я сигнальный бот для MEXC/DEX. Ожидай сигналов!")
