# HEMS Software

Software stack for the OG&E Home Energy Management System (HEMS).

## Architecture
- Hub: Owns system state and control logic
- MQTT Broker: Message backbone
- UI Bridge: MQTT ↔ WebSocket translation
- Web UI: Browser-based client

## Structure
- hub/ – Hub service
- bridge/ – UI bridge service
- web/ – Browser-based UI
