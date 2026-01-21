# -*- coding: utf-8 -*-
"""
HTF-lite detectability audit (finite kernel family; residue extraction).

Purpose
  Provide a reproducible finite-family evidence module for a concrete instance of
  the "detectability/noncancellation" gate (H3) in Assumption HTF-lite.

Model
  Use the irrational rotation scan x_t = x0 + t alpha (mod 1) and the Fourier kernel
    f_m(x) = exp(2π i m x).
  The Abel trace has the closed form:
    S_m(r) = exp(2π i m x0) / (1 - r * lambda_m),
    lambda_m = exp(2π i m alpha).

Detectability mechanism (finite, auditable)
  The residue at the pole r_* = 1/lambda_m can be extracted by:
    Res_m = lim_{r->r_*} (1 - r*lambda_m) S_m(r) = exp(2π i m x0).
  For a hypothetical amplitude shift lambda_m -> exp(delta)*lambda_m (delta>0),
  the pole moves inside the unit disk with |r_*|=exp(-delta). The same residue
  extraction works.

Outputs (LaTeX fragments)
  - sections/generated/htf_lite_detectability_rows.tex
  - sections/generated/htf_lite_detectability_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import cmath
import math
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _fmt_c(z: complex, nd: int = 6) -> str:
    return f"{z.real:.{int(nd)}f}+{z.imag:.{int(nd)}f}i"

def _fmt_sci(x: float) -> str:
    # Compact scientific notation like 1e-3 (no plus sign, no leading zeros in exponent)
    s = f"{float(x):.0e}"
    s = s.replace("e+0", "e").replace("e-0", "e-").replace("e+", "e")
    return s


def _lambda_m(alpha: float, m: int, delta: float) -> complex:
    return cmath.exp(float(delta)) * cmath.exp(2.0j * math.pi * float(m) * float(alpha))


def _phase0(x0: float, m: int) -> complex:
    return cmath.exp(2.0j * math.pi * float(m) * float(x0))


def _S_closed(alpha: float, x0: float, m: int, r: complex, delta: float) -> complex:
    lam = _lambda_m(alpha=alpha, m=m, delta=delta)
    return _phase0(x0=x0, m=m) / (1.0 - r * lam)


def _r_star(alpha: float, m: int, delta: float) -> complex:
    lam = _lambda_m(alpha=alpha, m=m, delta=delta)
    return 1.0 / lam


def _residue_estimate(alpha: float, x0: float, m: int, delta: float, eps: float) -> complex:
    """
    Estimate residue by evaluating at r = r_* (1 - eps), i.e. approaching along the radial line.
    """
    rs = _r_star(alpha=alpha, m=m, delta=delta)
    r = rs * (1.0 - float(eps))
    lam = _lambda_m(alpha=alpha, m=m, delta=delta)
    S = _S_closed(alpha=alpha, x0=x0, m=m, r=r, delta=delta)
    return (1.0 - r * lam) * S


def _abs(z: complex) -> float:
    return float(abs(z))


def main() -> None:
    out = generated_dir()

    alpha = (math.sqrt(5.0) - 1.0) / 2.0
    x0 = 0.123456789

    m_list = [1, 2, 3]
    delta_list = [0.0, 0.05, 0.10]
    eps_list = [1e-2, 1e-3, 1e-4]

    rows: List[str] = []
    for m in m_list:
        true_res = _phase0(x0=x0, m=m)
        for delta in delta_list:
            rs = _r_star(alpha=alpha, m=m, delta=delta)
            for eps in eps_list:
                est = _residue_estimate(alpha=alpha, x0=x0, m=m, delta=delta, eps=eps)
                err = _abs(est - true_res)
                rows.append(
                    " & ".join(
                        [
                            str(int(m)),
                            _fmt(delta, nd=2),
                            _fmt(abs(rs)),
                            _fmt_sci(eps),
                            _fmt_c(est),
                            _fmt_c(true_res),
                            _fmt(err),
                        ]
                    )
                    + r" \\"
                )

    rows.append(r"\bottomrule")
    write_lines(out / "htf_lite_detectability_rows.tex", rows)

    summary = [
        r"\paragraph{HTF-lite detectability audit summary.} \AuditTag "
        + r"In the rotation-scan Fourier mode model, the Abel trace has the resolvent form "
        + r"$S_m(r)=\e^{2\pi\iu m x_0}/(1-r\lambda_m)$ with $\lambda_m=\e^{2\pi\iu m\alpha}$, "
        + r"so the residue at the pole $r_\star=1/\lambda_m$ equals $\e^{2\pi\iu m x_0}$. "
        + r"Table~\ref{tab:htf_lite_detectability_audit} reports a finite, deterministic residue estimator "
        + r"evaluated at $r=r_\star(1-\epsilon)$ for a small finite family of $\epsilon$ values, "
        + r"both at $\delta=0$ (boundary pole) and under a hypothetical amplitude shift $\lambda_m\mapsto \e^\delta\lambda_m$ "
        + r"(interior pole radius $|r_\star|=\e^{-\delta}$). "
        + r"This provides a concrete finite-family instance of a detectability gate (H3) in the HTF-lite bridge vocabulary."
    ]
    write_lines(out / "htf_lite_detectability_summary.tex", summary)

    print("Wrote sections/generated/htf_lite_detectability_rows.tex")
    print("Wrote sections/generated/htf_lite_detectability_summary.tex")


if __name__ == "__main__":
    main()

