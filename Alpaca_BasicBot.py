### Python bot using Alpaca that buys various crypto every seconds and then liquidates all positions. Process then repeats

import asyncio
import websockets
import json
import alpaca_trade_api as tradeapi

api_key = 'Add API Key'
api_secret = 'Add API Secret'
assets_to_buy = ["BTC/USD", "ETH/USD", 'LTC/USD']  # Replace with the assets you want to trade

# Additional Parameters
cycles = 3 # number of buy cycles before liquidating
buy_wait_time = 5 # wait time between buy cycles

# Initialize the Alpaca API client
api = tradeapi.REST(api_key, api_secret, base_url='https://paper-api.alpaca.markets')

async def connect_to_websocket():
    uri = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
    async with websockets.connect(uri) as websocket:
        auth_data = {
            "action": "auth",
            "key": api_key,
            "secret": api_secret
        }
        await websocket.send(json.dumps(auth_data))

        while True:  # Outer loop to continue after liquidation
            i = 0.01 # this is so I can see different qtys
            for _ in range(cycles):
                buy_qty = 0.2 + i # this is so I can see different qtys
                i += 0.01 # this is so I can see different qtys
                await trading_strategy(buy_qty)
                # Wait x seconds before the next buying cycle
                await asyncio.sleep(buy_wait_time)
            
            await liquidate_positions()

async def trading_strategy(buy_qty):
    # Buy buy_qty shares of each asset every minute
    for asset in assets_to_buy:
        try:
            # Place a market order to buy the specified quantity of the asset
            api.submit_order(
                symbol=asset,
                qty=buy_qty,
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            print(f"Bought {buy_qty} unit of {asset}")
        except Exception as e:
            print(f"Failed to buy {asset}: {e}")

async def liquidate_positions():
    # Liquidate all positions (including any bought outside of code)
    positions = api.list_positions()
    for position in positions:
        try:
            # Place a market order to sell the entire position
            api.submit_order(
                symbol=position.symbol,
                qty=position.qty,
                side='sell',
                type='market',
                time_in_force='gtc'
            )
            print(f"Liquidated {position.qty} units of {position.symbol}")
        except Exception as e:
            print(f"Failed to liquidate {position.symbol}: {e}")

if __name__ == "__main__":
    asyncio.run(connect_to_websocket())
