"""Blocking facade over the broker's asyncio SDK.

The process holds one broker session. open() runs the SDK on its own event-loop thread ("broker-io");
every method below, called from any thread, submits a coroutine to that loop and blocks until it finishes.

SDK behaviour: a request (positions, orders, fills, P&L) returns when the server sends its final message
for that request; the SDK sets no timeout of its own.
"""
import asyncio
import threading

from utils.logger import log
from vendor.tradesdk import Session as SdkSession


class Broker:
    def __init__(self):
        self._sdk = SdkSession()
        self._loop = None

    def open(self, host, port):
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, name="broker-io", daemon=True).start()
        self._wait(self._sdk.open(host, port))
        self._sdk.on_resume(lambda: log.warning("broker session resumed; local fill cache cleared"))
        log.info("Broker session open | %s:%d", host, port)

    def connected(self):
        return self._sdk.is_open()

    def _wait(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    # --- reads ---------------------------------------------------------
    def net_value(self):
        return self._wait(self._sdk.account_value("net_value"))

    def quote(self, symbol):
        return self._wait(self._sdk.quote(symbol))

    def chain(self, symbol, expiry):
        return self._wait(self._sdk.option_chain(symbol, expiry))

    def fills_since(self, since_utc):
        """Server-side fills since a UTC time (kept across session resumes, unlike the local cache)."""
        return self._wait(self._sdk.fills(since=since_utc))

    def realized_pnl(self, day):
        return self._wait(self._sdk.realized_pnl(day))

    # --- orders --------------------------------------------------------
    def place_condor(self, legs, limit):
        return self._wait(self._sdk.submit_multileg(legs, limit))

    def place_leg(self, contract, side, qty, limit=None):
        return self._wait(self._sdk.submit(contract, side, qty, limit))


broker = Broker()
