# -*- coding: utf-8 -*-
"""
Minimal progress helpers for long-running deterministic scripts.

Design goals:
  - Pure standard library.
  - Low overhead (checks time only).
  - Print at most once per interval (default: 60s) to avoid log spam.
  - English-only output (repo convention).
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProgressEvery:
    """
    Print a progress heartbeat at most once every `interval_s` seconds.
    """

    label: str
    total: Optional[int] = None
    interval_s: float = 60.0

    _t0: float = 0.0
    _last: float = 0.0

    def start(self) -> None:
        now = time.time()
        self._t0 = now
        self._last = now

    def maybe(self, i: int, extra: str = "") -> None:
        """
        Maybe print a heartbeat for the i-th unit of work (0-based or 1-based are both fine).
        """
        now = time.time()
        if (now - self._last) < self.interval_s:
            return
        self._last = now
        elapsed = int(now - self._t0) if self._t0 else 0
        if self.total is None or self.total <= 0:
            msg = f"[progress] {self.label}: i={i} elapsed={elapsed}s"
        else:
            pct = 100.0 * float(i) / float(self.total)
            msg = f"[progress] {self.label}: {i}/{self.total} ({pct:.1f}%) elapsed={elapsed}s"
        if extra:
            msg += f" {extra}"
        print(msg, flush=True)

    def done(self, extra: str = "") -> None:
        now = time.time()
        elapsed = int(now - self._t0) if self._t0 else 0
        msg = f"[progress] {self.label}: done elapsed={elapsed}s"
        if extra:
            msg += f" {extra}"
        print(msg, flush=True)


def heartbeat_wait(proc, label: str, interval_s: float = 60.0, poll_s: float = 1.0) -> int:
    """
    Wait for a subprocess.Popen-like object, printing a heartbeat every interval_s.
    The subprocess stdout/stderr should be inherited by the parent for live logs.
    Returns the process return code.
    """
    t0 = time.time()
    last = t0
    while True:
        rc = proc.poll()
        if rc is not None:
            return int(rc)
        now = time.time()
        if (now - last) >= interval_s:
            last = now
            elapsed = int(now - t0)
            print(f"[run_all] {label} still running ({elapsed}s elapsed)", flush=True)
            sys.stdout.flush()
        time.sleep(poll_s)


