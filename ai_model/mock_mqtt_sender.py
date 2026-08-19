import time
import json
import random
import paho.mqtt.client as mqtt

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "rideguard/sensor_data"

# Telemetry presets matching riding states
PRESETS = [
    # Normal Riding (High chance)
    {"AccX": 0.14, "AccY": -0.06, "AccZ": 9.55, "GyroX": 0.25, "GyroY": 0.32, "GyroZ": 5.03, "state": "Normal Riding"},
    {"AccX": 0.09, "AccY": 0.1, "AccZ": 9.82, "GyroX": -0.99, "GyroY": 0.92, "GyroZ": 3.18, "state": "Normal Riding"},
    {"AccX": 0.14, "AccY": -0.34, "AccZ": 9.57, "GyroX": -0.82, "GyroY": -1.83, "GyroZ": 0.73, "state": "Normal Riding"},
    
    # Sudden Braking
    {"AccX": -5.82, "AccY": 0.41, "AccZ": 9.01, "GyroX": 4.43, "GyroY": 14.03, "GyroZ": -0.33, "state": "Sudden Braking"},
    {"AccX": -8.29, "AccY": 0.37, "AccZ": 9.75, "GyroX": -1.82, "GyroY": 8.92, "GyroZ": -1.62, "state": "Sudden Braking"},
    
    # Sharp Turns
    {"AccX": 0.16, "AccY": 3.97, "AccZ": 10.61, "GyroX": 7.51, "GyroY": 1.19, "GyroZ": 50.66, "state": "Sharp Turn"},
    {"AccX": 0.31, "AccY": 3.49, "AccZ": 9.18, "GyroX": -0.11, "GyroY": 2.59, "GyroZ": 53.48, "state": "Sharp Turn"},
    
    # Speed Bump
    {"AccX": -0.46, "AccY": 0.98, "AccZ": 13.24, "GyroX": 13.66, "GyroY": -6.35, "GyroZ": -0.4, "state": "Speed Bump"},
    
    # Major Crash
    {"AccX": 8.78, "AccY": 6.29, "AccZ": 15.47, "GyroX": 73.44, "GyroY": 43.41, "GyroZ": 72.14, "state": "Major Crash"},
    {"AccX": 6.31, "AccY": 6.42, "AccZ": 16.45, "GyroX": 85.55, "GyroY": 95.5, "GyroZ": 92.7, "state": "Major Crash"}
]

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"Mock Sender connected with result code: {reason_code}")

def start_mock_publisher():
    # Setup client compatibility for paho-mqtt v2.x/v1.x
    if hasattr(mqtt, 'CallbackAPIVersion'):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    else:
        client = mqtt.Client()
        
    client.on_connect = on_connect
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print(f"Starting mock publisher. Topic: {MQTT_TOPIC} on {MQTT_BROKER}")
        print("Press Ctrl+C to stop.\n")
        
        while True:
            # Pick a state. 60% chance of normal, 40% of anomalous behavior
            if random.random() < 0.6:
                preset = random.choice([p for p in PRESETS if p["state"] == "Normal Riding"])
            else:
                preset = random.choice([p for p in PRESETS if p["state"] != "Normal Riding"])
                
            # Add small random noise to make the data organic
            payload = {
                "AccX": preset["AccX"] + random.uniform(-0.1, 0.1),
                "AccY": preset["AccY"] + random.uniform(-0.1, 0.1),
                "AccZ": preset["AccZ"] + random.uniform(-0.1, 0.1),
                "GyroX": preset["GyroX"] + random.uniform(-2.0, 2.0),
                "GyroY": preset["GyroY"] + random.uniform(-2.0, 2.0),
                "GyroZ": preset["GyroZ"] + random.uniform(-2.0, 2.0)
            }
            
            payload_str = json.dumps(payload)
            print(f"Publishing event ({preset['state']}): {payload_str}")
            client.publish(MQTT_TOPIC, payload_str)
            
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        print("\nStopping publisher...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Disconnected.")

if __name__ == "__main__":
    start_mock_publisher()
