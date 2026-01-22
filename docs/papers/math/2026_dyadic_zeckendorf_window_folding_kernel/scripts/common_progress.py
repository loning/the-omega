#!/usr/bin/env python3
"""Progress helpers for long-running scripts."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Progress:
    label: str
    every_seconds: float = 20.0
    _last: float = 0.0

    def tick(self, msg: str) -> None:
        now = time.time()
        if self._last == 0.0 or (now - self._last) >= self.every_seconds:
            self._last = now
            print(f"[{self.label}] {msg}", flush=True)

