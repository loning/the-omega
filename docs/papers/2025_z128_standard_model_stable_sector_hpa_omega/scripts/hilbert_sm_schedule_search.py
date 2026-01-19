# -*- coding: utf-8 -*-
"""
Generate candidate m-schedules for experimental search.

We treat m-schedule as a design variable (not a fixed demo input).
This module provides deterministic sampling utilities driven by a PRNG seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ScheduleStats:
    n_changed: int
    n_switches: int
    max_m: int


def schedule_stats(m_by_k: Dict[int, int], k_min: int = 0, k_max: int = 63) -> ScheduleStats:
    seq = [int(m_by_k.get(int(k), 6)) for k in range(int(k_min), int(k_max) + 1)]
    n_changed = sum(1 for m in seq if m != 6)
    n_switches = sum(1 for a, b in zip(seq[:-1], seq[1:]) if a != b)
    return ScheduleStats(n_changed=int(n_changed), n_switches=int(n_switches), max_m=int(max(seq) if seq else 6))


def demo_fixed_schedule() -> Dict[int, int]:
    """
    Legacy demo schedule (kept as a baseline).
    """
    m_by_k: Dict[int, int] = {}
    for k in range(18, 53):
        if 18 <= k <= 19:
            m_by_k[k] = 8
        elif 20 <= k <= 22:
            m_by_k[k] = 10
        elif 23 <= k <= 26:
            m_by_k[k] = 8
        else:
            m_by_k[k] = 6
    return m_by_k


def sample_hierarchical_schedule(rng, *, k_lo: int = 0, k_hi: int = 63) -> Dict[int, int]:
    """
    Sample an m-schedule with a simple hierarchy:
      - baseline m=6 everywhere
      - choose 0..2 uplift blocks to m=8 (contiguous)
      - within each 8-block optionally choose a nested 10-block (contiguous)

    This deliberately avoids extremely fragmented schedules which tend to be infeasible under strict wiring.
    """
    k_lo = int(k_lo)
    k_hi = int(k_hi)
    if k_lo < 0 or k_hi > 63 or k_lo > k_hi:
        raise ValueError("Require 0<=k_lo<=k_hi<=63.")

    m_by_k: Dict[int, int] = {}

    n8 = int(rng.randrange(0, 3))  # 0..2 blocks
    blocks8: List[Tuple[int, int]] = []
    for _ in range(n8):
        length = int(rng.randrange(2, min(12, k_hi - k_lo + 1) + 1))
        start = int(rng.randrange(k_lo, k_hi - length + 2))
        end = start + length - 1
        blocks8.append((start, end))
    # merge overlaps deterministically
    blocks8.sort()
    merged: List[Tuple[int, int]] = []
    for a, b in blocks8:
        if not merged or a > merged[-1][1] + 1:
            merged.append((a, b))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
    blocks8 = merged[:2]

    for a, b in blocks8:
        for k in range(a, b + 1):
            m_by_k[int(k)] = 8
        # nested 10-block with probability
        if rng.random() < 0.7 and (b - a + 1) >= 2:
            len10 = int(rng.randrange(1, min(6, b - a + 1) + 1))
            s10 = int(rng.randrange(a, b - len10 + 2))
            e10 = s10 + len10 - 1
            for k in range(s10, e10 + 1):
                m_by_k[int(k)] = 10

    # clean: omit explicit 6 entries
    m_by_k = {int(k): int(m) for k, m in m_by_k.items() if int(m) != 6}
    return m_by_k


def sample_richer_schedule(rng, *, k_lo: int = 0, k_hi: int = 63) -> Dict[int, int]:
    """
    Sample a richer but still structured m-schedule (less demo-like, more search-friendly):
      - baseline 6
      - choose 1..3 m=8 blocks (contiguous, merged if overlapping)
      - in each 8-block choose 1..2 nested m=10 blocks (contiguous, may overlap/merge)

    This tends to increase the number of refined cells while avoiding high-frequency alternation.
    """
    k_lo = int(k_lo)
    k_hi = int(k_hi)
    if k_lo < 0 or k_hi > 63 or k_lo > k_hi:
        raise ValueError("Require 0<=k_lo<=k_hi<=63.")

    m_by_k: Dict[int, int] = {}

    n8 = int(rng.randrange(1, 4))  # 1..3 blocks
    blocks8: List[Tuple[int, int]] = []
    for _ in range(n8):
        length = int(rng.randrange(4, min(20, k_hi - k_lo + 1) + 1))
        start = int(rng.randrange(k_lo, k_hi - length + 2))
        end = start + length - 1
        blocks8.append((start, end))
    blocks8.sort()

    merged8: List[Tuple[int, int]] = []
    for a, b in blocks8:
        if not merged8 or a > merged8[-1][1] + 1:
            merged8.append((a, b))
        else:
            merged8[-1] = (merged8[-1][0], max(merged8[-1][1], b))
    blocks8 = merged8[:3]

    for a, b in blocks8:
        for k in range(a, b + 1):
            m_by_k[int(k)] = 8
        # Choose 1..2 nested 10-blocks within [a,b]
        n10 = 1 if rng.random() < 0.7 else 2
        blocks10: List[Tuple[int, int]] = []
        for _ in range(n10):
            len10 = int(rng.randrange(2, min(10, b - a + 1) + 1))
            s10 = int(rng.randrange(a, b - len10 + 2))
            e10 = s10 + len10 - 1
            blocks10.append((s10, e10))
        blocks10.sort()
        # merge nested 10 blocks
        merged10: List[Tuple[int, int]] = []
        for x, y in blocks10:
            if not merged10 or x > merged10[-1][1] + 1:
                merged10.append((x, y))
            else:
                merged10[-1] = (merged10[-1][0], max(merged10[-1][1], y))
        for s10, e10 in merged10:
            for k in range(s10, e10 + 1):
                m_by_k[int(k)] = 10

    m_by_k = {int(k): int(m) for k, m in m_by_k.items() if int(m) != 6}
    return m_by_k


def sample_unimodal_schedule(rng, *, k_lo: int = 0, k_hi: int = 63) -> Dict[int, int]:
    """
    Sample a unimodal m-schedule:
      - baseline 6
      - choose one contiguous 10-block
      - wrap it by a contiguous 8-block (a superset of the 10-block)

    This yields a single \"hump\" in refinement and avoids frequent alternation.
    """
    k_lo = int(k_lo)
    k_hi = int(k_hi)
    if k_lo < 0 or k_hi > 63 or k_lo > k_hi:
        raise ValueError("Require 0<=k_lo<=k_hi<=63.")

    width = int(k_hi - k_lo + 1)
    if width <= 0:
        return {}

    # 10-block
    len10 = int(rng.randrange(2, min(12, width) + 1))
    s10 = int(rng.randrange(k_lo, k_hi - len10 + 2))
    e10 = int(s10 + len10 - 1)

    # 8-block (contains 10-block)
    extra_left = int(rng.randrange(0, min(10, s10 - k_lo) + 1))
    extra_right = int(rng.randrange(0, min(10, k_hi - e10) + 1))
    s8 = int(max(k_lo, s10 - extra_left))
    e8 = int(min(k_hi, e10 + extra_right))

    m_by_k: Dict[int, int] = {}
    for k in range(s8, e8 + 1):
        m_by_k[int(k)] = 8
    for k in range(s10, e10 + 1):
        m_by_k[int(k)] = 10
    return {int(k): int(m) for k, m in m_by_k.items() if int(m) != 6}

