import requests
import logging

def get_dex_data_by_symbol(symbol: str):
    url = f"https://api.dexscreener.com/latest/dex/search/?q={symbol}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        for pair in data.get("pairs", []):
            if pair.get("chainId") == "bsc" and "USDT" in pair.get("baseToken", {}).get("symbol", ""):
                price = float(pair.get("priceUsd", 0))
                volume = float(pair.get("volume", {}).get("h24", 0))
                return {
                    "price": price,
                    "volume": volume
                }

        return None

    except Exception as error:
        logging.warning(f"[DEX ERROR] Failed to search DEX price for {symbol}: {error}")
        return None