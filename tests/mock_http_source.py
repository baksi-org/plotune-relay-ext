import time
import random
from fastapi import FastAPI, HTTPException
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
# Signal endpoint (authoritative)
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
# Run
# -------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
