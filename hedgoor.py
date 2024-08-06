import time
import math
from web3 import Web3
from hyperliquid.utils import constants
import utils
import json
import subprocess

q96 = 2**96
eth = 10**18


def trade(coin, is_buy, sz):
    address, info, exchange = utils.setup(
        constants.MAINNET_API_URL, skip_ws=True)

    coin = "ZRO"
    is_buy = False
    sz = 5

    print(f"We try to Market {'Buy' if is_buy else 'Sell'} {sz} {coin}.")

    order_result = exchange.market_open(coin, is_buy, sz, None, 0.01)
    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(
                    f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
            except KeyError:
                print(f'Error: {status["error"]}')


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
    # print(f"Raw output: {result.stdout}")
    try:
        output = json.loads(result.stdout)
        if 'priceTick' in output and 'tickLower' in output and 'tickUpper' in output and 'liquidity' in output:
            details = {
                'priceTick': output['priceTick'],
                'tickLower': output['tickLower'],
                'tickUpper': output['tickUpper'],
                'liquidity': output['liquidity']
            }

            print(f"NFT Details:")
            print(f"Price Tick: {details['priceTick']}")
            print(f"Tick Lower: {details['tickLower']}")
            print(f"Tick Upper: {details['tickUpper']}")
            print(f"Liquidity: {details['liquidity']}")

            return details
        else:
            print("Error: Unexpected output format")
            return None
    except json.JSONDecodeError:
        print("Error: Unable to parse output")
        return None


def calculateTokenAmounts(price_tick, tick_lower, tick_upper, liquidity_hex):
    liquidity = int(liquidity_hex, 16)
    sqrtp_current = tick_to_sqrtp(price_tick)
    sqrtp_lower = tick_to_sqrtp(tick_lower)
    sqrtp_upper = tick_to_sqrtp(tick_upper)

    if price_tick < tick_lower:
        amount0 = calc_amount0(liquidity, sqrtp_lower, sqrtp_upper)
        amount1 = 0
    elif price_tick > tick_upper:
        amount0 = 0
        amount1 = calc_amount1(liquidity, sqrtp_lower, sqrtp_upper)
    else:
        amount0 = calc_amount0(liquidity, sqrtp_current, sqrtp_upper)
        amount1 = calc_amount1(liquidity, sqrtp_current, sqrtp_lower)

    # Convert amounts to standard token units (assuming 18 decimal places)
    token0_amount = amount0 / eth
    token1_amount = amount1 / eth

    # Return the calculated amounts
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


if __name__ == "__main__":
    id = findNft('0x7EEE7bC996F430232caF838EE7F6fb0eFEC44CDF')
    details = nftDetails(id)
    if details:  # Add this check to ensure details is not None
        amounts = calculateTokenAmounts(
            details['priceTick'], 
            details['tickLower'], 
            details['tickUpper'], 
            details['liquidity']['hex']
        )