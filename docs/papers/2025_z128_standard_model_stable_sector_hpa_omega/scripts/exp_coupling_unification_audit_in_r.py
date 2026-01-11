#!/usr/bin/env python3
"""
Coupling unification audit in the r coordinate (bounded family, deterministic).

Writes:
  - sections/generated/coupling_unification_audit_rows.tex
  - sections/generated/coupling_unification_audit_summary.tex

English only (repo rule).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple


def fmt(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"

def _tex_escape_tt(s: str) -> str:
    return s.replace("_", r"\_")


def _parse_mass_spectrum_rows(tex: str) -> Dict[str, Tuple[float, float, int]]:
    """
    Parse lines like:
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


def _piecewise_integral(b_segments: List[Tuple[float, float, float]], r: float) -> float:
    """
    Integrate b(r') dr' from 0 to r for piecewise-constant segments.
    b_segments: list of (r_lo, r_hi, b), assumed to cover the domain.
    """
    if r == 0.0:
        return 0.0
    sign = 1.0
    r0, r1 = 0.0, r
    if r < 0.0:
        sign = -1.0
        r0, r1 = r, 0.0
    acc = 0.0
    for lo, hi, b in b_segments:
        a = max(lo, r0)
        c = min(hi, r1)
        if c > a:
            acc += b * (c - a)
    return sign * acc


def main() -> None:
    root = Path(__file__).resolve().parents[1]  # .../docs/papers/.../ (paper root)
    gen = root / "sections" / "generated"
    gen.mkdir(parents=True, exist_ok=True)

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    logphi = math.log(phi)
    pi = math.pi
    pi2 = pi * pi

    # One-loop SM beta coefficients (as used in appendix 31).
    b1 = 41.0 / 6.0
    b2 = -19.0 / 6.0
    b3_full = -7.0  # nf=6

    # Higgs-doublet contributions (with Q = T3 + Y convention used in the paper).
    b1_H = 1.0 / 6.0
    b2_H = 1.0 / 12.0

    # Anchor at mu_Z, with r=0 at mu_Z.
    alpha2_inv_0 = 3.0 * pi2  # alpha_w^{-1}
    alpha1_inv_0 = 10.0 * pi2  # alpha_Y^{-1} with Q = T3 + Y convention used in the paper

    def r_ij(alpha_i_inv: float, alpha_j_inv: float, bi: float, bj: float) -> float:
        return (2.0 * pi * (alpha_i_inv - alpha_j_inv)) / ((bi - bj) * logphi)

    r12 = r_ij(alpha1_inv_0, alpha2_inv_0, b1, b2)

    rows = []
    best = None  # (Einf, n, r13, r23)

    for n in range(1, 51):
        alpha3_inv_0 = n * pi2
        r13 = r_ij(alpha1_inv_0, alpha3_inv_0, b1, b3_full)
        r23 = r_ij(alpha2_inv_0, alpha3_inv_0, b2, b3_full)
        einf = max(abs(r12 - r13), abs(r12 - r23), abs(r13 - r23))

        if best is None or (einf, n) < (best[0], best[1]):
            best = (einf, n, r13, r23)

        rows.append((n, float(n), r12, r13, r23, einf))

    assert best is not None
    best_einf, best_n, best_r13, best_r23 = best

    # Deterministic compact table: show all n but keep numeric width small.
    # If you want a shorter table later, restrict to a window around the winner.
    row_lines = []
    for n, n_pi2, r12_v, r13_v, r23_v, _einf in rows:
        row_lines.append(
            f"{n} & {fmt(n_pi2, 0)} & {fmt(r12_v)} & {fmt(r13_v)} & {fmt(r23_v)} \\\\"
        )

    (gen / "coupling_unification_audit_rows.tex").write_text(
        "\n".join(row_lines) + "\n",
        encoding="utf-8",
    )

    summary = (
        "\\paragraph{Audit winner (within the declared family).}\n"
        "\\AuditTag "
        f"Within the discrete family $\\alpha_3^{{-1}}(\\mu_Z)=n\\pi^2$ for $1\\le n\\le 50$, "
        f"the lexicographic minimizer of $(E_\\infty,n)$ is $n={best_n}$, "
        f"with $E_\\infty\\approx {fmt(best_einf)}$ and "
        f"intersection points $r_{{12}}\\approx {fmt(r12)}$, "
        f"$r_{{13}}\\approx {fmt(best_r13)}$, $r_{{23}}\\approx {fmt(best_r23)}$.\n"
    )
    (gen / "coupling_unification_audit_summary.tex").write_text(summary, encoding="utf-8")

    # --- Threshold-registry audit (bounded, named thresholds) ---
    ms_path = gen / "mass_spectrum_rows.tex"
    ms = _parse_mass_spectrum_rows(ms_path.read_text(encoding="utf-8"))
    if "Z" not in ms or "H" not in ms or "t" not in ms:
        raise RuntimeError("Missing required anchor rows in sections/generated/mass_spectrum_rows.tex")

    rZ_abs = ms["Z"][1]

    def rel_r(key: str) -> float:
        return ms[key][1] - rZ_abs

    rH = rel_r("H")
    rt = rel_r("t")
    rb = rel_r("b")
    rc = rel_r("c")
    rs = rel_r("s")

    def b3_from_nf(nf: int) -> float:
        return -11.0 + (2.0 / 3.0) * float(nf)

    # Simple named-threshold model for nf (u,d always on; add s,c,b,t at their reference masses).
    qcd_thresholds = sorted([(rs, 3), (rc, 4), (rb, 5), (rt, 6)], key=lambda x: x[0])

    def nf_at(r: float) -> int:
        nf = 2
        for thr, nf_new in qcd_thresholds:
            if r >= thr:
                nf = nf_new
        return nf

    r_min = -40.0
    r_max = 140.0
    cut_points = sorted(set([r_min, rs, rc, rb, rt, rH, r_max]))

    def segments_b3_qcd() -> List[Tuple[float, float, float]]:
        segs: List[Tuple[float, float, float]] = []
        for a, c in zip(cut_points[:-1], cut_points[1:]):
            mid = 0.5 * (a + c)
            segs.append((a, c, b3_from_nf(nf_at(mid))))
        return segs

    seg_b3_qcd = segments_b3_qcd()

    b1_noH = b1 - b1_H
    b2_noH = b2 - b2_H

    def segments_b1(higgs_decouple: bool) -> List[Tuple[float, float, float]]:
        if not higgs_decouple:
            return [(r_min, r_max, b1)]
        return [(r_min, rH, b1_noH), (rH, r_max, b1)]

    def segments_b2(higgs_decouple: bool) -> List[Tuple[float, float, float]]:
        if not higgs_decouple:
            return [(r_min, r_max, b2)]
        return [(r_min, rH, b2_noH), (rH, r_max, b2)]

    registry = [
        ("MSbar_full", False, False),
        ("Decouple_H", True, False),
        ("Decouple_QCD_nf", False, True),
        ("Decouple_QCD_nf_H", True, True),
    ]

    def alpha_inv_at_r(alpha0: float, b_segments: List[Tuple[float, float, float]], r: float) -> float:
        integral_b = _piecewise_integral(b_segments, r)
        return alpha0 - (logphi / (2.0 * pi)) * integral_b

    grid = [0.0 + 0.25 * k for k in range(int(r_max / 0.25) + 1)]

    registry_lines: List[str] = []
    audit_lines: List[str] = []
    best_thr: Tuple[float, str, int, float] | None = None

    for scheme_id, higgs_decouple, qcd_nf in registry:
        scheme_tt = r"\texttt{" + _tex_escape_tt(scheme_id) + "}"
        b1_segs = segments_b1(higgs_decouple)
        b2_segs = segments_b2(higgs_decouple)
        b3_segs = seg_b3_qcd if qcd_nf else [(r_min, r_max, b3_full)]

        registry_lines.append(
            f"{scheme_tt} & "
            f"{'on' if higgs_decouple else 'off'} & "
            f"{'on' if qcd_nf else 'off'} & "
            f"{fmt(rH)} & {fmt(rt)} \\\\"
        )

        scheme_best: Tuple[float, int, float] | None = None  # (Emin, n, r_star)
        for n in range(1, 51):
            alpha3_inv_0 = n * pi2
            Emin: float | None = None
            r_star = 0.0
            for r in grid:
                a1 = alpha_inv_at_r(alpha1_inv_0, b1_segs, r)
                a2 = alpha_inv_at_r(alpha2_inv_0, b2_segs, r)
                a3 = alpha_inv_at_r(alpha3_inv_0, b3_segs, r)
                e = max(abs(a1 - a2), abs(a1 - a3), abs(a2 - a3))
                if Emin is None or (e, r) < (Emin, r_star):
                    Emin = e
                    r_star = r
            assert Emin is not None
            if scheme_best is None or (Emin, n) < (scheme_best[0], scheme_best[1]):
                scheme_best = (Emin, n, r_star)

        assert scheme_best is not None
        Emin_s, n_s, r_s = scheme_best
        audit_lines.append(f"{scheme_tt} & {n_s} & {fmt(r_s)} & {fmt(Emin_s)} \\\\")

        if best_thr is None or (Emin_s, scheme_id, n_s) < (best_thr[0], best_thr[1], best_thr[2]):
            best_thr = (Emin_s, scheme_id, n_s, r_s)

    (gen / "coupling_unification_threshold_registry_rows.tex").write_text(
        "\n".join(registry_lines) + "\n", encoding="utf-8"
    )
    (gen / "coupling_unification_threshold_audit_rows.tex").write_text(
        "\n".join(audit_lines) + "\n", encoding="utf-8"
    )

    assert best_thr is not None
    Emin_b, scheme_b, n_b, r_b = best_thr
    scheme_b_tt = r"\texttt{" + _tex_escape_tt(scheme_b) + "}"
    thr_summary = (
        "\\paragraph{Threshold-registry audit winner (bounded).}\n"
        "\\AuditTag "
        "Within the declared threshold-registry family and the discrete strong-coupling anchor "
        "$\\alpha_3^{-1}(\\mu_Z)=n\\pi^2$ for $1\\le n\\le 50$, "
        f"the winner is scheme {scheme_b_tt} with $n={n_b}$, "
        f"achieving $E_\\infty\\approx {fmt(Emin_b)}$ at $r_\\star\\approx {fmt(r_b)}$.\n"
    )
    (gen / "coupling_unification_threshold_audit_summary.tex").write_text(
        thr_summary, encoding="utf-8"
    )

    print("Wrote sections/generated/coupling_unification_threshold_registry_rows.tex")
    print("Wrote sections/generated/coupling_unification_threshold_audit_rows.tex")
    print("Wrote sections/generated/coupling_unification_threshold_audit_summary.tex")

    print("Wrote sections/generated/coupling_unification_audit_rows.tex")
    print("Wrote sections/generated/coupling_unification_audit_summary.tex")


if __name__ == "__main__":
    main()

