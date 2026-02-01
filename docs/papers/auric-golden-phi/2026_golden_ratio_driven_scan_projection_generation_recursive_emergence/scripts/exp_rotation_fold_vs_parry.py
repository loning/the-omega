#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rotation scan -> window microstates -> Fold_m histogram vs Parry baseline.

Outputs:
- artifacts/export/rotation_fold_vs_parry.csv
"""

from __future__ import annotations

import csv
import math
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np

from common_paths import export_dir
from common_ostrowski_fold import metallic_alpha
from common_phi_fold import PHI, Progress, fold_m, is_golden_legal


def _pack_bits_to_int(bits: Iterable[int], m: int) -> int:
    """Pack length-m bits into an int, MSB is position 1."""
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
    # Parameters from the paper: pi(1)=1/(phi^2+1), pi(0)=1-pi(1);
    # transitions: 00 with 1/phi, 01 with 1/phi^2, 10 with 1.
    pi1 = 1.0 / (PHI * PHI + 1.0)
    pi0 = 1.0 - pi1
    p00 = 1.0 / PHI
    p01 = 1.0 / (PHI * PHI)

    q: Dict[int, float] = {}
    for w in range(1 << m):
        # Fast legality check on packed bits: forbid adjacent 1s.
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


def _golden_discrepancy_upper_bound_explicit(N: int) -> float:
    """Appendix-H explicit bound for alpha=phi^{-1}, valid for N>=2."""
    if N < 2:
        return 1.0
    return (3.0 + math.ceil(math.log((5.0 ** 0.5) * N) / math.log(PHI))) / float(N)


def discrepancy_upper_bound_from_partial_quotients(N: int, a: List[int]) -> float:
    """Upper bound via partial quotients: D_N^* <= (1 + sum_{j=1}^{n+1} a_j)/N.

    Uses denominators q_n from continued fractions; valid uniformly in x0.
    """
    if N < 1:
        return 1.0
    if any(x < 1 for x in a):
        raise ValueError("partial quotients must be >= 1")

    # Build q_n until q_n <= N < q_{n+1}.
    # q_{-1}=0, q_0=1, q_{k+1}=a_{k+1} q_k + q_{k-1}.
    q_minus_1 = 0
    q_0 = 1
    qs = [q_0]
    q_prev, q_curr = q_minus_1, q_0
    # We will extend with 1's if needed (tail-ones family).
    # This is enough for the experiment families we use.
    a_extended: List[int] = list(a)

    # Ensure we have enough digits to push q above N.
    while True:
        k = len(qs) - 1  # current index is q_k
        if q_curr > N:
            break
        # Need a_{k+1}
        if k + 1 > len(a_extended):
            a_extended.append(1)
        ak1 = a_extended[k]  # a_{k+1} with 1-based indexing
        q_next = ak1 * q_curr + q_prev
        qs.append(q_next)
        q_prev, q_curr = q_curr, q_next

    # Find n s.t. q_n <= N < q_{n+1}. Since qs[-1] = q_{K} > N, take n=K-1.
    n = len(qs) - 2
    # Need sum_{j=1}^{n+1} a_j. Ensure a_extended is long enough.
    while len(a_extended) < n + 1:
        a_extended.append(1)
    sum_a = sum(a_extended[: n + 1])
    return (1.0 + float(sum_a)) / float(N)


def rotation_bits(alpha: float, x0: float, beta: float, n: int) -> np.ndarray:
    """Binary readout s_t = 1_{[0,beta)}({x0 + t alpha}), length n."""
    ts = np.arange(n, dtype=np.float64)
    xs = (x0 + alpha * ts) % 1.0
    return (xs < beta).astype(np.uint8)


@dataclass(frozen=True)
class Config:
    alpha_name: str
    alpha: float
    partial_quotients_prefix: List[int]
    beta: float
    x0: float


def count_folded_hist(s: np.ndarray, m: int, N: int, fold_map: List[int], prog: Progress) -> Dict[int, int]:
    """Count histogram of Fold_m over the first N windows of length m from s."""
    if N + m - 1 > len(s):
        raise ValueError("s too short for requested N,m")
    mask = (1 << m) - 1
    w = _pack_bits_to_int(s[:m], m)
    counts: Dict[int, int] = {}
    for t in range(N):
        if t > 0:
            w = ((w << 1) & mask) | int(s[t + m - 1])
        folded = fold_map[w]
        counts[folded] = counts.get(folded, 0) + 1
        prog.tick(f"count m={m} t={t}/{N}")
    return counts


def main() -> None:
    out_csv = export_dir() / "rotation_fold_vs_parry.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Systematic but bounded grid (keeps runtime reasonable).
    # NOTE: build_fold_map scales like 2^m, so keep max m moderate.
    ms = [6, 8, 10, 12, 14, 16, 18]
    Ns = [10_000, 30_000, 100_000, 300_000]

    # Deterministic (beta,x0) replicates for error bars.
    betas = [0.2, 0.3, 0.5, 0.6180339887]
    x0s = [0.123, 0.271, 0.731]

    # Alpha families:
    # - bounded partial quotients (metallic means): [0;A,A,A,...]
    # - large partial quotient then ones: [0;B,1,1,1,...] to stress resonance.
    alpha_families: List[Tuple[str, float, List[int]]] = []

    for A in [1, 2, 3, 5]:
        name = "golden" if A == 1 else f"metal_{A}"
        alpha_families.append((name, metallic_alpha(A), [A]))

    # Large-partial-quotient prefix, then a tail of ones (approximated by float alpha).
    # We record the prefix so we can compute discrepancy upper bounds consistently.
    for B in [10, 30, 100]:
        # alpha ~ [0; B, 1, 1, 1, ...]
        # We implement this by solving the tail ones exactly: tail = 1/phi.
        tail = 1.0 / PHI
        alpha = 1.0 / (float(B) + tail)
        alpha_families.append((f"large_pq_{B}_then_ones", alpha, [B, 1]))

    configs: List[Config] = []
    for (alpha_name, alpha, pq_prefix) in alpha_families:
        for beta in betas:
            for x0 in x0s:
                configs.append(
                    Config(
                        alpha_name=alpha_name,
                        alpha=alpha,
                        partial_quotients_prefix=list(pq_prefix),
                        beta=float(beta),
                        x0=float(x0),
                    )
                )

    # Precompute fold maps and Parry baselines per m.
    fold_maps: Dict[int, List[int]] = {}
    parry_qs: Dict[int, Dict[int, float]] = {}

    prog = Progress("exp_rotation_fold_vs_parry", every_seconds=20.0)

    t0_all = time.time()
    for m in ms:
        fold_maps[m] = build_fold_map(m, prog)
        parry_qs[m] = build_parry_q(m)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "alpha_name",
                "alpha",
                "partial_quotients_prefix",
                "beta",
                "x0",
                "m",
                "N",
                "tv",
                "kl",
                "unique_types",
                "DN_star_upper_bound",
                "elapsed_s",
            ],
        )
        wr.writeheader()

        for cfg in configs:
            for m in ms:
                # Generate bits once per (cfg,m,Nmax) and slice prefixes for smaller N.
                Nmax = max(Ns)
                s_len = Nmax + m - 1
                s = rotation_bits(cfg.alpha, cfg.x0, cfg.beta, s_len)

                for N in Ns:
                    t0 = time.time()
                    counts = count_folded_hist(
                        s=s,
                        m=m,
                        N=N,
                        fold_map=fold_maps[m],
                        prog=prog,
                    )

                    # Normalize p
                    p: Dict[int, float] = {k: v / float(N) for k, v in counts.items()}
                    q = parry_qs[m]

                    # Sanity: folded outputs should be golden-legal.
                    for k in list(p.keys())[:10]:
                        if (k & (k >> 1)) != 0:
                            raise RuntimeError("Fold produced illegal word")

                    tv = tv_distance_int(p, q)
                    kl = kl_divergence_int(p, q)

                    elapsed = time.time() - t0
                    wr.writerow(
                        {
                            "model": "rotation_scan",
                            "alpha_name": cfg.alpha_name,
                            "alpha": f"{cfg.alpha:.16g}",
                            "partial_quotients_prefix": ",".join(str(x) for x in cfg.partial_quotients_prefix),
                            "beta": f"{cfg.beta:.16g}",
                            "x0": f"{cfg.x0:.16g}",
                            "m": m,
                            "N": N,
                            "tv": f"{tv:.12g}",
                            "kl": f"{kl:.12g}",
                            "unique_types": len(counts),
                            "DN_star_upper_bound": f"{min(_golden_discrepancy_upper_bound_explicit(N), discrepancy_upper_bound_from_partial_quotients(N, cfg.partial_quotients_prefix)):.12g}"
                            if cfg.alpha_name == "golden"
                            else f"{discrepancy_upper_bound_from_partial_quotients(N, cfg.partial_quotients_prefix):.12g}",
                            "elapsed_s": f"{elapsed:.6g}",
                        }
                    )
                    prog.tick(f"done cfg={cfg.alpha_name} m={m} N={N} tv={tv:.4g} kl={kl:.4g}")

    dt_all = time.time() - t0_all
    print(f"[exp_rotation_fold_vs_parry] WROTE {out_csv} in {dt_all:.1f}s", flush=True)


if __name__ == "__main__":
    main()

