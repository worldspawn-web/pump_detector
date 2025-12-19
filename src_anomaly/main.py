"""Main entry point for the Anomaly Pump Detector."""

import asyncio
import sys
from datetime import datetime, timezone

from loguru import logger

from src_anomaly.config import get_anomaly_settings
from src_anomaly.detector import AnomalyPumpDetector
from src.database.db import Database
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.services.bybit import ByBitClient
from src.services.bingx import BingXClient
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
        "logs/anomaly_detector_{time:YYYY-MM-DD}.log",
        level=log_level.upper(),
        rotation="1 day",
        retention="7 days",
        compression="zip",
    )


async def run_scanner() -> None:
    """Run the anomaly scanner loop."""
    settings = get_anomaly_settings()
    setup_logging(settings.log_level)

    logger.info("Starting Anomaly Pump Detector...")
    logger.info(f"Detection: {settings.anomaly_min_pump_percent}%+ in single 5M candle")
    logger.info(f"Volume spike threshold: {settings.anomaly_min_volume_spike}x average")
    logger.info(f"Candle body threshold: {settings.anomaly_min_candle_body}x average")
    logger.info(f"Scan interval: {settings.scan_interval_seconds}s")

    # Initialize database with anomaly-specific path
    database = Database(db_path="data/anomaly.db")
    await database.connect()

    # Create custom settings dict for TelegramNotifier
    # It expects telegram_chat_id, so we map anomaly_telegram_chat_id
    class AnomalyTelegramSettings:
        def __init__(self):
            self.telegram_bot_token = settings.telegram_bot_token
            self.telegram_chat_id = settings.anomaly_telegram_chat_id
    
    telegram_settings = AnomalyTelegramSettings()
    telegram = TelegramNotifier(telegram_settings, database)
    stats_formatter = StatsFormatter(database)

    # Track last stats update hour (anomaly detector also updates stats)
    last_stats_hour = -1

    try:
        # Initialize all API clients
        async with (
            MEXCClient(settings) as mexc_client,
            BinanceClient() as binance_client,
            ByBitClient() as bybit_client,
            BingXClient() as bingx_client,
        ):
            logger.info("[ANOMALY] Connected to all exchange APIs")

            # Initialize tracker with anomaly database
            tracker = PumpTracker(
                database,
                mexc_client,
                monitoring_hours=settings.monitoring_hours,
            )
            await tracker.load_active_pumps()

            # Initialize anomaly detector with tracker
            detector = AnomalyPumpDetector(
                settings,
                mexc_client,
                binance_client,
                bybit_client,
                bingx_client,
                tracker,
            )
            
            # Load recently alerted symbols
            await detector.load_alerted_symbols()

            # Create initial stats message
            logger.info("[ANOMALY] Creating initial stats message...")
            stats_text = await stats_formatter.format_global_stats_message()
            await telegram.update_stats_message(stats_text)

            while True:
                try:
                    logger.debug("[ANOMALY] Starting scan cycle...")
                    
                    # Scan for anomaly pumps
                    signals, tickers = await detector.scan_for_pumps()

                    if signals:
                        logger.info(f"[ANOMALY] Found {len(signals)} anomaly pump(s)!")
                        sent = await telegram.send_signals(signals)
                        logger.info(f"[ANOMALY] Sent {sent}/{len(signals)} alerts")
                    else:
                        logger.debug("[ANOMALY] No anomaly pumps detected in this cycle")

                    # Check active pumps for reversals
                    if tracker.active_count > 0:
                        completed = await tracker.check_active_pumps()
                        if completed:
                            logger.info(f"[ANOMALY] Completed monitoring for {len(completed)} pump(s)")
                            # Allow these coins to be alerted again if they pump
                            detector.remove_completed_alerts([p.symbol for p in completed])

                    # Update stats hourly
                    current_hour = datetime.now(timezone.utc).hour
                    if current_hour != last_stats_hour:
                        last_stats_hour = current_hour
                        logger.info("[ANOMALY] Hourly stats update...")
                        stats_text = await stats_formatter.format_global_stats_message()
                        await telegram.update_stats_message(stats_text)

                except Exception as e:
                    logger.error(f"[ANOMALY] Error during scan cycle: {e}")

                # Wait before next scan
                logger.debug(f"[ANOMALY] Sleeping for {settings.scan_interval_seconds}s...")
                await asyncio.sleep(settings.scan_interval_seconds)

    except KeyboardInterrupt:
        logger.info("[ANOMALY] Shutting down...")
    finally:
        await telegram.close()
        await database.close()
        logger.info("[ANOMALY] Anomaly Pump Detector stopped")


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

