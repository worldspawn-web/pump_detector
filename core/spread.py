from core.mexc import get_mexc_symbols, get_mexc_price
from core.dex import get_dex_data_by_symbol

def calculate_spread(dex_price: float, mexc_price: float) -> float:
    return (dex_price - mexc_price) / mexc_price * 100

def scan_market_for_signals():
    results = []
    symbols = get_mexc_symbols()

    for full_symbol in symbols:
        if not full_symbol.endswith("USDT"):
            continue

        base_symbol = full_symbol.replace("USDT", "")
        mexc_price = get_mexc_price(full_symbol)
        dex_data = get_dex_data_by_symbol(base_symbol)

        if not dex_data or not mexc_price:
            continue

        spread = calculate_spread(dex_data['price'], mexc_price)

        if spread >= 10 and dex_data['volume'] >= 5000:
            results.append({
                "symbol": base_symbol,
                "mexc_price": mexc_price,
                "dex_price": dex_data['price'],
                "spread": spread,
                "dex_volume": dex_data['volume']
            })

    return results
