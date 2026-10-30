"""Tidewatch: open the broker session, start the cron jobs, serve the status API."""
import uvicorn

from broker.client import broker
from config import Config
from scheduler.jobs import build_scheduler
from utils.logger import log


def run():
    log.info("Tidewatch 启动 (%s)", "live" if Config.LIVE else "paper")
    log.info("标的池: %s", ", ".join(Config.UNIVERSE))
    broker.open(*Config.BROKER_ADDR)
    n = build_scheduler()
    log.info("调度就绪，共 %d 个任务", n)
    log.info("status API on 127.0.0.1:%d", Config.STATUS_PORT)
    uvicorn.run("api.app:app", host="127.0.0.1", port=Config.STATUS_PORT, access_log=False)


if __name__ == "__main__":
    run()
