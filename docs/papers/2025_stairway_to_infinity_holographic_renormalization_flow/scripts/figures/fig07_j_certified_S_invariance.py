from __future__ import annotations

from pathlib import Path


ZETA3 = 1.2020569031595942854
ZETA5 = 1.0369277551433699263


def _sigma_k(n: int, k: int) -> int:
    import math

    s = 0
    r = int(math.isqrt(n))
    for d in range(1, r + 1):
        if n % d == 0:
            s += d**k
            e = n // d
            if e != d:
                s += e**k
    return s


def _e4_coeffs(n_max: int) -> list[int]:
    a = [0] * (n_max + 1)
    a[0] = 1
    for n in range(1, n_max + 1):
        a[n] = 240 * _sigma_k(n, 3)
    return a


def _e6_coeffs(n_max: int) -> list[int]:
    a = [0] * (n_max + 1)
    a[0] = 1
    for n in range(1, n_max + 1):
        a[n] = -504 * _sigma_k(n, 5)
    return a


def _qseries_eval(coeffs: list[int], q: complex) -> complex:
    s = 0.0 + 0.0j
    qp = 1.0 + 0.0j
    for c in coeffs:
        s += c * qp
        qp *= q
    return s


def _j_invariant(tau: complex, n_terms: int) -> complex:
    import cmath
    import math

    q = cmath.exp(2j * math.pi * tau)
    e4 = _qseries_eval(_e4_coeffs(n_terms), q)
    e6 = _qseries_eval(_e6_coeffs(n_terms), q)
    return 1728.0 * (e4**3) / (e4**3 - e6**2)


def _tail_sum_power(r: float, k: int, n0: int) -> float:
    s = 0.0
    n = n0 + 1
    for _ in range(500_000):
        term = (n**k) * (r**n)
        s += term
        if term < 1e-20:
            break
        n += 1
    return s


def _j_truncation_bound(tau: complex, n_terms: int) -> float:
    import cmath
    import math

    q = cmath.exp(2j * math.pi * tau)
    r = abs(q)

    e4n = _qseries_eval(_e4_coeffs(n_terms), q)
    e6n = _qseries_eval(_e6_coeffs(n_terms), q)

    eps4 = 240.0 * ZETA3 * _tail_sum_power(r, 3, n_terms)
    eps6 = 504.0 * ZETA5 * _tail_sum_power(r, 5, n_terms)

    m4 = abs(e4n) + eps4
    m6 = abs(e6n) + eps6

    dn = e4n**3 - e6n**2
    delta_d = 3.0 * (m4**2) * eps4 + 2.0 * m6 * eps6
    d_min = abs(dn) - delta_d
    if d_min <= 0.0:
        return float("inf")

    delta_e4cube = 3.0 * (m4**2) * eps4
    inv_diff = delta_d / (d_min * abs(dn))

    return 1728.0 * (delta_e4cube / d_min + abs(e4n**3) * inv_diff)


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt

    tau = 0.3 + 0.2j
    n_list = [20, 30, 40]

    diffs: list[float] = []
    bounds: list[float] = []

    for n_terms in n_list:
        j1 = _j_invariant(tau, n_terms)
        j2 = _j_invariant(-1.0 / tau, n_terms)
        diff = abs(j1 - j2)
        b1 = _j_truncation_bound(tau, n_terms)
        b2 = _j_truncation_bound(-1.0 / tau, n_terms)
        diffs.append(diff)
        bounds.append(b1 + b2)

    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    ax.semilogy(n_list, diffs, marker="o", label=r"$|j^{(N)}(\tau)-j^{(N)}(-1/\tau)|$")
    ax.semilogy(n_list, bounds, marker="s", linestyle="--", label=r"certified bound $B(\tau)+B(-1/\tau)$")
    ax.set_xlabel(r"truncation depth $N$")
    ax.set_ylabel("absolute value")
    ax.set_title(r"Certified $S$-invariance check for $j$ (truncation budget)")
    ax.legend(frameon=False, loc="best")

    out_pdf = out_dir / "fig07_j_certified_S_invariance.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig07_j_certified_S_invariance.png", bbox_inches="tight")
    plt.close(fig)


