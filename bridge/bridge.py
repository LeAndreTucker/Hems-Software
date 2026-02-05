import asyncio
import json
import time
import threading
import paho.mqtt.client as mqtt
import websockets

# =========================
# Configuration
# =========================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_SUB_TOPIC = "hems/#"

WS_HOST = "localhost"
WS_PORT = 8765

# =========================
# Shared state (owned by asyncio loop)
# =========================
clients = set()          # websocket clients (asyncio loop thread)
latest_state = {}        # last payload per topic (asyncio loop thread)

loop = None              # main asyncio event loop (set in main)
mqtt_client = None       # paho client


# =========================
# Async helpers (run on asyncio loop)
# =========================
async def send_to_all(message: dict):
    if not clients:
        return

    raw = json.dumps(message)
    dead = set()

    for ws in clients:
        try:
            await ws.send(raw)
        except Exception:
            dead.add(ws)

    for ws in dead:
        clients.discard(ws)


async def push_snapshot(websocket):
    # Send latest known values on connect
    for topic, payload in latest_state.items():
        await websocket.send(json.dumps({"topic": topic, "payload": payload}))


async def handle_ws_message(raw: str):
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        print("[WS] Bad JSON from UI ignored:", raw)
        return

    if msg.get("type") != "command":
        return

    device_id = msg.get("id")
    command = msg.get("command")

    if not device_id or not command:
        return

    topic = f"hems/ui/command/{device_id}"
    payload = json.dumps({"command": command})

    print(f"[WS→MQTT] {topic} {payload}")
    mqtt_client.publish(topic, payload)


async def ws_handler(websocket):
    print("[WS] UI connected")
    clients.add(websocket)

    # Snapshot first
    await push_snapshot(websocket)

    try:
        async for msg in websocket:
            await handle_ws_message(msg)
    except Exception:
        pass
    finally:
        clients.discard(websocket)
        print("[WS] UI disconnected")


async def bridge_heartbeat_task():
    # Optional, but useful
    while True:
        mqtt_client.publish("hems/bridge/heartbeat", json.dumps({"status": "alive", "ts": int(time.time() * 1000)}))
        await asyncio.sleep(2)


# =========================
# MQTT callbacks (run on MQTT thread)
# =========================
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected")
    client.subscribe(MQTT_SUB_TOPIC)


def on_message(client, userdata, msg):
    raw = msg.payload.decode(errors="replace").strip()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[MQTT] Bad JSON ignored on {msg.topic}: {raw}")
        return

    # Schedule update onto the main asyncio loop (thread-safe)
    def _apply_and_send():
        latest_state[msg.topic] = payload
        ui_msg = {"topic": msg.topic, "payload": payload}
        asyncio.create_task(send_to_all(ui_msg))

    if loop is not None:
        loop.call_soon_threadsafe(_apply_and_send)


def start_mqtt_thread():
    mqtt_client.loop_forever()


# =========================
# Main
# =========================
async def main():
    global loop, mqtt_client
    loop = asyncio.get_running_loop()

    # MQTT setup
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

    t = threading.Thread(target=start_mqtt_thread, daemon=True)
    t.start()

    print(f"[WS] Serving on ws://{WS_HOST}:{WS_PORT}")
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        # optional heartbeat task
        asyncio.create_task(bridge_heartbeat_task())
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
