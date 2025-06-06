import paho.mqtt.client as mqtt
import time
import math
import struct
import threading

class MQTTPublisher:
    def __init__(self, broker, topics):
        self.broker = broker
        self.topics = topics if isinstance(topics, list) else [topics]
        self.count = 1

        self.frequency = 10
        amp = 3
        self.amplitude = ((amp * 0.5) / (3.3 / 65535))
        self.offset = 32768

        self.sample_rate = 4096
        self.time_per_message = 1.0
        self.current_time = 0.0

        self.channel = 6
        self.main_channels = 4
        self.frame_index = 0
        self.timer = None

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log

        self.client.connect(self.broker, 1883, 60)

    def on_connect(self, client, userdata, flags, rc):
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} - INFO - Connected to MQTT broker: {self.broker}")
        if not self.timer:
            self.timer = threading.Timer(1.0, self.publish_message)
            self.timer.start()
            print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} - INFO - Publishing started")

    def on_publish(self, client, userdata, mid):
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} - INFO - Published message with mid: {mid}")

    def on_disconnect(self, client, userdata, rc):
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} - INFO - Disconnected from MQTT broker: {self.broker}")

    def on_log(self, client, userdata, level, buf):
        print(f"Log: {buf}")

    def publish_message(self):
        if self.count >= 20000:
            print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} - INFO - Publishing stopped after 20000 messages")
            self.client.disconnect()
            return

        samples_per_channel = self.sample_rate
        all_channel_data = [[0] * samples_per_channel for _ in range(self.channel)]

        for i in range(samples_per_channel):
            t = self.current_time + (i / self.sample_rate)
            base_value = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
            rounded_value = round(base_value)
            for ch in range(self.main_channels):
                all_channel_data[ch][i] = rounded_value

        for i in range(samples_per_channel):
            all_channel_data[self.channel - 2][i] = self.frequency

        interval = self.sample_rate / self.frequency

        for i in range(samples_per_channel):
            all_channel_data[self.channel - 1][i] = 1 if i % round(interval) == 0 else 0

        self.current_time += self.time_per_message

        header = [
            self.frame_index % 65535,
            self.frame_index // 65535,
            self.main_channels,
            self.sample_rate,
            16,
            self.sample_rate,
            2,
            0,
            0,
            0
        ]

        interleaved_main = []
        for i in range(samples_per_channel):
            for ch in range(self.main_channels):
                interleaved_main.append(all_channel_data[ch][i])

        message_values = header + interleaved_main + all_channel_data[self.channel - 2] + all_channel_data[self.channel - 1]

        buffer = struct.pack(f"<{len(message_values)}H", *message_values)

        for topic in self.topics:
            self.client.publish(topic, buffer, qos=1)

        print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} - INFO - [{self.count}] Published to {topic}: frame {self.frame_index} with {len(message_values)} values")

        self.frame_index += 1
        self.count += 1

        if self.timer:
            self.timer = threading.Timer(1.0, self.publish_message)
            self.timer.start()

if __name__ == "__main__":
    broker = '192.168.1.235'
    topics = ['sarayu/d1/topic1']
    publisher = MQTTPublisher(broker, topics)
    publisher.client.loop_forever()
