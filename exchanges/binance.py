import aiohttp

BASE_URL = "https://api.binance.com"

async def place_order(api_key, api_secret, signal):
    """Place an order on Binance."""
    url = f"{BASE_URL}/api/v3/order"
    headers = {
        "X-MBX-APIKEY": api_key,
    }

    payload = {
        "symbol": signal.symbol,
        "side": signal.action.upper(),
        "type": "MARKET",
        "quantity": signal.quantity,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}
