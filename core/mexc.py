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

def get_mexc_price(symbol: str):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        price = float(data.get("price"))
        return price

    except (requests.RequestException, ValueError, TypeError) as error:
        print(f"[MEXC ERROR] Failed to get MEXC price: {error}")
        return None