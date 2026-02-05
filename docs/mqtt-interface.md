# HEMS MQTT Interface Contract

**Project:** OG&E Home Energy Management System (HEMS)  
**Purpose:** Define MQTT topics and JSON payloads used between Hub, devices, bridge, and UI.  
**Status:** Draft (v0.1)  
**Last Updated:** 2026-02-04

---

## 1. Broker & Transport Assumptions

- **Broker:** Mosquitto
- **Port:** 1883 (default)
- **QoS:** 0 (default) unless specified otherwise
- **Retained Messages:** OFF by default unless specified otherwise
- **Payload Encoding:** UTF-8 JSON only

---

## 2. Naming Conventions

### 2.1 Topic Prefix
All topics are under:

- `hems/`

### 2.2 Device IDs
- `device_id` is a short string (example: `plug1`, `plug2`, `main`, `solar1`)
- Use lowercase + numbers, no spaces

---

## 3. Topic Schema Overview

### 3.1 Telemetry (Data)
- Per-device power:
  - `hems/devices/<device_id>/power_w`
- Total power:
  - `hems/total/power_w`

### 3.2 Commands (UI → Hub)
- Device control:
  - `hems/ui/command/<device_id>`

### 3.3 Status / Health (Recommended)
- Hub heartbeat:
  - `hems/hub/heartbeat`
- Bridge heartbeat:
  - `hems/bridge/heartbeat`
- Optional per-device status:
  - `hems/devices/<device_id>/status`

---

## 4. Payload Definitions (JSON)

> All payloads MUST be valid JSON. Unknown fields should be ignored; missing required fields should be handled safely.

### 4.1 Common Fields

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `ts` | int | yes | Unix timestamp in milliseconds |
| `source` | string | no | Who sent it (`hub`, `ui`, `bridge`, `device`) |

---

## 5. Telemetry Topics

### 5.1 `hems/devices/<device_id>/power_w`

**Direction:** Hub → MQTT → Bridge/UI  
**Meaning:** Instantaneous device power in watts.

**Payload:**
```json
{
  "device_id": "plug1",
  "power_w": 147.2,
  "is_on": true,
  "ts": 1738701234567
}
