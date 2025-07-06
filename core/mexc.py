import requests

def get_mexc_symbols():
    url = "https://api.mexc.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        symbols = [item["symbol"] for item in data.get("symbols", []) if item.get("quoteAsset") == "USDT"]
        return symbols
    except Exception as error:
        print(f"[MEXC ERROR] Failed to fetch trading pairs: {error}")
        return []

def get_all_mexc_prices():
    url = "https://api.mexc.com/api/v3/ticker/price"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {item["symbol"]: float(item["price"]) for item in data}
    except Exception as error:
        print(f"[MEXC ERROR] Failed to fetch all prices: {error}")
        return {}
