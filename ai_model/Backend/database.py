import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sensor_readings.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            acc_x REAL,
            acc_y REAL,
            acc_z REAL,
            gyro_x REAL,
            gyro_y REAL,
            gyro_z REAL,
            anomaly_probability REAL,
            is_anomaly INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_reading(acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, probability, is_anomaly):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sensor_readings (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, anomaly_probability, is_anomaly)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, probability, int(is_anomaly)))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id

def get_recent_readings(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, timestamp, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, anomaly_probability, is_anomaly 
        FROM sensor_readings
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]  # chronological order for UI charting

def get_recent_alerts(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, timestamp, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, anomaly_probability, is_anomaly 
        FROM sensor_readings
        WHERE is_anomaly = 1
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]  # newest alerts first

def clear_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sensor_readings')
    conn.commit()
    conn.close()
