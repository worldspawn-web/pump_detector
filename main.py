from core.price_feed import BinancePriceFeed
from core.signal_logic import PumpDetector
from core.telegram_alert import TelegramAlert
import time
import datetime


def main():
    feed = BinancePriceFeed()
    detector = PumpDetector()
    alert = TelegramAlert()

    print("[+] Starting Binance Pump Watcher Bot...")
    startup_message = alert.send_message(
        "🤖 Bot started at {}".format(
            datetime.datetime.utcnow().strftime("%H:%M:%S UTC")
        )
    )

    if startup_message:
        time.sleep(10)
        alert.delete_message(startup_message["message_id"])

    while True:
        print(f"[~] Scanning at {datetime.datetime.utcnow().strftime('%H:%M:%S')}...")
        for symbol in feed.get_watchlist():
            candles = feed.get_recent_1m_candles(symbol)
            if not candles:
                print(f"  └─ {symbol}: no data")
                continue
            result = detector.check_pump(symbol, candles, verbose=True)
            if isinstance(result, str):
                alert.send_message(result)
                print(f"  └─ {symbol}: 🚨 SIGNAL")
        time.sleep(10)


if __name__ == "__main__":
    main()
