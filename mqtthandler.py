import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import struct
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MQTTHandler(QObject):
    data_received = pyqtSignal(str, str, list, int)  # tag_name, model_name, values, sample_rate
    connection_status = pyqtSignal(str)

    def __init__(self, db, project_name, broker="192.168.1.232", port=1883):
        super().__init__()
        self.db = db
        self.project_name = project_name
        self.broker = broker
        self.port = port
        self.client = None
        self.connected = False
        self.subscribed_topics = []
        logging.debug(f"Initializing MQTTHandler with project_name: {project_name}, broker: {broker}")

    def parse_topic(self, topic):
        try:
            tag_name = topic
            project_data = self.db.get_project_data(self.project_name)
            model_name = None
            if project_data and "models" in project_data:
                for model in project_data["models"]:
                    if model.get("tagName") == topic:
                        model_name = model.get("name")
                        break
            logging.debug(f"Parsed topic {topic}: project_name={self.project_name}, model_name={model_name}, tag_name={tag_name}")
            return self.project_name, model_name, tag_name
        except Exception as e:
            logging.error(f"Error parsing topic {topic}: {str(e)}")
            return None, None, None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.connection_status.emit("Connected to MQTT Broker")
            logging.info("Connected to MQTT Broker")
            QTimer.singleShot(0, self.subscribe_to_topics)  # Subscribe asynchronously
        else:
            self.connected = False
            self.connection_status.emit(f"Connection failed with code {rc}")
            logging.error(f"Failed to connect to MQTT Broker with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.connection_status.emit("Disconnected from MQTT Broker")
        logging.info("Disconnected from MQTT Broker")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload

            project_name, model_name, tag_name = self.parse_topic(topic)
            if not tag_name:
                logging.warning(f"Failed to parse topic: {topic}")
                return

            if project_name != self.project_name:
                logging.debug(f"Ignoring message for project {project_name}, expected {self.project_name}")
                return

            try:
                # Attempt JSON decode first
                payload_str = payload.decode('utf-8')
                data = json.loads(payload_str)
                values = data.get("values", [])
                sample_rate = data.get("sample_rate", 1000)
                if not isinstance(values, list) or not values:
                    logging.warning(f"Invalid JSON payload format: {payload_str}")
                    return
                num_channels = len(values)
                logging.debug(f"Parsed JSON payload: {num_channels} channels")
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload_length = len(payload)
                if payload_length < 20 or payload_length % 2 != 0:
                    logging.warning(f"Invalid payload length: {payload_length} bytes")
                    return

                num_samples = payload_length // 2
                try:
                    values = struct.unpack(f"<{num_samples}H", payload)
                except struct.error as e:
                    logging.error(f"Failed to unpack payload of {num_samples} uint16_t: {str(e)}")
                    return

                if len(values) < 10:
                    logging.warning(f"Payload too short: {len(values)} samples")
                    return

                # Header: first 100 values
                header = values[:100]
                total_values = values[100:]

                # Extract header values with defaults
                num_channels = header[2] if len(header) > 2 and header[2] > 0 else 4
                sample_rate = header[3] if len(header) > 3 and header[3] > 0 else 4096
                samples_per_channel = 4096
                num_tacho_channels = header[6] if len(header) > 6 and header[6] > 0 else 2

                # Calculate expected number of data points
                expected_main = samples_per_channel * num_channels
                expected_tacho = 4096 * num_tacho_channels
                expected_total = expected_main + expected_tacho
                logging.debug(f" total values coming {expected_total}") 

                if len(total_values) != expected_total:
                    logging.warning(f"Unexpected data length: got {len(total_values)}, expected {expected_total}")
                    logging.debug(f"Header: {header}")
                    logging.debug(f"Num channels: {num_channels}, Samples per channel: {samples_per_channel}, Num tacho channels: {num_tacho_channels}")
                    return

                # Extract and deinterleave main channel data
                main_data = total_values[:expected_main]
                tacho_freq_data = total_values[expected_main:expected_main + 4096]
                tacho_trigger_data = total_values[expected_main + 4096:expected_main + 8192]

                channel_data = [[] for _ in range(num_channels)]
                for i in range(0, len(main_data), num_channels):
                    for ch in range(num_channels):
                        channel_data[ch].append(main_data[i + ch])

                # Convert to float for channels and include tacho data
                values = [[float(v) for v in ch] for ch in channel_data]
                values.append([float(v) for v in tacho_freq_data])
                values.append([float(v) for v in tacho_trigger_data])

                logging.debug(f"Parsed binary payload:")
                logging.debug(f" - Channels: {num_channels}")
                logging.debug(f" - Samples/channel: {len(channel_data[0])}")
                logging.debug(f" - Tacho freq (first 5): {tacho_freq_data[:5]}")
                logging.debug(f" - Tacho trigger (first 10): {tacho_trigger_data[:10]}")

            if model_name:
                self.data_received.emit(tag_name, model_name, values, sample_rate)
                logging.debug(f"Emitted data for {tag_name}/{model_name}: {len(values)} channels, sample_rate={sample_rate}")

        except Exception as e:
            logging.error(f"Error processing MQTT message: {str(e)}")

    def subscribe_to_topics(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            for model in project_data.get("models", []):
                tag_name = model.get("tagName", "")
                if tag_name and tag_name not in self.subscribed_topics:
                    self.client.subscribe(tag_name)
                    self.subscribed_topics.append(tag_name)
                    logging.info(f"Subscribed to topic: {tag_name}")
        except Exception as e:
            logging.error(f"Error subscribing to topics: {str(e)}")
            self.connection_status.emit(f"Failed to subscribe to topics: {str(e)}")

    def start(self):
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            self.client.connect_async(self.broker, self.port, 60)  # Use async connect
            self.client.loop_start()
            logging.info("MQTT client started")
        except Exception as e:
            logging.error(f"Failed to start MQTT client: {str(e)}")
            self.connection_status.emit(f"Failed to start MQTT: {str(e)}")

    def stop(self):
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                self.subscribed_topics = []
                logging.info("MQTT client stopped")
        except Exception as e:
            logging.error(f"Error stopping MQTT client: {str(e)}")