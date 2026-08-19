// Chart.js Manager for RideGuard AI
let telemetryChart = null;
const MAX_DATA_POINTS = 30;

function initChart() {
  const ctx = document.getElementById('telemetryChart').getContext('2d');
  
  // Custom font options matching our design
  const fontOptions = {
    family: "'Inter', sans-serif",
    size: 10,
  };

  const data = {
    labels: Array(MAX_DATA_POINTS).fill(''), // empty labels for sliding window
    datasets: [
      // Accelerometer datasets (Left Y-Axis)
      {
        label: 'Acc X (m/s²)',
        data: Array(MAX_DATA_POINTS).fill(null),
        borderColor: '#00f0ff',
        backgroundColor: 'rgba(0, 240, 255, 0.05)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Acc Y (m/s²)',
        data: Array(MAX_DATA_POINTS).fill(null),
        borderColor: '#3b82f6',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Acc Z (m/s²)',
        data: Array(MAX_DATA_POINTS).fill(null),
        borderColor: '#8b5cf6',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.3,
        yAxisID: 'y',
      },
      // Gyroscope datasets (Right Y-Axis)
      {
        label: 'Gyro X (°/s)',
        data: Array(MAX_DATA_POINTS).fill(null),
        borderColor: '#f59e0b',
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderDash: [3, 3],
        pointRadius: 0,
        tension: 0.3,
        yAxisID: 'y1',
      },
      {
        label: 'Gyro Y (°/s)',
        data: Array(MAX_DATA_POINTS).fill(null),
        borderColor: '#ec4899',
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderDash: [3, 3],
        pointRadius: 0,
        tension: 0.3,
        yAxisID: 'y1',
      },
      {
        label: 'Gyro Z (°/s)',
        data: Array(MAX_DATA_POINTS).fill(null),
        borderColor: '#ef4444',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.3,
        yAxisID: 'y1',
      }
    ]
  };

  const config = {
    type: 'line',
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 250 // fast transitions for real-time feel
      },
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: '#0f172a',
            boxWidth: 12,
            font: fontOptions,
            padding: 15
          }
        },
        tooltip: {
          backgroundColor: 'rgba(255, 255, 255, 0.96)',
          titleColor: '#0ea5e9',
          bodyColor: '#0f172a',
          borderColor: 'rgba(15, 23, 42, 0.08)',
          borderWidth: 1,
          padding: 10,
          titleFont: { family: "'Outfit', sans-serif", weight: 'bold' },
          bodyFont: { family: "'Inter', sans-serif" }
        }
      },
      scales: {
        x: {
          grid: {
            color: 'rgba(15, 23, 42, 0.03)',
            borderColor: 'rgba(15, 23, 42, 0.08)'
          },
          ticks: {
            color: '#475569',
            font: fontOptions
          }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: {
            display: true,
            text: 'Accelerometer (m/s²)',
            color: '#00f0ff',
            font: { family: "'Outfit', sans-serif", weight: '600', size: 11 }
          },
          grid: {
            color: 'rgba(15, 23, 42, 0.04)',
            borderColor: 'rgba(15, 23, 42, 0.08)'
          },
          ticks: {
            color: '#475569',
            font: fontOptions
          },
          suggestedMin: -15,
          suggestedMax: 15
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: {
            display: true,
            text: 'Gyroscope (°/s)',
            color: '#ef4444',
            font: { family: "'Outfit', sans-serif", weight: '600', size: 11 }
          },
          grid: {
            drawOnChartArea: false, // only show grid lines for left axis
            borderColor: 'rgba(15, 23, 42, 0.08)'
          },
          ticks: {
            color: '#475569',
            font: fontOptions
          },
          suggestedMin: -250,
          suggestedMax: 250
        }
      }
    }
  };

  telemetryChart = new Chart(ctx, config);
}

function addChartData(acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp = '') {
  if (!telemetryChart) return;

  const datasets = telemetryChart.data.datasets;
  const labels = telemetryChart.data.labels;

  // Shift values
  labels.shift();
  labels.push(timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString());

  const values = [acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z];
  for (let i = 0; i < datasets.length; i++) {
    datasets[i].data.shift();
    datasets[i].data.push(values[i]);
  }

  telemetryChart.update('none'); // Update without default animation for speed
}

function clearChartData() {
  if (!telemetryChart) return;
  
  telemetryChart.data.datasets.forEach(dataset => {
    dataset.data = Array(MAX_DATA_POINTS).fill(null);
  });
  telemetryChart.data.labels = Array(MAX_DATA_POINTS).fill('');
  telemetryChart.update();
}

function preloadChartData(records) {
  if (!telemetryChart || !records || records.length === 0) return;

  // We want the last MAX_DATA_POINTS elements
  const sliceIndex = Math.max(0, records.length - MAX_DATA_POINTS);
  const dataSlice = records.slice(sliceIndex);

  // Pad the beginning with nulls if we have fewer than MAX_DATA_POINTS
  const paddingLength = MAX_DATA_POINTS - dataSlice.length;
  
  const labels = Array(paddingLength).fill('');
  const acc_x_data = Array(paddingLength).fill(null);
  const acc_y_data = Array(paddingLength).fill(null);
  const acc_z_data = Array(paddingLength).fill(null);
  const gyro_x_data = Array(paddingLength).fill(null);
  const gyro_y_data = Array(paddingLength).fill(null);
  const gyro_z_data = Array(paddingLength).fill(null);

  dataSlice.forEach(rec => {
    labels.push(new Date(rec.timestamp).toLocaleTimeString());
    acc_x_data.push(rec.acc_x);
    acc_y_data.push(rec.acc_y);
    acc_z_data.push(rec.acc_z);
    gyro_x_data.push(rec.gyro_x);
    gyro_y_data.push(rec.gyro_y);
    gyro_z_data.push(rec.gyro_z);
  });

  telemetryChart.data.labels = labels;
  telemetryChart.data.datasets[0].data = acc_x_data;
  telemetryChart.data.datasets[1].data = acc_y_data;
  telemetryChart.data.datasets[2].data = acc_z_data;
  telemetryChart.data.datasets[3].data = gyro_x_data;
  telemetryChart.data.datasets[4].data = gyro_y_data;
  telemetryChart.data.datasets[5].data = gyro_z_data;

  telemetryChart.update();
}

// Initialise chart on DOM load
document.addEventListener('DOMContentLoaded', () => {
  initChart();
});
