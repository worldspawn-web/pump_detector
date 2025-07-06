from core.mexc import get_mexc_symbols, get_all_mexc_prices
from core.dex import get_dex_data_by_symbol
import logging
import asyncio
import aiohttp


def calculate_spread(dex_price: float, mexc_price: float) -> float:
    return (dex_price - mexc_price) / mexc_price * 100


async def scan_market_for_signals():
    logging.info("Запущен анализ рынка...")
    results = []
    symbols = get_mexc_symbols()
    prices = get_all_mexc_prices()
    logging.info(f"Получено {len(symbols)} пар с MEXC. Начинаем проверку на объём и спред...")

    filtered = [(s.replace("USDT", ""), s) for s in symbols if s.endswith("USDT") and s in prices]

    async def process_symbol(session, base_symbol, full_symbol):
        mexc_price = prices.get(full_symbol)
        dex_data = await get_dex_data_by_symbol(session, base_symbol)
        if not dex_data:
            logging.debug(f"{base_symbol} — нет данных на DEX или объём < $50k, пропускаем")
            return None
        spread = calculate_spread(dex_data['price'], mexc_price)
        logging.info(f"{base_symbol} | MEXC: {mexc_price:.6f}, DEX: {dex_data['price']:.6f}, Объём: ${dex_data['volume']:.0f}, Спред: {spread:.2f}%")
        if spread >= 10:
            logging.info(f"💰 СИГНАЛ: {base_symbol} — {spread:.2f}%")
            return {
                "symbol": base_symbol,
                "mexc_price": mexc_price,
                "dex_price": dex_data['price'],
                "spread": spread,
                "dex_volume": dex_data['volume']
            }
        return None

    async with asyncio.Semaphore(10):
        async with aiohttp.ClientSession() as session:
            tasks = [process_symbol(session, base, full) for base, full in filtered]
            responses = await asyncio.gather(*tasks)
            results = [r for r in responses if r]

    logging.info(f"✅ Проверено: {len(filtered)} токенов. Найдено сигналов: {len(results)}")
    return results
