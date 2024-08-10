
# Ramses <-> Hyperliquid Hedgoor

This is a bot for hedging ZRO exposure on hyperliquid.

Given a user address in config.json, the script will:
- look for a ramses NFT representing a ZRO/ETH CL position held by that address
- subscribe to hyperliquid's websocket for ZRO and ETH price updates
- calculate how much ETH and ZRO the ramses position equates to at current prices (assumes no arbitrage between ramses and hyperliquid)
- query hyperliquid's api for any ZRO and ETH positions
- hedge off ZRO exposure (go short the amount of ZRO held), and long the equivalent $ amount of ETH, subject to the amounts being greater than threshold (set on lines 10 and 11)

This allows the user to harvest incentives on Ramses, while maintaining an exposure that closely tracks the price of ETH. 

***Please be aware!*** I have tested this overnight only with a relatively small balance - the code is provided as is, don't come crying to me if you lose money. Particularly, if you set the threshold too low relative to the amount held in the Ramses position, the bot will trade far too frequently and you'll spend more in fees than you get in rewards. Also, if you don't leave enough USD for margin in hyperliquid, you'll get liquidated. NFA, DYOR. 

## Requirements

Python + Node  
Alchemy API key (in .env)  
Hyperliquid API key (in config.json)  