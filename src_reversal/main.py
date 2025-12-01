"""Main entry point for the reversal signal detector."""

import asyncio
import signal
import sys
from datetime import datetime, timezone

from loguru import logger

from src_reversal.config import get_reversal_settings
from src_reversal.services.mexc import MexcClient
from src_reversal.services.binance import BinanceClient
from src_reversal.services.bybit import BybitClient
from src_reversal.services.bingx import BingXClient
from src_reversal.services.detector import ReversalDetector
from src_reversal.services.tracker import ReversalTracker
from src_reversal.services.telegram import TelegramService
from src_reversal.database.db import ReversalDatabase


async def run_scanner() -> None:
    """Main scanner loop."""
    settings = get_reversal_settings()
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
    )
    
    logger.info("Starting Reversal Signal Detector...")
    logger.info(f"Pump threshold: {settings.pump_threshold_percent}%")
    logger.info(f"Min volume: ${settings.min_volume_usd:,.0f}")
    logger.info(f"Scan interval: {settings.scan_interval_seconds}s")
    
    # Initialize database
    database = ReversalDatabase()
    await database.initialize()
    
    # Initialize tracker
    tracker = ReversalTracker(
        database=database,
        monitoring_hours=settings.monitoring_hours,
        success_retrace_pct=settings.success_retrace_percent,
        failure_increase_pct=settings.failure_increase_percent,
    )
    
    # Initialize Telegram
    telegram = TelegramService(
        bot_token=settings.telegram_bot_token,
        channel_id=settings.telegram_reversal_channel_id,
        database=database,
    )
    await telegram.load_stats_message_id()
    
    # Shutdown handler
    shutdown_event = asyncio.Event()
    
    def handle_shutdown(sig, frame):
        logger.info("Shutdown signal received...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        async with (
            MexcClient(settings) as mexc,
            BinanceClient() as binance,
            BybitClient() as bybit,
            BingXClient() as bingx,
        ):
            logger.info("Connected to all exchange APIs")
            
            # Initialize detector
            detector = ReversalDetector(
                settings=settings,
                mexc=mexc,
                binance=binance,
                bybit=bybit,
                bingx=bingx,
                tracker=tracker,
            )
            
            # Load existing monitoring data
            await tracker.load_active_signals()
            await detector.load_alerted_symbols()
            
            # Track last stats update hour
            last_stats_hour = -1
            
            while not shutdown_event.is_set():
                try:
                    # Scan for reversal signals
                    signals, price_cache = await detector.scan_for_reversals()
                    
                    if signals:
                        logger.info(f"Found {len(signals)} reversal signal(s)!")
                        sent = await telegram.send_signals(signals)
                        logger.info(f"Sent {sent}/{len(signals)} alerts")
                    else:
                        logger.debug("No reversal signals detected in this cycle")
                    
                    # Check active signals for completion
                    if tracker.active_count > 0:
                        completed = await tracker.check_signals()
                        if completed:
                            logger.info(f"Completed monitoring for {len(completed)} signal(s)")
                            # Allow these coins to be alerted again
                            detector.remove_completed_alerts([s.symbol for s in completed])
                    
                    # Update stats hourly
                    current_hour = datetime.now(timezone.utc).hour
                    if current_hour != last_stats_hour:
                        last_stats_hour = current_hour
                        logger.info("Updating stats message...")
                        
                        today_stats = await tracker.get_today_stats()
                        global_stats = await tracker.get_global_stats()
                        
                        await telegram.update_stats_message(
                            today_stats=today_stats,
                            global_stats=global_stats,
                            monitoring_count=tracker.active_count,
                        )
                
                except Exception as e:
                    logger.error(f"Error in scan loop: {e}")
                
                # Wait for next scan or shutdown
                try:
                    await asyncio.wait_for(
                        shutdown_event.wait(),
                        timeout=settings.scan_interval_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
        
        logger.info("Reversal detector stopped")
    
    finally:
        await telegram.close()


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

