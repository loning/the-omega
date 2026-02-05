#!/usr/bin/env python3
"""
Progress printing helpers.
Requirement: long-running scripts should print progress at least every ~20s.
"""

from __future__ import annotations

import time


class Progress:
    def __init__(self, every_seconds: float = 15.0) -> None:
        self.every_seconds = float(every_seconds)
        self._t0 = time.time()
        self._t_last = self._t0
        self._last_msg = ""

    def maybe(self, msg: str) -> None:
        now = time.time()
        if (now - self._t_last) >= self.every_seconds:
            dt = now - self._t0
            print(f"[progress] t={dt:.1f}s {msg}", flush=True)
            self._t_last = now
            self._last_msg = msg

    def done(self, msg: str = "done") -> None:
        now = time.time()
        dt = now - self._t0
        print(f"[progress] t={dt:.1f}s {msg}", flush=True)

