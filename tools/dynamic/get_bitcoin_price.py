"""
Dynamically created tool: get_bitcoin_price
Task: fetch current BTC/USD price from CoinGecko public API: https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd
"""

def get_bitcoin_price() -> str:
    """Fetch the current BTC/USD price from the CoinGecko public API.

    Args:
        None

    Returns:
        A formatted string containing the BTC price in USD or an error message.
    """
    import urllib.request
    import json
    
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            price = data.get('bitcoin', {}).get('usd')
            if price is not None:
                return f"Current BTC/USD price: ${price:,.2f}"
            else:
                return "Error: Could not parse price from API response."
    except Exception as e:
        return f"Error: Unable to fetch price - {str(e)}"
