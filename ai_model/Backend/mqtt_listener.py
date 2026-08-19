import os
import sys
import json
import paho.mqtt.client as mqtt

# Ensure parent directory is in path for imports when run standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Backend.predict import predict_anomaly
from Backend.database import save_reading, init_db

MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "rideguard/sensor_data")

# Global callback list for WebSocket integrations
data_callbacks = []

def register_callback(cb):
    data_callbacks.append(cb)

def extract_sensor_fields(data):
    """
    Safely extracts AccX/Y/Z and GyroX/Y/Z from a dictionary.
    Handles case variations and alternative names (e.g. ax, acc_x, AccX).
    """
    def find_key(keys_to_try):
        for k in keys_to_try:
            for data_key in data.keys():
                # Normalize keys by converting to lowercase and stripping underscores/spaces
                norm_data_key = data_key.lower().replace('_', '').replace(' ', '')
                if k.lower() == norm_data_key:
                    return data[data_key]
        return None

    acc_x = find_key(['accx', 'acc_x', 'ax'])
    acc_y = find_key(['accy', 'acc_y', 'ay'])
    acc_z = find_key(['accz', 'acc_z', 'az'])
    gyro_x = find_key(['gyrox', 'gyro_x', 'gx'])
    gyro_y = find_key(['gyroy', 'gyro_y', 'gy'])
    gyro_z = find_key(['gyroz', 'gyro_z', 'gz'])
    
    if None in (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z):
        raise ValueError(f"Missing required sensor values in: {data}")
        
    return float(acc_x), float(acc_y), float(acc_z), float(gyro_x), float(gyro_y), float(gyro_z)

# Setup callbacks with version tolerance for paho-mqtt v2.x and v1.x
def on_connect_v2(client, userdata, flags, reason_code, properties=None):
    print(f"Connected to MQTT Broker with result code: {reason_code}")
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to topic: {MQTT_TOPIC}")

def on_connect_v1(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code: {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to topic: {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        # 1. Parse fields
        acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z = extract_sensor_fields(data)
        
        # 2. Predict anomaly
        is_anomaly, probability = predict_anomaly(acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z)
        
        # 3. Save to database
        row_id = save_reading(acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, probability, is_anomaly)
        
        # 4. Construct response dictionary
        result_payload = {
            "id": row_id,
            "acc_x": acc_x,
            "acc_y": acc_y,
            "acc_z": acc_z,
            "gyro_x": gyro_x,
            "gyro_y": gyro_y,
            "gyro_z": gyro_z,
            "anomaly_probability": probability,
            "is_anomaly": int(is_anomaly),
            "timestamp": data.get("timestamp") or ""
        }
        
        # 5. Notify registered callbacks (e.g. WebSockets in app.py)
        for callback in data_callbacks:
            try:
                callback(result_payload)
            except Exception as ex:
                print(f"Callback error: {ex}")
                
        print(f"Processed MQTT data: Anomaly={is_anomaly} (p={probability:.4f}) - saved with ID {row_id}")
        
    except json.JSONDecodeError:
        print(f"Error: Received message payload is not valid JSON. Payload: {msg.payload}")
    except ValueError as val_err:
        print(f"ValueError parsing payload: {val_err}")
    except Exception as e:
        print(f"Unexpected error in MQTT message handler: {e}")

def start_mqtt_client():
    init_db()
    
    # Check if CallbackAPIVersion is available to support both v1 and v2
    if hasattr(mqtt, 'CallbackAPIVersion'):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect_v2
    else:
        client = mqtt.Client()
        client.on_connect = on_connect_v1
        
    client.on_message = on_message
    
    try:
        print(f"Connecting to MQTT Broker (async): {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
        return client
    except Exception as e:
        print(f"Failed to initialize MQTT connection: {e}")
        return None

if __name__ == "__main__":
    print("Starting Standalone MQTT Listener...")
    client = start_mqtt_client()
    if client:
        try:
            client.loop_forever()
        except KeyboardInterrupt:
            print("\nDisconnecting...")
            client.disconnect()
            print("MQTT Listener stopped.")
