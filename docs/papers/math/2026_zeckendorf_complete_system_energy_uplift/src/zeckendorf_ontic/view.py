#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human-facing view helpers (not part of Layer-1 API)."""

from __future__ import annotations

from .ontic_system import OnticZeckendorfSystem

__all__ = ["OnticZeckendorfView"]


class OnticZeckendorfView:
    def __init__(self, system: OnticZeckendorfSystem) -> None:
        self._sys = system

    def format_bits(self, x: int, width: int) -> str:
        xi = int(x)
        w = int(width)
        return "".join("1" if (xi >> i) & 1 else "0" for i in range(w))

    def macro_word(self, macro_word: int) -> str:
        return self.format_bits(int(macro_word), self._sys.window_length)

    def tail_word(self, tail_word: int) -> str:
        return self.format_bits(int(tail_word), self._sys.tail_length())

