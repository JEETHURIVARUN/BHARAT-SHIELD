import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_aisstream():
    api_key = os.getenv("AISSTREAM_API_KEY")
    print(f"Key: {api_key}")
    subscribe_message = {
        "APIKey": api_key,
        "BoundingBoxes": [[[-180, -90], [180, 90]]]
    }
    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
            await ws.send(json.dumps(subscribe_message))
            print("Subscribed...")
            msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(msg)
            print(f"Msg Type: {data.get('MessageType')}")
    except asyncio.TimeoutError:
        print("Timeout waiting for message")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_aisstream())
