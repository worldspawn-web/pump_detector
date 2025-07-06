import requests

def get_dex_price(token_address: str):
    url = f"https://api.dexscreener.com/latest/dex/pairs/bsc/{token_address}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        pair_data = data.get("pair")
        if not pair_data:
            raise ValueError("No pair data found for this token.")

        price_usd = float(pair_data["priceUsd"])
        volume_usd = float(pair_data["volume"].get("h24", 0))

        return {
            "price": price_usd,
            "volume": volume_usd
        }

    except (requests.RequestException, ValueError) as error:
        print(f"[DEX ERROR] Failed to get DEX price: {error}")
        return None