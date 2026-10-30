"""Tidewatch cron jobs. Triggers are ET; APScheduler runs each job on a worker thread."""
import threading
from collections import defaultdict
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from broker.client import broker
from config import Config
from data.db import Session
from data.economic_calendar import macro_event
from data.models import Condor, DaySummary, PremarketValue
from execution.orders import flatten_condor, open_condor
from notify.discord import send_discord
from strategy.condors import open_slots, pick_condors
from utils.logger import log

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
SCHEDULE = [("premarket", 9, 20), ("entry_am", 10, 5), ("entry_pm", 13, 0),   # (job id, hour, minute) ET
            ("flatten", 15, 45), ("wrapup", 16, 10)]

_recon_lock = threading.Lock()   # one fills reconciliation against the broker at a time


def et_today():
    return datetime.now(ET).date()


def build_scheduler():
    sched = BackgroundScheduler(timezone=Config.TZ)
    run = {"premarket": _premarket, "entry_am": _entry, "entry_pm": _entry,
           "flatten": _run_flatten, "wrapup": _wrapup}
    for job_id, hh, mm in SCHEDULE:
        sched.add_job(run[job_id], CronTrigger(day_of_week="mon-fri", hour=hh, minute=mm, timezone=Config.TZ),
                      id=job_id, args=[job_id] if job_id.startswith("entry") else [])
    sched.start()
    log.info("[Cron] ET schedule: %s", ", ".join(f"{j} {h:02d}:{m:02d}" for j, h, m in SCHEDULE))
    return len(SCHEDULE)


# --------------------------------------------------------------------------- morning

def _premarket():
    event = macro_event(et_today())
    if event:
        log.info("[premarket] BLACKOUT %s: no entries today", event)
        send_discord(f"【TW】今天是 {event}，不入场")
        return
    with Session() as s:
        nv = broker.net_value()
        s.add(PremarketValue(day=et_today(), net_value=nv))
        s.commit()
    log.info("[premarket] calendar ok (not FOMC/CPI/NFP), net_value=$%s", f"{nv:,.2f}")


def _entry(window):
    if macro_event(et_today()):
        return
    vix1d = broker.quote("VIX1D").last
    if vix1d > Config.VIX1D_CAP:
        log.info("[%s] HOLD: VIX1D %.1f above cap %.1f", window, vix1d, Config.VIX1D_CAP)
        return
    with Session() as s:
        slots = open_slots(s, window)
        log.info("[%s] VIX1D %.1f ok, open slots %s", window, vix1d,
                 " ".join(f"{k}={v}" for k, v in slots.items()))
        risk = Config.RISK_BUDGET * Config.RISK_PER_ENTRY          # $1,000 of max loss per entry
        n = 0
        for cand in pick_condors(Config.UNIVERSE, slots):
            open_condor(s, cand, max(1, int(risk // cand.max_loss)))
            n += 1
        if not n:
            log.info("[%s] no condor meets the credit floor", window)


# --------------------------------------------------------------------------- close

def _reconcile_fills(session):
    """Fetch today's fills from the broker and close out condors whose profit-target order filled.

    The local fill cache is lost when the broker session resumes, so flatten and wrapup reconcile
    from the server-side fill list instead (added 2026-10-08).
    """
    with _recon_lock:
        since = datetime.combine(et_today(), time(0, 0), tzinfo=ET).astimezone(UTC)
        by_order = defaultdict(list)
        for f in broker.fills_since(since):
            by_order[f.order_id].append(f)
        done = []
        for c in session.query(Condor).filter(Condor.expiry == et_today(), Condor.status == "open"):
            pt = by_order.get(c.pt_order_id)
            if pt:
                c.close(debit=sum(f.price * f.qty for f in pt) / sum(f.qty for f in pt), why="profit_target")
                done.append(c)
        session.commit()
        return done


def _run_flatten():
    """15:45 ET: buy back every XLK/XLF condor expiring today that is still open, then post the FLAT report."""
    with Session() as s:
        try:
            pt_done = _reconcile_fills(s)
            todays = (s.query(Condor).filter(Condor.expiry == et_today())
                      .filter(Condor.symbol.in_(Config.FLATTEN_SYMBOLS)).all())
            if not todays:
                log.info("[flatten] nothing to flatten: no XLK/XLF condors expiring today")
                return
            flat, failed = [], []
            for c in todays:
                if c.status != "open":
                    continue
                try:
                    c.close(debit=flatten_condor(c), why="flatten")
                    flat.append(c)
                except Exception as exc:
                    log.error("[flatten] #%d close rejected by broker: %s", c.id, exc)
                    failed.append(c)
            s.commit()
            log.info("[flatten] %d ETF condor(s): %d hit PT, %d flattened, %d failed",
                     len(todays), len(pt_done), len(flat), len(failed))
            msg = [f"【TW】FLAT 报告 15:45 ET：{len(todays)} 组 ETF 铁鹰"]
            msg += [f"  ❗没平掉 #{c.id} {c.symbol}：去券商手动平" for c in failed]
            msg += [f"  止盈已平 #{c.id} {c.symbol} {c.pnl:+.2f}" for c in pt_done]
            msg += [f"  已平 #{c.id} {c.symbol} {c.pnl:+.2f}" for c in flat]
            send_discord("\n".join(msg))
        except Exception as exc:
            s.rollback()
            log.error("[flatten] crashed: %s", exc)
            send_discord(f"【TW】flatten 出错：{exc}，去券商看今天的 XLK/XLF 仓位")


def _wrapup():
    """16:10 ET: close the day (XSP is cash-settled), store the summary, post the 日终复盘."""
    with Session() as s:
        try:
            _reconcile_fills(s)
            todays = s.query(Condor).filter(Condor.expiry == et_today()).all()
            for c in todays:
                if c.status == "open":
                    c.expire()
            realized = broker.realized_pnl(et_today())
            s.add(DaySummary(day=et_today(), risk_budget=Config.RISK_BUDGET, realized_pnl=realized,
                             net_value=broker.net_value()))
            s.commit()
            log.info("[wrapup] day done: %d condor(s), realized=$%+.2f, budget=$%s", len(todays), realized,
                     f"{Config.RISK_BUDGET:,.0f}")
            msg = [f"【TW】日终复盘 {et_today()}：{len(todays)} 组"]
            msg += [f"  #{c.id} {c.symbol} x{c.qty} {c.close_reason} {c.pnl:+.2f}" for c in todays]
            msg.append(f"  券商已实现 {realized:+.2f}")
            send_discord("\n".join(msg))
        except Exception as exc:
            s.rollback()
            log.error("[wrapup] crashed: %s", exc)
            send_discord(f"【TW】wrapup 出错：{exc}")
