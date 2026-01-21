#!/usr/bin/env python3
"""
Two-loop coupling-unification audit in the r coordinate with bounded threshold uncertainty.

This script extends the existing one-loop (affine) audit by:
  - Using a standard two-loop gauge-running dictionary (Machacek-Vaughn style),
    expressed in the same Q = T3 + Y normalization used in the paper.
  - Keeping the strong-coupling anchor alpha3^{-1}(mu_Z)=n*pi^2 as a bounded discrete family.
  - Reusing the named threshold registry anchored to the paper's discrete mass-spectrum rows,
    and adding a bounded threshold-location perturbation family to expose uncertainty.

Design goals:
  - Deterministic output (no randomness, fixed grids, fixed tie-breaks).
  - Auditable bounded families (registry + perturbations are explicit).
  - English-only output (repo rule).

Writes (LaTeX fragments):
  - sections/generated/coupling_unification_2loop_threshold_audit_rows.tex
  - sections/generated/coupling_unification_2loop_threshold_audit_summary.tex
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
    """
    Parse rows like:
      $H$ & $125.25$ & 25.788 & 26 & -0.212 & $0.902982$ \\\\
    Returns: key -> (mu_GeV, r_abs, rhat)
    """
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

    # One-loop SM coefficients (tick+CAP-derived in the paper; used here as dictionary).
    b1_full = 41.0 / 6.0
    b2_full = -19.0 / 6.0
    b3_nf6 = -7.0

    # Higgs-doublet one-loop contributions in this normalization (used for a decoupling convention).
    b1_H = 1.0 / 6.0
    b2_H = 1.0 / 12.0

    # Two-loop gauge-gauge coefficients (dictionary input).
    # We take the standard SM matrix in SU(5)-normalized g1 (Machacek-Vaughn form)
    # and convert to the paper's g1 where g1_SU5 = sqrt(5/3) * g1_here.
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

    # Mass-spectrum anchors for threshold locations (relative to mu_Z).
    ms = _parse_mass_spectrum_rows((gen / "mass_spectrum_rows.tex").read_text(encoding="utf-8"))
    if "Z" not in ms or "H" not in ms or "t" not in ms:
        raise RuntimeError("Missing required anchor rows in sections/generated/mass_spectrum_rows.tex")
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

    # Registry: (id, higgs_decouple, qcd_nf_decouple)
    registry: List[Tuple[str, bool, bool]] = [
        ("MSbar_full", False, False),
        ("Decouple_H", True, False),
        ("Decouple_QCD_nf", False, True),
        ("Decouple_QCD_nf_H", True, True),
    ]

    # Bounded threshold-location perturbations (in r units), centered at the discrete anchor depths.
    dr_family = [-0.25, 0.0, 0.25]

    # Integration / search window.
    r_max = 140.0
    dr = 0.25
    grid = [0.0 + dr * k for k in range(int(r_max / dr) + 1)]

    def flow(
        scheme: Tuple[str, bool, bool],
        n: int,
        dH: float,
        dt: float,
        db: float,
        dc: float,
        ds: float,
    ) -> Tuple[float, float]:
        """
        Return (Emin, r_star) for the given bounded scheme + thresholds + alpha3 family choice.
        Objective: minimize E_inf(r) := max_{i<j} |alpha_i^{-1}(r) - alpha_j^{-1}(r)|.
        """
        _sid, higgs_decouple, qcd_nf = scheme
        alpha3_inv_0 = float(n) * pi2

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

        # ODE for inverse couplings y_i := alpha_i^{-1}.
        # dy_i/dlog(mu) = -(b_i)/(2*pi) - (1/(8*pi^2)) sum_j b_ij alpha_j + ...
        # In r: dy_i/dr = (logphi) * dy_i/dlog(mu).
        def f(r: float, y: Tuple[float, float, float]) -> Tuple[float, float, float]:
            y1, y2, y3 = y
            # avoid division by zero; if any coupling crosses 0 inverse, stop by blowing up mismatch.
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
            # advance from r_prev to r (uniform step, deterministic)
            if r > r_prev:
                y = rk4_step(f, r_prev, y, float(r - r_prev))
                r_prev = r
            e = max(abs(y[0] - y[1]), abs(y[0] - y[2]), abs(y[1] - y[2]))
            if Emin is None or (e, r) < (Emin, r_star):
                Emin = float(e)
                r_star = float(r)
        assert Emin is not None
        return (Emin, r_star)

    # Central thresholds (no perturbation): pick per-scheme winner (Emin, n, r_star).
    scheme_winners: Dict[str, Tuple[float, int, float]] = {}
    for sid, higgs_decouple, qcd_nf in registry:
        best = None
        for n in range(1, 51):
            Emin, r_star = flow((sid, higgs_decouple, qcd_nf), n, 0.0, 0.0, 0.0, 0.0, 0.0)
            if best is None or (Emin, n, r_star) < (best[0], best[1], best[2]):
                best = (Emin, n, r_star)
        assert best is not None
        scheme_winners[sid] = best

    # For each scheme, produce a bounded threshold-uncertainty band at the chosen n.
    rows: List[str] = []
    overall_best = None  # (Emin, sid, n, r_star)
    for sid, higgs_decouple, qcd_nf in registry:
        Emin0, n0, r0 = scheme_winners[sid]
        if overall_best is None or (Emin0, sid, n0, r0) < (overall_best[0], overall_best[1], overall_best[2], overall_best[3]):
            overall_best = (Emin0, sid, n0, r0)

        band_E: List[float] = []
        band_r: List[float] = []
        for dH in dr_family:
            for dt in dr_family:
                for db in dr_family:
                    for dc in dr_family:
                        for ds in dr_family:
                            Emin, r_star = flow((sid, higgs_decouple, qcd_nf), int(n0), dH, dt, db, dc, ds)
                            band_E.append(float(Emin))
                            band_r.append(float(r_star))

        band_E_min, band_E_max = min(band_E), max(band_E)
        band_r_min, band_r_max = min(band_r), max(band_r)

        scheme_tt = r"\texttt{" + _tex_escape_tt(sid) + "}"
        rows.append(
            " & ".join(
                [
                    scheme_tt,
                    str(int(n0)),
                    fmt(float(r0), 3),
                    fmt(float(Emin0), 3),
                    fmt(float(band_r_min), 3),
                    fmt(float(band_r_max), 3),
                    fmt(float(band_E_min), 3),
                    fmt(float(band_E_max), 3),
                ]
            )
            + r" \\"
        )

    (gen / "coupling_unification_2loop_threshold_audit_rows.tex").write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )

    assert overall_best is not None
    Emin_best, sid_best, n_best, r_best = overall_best
    sid_best_tt = r"\texttt{" + _tex_escape_tt(sid_best) + "}"
    summary = (
        "\\paragraph{Two-loop + threshold-uncertainty audit summary (bounded).}\n"
        "\\AuditTag "
        "We run a two-loop gauge-running dictionary in the $r$ coordinate under a bounded named-threshold registry, "
        "with a bounded discrete family $\\alpha_3^{-1}(\\mu_Z)=n\\pi^2$ for $1\\le n\\le 50$. "
        f"At the central threshold anchors (no perturbation), the overall winner is scheme {sid_best_tt} "
        f"with $n={int(n_best)}$, achieving $E_\\infty\\approx {fmt(float(Emin_best), 3)}$ at $r_\\star\\approx {fmt(float(r_best), 3)}$. "
        "For each scheme we additionally report a bounded threshold-location perturbation band (step $\\Delta r\\in\\{-0.25,0,0.25\\}$ at $(H,t,b,c,s)$).\n"
    )
    (gen / "coupling_unification_2loop_threshold_audit_summary.tex").write_text(summary, encoding="utf-8")

    print("Wrote sections/generated/coupling_unification_2loop_threshold_audit_rows.tex")
    print("Wrote sections/generated/coupling_unification_2loop_threshold_audit_summary.tex")


if __name__ == "__main__":
    main()

