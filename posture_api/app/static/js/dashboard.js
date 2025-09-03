//later change all uses of userId to currentuserId


// ---- Config & State ----
const qs = new URLSearchParams(location.search);
const userIdInput = document.getElementById("user-id");
const defaultUserId = Number(userIdInput?.value || 1);
let currentUserId = Number(qs.get("user_id")) || defaultUserId;
let lastNotificationTime = 0;

const connectionBanner = document.getElementById("connection-banner");

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const btnRecalibrate = document.getElementById("btn-recalibrate");
const btnReconnect = document.getElementById("btn-reconnect");
const btnReset = document.getElementById("btn-reset");
const btnExport = document.getElementById("btn-export");

// Track whether we’re actively processing incoming updates (Start/Stop)
let liveProcessing = true;

// Session timer
let sessionStart = new Date();




// ---- Socket.IO connection ----
let socket = null;

function connectSocket(userId) {
  if (socket) {
    try { socket.disconnect(); } catch (_) {}
    socket = null;
  }

  // If same origin as server, no URL needed; Socket.IO will use window.location origin
  socket = io({
    query: { user_id: userId }  // your server reads this to join the user_{id} room
    // If you ever host dashboard elsewhere, use: io("http://127.0.0.1:5000/", { query: { user_id: userId } })
  });

  socket.on("connect", async () => {
    console.log(`Connected as user_id=${userId} socket.id=${socket.id}`);
    

    try{
        const response = await fetch("/api/posture-buffer?user_id=" + userId);
        const buffered = await response.json();
        buffered.forEach(reading => {
          timelineChart.data.labels.push(new Date(reading.timestamp));
          timelineChart.data.datasets[0].data.push(reading.angle);
        });
      timelineChart.update();
    } catch (e) {
      console.error("Failed to fetch buffer", e);
  }
  });

  socket.on("disconnect", (reason) => {
    setBanner(`Disconnected: ${reason}`, "bad");
  });


  socket.on("posture_update", (payload) => {
    const angle = Math.round(payload.angle);
    document.getElementById("current-angle").textContent = angle + "°";

    updateGauge(angle);

    updateQuality(payload);

    const now = new Date();

    timelineChart.data.labels.push(now);
    timelineChart.data.datasets[0].data.push(angle);

    const cutoff = new Date(now - 30000);
    while (timelineChart.data.labels[0] < cutoff) {
      timelineChart.data.labels.shift();
      timelineChart.data.datasets[0].data.shift();
    }

    const currentMax = Math.max(...timelineChart.data.datasets[0].data, 90);
    timelineChart.options.scales.y.max = currentMax;

    timelineChart.update();

    if (payload.quality_score === 3) {
      sendPostureNotification("Posture Warning: Please adjust your posture.");
    }
    else if (payload.quality_score === 5) {
      sendPostureNotification("Posture Horrible: FIX NOW");
    }

  });


  socket.on("calibration_complete", () => {
    // Show quick visual feedback
    showToast("Calibration complete");
    // You might also want to reset sessionStart or show baseline somewhere
  });

  socket.on("notification_triggered", (msg) => {
    // Optional: simple UI popup; refine later
    alert(typeof msg === "string" ? msg : "Notification triggered");
  });

  socket.on("connection_status", (status) => {
    // status could be { online_users: [...], user_id: ... } depending on your server
    // Useful for debugging; not displayed by default
    // console.debug("connection_status", status);
  });
}

document.addEventListener("DOMContentLoaded", () => {


  connectSocket(currentUserId);
});

// ---- UI handlers ----
btnStart?.addEventListener("click", () => {
  fetch("/api/posture/toggle_tracking", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "start" })
  })
  .then(response => response.json())
  .then(data => {
    console.log("tracking started", data);
  });
});

btnStop?.addEventListener("click", () => {
  fetch("/api/posture/toggle_tracking", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "stop" })
  })
  .then(response => response.json())
  .then(data => {
    console.log("tracking stopped:", data);
  });
});

btnReset?.addEventListener("click", () => {
  fetch("/api/overview/reset?user_id=" + currentUserId, { method: "POST" })
    .then(response => response.json())
    .then(data => console.log("today reset:", data));
});

btnExport?.addEventListener("click", () => {
  window.location.href = `/api/export?user_id=${currentUserId}&format=csv`;
});

btnRecalibrate?.addEventListener("click", async () => {
  try {
    await fetch("/api/posture/recalibrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: currentUserId})
    });

  } catch (e) {
    console.log("Calibration request failed", "bad");
  }
});

btnReconnect?.addEventListener("click", () => {
  const nextId = Number(userIdInput.value || "1");
  if (!Number.isFinite(nextId) || nextId < 1) return;
  currentUserId = nextId;
  connectSocket(currentUserId);
});

// ---- Helpers ----
function sendPostureNotification(message) {
  const now = Date.now();
  
  Notification.requestPermission().then(permission => {
      if (permission === "granted" && now - lastNotificationTime > 5000) {
        new Notification(message);
        lastNotificationTime = now;
      }
    });
}

function setBanner(text, level) {
  connectionBanner.textContent = text;
  connectionBanner.style.background =
    level === "good" ? "var(--good)" :
    level === "bad"  ? "var(--bad)"  : "#1f242b";
  connectionBanner.style.color = level ? "#0b0d10" : "var(--muted)";
}

function updateQuality(data) {
    const indicator = document.getElementById("quality-indicator");
    const score = data.quality_score;

    if (score === 5){
      indicator.textContent = "Good";
      indicator.style.color = "green";
    } else if (score === 3) {
      indicator.textContent = "Warning";
      indicator.style.color = "orange";
    } else {
      indicator.textContent = "Bad";
      indicator.style.color = "red";
    }
}


function classifyAngle(angle) {
  if (typeof angle !== "number") return { label: "Unknown", level: "warn" };
  if (angle <= 15) return { label: "Good", level: "good" };
  if (angle <= 30) return { label: "Warning", level: "warn" };
  return { label: "Bad", level: "bad" };
}

function formatHMS(totalSec) {
  const h = Math.floor(totalSec / 3600).toString().padStart(2, "0");
  const m = Math.floor((totalSec % 3600) / 60).toString().padStart(2, "0");
  const s = Math.floor(totalSec % 60).toString().padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function updateTimer(){
    const now = new Date();
    const elapsed = Math.floor((now - sessionStart) / 1000);
    const hours = String(Math.floor(elapsed / 3600)).padStart(2,'0');
    const minutes = String(Math.floor((elapsed % 3600) / 60)).padStart(2,'0');
    const seconds = String(elapsed % 60).padStart(2,'0');
   document.getElementById("session-timer").textContent = `${hours}:${minutes}:${seconds}`;
}

async function fetchDailyData(userId) {
    try {
        const response = await fetch(`/api/overview?user_id=${userId}`);
        if (!response.ok) throw new Error("Failed to fetch daily data");

        const data = await response.json();

        if (data.timeline) {
            dailyChart.data.labels = data.timeline.map(entry => new Date(entry.timestamp));
            dailyChart.data.datasets[0].data = data.timeline.map(entry => entry.angle);
            dailyChart.update();

            document.getElementById("avg-angle").textContent = (data.avg_angle ? Number(data.avg_angle).toPrecision(3) + "°" : "0°");
            document.getElementById("count-good").textContent = data.quality_counts?.good ?? 0;
            document.getElementById("count-warning").textContent = data.quality_counts?.warning ?? 0;
            document.getElementById("count-bad").textContent = data.quality_counts?.bad ?? 0;
        }
        if (data.quality_counts) {
          pieChart.data.datasets[0].data = [
              data.quality_counts.good ?? 0,
              data.quality_counts.warning ?? 0,
              data.quality_counts.bad ?? 0
          ];
          pieChart.update();
        }
    } catch (error) {
        console.error("Error fetching daily data:", error);
    }
}


setInterval(updateTimer, 1000);
fetchDailyData(currentUserId);
setInterval(() => fetchDailyData(currentUserId), 60000);


const gaugeCtx = document.getElementById('angle-gauge').getContext('2d');
const gaugeChart = new Chart (gaugeCtx, {
    type: "doughnut",
    data: {
        labels: ['Tilt', 'Remaining'],
        datasets: [{
            data: [0, 90],
            backgroundColor: ['#4caf50', '#FF6384'],
            hoverBackgroundColor: ['#4caf50', '#FF6384'],
            borderWidth: 1
        }]
    },
    options: {
        rotation: -90,
        circumference: 180,
        cutout: '70%',
        plugins: {
            tooltip: { enabled: false },
            legend: { display: false }
        },
    }
})

function updateGauge(angle) {
    const value = Math.min(angle, 90);
    gaugeChart.data.datasets[0].data[0] = value;
    gaugeChart.data.datasets[0].data[1] = 90 - value;
    gaugeChart.update();
}

const timelineCtx = document.getElementById('live-timeline').getContext('2d');
const timelineChart = new Chart(timelineCtx, {
    type: 'line',
    data: {
        labels: [], // Time labels
        datasets: [{
            label: 'Angle',
            data: [], // Angle data points
            borderColor: '#36A2EB',
            tension: 0.2
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: { type: 'time', time: { unit: 'minute' }},
            y: { min: 0}
        }
    }
});

const dailyCtx = document.getElementById('daily-timeline').getContext('2d');
const dailyChart = new Chart(dailyCtx, {
    type: 'line',
    data: {
        labels: [], // Time labels
        datasets: [{
            label: 'Angle',
            data: [], // Angle data points
            borderColor: '#36A2EB',
            tension: 0.2
        }]
    },
    options: {
        animation: false,
        scales: {
            x: { type: 'time', time: { unit: 'minute' }},
            y: { min: 0, max: 90 }
        }
    }
});

const pieCtx = document.getElementById('daily-pie').getContext('2d');
const pieChart = new Chart(pieCtx, {
    type: 'pie',
    data: {
        labels: ['Good', 'Warning', 'Bad'],
        datasets: [{
            data: [0, 0, 0],
            backgroundColor: ['#4caf50', '#FF9800', '#F44336'],
            hoverOffset: 15
        }]
    },
    options: {
        plugins: {
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const dataset = context.dataset;
                        const total = dataset.data.reduce((a, b) => a + b, 0);
                        const value = dataset.data[context.dataIndex];
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${context.label}: ${percentage}%`;
                    }
                }
            },
            legend: {
                display: true
            }
        }
    }
});