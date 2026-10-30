"""Open and flatten iron condors."""
from broker.client import broker
from config import Config
from data.models import Condor
from notify.discord import send_discord
from utils.logger import log


def open_condor(session, cand, qty):
    """Sell all four legs as one order, then rest a profit-target buy-back at the broker."""
    fill = broker.place_condor(cand.legs("SELL"), cand.credit)
    c = Condor(symbol=cand.symbol, expiry=cand.expiry, qty=qty, strikes=cand.strikes, credit=fill.avg_price)
    session.add(c)
    session.flush()
    pt = broker.place_condor(cand.legs("BUY"), round(fill.avg_price * Config.PROFIT_TARGET, 2))
    c.pt_order_id = pt.order_id
    session.commit()
    ps, pl, cs, cl = cand.strikes
    log.info("[fill] condor #%d %s P%s/%s C%s/%s x%d credit $%.2f, PT order #%d @ $%.2f",
             c.id, c.symbol, ps, pl, cs, cl, qty, fill.avg_price, pt.order_id, pt.limit)
    send_discord(f"【TW】入场 #{c.id} {c.symbol} 铁鹰 P{ps}/{pl} C{cs}/{cl} x{qty}，"
                 f"收 ${fill.avg_price:.2f}，止盈单 @ ${pt.limit:.2f}")
    return c


def flatten_condor(c):
    """Buy back both short legs and sell both wings at market; returns the net debit per condor."""
    debit = 0.0
    for leg in c.legs():
        f = broker.place_leg(leg.contract, "BUY" if leg.short else "SELL", c.qty)
        debit += f.avg_price if leg.short else -f.avg_price
    return debit
