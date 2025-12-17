"""Simple database for core detector - just tracks alerted symbols."""

import aiosqlite
from pathlib import Path
from loguru import logger


class CoreDatabase:
    """Minimal database for core detector to track alerted symbols."""

    def __init__(self, db_path: str = "data/core.db") -> None:
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Connect to database and create tables if needed."""
        # Ensure data directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        
        await self._create_tables()
        logger.info(f"Core database connected: {self._db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            logger.info("Core database connection closed")

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS alerted_pumps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                price REAL NOT NULL,
                pump_percent REAL NOT NULL,
                UNIQUE(symbol, detected_at)
            )
        """)
        
        await self._conn.commit()

    async def record_alert(
        self,
        symbol: str,
        detected_at: str,
        price: float,
        pump_percent: float,
    ) -> None:
        """Record an alerted pump.
        
        Args:
            symbol: Coin symbol.
            detected_at: Detection timestamp (ISO format).
            price: Price at detection.
            pump_percent: Pump percentage.
        """
        try:
            await self._conn.execute("""
                INSERT OR IGNORE INTO alerted_pumps (symbol, detected_at, price, pump_percent)
                VALUES (?, ?, ?, ?)
            """, (symbol, detected_at, price, pump_percent))
            await self._conn.commit()
        except Exception as e:
            logger.error(f"Error recording alert: {e}")

    async def get_recent_alerts(self, hours: int = 24) -> list[str]:
        """Get symbols alerted in the last N hours.
        
        Args:
            hours: Number of hours to look back.
            
        Returns:
            List of symbol names.
        """
        try:
            cursor = await self._conn.execute("""
                SELECT DISTINCT symbol
                FROM alerted_pumps
                WHERE datetime(detected_at) > datetime('now', '-' || ? || ' hours')
            """, (hours,))
            rows = await cursor.fetchall()
            return [row["symbol"] for row in rows]
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []

    async def cleanup_old_alerts(self, days: int = 7) -> None:
        """Clean up alerts older than N days.
        
        Args:
            days: Number of days to keep.
        """
        try:
            await self._conn.execute("""
                DELETE FROM alerted_pumps
                WHERE datetime(detected_at) < datetime('now', '-' || ? || ' days')
            """, (days,))
            await self._conn.commit()
            logger.debug(f"Cleaned up alerts older than {days} days")
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")

