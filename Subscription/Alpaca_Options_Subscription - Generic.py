import asyncio
import websockets
import msgpack

api_key = 'ENTER API KEY'
api_secret ='ENTER API SECRET'

async def connect_to_websocket():
    uri = "wss://stream.data.alpaca.markets/v1beta1/indicative"
    async with websockets.connect(uri) as websocket:
        auth_data = {
            "action": "auth",
            "key": api_key,
            "secret": api_secret
        }

        await websocket.send(msgpack.packb(auth_data))

        subscribe_data = {
            "action": "subscribe",
            "quotes": ["TSLA240621C00185000", "AAPL240621C00195000"],
            "trades": ["AAPL240621C00190000"]
        }

        await websocket.send(msgpack.packb(subscribe_data))

        async for message in websocket:
            msg = msgpack.unpackb(message)
            print(msg)

asyncio.run(connect_to_websocket())
