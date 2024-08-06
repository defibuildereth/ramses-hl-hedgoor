import time

from hyperliquid.utils import constants
import utils

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

if __name__ == "__main__":
    trade('ZRO', False, 5)