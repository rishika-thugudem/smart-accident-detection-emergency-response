import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd

X_train = pd.read_csv(os.path.join('dataset', 'processed', 'x_train.csv')).values
y_train = pd.read_csv(os.path.join('dataset', 'processed', 'y_train.csv')).values.flatten()

print(f"Loaded train data. X_train: {X_train.shape}, y_train: {y_train.shape}")

model = Sequential([
    Dense(16, activation='relu', input_shape=(6,), name='dense_input'),
    Dense(8, activation='relu', name='dense_hidden'),
    Dense(1, activation='sigmoid', name='dense_output')
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.005),
    loss='binary_crossentropy',
    metrics=['accuracy']
)

model.summary()

early_stopping = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    epochs=150,
    batch_size=16,
    validation_split=0.2,
    callbacks=[early_stopping],
    verbose=1
)

os.makedirs('model', exist_ok=True)
model_path = os.path.join('model', 'model.h5')
model.save(model_path)
print(f"Model successfully saved to {model_path}")
