import os
import sys
import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Backend.database import (
    init_db, save_reading, get_recent_readings, get_recent_alerts, clear_database
)
from Backend.predict import predict_anomaly
from Backend.mqtt_listener import start_mqtt_client, register_callback

# Generate self-signed SSL certificates dynamically if they are missing
CERT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cert.pem")
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "key.pem")

def generate_ssl_keys():
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        print("SSL certificates already exist. Skipping generation.")
        return
        
    print("Generating self-signed SSL certificate and private key...")
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    import datetime

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "RideGuard AI"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1")
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    os.makedirs(os.path.dirname(CERT_FILE), exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"SSL keys written successfully:\n  - {KEY_FILE}\n  - {CERT_FILE}")

generate_ssl_keys()

# Active WebSocket connections list
active_websockets = []
main_loop = None

async def broadcast_telemetry(data):
    """Broadcasts telemetry payload to all connected WebSocket clients."""
    if not active_websockets:
        return
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
            
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

def threadsafe_mqtt_callback(data):
    """Callback triggered from MQTT background thread. Schedules broadcast on main event loop."""
    if main_loop:
        asyncio.run_coroutine_threadsafe(broadcast_telemetry(data), main_loop)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    # 1. Initialize SQLite Database
    init_db()
    print("Database initialized.")
    
    # 2. Setup MQTT listener with threadsafe callback
    register_callback(threadsafe_mqtt_callback)
    mqtt_client = start_mqtt_client()
    mqtt_thread = None
    
    if mqtt_client:
        mqtt_thread = threading.Thread(target=mqtt_client.loop_forever, daemon=True)
        mqtt_thread.start()
        print("MQTT client loop running in background thread.")
        
    yield
    
    # Shutdown logic
    if mqtt_client:
        mqtt_client.disconnect()
        print("MQTT client disconnected.")

app = FastAPI(
    title="RideGuard AI API",
    description="Backend API for RideGuard AI Real-Time Ride Safety and Anomaly Detection System.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for REST endpoints
class SensorTelemetry(BaseModel):
    acc_x: float
    acc_y: float
    acc_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float

@app.get("/")
async def redirect_to_dashboard():
    return RedirectResponse(url="/dashboard/index.html")

@app.get("/api/readings")
async def get_readings(limit: int = 100):
    try:
        return get_recent_readings(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    try:
        return get_recent_alerts(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/predict")
async def create_prediction(telemetry: SensorTelemetry):
    try:
        is_anomaly, probability = predict_anomaly(
            telemetry.acc_x, telemetry.acc_y, telemetry.acc_z,
            telemetry.gyro_x, telemetry.gyro_y, telemetry.gyro_z
        )
        
        row_id = save_reading(
            telemetry.acc_x, telemetry.acc_y, telemetry.acc_z,
            telemetry.gyro_x, telemetry.gyro_y, telemetry.gyro_z,
            probability, is_anomaly
        )
        
        result = {
            "id": row_id,
            "acc_x": telemetry.acc_x,
            "acc_y": telemetry.acc_y,
            "acc_z": telemetry.acc_z,
            "gyro_x": telemetry.gyro_x,
            "gyro_y": telemetry.gyro_y,
            "gyro_z": telemetry.gyro_z,
            "anomaly_probability": probability,
            "is_anomaly": int(is_anomaly)
        }
        
        # Broadcast to dashboard WebSockets
        await broadcast_telemetry(result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/clear")
async def clear_data():
    try:
        clear_database()
        return {"status": "success", "message": "All database records successfully cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    print(f"WebSocket client connected. Active: {len(active_websockets)}")
    try:
        while True:
            # Keep connection open by listening for arbitrary text/heartbeats
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        print(f"WebSocket client disconnected. Active: {len(active_websockets)}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)

# Mount Dashboard static files
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Dashboard")
if os.path.exists(DASHBOARD_DIR):
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")
    print(f"Mounted static Dashboard files from {DASHBOARD_DIR}")
else:
    print(f"Warning: Dashboard directory not found at {DASHBOARD_DIR}")

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import time

    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8000/dashboard/index.html")

    threading.Thread(target=open_browser, daemon=True).start()

    print("Launching RideGuard AI FastAPI Server...")
    uvicorn.run(
        "Backend.app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False
    )
