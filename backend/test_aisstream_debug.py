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
        "BoundingBoxes": [[[0, 45], [30, 80]]]
    }
    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
            await ws.send(json.dumps(subscribe_message))
            print("Subscribed...")
            for i in range(10):
                msg = await ws.recv()
                data = json.loads(msg)
                print(f"Msg {i} Type: {data.get('MessageType')}")
                if data.get("MessageType") == "PositionReport":
                    print(data.get("Message", {}).get("PositionReport"))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_aisstream())
