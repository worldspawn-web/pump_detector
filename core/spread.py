def calculate_spread(dex_price: float, mexc_price: float) -> float:
    return (dex_price - mexc_price) / mexc_price * 100

def evaluate_signal(token_address: str, mexc_symbol: str) -> dict | None:
    from core.dex import get_dex_price
    from core.mexc import get_mexc_price

    dex_data = get_dex_price(token_address)
    mexc_price = get_mexc_price(mexc_symbol)

    if not dex_data or not mexc_price:
        return None

    spread = calculate_spread(dex_data['price'], mexc_price)

    if spread >= 10:
        return {
            "dex_price": dex_data['price'],
            "mexc_price": mexc_price,
            "spread": spread,
            "dex_volume": dex_data['volume']
        }

    return None
