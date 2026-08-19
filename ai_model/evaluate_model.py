import os
import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import pandas as pd

X_test = pd.read_csv(os.path.join('dataset', 'processed', 'x_test.csv')).values
y_test = pd.read_csv(os.path.join('dataset', 'processed', 'y_test.csv')).values.flatten()

model_path = os.path.join('model', 'model.h5')
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model file not found at {model_path}. Please run train_model.py first.")

model = tf.keras.models.load_model(model_path)
print(f"Model loaded from {model_path}")

loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f"\nEvaluation on Test Set:")
print(f"Loss: {loss:.4f}")
print(f"Accuracy (Keras Evaluate): {accuracy:.4f}")

y_pred_prob = model.predict(X_test)
y_pred = (y_pred_prob > 0.5).astype(int).flatten()

acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred, zero_division=0)
rec = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
cm = confusion_matrix(y_test, y_pred)

print(f"Accuracy:  {acc*100:.2f}%")
print(f"Precision: {prec*100:.2f}%")
print(f"Recall:    {rec*100:.2f}%")
print(f"F1-Score:  {f1*100:.2f}%")
print("\nConfusion Matrix:")
print(cm)
