import time
import random
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"   # Mosquitto running on this same PC
PORT = 1883

TOPIC_PLUG1 = "hems/plug1/power_w"
TOPIC_TOTAL = "hems/total/power_w"

def main():
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)

    t = 0
    base = 120.0

    print("HEMS Hub Publisher running. Press Ctrl+C to stop.")
    while True:
        t += 1

        # Fake load pattern: steps up/down so it looks realistic
        step = 250.0 if (t // 10) % 2 == 0 else 0.0  # toggles about every 20 seconds
        noise = random.uniform(-8, 8)

        plug1_w = max(0.0, base + step + noise)
        total_w = plug1_w

        client.publish(TOPIC_PLUG1, f"{plug1_w:.1f}")
        client.publish(TOPIC_TOTAL, f"{total_w:.1f}")

        print(f"Published plug1={plug1_w:.1f}W total={total_w:.1f}W")
        time.sleep(2)

if __name__ == "__main__":
    main()
