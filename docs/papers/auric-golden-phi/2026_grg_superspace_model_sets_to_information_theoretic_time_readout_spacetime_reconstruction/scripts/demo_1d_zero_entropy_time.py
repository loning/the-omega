#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo A: zero-entropy refinement time for Sturmian rotation readout.

We compute the cylinder measure exactly by intersecting shifted interval constraints
on the circle (Haar measure), and plot tau(t) = -log mu(C(prefix)).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from common_progress import ProgressPrinter


Interval = Tuple[float, float]  # half-open [a,b) with 0<=a<b<=1


def _wrap01(x: float) -> float:
    x = x % 1.0
    return x + 1.0 if x < 0 else x


def _mod_interval(a: float, b: float) -> List[Interval]:
    """Return a list of intervals in [0,1) representing [a,b) mod 1."""
    a = _wrap01(a)
    b = _wrap01(b)
    if a <= b:
        return [(a, b)] if a != b else []
    # Wraps around.
    return [(0.0, b), (a, 1.0)]


def _normalize_union(intervals: List[Interval]) -> List[Interval]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    out: List[Interval] = []
    a0, b0 = intervals[0]
    for a, b in intervals[1:]:
        if a <= b0 + 1e-15:
            b0 = max(b0, b)
        else:
            out.append((a0, b0))
            a0, b0 = a, b
    out.append((a0, b0))
    # Clip.
    out2: List[Interval] = []
    for a, b in out:
        a = max(0.0, min(1.0, a))
        b = max(0.0, min(1.0, b))
        if b > a:
            out2.append((a, b))
    return out2


def _union_complement(intervals: List[Interval]) -> List[Interval]:
    """Complement of a union of disjoint intervals in [0,1)."""
    intervals = _normalize_union(intervals)
    if not intervals:
        return [(0.0, 1.0)]
    out: List[Interval] = []
    cur = 0.0
    for a, b in intervals:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < 1.0:
        out.append((cur, 1.0))
    return out


def _intersect_union(A: List[Interval], B: List[Interval]) -> List[Interval]:
    """Intersection of two unions of disjoint intervals in [0,1)."""
    A = _normalize_union(A)
    B = _normalize_union(B)
    i = 0
    j = 0
    out: List[Interval] = []
    while i < len(A) and j < len(B):
        a1, a2 = A[i]
        b1, b2 = B[j]
        lo = max(a1, b1)
        hi = min(a2, b2)
        if hi > lo:
            out.append((lo, hi))
        if a2 < b2:
            i += 1
        else:
            j += 1
    return out


def union_measure(intervals: List[Interval]) -> float:
    intervals = _normalize_union(intervals)
    return float(sum(b - a for a, b in intervals))


def rotation_readout(alpha: float, x0: float, t: int, interval_I: Interval) -> List[int]:
    a, b = interval_I
    out = []
    for k in range(t):
        x = _wrap01(x0 + k * alpha)
        out.append(1 if (a <= x < b) else 0)
    return out


def cylinder_measure_for_prefix(
    alpha: float,
    prefix: Sequence[int],
    interval_I: Interval,
) -> float:
    """Exact Haar measure of {x0: R(T^k x0)=prefix[k]}."""
    I_a, I_b = interval_I
    allowed: List[Interval] = [(0.0, 1.0)]
    for k, bit in enumerate(prefix):
        # Constraint is x0 in T^{-k}(I) or complement.
        shifted_I = _mod_interval(I_a - k * alpha, I_b - k * alpha)
        if bit == 1:
            constraint = shifted_I
        else:
            constraint = _union_complement(shifted_I)
        allowed = _intersect_union(allowed, constraint)
        if not allowed:
            return 0.0
    return union_measure(allowed)


def empirical_block_entropy(bits: Sequence[int], block_len: int) -> float:
    """Empirical Shannon entropy H(A_0^{n-1}) from a long 0/1 sequence."""
    if block_len <= 0:
        return 0.0
    n = len(bits)
    if n < block_len:
        return 0.0
    counts: Dict[Tuple[int, ...], int] = {}
    total = n - block_len + 1
    for i in range(total):
        w = tuple(bits[i : i + block_len])
        counts[w] = counts.get(w, 0) + 1
    H = 0.0
    for c in counts.values():
        p = c / total
        H -= p * math.log(p)
    return H


@dataclass(frozen=True)
class Demo1DParams:
    alpha: float
    interval_a: float
    interval_b: float
    x0: float
    t_max: int
    long_T: int
    max_block_len: int


def run_demo(out_dir: Path, fig_out_dir: Path, seed: int = 0) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_out_dir.mkdir(parents=True, exist_ok=True)
    # Golden ratio conjugate (good Diophantine, Sturmian coding for 2-interval partitions).
    phi = (1.0 + 5.0**0.5) / 2.0
    params = Demo1DParams(
        alpha=phi - 1.0,
        interval_a=0.0,
        interval_b=0.38196601125,  # 1/phi^2 (arbitrary non-degenerate choice)
        x0=0.123456789,
        t_max=2000,
        long_T=200000,
        max_block_len=14,
    )

    I = (params.interval_a, params.interval_b)

    pp = ProgressPrinter("demo_1d")
    # Exact tau(t)
    tau_t = np.zeros(params.t_max, dtype=float)
    mu_t = np.zeros(params.t_max, dtype=float)
    prefix: List[int] = []
    for t in range(1, params.t_max + 1):
        prefix = rotation_readout(params.alpha, params.x0, t, I)
        mu = cylinder_measure_for_prefix(params.alpha, prefix, I)
        mu = max(mu, 1e-300)
        mu_t[t - 1] = mu
        tau_t[t - 1] = -math.log(mu)
        pp.tick(f"t={t} mu={mu:.3e} tau={tau_t[t-1]:.3f}")

    # Long sequence for empirical block entropies (demonstrate h=0 via H_n/n -> 0).
    long_bits = rotation_readout(params.alpha, params.x0, params.long_T, I)
    block_H: Dict[int, float] = {}
    for n in range(1, params.max_block_len + 1):
        Hn = empirical_block_entropy(long_bits, n)
        block_H[n] = float(Hn)
        pp.tick(f"block_entropy n={n} H={Hn:.4f}")

    # Save JSON.
    json_path = out_dir / "demo_1d_entropy_estimates.json"
    payload = {
        "params": {
            "alpha": params.alpha,
            "interval_I": [params.interval_a, params.interval_b],
            "x0": params.x0,
            "t_max": params.t_max,
            "long_T": params.long_T,
            "max_block_len": params.max_block_len,
            "seed": seed,
        },
        "mu_prefix": mu_t.tolist(),
        "tau_prefix": tau_t.tolist(),
        "block_entropy": {str(k): v for k, v in block_H.items()},
        "notes": [
            "For Sturmian codings, KS entropy is zero; tau(t) does not grow linearly in t.",
            "This demo computes exact cylinder measures by interval intersections on the circle.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Plot.
    import matplotlib.pyplot as plt

    t = np.arange(1, params.t_max + 1)
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(t, tau_t, lw=1.0)
    ax[0].set_xlabel("t (prefix length)")
    ax[0].set_ylabel("tau(t) = -log mu(C(prefix))")
    ax[0].set_title("Zero-entropy refinement time (exact)")
    ax[0].grid(True, alpha=0.3)

    ax[1].plot(np.log(t), tau_t, lw=1.0)
    ax[1].set_xlabel("log t")
    ax[1].set_ylabel("tau(t)")
    ax[1].set_title("Subexponential scaling (log t axis)")
    ax[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig_path = fig_out_dir / "demo_1d_tau_log_growth.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)

    # Also a small entropy plot.
    fig2, ax2 = plt.subplots(figsize=(5, 3.6))
    ns = np.array(sorted(block_H.keys()))
    Hs = np.array([block_H[int(n)] for n in ns])
    ax2.plot(ns, Hs / ns, marker="o", ms=3, lw=1.0)
    ax2.set_xlabel("block length n")
    ax2.set_ylabel("H(block_n)/n")
    ax2.set_title("Empirical entropy-rate proxy")
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2_path = fig_out_dir / "demo_1d_entropy_rate_proxy.png"
    fig2.savefig(fig2_path, dpi=160)
    plt.close(fig2)

    return {
        "demo_1d_entropy_estimates.json": str(json_path),
        "demo_1d_tau_log_growth.png": str(fig_path),
        "demo_1d_entropy_rate_proxy.png": str(fig2_path),
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, required=True, help="Output directory for data artifacts/")
    ap.add_argument("--fig-out", type=str, required=True, help="Output directory for figures/")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    out_dir = Path(args.out)
    fig_out_dir = Path(args.fig_out)
    outputs = run_demo(out_dir=out_dir, fig_out_dir=fig_out_dir, seed=int(args.seed))
    for k, v in outputs.items():
        print(f"[demo_1d] wrote {k}: {v}", flush=True)


if __name__ == "__main__":
    main()

