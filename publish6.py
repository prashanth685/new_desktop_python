# import math
# import struct
# import paho.mqtt.publish as publish
# from PyQt5.QtCore import QTimer, QObject
# from PyQt5.QtWidgets import QApplication
# import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# class MQTTPublisher(QObject):
#     def __init__(self, broker, topics):
#         super().__init__()
#         self.broker = broker
#         self.topics = topics if isinstance(topics, list) else [topics]
#         self.count = 1

#         self.frequency = 10  # Hz
#         self.amplitude = (46537 - 16390) / 2  # Sine wave amplitude
#         self.offset = (46537 + 16390) / 2     # Sine wave offset
#         self.sample_rate = 4096               # Samples per second
#         self.time_per_message = 1.0           # 1-second window
#         self.current_time = 0.0
#         self.channel = 4                     # Number of channels
#         self.frame_index = 0

#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.publish_message)
#         self.timer.start(1000)  # Publish every 1 second
#         logging.debug(f"Initialized MQTTPublisher with broker: {broker}, topics: {self.topics}")

#     def publish_message(self):
#         try:
#             samples_per_channel = self.sample_rate  # 4096 samples per channel
#             all_channel_data = []

#             # Generate sine wave samples for channels
#             for i in range(samples_per_channel):
#                 t = self.current_time + (i / self.sample_rate)
#                 base_value = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
#                 rounded_value = int(round(base_value))
#                 all_channel_data.append(rounded_value)

#             self.current_time += self.time_per_message

#             # Interleave channel data (16384 values for 4 channels)
#             interleaved = []
#             for i in range(samples_per_channel):
#                 for ch in range(self.channel):
#                     interleaved.append(all_channel_data[i])  # Same data for all channels

#             if len(interleaved) != 16384:
#                 logging.error(f"Interleaved data length incorrect: expected 16384, got {len(interleaved)}")
#                 return

#             # Generate tacho frequency data (4096 samples, same waveform)
#             tacho_freq_data = []
#             for i in range(4096):
#                 t = self.current_time - self.time_per_message + (i / self.sample_rate)
#                 freq_value = int(self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t))
#                 tacho_freq_data.append(freq_value)

#             # Generate tacho trigger data (4096 values, alternating 0 and 1)
#             tacho_trigger_data = [i % 2 for i in range(4096)]

#             # Build header
#             header = [
#                 self.frame_index % 65535,  # Frame index low
#                 self.frame_index // 65535,  # Frame index high
#                 self.channel,              # Number of channels
#                 self.sample_rate,          # Sample rate
#                 16,                        # Bit depth
#                 int(self.sample_rate / self.channel),  # Samples per channel
#                 0, 0, 0, 0                 # Reserved
#             ]

#             # Combine all data
#             message_values = header + interleaved + tacho_freq_data + tacho_trigger_data
#             total_expected = 10 + 16384 + 4096 + 4096
#             if len(message_values) != total_expected:
#                 logging.error(f"Message length incorrect: expected {total_expected}, got {len(message_values)}")
#                 return

#             # Convert to binary
#             binary_message = struct.pack(f"{len(message_values)}H", *message_values)

#             # Publish to all topics
#             for topic in self.topics:
#                 try:
#                     publish.single(topic, binary_message, hostname=self.broker, qos=1)
#                     logging.info(f"[{self.count}] Published to {topic}: frame {self.frame_index}, {len(message_values)} values")
#                 except Exception as e:
#                     logging.error(f"Failed to publish to {topic}: {str(e)}")

#             self.frame_index += 1
#             self.count += 1
#         except Exception as e:
#             logging.error(f"Error in publish_message: {str(e)}")

# if __name__ == "__main__":
#     app = QApplication([])
#     broker = "192.168.1.179"
#     topics = ["sarayu/tag1/topic1|m/s"]
#     mqtt_publisher = MQTTPublisher(broker, topics)
#     app.exec_()





# import math
# import struct
# import paho.mqtt.publish as publish
# from PyQt5.QtCore import QTimer, QObject
# from PyQt5.QtWidgets import QApplication
# import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# class MQTTPublisher(QObject):
#     def __init__(self, broker, topics):
#         super().__init__()
#         self.broker = broker
#         self.topics = topics if isinstance(topics, list) else [topics]
#         self.count = 1

#         self.frequency = 15  # Hz
#         self.amplitude = (46537 - 16390) / 2  # Sine wave amplitude
#         self.offset = (46537 + 16390) / 2     # Sine wave offset
#         self.sample_rate = 4096               # Samples per second
#         self.time_per_message = 1.0           # 1 second for 4096 samples
#         self.current_time = 0.0
#         self.channel = 4                      # Number of channels
#         self.samples_per_channel = 4096       # Samples per channel
#         self.frame_index = 0

#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.publish_message)
#         self.timer.start(1000)  # Publish every 1 second
#         logging.debug(f"Initialized MQTTPublisher with broker: {self.broker}, topics: {self.topics}")

#     def publish_message(self):
#         try:
#             # Generate sine wave samples for channels
#             all_channel_data = []
#             for i in range(self.samples_per_channel):
#                 t = self.current_time + (i / self.sample_rate)
#                 base_value = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
#                 rounded_value = int(round(base_value))
#                 all_channel_data.append(rounded_value)

#             self.current_time += self.time_per_message

#             # Interleave channel data (16384 values for 4 channels)
#             interleaved = []
#             for i in range(self.samples_per_channel):
#                 for ch in range(self.channel):
#                     interleaved.append(all_channel_data[i])  # Same data for all channels

#             if len(interleaved) != 16384:
#                 logging.error(f"Interleaved data length incorrect: expected 16384, got {len(interleaved)}")
#                 return

#             # Generate tacho frequency data (4096 samples, same waveform)
#             tacho_freq_data = []
#             for i in range(4096):
#                 t = self.current_time - self.time_per_message + (i / self.sample_rate)
#                 freq_value = int(self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t))
#                 tacho_freq_data.append(freq_value)

#             # Generate tacho trigger data (4096 values, alternating 0 and 1)
#             # tacho_trigger_data = [i % 2 == 1 for i in range(4096)]
#             tacho_trigger_data = [0 if i % 2 == 0 else 65535 for i in range(4096)]


#             # Build header
#             header = [
#                 self.frame_index % 65535,  # Frame index low
#                 self.frame_index // 65535,  # Frame index high
#                 self.channel,              # Number of channels (4)
#                 self.sample_rate,          # Sample rate
#                 16,                        # Bit depth
#                 self.samples_per_channel,  # Samples per channel (4096)
#                 0, 0, 0, 0                 # Reserved
#             ]

#             # Combine all data
#             message_values = header + interleaved + tacho_freq_data + tacho_trigger_data
#             total_expected = 10 + 16384 + 4096 + 4096
#             if len(message_values) != total_expected:
#                 logging.error(f"Message length incorrect: expected {total_expected}, got {len(message_values)}")
#                 return

#             # Convert to binary
#             binary_message = struct.pack(f"{len(message_values)}H", *message_values)

#             # Publish to all topics
#             for topic in self.topics:
#                 try:
#                     publish.single(topic, binary_message, hostname=self.broker, qos=1)
#                     logging.info(f"[{self.count}] Published to {topic}: frame {self.frame_index}, {len(message_values)} values")
#                 except Exception as e:
#                     logging.error(f"Failed to publish to {topic}: {str(e)}")

#             self.frame_index += 1
#             self.count += 1
#         except Exception as e:
#             logging.error(f"Error in publish_message: {str(e)}")

# if __name__ == "__main__":
#     app = QApplication([])
#     broker = "192.168.1.179"
#     topics = ["sarayu/tag1/topic1|m/s"]
#     mqtt_publisher = MQTTPublisher(broker, topics)
#     app.exec_()





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

        self.frequency = 10  # Hz
        self.amplitude = (46537 - 16390) / 2  # Sine wave amplitude
        self.offset = (46537 + 16390) / 2     # Sine wave offset
        self.sample_rate = 4096               # Samples per second
        self.time_per_message = 1.0           # 1 second for 4096 samples
        self.current_time = 0.0
        self.channel = 4                      # Number of channels
        self.samples_per_channel = 4096       # Samples per channel
        self.frame_index = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(1000)  # Publish every 1 second
        logging.debug(f"Initialized MQTTPublisher with broker: {self.broker}, topics: {self.topics}")

    def publish_message(self):
        try:
            # Generate sine wave samples for all channels
            all_channel_data = []
            for i in range(self.samples_per_channel):
                t = self.current_time + (i / self.sample_rate)
                base_value = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
                rounded_value = int(round(base_value))
                all_channel_data.append(rounded_value)

            self.current_time += self.time_per_message

            # Interleave channel data (16384 = 4096 samples * 4 channels)
            interleaved = []
            for i in range(self.samples_per_channel):
                for ch in range(self.channel):
                    interleaved.append(all_channel_data[i])  # Same data for all channels

            if len(interleaved) != 16384:
                logging.error(f"Interleaved data length incorrect: expected 16384, got {len(interleaved)}")
                return

            # Generate tacho frequency data (4096 samples, same waveform)
            tacho_freq_data = []
            # for i in range(4096):
            #     t = self.current_time - self.time_per_message + (i / self.sample_rate)
            #     freq_value = int(self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t))
            #     tacho_freq_data.append(freq_value)
            for i in range(4096):
                freq_data=self.frequency
                tacho_freq_data.append(freq_data)

            # Generate tacho trigger data (10 spikes at 3.3V)
            tacho_trigger_data = [0] * self.samples_per_channel
            num_triggers = self.frequency
            step = self.samples_per_channel // num_triggers
            for i in range(num_triggers):
                index = i * step
                if index < self.samples_per_channel:
                    tacho_trigger_data[index] = 65535  # Single-sample pulse at 3.3V
            

            # Build header
            header = [
                self.frame_index % 65535,  # Frame index low
                self.frame_index // 65535,  # Frame index high
                self.channel,              # Number of channels (4)
                self.sample_rate,          # Sample rate
                16,                        # Bit depth
                self.samples_per_channel,  # Samples per channel (4096)
                0, 0, 0, 0                 # Reserved
            ]

            # Combine all data
            message_values = header + interleaved + tacho_freq_data + tacho_trigger_data
            total_expected = 10 + 16384 + 4096 + 4096
            if len(message_values) != total_expected:
                logging.error(f"Message length incorrect: expected {total_expected}, got {len(message_values)}")
                return

            # Convert to binary
            binary_message = struct.pack(f"{len(message_values)}H", *message_values)

            # Publish to all topics
            for topic in self.topics:
                try:
                    publish.single(topic, binary_message, hostname=self.broker, qos=1)
                    logging.info(f"[{self.count}] Published to {topic}: frame {self.frame_index}, {len(message_values)} values")
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
