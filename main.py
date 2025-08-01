from core.price_feed import MexcPriceFeed
from core.signal_logic import PumpDetector
from core.telegram_alert import TelegramAlert
import time
import datetime


def main():
    feed = MexcPriceFeed()
    detector = PumpDetector()
    alert = TelegramAlert()

    print("[+] Starting MEXC Pump Watcher Bot...")
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
            print(f"  └─ Checking {symbol}...", end=" ")
            candles = feed.get_recent_1m_candles(symbol)
            if not candles:
                print("no data")
                continue
            signal = detector.check_pump(symbol, candles)
            if signal:
                alert.send_message(signal)
                print("🚨 SIGNAL")
            else:
                print("ok")
        time.sleep(10)


if __name__ == "__main__":
    main()
