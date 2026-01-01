# -*- coding: utf-8 -*-
"""
Small time-based progress helpers (standard library only).

Goal: keep long-running scripts from going silent in terminals by printing
at least once per configured interval.
"""

from __future__ import annotations

import time


class Heartbeat:
    """
    Print a heartbeat message at most once per interval.
    """

    def __init__(self, *, every_s: float = 60.0, prefix: str = "[progress]") -> None:
        self.every_s = float(every_s)
        self.prefix = str(prefix)
        now = time.monotonic()
        self.t0 = now
        self.last = now

    def force(self, msg: str) -> None:
        """
        Print immediately and reset the interval timer.
        """
        now = time.monotonic()
        elapsed = now - self.t0
        print(f"{self.prefix} +{elapsed:.0f}s {msg}", flush=True)
        self.last = now

    def maybe(self, msg: str) -> None:
        """
        Print only if the interval has elapsed.
        """
        if self.every_s <= 0:
            return
        now = time.monotonic()
        if (now - self.last) >= self.every_s:
            elapsed = now - self.t0
            print(f"{self.prefix} +{elapsed:.0f}s {msg}", flush=True)
            self.last = now


