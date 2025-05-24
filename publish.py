import math
import struct
import paho.mqtt.publish as publish
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MQTTPublisher(QObject):
    def __init__(self, broker, topics):
        super().__init__()
        self.broker = broker
        self.topics = topics if isinstance(topics, list) else [topics]
        self.count = 1

        self.frequency = 15
        self.amplitude = (46537 - 16390) / 2
        self.offset = (46537 + 16390) / 2

        self.sample_rate = 4096
        self.time_per_message = 1.0
        self.current_time = 0.0

        self.channel = 4
        self.frame_index = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(1000)
        logging.debug(f"Initialized MQTTPublisher with broker: {broker}, topics: {self.topics}")

    def publish_message(self):
        samples_per_channel = self.sample_rate
        all_channel_data = []

        for i in range(samples_per_channel):
            t = self.current_time + (i / self.sample_rate)
            base_value = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
            rounded_value = int(round(base_value))
            all_channel_data.append(rounded_value)

        self.current_time += self.time_per_message

        temp = []
        for i in range(samples_per_channel):
            for ch in range(self.channel):
                temp.append(all_channel_data[i])

        assert len(temp) == 16384, f"Expected 16384 values, got {len(temp)}"

        header = [
            self.frame_index % 65535,
            self.frame_index // 65535,
            self.channel,
            self.sample_rate,
            16,
            int(self.sample_rate / self.channel),
            0, 0, 0, 0
        ]

        message_values = header + temp
        logging.debug(f"Prepared message: header {header}, data length {len(temp)}, total length {len(message_values)}")

        binary_message = struct.pack(f"{len(message_values)}H", *message_values)

        for topic in self.topics:
            try:
                publish.single(topic, binary_message, hostname=self.broker, qos=1)
                logging.info(f"[{self.count}] Published to {topic}: frame {self.frame_index} with {len(temp)} values")
            except Exception as e:
                logging.error(f"Failed to publish to {topic}: {str(e)}")

        self.frame_index += 1
        self.count += 1

if __name__ == "__main__":
    app = QApplication([])
    broker = "192.168.1.179"
    topics = ["sarayu/tag1/topic1|m/s"]
    mqtt_publisher = MQTTPublisher(broker, topics)
    app.exec_()