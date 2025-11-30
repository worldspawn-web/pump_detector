"""Telegram notification service."""

from aiogram import Bot
from aiogram.enums import ParseMode
from loguru import logger

from src.config import Settings
from src.models.signal import PumpSignal


class TelegramNotifier:
    """Sends notifications to Telegram."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Telegram notifier.

        Args:
            settings: Application settings.
        """
        self._bot = Bot(token=settings.telegram_bot_token)
        self._chat_id = settings.telegram_chat_id

    async def close(self) -> None:
        """Close the bot session."""
        await self._bot.session.close()

    async def send_signal(self, signal: PumpSignal) -> bool:
        """Send a pump signal to Telegram.

        Args:
            signal: The pump signal to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            message = signal.format_message()
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
            )
            logger.info(f"Sent Telegram alert for {signal.symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_signals(self, signals: list[PumpSignal]) -> int:
        """Send multiple pump signals to Telegram.

        Args:
            signals: List of pump signals to send.

        Returns:
            Number of successfully sent messages.
        """
        sent_count = 0
        for signal in signals:
            if await self.send_signal(signal):
                sent_count += 1
        return sent_count

    async def send_startup_message(self) -> bool:
        """Send a startup notification.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text="🟢 <b>Pump Detector Started</b>\n\nMonitoring MEXC futures for pump anomalies...",
                parse_mode=ParseMode.HTML,
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")
            return False

