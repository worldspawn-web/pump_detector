from core.price_feed import MexcPriceFeed
from core.signal_logic import PumpDetector
from core.telegram_alert import TelegramAlert
import time


def main():
    feed = MexcPriceFeed()
    detector = PumpDetector()
    alert = TelegramAlert()

    print("[+] Starting MEXC Pump Watcher Bot...")
    while True:
        for symbol in feed.get_watchlist():
            candles = feed.get_recent_1m_candles(symbol)
            if not candles:
                continue
            signal = detector.check_pump(symbol, candles)
            if signal:
                alert.send_message(signal)
        time.sleep(10)


if __name__ == "__main__":
    main()
