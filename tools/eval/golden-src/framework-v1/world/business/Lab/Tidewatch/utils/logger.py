"""Tidewatch log: one file per local (PT) day, plus the console."""
import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

log = logging.getLogger("tw")
log.setLevel(logging.INFO)

for h in (logging.FileHandler(os.path.join(LOG_DIR, f"tw_{datetime.now():%Y-%m-%d}.log"), encoding="utf-8"),
          logging.StreamHandler()):
    h.setFormatter(_fmt)
    log.addHandler(h)
