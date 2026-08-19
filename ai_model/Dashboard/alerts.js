// RideGuard AI - Dashboard Alerts & Networking Logic
let socket = null;
let reconnectInterval = 3000;
let totalReadingsCount = 0;
let totalAlertsCount = 0;

// Connect to secure WebSocket
function connectWebSocket() {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
  
  console.log(`Connecting to WebSocket: ${wsUrl}`);
  
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("WebSocket connection established.");
    updateWebSocketUI(true);
    fetchHistory();
    fetchAlerts();
  };

  socket.onclose = () => {
    console.log("WebSocket connection lost. Attempting reconnect...");
    updateWebSocketUI(false);
    setTimeout(connectWebSocket, reconnectInterval);
  };

  socket.onerror = (error) => {
    console.error("WebSocket error observed:", error);
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      processIncomingData(data);
    } catch (e) {
      console.error("Error parsing WebSocket message:", e);
    }
  };
}

function updateWebSocketUI(isConnected) {
  const card = document.getElementById('websocket-card');
  const icon = document.getElementById('websocket-icon');
  const val = document.getElementById('websocket-value');

  if (isConnected) {
    card.className = "glass-card metric-card connected-link";
    icon.className = "fa-solid fa-link";
    val.innerText = "CONNECTED";
  } else {
    card.className = "glass-card metric-card disconnected-link";
    icon.className = "fa-solid fa-link-slash";
    val.innerText = "DISCONNECTED";
  }
}

// REST Api fetchers
async function fetchHistory() {
  try {
    const response = await fetch('/api/readings?limit=100');
    if (!response.ok) throw new Error("API error fetching history");
    const readings = await response.json();
    
    // Set total count
    totalReadingsCount = readings.length;
    document.getElementById('total-records-value').innerText = totalReadingsCount;
    
    // Preload into the chart
    if (typeof preloadChartData === 'function') {
      preloadChartData(readings);
    }
  } catch (error) {
    console.error("Failed to fetch history:", error);
  }
}

async function fetchAlerts() {
  try {
    const response = await fetch('/api/alerts?limit=50');
    if (!response.ok) throw new Error("API error fetching alerts");
    const alerts = await response.json();
    
    totalAlertsCount = alerts.length;
    document.getElementById('total-alerts-value').innerText = totalAlertsCount;
    
    const list = document.getElementById('alerts-list');
    
    if (alerts.length > 0) {
      list.innerHTML = ''; // clear placeholder
      alerts.forEach(alert => {
        appendAlertToUI(alert, false); // append at end of list (historical)
      });
    }
  } catch (error) {
    console.error("Failed to fetch alerts:", error);
  }
}

// Ingestion processing
function processIncomingData(data) {
  // Increment counter
  totalReadingsCount++;
  document.getElementById('total-records-value').innerText = totalReadingsCount;

  // Add to chart
  if (typeof addChartData === 'function') {
    addChartData(
      data.acc_x, data.acc_y, data.acc_z,
      data.gyro_x, data.gyro_y, data.gyro_z,
      data.timestamp
    );
  }

  // Update Status & Prob progress bar
  updateStatusUI(data.is_anomaly, data.anomaly_probability);

  // If anomaly, update alerts
  if (data.is_anomaly === 1) {
    totalAlertsCount++;
    document.getElementById('total-alerts-value').innerText = totalAlertsCount;
    appendAlertToUI(data, true); // prepend in real-time
  }
}

function updateStatusUI(isAnomaly, probability) {
  const card = document.getElementById('status-card');
  const icon = document.getElementById('status-icon');
  const value = document.getElementById('status-value');

  // Simulator probability elements
  const liveProbText = document.getElementById('live-prob-value');
  const liveProbFill = document.getElementById('live-prob-fill');

  // Set probability indicators
  const pct = (probability * 100).toFixed(1);
  liveProbText.innerText = `${pct}%`;
  liveProbFill.style.width = `${pct}%`;

  if (isAnomaly === 1) {
    card.className = "glass-card metric-card status-anomaly";
    icon.className = "fa-solid fa-triangle-exclamation";
    value.innerText = "ANOMALY";
    liveProbText.style.color = "var(--accent-red)";
  } else {
    card.className = "glass-card metric-card status-safe";
    icon.className = "fa-solid fa-circle-check";
    value.innerText = "SAFE";
    liveProbText.style.color = "var(--accent-cyan)";
  }
}

function appendAlertToUI(alert, prepend = true) {
  const list = document.getElementById('alerts-list');
  
  // Clear placeholder if it exists
  const noAlerts = list.querySelector('.no-alerts');
  if (noAlerts) {
    list.innerHTML = '';
  }

  const dateStr = alert.timestamp 
    ? new Date(alert.timestamp).toLocaleString() 
    : new Date().toLocaleString();

  const item = document.createElement('div');
  item.className = 'alert-item';
  item.innerHTML = `
    <div class="alert-item-top">
      <span class="alert-time"><i class="fa-regular fa-clock"></i> ${dateStr}</span>
      <span class="alert-prob">Prob: ${(alert.anomaly_probability * 100).toFixed(1)}%</span>
    </div>
    <div class="alert-item-details">
      <div class="alert-val">AX: <span>${alert.acc_x.toFixed(2)}</span></div>
      <div class="alert-val">AY: <span>${alert.acc_y.toFixed(2)}</span></div>
      <div class="alert-val">AZ: <span>${alert.acc_z.toFixed(2)}</span></div>
      <div class="alert-val">GX: <span>${alert.gyro_x.toFixed(1)}</span></div>
      <div class="alert-val">GY: <span>${alert.gyro_y.toFixed(1)}</span></div>
      <div class="alert-val">GZ: <span>${alert.gyro_z.toFixed(1)}</span></div>
    </div>
  `;

  if (prepend) {
    list.insertBefore(item, list.firstChild);
  } else {
    list.appendChild(item);
  }
}

// REST Injection Form
async function injectTelemetry() {
  const acc_x = parseFloat(document.getElementById('input-acc-x').value);
  const acc_y = parseFloat(document.getElementById('input-acc-y').value);
  const acc_z = parseFloat(document.getElementById('input-acc-z').value);
  const gyro_x = parseFloat(document.getElementById('input-gyro-x').value);
  const gyro_y = parseFloat(document.getElementById('input-gyro-y').value);
  const gyro_z = parseFloat(document.getElementById('input-gyro-z').value);

  const payload = {
    acc_x: acc_x,
    acc_y: acc_y,
    acc_z: acc_z,
    gyro_x: gyro_x,
    gyro_y: gyro_y,
    gyro_z: gyro_z
  };

  try {
    const response = await fetch('/api/predict', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) throw new Error("Failed to post simulation data");
    // We don't manually draw here, as the backend will broadcast this telemetry via WebSocket back to us!
    
  } catch (error) {
    console.error("Simulation inject error:", error);
    alert("Simulation post failed. Is the backend running?");
  }
}

// Clear Database REST Call
async function clearDB() {
  if (!confirm("Are you sure you want to clear all telemetry and alert database logs?")) {
    return;
  }

  try {
    const response = await fetch('/api/db/clear', { method: 'POST' });
    if (!response.ok) throw new Error("Failed to clear DB");
    
    // Reset local UI states
    totalReadingsCount = 0;
    totalAlertsCount = 0;
    document.getElementById('total-records-value').innerText = "0";
    document.getElementById('total-alerts-value').innerText = "0";
    
    // Reset Status
    updateStatusUI(0, 0.0);
    
    // Reset Chart
    if (typeof clearChartData === 'function') {
      clearChartData();
    }
    
    // Clear list
    document.getElementById('alerts-list').innerHTML = `
      <div class="no-alerts">
        <i class="fa-solid fa-satellite-dish"></i>
        <span>Monitoring active sensor feeds.<br>Awaiting anomalous activity...</span>
      </div>
    `;
    
    alert("Database successfully cleared.");
  } catch (error) {
    console.error("Failed to clear DB:", error);
    alert("DB clear operation failed.");
  }
}

// Slider helper
function updateSliderLabel(axis, val) {
  const valueElement = document.getElementById(`val-${axis}`);
  const floatVal = parseFloat(val);
  valueElement.innerText = floatVal.toFixed(2);
}

// Preset Loader
function loadPreset(presetName) {
  // Preset definitions corresponding to actual riding features
  const presets = {
    normal: { ax: 0.14, ay: -0.06, az: 9.55, gx: 0.25, gy: 0.32, gz: 5.03 }, // Row 58
    braking: { ax: -5.82, ay: 0.41, az: 9.01, gx: 4.43, gy: 14.03, gz: -0.33 }, // Row 13
    turn: { ax: 0.16, ay: 3.97, az: 10.61, gx: 7.51, gy: 1.19, gz: 50.66 }, // Row 12
    bump: { ax: -0.46, ay: 0.98, az: 13.24, gx: 13.66, gy: -6.35, gz: -0.4 }, // Row 10
    crash: { ax: 8.78, ay: 6.29, az: 15.47, gx: 73.44, gy: 43.41, gz: 72.14 } // Row 6
  };

  const p = presets[presetName];
  if (!p) return;

  // Set slider input values
  document.getElementById('input-acc-x').value = p.ax;
  document.getElementById('input-acc-y').value = p.ay;
  document.getElementById('input-acc-z').value = p.az;
  document.getElementById('input-gyro-x').value = p.gx;
  document.getElementById('input-gyro-y').value = p.gy;
  document.getElementById('input-gyro-z').value = p.gz;

  // Update visual numeric labels
  updateSliderLabel('acc-x', p.ax);
  updateSliderLabel('acc-y', p.ay);
  updateSliderLabel('acc-z', p.az);
  updateSliderLabel('gyro-x', p.gx);
  updateSliderLabel('gyro-y', p.gy);
  updateSliderLabel('gyro-z', p.gz);
}

let simulationInterval = null;
function toggleLiveSimulation() {
  const btn = document.getElementById('btn-toggle-sim');
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
    btn.innerHTML = '<i class="fa-solid fa-play"></i> Auto Simulate';
    btn.style.background = 'rgba(15, 23, 42, 0.05)';
    btn.style.color = 'var(--text-primary)';
  } else {
    btn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Simulation';
    btn.style.background = 'var(--accent-cyan)';
    btn.style.color = 'white';
    
    simulationInterval = setInterval(() => {
      const isNormal = Math.random() < 0.6;
      const presets = ['normal', 'braking', 'turn', 'bump', 'crash'];
      const chosenPreset = isNormal ? 'normal' : presets[Math.floor(Math.random() * (presets.length - 1)) + 1];
      
      loadPreset(chosenPreset);
      
      const acc_x = parseFloat(document.getElementById('input-acc-x').value) + (Math.random() - 0.5) * 0.2;
      const acc_y = parseFloat(document.getElementById('input-acc-y').value) + (Math.random() - 0.5) * 0.2;
      const acc_z = parseFloat(document.getElementById('input-acc-z').value) + (Math.random() - 0.5) * 0.2;
      const gyro_x = parseFloat(document.getElementById('input-gyro-x').value) + (Math.random() - 0.5) * 4.0;
      const gyro_y = parseFloat(document.getElementById('input-gyro-y').value) + (Math.random() - 0.5) * 4.0;
      const gyro_z = parseFloat(document.getElementById('input-gyro-z').value) + (Math.random() - 0.5) * 4.0;

      document.getElementById('input-acc-x').value = acc_x;
      document.getElementById('input-acc-y').value = acc_y;
      document.getElementById('input-acc-z').value = acc_z;
      document.getElementById('input-gyro-x').value = gyro_x;
      document.getElementById('input-gyro-y').value = gyro_y;
      document.getElementById('input-gyro-z').value = gyro_z;

      updateSliderLabel('acc-x', acc_x);
      updateSliderLabel('acc-y', acc_y);
      updateSliderLabel('acc-z', acc_z);
      updateSliderLabel('gyro-x', gyro_x);
      updateSliderLabel('gyro-y', gyro_y);
      updateSliderLabel('gyro-z', gyro_z);

      injectTelemetry();
    }, 2000);
  }
}

// Start WebSocket on DOM load
document.addEventListener('DOMContentLoaded', () => {
  connectWebSocket();
  loadPreset('normal'); // Default presets
});
