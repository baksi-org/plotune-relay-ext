import time
import random
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

# -------------------------
# Defined signals
# -------------------------
SIGNALS = {
    "temperature": lambda: random.uniform(20.0, 30.0),
    "humidity": lambda: random.uniform(40.0, 60.0),
    "voltage": lambda: random.uniform(3.0, 3.3),
}

# -------------------------
# Discovery
# -------------------------
@app.get("/signals")
def list_signals():
    return {
        "signals": list(SIGNALS.keys())
    }

# -------------------------
# Signal endpoint (authoritative - HTTP)
# -------------------------
@app.get("/data/{signal_name}")
def get_signal(signal_name: str):
    if signal_name not in SIGNALS:
        raise HTTPException(
            status_code=404,
            detail=f"Signal '{signal_name}' not found"
        )

    return {
        "key": signal_name,
        "value": SIGNALS[signal_name](),
        "time": time.time()
    }

# -------------------------
# Signal endpoint (WebSocket)
# -------------------------
@app.websocket("/ws/{signal_name}")
async def websocket_signal(websocket: WebSocket, signal_name: str):
    await websocket.accept()

    if signal_name not in SIGNALS:
        await websocket.close(code=1008)
        return

    try:
        while True:
            payload = {
                "key": signal_name,
                "value": SIGNALS[signal_name](),
                "time": time.time()
            }

            await websocket.send_json(payload)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=9001)
