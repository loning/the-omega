#!/usr/bin/env python3
"""
Threshold correlation-mode registry for coupling-unification audits (bounded).

We turn "independent threshold jitter" into a small correlated family to make
look-elsewhere freedom auditable and structured.

We reuse the two-loop gauge-gauge dictionary and the named threshold anchors
from the mass spectrum table, but perturb thresholds only through a declared
correlated mode family.

Writes:
  - sections/generated/coupling_unification_threshold_corr_modes_rows.tex
  - sections/generated/coupling_unification_threshold_corr_modes_summary.tex
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple


def fmt(x: float, nd: int = 3) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(nd)}f}"


def _tex_escape_tt(s: str) -> str:
    return s.replace("_", r"\_")


def _parse_mass_spectrum_rows(tex: str) -> Dict[str, Tuple[float, float, int]]:
    out: Dict[str, Tuple[float, float, int]] = {}
    for raw in tex.splitlines():
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        if "&" not in line or "\\\\" not in line:
            continue
        cols = [c.strip() for c in line.split("&")]
        if len(cols) < 4:
            continue
        key = cols[0].strip().strip("$").strip()
        mu_s = cols[1].strip().strip("$").strip()
        try:
            mu = float(mu_s)
            r_abs = float(cols[2].strip().strip("$"))
            rhat = int(cols[3].strip().strip("$"))
        except Exception:
            continue
        out[key] = (mu, r_abs, rhat)
    return out


def rk4_step(f, r: float, y: Tuple[float, float, float], h: float) -> Tuple[float, float, float]:
    k1 = f(r, y)
    k2 = f(r + 0.5 * h, (y[0] + 0.5 * h * k1[0], y[1] + 0.5 * h * k1[1], y[2] + 0.5 * h * k1[2]))
    k3 = f(r + 0.5 * h, (y[0] + 0.5 * h * k2[0], y[1] + 0.5 * h * k2[1], y[2] + 0.5 * h * k2[2]))
    k4 = f(r + h, (y[0] + h * k3[0], y[1] + h * k3[1], y[2] + h * k3[2]))
    return (
        y[0] + (h / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]),
        y[1] + (h / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1]),
        y[2] + (h / 6.0) * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2]),
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    gen = root / "sections" / "generated"
    gen.mkdir(parents=True, exist_ok=True)

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    logphi = math.log(phi)
    pi = math.pi
    pi2 = pi * pi

    alpha2_inv_0 = 3.0 * pi2
    alpha1_inv_0 = 10.0 * pi2

    b1_full = 41.0 / 6.0
    b2_full = -19.0 / 6.0
    b3_nf6 = -7.0
    b1_H = 1.0 / 6.0
    b2_H = 1.0 / 12.0

    # Two-loop gauge-gauge matrix (dictionary; same conversion convention).
    c2 = 5.0 / 3.0
    c4 = c2 * c2
    b11 = (199.0 / 50.0) * c4
    b12 = (27.0 / 10.0) * c2
    b13 = (44.0 / 5.0) * c2
    b21 = (9.0 / 10.0) * c2
    b22 = 35.0 / 6.0
    b23 = 12.0
    b31 = (11.0 / 10.0) * c2
    b32 = 9.0 / 2.0
    b33 = -26.0
    bij = (
        (b11, b12, b13),
        (b21, b22, b23),
        (b31, b32, b33),
    )

    ms = _parse_mass_spectrum_rows((gen / "mass_spectrum_rows.tex").read_text(encoding="utf-8"))
    rZ_abs = ms["Z"][1]

    def rel_r(key: str) -> float:
        return ms[key][1] - rZ_abs

    rH0 = rel_r("H")
    rt0 = rel_r("t")
    rb0 = rel_r("b")
    rc0 = rel_r("c")
    rs0 = rel_r("s")

    def b3_from_nf(nf: int) -> float:
        return -11.0 + (2.0 / 3.0) * float(nf)

    # Evaluate only the two-loop best-known scheme/n from the baseline audit output style:
    # keep family bounded and interpretable. (Same registry as before.)
    scheme = ("Decouple_QCD_nf", False, True)
    n0 = 10

    # Correlated modes: return (dH, dt, db, dc, ds) as functions of a single signed amplitude a.
    # Amplitude family is bounded.
    amps = [-0.25, 0.0, 0.25]

    def modes(a: float) -> List[Tuple[str, float, float, float, float, float]]:
        return [
            ("none", 0.0, 0.0, 0.0, 0.0, 0.0),
            ("all_shift", a, a, a, a, a),
            ("heavy_quarks_shift", 0.0, a, a, a, a),
            ("top_only_shift", 0.0, a, 0.0, 0.0, 0.0),
            ("higgs_only_shift", a, 0.0, 0.0, 0.0, 0.0),
            ("stratified_heavy", 0.0, 2.0 * a, 1.5 * a, 1.0 * a, 0.5 * a),
        ]

    r_max = 140.0
    dr = 0.25
    grid = [0.0 + dr * k for k in range(int(r_max / dr) + 1)]

    sid, higgs_decouple, qcd_nf = scheme

    def best_for_thresholds(dH: float, dt: float, db: float, dc: float, ds: float) -> Tuple[float, float]:
        alpha3_inv_0 = float(n0) * pi2

        rH = rH0 + float(dH)
        rt = rt0 + float(dt)
        rb = rb0 + float(db)
        rc = rc0 + float(dc)
        rs = rs0 + float(ds)

        qcd_thresholds = sorted([(rs, 3), (rc, 4), (rb, 5), (rt, 6)], key=lambda x: x[0])

        def nf_at(r: float) -> int:
            nf = 2
            for thr, nf_new in qcd_thresholds:
                if r >= thr:
                    nf = nf_new
            return nf

        def b_vec(r: float) -> Tuple[float, float, float]:
            b1 = b1_full
            b2 = b2_full
            b3 = b3_nf6
            if higgs_decouple and r < rH:
                b1 = b1_full - b1_H
                b2 = b2_full - b2_H
            if qcd_nf:
                b3 = -b3_from_nf(nf_at(r))
            return (b1, b2, b3)

        def f(r: float, y: Tuple[float, float, float]) -> Tuple[float, float, float]:
            y1, y2, y3 = y
            if y1 <= 0.0 or y2 <= 0.0 or y3 <= 0.0:
                return (0.0, 0.0, 0.0)
            a1, a2, a3 = 1.0 / y1, 1.0 / y2, 1.0 / y3
            b1, b2, b3 = b_vec(r)
            d1 = -(b1 / (2.0 * pi)) - (1.0 / (8.0 * pi2)) * (bij[0][0] * a1 + bij[0][1] * a2 + bij[0][2] * a3)
            d2 = -(b2 / (2.0 * pi)) - (1.0 / (8.0 * pi2)) * (bij[1][0] * a1 + bij[1][1] * a2 + bij[1][2] * a3)
            d3 = -(b3 / (2.0 * pi)) - (1.0 / (8.0 * pi2)) * (bij[2][0] * a1 + bij[2][1] * a2 + bij[2][2] * a3)
            return (logphi * d1, logphi * d2, logphi * d3)

        y = (alpha1_inv_0, alpha2_inv_0, alpha3_inv_0)
        Emin = None
        r_star = 0.0
        r_prev = 0.0
        for r in grid:
            if r > r_prev:
                y = rk4_step(f, r_prev, y, float(r - r_prev))
                r_prev = r
            e = max(abs(y[0] - y[1]), abs(y[0] - y[2]), abs(y[1] - y[2]))
            if Emin is None or (e, r) < (Emin, r_star):
                Emin = float(e)
                r_star = float(r)
        assert Emin is not None
        return Emin, r_star

    out_rows: List[str] = []
    best = None  # (E, amp, mode, r)
    for a in amps:
        for mode_id, dH, dt, db, dc, ds in modes(float(a)):
            Emin, r_star = best_for_thresholds(dH, dt, db, dc, ds)
            out_rows.append(
                " & ".join(
                    [
                        r"\texttt{" + _tex_escape_tt(mode_id) + "}",
                        fmt(float(a), 3),
                        fmt(float(dH), 3),
                        fmt(float(dt), 3),
                        fmt(float(Emin), 3),
                        fmt(float(r_star), 3),
                    ]
                )
                + r" \\"
            )
            key = (Emin, abs(a), mode_id, r_star)
            if best is None or key < best:
                best = key

    (gen / "coupling_unification_threshold_corr_modes_rows.tex").write_text(
        "\n".join(out_rows) + "\n",
        encoding="utf-8",
    )

    assert best is not None
    best_E, best_abs_a, best_mode, best_r = best
    summary = (
        "\\paragraph{Threshold correlation-mode audit summary (bounded).}\n"
        "\\AuditTag "
        f"We evaluate a bounded correlated threshold-mode family under scheme \\texttt{{{_tex_escape_tt(sid)}}} "
        f"with $n={n0}$ using two-loop gauge-gauge running. "
        "Each mode is parameterized by a single signed amplitude $a\\in\\{-0.25,0,0.25\\}$ in the $r$ coordinate "
        "and yields an optimized mismatch $\\min_r E_\\infty(r)$ and its minimizing $r_\\star$. "
        f"The best row in the declared family achieves $E_\\infty\\approx {fmt(best_E,3)}$ "
        f"at $r_\\star\\approx {fmt(best_r,3)}$ (mode \\texttt{{{_tex_escape_tt(best_mode)}}}, $|a|={fmt(best_abs_a,3)}$).\n"
    )
    (gen / "coupling_unification_threshold_corr_modes_summary.tex").write_text(
        summary,
        encoding="utf-8",
    )

    print("Wrote sections/generated/coupling_unification_threshold_corr_modes_rows.tex")
    print("Wrote sections/generated/coupling_unification_threshold_corr_modes_summary.tex")


if __name__ == "__main__":
    main()

