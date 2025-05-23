import paho.mqtt.client as mqtt
import numpy as np
import struct
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SineWavePublisher:
    def __init__(self, broker="192.168.1.179", port=1883, topic="sarayu/tag1/topic1|m/s"):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        self.num_channels = 4
        self.sample_rate = 1000  # Hz
        self.samples_per_message = 1000  # 1 second of data
        self.amplitude = 10000  # Amplitude for uint16_t range
        self.offset = 32768  # Center point for uint16_t
        self.frequencies = [1.0, 1.1, 1.2, 1.3]  # Slightly different frequencies for each channel
        logging.debug(f"Initializing SineWavePublisher with broker: {broker}, topic: {topic}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT Broker")
        else:
            logging.error(f"Failed to connect to MQTT Broker with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logging.info("Disconnected from MQTT Broker")

    def start(self):
        try:
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logging.info("MQTT client started")
        except Exception as e:
            logging.error(f"Failed to start MQTT client: {str(e)}")
            raise

    def stop(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logging.info("MQTT client stopped")
        except Exception as e:
            logging.error(f"Error stopping MQTT client: {str(e)}")

    def generate_sine_wave(self, t):
        """Generate sine wave data for all channels."""
        data = []
        for ch in range(self.num_channels):
            # Generate sine wave for each channel with slight frequency variation
            values = self.amplitude * np.sin(2 * np.pi * self.frequencies[ch] * t) + self.offset
            # Clip to uint16_t range and convert to integers
            values = np.clip(values, 0, 65535).astype(np.uint16)
            data.append(values)
        return data

    def publish(self):
        try:
            t = np.linspace(0, 1, self.samples_per_message, endpoint=False)  # 1 second of data
            channel_data = self.generate_sine_wave(t)
            
            # Interleave channel data: [ch1[0], ch2[0], ch3[0], ch4[0], ch1[1], ch2[1], ...]
            interleaved_data = []
            for i in range(self.samples_per_message):
                for ch in range(self.num_channels):
                    interleaved_data.append(channel_data[ch][i])
            
            # Pack as uint16_t values
            binary_data = struct.pack(f"<{len(interleaved_data)}H", *interleaved_data)
            self.client.publish(self.topic, binary_data, qos=0)
            logging.debug(f"Published {len(interleaved_data)} samples to {self.topic}")
        except Exception as e:
            logging.error(f"Error publishing data: {str(e)}")

    def run(self, duration=None):
        """Run the publisher for a specified duration (seconds) or indefinitely if None."""
        try:
            self.start()
            start_time = time.time()
            while duration is None or (time.time() - start_time) < duration:
                self.publish()
                time.sleep(1.0)  # Publish every second
        except KeyboardInterrupt:
            logging.info("Received KeyboardInterrupt, stopping publisher")
        finally:
            self.stop()

if __name__ == "__main__":
    publisher = SineWavePublisher()
    publisher.run(duration=60)  # Run for 60 seconds