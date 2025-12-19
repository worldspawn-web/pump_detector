#!/usr/bin/env python3
"""Run all three Pump Detectors simultaneously."""

import asyncio
import sys

from loguru import logger

from src.main import run_scanner as run_main_scanner
from src_core.main import run_scanner as run_core_scanner
from src_anomaly.main import run_scanner as run_anomaly_scanner


async def run_all() -> None:
    """Run all three detectors concurrently."""
    logger.info("Starting Main, Core, and Anomaly Pump Detectors...")
    
    # Run all three scanners concurrently
    await asyncio.gather(
        run_main_scanner(),
        run_core_scanner(),
        run_anomaly_scanner(),
        return_exceptions=True,
    )


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        logger.info("Shutting down all detectors...")


if __name__ == "__main__":
    main()
