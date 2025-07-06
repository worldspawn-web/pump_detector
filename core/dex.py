import aiohttp
import asyncio
import logging

async def get_dex_data_by_symbol(session, symbol: str):
    url = f"https://api.dexscreener.com/latest/dex/search/?q={symbol}"
    headers = {"Accept": "application/json"}
    try:
        async with session.get(url, timeout=10, headers=headers) as response:
            if response.status == 429:
                logging.warning(f"[DEX ERROR] Rate limit for {symbol}. Skipping.")
                return None
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                logging.warning(f"[DEX ERROR] Unexpected content-type for {symbol}: {content_type}")
                return None
            data = await response.json()
            for pair in data.get("pairs", []):
                if pair.get("chainId") == "bsc" and "USDT" in pair.get("baseToken", {}).get("symbol", ""):
                    price = float(pair.get("priceUsd", 0))
                    volume = float(pair.get("volume", {}).get("h24", 0))
                    if volume < 50000:
                        return None
                    return {
                        "symbol": symbol,
                        "price": price,
                        "volume": volume
                    }
            return None
    except Exception as error:
        logging.warning(f"[DEX ERROR] Failed to search DEX price for {symbol}: {error}")
        return None
