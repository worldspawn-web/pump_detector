import asyncio
import datetime
import argparse
from core.price_feed import BinancePriceFeed
from core.signal_logic import PumpDetector
from core.telegram_alert import TelegramAlert
from core.plot_generator import ChartGenerator, get_hourly_levels


async def test_signal(symbol: str):
    feed = BinancePriceFeed()
    chart = ChartGenerator()
    detector = PumpDetector(threshold=3)
    alert = TelegramAlert()

    candles_data = await feed.get_recent_1m_candles_for_symbol(symbol)
    if not candles_data:
        print(f"[!] No data for {symbol}")
        return

    funding_rates = await feed.get_all_funding_rates()
    funding = funding_rates.get(symbol, "N/A")
    result = detector.check_pump(symbol, candles_data, funding=funding, verbose=True)
    support, resistance = await get_hourly_levels(symbol)
    image_path = chart.generate_chart(
        symbol, candles_data, support=support, resistance=resistance
    )
    caption = result or f"📊 <b>TEST SIGNAL</b>\nCoin: <code>{symbol}</code>"
    alert.send_photo(caption, image_path)
    print(f"[+] Test signal sent for {symbol}")


async def main_loop():
    feed = BinancePriceFeed()
    detector = PumpDetector(threshold=3)
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
                    support, resistance = await get_hourly_levels(symbol)
                    image_path = chart.generate_chart(
                        symbol, candles, support=support, resistance=resistance
                    )
                    alert.send_photo(result, image_path)
                    detector.register_alert(symbol)
                    print(f"  └─ {symbol}: 🚨 SIGNAL")

        await asyncio.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", help="Run test signal for given symbol", type=str)
    args = parser.parse_args()

    if args.test:
        asyncio.run(test_signal(args.test.upper()))
    else:
        asyncio.run(main_loop())
