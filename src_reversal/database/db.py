"""Database operations for reversal tracking."""

import aiosqlite
from datetime import datetime, timezone, timedelta
from pathlib import Path

from loguru import logger

from src_reversal.database.models import (
    ReversalRecord,
    ReversalStatus,
    ReversalStats,
    CoinReversalStats,
)


class ReversalDatabase:
    """SQLite database for reversal signal tracking."""
    
    def __init__(self, db_path: str = "data/reversals.db") -> None:
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reversal_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_price REAL NOT NULL,
                    pre_pump_price REAL NOT NULL,
                    pump_percent REAL NOT NULL,
                    score INTEGER NOT NULL,
                    strength TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'monitoring',
                    highest_price REAL DEFAULT 0,
                    lowest_price REAL DEFAULT 0,
                    retrace_percent REAL DEFAULT 0,
                    completed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Key-value store for settings like pinned message ID
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_reversal_symbol 
                ON reversal_signals(symbol)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_reversal_status 
                ON reversal_signals(status)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_reversal_timestamp 
                ON reversal_signals(timestamp)
            """)
            
            await db.commit()
            logger.info("Reversal database initialized")
    
    async def get_setting(self, key: str) -> str | None:
        """Get a setting value.
        
        Args:
            key: Setting key.
            
        Returns:
            Setting value or None if not found.
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def set_setting(self, key: str, value: str) -> None:
        """Set a setting value.
        
        Args:
            key: Setting key.
            value: Setting value.
        """
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            await db.commit()
    
    async def add_signal(self, record: ReversalRecord) -> int:
        """Add a new reversal signal to the database.
        
        Args:
            record: Reversal record to add.
            
        Returns:
            ID of the inserted record.
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                INSERT INTO reversal_signals 
                (symbol, signal_price, pre_pump_price, pump_percent, score, 
                 strength, timestamp, status, highest_price, lowest_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.symbol,
                record.signal_price,
                record.pre_pump_price,
                record.pump_percent,
                record.score,
                record.strength,
                record.timestamp.isoformat(),
                record.status.value,
                record.signal_price,  # Initial highest = signal price
                record.signal_price,  # Initial lowest = signal price
            ))
            await db.commit()
            
            return cursor.lastrowid
    
    async def update_signal(
        self,
        signal_id: int,
        status: ReversalStatus | None = None,
        highest_price: float | None = None,
        lowest_price: float | None = None,
        retrace_percent: float | None = None,
    ) -> None:
        """Update a reversal signal.
        
        Args:
            signal_id: ID of the signal to update.
            status: New status.
            highest_price: New highest price.
            lowest_price: New lowest price.
            retrace_percent: New retrace percentage.
        """
        updates = []
        values = []
        
        if status is not None:
            updates.append("status = ?")
            values.append(status.value)
            if status != ReversalStatus.MONITORING:
                updates.append("completed_at = ?")
                values.append(datetime.now(timezone.utc).isoformat())
        
        if highest_price is not None:
            updates.append("highest_price = ?")
            values.append(highest_price)
        
        if lowest_price is not None:
            updates.append("lowest_price = ?")
            values.append(lowest_price)
        
        if retrace_percent is not None:
            updates.append("retrace_percent = ?")
            values.append(retrace_percent)
        
        if not updates:
            return
        
        values.append(signal_id)
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                f"UPDATE reversal_signals SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await db.commit()
    
    async def get_monitoring_signals(self) -> list[ReversalRecord]:
        """Get all signals currently being monitored.
        
        Returns:
            List of monitoring reversal records.
        """
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM reversal_signals 
                WHERE status = 'monitoring'
                ORDER BY timestamp DESC
            """)
            rows = await cursor.fetchall()
            
            return [self._row_to_record(row) for row in rows]
    
    async def get_recent_signals(
        self,
        symbol: str | None = None,
        hours: int = 24,
    ) -> list[ReversalRecord]:
        """Get recent reversal signals.
        
        Args:
            symbol: Filter by symbol (optional).
            hours: Look back this many hours.
            
        Returns:
            List of reversal records.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if symbol:
                cursor = await db.execute("""
                    SELECT * FROM reversal_signals 
                    WHERE symbol = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                """, (symbol, cutoff.isoformat()))
            else:
                cursor = await db.execute("""
                    SELECT * FROM reversal_signals 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (cutoff.isoformat(),))
            
            rows = await cursor.fetchall()
            return [self._row_to_record(row) for row in rows]
    
    async def get_global_stats(self) -> ReversalStats:
        """Get global statistics for all signals.
        
        Returns:
            Global reversal statistics.
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                    SUM(CASE WHEN status = 'monitoring' THEN 1 ELSE 0 END) as monitoring
                FROM reversal_signals
            """)
            row = await cursor.fetchone()
            
            return ReversalStats(
                total_signals=row[0] or 0,
                successful=row[1] or 0,
                failed=row[2] or 0,
                expired=row[3] or 0,
                monitoring=row[4] or 0,
            )
    
    async def get_today_stats(self) -> ReversalStats:
        """Get statistics for today's signals.
        
        Returns:
            Today's reversal statistics.
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                    SUM(CASE WHEN status = 'monitoring' THEN 1 ELSE 0 END) as monitoring
                FROM reversal_signals
                WHERE timestamp >= ?
            """, (today_start.isoformat(),))
            row = await cursor.fetchone()
            
            return ReversalStats(
                total_signals=row[0] or 0,
                successful=row[1] or 0,
                failed=row[2] or 0,
                expired=row[3] or 0,
                monitoring=row[4] or 0,
            )
    
    async def get_coin_stats(self, symbol: str) -> CoinReversalStats | None:
        """Get statistics for a specific coin.
        
        Args:
            symbol: Coin symbol.
            
        Returns:
            Coin-specific statistics or None if not enough data.
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(retrace_percent) as avg_retrace
                FROM reversal_signals
                WHERE symbol = ? AND status != 'monitoring'
            """, (symbol,))
            row = await cursor.fetchone()
            
            total = row[0] or 0
            if total < 3:  # Minimum 3 signals for stats
                return None
            
            return CoinReversalStats(
                symbol=symbol,
                total_signals=total,
                successful=row[1] or 0,
                failed=row[2] or 0,
                avg_retrace_percent=row[3] or 0,
            )
    
    async def get_monitoring_symbols(self) -> set[str]:
        """Get symbols currently being monitored.
        
        Returns:
            Set of symbols with active monitoring.
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                SELECT DISTINCT symbol FROM reversal_signals 
                WHERE status = 'monitoring'
            """)
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
    
    def _row_to_record(self, row: aiosqlite.Row) -> ReversalRecord:
        """Convert database row to ReversalRecord."""
        return ReversalRecord(
            id=row["id"],
            symbol=row["symbol"],
            signal_price=row["signal_price"],
            pre_pump_price=row["pre_pump_price"],
            pump_percent=row["pump_percent"],
            score=row["score"],
            strength=row["strength"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            status=ReversalStatus(row["status"]),
            highest_price=row["highest_price"],
            lowest_price=row["lowest_price"],
            retrace_percent=row["retrace_percent"],
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

