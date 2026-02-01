#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IID baselines: Bernoulli and Parry source -> Fold_m histogram vs Parry baseline, with TV certificates.

Motivation:
- The rotation (Sturmian) experiment is illustrative but not mixing.
- Here we add IID block sampling to provide finite-sample confidence envelopes (TV) under explicit assumptions.

Outputs:
- artifacts/export/iid_sources_fold_vs_parry.csv
"""

from __future__ import annotations

import csv
import math
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np

from common_paths import export_dir
from common_phi_fold import PHI, Progress, fold_m, parry_params


def _pack_bits_to_int(bits: Iterable[int], m: int) -> int:
    x = 0
    for b in bits:
        x = (x << 1) | (1 if b else 0)
    return x & ((1 << m) - 1)


def _int_to_bits(x: int, m: int) -> List[int]:
    return [(x >> (m - 1 - i)) & 1 for i in range(m)]


def build_fold_map(m: int, prog: Progress) -> List[int]:
    """Map each microstate int in [0,2^m) to folded int in [0,2^m)."""
    size = 1 << m
    out = [0] * size
    for w in range(size):
        bits = _int_to_bits(w, m)
        folded = fold_m(bits)
        out[w] = _pack_bits_to_int(folded, m)
        prog.tick(f"build_fold_map m={m} w={w}/{size}")
    return out


def build_parry_q(m: int) -> Dict[int, float]:
    """Parry cylinder distribution on legal length-m words, keyed by packed int."""
    # Same parameterization as in exp_rotation_fold_vs_parry.py.
    pi1 = 1.0 / (PHI * PHI + 1.0)
    pi0 = 1.0 - pi1
    p00 = 1.0 / PHI
    p01 = 1.0 / (PHI * PHI)

    q: Dict[int, float] = {}
    for w in range(1 << m):
        # Forbid adjacent 1s.
        if (w & (w >> 1)) != 0:
            continue
        bits = _int_to_bits(w, m)
        p = pi1 if bits[0] == 1 else pi0
        ok = True
        for a, b in zip(bits, bits[1:]):
            if a == 0 and b == 0:
                p *= p00
            elif a == 0 and b == 1:
                p *= p01
            elif a == 1 and b == 0:
                p *= 1.0
            else:
                ok = False
                break
        if ok:
            q[w] = p
    return q


def tv_distance_int(p: Dict[int, float], q: Dict[int, float]) -> float:
    keys = set(p.keys()) | set(q.keys())
    s = 0.0
    for k in keys:
        s += abs(p.get(k, 0.0) - q.get(k, 0.0))
    return 0.5 * s


def kl_divergence_int(p: Dict[int, float], q: Dict[int, float], eps: float = 1e-300) -> float:
    s = 0.0
    for k, pk in p.items():
        if pk <= 0.0:
            continue
        qk = q.get(k, 0.0)
        qk = qk if qk > 0.0 else eps
        s += pk * math.log(pk / qk)
    return s


def weissman_kl_eps(n: int, k: int, delta: float) -> float:
    """A simple high-probability upper bound for KL(ĥ || p) under IID sampling.

    Standard "method of types" / Sanov-style bound for a k-ary distribution:
      P( KL(ĥ || p) >= eps ) <= (n+1)^k * exp(-n eps).

    Solve for eps at confidence 1-delta:
      eps = (k log(n+1) + log(1/delta)) / n.

    This is conservative but fully explicit and assumption-auditable.
    """
    if n <= 0:
        return 1.0
    if k <= 1:
        return 0.0
    if not (0.0 < delta < 1.0):
        raise ValueError("delta must be in (0,1)")
    return (float(k) * math.log(float(n) + 1.0) + math.log(1.0 / delta)) / float(n)


def weissman_tv_eps(n: int, k: int, delta: float) -> float:
    """Return epsilon such that P(TV(ĥ, p) > eps) <= delta for IID samples over k symbols.

    Uses a standard bound (Weissman et al.): P(||ĥ-p||_1 > e) <= 2^k * exp(-n e^2 / 2).
    Thus with e = sqrt(2/n * (k ln2 + ln(1/delta))), we get TV = 0.5 * ||.||_1.
    """
    if n <= 0:
        return 1.0
    if k <= 1:
        return 0.0
    if not (0.0 < delta < 1.0):
        raise ValueError("delta must be in (0,1)")
    e_l1 = math.sqrt((2.0 / float(n)) * (float(k) * math.log(2.0) + math.log(1.0 / delta)))
    return 0.5 * e_l1


def bernoulli_true_folded_dist(m: int, p1: float, fold_map: List[int], prog: Progress) -> Dict[int, float]:
    """Exact pushforward distribution of Fold_m under IID Bernoulli(p1) blocks."""
    if not (0.0 <= p1 <= 1.0):
        raise ValueError("p1 must be in [0,1]")
    size = 1 << m
    out: Dict[int, float] = {}
    p0 = 1.0 - p1
    for w in range(size):
        ones = int(bin(w).count("1"))
        pw = (p1**ones) * (p0 ** (m - ones))
        fw = fold_map[w]
        out[fw] = out.get(fw, 0.0) + pw
        prog.tick(f"bernoulli_true_folded_dist m={m} w={w}/{size}")
    return out


def sample_blocks_bernoulli(rng: np.random.Generator, m: int, n_blocks: int, p1: float) -> np.ndarray:
    """Return packed int blocks of length m, IID Bernoulli(p1)."""
    bits = (rng.random((n_blocks, m)) < p1).astype(np.uint8)
    out = np.zeros(n_blocks, dtype=np.uint32)
    for j in range(m):
        out = (out << 1) | bits[:, j].astype(np.uint32)
    return out


def sample_blocks_parry(rng: np.random.Generator, m: int, n_blocks: int) -> np.ndarray:
    """Return packed int blocks of length m, IID blocks sampled from stationary Parry chain."""
    _, pi0, pi1, p00, p01 = parry_params()
    # For state 0: P(0->0)=p00, P(0->1)=p01. For state 1: P(1->0)=1.
    out = np.zeros(n_blocks, dtype=np.uint32)
    # First bit from stationary distribution.
    s = (rng.random(n_blocks) < pi1).astype(np.uint8)
    out = (out << 1) | s.astype(np.uint32)
    for _ in range(m - 1):
        u = rng.random(n_blocks)
        nxt = np.zeros(n_blocks, dtype=np.uint8)
        # from 0
        mask0 = s == 0
        if mask0.any():
            # 0->1 if u in [p00, 1), i.e. u >= p00
            nxt0 = (u[mask0] >= p00).astype(np.uint8)
            nxt[mask0] = nxt0
        # from 1: always go to 0
        # nxt already 0 on mask1.
        s = nxt
        out = (out << 1) | s.astype(np.uint32)
    return out


@dataclass(frozen=True)
class Case:
    model: str
    p1: float | None  # used only for Bernoulli


def main() -> None:
    out_csv = export_dir() / "iid_sources_fold_vs_parry.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Moderate grid to keep runtime reasonable while still showing finite-sample behavior.
    ms = [6, 8, 10, 12, 14, 16, 18]
    Ns = [2_000, 5_000, 10_000, 30_000, 100_000]
    seeds = [1, 2, 3, 4, 5]
    delta = 0.05  # 95% confidence envelope

    cases = [
        Case(model="parry_iid_blocks", p1=None),
        Case(model="bernoulli_iid_blocks", p1=0.5),
    ]

    prog = Progress("exp_iid_sources_fold_vs_parry", every_seconds=20.0)
    t0_all = time.time()

    # Precompute fold maps and Parry baselines per m.
    fold_maps: Dict[int, List[int]] = {}
    parry_qs: Dict[int, Dict[int, float]] = {}
    for m in ms:
        fold_maps[m] = build_fold_map(m, prog)
        parry_qs[m] = build_parry_q(m)

    # Precompute the Bernoulli(p=0.5) exact folded distribution for each m (used for the gap term).
    bernoulli_fold_true: Dict[int, Dict[int, float]] = {}
    for m in ms:
        bernoulli_fold_true[m] = bernoulli_true_folded_dist(m, 0.5, fold_maps[m], prog)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "p1",
                "seed",
                "m",
                "N",
                "tv_to_parry",
                "kl_to_parry",
                "kl_to_true",
                "tv_gap_true_to_parry",
                "kl_eps_95",
                "kl_bound_95",
                "tv_eps_95",
                "tv_bound_95",
                "unique_types",
                "elapsed_s",
            ],
        )
        wr.writeheader()

        for case in cases:
            for seed in seeds:
                rng = np.random.default_rng(seed)
                for m in ms:
                    fold_map = fold_maps[m]
                    q_parry = parry_qs[m]
                    k = len(q_parry)  # alphabet size for folded outputs (legal words)

                    # True gap term TV(p_true, parry).
                    # Also compute KL(ĥ || p_true) and a non-asymptotic high-probability certificate.
                    if case.model == "parry_iid_blocks":
                        tv_gap = 0.0
                        p_true = q_parry
                    elif case.model == "bernoulli_iid_blocks":
                        tv_gap = tv_distance_int(bernoulli_fold_true[m], q_parry)
                        p_true = bernoulli_fold_true[m]
                    else:
                        raise RuntimeError("unknown case")

                    # Sample once at Nmax and slice prefixes (keeps runtime lower).
                    Nmax = max(Ns)
                    t0 = time.time()
                    if case.model == "parry_iid_blocks":
                        blocks = sample_blocks_parry(rng, m, Nmax)
                    else:
                        assert case.p1 is not None
                        blocks = sample_blocks_bernoulli(rng, m, Nmax, case.p1)

                    # Fold all blocks (vectorized-ish loop).
                    folded = np.empty(Nmax, dtype=np.uint32)
                    for i in range(Nmax):
                        folded[i] = fold_map[int(blocks[i])]
                        prog.tick(f"fold blocks model={case.model} seed={seed} m={m} i={i}/{Nmax}")

                    for N in Ns:
                        t1 = time.time()
                        vals = folded[:N]
                        counts: Dict[int, int] = {}
                        for x in vals:
                            kx = int(x)
                            counts[kx] = counts.get(kx, 0) + 1

                        p_hat: Dict[int, float] = {k0: v / float(N) for k0, v in counts.items()}
                        tv = tv_distance_int(p_hat, q_parry)
                        kl = kl_divergence_int(p_hat, q_parry)

                        # Finite-sample TV envelope against true model, then triangle to Parry baseline.
                        tv_eps = weissman_tv_eps(N, k, delta=delta)
                        tv_bound = min(1.0, tv_gap + tv_eps)

                        # KL to the true IID model distribution and its certificate.
                        kl_true = kl_divergence_int(p_hat, p_true)
                        kl_eps = weissman_kl_eps(N, k, delta=delta)
                        kl_bound = min(1.0, kl_eps)

                        elapsed = time.time() - t1
                        wr.writerow(
                            {
                                "model": case.model,
                                "p1": "" if case.p1 is None else f"{case.p1:.16g}",
                                "seed": seed,
                                "m": m,
                                "N": N,
                                "tv_to_parry": f"{tv:.12g}",
                                "kl_to_parry": f"{kl:.12g}",
                                "kl_to_true": f"{kl_true:.12g}",
                                "tv_gap_true_to_parry": f"{tv_gap:.12g}",
                                "kl_eps_95": f"{kl_eps:.12g}",
                                "kl_bound_95": f"{kl_bound:.12g}",
                                "tv_eps_95": f"{tv_eps:.12g}",
                                "tv_bound_95": f"{tv_bound:.12g}",
                                "unique_types": len(counts),
                                "elapsed_s": f"{elapsed:.6g}",
                            }
                        )
                        prog.tick(
                            f"done model={case.model} seed={seed} m={m} N={N} tv={tv:.4g} kl_true={kl_true:.3g} tv_bound95={tv_bound:.3g} kl_eps95={kl_eps:.3g}"
                        )

                    _ = time.time() - t0

    dt_all = time.time() - t0_all
    print(f"[exp_iid_sources_fold_vs_parry] WROTE {out_csv} in {dt_all:.1f}s", flush=True)


if __name__ == "__main__":
    main()

