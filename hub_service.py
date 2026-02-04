import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "localhost"

device_state = {
    "plug1": {
        "on": True,
        "power_w": 0.0
    }
}

def on_connect(client, userdata, flags, rc):
    print("Hub connected to MQTT")
    client.subscribe("hems/ui/command/#")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = json.loads(msg.payload.decode())

    if "plug1" in topic:
        if payload["command"] == "OFF":
            device_state["plug1"]["on"] = False
        elif payload["command"] == "ON":
            device_state["plug1"]["on"] = True

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER)
client.loop_start()

while True:
    if device_state["plug1"]["on"]:
        device_state["plug1"]["power_w"] = 200 + random.random() * 50
    else:
        device_state["plug1"]["power_w"] = 0.0

    msg = {
        "power_w": device_state["plug1"]["power_w"],
        "timestamp": time.time()
    }

    client.publish("hems/devices/plug1/power_w", json.dumps(msg))
    client.publish("hems/total/power_w", json.dumps(msg))

    time.sleep(2)
