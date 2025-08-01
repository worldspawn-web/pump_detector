import asyncio
import datetime
from core.price_feed import BinancePriceFeed
from core.signal_logic import PumpDetector
from core.telegram_alert import TelegramAlert


async def main():
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
        await asyncio.sleep(10)
        alert.delete_message(startup_message["message_id"])

    while True:
        print(f"[~] Scanning at {datetime.datetime.utcnow().strftime('%H:%M:%S')}...")
        candles_data = await feed.get_all_candles()

        for symbol, candles in candles_data.items():
            if not candles:
                print(f"  └─ {symbol}: no data")
                continue
            result = detector.check_pump(symbol, candles, verbose=True)
            if isinstance(result, str):
                alert.send_message(result)
                print(f"  └─ {symbol}: 🚨 SIGNAL")

        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
