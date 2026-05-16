# Live Tracking POC

## What is this?

This is a proof of concept that answers one question:

> **How do we show a customer where their delivery rider is in real-time — without hammering the database, and in a way that can handle more users as we grow?**

The short answer: **WebSockets** (for instant updates) + **Redis** (as a shared message pipe between servers).

---

## How it works — in plain English

Imagine a walkie-talkie system:

1. **The rider's app** sends a GPS location every second → goes straight into Redis (think of Redis as a bulletin board everyone can read instantly)
2. **The WebSocket servers** are listening to that bulletin board — the moment a location appears, they forward it to any customers currently watching
3. **The customer** sees the location update on their screen within a second, no refreshing needed

Because the bulletin board (Redis) is shared, it doesn't matter which server a customer connects to — they all read from the same source and get the same updates.

---

## What's running

| Part | What it does |
|---|---|
| `redis` | The shared bulletin board. Holds location updates in memory. |
| `ws-server` (×2) | Two copies of the WebSocket server. Both read from Redis and push to customers. |
| `tracker-sim` | Pretends to be a rider. Sends fake GPS coordinates every second. |
| `client` | Pretends to be a customer app. Prints the coordinates it receives. |
---

## What this proves

**Real-time works:** The client receives a new location within 1 second, no polling or page refreshing.

**No database pressure:** Location updates never touch the database. They go rider → Redis → customer and are gone. The DB only gets involved when it truly needs to (e.g. storing the final delivery confirmation).

**It scales horizontally:** Two ws-server copies are running. Each one independently reads from Redis. A customer on server 1 and a customer on server 2 both receive the exact same coordinates. You can add more servers without changing anything else.

The `served_by` field in each message shows which server copy handled your connection — run two clients at once and you'll see different values there, but identical coordinates.

---

## Running it yourself

**Requirements:** Docker with Swarm mode on a Linux machine.

```bash
# 1. Set up
docker swarm init

# 2. Build the images
bash build.sh

# 3. Deploy
docker stack deploy --compose-file poc.yaml poc

# 4. Watch it work
docker service logs -f poc_client

# Press Ctrl+C to stop watching

# 5. Clean up when done
docker stack rm poc
```

---

## What this is NOT

This is a proof of concept, not production-ready code. The following are intentionally left out to keep it simple:

- No login or authentication
- No encrypted connection (in production this would use `wss://` instead of `ws://`)
- Only one fake rider and one fake order
- No permanent storage of location history
