import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils import logger

class TelegramNotifier:
    def __init__(self):
        self.bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = TELEGRAM_CHAT_ID
        logger.info("Telegram bot initialized")

    def send_message(self, text: str):
        """Отправить текстовое сообщение."""
        try:
            self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=telegram.ParseMode.HTML)
            logger.info("Telegram message sent")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def send_photo(self, photo_path: str, caption: str = ""):
        """Отправить фото с подписью."""
        try:
            with open(photo_path, 'rb') as photo:
                self.bot.send_photo(chat_id=self.chat_id, photo=photo, caption=caption)
            logger.info(f"Photo sent: {photo_path}")
        except Exception as e:
            logger.error(f"Failed to send photo {photo_path}: {e}")