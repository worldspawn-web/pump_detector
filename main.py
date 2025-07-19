from core.market_data import BinanceMarketData
from core.signal_engine import SignalEngine
from tqdm import tqdm


def main():
    market = BinanceMarketData()
    engine = SignalEngine(market)

    print("[+] Starting pump short bot...")
    symbols = market.get_active_symbols()

    for symbol_data in tqdm(symbols, desc="Scanning symbols", ncols=100):
        signal = engine.check_signal(symbol_data["symbol"])
        if signal:
            print(signal)


if __name__ == "__main__":
    main()
