"""Telegram service for reversal signals."""

import asyncio
from io import BytesIO

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile, LinkPreviewOptions
from loguru import logger

from src_reversal.models.signal import ReversalSignal
from src_reversal.database.models import ReversalStats
from src_reversal.database.db import ReversalDatabase


class TelegramService:
    """Handles sending reversal signals to Telegram."""
    
    STATS_MESSAGE_KEY = "stats_message_id"
    
    def __init__(self, bot_token: str, channel_id: str, database: ReversalDatabase) -> None:
        """Initialize the Telegram service.
        
        Args:
            bot_token: Telegram bot token.
            channel_id: Telegram channel ID for reversal signals.
            database: Database instance for persisting message IDs.
        """
        self._bot = Bot(token=bot_token)
        self._channel_id = channel_id
        self._db = database
        self._stats_message_id: int | None = None
    
    async def load_stats_message_id(self) -> None:
        """Load the stats message ID from database."""
        stored_id = await self._db.get_setting(self.STATS_MESSAGE_KEY)
        if stored_id:
            self._stats_message_id = int(stored_id)
            logger.info(f"Loaded stats message ID: {self._stats_message_id}")
    
    async def send_signal(self, signal: ReversalSignal) -> bool:
        """Send a reversal signal to Telegram.
        
        Args:
            signal: Reversal signal to send.
            
        Returns:
            True if sent successfully.
        """
        message_text = signal.format_message()
        
        for attempt in range(3):
            try:
                if signal.chart_image:
                    # Send with chart image (no link preview option for photos)
                    photo = BufferedInputFile(
                        signal.chart_image,
                        filename=f"{signal.symbol}_reversal.png"
                    )
                    await self._bot.send_photo(
                        chat_id=self._channel_id,
                        photo=photo,
                        caption=message_text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    # Send text only
                    await self._bot.send_message(
                        chat_id=self._channel_id,
                        text=message_text,
                        parse_mode=ParseMode.MARKDOWN,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                    )
                
                return True
            
            except Exception as e:
                error_str = str(e).lower()
                if "flood" in error_str or "retry after" in error_str:
                    # Extract retry time
                    try:
                        retry_after = int("".join(c for c in error_str.split("retry after")[-1] if c.isdigit())[:2])
                    except:
                        retry_after = 5
                    
                    logger.warning(f"Rate limited, waiting {retry_after + 1}s...")
                    await asyncio.sleep(retry_after + 1)
                    continue
                
                logger.error(f"Failed to send signal: {e}")
                return False
        
        return False
    
    async def send_signals(self, signals: list[ReversalSignal]) -> int:
        """Send multiple reversal signals.
        
        Args:
            signals: List of signals to send.
            
        Returns:
            Number of signals sent successfully.
        """
        sent = 0
        for signal in signals:
            if await self.send_signal(signal):
                sent += 1
                await asyncio.sleep(0.5)  # Small delay between messages
        return sent
    
    async def update_stats_message(
        self,
        today_stats: ReversalStats,
        global_stats: ReversalStats,
        monitoring_count: int,
    ) -> bool:
        """Update or create the pinned stats message.
        
        Args:
            today_stats: Today's statistics.
            global_stats: All-time statistics.
            monitoring_count: Number of signals currently being monitored.
            
        Returns:
            True if updated successfully.
        """
        message_text = self._format_stats_message(today_stats, global_stats, monitoring_count)
        
        for attempt in range(3):
            try:
                if self._stats_message_id:
                    # Update existing message
                    try:
                        await self._bot.edit_message_text(
                            chat_id=self._channel_id,
                            message_id=self._stats_message_id,
                            text=message_text,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                        return True
                    except Exception as edit_err:
                        # Message might have been deleted, create new one
                        if "message to edit not found" in str(edit_err).lower():
                            logger.warning("Stats message was deleted, creating new one...")
                            self._stats_message_id = None
                        else:
                            raise
                
                if not self._stats_message_id:
                    # Create new message and pin it
                    message = await self._bot.send_message(
                        chat_id=self._channel_id,
                        text=message_text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    self._stats_message_id = message.message_id
                    
                    # Save to database
                    await self._db.set_setting(
                        self.STATS_MESSAGE_KEY, 
                        str(self._stats_message_id)
                    )
                    
                    # Try to pin the message
                    try:
                        await self._bot.pin_chat_message(
                            chat_id=self._channel_id,
                            message_id=self._stats_message_id,
                            disable_notification=True,
                        )
                    except Exception as e:
                        logger.warning(f"Could not pin stats message: {e}")
                
                return True
            
            except Exception as e:
                error_str = str(e).lower()
                if "flood" in error_str or "retry after" in error_str:
                    try:
                        retry_after = int("".join(c for c in error_str.split("retry after")[-1] if c.isdigit())[:2])
                    except:
                        retry_after = 5
                    
                    logger.warning(f"Rate limited on stats update, waiting {retry_after + 1}s...")
                    await asyncio.sleep(retry_after + 1)
                    continue
                
                logger.error(f"Failed to update stats message: {e}")
                return False
        
        return False
    
    def _format_stats_message(
        self,
        today: ReversalStats,
        all_time: ReversalStats,
        monitoring: int,
    ) -> str:
        """Format the statistics message.
        
        Args:
            today: Today's stats.
            all_time: All-time stats.
            monitoring: Current monitoring count.
            
        Returns:
            Formatted message string.
        """
        lines = [
            "📊 *Reversal Signal Statistics*",
            "",
            "━━━ Today ━━━",
            f"Signals: {today.total_signals}",
            f"Monitoring: {today.monitoring}",
        ]
        
        if today.completed > 0:
            lines.append(f"✅ Success: {today.successful} ({today.success_rate:.0f}%)")
            lines.append(f"❌ Failed: {today.failed} ({today.failure_rate:.0f}%)")
            lines.append(f"⏰ Expired: {today.expired}")
        
        lines.extend([
            "",
            "━━━ All Time ━━━",
            f"Total Signals: {all_time.total_signals}",
            f"Currently Monitoring: {monitoring}",
        ])
        
        if all_time.completed > 0:
            lines.append(f"✅ Success Rate: {all_time.success_rate:.1f}%")
            lines.append(f"❌ Failure Rate: {all_time.failure_rate:.1f}%")
            lines.append(f"Completed: {all_time.completed}")
        
        lines.extend([
            "",
            "_Updated hourly_",
        ])
        
        return "\n".join(lines)
    
    async def close(self) -> None:
        """Close the bot session."""
        await self._bot.session.close()

