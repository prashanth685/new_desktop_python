import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtSignal
import struct
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MQTTHandler(QObject):
    data_received = pyqtSignal(str, str, list)  # tag_name, model_name, values
    connection_status = pyqtSignal(str)

    def __init__(self, db, project_name, broker="192.168.1.175", port=1883):
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
            parts = topic.split('/')
            if len(parts) != 3:
                logging.error(f"Invalid topic format: {topic}")
                return None, None, None
            project_name, model_name, tag_with_unit = parts
            tag_name = tag_with_unit.split('|')[0]
            logging.debug(f"Parsed topic {topic}: project_name={project_name}, model_name={model_name}, tag_name={tag_name}")
            return project_name, model_name, tag_name
        except Exception as e:
            logging.error(f"Error parsing topic {topic}: {str(e)}")
            return None, None, None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.connection_status.emit("Connected to MQTT Broker")
            logging.info("Connected to MQTT Broker")
            self.subscribe_to_topics()
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
            if not all([project_name, model_name, tag_name]):
                logging.warning(f"Failed to parse topic: {topic}")
                return

            if project_name != self.project_name:
                logging.debug(f"Ignoring message for project {project_name}, expected {self.project_name}")
                return

            # Try to parse payload as JSON first
            try:
                payload_str = payload.decode('utf-8')
                data = json.loads(payload_str)
                values = data.get("values", [])
                if not isinstance(values, list) or not values:
                    logging.warning(f"Invalid JSON payload format: {payload_str}")
                    return
                logging.debug(f"Parsed JSON payload: {values}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                # If JSON parsing fails, assume it's a binary payload
                if len(payload) != (10 + 16384) * 2:
                    logging.warning(f"Invalid binary payload length: {len(payload)} bytes, expected {(10 + 16384) * 2}")
                    return
                values = struct.unpack(f"{10 + 16384}H", payload)
                header = values[:10]
                data_values = values[10:]
                frame_index = header[0] + (header[1] * 65535)
                num_channels = header[2]
                sample_rate = header[3]
                logging.debug(f"Parsed binary header: frame_index={frame_index}, num_channels={num_channels}, sample_rate={sample_rate}")
                values = [float(data_values[0])]  # Take the first value

            # Emit the data
            self.data_received.emit(tag_name, model_name, values)
            logging.debug(f"Emitted data for {tag_name}/{model_name}: {values}")

            # Save to timeview_messages
            message_data = {
                "topic": tag_name,
                "filename": f"data{datetime.now().timestamp()}",
                "frameIndex": 0,  # Simplified for JSON; binary payload already sets this
                "message": values,
                "numberOfChannels": 1,
                "createdAt": datetime.now().isoformat()
            }
            self.db.save_timeview_message(project_name, model_name, message_data)

        except Exception as e:
            logging.error(f"Error processing MQTT message: {str(e)}")

    def subscribe_to_topics(self):
        try:
            tags = self.db.tags_collection.find({"project_name": self.project_name})
            for tag in tags:
                model_name = tag.get("model_name", "default_model")
                tag_name = tag["tag_name"]
                topic = f"{self.project_name}/{model_name}/{tag_name}|m/s"
                self.client.subscribe(topic)
                self.subscribed_topics.append(topic)
                logging.info(f"Subscribed to topic: {topic}")
        except Exception as e:
            logging.error(f"Error subscribing to topics: {str(e)}")

    def start(self):
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            self.client.connect(self.broker, self.port, 60)
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