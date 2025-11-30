"""Telegram notification service."""

import asyncio

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import LinkPreviewOptions, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from loguru import logger

from src.config import Settings
from src.models.signal import PumpSignal
from src.database.db import Database


class TelegramNotifier:
    """Sends notifications to Telegram."""

    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        """Initialize the Telegram notifier.

        Args:
            settings: Application settings.
            database: Database for storing pinned message IDs.
        """
        self._bot = Bot(token=settings.telegram_bot_token)
        self._chat_id = settings.telegram_chat_id
        self._db = database
        # Disable link previews
        self._link_preview = LinkPreviewOptions(is_disabled=True)

    async def close(self) -> None:
        """Close the bot session."""
        await self._bot.session.close()

    async def send_signal(self, signal: PumpSignal, max_retries: int = 3) -> bool:
        """Send a pump signal to Telegram.

        Sends photo with caption if chart is available, otherwise sends text.

        Args:
            signal: The pump signal to send.
            max_retries: Maximum number of retries for rate limit errors.

        Returns:
            True if sent successfully, False otherwise.
        """
        for attempt in range(max_retries):
            try:
                message = signal.format_message()

                if signal.chart_image:
                    # Send as photo with caption
                    photo = BufferedInputFile(
                        signal.chart_image,
                        filename=f"{signal.symbol}_chart.png",
                    )
                    await self._bot.send_photo(
                        chat_id=self._chat_id,
                        photo=photo,
                        caption=message,
                        parse_mode=ParseMode.HTML,
                    )
                    logger.info(f"Sent Telegram alert with chart for {signal.symbol}")
                else:
                    # Send as text message
                    await self._bot.send_message(
                        chat_id=self._chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        link_preview_options=self._link_preview,
                    )
                    logger.info(f"Sent Telegram alert for {signal.symbol}")

                return True

            except TelegramRetryAfter as e:
                # Rate limited - wait and retry
                wait_time = e.retry_after + 1
                logger.warning(f"Rate limited for {signal.symbol}, waiting {wait_time}s ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue

            except Exception as e:
                logger.error(f"Failed to send Telegram message for {signal.symbol}: {e}")
                return False

        logger.error(f"Max retries exceeded for {signal.symbol}")
        return False

    async def send_signals(self, signals: list[PumpSignal]) -> int:
        """Send multiple pump signals to Telegram.

        Args:
            signals: List of pump signals to send.

        Returns:
            Number of successfully sent messages.
        """
        sent_count = 0
        for i, signal in enumerate(signals):
            if await self.send_signal(signal):
                sent_count += 1
            
            # Small delay between messages to avoid rate limiting
            if i < len(signals) - 1:
                await asyncio.sleep(0.5)
        
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
                link_preview_options=self._link_preview,
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")
            return False

    async def update_stats_message(self, stats_text: str, max_retries: int = 3) -> bool:
        """Update or create the pinned stats message.

        Args:
            stats_text: Formatted stats message text.
            max_retries: Maximum number of retries for rate limit errors.

        Returns:
            True if successful, False otherwise.
        """
        if not self._db:
            logger.warning("Database not available for pinned message management")
            return False

        for attempt in range(max_retries):
            try:
                # Try to get existing pinned message ID
                message_id = await self._db.get_pinned_message(
                    str(self._chat_id),
                    "global_stats",
                )

                if message_id:
                    # Try to edit existing message
                    try:
                        await self._bot.edit_message_text(
                            chat_id=self._chat_id,
                            message_id=message_id,
                            text=stats_text,
                            parse_mode=ParseMode.HTML,
                            link_preview_options=self._link_preview,
                        )
                        logger.debug("Updated pinned stats message")
                        return True
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e).lower():
                            # No changes needed
                            return True
                        elif "message to edit not found" in str(e).lower():
                            # Message was deleted, create new one
                            logger.info("Pinned message was deleted, creating new one")
                            message_id = None
                        else:
                            raise

                # Create new message and pin it
                if not message_id:
                    message = await self._bot.send_message(
                        chat_id=self._chat_id,
                        text=stats_text,
                        parse_mode=ParseMode.HTML,
                        link_preview_options=self._link_preview,
                    )

                    # Try to pin the message
                    try:
                        await self._bot.pin_chat_message(
                            chat_id=self._chat_id,
                            message_id=message.message_id,
                            disable_notification=True,
                        )
                        logger.info("Created and pinned new stats message")
                    except TelegramBadRequest as e:
                        logger.warning(f"Could not pin message (bot may lack permissions): {e}")

                    # Save message ID
                    await self._db.save_pinned_message(
                        str(self._chat_id),
                        message.message_id,
                        "global_stats",
                    )

                return True

            except TelegramRetryAfter as e:
                # Rate limited - wait and retry
                wait_time = e.retry_after + 1
                logger.warning(f"Rate limited, waiting {wait_time}s before retry ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue

            except Exception as e:
                logger.error(f"Failed to update stats message: {e}")
                return False

        logger.error("Max retries exceeded for stats message update")
        return False
