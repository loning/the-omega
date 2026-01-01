"""
Genetic-code reverse compilation tools for the Fold_6 template.

All code is standard-library Python (no third-party dependencies).
"""

from __future__ import annotations

import itertools
import math
import gzip
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


# --------------------------
# Core data: standard genetic code (RNA)
# --------------------------

GENETIC_CODE: dict[str, str] = {
    "UUU": "Phe",
    "UUC": "Phe",
    "UUA": "Leu",
    "UUG": "Leu",
    "CUU": "Leu",
    "CUC": "Leu",
    "CUA": "Leu",
    "CUG": "Leu",
    "AUU": "Ile",
    "AUC": "Ile",
    "AUA": "Ile",
    "AUG": "Met",
    "GUU": "Val",
    "GUC": "Val",
    "GUA": "Val",
    "GUG": "Val",
    "UCU": "Ser",
    "UCC": "Ser",
    "UCA": "Ser",
    "UCG": "Ser",
    "CCU": "Pro",
    "CCC": "Pro",
    "CCA": "Pro",
    "CCG": "Pro",
    "ACU": "Thr",
    "ACC": "Thr",
    "ACA": "Thr",
    "ACG": "Thr",
    "GCU": "Ala",
    "GCC": "Ala",
    "GCA": "Ala",
    "GCG": "Ala",
    "UAU": "Tyr",
    "UAC": "Tyr",
    "UAA": "Stop",
    "UAG": "Stop",
    "CAU": "His",
    "CAC": "His",
    "CAA": "Gln",
    "CAG": "Gln",
    "AAU": "Asn",
    "AAC": "Asn",
    "AAA": "Lys",
    "AAG": "Lys",
    "GAU": "Asp",
    "GAC": "Asp",
    "GAA": "Glu",
    "GAG": "Glu",
    "UGU": "Cys",
    "UGC": "Cys",
    "UGA": "Stop",
    "UGG": "Trp",
    "CGU": "Arg",
    "CGC": "Arg",
    "CGA": "Arg",
    "CGG": "Arg",
    "AGU": "Ser",
    "AGC": "Ser",
    "AGA": "Arg",
    "AGG": "Arg",
    "GGU": "Gly",
    "GGC": "Gly",
    "GGA": "Gly",
    "GGG": "Gly",
}

STOP_CODONS = ("UAA", "UAG", "UGA")
START_CODON = "AUG"


# --------------------------
# Fold_6: Zeckendorf digits and window truncation
# --------------------------

WEIGHTS_6 = (1, 2, 3, 5, 8, 13)  # F2..F7

BOUNDARY_WORDS = {
    "100001",
    "100101",
    "101001",
}

BOUNDARY_INT_SET = {14, 17, 19, 48, 51, 53}


def fib_weights_up_to(n: int) -> list[int]:
    """
    Fibonacci weights for Zeckendorf coding:
      [F2, F3, ...] with F2=1, F3=2, and each next is sum of previous two.
    """
    if n < 0:
        raise ValueError("n must be nonnegative")
    weights = [1, 2]
    while weights[-1] <= n:
        weights.append(weights[-1] + weights[-2])
    if n > 0:
        weights.pop()  # last is > n
    return weights


def zeckendorf_digits(n: int) -> list[int]:
    """
    Greedy Zeckendorf digits for n in Fibonacci weights [F2,F3,...].
    Returns a digit list aligned with those weights (same length).
    """
    if n < 0:
        raise ValueError("n must be nonnegative")
    if n == 0:
        return []

    weights = fib_weights_up_to(n)
    digits = [0] * len(weights)
    k = len(weights) - 1
    r = n
    while r > 0 and k >= 0:
        if weights[k] <= r:
            digits[k] = 1
            r -= weights[k]
            k -= 2  # enforce no adjacent ones
        else:
            k -= 1

    # sanity
    if sum(digits[i] * weights[i] for i in range(len(weights))) != n:
        raise AssertionError("Zeckendorf reconstruction failed.")
    for i in range(len(digits) - 1):
        if digits[i] == 1 and digits[i + 1] == 1:
            raise AssertionError("Adjacent ones in Zeckendorf digits.")

    return digits


def fold6(n: int) -> str:
    """
    Fold_6(n): first 6 Zeckendorf digits (c1..c6), padded by zeros.
    Output is a 6-character string in {'0','1'} with no substring '11'.
    """
    digits = zeckendorf_digits(n)
    digits = digits + [0] * (6 - len(digits))
    d6 = digits[:6]
    s = "".join("1" if b else "0" for b in d6)
    if "11" in s:
        raise AssertionError("Fold_6 output violated admissibility.")
    return s


def fib_weights_first(m: int) -> list[int]:
    """
    Return the first m Fibonacci weights used in Zeckendorf coding:
      [F2, F3, ..., F_{m+1}] with F2=1, F3=2.
    """
    if m <= 0:
        raise ValueError("m must be positive")
    if m == 1:
        return [1]
    weights = [1, 2]
    while len(weights) < m:
        weights.append(weights[-1] + weights[-2])
    return weights[:m]


def is_admissible_word(w: str) -> bool:
    """
    Golden-mean admissibility: no consecutive ones.
    """
    return "11" not in w


def fold_m(n: int, m: int) -> str:
    """
    Fold_m(n): first m Zeckendorf digits (c1..cm), padded by zeros.
    Output is a length-m word in {'0','1'} with no substring '11'.
    """
    if m <= 0:
        raise ValueError("m must be positive")
    digits = zeckendorf_digits(n)
    if len(digits) < m:
        digits = digits + [0] * (m - len(digits))
    dm = digits[:m]
    s = "".join("1" if b else "0" for b in dm)
    if "11" in s:
        raise AssertionError("Fold_m output violated admissibility.")
    return s


def zeckendorf_value_word(w: str) -> int:
    """
    Value V(w) under Fibonacci weights [F2..] aligned with the digits in w.
    Supports any length (including 0).
    """
    if not w:
        return 0
    weights = fib_weights_first(len(w))
    return sum(int(w[i]) * weights[i] for i in range(len(w)))


def zeckendorf_value_m(w: str) -> int:
    """
    Back-compat alias for zeckendorf_value_word(w).
    """
    return zeckendorf_value_word(w)


def is_boundary_word(w: str) -> bool:
    """
    Boundary words are admissible words with a cyclic boundary defect:
      w_1 = w_m = 1.
    """
    if len(w) < 2:
        return False
    if not is_admissible_word(w):
        return False
    return w[0] == "1" and w[-1] == "1"


def x_m(m: int) -> list[str]:
    """
    Enumerate the admissible set X_m: binary words of length m with no consecutive ones.
    """
    if m < 0:
        raise ValueError("m must be nonnegative")
    if m == 0:
        return [""]
    words = ["0", "1"]
    for _ in range(1, m):
        nxt: list[str] = []
        for w in words:
            nxt.append(w + "0")
            if not w.endswith("1"):
                nxt.append(w + "1")
        words = nxt
    # Deterministic order for reproducibility.
    words.sort()
    # Sanity check.
    if any(not is_admissible_word(w) or len(w) != m for w in words):
        raise AssertionError("X_m enumeration produced invalid words.")
    return words


def boundary_words_m(m: int) -> set[str]:
    """
    Boundary subset of X_m: admissible words with first and last bit 1.
    """
    return {w for w in x_m(m) if is_boundary_word(w)}


def zeckendorf_value(w: str) -> int:
    if len(w) != 6:
        raise ValueError("w must be a length-6 binary word")
    return sum(int(w[i]) * WEIGHTS_6[i] for i in range(6))


# --------------------------
# Encoding layer
# --------------------------

BASES = ("A", "C", "G", "U")
BITPAIRS = ("00", "01", "10", "11")


def all_encodings() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for perm in itertools.permutations(BITPAIRS):
        out.append(dict(zip(BASES, perm)))
    return out


def codon_bits(codon: str, mu: dict[str, str]) -> str:
    return "".join(mu[b] for b in codon)


def codon_index(codon: str, mu: dict[str, str]) -> int:
    return int(codon_bits(codon, mu), 2)


@dataclass(frozen=True)
class CodonFold:
    codon: str
    aa: str
    bits: str
    n: int
    w: str
    v: int
    delta: int
    is_boundary: bool


def fold_codon(codon: str, mu: dict[str, str]) -> CodonFold:
    codon = codon.upper().replace("T", "U")
    if len(codon) != 3 or any(b not in mu for b in codon):
        raise ValueError(f"Invalid codon: {codon!r}")
    aa = GENETIC_CODE.get(codon)
    if aa is None:
        raise ValueError(f"Unknown codon (not in standard code): {codon!r}")
    bits = codon_bits(codon, mu)
    n = int(bits, 2)
    w = fold6(n)
    v = zeckendorf_value(w)
    delta = n - v
    return CodonFold(
        codon=codon,
        aa=aa,
        bits=bits,
        n=n,
        w=w,
        v=v,
        delta=delta,
        is_boundary=(w in BOUNDARY_WORDS),
    )


@dataclass(frozen=True)
class CodonFoldM:
    codon: str
    aa: str
    bits: str
    n: int
    w: str
    v: int
    delta: int
    is_boundary: bool
    m: int


def fold_codon_m(codon: str, mu: dict[str, str], m: int) -> CodonFoldM:
    """
    Fold a codon under the m-digit Zeckendorf window (resolution m).
    Keeps the same two-bit encoding mu; only the folding window changes.
    """
    if m <= 0:
        raise ValueError("m must be positive")
    codon = codon.upper().replace("T", "U")
    if len(codon) != 3 or any(b not in mu for b in codon):
        raise ValueError(f"Invalid codon: {codon!r}")
    aa = GENETIC_CODE.get(codon)
    if aa is None:
        raise ValueError(f"Unknown codon (not in standard code): {codon!r}")
    bits = codon_bits(codon, mu)
    n = int(bits, 2)
    w = fold_m(n, m)
    v = zeckendorf_value_word(w)
    delta = n - v
    return CodonFoldM(
        codon=codon,
        aa=aa,
        bits=bits,
        n=n,
        w=w,
        v=int(v),
        delta=int(delta),
        is_boundary=is_boundary_word(w),
        m=int(m),
    )


def mutual_information_bits(mu: dict[str, str]) -> float:
    """
    Mutual information I(Gen(C); Fold6(Code_mu(C))) under uniform codon prior.
    Output is in bits.
    """
    joint: dict[tuple[str, str], int] = defaultdict(int)  # (fold_word, aa) -> count
    x_count: Counter[str] = Counter()
    y_count: Counter[str] = Counter()

    for codon, aa in GENETIC_CODE.items():
        f = fold_codon(codon, mu)
        x = f.w
        y = aa
        joint[(x, y)] += 1
        x_count[x] += 1
        y_count[y] += 1

    mi = 0.0
    for (x, y), c in joint.items():
        pxy = c / 64.0
        px = x_count[x] / 64.0
        py = y_count[y] / 64.0
        mi += pxy * math.log2(pxy / (px * py))
    return mi


def satisfies_start_stop_boundary_homology(mu: dict[str, str]) -> bool:
    a = fold_codon("AUG", mu)
    b = fold_codon("UAA", mu)
    return (a.w == b.w) and (a.w in BOUNDARY_WORDS)


def find_start_stop_homology_encodings() -> list[dict[str, str]]:
    hits = []
    for mu in all_encodings():
        if satisfies_start_stop_boundary_homology(mu):
            hits.append(mu)
    return hits


def encoding_to_str(mu: dict[str, str]) -> str:
    return f"A={mu['A']}, C={mu['C']}, G={mu['G']}, U={mu['U']}"


# --------------------------
# Hydrophobicity (Kyte--Doolittle) and correlation utilities
# --------------------------

KYTE_DOOLITTLE: dict[str, float] = {
    "Ala": 1.8,
    "Arg": -4.5,
    "Asn": -3.5,
    "Asp": -3.5,
    "Cys": 2.5,
    "Gln": -3.5,
    "Glu": -3.5,
    "Gly": -0.4,
    "His": -3.2,
    "Ile": 4.5,
    "Leu": 3.8,
    "Lys": -3.9,
    "Met": 1.9,
    "Phe": 2.8,
    "Pro": -1.6,
    "Ser": -0.8,
    "Thr": -0.7,
    "Trp": -0.9,
    "Tyr": -1.3,
    "Val": 4.2,
}


# Standard molecular weights (free amino acids, g/mol).
# These values are commonly tabulated; they are used here only for exploratory correlation tests.
AMINO_ACID_MASS: dict[str, float] = {
    "Ala": 89.09,
    "Arg": 174.20,
    "Asn": 132.12,
    "Asp": 133.10,
    "Cys": 121.16,
    "Gln": 146.15,
    "Glu": 147.13,
    "Gly": 75.07,
    "His": 155.16,
    "Ile": 131.17,
    "Leu": 131.17,
    "Lys": 146.19,
    "Met": 149.21,
    "Phe": 165.19,
    "Pro": 115.13,
    "Ser": 105.09,
    "Thr": 119.12,
    "Trp": 204.23,
    "Tyr": 181.19,
    "Val": 117.15,
}


def pearson_r(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("xs and ys must have same length >= 2")
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    if sxx <= 0 or syy <= 0:
        raise ValueError("Zero variance in input")
    return sxy / math.sqrt(sxx * syy)


def linear_regression(xs: list[float], ys: list[float]) -> dict[str, float]:
    """
    Ordinary least squares (OLS) for y = intercept + slope * x.

    Returns:
      slope, intercept, r, r2, se_slope, se_intercept, t_slope, p_slope, n.
    """
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("xs and ys must have same length >= 3")

    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    if sxx <= 0:
        raise ValueError("Zero variance in xs")

    slope = sxy / sxx
    intercept = my - slope * mx

    # Residuals / R^2
    sse = 0.0
    for i in range(n):
        yhat = intercept + slope * xs[i]
        sse += (ys[i] - yhat) ** 2
    r2 = 1.0 - (sse / syy) if syy > 0 else 0.0
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else 0.0

    # Standard errors (n-2 degrees of freedom)
    df = n - 2
    if df <= 0:
        raise ValueError("Need at least 3 points for regression")
    s = math.sqrt(sse / df)
    se_slope = s / math.sqrt(sxx)
    se_intercept = s * math.sqrt(1.0 / n + (mx * mx) / sxx)

    t_slope = slope / se_slope if se_slope > 0 else float("inf")
    p_slope = 2.0 * (1.0 - student_t_cdf(abs(t_slope), df=df))
    p_slope = max(0.0, min(1.0, p_slope))

    return {
        "slope": slope,
        "intercept": intercept,
        "r": r,
        "r2": r2,
        "se_slope": se_slope,
        "se_intercept": se_intercept,
        "t_slope": t_slope,
        "p_slope": p_slope,
        "n": float(n),
    }


def _betacf(a: float, b: float, x: float) -> float:
    """
    Continued fraction for incomplete beta (Numerical Recipes style).
    """
    max_iter = 200
    eps = 3e-14
    fpmin = 1e-300

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0

    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < eps:
            break

    return h


def regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """
    Regularized incomplete beta I_x(a,b).
    """
    if not (0.0 <= x <= 1.0):
        raise ValueError("x must be in [0,1]")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0

    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    bt = math.exp(a * math.log(x) + b * math.log(1.0 - x) - ln_beta)

    # Use symmetry for better convergence.
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(t: float, df: int) -> float:
    """
    CDF of Student's t distribution with df degrees of freedom.
    """
    if df <= 0:
        raise ValueError("df must be positive")
    x = df / (df + t * t)
    a = df / 2.0
    b = 0.5
    ib = regularized_incomplete_beta(a, b, x)
    if t >= 0:
        return 1.0 - 0.5 * ib
    return 0.5 * ib


def pearson_p_value_two_sided(r: float, n: int) -> float:
    """
    Two-sided p-value for Pearson correlation under t-test with df=n-2.
    """
    if n < 3:
        raise ValueError("n must be >= 3")
    if abs(r) >= 1.0:
        return 0.0
    df = n - 2
    t = abs(r) * math.sqrt(df / (1.0 - r * r))
    p = 2.0 * (1.0 - student_t_cdf(t, df=df))
    return max(0.0, min(1.0, p))


def ranks(values: list[float]) -> list[float]:
    """
    Average ranks for ties (1-based ranks).
    """
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = 0.5 * (i + 1 + j + 1)
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman_rho(xs: list[float], ys: list[float]) -> float:
    rx = ranks(xs)
    ry = ranks(ys)
    return pearson_r(rx, ry)


def amino_acid_codons() -> dict[str, list[str]]:
    """
    Return AA -> sorted list of codons (including 'Stop').
    """
    out: dict[str, list[str]] = defaultdict(list)
    for codon, aa in GENETIC_CODE.items():
        out[aa].append(codon)
    for aa in out:
        out[aa].sort()
    return dict(out)


def amino_acid_spectrum(mu: dict[str, str]) -> dict[str, dict[str, object]]:
    """
    For each amino acid, compute spectrum summary:
      V_set, V_min, V_max, N_max.
    """
    codons_by_aa = amino_acid_codons()
    out: dict[str, dict[str, object]] = {}
    for aa, codons in codons_by_aa.items():
        vs: list[int] = []
        ns: list[int] = []
        for codon in codons:
            f = fold_codon(codon, mu)
            vs.append(f.v)
            ns.append(f.n)
        out[aa] = {
            "V_set": sorted(set(vs)),
            "V_min": min(vs),
            "V_max": max(vs),
            "N_max": max(ns),
            "codons": list(codons),
        }
    return out


def hydrophobicity_correlation_under_mu(mu: dict[str, str]) -> dict[str, float]:
    """
    Compute correlation between N_max(AA) and Kyte-Doolittle index over 20 AA.
    Returns Pearson r, Pearson p (two-sided), Spearman rho, Spearman p (two-sided, t-approx).
    """
    spec = amino_acid_spectrum(mu)
    aas = sorted([aa for aa in spec.keys() if aa != "Stop"])
    xs: list[float] = []
    ys: list[float] = []
    for aa in aas:
        if aa not in KYTE_DOOLITTLE:
            raise KeyError(f"Missing Kyte-Doolittle index for {aa}")
        xs.append(float(spec[aa]["N_max"]))
        ys.append(float(KYTE_DOOLITTLE[aa]))

    r = pearson_r(xs, ys)
    p = pearson_p_value_two_sided(r, n=len(xs))

    rho = spearman_rho(xs, ys)
    p_rho = pearson_p_value_two_sided(rho, n=len(xs))

    reg = linear_regression(xs, ys)

    out = {
        "pearson_r": r,
        "pearson_p": p,
        "spearman_rho": rho,
        "spearman_p": p_rho,
        "n": float(len(xs)),
    }
    out.update({f"reg_{k}": float(v) for k, v in reg.items()})
    return out


def amino_acid_vmean(mu: dict[str, str]) -> dict[str, float]:
    """
    Uniform-codon average of V for each amino acid (excluding Stop):
      V_mean(AA) := average_{codons coding AA} V(codon).
    """
    codons_by_aa = amino_acid_codons()
    out: dict[str, float] = {}
    for aa, codons in codons_by_aa.items():
        if aa == "Stop":
            continue
        vs: list[int] = []
        for codon in codons:
            vs.append(fold_codon(codon, mu).v)
        out[aa] = sum(vs) / float(len(vs))
    return out


def vmean_property_correlation_under_mu(
    mu: dict[str, str],
    *,
    prop: dict[str, float],
    prop_name: str,
) -> dict[str, float]:
    """
    Correlate V_mean(AA) with an external amino-acid property over 20 AA.
    Returns Pearson r/p and Spearman rho/p (t-approx).
    """
    vmean = amino_acid_vmean(mu)
    aas = sorted(vmean.keys())
    xs: list[float] = []
    ys: list[float] = []
    for aa in aas:
        if aa not in prop:
            raise KeyError(f"Missing {prop_name} value for {aa}")
        xs.append(float(vmean[aa]))
        ys.append(float(prop[aa]))

    r = pearson_r(xs, ys)
    p = pearson_p_value_two_sided(r, n=len(xs))

    rho = spearman_rho(xs, ys)
    p_rho = pearson_p_value_two_sided(rho, n=len(xs))

    reg = linear_regression(xs, ys)

    out = {
        "pearson_r": r,
        "pearson_p": p,
        "spearman_rho": rho,
        "spearman_p": p_rho,
        "n": float(len(xs)),
    }
    out.update({f"reg_{k}": float(v) for k, v in reg.items()})
    return out


def vmean_hydrophobicity_correlation_under_mu(mu: dict[str, str]) -> dict[str, float]:
    return vmean_property_correlation_under_mu(mu, prop=KYTE_DOOLITTLE, prop_name="Kyte-Doolittle index")


def vmean_mass_correlation_under_mu(mu: dict[str, str]) -> dict[str, float]:
    return vmean_property_correlation_under_mu(mu, prop=AMINO_ACID_MASS, prop_name="amino-acid mass")


# --------------------------
# FASTA / sequence utilities
# --------------------------


def normalize_sequence(seq: str) -> str:
    """
    Uppercase, convert DNA to RNA (T->U).

    Keep A/C/G/U as-is; map other alphabetic IUPAC symbols to 'N' to preserve length
    without shifting reading frames. Non-alphabetic characters are dropped.
    """
    seq = seq.upper().replace("T", "U")
    out: list[str] = []
    for ch in seq:
        if ch in "ACGU":
            out.append(ch)
        elif ch.isalpha():
            out.append("N")
    return "".join(out)


def iter_fasta(path: str) -> Iterator[tuple[str, str]]:
    """
    Yield (record_id, sequence) from a FASTA file.
    """
    rid = None
    chunks: list[str] = []
    p = Path(path)
    if p.suffix == ".gz":
        fobj = gzip.open(p, "rt", encoding="utf-8", newline="")
    else:
        fobj = open(p, "r", encoding="utf-8", newline="")
    with fobj as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if rid is not None:
                    yield rid, normalize_sequence("".join(chunks))
                rid = line[1:].split()[0] or "record"
                chunks = []
            else:
                chunks.append(line)
    if rid is not None:
        yield rid, normalize_sequence("".join(chunks))


def codon_stream(seq: str, frame: int = 0) -> Iterator[tuple[int, str]]:
    """
    Yield (base_pos, codon) for a normalized RNA sequence in a given frame (0,1,2).
    base_pos is 0-based index in the normalized sequence.
    """
    if frame not in (0, 1, 2):
        raise ValueError("frame must be 0, 1, or 2")
    for i in range(frame, len(seq) - 2, 3):
        yield i, seq[i : i + 3]


def find_orfs(seq: str, frame: int = 0, min_codons: int = 0) -> list[tuple[int, int]]:
    """
    Find ORFs in a normalized RNA sequence in a fixed frame.
    Returns list of (start_base_pos, stop_base_pos_inclusive) in base coordinates,
    where stop_base_pos_inclusive is the first base of the stop codon.
    """
    starts: list[int] = []
    orfs: list[tuple[int, int]] = []
    in_orf = False
    start_pos = None

    for pos, codon in codon_stream(seq, frame=frame):
        if any(b not in "ACGU" for b in codon):
            # Ambiguous base: break any in-progress ORF and continue scanning.
            in_orf = False
            start_pos = None
            continue
        if not in_orf:
            if codon == START_CODON:
                in_orf = True
                start_pos = pos
        else:
            if codon in STOP_CODONS:
                if start_pos is not None:
                    length_codons = (pos - start_pos) // 3 + 1
                    if length_codons >= min_codons:
                        orfs.append((start_pos, pos))
                in_orf = False
                start_pos = None

    return orfs


def sequence_spectrum_rows(
    seq: str,
    mu: dict[str, str],
    frame: int = 0,
    start_base: int = 0,
    end_base_exclusive: int | None = None,
) -> list[dict[str, object]]:
    """
    Return per-codon rows with spectrum data.
    """
    seq = normalize_sequence(seq)
    if end_base_exclusive is None:
        end_base_exclusive = len(seq)
    out: list[dict[str, object]] = []
    codon_idx = 0
    for pos, codon in codon_stream(seq, frame=frame):
        if pos < start_base:
            continue
        if pos + 3 > end_base_exclusive:
            break
        if codon not in GENETIC_CODE:
            codon_idx += 1
            continue
        f = fold_codon(codon, mu)
        out.append(
            {
                "codon_index": codon_idx,
                "base_pos": pos,
                "codon": codon,
                "aa": f.aa,
                "bits": f.bits,
                "N": f.n,
                "Fold6": f.w,
                "V": f.v,
                "Delta": f.delta,
                "is_boundary": int(f.is_boundary),
                "is_start": int(codon == START_CODON),
                "is_stop": int(codon in STOP_CODONS),
            }
        )
        codon_idx += 1
    return out


