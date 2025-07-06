from core.mexc import get_mexc_symbols, get_all_mexc_prices
from core.dex import get_dex_data_by_symbol
import logging
import time

def calculate_spread(dex_price: float, mexc_price: float) -> float:
    return (dex_price - mexc_price) / mexc_price * 100

def scan_market_for_signals():
    logging.info("Запущен анализ рынка...")
    results = []
    symbols = get_mexc_symbols()
    prices = get_all_mexc_prices()
    logging.info(f"Найдено {len(symbols)} пар для анализа.")

    for index, full_symbol in enumerate(symbols):
        if not full_symbol.endswith("USDT"):
            continue

        base_symbol = full_symbol.replace("USDT", "")
        logging.info(f"▶️ [{index + 1}/{len(symbols)}] Проверка: {base_symbol}")

        mexc_price = prices.get(full_symbol)
        if not mexc_price:
            logging.debug(f"{base_symbol} — нет цены на MEXC, пропускаем")
            continue

        dex_data = get_dex_data_by_symbol(base_symbol)
        time.sleep(1)

        if not dex_data:
            logging.debug(f"{base_symbol} — нет данных на DEX, пропускаем")
            continue

        spread = calculate_spread(dex_data['price'], mexc_price)

        logging.info(f"{base_symbol} | MEXC: {mexc_price:.6f}, DEX: {dex_data['price']:.6f}, Объём: ${dex_data['volume']:.0f}, Спред: {spread:.2f}%")

        if spread >= 10 and dex_data['volume'] >= 5000:
            logging.info(f"💰 СИГНАЛ: {base_symbol} — {spread:.2f}%")
            results.append({
                "symbol": base_symbol,
                "mexc_price": mexc_price,
                "dex_price": dex_data['price'],
                "spread": spread,
                "dex_volume": dex_data['volume']
            })

    logging.info(f"Анализ завершён. Найдено сигналов: {len(results)}")
    return results