"""
WebSocket Client — Live Tracking POC
"""
import asyncio, json, logging, os, sys
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

WS_URL  = sys.argv[1] if len(sys.argv) > 1 else os.getenv("WS_URL", "ws://ws-server:8765")
RETRIES = int(os.getenv("MAX_RETRIES", "0"))

async def listen(retries_left: int) -> None:
    attempt = 0
    while True:
        attempt += 1
        try:
            log.info("Connecting to %s (attempt %d)…", WS_URL, attempt)
            async with websockets.connect(WS_URL) as ws:
                log.info("Connected.")
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        if msg.get("type") == "connected":
                            print(f"\n{'='*55}\n  Connected to server instance: {msg['instance']}\n  (This proves which replica is serving you)\n{'='*55}\n")
                        else:
                            print(f"[{msg.get('timestamp','?')}] order={msg.get('order_id','?')}  lat={msg.get('lat','?')}  lon={msg.get('lon','?')}  heading={msg.get('heading','?')}°  → served_by={msg.get('served_by','?')}")
                    except (json.JSONDecodeError, KeyError):
                        print(f"RAW: {raw}")
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as exc:
            log.warning("Connection lost: %s", exc)
            if retries_left != 0:
                retries_left -= 1
                if retries_left == 0:
                    log.error("Max retries reached. Exiting.")
                    sys.exit(1)
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(listen(RETRIES))
