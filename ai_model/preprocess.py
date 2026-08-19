import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import json

RAW_DIR = os.path.join('dataset', 'raw_data')
PROCESSED_DIR = os.path.join('dataset', 'processed')
MODEL_DIR = 'model'

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

src_csv = 'sensor_dataset.csv'
dst_csv = os.path.join(RAW_DIR, 'sensor_dataset.csv')
if os.path.exists(src_csv):
    import shutil
    shutil.copy(src_csv, dst_csv)
    print(f"Copied {src_csv} to {dst_csv}")
else:
    print(f"Source {src_csv} not found in current directory.")

df = pd.read_csv(dst_csv)

print("Unique labels found in dataset:", df['Label'].unique())

df['Binary_Label'] = df['Label'].apply(lambda x: 0 if str(x).strip() == 'Normal Riding' else 1)

labels_df = pd.DataFrame({
    'Row_ID': df.index,
    'Original_Label': df['Label'],
    'Binary_Label': df['Binary_Label']
})
labels_csv_path = os.path.join('dataset', 'labels.csv')
labels_df.to_csv(labels_csv_path, index=False)
print(f"Saved binary labels to {labels_csv_path}")

features = ['AccX', 'AccY', 'AccZ', 'GyroX', 'GyroY', 'GyroZ']
X = df[features].values
y = df['Binary_Label'].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

scaler_params = {
    'mean': scaler.mean_.tolist(),
    'std': scaler.scale_.tolist()
}
scaler_path = os.path.join(MODEL_DIR, 'scaler_params.json')
with open(scaler_path, 'w') as f:
    json.dump(scaler_params, f, indent=4)
print(f"Saved scaler parameters to {scaler_path}")

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

pd.DataFrame(X_train, columns=features).to_csv(os.path.join(PROCESSED_DIR, 'x_train.csv'), index=False)
pd.DataFrame(X_test, columns=features).to_csv(os.path.join(PROCESSED_DIR, 'x_test.csv'), index=False)
pd.DataFrame(y_train, columns=['Label']).to_csv(os.path.join(PROCESSED_DIR, 'y_train.csv'), index=False)
pd.DataFrame(y_test, columns=['Label']).to_csv(os.path.join(PROCESSED_DIR, 'y_test.csv'), index=False)

for filename in ['x_train.npy', 'x_test.npy', 'y_train.npy', 'y_test.npy']:
    npy_path = os.path.join(PROCESSED_DIR, filename)
    if os.path.exists(npy_path):
        os.remove(npy_path)

print("Preprocessed data saved to dataset/processed/ as CSV files.")
print(f"Train set shape: {X_train.shape}, Test set shape: {X_test.shape}")
