# -*- coding: utf-8 -*-
"""
HTF-lite resolvent identity audit (finite window / finite Fourier kernel family).

Purpose
  Provide a stronger, self-contained, reproducible evidence module showing that
  in a concrete scan model (irrational rotation scan + Fourier kernel family),
  Abel-regularized traces admit an explicit resolvent-mode decomposition.

Key point
  For the rotation scan, the spectral modes lie on the unit circle (|lambda|=1),
  so poles occur only on the boundary |r|=1. This is the finite, auditable
  analogue of the "unit-disk holomorphy vs interior poles" obstruction motif.

Outputs (LaTeX fragments)
  - sections/generated/htf_lite_resolvent_identity_rows.tex
  - sections/generated/htf_lite_resolvent_pole_rows.tex
  - sections/generated/htf_lite_resolvent_identity_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import cmath
import math
from typing import List, Tuple

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


def _abel_partial_sum_complex(a: List[complex], r: float) -> complex:
    rr = float(r)
    s = 0.0 + 0.0j
    p = 1.0
    for v in a:
        s += v * p
        p *= rr
    return s


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _fmt_c(z: complex, nd: int = 6) -> str:
    return f"{z.real:.{int(nd)}f}+{z.imag:.{int(nd)}f}i"


def _resolvent_closed_form(alpha: float, x0: float, m: int, r: float) -> complex:
    """
    For f(x)=exp(2π i m x) and rotation x_t=x0+t alpha, the Abel sum is:
      S(r) = sum_{t>=0} r^t exp(2π i m (x0+t alpha))
           = exp(2π i m x0) / (1 - r exp(2π i m alpha))
    """
    phase0 = cmath.exp(2.0j * math.pi * float(m) * float(x0))
    lam = cmath.exp(2.0j * math.pi * float(m) * float(alpha))
    return phase0 / (1.0 - float(r) * lam)


def _pole_info(alpha: float, m: int, delta: float) -> Tuple[float, float, float]:
    """
    Consider a mode factor 1 / (1 - r * exp(delta) * exp(i theta)),
    theta = 2π m alpha. The pole is at r_* = exp(-delta) * exp(-i theta).
    Return (abs_r, Re(r), Im(r)).
    """
    theta = 2.0 * math.pi * float(m) * float(alpha)
    abs_r = math.exp(-float(delta))
    re = abs_r * math.cos(theta)
    im = -abs_r * math.sin(theta)
    return abs_r, re, im


def main() -> None:
    out_dir = generated_dir()

    alpha = (math.sqrt(5.0) - 1.0) / 2.0
    x0 = 0.123456789

    # Finite family
    m_list = [1, 2, 3]
    r_list = [0.50, 0.80, 0.90, 0.95]
    T = 8192

    orbit = _rotation_orbit(alpha=alpha, x0=x0, T=T)

    rows: List[str] = []
    for m in m_list:
        a = [cmath.exp(2.0j * math.pi * float(m) * float(x)) for x in orbit]
        for r in r_list:
            s_T = _abel_partial_sum_complex(a, r=r)
            s_cf = _resolvent_closed_form(alpha=alpha, x0=x0, m=m, r=r)
            err = abs(s_T - s_cf)
            # Deterministic truncation bound: tail <= r^T / (1-r).
            tail = (float(r) ** float(T)) / (1.0 - float(r))
            rows.append(
                " & ".join(
                    [
                        str(int(m)),
                        str(int(T)),
                        _fmt(r, nd=2),
                        _fmt_c(s_T),
                        _fmt_c(s_cf),
                        _fmt(err),
                        _fmt(tail),
                    ]
                )
                + r" \\"
            )

    rows.append(r"\bottomrule")
    write_lines(out_dir / "htf_lite_resolvent_identity_rows.tex", rows)

    pole_rows: List[str] = []
    delta_list = [0.0, 0.05, 0.10]
    for m in m_list:
        for delta in delta_list:
            abs_r, re, im = _pole_info(alpha=alpha, m=m, delta=delta)
            pole_rows.append(
                " & ".join(
                    [
                        str(int(m)),
                        _fmt(delta, nd=2),
                        _fmt(abs_r),
                        _fmt(re),
                        _fmt(im),
                    ]
                )
                + r" \\"
            )

    pole_rows.append(r"\bottomrule")
    write_lines(out_dir / "htf_lite_resolvent_pole_rows.tex", pole_rows)

    summary = [
        r"\paragraph{HTF-lite resolvent identity audit summary.} \AuditTag "
        + r"For the irrational rotation scan $x_t=x_0+t\alpha$ and the Fourier kernel "
        + r"$f_m(x)=\exp(2\pi i m x)$, the Abel-regularized trace admits an explicit resolvent-mode form "
        + r"$S_m(r)=\sum_{t\ge 0} r^t f_m(x_t)=\exp(2\pi i m x_0)/(1-r\exp(2\pi i m\alpha))$ on $|r|<1$. "
        + r"Table~\ref{tab:htf_lite_resolvent_identity_audit} verifies this identity numerically against a long finite sum "
        + r"with an explicit truncation tail bound. "
        + r"The associated mode eigenvalue has modulus $|\lambda|=1$, so the pole location lies on $|r|=1$ (boundary). "
        + r"Table~\ref{tab:htf_lite_resolvent_pole_audit} shows the pole radius under a hypothetical amplitude shift "
        + r"$\lambda\mapsto \exp(\delta)\lambda$; for $\delta>0$ the pole radius becomes $\exp(-\delta)<1$, "
        + r"illustrating the same interior-pole obstruction motif used in the pole-barrier template (Appendix~\ref{app:trace_pole_barrier_template})."
    ]
    write_lines(out_dir / "htf_lite_resolvent_identity_summary.tex", summary)

    print("Wrote sections/generated/htf_lite_resolvent_identity_rows.tex")
    print("Wrote sections/generated/htf_lite_resolvent_pole_rows.tex")
    print("Wrote sections/generated/htf_lite_resolvent_identity_summary.tex")


if __name__ == "__main__":
    main()

