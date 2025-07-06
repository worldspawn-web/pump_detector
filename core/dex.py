import aiohttp
import asyncio
import logging

async def get_dex_data_by_symbol(session, symbol: str):
    from urllib.parse import quote
    encoded_symbol = quote(symbol)
    url = f"https://api.dexscreener.com/latest/dex/search/?q={encoded_symbol}"
    headers = {"Accept": "application/json"}
    try:
        async with session.get(url, timeout=10, headers=headers) as response:
            if response.status == 429:
                logging.warning(f"[DEX ERROR] Rate limit for {symbol}. Skipping.")
                return None
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                text = await response.text()
                logging.warning(f"[DEX ERROR] Unexpected content-type for {symbol}: {content_type}, text: {text[:100]}")
                return None
            try:
                data = await response.json()
            except Exception as json_error:
                logging.warning(f"[DEX ERROR] Failed to parse JSON for {symbol}: {json_error}")
                return None
            if not isinstance(data, dict):
                text = await response.text()
                if '<html>' in text:
                    logging.warning(f"[DEX ERROR] Invalid token for {symbol}. Raw response looks like HTML. Skipping.")
                    return None
                clean_text = text.replace(chr(10), ' ').replace(chr(13), ' ')
                logging.warning(
                    f"[DEX ERROR] Invalid JSON response for {symbol}: not a dict. Raw text: {clean_text[:200]}")
                return None
            for pair in data.get("pairs", []):
                if not isinstance(pair, dict):
                    continue
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
    except Exception as e:
        logging.warning(f"[DEX ERROR] Failed to search DEX price for {symbol}: {e}")
        return None
