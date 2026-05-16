import asyncio, json, logging, os, socket
import redis.asyncio as aioredis
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CHANNEL   = os.getenv("REDIS_CHANNEL", "tracking")
HOST      = "0.0.0.0"
PORT      = int(os.getenv("PORT", 8765))
INSTANCE  = socket.gethostname()
connected = set()

async def ws_handler(websocket):
    connected.add(websocket)
    remote = websocket.remote_address
    log.info("Client connected: %s (instance=%s, total=%d)", remote, INSTANCE, len(connected))
    try:
        await websocket.send(json.dumps({"type": "connected", "instance": INSTANCE, "message": "Waiting for location updates"}))
        await websocket.wait_closed()
    finally:
        connected.discard(websocket)
        log.info("Client disconnected: %s (remaining=%d)", remote, len(connected))

async def redis_listener():
    backoff = 1
    while True:
        try:
            r = aioredis.from_url(REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(CHANNEL)
            log.info("Subscribed to Redis channel '%s' (instance=%s)", CHANNEL, INSTANCE)
            backoff = 1
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                raw = message["data"]
                try:
                    payload = json.loads(raw)
                    payload["served_by"] = INSTANCE
                    raw = json.dumps(payload)
                except (json.JSONDecodeError, TypeError):
                    pass
                if connected:
                    await asyncio.gather(*[ws.send(raw) for ws in connected], return_exceptions=True)
        except Exception as exc:
            log.error("Redis error: %s -- retrying in %ds", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

async def main():
    log.info("Starting WebSocket server on %s:%d (instance=%s)", HOST, PORT, INSTANCE)
    async with websockets.serve(ws_handler, HOST, PORT):
        await redis_listener()

if __name__ == "__main__":
    asyncio.run(main())
