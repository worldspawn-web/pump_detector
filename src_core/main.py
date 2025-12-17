"""Main entry point for the Core Pump Detector."""

import asyncio
import sys

from loguru import logger

from src_core.config import get_core_settings
from src_core.watchlist import WatchlistManager
from src_core.detector import CorePumpDetector
from src_core.telegram import CoreTelegramNotifier
from src_core.database import CoreDatabase
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.services.bybit import ByBitClient
from src.services.bingx import BingXClient


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
        "logs/core_detector_{time:YYYY-MM-DD}.log",
        level=log_level.upper(),
        rotation="1 day",
        retention="7 days",
        compression="zip",
    )


async def run_scanner() -> None:
    """Run the core scanner loop."""
    settings = get_core_settings()
    setup_logging(settings.log_level)

    logger.info("Starting Core Pump Detector...")
    logger.info(f"Pump threshold: {settings.core_pump_threshold_percent}%")
    logger.info(f"Min volume: ${settings.core_min_volume_usd:,}")
    logger.info(f"Scan interval: {settings.scan_interval_seconds}s")

    # Initialize watchlist
    watchlist = WatchlistManager(settings.watchlist_file)
    watchlist.load()

    if watchlist.count == 0:
        logger.warning("Watchlist is empty! Add coins to watchlist.txt")
        logger.info("Example: BTC, ETH, SOL (one per line)")
        return

    # Initialize database
    database = CoreDatabase()
    await database.connect()

    # Initialize Telegram
    telegram = CoreTelegramNotifier(settings)

    # Track reload counter (reload watchlist every 10 cycles)
    reload_counter = 0
    cleanup_counter = 0

    try:
        # Initialize all API clients
        async with (
            MEXCClient(settings) as mexc_client,
            BinanceClient() as binance_client,
            ByBitClient() as bybit_client,
            BingXClient() as bingx_client,
        ):
            logger.info("Connected to all exchange APIs")

            # Initialize detector
            detector = CorePumpDetector(
                settings,
                watchlist,
                mexc_client,
                binance_client,
                bybit_client,
                bingx_client,
            )

            while True:
                try:
                    # Reload watchlist periodically (every 10 scans)
                    reload_counter += 1
                    if reload_counter >= 10:
                        watchlist.reload()
                        reload_counter = 0
                        
                        # If watchlist becomes empty, warn and wait
                        if watchlist.count == 0:
                            logger.warning("Watchlist is empty! Waiting...")
                            await asyncio.sleep(settings.scan_interval_seconds)
                            continue

                    logger.debug("Starting scan cycle...")
                    
                    # Scan for pumps
                    signals = await detector.scan_for_pumps()

                    if signals:
                        logger.info(f"[CORE] Found {len(signals)} pump(s) in watchlist!")
                        sent = await telegram.send_signals(signals)
                        logger.info(f"[CORE] Sent {sent}/{len(signals)} alerts")
                        
                        # Record alerts in database
                        for signal in signals:
                            await database.record_alert(
                                symbol=signal.symbol,
                                detected_at=signal.detected_at.isoformat(),
                                price=signal.current_price,
                                pump_percent=signal.price_change_percent,
                            )
                    else:
                        logger.debug("No pumps detected in watchlist")

                    # Cleanup old alerts periodically (every 100 scans)
                    cleanup_counter += 1
                    if cleanup_counter >= 100:
                        await database.cleanup_old_alerts(days=7)
                        cleanup_counter = 0

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
        logger.info("Core Pump Detector stopped")


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

