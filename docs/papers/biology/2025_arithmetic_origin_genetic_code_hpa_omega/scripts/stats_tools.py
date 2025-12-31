# -*- coding: utf-8 -*-
"""
Small statistical utilities (standard library only).

This module intentionally avoids third-party dependencies to keep the paper
reproducible in minimal environments.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Iterable


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_two_sided_p(z: float) -> float:
    p = 2.0 * (1.0 - normal_cdf(abs(z)))
    return max(0.0, min(1.0, p))


def bh_fdr(p_values: list[float]) -> list[float]:
    """
    Benjamini–Hochberg FDR correction.
    Returns q-values in the original order.
    """
    n = len(p_values)
    if n == 0:
        return []
    pairs = [(i, float(p)) for i, p in enumerate(p_values)]
    pairs.sort(key=lambda x: x[1])

    # Initial q_i = p_i * n / i (1-based rank in ascending order).
    q_raw = [0.0] * n
    for rank, (_idx, p) in enumerate(pairs, start=1):
        q = (p * n) / float(rank)
        q_raw[rank - 1] = max(0.0, min(1.0, q))

    # Enforce monotonicity from the tail: q_i = min(q_i, q_{i+1}).
    for i in range(n - 2, -1, -1):
        q_raw[i] = min(q_raw[i], q_raw[i + 1])

    # Map back to original order.
    out = [0.0] * n
    for k, (idx, _p) in enumerate(pairs):
        out[idx] = q_raw[k]
    return out


def pooled_sd(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(ys) < 2:
        return None
    vx = statistics.pvariance(xs) * (len(xs) / max(1, len(xs) - 1))
    vy = statistics.pvariance(ys) * (len(ys) / max(1, len(ys) - 1))
    num = (len(xs) - 1) * vx + (len(ys) - 1) * vy
    den = (len(xs) - 1) + (len(ys) - 1)
    if den <= 0:
        return None
    s2 = num / float(den)
    return math.sqrt(s2) if s2 > 0 else 0.0


def pooled_sd_from_stats(*, n1: int, var1: float, n2: int, var2: float) -> float | None:
    if n1 < 2 or n2 < 2:
        return None
    den = (n1 - 1) + (n2 - 1)
    if den <= 0:
        return None
    s2 = ((n1 - 1) * float(var1) + (n2 - 1) * float(var2)) / float(den)
    if s2 <= 0:
        return 0.0
    return math.sqrt(s2)


def cohen_d_from_stats(*, n1: int, mean1: float, var1: float, n2: int, mean2: float, var2: float) -> float | None:
    sd = pooled_sd_from_stats(n1=n1, var1=var1, n2=n2, var2=var2)
    if sd is None or sd == 0.0:
        return None
    return (float(mean1) - float(mean2)) / sd


def hedges_g_from_stats(*, n1: int, mean1: float, var1: float, n2: int, mean2: float, var2: float) -> float | None:
    d = cohen_d_from_stats(n1=n1, mean1=mean1, var1=var1, n2=n2, mean2=mean2, var2=var2)
    if d is None:
        return None
    df = int(n1 + n2 - 2)
    if df <= 1:
        return None
    j = 1.0 - (3.0 / (4.0 * float(df) - 1.0))
    return d * j


def mean_diff_ci_normal_from_stats(
    *,
    n1: int,
    mean1: float,
    var1: float,
    n2: int,
    mean2: float,
    var2: float,
    alpha: float = 0.05,
) -> tuple[float, float] | None:
    if n1 < 2 or n2 < 2:
        return None
    se2 = float(var1) / float(n1) + float(var2) / float(n2)
    if se2 <= 0:
        return None
    z = _normal_ppf(1.0 - alpha / 2.0)
    diff = float(mean1) - float(mean2)
    se = math.sqrt(se2)
    return (diff - z * se, diff + z * se)


def cohen_d(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(ys) < 2:
        return None
    sd = pooled_sd(xs, ys)
    if sd is None or sd == 0.0:
        return None
    return (statistics.mean(xs) - statistics.mean(ys)) / sd


def hedges_g(xs: list[float], ys: list[float]) -> float | None:
    """
    Hedges' g: small-sample corrected Cohen's d.
    """
    d = cohen_d(xs, ys)
    if d is None:
        return None
    n1 = len(xs)
    n2 = len(ys)
    df = n1 + n2 - 2
    if df <= 1:
        return None
    j = 1.0 - (3.0 / (4.0 * df - 1.0))
    return d * j


def mean_diff_ci_normal(
    xs: list[float],
    ys: list[float],
    *,
    alpha: float = 0.05,
) -> tuple[float, float] | None:
    """
    Approximate CI for mean difference (mean(xs) - mean(ys)) using normal quantiles.
    This is intentionally minimal and meant for large-n regimes.
    """
    if len(xs) < 2 or len(ys) < 2:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    vx = statistics.pvariance(xs) * (len(xs) / max(1, len(xs) - 1))
    vy = statistics.pvariance(ys) * (len(ys) / max(1, len(ys) - 1))
    se2 = vx / len(xs) + vy / len(ys)
    if se2 <= 0:
        return None
    se = math.sqrt(se2)
    # Two-sided normal critical value using erf inverse approximation via binary search.
    z = _normal_ppf(1.0 - alpha / 2.0)
    diff = mx - my
    return (diff - z * se, diff + z * se)


def _normal_ppf(p: float) -> float:
    """
    Inverse CDF for standard normal via binary search over erf.
    Accurate enough for reporting CIs in this project.
    """
    if not (0.0 < p < 1.0):
        if p <= 0.0:
            return float("-inf")
        if p >= 1.0:
            return float("inf")
        raise ValueError("p must be in (0,1)")
    lo = -10.0
    hi = 10.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if normal_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def perm_p_value_two_sided(
    xs: list[float],
    ys: list[float],
    *,
    n_perm: int = 2000,
    seed: int = 12345,
) -> float | None:
    if len(xs) < 2 or len(ys) < 2:
        return None
    rng = random.Random(int(seed))
    pooled = [float(x) for x in xs] + [float(y) for y in ys]
    n1 = len(xs)
    obs = abs(statistics.mean(xs) - statistics.mean(ys))
    ge = 0
    for _ in range(int(n_perm)):
        rng.shuffle(pooled)
        x1 = pooled[:n1]
        y1 = pooled[n1:]
        if abs(statistics.mean(x1) - statistics.mean(y1)) >= obs:
            ge += 1
    return (ge + 1) / float(int(n_perm) + 1)


@dataclass(frozen=True)
class MeanDiffSummary:
    n_x: int
    n_y: int
    mean_x: float
    mean_y: float
    diff: float
    ci_low: float | None
    ci_high: float | None
    d: float | None
    g: float | None


def summarize_mean_diff(xs: Iterable[float], ys: Iterable[float]) -> MeanDiffSummary | None:
    x = [float(v) for v in xs]
    y = [float(v) for v in ys]
    if len(x) < 2 or len(y) < 2:
        return None
    mx = statistics.mean(x)
    my = statistics.mean(y)
    ci = mean_diff_ci_normal(x, y)
    d = cohen_d(x, y)
    g = hedges_g(x, y)
    return MeanDiffSummary(
        n_x=len(x),
        n_y=len(y),
        mean_x=mx,
        mean_y=my,
        diff=mx - my,
        ci_low=(ci[0] if ci else None),
        ci_high=(ci[1] if ci else None),
        d=d,
        g=g,
    )


@dataclass(frozen=True)
class NullContributionAA:
    aa: str
    n: int
    obs_mean: float
    null_mean: float
    contrib: float


@dataclass(frozen=True)
class NullContributionCodon:
    codon: str
    aa: str
    obs_count: int
    null_count: float
    contrib: float


@dataclass(frozen=True)
class AAPreservingNullDecomposition:
    total_codons: int
    obs_mean: float
    null_mean: float
    null_sd: float
    z_score: float
    p_value: float
    aa_contribs: list[NullContributionAA]
    codon_contribs: list[NullContributionCodon]


def aa_preserving_null_decomposition(
    *,
    aa_counts: dict[str, int],
    codon_counts: dict[str, int],
    codons_by_aa: dict[str, list[str]],
    genetic_code: dict[str, str],
    codon_value: dict[str, float],
    exclude_aas: set[str] | None = None,
) -> AAPreservingNullDecomposition:
    """
    Decompose the deviation of an observed per-codon mean from an amino-acid preserving null:
      - null: within each amino acid, choose synonymous codon uniformly, independently across positions.

    Inputs are expected to be consistent:
      - aa_counts: counts per amino acid across coding tokens (excluding terminal stops if desired)
      - codon_counts: counts per codon across the same token set
      - codons_by_aa: mapping amino acid -> list of synonymous codons
      - genetic_code: mapping codon -> amino acid label
      - codon_value: mapping codon -> scalar value to average (e.g., V or Delta under mu*)
    """
    if exclude_aas is None:
        exclude_aas = {"Stop"}

    total_codons = 0
    for aa, n in aa_counts.items():
        if aa in exclude_aas:
            continue
        total_codons += int(n)
    if total_codons <= 0:
        raise ValueError("No coding codons")

    # Observed mean
    obs_sum = 0.0
    for codon, cnt in codon_counts.items():
        aa = genetic_code.get(codon)
        if aa is None or aa in exclude_aas:
            continue
        v = codon_value.get(codon)
        if v is None:
            continue
        obs_sum += float(cnt) * float(v)
    obs_mean = obs_sum / float(total_codons)

    # Null mean and variance under independence.
    null_sum = 0.0
    null_var_sum = 0.0
    aa_contribs: list[NullContributionAA] = []

    for aa, n in aa_counts.items():
        if aa in exclude_aas:
            continue
        n_i = int(n)
        syn = codons_by_aa.get(aa, [])
        if not syn:
            continue
        vals = [float(codon_value[c]) for c in syn if c in codon_value]
        if not vals:
            continue
        null_mean_aa = float(sum(vals)) / float(len(vals))
        null_var_aa = float(sum((x - null_mean_aa) ** 2 for x in vals)) / float(len(vals))
        null_sum += float(n_i) * null_mean_aa
        null_var_sum += float(n_i) * null_var_aa

        # Observed mean within aa (if present).
        obs_sum_aa = 0.0
        obs_n_aa = 0
        for c in syn:
            cnt = int(codon_counts.get(c, 0))
            if cnt <= 0:
                continue
            v = codon_value.get(c)
            if v is None:
                continue
            obs_sum_aa += float(cnt) * float(v)
            obs_n_aa += cnt
        obs_mean_aa = (obs_sum_aa / float(obs_n_aa)) if obs_n_aa > 0 else null_mean_aa
        contrib = (float(n_i) / float(total_codons)) * (obs_mean_aa - null_mean_aa)
        aa_contribs.append(
            NullContributionAA(
                aa=str(aa),
                n=n_i,
                obs_mean=float(obs_mean_aa),
                null_mean=float(null_mean_aa),
                contrib=float(contrib),
            )
        )

    null_mean = null_sum / float(total_codons)
    null_sd = (math.sqrt(null_var_sum) / float(total_codons)) if null_var_sum > 0 else 0.0
    z_score = (obs_mean - null_mean) / null_sd if null_sd > 0 else 0.0
    p_value = normal_two_sided_p(z_score) if null_sd > 0 else 1.0

    # Codon-level contributions: (obs_count - expected_count_under_null) * value / total_codons
    codon_contribs: list[NullContributionCodon] = []
    for aa, n in aa_counts.items():
        if aa in exclude_aas:
            continue
        n_i = int(n)
        syn = codons_by_aa.get(aa, [])
        if not syn:
            continue
        exp = float(n_i) / float(len(syn))
        for c in syn:
            v = codon_value.get(c)
            if v is None:
                continue
            obs_c = int(codon_counts.get(c, 0))
            contrib = ((float(obs_c) - exp) * float(v)) / float(total_codons)
            codon_contribs.append(
                NullContributionCodon(
                    codon=str(c),
                    aa=str(aa),
                    obs_count=obs_c,
                    null_count=exp,
                    contrib=float(contrib),
                )
            )

    # Sort by absolute contribution (descending) for convenient top-k reporting.
    aa_contribs.sort(key=lambda x: abs(x.contrib), reverse=True)
    codon_contribs.sort(key=lambda x: abs(x.contrib), reverse=True)

    return AAPreservingNullDecomposition(
        total_codons=int(total_codons),
        obs_mean=float(obs_mean),
        null_mean=float(null_mean),
        null_sd=float(null_sd),
        z_score=float(z_score),
        p_value=float(p_value),
        aa_contribs=aa_contribs,
        codon_contribs=codon_contribs,
    )


def prefix_sums(xs: list[float]) -> list[float]:
    """
    Return prefix sums ps with ps[0]=0 and ps[i+1]=sum(xs[:i+1]).
    """
    ps = [0.0]
    s = 0.0
    for x in xs:
        s += float(x)
        ps.append(s)
    return ps


def window_mean_from_prefix(ps: list[float], start: int, end_exclusive: int) -> float:
    """
    Mean of xs[start:end_exclusive] given prefix sums ps.
    Assumes 0 <= start < end_exclusive <= len(xs).
    """
    n = end_exclusive - start
    if n <= 0:
        raise ValueError("empty window")
    return (ps[end_exclusive] - ps[start]) / float(n)


def before_after_window_means_from_prefix(
    ps: list[float],
    *,
    center_idx: int,
    k: int,
) -> tuple[float, float] | None:
    """
    Given prefix sums for a value array v[0..L-1], compute:
      before = mean(v[center_idx-k : center_idx])
      after  = mean(v[center_idx+1 : center_idx+1+k])
    Returns None if either window is out of range.
    """
    if k <= 0:
        raise ValueError("k must be >= 1")
    # Need at least k elements before.
    if center_idx - k < 0:
        return None
    # Need at least k elements after.
    if center_idx + k >= len(ps) - 1:
        return None
    before = window_mean_from_prefix(ps, center_idx - k, center_idx)
    after = window_mean_from_prefix(ps, center_idx + 1, center_idx + 1 + k)
    return (before, after)


def before_after_window_means_multi_k(
    xs: list[float],
    *,
    center_idx: int,
    k_list: list[int],
) -> dict[int, tuple[float, float]]:
    """
    Convenience wrapper for multi-k stop-context summaries.
    Skips k values that do not fit within the array bounds.
    """
    ks = sorted({int(k) for k in k_list if int(k) > 0})
    ps = prefix_sums(xs)
    out: dict[int, tuple[float, float]] = {}
    for k in ks:
        r = before_after_window_means_from_prefix(ps, center_idx=center_idx, k=k)
        if r is None:
            continue
        out[int(k)] = (float(r[0]), float(r[1]))
    return out


