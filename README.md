# Plotune Relay Extension

The **Plotune Relay Extension** acts as a transport-agnostic relay that proxies external data sources into **Plotune Core**.
It supports both **HTTP polling** and **WebSocket streaming** sources and exposes them to Plotune clients through a unified WebSocket interface.

---

## Features

* HTTP polling (`/signals`, `/data/{signal}`)
* WebSocket streaming (`/signals`, `/ws/{signal}`)
* Automatic signal discovery
* Multiple concurrent listeners
* Queue-based fan-out (asyncio)
* Transport-agnostic design
* Auto-reconnect for WebSocket sources
* Docker-ready and production-safe

---

## Supported Source Types

### HTTP Polling

* Fetches available signals from `/signals`
* Polls `/data/{signal_name}` at a configurable interval
* Suitable for REST-based or legacy systems

### WebSocket Streaming

* Fetches available signals from `/signals`
* Subscribes to `/ws/{signal_name}`
* Low-latency, push-based streaming

Both source types are normalized into the same internal payload format.

---

## Default Payload Format

```json
{
  "key": "temperature",
  "time": 1712345678.123,
  "value": 23.7
}
```

Custom JSON field mappings are supported via configuration.

---

## Architecture Overview

```
External Source
   │
   ├── HTTPPool        (HTTP polling)
   ├── SocketListener  (WebSocket streaming)
   │
   ▼
RelayAgent
   │
   ▼
Plotune Core (WebSocket)
```

* Each signal uses an asyncio queue
* Multiple clients can subscribe to the same signal
* Transport details are abstracted away from consumers

---

## API Endpoints

### Extension API

| Endpoint      | Method | Description                  |
| ------------- | ------ | ---------------------------- |
| `/help`       | GET    | Extension description        |
| `/form`       | GET    | Dynamic connection form      |
| `/form`       | POST   | Create new source connection |
| `/fetch-meta` | GET    | Fetch available signals      |
| `/ws/{signal}`| WS     | Stream signal values         |

---

## Configuration

### `plugin.json`

```json
{
  "connection": {
    "target": "127.0.0.1",
    "target_port": 8000
  },
  "configuration": {}
}
```

### Environment Variables

| Variable             | Description            | Default |
| -------------------- | ---------------------- | ------- |
| `USE_AVAILABLE_PORT` | Auto-select free port  | `true`  |
| `SERVER_PORT`        | Fixed port if disabled | `9000`  |
| `PYSTRAY_HEADLESS`   | Headless runtime mode  | `1`     |

---

## Running Locally

```bash
pip install -r requirements.txt
python main.py
```

---

## Running with Docker

```bash
docker build -t plotune-relay .
docker run -p 9000:9000 plotune-relay
```

---

## Logging

The extension uses Python’s built-in `logging` module.

```python
logging.basicConfig(level=logging.INFO)
```

Available levels:

* `INFO` – lifecycle events
* `DEBUG` – payloads and internal state
* `WARNING` – reconnects and recoverable errors

---

## Design Principles

* **Non-blocking async IO**
* **Explicit lifecycle control**
* **Minimal shared state**
* **Queue-based backpressure**
* **Fail-safe reconnect behavior**
