"""Watchlist management for core coins."""

from pathlib import Path

from loguru import logger


class WatchlistManager:
    """Manages the watchlist of coins to monitor."""

    def __init__(self, watchlist_file: str) -> None:
        """Initialize watchlist manager.
        
        Args:
            watchlist_file: Path to watchlist file.
        """
        self._file_path = Path(watchlist_file)
        self._coins: set[str] = set()
        
    def load(self) -> None:
        """Load coins from watchlist file."""
        if not self._file_path.exists():
            logger.warning(f"Watchlist file not found: {self._file_path}")
            logger.info("Creating empty watchlist file...")
            self._file_path.write_text("# Add coin symbols one per line (without _USDT suffix)\n")
            return
            
        try:
            content = self._file_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            
            # Filter out comments and empty lines
            coins = [
                line.strip().upper()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
            
            self._coins = set(coins)
            logger.info(f"Loaded {len(self._coins)} coins from watchlist: {', '.join(sorted(self._coins))}")
            
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")
            self._coins = set()
    
    def reload(self) -> None:
        """Reload watchlist from file."""
        old_count = len(self._coins)
        self.load()
        new_count = len(self._coins)
        
        if new_count != old_count:
            logger.info(f"Watchlist updated: {old_count} -> {new_count} coins")
    
    def is_watched(self, symbol: str) -> bool:
        """Check if a symbol is in the watchlist.
        
        Args:
            symbol: Symbol to check (e.g., "BTC_USDT" or "BTC").
            
        Returns:
            True if symbol is watched.
        """
        # Handle both formats: BTC_USDT and BTC
        coin = symbol.replace("_USDT", "").upper()
        return coin in self._coins
    
    @property
    def coins(self) -> set[str]:
        """Get all watched coins."""
        return self._coins.copy()
    
    @property
    def count(self) -> int:
        """Get number of watched coins."""
        return len(self._coins)

