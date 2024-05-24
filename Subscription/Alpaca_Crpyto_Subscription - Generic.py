import asyncio
import websockets
import json

api_key = 'ENTER API KEY'
api_secret ='ENTER API SECRET'

async def connect_to_websocket():
    uri = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
    async with websockets.connect(uri) as websocket:
        auth_data = {
            "action": "auth",
            "key": api_key,
            "secret": api_secret
        }
        await websocket.send(json.dumps(auth_data))

        subscribe_data = {
            "action": "subscribe",
            "trades": ["BTC/USD"],
            "quotes": ["LTC/USD", "ETH/USD"],
            "bars": ["BCH/USD"]
        }
        await websocket.send(json.dumps(subscribe_data))

        async for message in websocket:
            print(message)

asyncio.run(connect_to_websocket())