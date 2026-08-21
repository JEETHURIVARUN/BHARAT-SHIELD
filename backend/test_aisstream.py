import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_aisstream():
    api_key = os.getenv("AISSTREAM_API_KEY")
    if not api_key:
        print("No AISSTREAM_API_KEY found")
        return

    # Arabian Sea roughly: Lat 0 to 30, Lon 45 to 80
    subscribe_message = {
        "APIKey": api_key,
        "BoundingBoxes": [[[0, 45], [30, 80]]],
        "FilterMessageTypes": ["PositionReport"]
    }

    print("Connecting to AISStream...")
    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
            await websocket.send(json.dumps(subscribe_message))
            print("Subscribed. Waiting for messages...")
            
            for _ in range(5):
                message = await websocket.recv()
                data = json.loads(message)
                print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_aisstream())
