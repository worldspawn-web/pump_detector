"""Main entry point for the pump detector."""

import asyncio
import sys
from datetime import datetime, timezone

from loguru import logger

from src.config import get_settings
from src.database.db import Database
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.services.bybit import ByBitClient
from src.services.bingx import BingXClient
from src.services.detector import PumpDetector
from src.services.telegram import TelegramNotifier
from src.services.tracker import PumpTracker
from src.services.stats import StatsFormatter


def setup_logging(log_level: str) -> None:
    """Configure loguru logging.

    Args:
        log_level: Logging level string.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    logger.add(
        "logs/pump_detector_{time:YYYY-MM-DD}.log",
        level=log_level.upper(),
        rotation="1 day",
        retention="7 days",
        compression="zip",
    )


async def update_stats_periodically(
    telegram: TelegramNotifier,
    stats_formatter: StatsFormatter,
    interval_seconds: int = 3600,
) -> None:
    """Background task to update stats message hourly.

    Args:
        telegram: Telegram notifier.
        stats_formatter: Stats formatter.
        interval_seconds: Update interval in seconds (default 1 hour).
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            logger.info("Updating pinned stats message...")
            stats_text = await stats_formatter.format_global_stats_message()
            await telegram.update_stats_message(stats_text)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error updating stats: {e}")


async def run_scanner() -> None:
    """Run the main scanner loop."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("Starting MEXC Pump Detector...")
    logger.info(f"Pump threshold: {settings.pump_threshold_percent}%")
    logger.info(f"Scan interval: {settings.scan_interval_seconds}s")

    # Initialize database
    database = Database()
    await database.connect()

    # Initialize services
    telegram = TelegramNotifier(settings, database)
    stats_formatter = StatsFormatter(database)

    # Track last stats update hour
    last_stats_hour = -1

    try:
        # Send startup message
        await telegram.send_startup_message()

        # Initialize all API clients
        async with (
            MEXCClient(settings) as mexc_client,
            BinanceClient() as binance_client,
            ByBitClient() as bybit_client,
            BingXClient() as bingx_client,
        ):
            logger.info("Connected to all exchange APIs")

            # Initialize tracker
            tracker = PumpTracker(database, mexc_client)
            await tracker.load_active_pumps()

            # Initialize detector with tracker
            detector = PumpDetector(
                settings,
                mexc_client,
                binance_client,
                bybit_client,
                bingx_client,
                tracker,
            )
            
            # Load recently alerted symbols to prevent duplicates on restart
            await detector.load_alerted_symbols()

            # Create initial stats message
            logger.info("Creating initial stats message...")
            stats_text = await stats_formatter.format_global_stats_message()
            await telegram.update_stats_message(stats_text)

            while True:
                try:
                    logger.debug("Starting scan cycle...")
                    
                    # Scan for pumps (also updates tracker price cache)
                    signals, tickers = await detector.scan_for_pumps()

                    if signals:
                        logger.info(f"Found {len(signals)} pump(s)!")
                        sent = await telegram.send_signals(signals)
                        logger.info(f"Sent {sent}/{len(signals)} alerts")
                    else:
                        logger.debug("No pumps detected in this cycle")

                    # Check active pumps for reversals
                    if tracker.active_count > 0:
                        completed = await tracker.check_active_pumps()
                        if completed:
                            logger.info(f"Completed monitoring for {len(completed)} pump(s)")
                            # Allow these coins to be alerted again if they pump
                            detector.remove_completed_alerts([p.symbol for p in completed])

                    # Update stats hourly
                    current_hour = datetime.now(timezone.utc).hour
                    if current_hour != last_stats_hour:
                        last_stats_hour = current_hour
                        logger.info("Hourly stats update...")
                        stats_text = await stats_formatter.format_global_stats_message()
                        await telegram.update_stats_message(stats_text)

                except Exception as e:
                    logger.error(f"Error during scan cycle: {e}")

                # Wait before next scan
                logger.debug(f"Sleeping for {settings.scan_interval_seconds}s...")
                await asyncio.sleep(settings.scan_interval_seconds)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await telegram.close()
        await database.close()
        logger.info("Pump Detector stopped")


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
