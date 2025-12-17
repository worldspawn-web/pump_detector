"""SQLite database operations for pump tracking."""

import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from src.database.models import PumpRecord, PumpStatus, CoinStats, GlobalStats


class Database:
    """Async SQLite database for pump tracking."""
    
    def __init__(self, db_path: str = "data/pumps.db") -> None:
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection | None = None
    
    async def connect(self) -> None:
        """Connect to database and create tables."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info(f"Connected to database: {self._db_path}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed")
    
    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS pump_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                detected_at TIMESTAMP NOT NULL,
                pump_percent REAL NOT NULL,
                
                price_at_detection REAL NOT NULL,
                price_before_pump REAL NOT NULL,
                
                highest_price REAL DEFAULT 0,
                lowest_price REAL DEFAULT 0,
                last_checked_price REAL DEFAULT 0,
                last_checked_at TIMESTAMP,
                
                time_to_25pct_retrace REAL,
                time_to_50pct_retrace REAL,
                time_to_75pct_retrace REAL,
                time_to_100pct_retrace REAL,
                
                max_drop_from_high_pct REAL DEFAULT 0,
                returned_to_prepump INTEGER DEFAULT 0,
                
                status TEXT DEFAULT 'monitoring',
                monitoring_ends_at TIMESTAMP,
                completed_at TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_pump_symbol ON pump_records(symbol);
            CREATE INDEX IF NOT EXISTS idx_pump_status ON pump_records(status);
            CREATE INDEX IF NOT EXISTS idx_pump_detected ON pump_records(detected_at);
            
            CREATE TABLE IF NOT EXISTS pinned_messages (
                id INTEGER PRIMARY KEY,
                chat_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self._conn.commit()
    
    # ==================== Pump Records ====================
    
    async def save_pump(self, record: PumpRecord) -> int:
        """Save a new pump record.
        
        Returns:
            The ID of the inserted record.
        """
        cursor = await self._conn.execute("""
            INSERT INTO pump_records (
                symbol, detected_at, pump_percent,
                price_at_detection, price_before_pump,
                highest_price, lowest_price, last_checked_price,
                status, monitoring_ends_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.symbol,
            record.detected_at.isoformat(),
            record.pump_percent,
            record.price_at_detection,
            record.price_before_pump,
            record.highest_price,
            record.lowest_price,
            record.last_checked_price,
            record.status.value,
            record.monitoring_ends_at.isoformat() if record.monitoring_ends_at else None,
        ))
        await self._conn.commit()
        return cursor.lastrowid
    
    async def update_pump(self, record: PumpRecord) -> None:
        """Update an existing pump record."""
        await self._conn.execute("""
            UPDATE pump_records SET
                highest_price = ?,
                lowest_price = ?,
                last_checked_price = ?,
                last_checked_at = ?,
                time_to_25pct_retrace = ?,
                time_to_50pct_retrace = ?,
                time_to_75pct_retrace = ?,
                time_to_100pct_retrace = ?,
                max_drop_from_high_pct = ?,
                returned_to_prepump = ?,
                status = ?,
                completed_at = ?
            WHERE id = ?
        """, (
            record.highest_price,
            record.lowest_price,
            record.last_checked_price,
            record.last_checked_at.isoformat() if record.last_checked_at else None,
            record.time_to_25pct_retrace,
            record.time_to_50pct_retrace,
            record.time_to_75pct_retrace,
            record.time_to_100pct_retrace,
            record.max_drop_from_high_pct,
            1 if record.returned_to_prepump else 0,
            record.status.value,
            record.completed_at.isoformat() if record.completed_at else None,
            record.id,
        ))
        await self._conn.commit()
    
    async def get_active_pumps(self) -> list[PumpRecord]:
        """Get all pumps currently being monitored."""
        cursor = await self._conn.execute("""
            SELECT * FROM pump_records WHERE status = 'monitoring'
        """)
        rows = await cursor.fetchall()
        return [self._row_to_pump_record(row) for row in rows]
    
    async def get_coin_pumps(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[PumpRecord]:
        """Get pump history for a specific coin."""
        cursor = await self._conn.execute("""
            SELECT * FROM pump_records 
            WHERE symbol = ? 
            ORDER BY detected_at DESC 
            LIMIT ?
        """, (symbol, limit))
        rows = await cursor.fetchall()
        return [self._row_to_pump_record(row) for row in rows]
    
    async def get_recent_pumps(
        self,
        hours: int = 24,
        status: PumpStatus | None = None,
    ) -> list[PumpRecord]:
        """Get recent pumps within the specified hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        if status:
            cursor = await self._conn.execute("""
                SELECT * FROM pump_records 
                WHERE detected_at >= ? AND status = ?
                ORDER BY detected_at DESC
            """, (since.isoformat(), status.value))
        else:
            cursor = await self._conn.execute("""
                SELECT * FROM pump_records 
                WHERE detected_at >= ?
                ORDER BY detected_at DESC
            """, (since.isoformat(),))
        
        rows = await cursor.fetchall()
        return [self._row_to_pump_record(row) for row in rows]
    
    def _row_to_pump_record(self, row: aiosqlite.Row) -> PumpRecord:
        """Convert database row to PumpRecord."""
        return PumpRecord(
            id=row["id"],
            symbol=row["symbol"],
            detected_at=datetime.fromisoformat(row["detected_at"]),
            pump_percent=row["pump_percent"],
            price_at_detection=row["price_at_detection"],
            price_before_pump=row["price_before_pump"],
            highest_price=row["highest_price"] or 0,
            lowest_price=row["lowest_price"] or 0,
            last_checked_price=row["last_checked_price"] or 0,
            last_checked_at=datetime.fromisoformat(row["last_checked_at"]) if row["last_checked_at"] else None,
            time_to_25pct_retrace=row["time_to_25pct_retrace"],
            time_to_50pct_retrace=row["time_to_50pct_retrace"],
            time_to_75pct_retrace=row["time_to_75pct_retrace"],
            time_to_100pct_retrace=row["time_to_100pct_retrace"],
            max_drop_from_high_pct=row["max_drop_from_high_pct"] or 0,
            returned_to_prepump=bool(row["returned_to_prepump"]),
            status=PumpStatus(row["status"]),
            monitoring_ends_at=datetime.fromisoformat(row["monitoring_ends_at"]) if row["monitoring_ends_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )
    
    # ==================== Statistics ====================
    
    async def get_coin_stats(self, symbol: str) -> CoinStats | None:
        """Calculate statistics for a specific coin."""
        cursor = await self._conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN time_to_25pct_retrace IS NOT NULL THEN 1 ELSE 0 END) as hit_25,
                SUM(CASE WHEN time_to_50pct_retrace IS NOT NULL THEN 1 ELSE 0 END) as hit_50,
                SUM(CASE WHEN time_to_75pct_retrace IS NOT NULL THEN 1 ELSE 0 END) as hit_75,
                SUM(CASE WHEN time_to_100pct_retrace IS NOT NULL THEN 1 ELSE 0 END) as hit_100,
                AVG(time_to_50pct_retrace) as avg_time_50,
                AVG(time_to_100pct_retrace) as avg_time_100,
                AVG(max_drop_from_high_pct) as avg_drop,
                SUM(CASE WHEN returned_to_prepump = 1 THEN 1 ELSE 0 END) as full_reversal
            FROM pump_records 
            WHERE symbol = ? AND status != 'monitoring'
        """, (symbol,))
        
        row = await cursor.fetchone()
        
        if not row or row["total"] == 0:
            return None
        
        return CoinStats(
            symbol=symbol,
            total_pumps=row["total"],
            pumps_hit_25pct=row["hit_25"] or 0,
            pumps_hit_50pct=row["hit_50"] or 0,
            pumps_hit_75pct=row["hit_75"] or 0,
            pumps_hit_100pct=row["hit_100"] or 0,
            avg_time_to_50pct_seconds=row["avg_time_50"],
            avg_time_to_100pct_seconds=row["avg_time_100"],
            avg_max_drop_from_high=row["avg_drop"] or 0,
            full_reversal_count=row["full_reversal"] or 0,
            last_updated=datetime.utcnow(),
        )
    
    async def get_global_stats(self) -> GlobalStats:
        """Calculate global statistics across all coins."""
        # Overall stats - only count successes from COMPLETED pumps
        cursor = await self._conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'monitoring' THEN 1 ELSE 0 END) as monitoring,
                SUM(CASE WHEN status != 'monitoring' AND time_to_50pct_retrace IS NOT NULL THEN 1 ELSE 0 END) as hit_50,
                SUM(CASE WHEN status != 'monitoring' AND returned_to_prepump = 1 THEN 1 ELSE 0 END) as full_reversal,
                AVG(CASE WHEN time_to_50pct_retrace IS NOT NULL THEN time_to_50pct_retrace END) as avg_time_50,
                AVG(CASE WHEN time_to_100pct_retrace IS NOT NULL THEN time_to_100pct_retrace END) as avg_time_100
            FROM pump_records
        """)
        overall = await cursor.fetchone()
        
        # Today's stats - only count successes from COMPLETED pumps
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor = await self._conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status != 'monitoring' AND time_to_50pct_retrace IS NOT NULL THEN 1 ELSE 0 END) as hit_50
            FROM pump_records
            WHERE detected_at >= ?
        """, (today_start.isoformat(),))
        today = await cursor.fetchone()
        
        # Top performers (min 2 completed pumps, sorted by FULL REVERSAL rate)
        cursor = await self._conn.execute("""
            SELECT 
                symbol,
                COUNT(*) as total,
                SUM(CASE WHEN returned_to_prepump = 1 THEN 1 ELSE 0 END) as full_reversals,
                CAST(SUM(CASE WHEN returned_to_prepump = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as rate
            FROM pump_records
            WHERE status != 'monitoring'
            GROUP BY symbol
            HAVING total >= 2
            ORDER BY rate DESC, total DESC
            LIMIT 5
        """)
        top_rows = await cursor.fetchall()
        top_coins = [(row["symbol"], row["rate"], row["total"]) for row in top_rows]
        
        # Worst performers (min 2 completed pumps, sorted by FULL REVERSAL rate)
        cursor = await self._conn.execute("""
            SELECT 
                symbol,
                COUNT(*) as total,
                SUM(CASE WHEN returned_to_prepump = 1 THEN 1 ELSE 0 END) as full_reversals,
                CAST(SUM(CASE WHEN returned_to_prepump = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as rate
            FROM pump_records
            WHERE status != 'monitoring'
            GROUP BY symbol
            HAVING total >= 2
            ORDER BY rate ASC, total DESC
            LIMIT 3
        """)
        worst_rows = await cursor.fetchall()
        worst_coins = [(row["symbol"], row["rate"], row["total"]) for row in worst_rows]
        
        return GlobalStats(
            total_pumps=overall["total"] or 0,
            active_monitoring=overall["monitoring"] or 0,
            total_hit_50pct=overall["hit_50"] or 0,
            total_full_reversal=overall["full_reversal"] or 0,
            avg_time_to_50pct_seconds=overall["avg_time_50"],
            avg_time_to_100pct_seconds=overall["avg_time_100"],
            today_pumps=today["total"] or 0,
            today_hit_50pct=today["hit_50"] or 0,
            top_coins=top_coins,
            worst_coins=worst_coins,
            last_updated=datetime.utcnow(),
        )
    
    async def get_last_n_results(self, symbol: str, n: int = 5) -> list[bool]:
        """Get last N pump results for a coin (True = hit 50%, False = didn't)."""
        cursor = await self._conn.execute("""
            SELECT time_to_50pct_retrace IS NOT NULL as success
            FROM pump_records
            WHERE symbol = ? AND status != 'monitoring'
            ORDER BY detected_at DESC
            LIMIT ?
        """, (symbol, n))
        rows = await cursor.fetchall()
        return [bool(row["success"]) for row in rows]
    
    # ==================== Pinned Messages ====================
    
    async def save_pinned_message(
        self,
        chat_id: str,
        message_id: int,
        message_type: str,
    ) -> None:
        """Save pinned message info."""
        await self._conn.execute("""
            INSERT OR REPLACE INTO pinned_messages (id, chat_id, message_id, message_type)
            VALUES (
                (SELECT id FROM pinned_messages WHERE chat_id = ? AND message_type = ?),
                ?, ?, ?
            )
        """, (chat_id, message_type, chat_id, message_id, message_type))
        await self._conn.commit()
    
    async def get_pinned_message(
        self,
        chat_id: str,
        message_type: str,
    ) -> int | None:
        """Get pinned message ID."""
        cursor = await self._conn.execute("""
            SELECT message_id FROM pinned_messages
            WHERE chat_id = ? AND message_type = ?
        """, (chat_id, message_type))
        row = await cursor.fetchone()
        return row["message_id"] if row else None

