#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight progress printing (guarantee periodic output)."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class ProgressPrinter:
    label: str
    min_interval_seconds: float = 20.0

    def __post_init__(self) -> None:
        self._t0 = time.time()
        self._last = self._t0
        self._ticks = 0

    def tick(self, detail: str = "") -> None:
        self._ticks += 1
        now = time.time()
        if now - self._last >= self.min_interval_seconds:
            elapsed = now - self._t0
            msg = f"[{self.label}] t={elapsed:.1f}s ticks={self._ticks}"
            if detail:
                msg += f" | {detail}"
            print(msg, flush=True)
            self._last = now

