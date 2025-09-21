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
    
    def monitor_symbols(self):
        """Основной цикл мониторинга всех символов."""
        logger.info("Starting pump monitoring cycle...")
        symbols = self.mexc.get_all_symbols()

        for symbol in symbols:
            if symbol in self.blacklist:
                continue

            # Получаем последние N минут
            ohlcv = self.mexc.fetch_ohlcv(symbol, '1m', limit=PUMP_WINDOW_MINUTES + 5)
            if not ohlcv:
                continue

            pump_data = self.is_pump(symbol, ohlcv)
            if pump_data:
                logger.info(f"PUMP DETECTED: {symbol} +{pump_data['change_percent']:.2f}%")

                # Генерируем графики
                chart_1m = plot_1min_chart(symbol, ohlcv)
                chart_1h = plot_1h_chart_with_indicators(symbol, self.mexc.fetch_ohlcv(symbol, '1h', limit=48))

                # Формируем сообщение
                message = (
                    f"<b>🚨 PUMP DETECTED 🚨</b>\n"
                    f"<b>Монета:</b> {symbol}\n"
                    f"<b>Рост:</b> {pump_data['change_percent']:.2f}%\n"
                    f"<b>Цена:</b> {pump_data['start_price']:.8f} → {pump_data['end_price']:.8f}\n"
                    f"<b>Объём:</b> {pump_data['volume']:,.0f} USDT\n"
                    f"<b>Биржа:</b> MEXC\n"
                    f"<a href='https://www.mexc.com/exchange/{symbol.replace('/', '')}'>Открыть график</a>"
                )

                # Отправляем
                self.telegram.send_message(message)
                if chart_1m:
                    self.telegram.send_photo(chart_1m, caption="1-минутный график")
                if chart_1h:
                    self.telegram.send_photo(chart_1h, caption="1-часовой график с индикаторами")

                # Чтобы не спамить — добавляем в blacklist на 1 час (опционально)
                # self.blacklist.add(symbol)
                # self.save_blacklist()

                # Пауза, чтобы не перегружать Telegram API
                time.sleep(2)

        logger.info("Monitoring cycle completed.")

def main():
    detector = PumpDetector()

    # Запуск каждые 5 минут
    schedule.every(5).minutes.do(detector.monitor_symbols)

    logger.info("Bot started. Monitoring every 5 minutes...")

    # Первый запуск сразу
    detector.monitor_symbols()

    # Бесконечный цикл
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()