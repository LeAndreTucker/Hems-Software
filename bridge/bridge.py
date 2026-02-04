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
# Shared state
# =========================
clients = set()               # connected websocket clients
latest_state = {}             # latest values by topic


# =========================
# MQTT callbacks
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

    latest_state[msg.topic] = payload

    # Build a UI-friendly message
    ui_msg = {
        "topic": msg.topic,
        "payload": payload
    }

    # Push to all websocket clients
    asyncio.run(send_to_all(ui_msg))


# =========================
# WebSocket handling
# =========================
async def send_to_all(message):
    if not clients:
        return

    dead = set()
    raw = json.dumps(message)

    for ws in clients:
        try:
            await ws.send(raw)
        except:
            dead.add(ws)

    for ws in dead:
        clients.remove(ws)


async def ws_handler(websocket):
    print("[WS] UI connected")
    clients.add(websocket)

    # Send snapshot on connect
    for topic, payload in latest_state.items():
        await websocket.send(json.dumps({
            "topic": topic,
            "payload": payload
        }))

    try:
        async for msg in websocket:
            await handle_ws_message(msg)
    except:
        pass
    finally:
        clients.remove(websocket)
        print("[WS] UI disconnected")


async def handle_ws_message(raw):
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


# =========================
# Startup
# =========================
def start_mqtt():
    mqtt_client.loop_forever()


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
mqtt_thread.start()


async def main():
    print(f"[WS] Serving on ws://{WS_HOST}:{WS_PORT}")
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
