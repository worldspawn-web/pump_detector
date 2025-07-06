from core.mexc import get_mexc_symbols, get_mexc_price
from core.dex import get_dex_data_by_symbol
import logging
import time

def calculate_spread(dex_price: float, mexc_price: float) -> float:
    return (dex_price - mexc_price) / mexc_price * 100

def scan_market_for_signals():
    logging.info("Запущен анализ рынка...")
    results = []
    symbols = get_mexc_symbols()
    logging.info(f"Найдено {len(symbols)} пар для анализа.")

    for full_symbol in symbols:
        if not full_symbol.endswith("USDT"):
            continue

        base_symbol = full_symbol.replace("USDT", "")
        logging.debug(f"Обрабатываем: {base_symbol}")

        mexc_price = get_mexc_price(full_symbol)
        dex_data = get_dex_data_by_symbol(base_symbol)

        if not dex_data or not mexc_price:
            time.sleep(0.5)
            continue

        spread = calculate_spread(dex_data['price'], mexc_price)

        logging.debug(f"{base_symbol} — спред: {spread:.2f}% при объёме {dex_data['volume']:.2f}")

        if spread >= 10 and dex_data['volume'] >= 5000:
            logging.info(f"НАЙДЕН СИГНАЛ: {base_symbol} — {spread:.2f}%")
            results.append({
                "symbol": base_symbol,
                "mexc_price": mexc_price,
                "dex_price": dex_data['price'],
                "spread": spread,
                "dex_volume": dex_data['volume']
            })

        time.sleep(0.5)

    logging.info(f"Анализ завершён. Найдено сигналов: {len(results)}")
    return results
