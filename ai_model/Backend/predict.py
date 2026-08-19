import os
import json
import numpy as np
import tensorflow as tf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'model')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler_params.json')
TFLITE_PATH = os.path.join(MODEL_DIR, 'model.tflite')
H5_PATH = os.path.join(MODEL_DIR, 'model.h5')

# Load scaler parameters
if not os.path.exists(SCALER_PATH):
    raise FileNotFoundError(f"Scaler parameters not found at {SCALER_PATH}")

with open(SCALER_PATH, 'r') as f:
    scaler_params = json.load(f)
    mean = np.array(scaler_params['mean'], dtype=np.float32)
    std = np.array(scaler_params['std'], dtype=np.float32)

# Load AI model (Try TFLite first, fallback to Keras H5)
model_tflite = None
model_keras = None
use_tflite = False

if os.path.exists(TFLITE_PATH):
    try:
        interpreter = tf.lite.Interpreter(model_path=TFLITE_PATH)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        use_tflite = True
        print(f"Successfully loaded TFLite model from {TFLITE_PATH}")
    except Exception as e:
        print(f"Error loading TFLite model: {e}. Trying Keras .h5 model...")

if not use_tflite:
    if os.path.exists(H5_PATH):
        try:
            model_keras = tf.keras.models.load_model(H5_PATH)
            print(f"Successfully loaded Keras model from {H5_PATH}")
        except Exception as e:
            raise RuntimeError(f"Failed to load both TFLite and Keras models. Keras error: {e}")
    else:
        raise FileNotFoundError(f"No model files found at {TFLITE_PATH} or {H5_PATH}")

def predict_anomaly(acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z):
    """
    Predicts if a sensor reading represents abnormal riding (anomaly).
    Returns (is_anomaly: bool, probability: float)
    """
    # 1. Preprocess raw input
    raw_input = np.array([[acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z]], dtype=np.float32)
    scaled_input = (raw_input - mean) / std
    
    # 2. Run prediction
    if use_tflite:
        interpreter.set_tensor(input_details[0]['index'], scaled_input)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        probability = float(output_data[0][0])
    else:
        # Keras model prediction
        probability = float(model_keras.predict(scaled_input, verbose=0)[0][0])
        
    is_anomaly = probability > 0.5
    return is_anomaly, probability
