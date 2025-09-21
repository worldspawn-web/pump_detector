import ccxt
from config import MEXC_SYMBOL_FILTER
from utils import logger

class MexcClient:
    def __init__(self):
        self.exchange = ccxt.mexc({
            'enableRateLimit': True,
            'timeout': 10000,
            'options': {
                'defaultType': 'future'
            }
        })
        logger.info("MEXC client initialized")

    def get_all_symbols(self) -> list:
        """Получить все торговые пары, оканчивающиеся на USDT."""
        try:
            markets = self.exchange.load_markets()
            symbols = [
                symbol for symbol in markets.keys()
                if symbol.endswith(f"/{MEXC_SYMBOL_FILTER}")
            ]
            logger.info(f"Loaded {len(symbols)} symbols")
            return symbols
        except Exception as e:
            logger.error(f"Error loading symbols: {e}")
            return []

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 15):
        """Получить OHLCV данные для символа."""
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.warning(f"Failed to fetch OHLCV for {symbol}: {e}")
            return None