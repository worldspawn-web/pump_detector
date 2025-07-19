from core.market_data import BinanceMarketData
from core.signal_engine import SignalEngine


def main():
    market = BinanceMarketData()
    engine = SignalEngine(market)

    print("[+] Starting pump short bot...")
    for symbol_data in market.get_active_symbols():
        signal = engine.check_signal(symbol_data["symbol"])
        if signal:
            print(signal)


if __name__ == "__main__":
    main()
