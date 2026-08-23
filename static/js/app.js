Chart.defaults.font.family = "'Fredoka', -apple-system, Segoe UI, Roboto, sans-serif";

// ---- keep every chart's x-axis (timestamp) range in sync ----------------
const allCharts = [];
let isSyncingZoom = false;

function syncXRange(sourceChart) {
  if (isSyncingZoom) return;
  isSyncingZoom = true;
  const { min, max } = sourceChart.scales.x;
  allCharts.forEach(c => {
    if (c === sourceChart) return;
    c.options.scales.x.min = min;
    c.options.scales.x.max = max;
    c.update('none');
  });
  isSyncingZoom = false;
}

// ---- formatting helpers -------------------------------------------------
function fmt(value, digits = 2, unit = '') {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toFixed(digits) + unit;
}

function statCard(label, value, sub) {
  const card = document.createElement('div');
  card.className = 'stat-card';
  card.innerHTML = `
    <div class="label">${label}</div>
    <div class="value">${value}</div>
    ${sub ? `<div class="sub">${sub}</div>` : ''}
  `;
  return card;
}

// ---- flight-event annotations (liftoff / apogee / landing) ------------
function eventLine(x, label) {
  return {
    type: 'line',
    xMin: x,
    xMax: x,
    borderColor: '#000',
    borderWidth: 2.5,
    label: {
      display: true,
      content: label,
      position: 'end',
      yAdjust: 14,
      xAdjust: 12,
      rotation: 90,
      color: '#000',
      font: { size: 15, weight: 'bold' },
      backgroundColor: 'transparent'
    }
  };
}

function buildEventAnnotations(events) {
  if (!events) return {};
  const annotations = {};
  if (events.liftoff) annotations.liftoff = eventLine(events.liftoff.timestamp, 'Liftoff');
  if (events.apogee) annotations.apogee = eventLine(events.apogee.timestamp, 'Apogee');
  if (events.landing) annotations.landing = eventLine(events.landing.timestamp, 'Landing');
  return annotations;
}

// ---- chart builder (zoom/pan + channel-selection checkboxes) ----------
function buildChart(canvasId, controlsId, timestamps, datasets, yLabel, annotations, extraScales) {
  const canvas = document.getElementById(canvasId);
  const controls = document.getElementById(controlsId);

  // Same tick spacing on every chart, so their x-axes always match.
  const tickStep = Math.max(1, Math.ceil(timestamps.length / 24));

  const chart = new Chart(canvas, {
    type: 'line',
    data: { labels: timestamps, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: Object.assign({
        x: {
          title: { display: true, text: 'Timestamp (s)', color: '#000' },
          ticks: { color: '#000', minRotation: 90, maxRotation: 90, autoSkip: false },
          afterBuildTicks: axis => {
            axis.ticks = axis.ticks.filter((_, i) => i % tickStep === 0);
          },
          grid: { color: '#f2c6da' }
        },
        y: {
          title: { display: true, text: yLabel, color: '#000' },
          ticks: { color: '#000' },
          grid: { color: '#f2c6da' }
        }
      }, extraScales || {}),
      plugins: {
        legend: { labels: { color: '#000', usePointStyle: true, pointStyle: 'circle' } },
        annotation: { annotations: annotations || {} },
        zoom: {
          pan: { enabled: true, mode: 'x', onPanComplete: ({ chart }) => syncXRange(chart) },
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: 'x',
            onZoomComplete: ({ chart }) => syncXRange(chart)
          }
        }
      }
    }
  });

  allCharts.push(chart);

  datasets.forEach((ds, i) => {
    const label = document.createElement('label');
    label.className = 'channel-toggle';
    label.style.borderColor = ds.borderColor;
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = true;
    checkbox.addEventListener('change', () => {
      chart.setDatasetVisibility(i, checkbox.checked);
      chart.update();
    });
    label.appendChild(checkbox);
    label.append(' ' + ds.label);
    controls.appendChild(label);
  });

  const resetBtn = document.createElement('button');
  resetBtn.type = 'button';
  resetBtn.className = 'reset-zoom-btn';
  resetBtn.textContent = 'Reset';
  resetBtn.addEventListener('click', () => allCharts.forEach(c => c.resetZoom()));
  controls.appendChild(resetBtn);

  return chart;
}

function line(label, values, color, extra) {
  return Object.assign(
    { label, data: values, borderColor: color, backgroundColor: color, fill: false, pointRadius: 0 },
    extra || {}
  );
}

// ---- load data -----------------------------------------------------------
Promise.all([
  fetch('/api/telemetry').then(res => res.json()),
  fetch('/api/summary').then(res => res.json())
])
  .then(([data, summary]) => {
    if (data && data.error) {
      document.getElementById('status').textContent = 'Error: ' + data.error;
      return;
    }
    if (!Array.isArray(data) || data.length === 0) {
      document.getElementById('status').textContent = 'No telemetry data to show yet.';
      return;
    }
    document.getElementById('status').textContent = '';

    const t = data.map(row => row.TIMESTAMP);
    const last = data[data.length - 1];
    const events = (summary && !summary.error) ? summary.events : null;
    const annotations = buildEventAnnotations(events);

    // ---- flight summary stat cards --------------------------------------
    const gridTop = document.getElementById('summaryTop');
    const gridBottom = document.getElementById('summaryBottom');
    if (summary && !summary.error) {
      if (summary.max_acceleration) {
        gridTop.appendChild(statCard('Max Acceleration', fmt(summary.max_acceleration.value, 1, ' m/s²'),
          `at t=${fmt(summary.max_acceleration.timestamp, 1, 's')}`));
      }
      if (summary.max_angular_velocity) {
        gridTop.appendChild(statCard('Max Angular Velocity', fmt(summary.max_angular_velocity.value, 1, ' °/s'),
          `at t=${fmt(summary.max_angular_velocity.timestamp, 1, 's')}`));
      }
      if (events && events.apogee) {
        gridTop.appendChild(statCard('Apogee Altitude', fmt(events.apogee.altitude, 1, ' m'),
          `at t=${fmt(events.apogee.timestamp, 1, 's')}`));
      }
      if (events && events.liftoff) {
        gridTop.appendChild(statCard('Liftoff', fmt(events.liftoff.timestamp, 1, ' s')));
      }
      if (events && events.landing) {
        gridTop.appendChild(statCard('Landing', fmt(events.landing.timestamp, 1, ' s')));
      }
    }
    const lastReadingSub = `at t=${fmt(last.TIMESTAMP, 1, 's')} (final reading)`;
    gridTop.appendChild(statCard('Battery Voltage', fmt(last.VOLTAGE, 1, ' V'), lastReadingSub));
    gridBottom.appendChild(statCard('Battery Current', fmt(last.CURRENT, 1, ' A'), lastReadingSub));
    gridBottom.appendChild(statCard('GPS Satellites', last.GPS_SATS ?? '—', lastReadingSub));
    gridBottom.appendChild(statCard('GPS Position',
      `${fmt(last.GPS_LATITUDE, 1)}, ${fmt(last.GPS_LONGITUDE, 1)}`, lastReadingSub));

    // ---- Accelerometer ---------------------------------------------------
    buildChart('accelChart', 'controls-accel', t, [
      line('Accel X', data.map(r => r.ACCEL_X), '#ec4899'),
      line('Accel Y', data.map(r => r.ACCEL_Y), '#fb923c'),
      line('Accel Z', data.map(r => r.ACCEL_Z), '#a78bfa'),
      line('Magnitude', data.map(r => r.ACCEL_MAGNITUDE), '#d946ef', { borderWidth: 2 })
    ], 'm/s²', annotations);

    // ---- Gyroscope ---------------------------------------------------------
    buildChart('gyroChart', 'controls-gyro', t, [
      line('Gyro X', data.map(r => r.GYRO_X), '#ec4899'),
      line('Gyro Y', data.map(r => r.GYRO_Y), '#fb923c'),
      line('Gyro Z', data.map(r => r.GYRO_Z), '#a78bfa')
    ], 'deg/s', annotations);

    // ---- Barometric pressure ---------------------------------------------
    buildChart('pressureChart', 'controls-pressure', t, [
      line('Pressure', data.map(r => r.PRESSURE), '#a78bfa')
    ], 'Pa', annotations);

    // ---- Altitude: GPS reading vs. barometric estimate --------------------
    buildChart('altitudeChart', 'controls-altitude', t, [
      line('GPS Altitude', data.map(r => r.GPS_ALTITUDE), '#a78bfa'),
      line('Estimated Barometric', data.map(r => r.ALTITUDE_BARO), '#fb923c')
    ], 'm', annotations);

    // ---- Power: voltage (left axis) vs current (right axis) --------------
    buildChart('powerChart', 'controls-power', t, [
      line('Voltage', data.map(r => r.VOLTAGE), '#ec4899', { yAxisID: 'y' }),
      line('Current', data.map(r => r.CURRENT), '#a78bfa', { yAxisID: 'y1' })
    ], 'Voltage (V)', annotations, {
      y1: {
        position: 'right',
        title: { display: true, text: 'Current (A)', color: '#000' },
        ticks: { color: '#000' },
        grid: { display: false }
      }
    });

    // ---- GPS position: latitude (left axis) vs longitude (right axis) ----
    buildChart('gpsChart', 'controls-gps', t, [
      line('Latitude', data.map(r => r.GPS_LATITUDE), '#ec4899', { yAxisID: 'y' }),
      line('Longitude', data.map(r => r.GPS_LONGITUDE), '#a78bfa', { yAxisID: 'y1' })
    ], 'Latitude (°)', annotations, {
      y1: {
        position: 'right',
        title: { display: true, text: 'Longitude (°)', color: '#000' },
        ticks: { color: '#000' },
        grid: { display: false }
      }
    });
  })
  .catch(err => {
    document.getElementById('status').textContent = "Couldn't load telemetry: " + err;
  });
