import paho.mqtt.client as mqtt
import json
import time
import math
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def publish_data():
    broker = "192.168.1.175"
    port = 1883
    topic = "sarayu"

    client = mqtt.Client()
    try:
        client.connect(broker, port, 60)
        logging.info(f"Connected to MQTT broker at {broker}:{port}")

        # Generate a simple sine wave value
        amplitude = (46537 - 16390) / 2
        offset = (46537 + 16390) / 2
        frequency = 5  # Hz

        for i in range(200):
            t = i * 1.0  # Time in seconds (1 message per second)
            value = offset + amplitude * math.sin(2 * math.pi * frequency * t)
            payload = {"values": [value]}  # Single value in a list
            client.publish(topic, json.dumps(payload), qos=1)
            logging.info(f"Published to {topic}: {payload}")
            time.sleep(1)  # Publish every 1 second

    except Exception as e:
        logging.error(f"Failed to publish: {str(e)}")
    finally:
        client.disconnect()
        logging.info("Disconnected from MQTT broker")

if __name__ == "__main__":
    publish_data()