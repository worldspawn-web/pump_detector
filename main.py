import asyncio
import datetime
from core.price_feed import BinancePriceFeed
from core.signal_logic import PumpDetector
from core.telegram_alert import TelegramAlert
from core.plot_generator import ChartGenerator


async def main():
    feed = BinancePriceFeed()
    detector = PumpDetector(threshold=3)  # Порог снижен с 5% до 3%
    alert = TelegramAlert()
    chart = ChartGenerator()

    print("[+] Starting Binance Pump Watcher Bot...")
    startup_message = alert.send_message("🤖 Bot started")

    if startup_message:
        await asyncio.sleep(10)
        alert.delete_message(startup_message["message_id"])

    while True:
        print(f"[~] Scanning at {datetime.datetime.utcnow().strftime('%H:%M:%S')}...")
        candles_data = await feed.get_all_candles()
        funding_rates = await feed.get_all_funding_rates()

        for symbol, candles in candles_data.items():
            if not candles:
                print(f"  └─ {symbol}: no data")
                continue
            funding = funding_rates.get(symbol, "N/A")
            result = detector.check_pump(symbol, candles, funding=funding, verbose=True)
            if isinstance(result, str):
                if detector.should_alert(symbol):
                    image_path = chart.generate_chart(symbol, candles)
                    alert.send_photo(result, image_path)
                    detector.register_alert(symbol)
                    print(f"  └─ {symbol}: 🚨 SIGNAL")

        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
