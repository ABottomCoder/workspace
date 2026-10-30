"""Discord notifications (took over from the email alerts on 2026-09-30)."""
import json
import os
import urllib.request

from config import Config
from utils.logger import log

API = "https://discord.com/api/v10"


def send_discord(text: str) -> bool:
    """Post one message to the Tidewatch channel. Never raises: a lost notification
    must not break a trading job."""
    token = os.getenv("TW_DISCORD_TOKEN")
    if not token or not Config.DISCORD_CHANNEL_ID:
        log.warning("[notify] Discord not set up, dropped: %s", text[:80])
        return False
    try:
        body = json.dumps({"content": text[:1990]}).encode()
        req = urllib.request.Request(f"{API}/channels/{Config.DISCORD_CHANNEL_ID}/messages", data=body,
                                     method="POST", headers={"Authorization": f"Bot {token}",
                                                             "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception as exc:
        log.warning("[notify] Discord post failed: %s", exc)
        return False
