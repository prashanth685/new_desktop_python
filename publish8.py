import math
import struct
import paho.mqtt.publish as publish
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication
import numpy as np
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MQTTPublisher(QObject):
    def __init__(self, broker, topics):
        super().__init__()
        self.broker = broker
        self.topics = topics if isinstance(topics, list) else [topics]
        self.count = 1

        self.frequency = 10  # Hz
        self.amplitude = (46537 - 16390) / 2  # Sine wave amplitude
        self.offset = (46537 + 16390) / 2     # Sine wave offset
        self.sample_rate = 4096               # Samples per second
        self.time_per_message = 1.0           # 1 second for 4096 samples
        self.current_time = 0.0
        self.num_channels = 4                 # Number of channels
        self.samples_per_channel = 4096       # Samples per channel
        self.frame_index = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(1000)  # Publish every 1 second
        logging.debug(f"Initialized MQTTPublisher with broker: {self.broker}, topics: {self.topics}")

    def publish_message(self):
        try:
            # Generate sine wave samples for all channels
            t = np.linspace(self.current_time, self.current_time + self.time_per_message, self.samples_per_channel)
            all_channel_data = []
            for ch in range(self.num_channels):
                # Different frequency for each channel for variety
                freq = self.frequency * (ch + 1)
                data = self.offset + self.amplitude * np.sin(2 * np.pi * freq * t)
                all_channel_data.append(data.astype(np.uint16))

            self.current_time += self.time_per_message

            # Interleave channel data (16384 = 4096 samples * 4 channels)
            interleaved = []
            for i in range(self.samples_per_channel):
                for ch in range(self.num_channels):
                    interleaved.append(all_channel_data[ch][i])

            if len(interleaved) != 16384:
                logging.error(f"Interleaved data length incorrect: expected 16384, got {len(interleaved)}")
                return

            # Generate tacho frequency data (4096 samples, sine wave)
            tacho_freq_data = (self.offset + self.amplitude * np.sin(2 * np.pi * self.frequency * t)).astype(np.uint16)

            # Generate tacho trigger data (15 pulses at 65535, matching 15 Hz)
            tacho_trigger_data = [0] * self.samples_per_channel
            num_triggers = self.frequency  # 15 pulses
            step = self.samples_per_channel // num_triggers  # ~273 samples per pulse
            for i in range(num_triggers):
                index = i * step
                if index < self.samples_per_channel:
                    tacho_trigger_data[index] = 65535  # Single-sample pulse at 3.3V

            header = [
                0,                 # Frame index high or reserved
                self.num_channels, # Number of channels (4)
                self.sample_rate,  # Sample rate (4096)
                4096,              # Bit depth or another parameter
                1000,              # Samples per channel (set to 1000 as per debug, overridden in MQTTHandler)
                2,                 # Number of tacho channels (1 freq + 1 trigger)
                0, 0, 0            # Reserved
            ]

            # Combine all data
            message_values = header + interleaved + tacho_freq_data.tolist() + tacho_trigger_data
            total_expected = 10 + 16384 + 4096 + 4096  # 24586 values
            if len(message_values) != total_expected:
                logging.error(f"Message length incorrect: expected {total_expected}, got {len(message_values)}")
                return

            # Convert to binary
            binary_message = struct.pack(f"<{len(message_values)}H", *message_values)

            # Publish to all topics
            for topic in self.topics:
                try:
                    publish.single(topic, binary_message, hostname=self.broker, qos=1)
                    logging.info(f"[{self.count}] Published to {topic}: frame {self.frame_index}, {len(message_values)} values")
                    logging.debug(f"Header: {header}")
                    logging.debug(f"Main data length: {len(interleaved)}")
                    logging.debug(f"Tacho freq (first 5): {tacho_freq_data[:5].tolist()}")
                    logging.debug(f"Tacho trigger (first 10): {tacho_trigger_data[:10]}")
                except Exception as e:
                    logging.error(f"Failed to publish to {topic}: {str(e)}")

            self.frame_index += 1
            self.count += 1
        except Exception as e:
            logging.error(f"Error in publish_message: {str(e)}")

if __name__ == "__main__":
    app = QApplication([])
    broker = "192.168.1.179"
    topics = ["sarayu/tag1/topic1|m/s"]
    mqtt_publisher = MQTTPublisher(broker, topics)
    app.exec_()