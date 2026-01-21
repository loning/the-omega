# -*- coding: utf-8 -*-
"""
HTF-lite bridge audit (finite window / finite kernel family).

Goal
  Provide a small, fully deterministic, standard-library-only evidence module
  for the HTF-lite bridge vocabulary recorded in Appendix 59 (operator mother space).

What this audit does (and does not) do
  - It DOES provide:
      (i) a finite kernel family K producing bounded scan readout sequences a_t
          and their Abel generating functions (numeric sanity checks on |r|<1),
      (ii) a small "zero-mode pole radius" table illustrating the interior-pole
          obstruction for hypothetical off-critical modes.
  - It DOES NOT claim:
      (i) the existence of a true HTF bridge identity,
      (ii) detectability/noncancellation for actual zeta zeros (this remains a
          bridge gate, recorded as a failure point when not established).

Outputs (LaTeX fragments)
  - sections/generated/htf_lite_kernel_holomorphy_rows.tex
  - sections/generated/htf_lite_zero_mode_pole_rows.tex
  - sections/generated/htf_lite_bridge_audit_summary.tex
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _wrap01(x: float) -> float:
    y = x - math.floor(x)
    if y >= 1.0:
        y -= 1.0
    if y < 0.0:
        y += 1.0
    return y


def _rotation_orbit(alpha: float, x0: float, T: int) -> List[float]:
    x = float(x0)
    out: List[float] = []
    for _ in range(int(T)):
        out.append(x)
        x = _wrap01(x + alpha)
    return out


def _kernel_cos(m: int, x: float) -> float:
    if m == 0:
        return 1.0
    return math.cos(2.0 * math.pi * float(m) * float(x))


def _abel_partial_sum(a: Sequence[float], r: float) -> float:
    rr = float(r)
    s = 0.0
    p = 1.0
    for v in a:
        s += float(v) * p
        p *= rr
    return float(s)


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _first_zero_imag_list() -> List[float]:
    # A small deterministic list of standard reference values (nontrivial zeros on the critical line).
    # These are used as illustrative constants in an audit-only table.
    return [
        14.134725141734693,
        21.022039638771554,
        25.010857580145688,
    ]


def _pole_location(beta: float, gamma: float) -> Tuple[float, float, float]:
    """
    Return (abs_r, Re(r), Im(r)) for r = exp(-(rho-1/2)) with rho=beta+i gamma.
    """
    abs_r = math.exp(-(float(beta) - 0.5))
    # r = abs_r * exp(-i gamma)
    re = abs_r * math.cos(float(gamma))
    im = -abs_r * math.sin(float(gamma))
    return abs_r, re, im


def _max_abs(xs: Iterable[float]) -> float:
    m = 0.0
    for v in xs:
        m = max(m, abs(float(v)))
    return float(m)


def main() -> None:
    out_dir = generated_dir()

    # Finite window / finite kernel family.
    # Use the golden rotation slope as a canonical bounded-type choice.
    alpha = (math.sqrt(5.0) - 1.0) / 2.0
    x0 = 0.123456789
    T = 4096

    orbit = _rotation_orbit(alpha=alpha, x0=x0, T=T)
    m_list = [0, 1, 2, 3]
    r_list = [0.50, 0.80, 0.95]

    hol_rows: List[str] = []
    for m in m_list:
        a = [_kernel_cos(m=m, x=x) for x in orbit]
        M = _max_abs(a)
        for r in r_list:
            S = _abel_partial_sum(a, r=r)
            bound = M / (1.0 - float(r))
            ratio = abs(S) / bound if bound > 0 else 0.0
            hol_rows.append(
                " & ".join(
                    [
                        str(int(m)),
                        str(int(T)),
                        _fmt(M),
                        _fmt(r, nd=2),
                        _fmt(S),
                        _fmt(bound),
                        _fmt(ratio),
                    ]
                )
                + r" \\"
            )

    hol_rows.append(r"\bottomrule")
    write_lines(out_dir / "htf_lite_kernel_holomorphy_rows.tex", hol_rows)

    # Zero-mode pole table: critical-line vs off-critical hypotheticals.
    gammas = _first_zero_imag_list()
    beta_list = [0.50, 0.55, 0.60]
    pole_rows: List[str] = []
    for gamma in gammas:
        for beta in beta_list:
            abs_r, re, im = _pole_location(beta=beta, gamma=gamma)
            pole_rows.append(
                " & ".join(
                    [
                        _fmt(gamma, nd=6),
                        _fmt(beta, nd=2),
                        _fmt(abs_r),
                        _fmt(re),
                        _fmt(im),
                    ]
                )
                + r" \\"
            )

    pole_rows.append(r"\bottomrule")
    write_lines(out_dir / "htf_lite_zero_mode_pole_rows.tex", pole_rows)

    summary_lines = [
        r"\paragraph{HTF-lite bridge audit summary.} \AuditTag "
        + r"This module provides reproducible, finite-family evidence for two ingredients used in the HTF-lite bridge vocabulary. "
        + r"(i) For a fixed irrational rotation scan and a finite Fourier kernel family $K_m(x)=\cos(2\pi m x)$, "
        + r"the scan readout sequence is bounded and its Abel generating function satisfies the standard unit-disk bound "
        + r"(Appendix~\ref{app:abel_finite_part_notes}, Subsection~\ref{subsec:abel_holomorphy}); "
        + r"Table~\ref{tab:htf_lite_kernel_holomorphy_audit} records a deterministic numeric sanity check. "
        + r"(ii) The mode factor $M_\rho(r)=(1-r\,\e^{(\rho-\frac12)})^{-1}$ has an interior pole whenever $\RePart(\rho)>\tfrac12$ "
        + r"(Appendix~\ref{app:trace_pole_barrier_template}); "
        + r"Table~\ref{tab:htf_lite_zero_mode_pole_audit} lists the corresponding pole radii for a small fixed set of reference $\gamma$ values "
        + r"and hypothetical real parts $\beta$. "
        + r"This audit does not assert the existence of a true trace-bridge identity (HTF); that remains an explicit bridge gate "
        + r"(Assumption~\ref{ass:htf_lite_operator_pack} and failure point IC13)."
    ]
    write_lines(out_dir / "htf_lite_bridge_audit_summary.tex", summary_lines)

    print("Wrote sections/generated/htf_lite_kernel_holomorphy_rows.tex")
    print("Wrote sections/generated/htf_lite_zero_mode_pole_rows.tex")
    print("Wrote sections/generated/htf_lite_bridge_audit_summary.tex")


if __name__ == "__main__":
    main()

