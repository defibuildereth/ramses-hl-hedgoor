import json
import websocket
import requests

# Constants
Q96 = 2**96
ETH = 10**18

def create_websocket():
    return websocket.WebSocketApp("wss://api.hyperliquid.xyz/ws",
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close,
                                  on_open=on_open)

def on_message(ws, message):
    data = json.loads(message)
    if data.get('channel') == 'allMids':
        mids = data.get('data', {}).get('mids', {})
        return mids.get('ZRO'), mids.get('ETH')
    return None, None

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def on_open(ws):
    subscribe_message = {
        "method": "subscribe",
        "subscription": {"type": "allMids"}
    }
    ws.send(json.dumps(subscribe_message))

def get_user_positions(user_address):
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    payload = {
        "type": "clearinghouseState",
        "user": user_address
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        positions = {}
        for asset_position in data.get("assetPositions", []):
            position = asset_position.get("position", {})
            coin = position.get("coin")
            if coin:
                positions[coin] = {
                    "size": float(position.get("szi", 0)),
                    "entry_price": float(position.get("entryPx", 0)),
                    "liquidation_price": float(position.get("liquidationPx", 0) or 0),
                    "unrealized_pnl": float(position.get("unrealizedPnl", 0)),
                    "leverage": position.get("leverage", {}).get("value", 0),
                    "position_value": float(position.get("positionValue", 0)),
                }

        return {
            "positions": positions,
            "account_value": float(data.get("marginSummary", {}).get("accountValue", 0)),
            "total_margin_used": float(data.get("marginSummary", {}).get("totalMarginUsed", 0)),
            "total_notional_position": float(data.get("marginSummary", {}).get("totalNtlPos", 0)),
            "withdrawable": float(data.get("withdrawable", 0))
        }

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def tick_to_sqrtp(t):
    return int((1.0001 ** (t / 2)) * Q96)

def calc_amount0(liq, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return int(liq * Q96 * (pb - pa) / pb / pa)

def calc_amount1(liq, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return int(liq * (pb - pa) / Q96)

def calculate_token_amounts(zro_eth_ratio, tick_lower, tick_upper, liquidity_dict):
    if isinstance(liquidity_dict, dict):
        liquidity = int(liquidity_dict['hex'], 16)
    elif isinstance(liquidity_dict, str):
        liquidity = int(liquidity_dict, 16)
    else:
        raise ValueError("liquidity_dict must be either a dictionary or a hex string")

    sqrtp_lower = tick_to_sqrtp(tick_lower)
    sqrtp_upper = tick_to_sqrtp(tick_upper)

    sqrtp_current = int((max(zro_eth_ratio, 1e-18) ** 0.5) * Q96)

    if sqrtp_current < sqrtp_lower:
        amount0 = calc_amount0(liquidity, sqrtp_lower, sqrtp_upper)
        amount1 = 0
    elif sqrtp_current > sqrtp_upper:
        amount0 = 0
        amount1 = calc_amount1(liquidity, sqrtp_lower, sqrtp_upper)
    else:
        amount0 = calc_amount0(liquidity, sqrtp_current, sqrtp_upper)
        amount1 = calc_amount1(liquidity, sqrtp_lower, sqrtp_current)

    token0_amount = amount0 / ETH  # ZRO amount
    token1_amount = amount1 / ETH  # WETH amount

    return token0_amount, token1_amount