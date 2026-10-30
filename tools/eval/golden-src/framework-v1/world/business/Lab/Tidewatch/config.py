"""Tidewatch settings."""
import os


class Config:
    TZ = "America/New_York"                # cron triggers are ET
    UNIVERSE = ["XSP", "XLK", "XLF"]
    FLATTEN_SYMBOLS = ["XLK", "XLF"]       # American-style ETF options: flattened at 15:45 ET
    LIVE = os.getenv("TW_LIVE", "1") == "1"

    BROKER_ADDR = ("127.0.0.1", int(os.getenv("TW_BROKER_PORT", "9300")))
    DB_PATH = "data/tw.sqlite"
    DISCORD_CHANNEL_ID = os.getenv("TW_DISCORD_CHANNEL", "")

    RISK_BUDGET = 20000.0                  # fixed sizing base (risk-budget rework, 2026-10-06)
    RISK_PER_ENTRY = 0.05                  # $1,000 of max loss per condor entry
    PROFIT_TARGET = 0.25                   # rest a buy-back at 25% of the credit
    VIX1D_CAP = 22.0                       # entries hold while VIX1D is above this
    STATUS_PORT = 8765
