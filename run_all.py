#!/usr/bin/env python3
"""Run both Main and Core Pump Detectors simultaneously."""

import asyncio
import sys

from loguru import logger

from src.main import run_scanner as run_main_scanner
from src_core.main import run_scanner as run_core_scanner


async def run_both() -> None:
    """Run both detectors concurrently."""
    logger.info("Starting both Main and Core Pump Detectors...")

    # Run both scanners concurrently
    await asyncio.gather(
        run_main_scanner(),
        run_core_scanner(),
        return_exceptions=True,
    )


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_both())
    except KeyboardInterrupt:
        logger.info("Shutting down both detectors...")


if __name__ == "__main__":
    main()
