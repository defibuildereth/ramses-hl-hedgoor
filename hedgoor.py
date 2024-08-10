import time
import json
import subprocess
import threading
from hyperliquid.utils import constants
import helpers 
import websocket  

# Define thresholds to avoid small trades/overtrading
zro_hedge_threshold = 250  # Adjust these values as needed
eth_hedge_threshold = 0.25

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

userAddress = config['account_address']

# Global variables 
latest_zro_price = None
latest_eth_price = None
nft_details = None

def trade(coin, is_buy, sz):
    address, info, exchange = utils.setup(
        constants.MAINNET_API_URL, skip_ws=True)

    # Define decimal places for each coin
    decimal_places = {
        'ZRO': 1,
        'ETH': 4
    }

    # Round the size based on the coin
    if coin in decimal_places:
        rounded_sz = round(sz, decimal_places[coin])
    else:
        rounded_sz = round(sz, 2)  # Default to 2 decimal places for unknown coins

    print(f"We try to Market {'Buy' if is_buy else 'Sell'} {rounded_sz} {coin}.")

    try:
        order_result = exchange.market_open(coin, is_buy, rounded_sz, None, 0.01)
        if order_result["status"] == "ok":
            for status in order_result["response"]["data"]["statuses"]:
                try:
                    filled = status["filled"]
                    print(
                        f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
                    return float(filled["totalSz"]) * float(filled["avgPx"])
                except KeyError:
                    print(f'Error: {status["error"]}')
        else:
            print(f"Order failed: {order_result}")
    except ValueError as e:
        print(f"ValueError in trade: {e}")
    except Exception as e:
        print(f"Unexpected error in trade: {e}")

    return None

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

def nftDetails(id):
    result = subprocess.run(['node', 'nftDetails.js', id],
                            capture_output=True, text=True)
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
    global nft_details
    if nft_details is None:
        id = findNft(userAddress)
        if id:
            nft_details = nftDetails(id)
    return nft_details

def calculate_position():
    global latest_zro_price, latest_eth_price, nft_details, userAddress

    if latest_zro_price and latest_eth_price and nft_details:
        zro_eth_ratio = float(latest_zro_price) / float(latest_eth_price)
        zro_amount, weth_amount = helpers.calculate_token_amounts(
            zro_eth_ratio,
            nft_details['tickLower'],
            nft_details['tickUpper'],
            nft_details['liquidity']
        )

        # Get current positions from Hyperliquid
        user_data = helpers.get_user_positions(userAddress)

        if user_data and 'positions' in user_data:
            current_zro_position = user_data['positions'].get(
                'ZRO', {}).get('size', 0)
            current_eth_position = user_data['positions'].get(
                'ETH', {}).get('size', 0)

            # Calculate the difference between NFT ZRO amount and current ZRO position
            # Add because current_zro_position is negative for short
            zro_difference = zro_amount + current_zro_position

            print(f"NFT ZRO amount: {zro_amount:.6f}")
            print(f"Current ZRO position: {current_zro_position:.6f}")
            print(f"ZRO difference to hedge: {zro_difference:.6f}")

            # Step 1: Hedge ZRO position
            if abs(zro_difference) > zro_hedge_threshold:
                if zro_difference > 0:
                    print(f"Selling {zro_difference:.6f} ZRO to hedge")
                    trade_result = trade('ZRO', False, abs(zro_difference))
                else:
                    print(
                        f"Buying {abs(zro_difference):.6f} ZRO to reduce hedge")
                    trade_result = trade('ZRO', True, abs(zro_difference))

                if trade_result:
                    print(f"ZRO trade executed: {trade_result}")
                    current_zro_position -= zro_difference  # Update the position after trade
                else:
                    print("ZRO trade failed")
            else:
                print(
                    "Current ZRO position is within acceptable range. No trade needed.")

            # Step 2: Balance ETH position
            zro_position_value = abs(
                current_zro_position * float(latest_zro_price))
            eth_position_value = current_eth_position * float(latest_eth_price)
            eth_difference = zro_position_value - eth_position_value

            print(f"ZRO position value: ${zro_position_value:.2f}")
            print(f"Current ETH position value: ${eth_position_value:.2f}")
            print(f"ETH value difference to balance: ${eth_difference:.2f}")

            if abs(eth_difference) > eth_hedge_threshold * float(latest_eth_price):
                eth_amount_to_trade = eth_difference / float(latest_eth_price)
                if eth_difference > 0:
                    print(f"Buying {eth_amount_to_trade:.6f} ETH to balance")
                    trade_result = trade('ETH', True, abs(eth_amount_to_trade))
                else:
                    print(
                        f"Selling {abs(eth_amount_to_trade):.6f} ETH to balance")
                    trade_result = trade(
                        'ETH', False, abs(eth_amount_to_trade))

                if trade_result:
                    print(f"ETH trade executed: {trade_result}")
                else:
                    print("ETH trade failed")
            else:
                print(
                    "Current ETH position is within acceptable range. No trade needed.")
        else:
            print("Failed to retrieve current positions or no positions found")
    else:
        print("Waiting for price data or NFT details...")

def position_calculator():
    while True:
        calculate_position()
        time.sleep(10)

def on_message_wrapper(ws, message):
    global latest_zro_price, latest_eth_price
    latest_zro_price, latest_eth_price = helpers.on_message(ws, message)

if __name__ == "__main__":
    if get_nft_details():
        print("NFT details retrieved successfully.")
    else:
        print("Unable to retrieve NFT details.")
        exit(1)

    # Start the position calculator in a separate thread
    calculator_thread = threading.Thread(
        target=position_calculator, daemon=True)
    calculator_thread.start()

    # Main loop to keep the WebSocket connection alive
    while True:
        try:
            ws = helpers.create_websocket()
            ws.on_message = on_message_wrapper
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except websocket.WebSocketException as e:
            print(f"WebSocket exception: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        print("WebSocket disconnected. Reconnecting...")
        time.sleep(5)