# -*- coding: utf-8 -*-
"""
Protocol kernel utilities for the z128 stable-sector paper.

This module centralizes the deterministic, auditable finite-resolution objects
used across generator scripts:
  - admissible language X_m (no consecutive ones),
  - Zeckendorf digits and the truncation folding map Fold_m,
  - folding fiber statistics g_m and cached enumerations,
  - the golden-mean shift transition matrix and its basic zeta template.

The code is intentionally dependency-light (standard library only) and designed
to be reusable by exp_*.py generators without redefining core logic.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Sequence, Tuple

from common_cache import CACHE_VERSION, cache_path, load_or_compute
from common_constants import LOG_PHI, PHI


def is_admissible_word(w: str) -> bool:
    """Return True iff w contains no consecutive ones ("11")."""
    return "11" not in w


def all_xm(m: int) -> List[str]:
    """
    Enumerate X_m: all length-m binary words with no consecutive ones.
    Cached on disk for determinism and reuse.
    """
    if m <= 0:
        raise ValueError("m must be positive.")

    key = cache_path(f"xm_words_m{m}_v{CACHE_VERSION}.pkl")

    def compute() -> List[str]:
        out: List[str] = []

        def rec(prefix: str, last: str) -> None:
            if len(prefix) == m:
                out.append(prefix)
                return
            rec(prefix + "0", "0")
            if last != "1":
                rec(prefix + "1", "1")

        rec("", "0")
        # Stable ordering helps with reproducible table rows.
        return sorted(out)

    return load_or_compute(key, compute)


def is_boundary_word(w: str) -> bool:
    """Pi-channel boundary tag at finite m: w1=wm=1."""
    if not w:
        raise ValueError("w must be non-empty.")
    return w[0] == "1" and w[-1] == "1"


def split_cyc_bdry(words: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Return (cyclic, boundary) word lists under the pi-channel split."""
    cyc: List[str] = []
    bdry: List[str] = []
    for w in words:
        (bdry if is_boundary_word(w) else cyc).append(w)
    return cyc, bdry


def fib_base_up_to(n: int) -> List[int]:
    """
    Zeckendorf weights [F2, F3, ...] up to the largest <= n.
    Here (F2, F3, F4, ...) = (1, 2, 3, 5, ...).
    """
    if n < 0:
        raise ValueError("n must be nonnegative.")
    F = [1, 2]
    while F[-1] <= n:
        F.append(F[-1] + F[-2])
    if n > 0:
        F.pop()
    return F


def zeckendorf_digits(n: int) -> List[int]:
    """
    Greedy Zeckendorf digits aligned to fib_base_up_to(n).
    Returns digits [c1, c2, ...] where n = sum_k c_k F_{k+1} and c_k c_{k+1}=0.
    """
    if n < 0:
        raise ValueError("n must be nonnegative.")
    if n == 0:
        return []
    F = fib_base_up_to(n)
    digits = [0] * len(F)
    k = len(F) - 1
    while n > 0 and k >= 0:
        if F[k] <= n:
            digits[k] = 1
            n -= F[k]
            k -= 2
        else:
            k -= 1
    return digits


def fold_m(n: int, m: int) -> str:
    """
    Zeckendorf-truncation folding map Fold_m.
    For n in {0,..,2^m-1} this matches the paper's definition.
    """
    if n < 0:
        raise ValueError("n must be nonnegative.")
    if m <= 0:
        raise ValueError("m must be positive.")
    digits = zeckendorf_digits(n)
    if len(digits) < m:
        digits = digits + [0] * (m - len(digits))
    w = "".join("1" if b else "0" for b in digits[:m])
    if not is_admissible_word(w):
        raise AssertionError("Fold_m output violated admissibility.")
    return w


def zeckendorf_value_from_word(w: str) -> int:
    """
    Compute the Zeckendorf value V_m(w)=sum_{k=1}^m w_k F_{k+1} for w in X_m.
    """
    if not w:
        return 0
    m = len(w)
    # Weights are [F2..F_{m+1}] = [1,2,3,5,...].
    weights: List[int] = [1, 2]
    while len(weights) < m:
        weights.append(weights[-1] + weights[-2])
    return sum((1 if w[k] == "1" else 0) * weights[k] for k in range(m))


def cached_foldm_outputs(m: int) -> List[str]:
    """Return outputs[k] = Fold_m(k) for k in {0..2^m-1}, cached on disk."""
    if m <= 0:
        raise ValueError("m must be positive.")
    key = cache_path(f"foldm_outputs_m{m}_v{CACHE_VERSION}.pkl")

    def compute() -> List[str]:
        return [fold_m(k, m) for k in range(1 << m)]

    return load_or_compute(key, compute)


def cached_degeneracy_map(m: int) -> Dict[str, int]:
    """Return gm[w] = |Fold_m^{-1}(w)| over k in {0..2^m-1}, cached on disk."""
    if m <= 0:
        raise ValueError("m must be positive.")
    key = cache_path(f"foldm_deg_m{m}_v{CACHE_VERSION}.pkl")

    def compute() -> Dict[str, int]:
        outs = cached_foldm_outputs(m)
        gm: Dict[str, int] = defaultdict(int)
        for w in outs:
            gm[w] += 1
        return dict(gm)

    return load_or_compute(key, compute)


def folding_histogram(m: int) -> Counter[int]:
    """Return histogram over preimage sizes: g -> number of stable types with that g."""
    Xm = all_xm(m)
    gm = cached_degeneracy_map(m)
    degs = [gm[w] for w in Xm]
    return Counter(degs)


def max_degeneracy(m: int) -> int:
    """Return r_m := max_w g_m(w) computed from the cached degeneracy map."""
    Xm = all_xm(m)
    gm = cached_degeneracy_map(m)
    return max(gm[w] for w in Xm)


@dataclass(frozen=True)
class GoldenMeanShift:
    """
    Minimal golden-mean shift package used by the e-channel templates.
    """

    A00: int = 1
    A01: int = 1
    A10: int = 1
    A11: int = 0

    def transition_matrix(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        return ((self.A00, self.A01), (self.A10, self.A11))

    def zeta(self, z: float) -> float:
        # ζ(z)=1/(1-z-z^2)
        denom = 1.0 - z - (z * z)
        return 1.0 / denom

    def zeta_abel_normalized(self, r: float) -> float:
        # ζ_e(r) := ζ(r/phi)
        return self.zeta(r / PHI)

    def topological_entropy(self) -> float:
        return LOG_PHI

    def spectral_radius(self) -> float:
        # For A=[[1,1],[1,0]] the spectral radius is phi.
        return PHI

    def subdominant_eigenvalue(self) -> float:
        # The second eigenvalue is -1/phi.
        return -1.0 / PHI

