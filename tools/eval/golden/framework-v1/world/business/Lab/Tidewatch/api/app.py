"""Status API (local only)."""
from fastapi import FastAPI

from broker.client import broker

app = FastAPI()


@app.get("/status")
def status():
    return {"up": True, "broker": broker.connected()}
