import os
import numpy as np
import tensorflow as tf
import pandas as pd

model_h5_path = os.path.join('model', 'model.h5')
tflite_model_path = os.path.join('model', 'model.tflite')
header_model_path = os.path.join('model', 'model.h')

if not os.path.exists(model_h5_path):
    raise FileNotFoundError(f"Keras model not found at {model_h5_path}. Please run train_model.py first.")

model = tf.keras.models.load_model(model_h5_path)
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]

try:
    X_train = pd.read_csv(os.path.join('dataset', 'processed', 'x_train.csv')).values
    
    def representative_data_gen():
        for i in range(len(X_train)):
            input_value = np.expand_dims(X_train[i], axis=0).astype(np.float32)
            yield [input_value]
            
    converter.representative_dataset = representative_data_gen
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.float32
    converter.inference_output_type = tf.float32
    print("Configured full integer quantization using representative dataset.")
except Exception as e:
    print(f"Could not configure full integer quantization: {e}. Falling back to default optimization.")
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

tflite_model = converter.convert()

with open(tflite_model_path, 'wb') as f:
    f.write(tflite_model)

print(f"Compressed TFLite model successfully saved to {tflite_model_path}")

h5_size = os.path.getsize(model_h5_path) / 1024.0
tflite_size = os.path.getsize(tflite_model_path) / 1024.0
print(f"Original H5 Model Size: {h5_size:.2f} KB")
print(f"Compressed TFLite Model Size: {tflite_size:.2f} KB")
print(f"Compression Ratio: {h5_size / tflite_size:.2f}x")

def convert_to_c_header(tflite_bytes, var_name="model_tflite", header_path=header_model_path):
    hex_lines = []
    for i, byte in enumerate(tflite_bytes):
        if i % 12 == 0:
            hex_lines.append("\n  ")
        hex_lines.append(f"0x{byte:02x}, ")
        
    c_array_content = "".join(hex_lines)
    
    header_content = f"""#ifndef MODEL_TFLITE_H
#define MODEL_TFLITE_H

#ifdef __has_attribute
#if __has_attribute(aligned)
#define TFLITE_ALIGN __attribute__((aligned(8)))
#else
#define TFLITE_ALIGN alignas(8)
#endif
#else
#define TFLITE_ALIGN alignas(8)
#endif

const unsigned char model_tflite[] TFLITE_ALIGN = {{{c_array_content}
}};

const unsigned int model_tflite_len = {len(tflite_bytes)};

#endif
"""
    with open(header_path, 'w') as f:
        f.write(header_content)
    print(f"C++ header file successfully saved to {header_path}")

convert_to_c_header(tflite_model)
