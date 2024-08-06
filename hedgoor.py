import time
from web3 import Web3
from hyperliquid.utils import constants
import utils
import json
import subprocess

def trade(coin, is_buy, sz):
    address, info, exchange = utils.setup(constants.MAINNET_API_URL, skip_ws=True)

    coin = "ZRO"
    is_buy = False
    sz = 5

    print(f"We try to Market {'Buy' if is_buy else 'Sell'} {sz} {coin}.")

    order_result = exchange.market_open(coin, is_buy, sz, None, 0.01)
    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
            except KeyError:
                print(f'Error: {status["error"]}')

def findNft(address):
    result = subprocess.run(['node', 'getNFT.js', address], capture_output=True, text=True)
    try:
        output = json.loads(result.stdout)
        if 'tokenId' in output:
            print(f"Token ID: {output['tokenId']}")
        else:
            print(f"Error: {output['error']}")
    except json.JSONDecodeError:
        print("Error: Unable to parse output")

if __name__ == "__main__":
    # trade('ZRO', False, 5)
    findNft('0x7EEE7bC996F430232caF838EE7F6fb0eFEC44CDF')