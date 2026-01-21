#!/usr/bin/env python3
"""
Two-loop coupling-unification audit: bounded missing-sector perturbations (Yukawa/scalar).

We treat the gauge-gauge two-loop dictionary as the baseline (see
exp_coupling_unification_audit_2loop_thresholds.py) and model the omitted two-loop
contributions (Yukawa traces / scalar self-coupling, etc.) as an explicit bounded
additive perturbation family in d(alpha^{-1})/d log(mu).

This keeps the layer semantics intact:
  - we do NOT fit these terms;
  - we register a small discrete family and report sensitivity bands.

Writes (LaTeX fragments):
  - sections/generated/coupling_unification_2loop_yukawa_scalar_audit_rows.tex
  - sections/generated/coupling_unification_2loop_yukawa_scalar_audit_summary.tex
"""

from __future__ import annotations

import math
from fractions import Fraction
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

    # Anchors at mu_Z with r=0 at mu_Z.
    alpha2_inv_0 = 3.0 * pi2  # alpha_w^{-1}
    alpha1_inv_0 = 10.0 * pi2  # fallback: W_Y=10 (three generations)

    # If the joint protocol-state selector is available, derive alpha_Y^{-1} from the selected kernel-closed EW weight.
    try:
        import exp_ew_resolution_weighted_match_family as ewfam
        import protocol_state_selection as psel

        sel = psel.load_selected_state("mu_Z")
        u_to_field = ewfam._build_x6_to_field_map()  # type: ignore[attr-defined]
        t = Fraction(str(sel.kernel.t))
        c = ewfam._candidate(m=int(sel.m), t=t, u_to_field=u_to_field)  # type: ignore[attr-defined]
        alpha1_inv_0 = float(c.W) * pi2
    except Exception:
        pass

    # One-loop SM coefficients (dictionary).
    b1_full = 41.0 / 6.0
    b2_full = -19.0 / 6.0
    b3_nf6 = -7.0

    # Higgs-doublet one-loop contributions for a decoupling convention.
    b1_H = 1.0 / 6.0
    b2_H = 1.0 / 12.0

    # Two-loop gauge-gauge matrix (dictionary; same conversion used in the baseline script).
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
    if "Z" not in ms or "H" not in ms or "t" not in ms:
        raise RuntimeError("Missing required anchor rows in sections/generated/mass_spectrum_rows.tex")
    rZ_abs = ms["Z"][1]

    def rel_r(key: str) -> float:
        return ms[key][1] - rZ_abs

    rH_thr = rel_r("H")
    rt_thr = rel_r("t")
    rb_thr = rel_r("b")
    rc_thr = rel_r("c")
    rs_thr = rel_r("s")

    def b3_from_nf(nf: int) -> float:
        return -11.0 + (2.0 / 3.0) * float(nf)

    registry: List[Tuple[str, bool, bool]] = [
        ("MSbar_full", False, False),
        ("Decouple_H", True, False),
        ("Decouple_QCD_nf", False, True),
        ("Decouple_QCD_nf_H", True, True),
    ]

    # Bounded missing-sector perturbations:
    # dy_i/dlog(mu) gets an additive eta_i. We register eta_i in a small symmetric family.
    # Units: same as dy/dlog(mu) (dimensionless). This is an audit-facing envelope.
    eta_vals = [-0.02, 0.0, 0.02]
    eta_family: List[Tuple[float, float, float]] = [
        (e1, e2, e3) for e1 in eta_vals for e2 in eta_vals for e3 in eta_vals
    ]

    r_max = 140.0
    dr = 0.25
    grid = [0.0 + dr * k for k in range(int(r_max / dr) + 1)]

    def solve_best(
        scheme: Tuple[str, bool, bool],
        n: int,
        eta: Tuple[float, float, float],
    ) -> Tuple[float, float]:
        sid, higgs_decouple, qcd_nf = scheme
        _ = sid
        alpha3_inv_0 = float(n) * pi2

        qcd_thresholds = sorted(
            [(rs_thr, 3), (rc_thr, 4), (rb_thr, 5), (rt_thr, 6)],
            key=lambda x: x[0],
        )

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
            if higgs_decouple and r < rH_thr:
                b1 = b1_full - b1_H
                b2 = b2_full - b2_H
            if qcd_nf:
                b3 = -b3_from_nf(nf_at(r))
            return (b1, b2, b3)

        eta1, eta2, eta3 = eta

        def f(r: float, y: Tuple[float, float, float]) -> Tuple[float, float, float]:
            y1, y2, y3 = y
            if y1 <= 0.0 or y2 <= 0.0 or y3 <= 0.0:
                return (0.0, 0.0, 0.0)
            a1, a2, a3 = 1.0 / y1, 1.0 / y2, 1.0 / y3
            b1, b2, b3 = b_vec(r)
            d1 = (
                -(b1 / (2.0 * pi))
                - (1.0 / (8.0 * pi2)) * (bij[0][0] * a1 + bij[0][1] * a2 + bij[0][2] * a3)
                + eta1
            )
            d2 = (
                -(b2 / (2.0 * pi))
                - (1.0 / (8.0 * pi2)) * (bij[1][0] * a1 + bij[1][1] * a2 + bij[1][2] * a3)
                + eta2
            )
            d3 = (
                -(b3 / (2.0 * pi))
                - (1.0 / (8.0 * pi2)) * (bij[2][0] * a1 + bij[2][1] * a2 + bij[2][2] * a3)
                + eta3
            )
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

    # Choose per-scheme n at eta=(0,0,0) by lexicographic minimization (Emin, n).
    chosen_n: Dict[str, int] = {}
    chosen_r: Dict[str, float] = {}
    chosen_E: Dict[str, float] = {}
    for sid, higgs_decouple, qcd_nf in registry:
        best = None
        for n in range(1, 51):
            Emin, r_star = solve_best((sid, higgs_decouple, qcd_nf), n=n, eta=(0.0, 0.0, 0.0))
            if best is None or (Emin, n, r_star) < (best[0], best[1], best[2]):
                best = (Emin, n, r_star)
        assert best is not None
        Emin0, n0, r0 = best
        chosen_n[sid] = int(n0)
        chosen_r[sid] = float(r0)
        chosen_E[sid] = float(Emin0)

    rows: List[str] = []
    overall_best = None  # (E0, sid, n0)
    for sid, higgs_decouple, qcd_nf in registry:
        n0 = chosen_n[sid]
        r0 = chosen_r[sid]
        E0 = chosen_E[sid]
        if overall_best is None or (E0, sid, n0) < (overall_best[0], overall_best[1], overall_best[2]):
            overall_best = (E0, sid, n0)

        Es: List[float] = []
        rs: List[float] = []
        for eta in eta_family:
            Emin, r_star = solve_best((sid, higgs_decouple, qcd_nf), n=n0, eta=eta)
            Es.append(float(Emin))
            rs.append(float(r_star))

        rows.append(
            " & ".join(
                [
                    r"\texttt{" + _tex_escape_tt(sid) + "}",
                    str(int(n0)),
                    fmt(float(r0), 3),
                    fmt(float(E0), 3),
                    fmt(min(rs), 3),
                    fmt(max(rs), 3),
                    fmt(min(Es), 3),
                    fmt(max(Es), 3),
                ]
            )
            + r" \\"
        )

    (gen / "coupling_unification_2loop_yukawa_scalar_audit_rows.tex").write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )

    assert overall_best is not None
    Ebest, sidbest, nbest = overall_best
    summary = (
        "\\paragraph{Two-loop missing-sector perturbation audit summary (bounded).}\n"
        "\\AuditTag "
        "We extend the two-loop gauge-gauge running audit by modeling the omitted two-loop sectors "
        "(Yukawa traces / scalar contributions) as a bounded additive perturbation family "
        "$\\eta_i\\in\\{-0.02,0,0.02\\}$ in $\\mathrm{d}\\alpha_i^{-1}/\\mathrm{d}\\log\\mu$. "
        "For each named-threshold scheme we select $n$ at $\\eta=0$ by lexicographic minimization of $(\\min_r E_\\infty, n)$ "
        "and report the resulting $(r,E_\\infty)$ bands across the declared perturbation family. "
        f"The best baseline (at $\\eta=0$) among the schemes is \\texttt{{{_tex_escape_tt(sidbest)}}} with $n={int(nbest)}$ "
        f"and $E_\\infty\\approx {fmt(float(Ebest),3)}$.\n"
    )
    (gen / "coupling_unification_2loop_yukawa_scalar_audit_summary.tex").write_text(
        summary,
        encoding="utf-8",
    )

    print("Wrote sections/generated/coupling_unification_2loop_yukawa_scalar_audit_rows.tex")
    print("Wrote sections/generated/coupling_unification_2loop_yukawa_scalar_audit_summary.tex")


if __name__ == "__main__":
    main()

