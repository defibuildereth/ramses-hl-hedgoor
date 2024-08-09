import time
from hyperliquid.utils import constants
import utils
import json
import subprocess
import websocket
import threading
import requests

# user input

interval = 60
userAddress = '0x7EEE7bC996F430232caF838EE7F6fb0eFEC44CDF'

# constants
q96 = 2**96
eth = 10**18

# Global variable to store NFT details
latest_zro_price = None
latest_eth_price = None
max_eth_exposure = None
nft_details = None


def trade(coin, is_buy, sz):
    address, info, exchange = utils.setup(
        constants.MAINNET_API_URL, skip_ws=True)

    print(f"We try to Market {'Buy' if is_buy else 'Sell'} {sz} {coin}.")

    order_result = exchange.market_open(coin, is_buy, sz, None, 0.01)
    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(
                    f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
                return filled["totalSz"] * filled["avgPx"]
            except KeyError:
                print(f'Error: {status["error"]}')

def get_user_positions(user_address):
    url = "https://api.hyperliquid.xyz/info"
    headers = {
        "Content-Type": "application/json"
    }
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
                    "liquidation_price": float(position.get("liquidationPx", 0)),
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


def on_message(ws, message):
    global latest_zro_price, latest_eth_price
    data = json.loads(message)
    if data.get('channel') == 'allMids':
        mids = data.get('data', {}).get('mids', {})
        latest_zro_price = mids.get('ZRO')
        latest_eth_price = mids.get('ETH')
        # if latest_zro_price and latest_eth_price:
        #     print(
        #         f"ZRO price: {latest_zro_price}, ETH price: {latest_eth_price}")


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")


def findNft(address):
    result = subprocess.run(['node', 'getNFT.js', address],
                            capture_output=True, text=True)
    try:
        output = json.loads(result.stdout)
        if 'tokenId' in output:
            print(f"Token ID: {output['tokenId']}")
            return str(output['tokenId'])
        else:
            print(f"Error: {output['error']}")
    except json.JSONDecodeError:
        print("Error: Unable to parse output")


def on_open(ws):
    subscribe_message = {
        "method": "subscribe",
        "subscription": {"type": "allMids"}
    }
    ws.send(json.dumps(subscribe_message))


def nftDetails(id):
    result = subprocess.run(['node', 'nftDetails.js', id],
                            capture_output=True, text=True)
    # print(f"Raw output: {result.stdout}")
    try:
        output = json.loads(result.stdout)
        if 'priceTick' in output and 'tickLower' in output and 'tickUpper' in output and 'liquidity' in output:
            details = {
                'priceTick': output['priceTick'],
                'tickLower': output['tickLower'],
                'tickUpper': output['tickUpper'],
                'liquidity': output['liquidity'],
                'lowerRatio': 1.0001 ** output['tickLower'],
                'upperRatio': 1.0001 ** output['tickUpper'],
            }
            print(f"NFT Details:")
            print(f"Tick Lower: {details['tickLower']}")
            print(f"Tick Upper: {details['tickUpper']}")
            print(f"Ratio Lower (all ZRO): {details['lowerRatio']}")
            print(f"Upper Ratio (all WETH): {details['upperRatio']}")
            print(f"Liquidity: {details['liquidity']}")

            return details
        else:
            print("Error: Unexpected output format")
            return None
    except json.JSONDecodeError:
        print("Error: Unable to parse output")
        return None


def get_nft_details():
    global nft_details, max_eth_exposure
    if nft_details is None:
        id = findNft(userAddress)
        if id:
            nft_details = nftDetails(id)
            if nft_details:
                _, max_eth_exposure = calculateTokenAmounts(
                    1,
                    nft_details['tickLower'],
                    nft_details['tickUpper'],
                    nft_details['liquidity']
                )
                print(f"Max ETH exposure: {max_eth_exposure:.6f} WETH")
    return nft_details


def calculateTokenAmounts(zro_eth_ratio, tick_lower, tick_upper, liquidity_dict):
    if isinstance(liquidity_dict, dict):
        liquidity = int(liquidity_dict['hex'], 16)
    elif isinstance(liquidity_dict, str):
        liquidity = int(liquidity_dict, 16)
    else:
        raise ValueError("liquidity_dict must be either a dictionary or a hex string")

    sqrtp_lower = tick_to_sqrtp(tick_lower)
    sqrtp_upper = tick_to_sqrtp(tick_upper)

    # Convert ZRO/ETH ratio to sqrtPrice
    sqrtp_current = int((max(zro_eth_ratio, 1e-18) ** 0.5) * q96)

    if sqrtp_current < sqrtp_lower:
        amount0 = calc_amount0(liquidity, sqrtp_lower, sqrtp_upper)
        amount1 = 0
    elif sqrtp_current > sqrtp_upper:
        amount0 = 0
        amount1 = calc_amount1(liquidity, sqrtp_lower, sqrtp_upper)
    else:
        amount0 = calc_amount0(liquidity, sqrtp_current, sqrtp_upper)
        amount1 = calc_amount1(liquidity, sqrtp_lower, sqrtp_current)

    # Convert amounts to standard token units (assuming 18 decimal places)
    token0_amount = amount0 / eth  # ZRO amount
    token1_amount = amount1 / eth  # WETH amount

    print(f"Holding {token0_amount:.6f} of ZRO and {token1_amount:.6f} of WETH")

    return token0_amount, token1_amount

def tick_to_sqrtp(t):
    return int((1.0001 ** (t / 2)) * q96)


def calc_amount0(liq, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return int(liq * q96 * (pb - pa) / pb / pa)


def calc_amount1(liq, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return int(liq * (pb - pa) / q96)


def calculate_position():
    global latest_zro_price, latest_eth_price, nft_details
    if latest_zro_price and latest_eth_price and nft_details:
        zro_eth_ratio = float(latest_zro_price) / float(latest_eth_price)
        zro_amount, weth_amount = calculateTokenAmounts(
            zro_eth_ratio,
            nft_details['tickLower'],
            nft_details['tickUpper'],
            nft_details['liquidity']
        )
        positions = get_user_positions(userAddress)
        print(positions)
    else:
        print("Waiting for price data or NFT details...")

def position_calculator():
    while True:
        calculate_position()
        time.sleep(5)


if __name__ == "__main__":
    if get_nft_details():
        print("NFT details retrieved successfully.")
    else:
        print("Unable to retrieve NFT details.")
        exit(1)

    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("wss://api.hyperliquid.xyz/ws",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open

    # Start the position calculator in a separate thread
    calculator_thread = threading.Thread(
        target=position_calculator, daemon=True)
    calculator_thread.start()

    # Main loop to keep the WebSocket connection alive
    while True:
        ws.run_forever(ping_interval=20, ping_timeout=10)
        print("WebSocket disconnected. Reconnecting...")
        time.sleep(5)
