// ====== Config ======
const WS_URL = "ws://localhost:8765";     // Your Python UI Bridge WebSocket endpoint
const STALE_MS = 5000;                   // UI shows "STALE" if no updates in this time

// ====== DOM ======
const statusBadge = document.getElementById("statusBadge");
const btnReconnect = document.getElementById("btnReconnect");
const btnClearLog = document.getElementById("btnClearLog");
const btnDemo = document.getElementById("btnDemo");

const totalPowerEl = document.getElementById("totalPower");
const plug1PowerEl = document.getElementById("plug1Power");
const lastUpdateEl = document.getElementById("lastUpdate");
const logBox = document.getElementById("logBox");

const btnOn = document.getElementById("btnOn");
const btnOff = document.getElementById("btnOff");

// ====== State ======
let ws = null;
let lastDataTime = 0;
let demoTimer = null;

function log(line) {
  const ts = new Date().toLocaleTimeString();
  const msg = `[${ts}] ${line}\n`;
  logBox.textContent = (logBox.textContent === "(waiting…)" ? "" : logBox.textContent) + msg;
  logBox.scrollTop = logBox.scrollHeight;
}

function setBadge(mode) {
  statusBadge.classList.remove("badge-connected", "badge-disconnected", "badge-stale");
  if (mode === "connected") {
    statusBadge.textContent = "CONNECTED";
    statusBadge.classList.add("badge-connected");
  } else if (mode === "stale") {
    statusBadge.textContent = "STALE";
    statusBadge.classList.add("badge-stale");
  } else {
    statusBadge.textContent = "DISCONNECTED";
    statusBadge.classList.add("badge-disconnected");
  }
}

function setPowerText(el, value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    el.textContent = "-- W";
    return;
  }
  el.textContent = `${Number(value).toFixed(1)} W`;
}

function touchLastUpdate() {
  lastDataTime = Date.now();
  lastUpdateEl.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
}

// ====== Incoming message handling ======
// Supports multiple message shapes so your bridge can evolve:
//
// Shape A (recommended bridge -> UI):
//   { type: "total", power_w: 222.3, timestamp: 123 }
//   { type: "device", id: "plug1", power_w: 210.1, timestamp: 123 }
//
// Shape B (MQTT-forward style):
//   { topic: "hems/total/power_w", payload: { power_w: 222.3, timestamp: 123 } }
//
// Shape C (string payload):
//   { topic: "...", payload: "{\"power_w\": 222.3, ...}" }
function handleMessage(obj) {
  // Normalize to (topic, payloadObj) OR (type-based)
  if (obj.type === "total") {
    setPowerText(totalPowerEl, obj.power_w);
    touchLastUpdate();
    return;
  }

  if (obj.type === "device" && obj.id === "plug1") {
    setPowerText(plug1PowerEl, obj.power_w);
    touchLastUpdate();
    return;
  }

  // Topic-based
  if (obj.topic) {
    let payload = obj.payload;

    // If payload is a JSON string, parse it
    if (typeof payload === "string") {
      try { payload = JSON.parse(payload); } catch { /* ignore */ }
    }

    if (obj.topic === "hems/total/power_w") {
      setPowerText(totalPowerEl, payload?.power_w);
      touchLastUpdate();
      return;
    }

    if (obj.topic === "hems/devices/plug1/power_w") {
      setPowerText(plug1PowerEl, payload?.power_w);
      touchLastUpdate();
      return;
    }
  }
}

// ====== WebSocket connection ======
function connectWebSocket() {
  stopDemoMode();

  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    setBadge("disconnected");
    log(`WebSocket init error: ${e}`);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    setBadge("connected");
    log(`Connected to bridge: ${WS_URL}`);
  };

  ws.onclose = () => {
    setBadge("disconnected");
    log("Bridge disconnected. Retrying...");
    scheduleReconnect();
  };

  ws.onerror = () => {
    // onerror often fires before onclose; keep logging simple
    log("WebSocket error (bridge may be offline).");
  };

  ws.onmessage = (event) => {
    const raw = String(event.data);
    log(`IN: ${raw}`);

    try {
      const obj = JSON.parse(raw);
      handleMessage(obj);
    } catch {
      // If it's not JSON, ignore (but keep log)
    }
  };
}

let reconnectTimer = null;
function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, 2000);
}

// ====== Outgoing commands (UI -> Bridge) ======
function sendCommand(deviceId, command) {
  const msg = {
    type: "command",
    id: deviceId,
    command: command
  };

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log(`OUT (not sent, no bridge): ${JSON.stringify(msg)}`);
    return;
  }

  const raw = JSON.stringify(msg);
  ws.send(raw);
  log(`OUT: ${raw}`);
}

btnOn.onclick = () => sendCommand("plug1", "ON");
btnOff.onclick = () => sendCommand("plug1", "OFF");

btnClearLog.onclick = () => {
  logBox.textContent = "(waiting…)";
};

btnReconnect.onclick = () => {
  log("Manual reconnect requested.");
  if (ws) {
    try { ws.close(); } catch {}
  }
  connectWebSocket();
};

// ====== Stale indicator ======
setInterval(() => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    const age = Date.now() - lastDataTime;
    if (lastDataTime !== 0 && age > STALE_MS) {
      setBadge("stale");
    } else if (statusBadge.textContent !== "CONNECTED") {
      setBadge("connected");
    }
  }
}, 500);

// ====== Demo mode (no bridge required) ======
function startDemoMode() {
  stopDemoMode();
  log("Demo mode started (simulated data).");

  let t = 0;
  demoTimer = setInterval(() => {
    t += 1;
    const total = 700 + 100 * Math.sin(t / 5) + (Math.random() * 30);
    const plug1 = 220 + 30 * Math.sin(t / 3) + (Math.random() * 10);

    // Simulate incoming bridge messages using supported shapes:
    handleMessage({ type: "total", power_w: total, timestamp: Date.now() / 1000 });
    handleMessage({ type: "device", id: "plug1", power_w: plug1, timestamp: Date.now() / 1000 });

    setBadge("connected");
    log(`IN (demo): total=${total.toFixed(1)} plug1=${plug1.toFixed(1)}`);
  }, 2000);
}

function stopDemoMode() {
  if (demoTimer) {
    clearInterval(demoTimer);
    demoTimer = null;
    log("Demo mode stopped.");
  }
}

btnDemo.onclick = () => {
  if (demoTimer) stopDemoMode();
  else startDemoMode();
};

// ====== Start ======
setBadge("disconnected");
connectWebSocket();
