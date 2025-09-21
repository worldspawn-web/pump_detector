from api import MexcClient
from plots import plot_1min_chart, plot_1h_chart_with_indicators
from telegram import TelegramNotifier
from config import (
    PUMP_THRESHOLD_PERCENT,
    PUMP_WINDOW_MINUTES,
    MIN_VOLUME_USDT,
    BLACKLIST_FILE
)
from utils import logger
import json
import time
import schedule

class PumpDetector:
    def __init__(self):
        self.mexc = MexcClient()
        self.telegram = TelegramNotifier()
        self.blacklist = self.load_blacklist()

    def load_blacklist(self) -> set:
        """Загрузить чёрный список из JSON."""
        try:
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except FileNotFoundError:
            logger.warning("Blacklist file not found, creating empty one.")
            return set()
        except Exception as e:
            logger.error(f"Error loading blacklist: {e}")
            return set()

    def save_blacklist(self):
        """Сохранить чёрный список в JSON."""
        try:
            with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(self.blacklist), f, indent=2, ensure_ascii=False)
            logger.info("Blacklist saved")
        except Exception as e:
            logger.error(f"Error saving blacklist: {e}")

    def is_pump(self, symbol: str, ohlcv_data) -> dict:
        """Проверить, был ли памп. Возвращает словарь с данными или None."""
        if not ohlcv_data or len(ohlcv_data) < PUMP_WINDOW_MINUTES:
            return None

        closes = [candle[4] for candle in ohlcv_data]  # close prices
        start_price = closes[0]
        end_price = closes[-1]

        if start_price <= 0:
            return None

        change_percent = ((end_price / start_price) - 1) * 100
        volume = sum(candle[5] for candle in ohlcv_data)  # total volume

        if change_percent >= PUMP_THRESHOLD_PERCENT and volume >= MIN_VOLUME_USDT:
            return {
                "symbol": symbol,
                "change_percent": change_percent,
                "start_price": start_price,
                "end_price": end_price,
                "volume": volume,
            }
        return None