"""
Delivery GPS Simulator — Live Tracking POC
"""
import asyncio, json, logging, math, os, random, time
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CHANNEL   = os.getenv("REDIS_CHANNEL", "tracking")
INTERVAL  = float(os.getenv("INTERVAL_SECONDS", "1"))
START_LAT = 50.846667
START_LON = 4.352500

def next_position(lat, lon, heading):
    heading += random.uniform(-15, 15)
    heading %= 360
    step = 0.0003
    rad = math.radians(heading)
    return lat + step * math.cos(rad), lon + step * math.sin(rad), heading

async def simulate() -> None:
    backoff = 1
    while True:
        try:
            r = aioredis.from_url(REDIS_URL)
            log.info("Connected to Redis. Publishing to channel '%s' every %.1fs", CHANNEL, INTERVAL)
            backoff = 1
            lat, lon, heading = START_LAT, START_LON, 45.0
            order_id = "order_001"
            while True:
                lat, lon, heading = next_position(lat, lon, heading)
                payload = {"order_id": order_id, "lat": round(lat, 7), "lon": round(lon, 7), "heading": round(heading, 1), "timestamp": round(time.time(), 3)}
                await r.publish(CHANNEL, json.dumps(payload))
                log.info("Published → %s", json.dumps(payload))
                await asyncio.sleep(INTERVAL)
        except Exception as exc:
            log.error("Redis error: %s — retrying in %ds", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

if __name__ == "__main__":
    asyncio.run(simulate())
