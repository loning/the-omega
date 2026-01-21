# -*- coding: utf-8 -*-
"""
HTF-lite detectability audit (finite window; nontrivial error).

Purpose
  Complement the closed-form residue extraction with a genuinely finite-window
  (truncated) Abel-sum proxy that exhibits a nonzero, controlled error.

Model
  Single Fourier mode with an optional amplitude shift:
    f_t = phase0 * (exp(delta) * exp(i theta))^t
  Abel sum (truncated at T):
    S_T(r) = sum_{t=0}^{T-1} r^t f_t
          = phase0 * (1 - q^T) / (1 - q),
    q = r * exp(delta) * exp(i theta).

Residue proxy
  Multiply by (1-q):
    (1-q) S_T(r) = phase0 * (1 - q^T).
  Evaluating near the pole q=1 by taking r = r_* (1-eps) makes q = 1-eps,
  so the proxy error is |phase0| * |1-eps|^T.

Outputs
  - sections/generated/htf_lite_detectability_finite_window_rows.tex
  - sections/generated/htf_lite_detectability_finite_window_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import cmath
import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _fmt_c(z: complex, nd: int = 6) -> str:
    return f"{z.real:.{int(nd)}f}+{z.imag:.{int(nd)}f}i"


def _fmt_sci(x: float) -> str:
    s = f"{float(x):.0e}"
    s = s.replace("e+0", "e").replace("e-0", "e-").replace("e+", "e")
    return s


def _phase0(x0: float, m: int) -> complex:
    return cmath.exp(2.0j * math.pi * float(m) * float(x0))


def main() -> None:
    out = generated_dir()

    # Use the same canonical constants as the other HTF-lite audits.
    alpha = (math.sqrt(5.0) - 1.0) / 2.0
    x0 = 0.123456789

    # Finite family knobs
    m_list = [1, 2, 3]
    delta_list = [0.0, 0.05, 0.10]
    eps_list = [1e-1, 1e-2, 1e-3, 1e-4]
    T_list = [64, 256, 1024, 4096]

    rows: List[str] = []
    for m in m_list:
        theta = 2.0 * math.pi * float(m) * float(alpha)
        lam_unit = cmath.exp(1.0j * theta)
        target = _phase0(x0=x0, m=m)
        for delta in delta_list:
            lam = cmath.exp(float(delta)) * lam_unit
            r_star_abs = math.exp(-float(delta))
            for T in T_list:
                for eps in eps_list:
                    # Take r = r_* (1-eps), so q = r*lam = (1-eps) exactly.
                    q = 1.0 - float(eps)
                    est = target * (1.0 - (q ** int(T)))
                    err = abs(target) * abs(q) ** int(T)
                    rows.append(
                        " & ".join(
                            [
                                str(int(m)),
                                _fmt(delta, nd=2),
                                _fmt(r_star_abs),
                                str(int(T)),
                                _fmt_sci(eps),
                                _fmt_c(est),
                                _fmt_c(target),
                                _fmt(err),
                            ]
                        )
                        + r" \\"
                    )

    rows.append(r"\bottomrule")
    write_lines(out / "htf_lite_detectability_finite_window_rows.tex", rows)

    summary = [
        r"\paragraph{HTF-lite finite-window detectability summary.} \AuditTag "
        + r"This audit records a genuinely finite-window residue proxy for a single resolvent mode. "
        + r"For a truncated Abel sum $S_T(r)=\sum_{t=0}^{T-1} q^t\,\e^{2\pi\iu m x_0}$ with $q=r\,\e^\delta\,\e^{2\pi\iu m\alpha}$, "
        + r"the residue proxy satisfies $(1-q)S_T(r)=\e^{2\pi\iu m x_0}(1-q^T)$. "
        + r"Evaluating at $r=r_\star(1-\epsilon)$ makes $q=1-\epsilon$ and yields an explicit error "
        + r"$|\e^{2\pi\iu m x_0}|\,(1-\epsilon)^T$. "
        + r"Table~\ref{tab:htf_lite_detectability_finite_window_audit} reports this finite-family proxy across bounded $(T,\epsilon)$ choices."
    ]
    write_lines(out / "htf_lite_detectability_finite_window_summary.tex", summary)

    print("Wrote sections/generated/htf_lite_detectability_finite_window_rows.tex")
    print("Wrote sections/generated/htf_lite_detectability_finite_window_summary.tex")


if __name__ == "__main__":
    main()

