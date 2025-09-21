from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils import logger

class TelegramNotifier:
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env")
        if not TELEGRAM_CHAT_ID:
            raise ValueError("TELEGRAM_CHAT_ID не задан в .env")

        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = TELEGRAM_CHAT_ID
        logger.info("Telegram bot initialized")

    async def send_message(self, text: str):
        """Отправить текстовое сообщение."""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            logger.info("Telegram message sent")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def send_photo(self, photo_path: str, caption: str = ""):
        """Отправить фото с подписью."""
        try:
            with open(photo_path, 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=caption
                )
            logger.info(f"Photo sent: {photo_path}")
        except Exception as e:
            logger.error(f"Failed to send photo {photo_path}: {e}")