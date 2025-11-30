"""Main entry point for the pump detector."""

import asyncio
import sys

from loguru import logger

from src.config import get_settings
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.services.detector import PumpDetector
from src.services.telegram import TelegramNotifier


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


async def run_scanner() -> None:
    """Run the main scanner loop."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("Starting MEXC Pump Detector...")
    logger.info(f"Pump threshold: {settings.pump_threshold_percent}%")
    logger.info(f"Scan interval: {settings.scan_interval_seconds}s")

    telegram = TelegramNotifier(settings)

    try:
        # Send startup message
        await telegram.send_startup_message()

        # Initialize both API clients
        async with MEXCClient(settings) as mexc_client, BinanceClient() as binance_client:
            logger.info("Connected to MEXC and Binance APIs")

            detector = PumpDetector(settings, mexc_client, binance_client)

            while True:
                try:
                    logger.debug("Starting scan cycle...")
                    signals = await detector.scan_for_pumps()

                    if signals:
                        logger.info(f"Found {len(signals)} pump(s)!")
                        sent = await telegram.send_signals(signals)
                        logger.info(f"Sent {sent}/{len(signals)} alerts")
                    else:
                        logger.debug("No pumps detected in this cycle")

                except Exception as e:
                    logger.error(f"Error during scan cycle: {e}")

                # Wait before next scan
                logger.debug(f"Sleeping for {settings.scan_interval_seconds}s...")
                await asyncio.sleep(settings.scan_interval_seconds)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await telegram.close()
        logger.info("Pump Detector stopped")


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
