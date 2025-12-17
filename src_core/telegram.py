"""Telegram notification service for core detector."""

import aiohttp
from loguru import logger

from src_core.config import CoreSettings
from src.models.signal import PumpSignal


class CoreTelegramNotifier:
    """Sends pump alerts to Telegram - simplified version for core detector."""

    def __init__(self, settings: CoreSettings) -> None:
        """Initialize Telegram notifier.

        Args:
            settings: Core application settings.
        """
        self._settings = settings
        self._session: aiohttp.ClientSession | None = None
        self._base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_signals(self, signals: list[PumpSignal]) -> int:
        """Send pump signal alerts to Telegram.

        Args:
            signals: List of pump signals to send.

        Returns:
            Number of successfully sent messages.
        """
        sent_count = 0

        for signal in signals:
            try:
                # Format message
                message_text = signal.format_message()

                # Send with chart if available
                if signal.chart_image:
                    success = await self._send_photo(
                        message_text,
                        signal.chart_image,
                    )
                else:
                    success = await self._send_message(message_text)

                if success:
                    sent_count += 1
                    logger.info(f"Sent alert for {signal.symbol}")
                else:
                    logger.warning(f"Failed to send alert for {signal.symbol}")

            except Exception as e:
                logger.error(f"Error sending signal for {signal.symbol}: {e}")

        return sent_count

    async def _send_message(self, text: str) -> bool:
        """Send text message to Telegram.

        Args:
            text: Message text (supports HTML formatting).

        Returns:
            True if successful.
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base_url}/sendMessage",
                json={
                    "chat_id": self._settings.core_telegram_chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def _send_photo(self, caption: str, photo_bytes: bytes) -> bool:
        """Send photo with caption to Telegram.

        Args:
            caption: Photo caption (supports HTML formatting).
            photo_bytes: PNG image bytes.

        Returns:
            True if successful.
        """
        try:
            session = await self._get_session()

            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field("chat_id", self._settings.core_telegram_chat_id)
            data.add_field("caption", caption)
            data.add_field("parse_mode", "HTML")
            data.add_field(
                "photo",
                photo_bytes,
                filename="chart.png",
                content_type="image/png",
            )

            async with session.post(
                f"{self._base_url}/sendPhoto",
                data=data,
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False

