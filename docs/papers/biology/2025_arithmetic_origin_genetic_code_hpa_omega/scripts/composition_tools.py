# -*- coding: utf-8 -*-
"""
Sequence composition utilities (standard library only).

Used for GC / dinucleotide-matched controls to separate uplift signals from base-composition bias.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable


_DNA = set("ACGT")
_DINUCS = [a + b for a in "ACGT" for b in "ACGT"]


def normalize_dna(seq: str) -> str:
    """
    Upper-case and normalize RNA to DNA (U->T), then remove non-ACGT characters.
    """
    s = (seq or "").upper().replace("U", "T")
    return "".join(ch for ch in s if ch in _DNA)


def gc_fraction(seq: str) -> float | None:
    """
    GC fraction over A/C/G/T only. Returns None if no valid bases.
    """
    s = normalize_dna(seq)
    n = len(s)
    if n <= 0:
        return None
    gc = sum(1 for ch in s if ch in ("G", "C"))
    return float(gc) / float(n)


def dinuc_counts(seq: str) -> dict[str, int]:
    """
    16-dinucleotide counts over A/C/G/T only (overlapping). Invalid chars are removed first.
    """
    s = normalize_dna(seq)
    out = Counter()
    for i in range(len(s) - 1):
        out[s[i : i + 2]] += 1
    # Ensure all keys exist for stable downstream vectorization.
    return {k: int(out.get(k, 0)) for k in _DINUCS}


def dinuc_freq(seq: str) -> dict[str, float] | None:
    """
    16-dinucleotide frequency vector (L1 sums to 1) over A/C/G/T only.
    Returns None if no dinucleotides exist.
    """
    c = dinuc_counts(seq)
    total = sum(int(v) for v in c.values())
    if total <= 0:
        return None
    return {k: float(v) / float(total) for k, v in c.items()}


def l1_distance_16(v1: dict[str, float] | None, v2: dict[str, float] | None) -> float | None:
    """
    L1 distance between two 16-dinucleotide frequency vectors.
    """
    if v1 is None or v2 is None:
        return None
    d = 0.0
    for k in _DINUCS:
        d += abs(float(v1.get(k, 0.0)) - float(v2.get(k, 0.0)))
    return float(d)


def cpg_rate(seq: str) -> float | None:
    """
    CpG dinucleotide fraction among all dinucleotides (overlapping), after filtering to A/C/G/T.
    """
    s = normalize_dna(seq)
    n = len(s)
    if n < 2:
        return None
    total = n - 1
    cpg = 0
    for i in range(total):
        if s[i] == "C" and s[i + 1] == "G":
            cpg += 1
    return float(cpg) / float(total) if total > 0 else None


def ta_rate(seq: str) -> float | None:
    """
    TA dinucleotide fraction among all dinucleotides (overlapping), after filtering to A/C/G/T.
    """
    s = normalize_dna(seq)
    n = len(s)
    if n < 2:
        return None
    total = n - 1
    ta = 0
    for i in range(total):
        if s[i] == "T" and s[i + 1] == "A":
            ta += 1
    return float(ta) / float(total) if total > 0 else None


def bin_value(x: float | None, *, edges: list[float]) -> int | None:
    """
    Bin x into 0..len(edges) by edges (monotone increasing).
    Returns None if x is None or NaN.
    """
    if x is None:
        return None
    x0 = float(x)
    if math.isnan(x0):
        return None
    b = 0
    for e in edges:
        if x0 <= float(e):
            return int(b)
        b += 1
    return int(b)


def summarize_bins(values: Iterable[tuple[str, int | None]]) -> dict[str, int]:
    """
    Utility to count bin assignments (string->count). None bins are counted under 'NA'.
    """
    out: dict[str, int] = {}
    for label, b in values:
        key = f"{label}:{'NA' if b is None else int(b)}"
        out[key] = int(out.get(key, 0)) + 1
    return out


