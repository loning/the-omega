# -*- coding: utf-8 -*-
"""
Numeric certificate for Proposition: folding as conditional entropy decomposition.

For m=6..16 we compute, using the Fold_m degeneracy map g_m(w)=|Fold_m^{-1}(w)|:
  - mu_m(w) = g_m(w)/2^m, the induced distribution on stable labels,
  - u_m(w) = 1/|X_m|, the uniform distribution on X_m,
  - H(N|W) = E_{mu_m}[log g_m(W)]  (nats),
  - log d_m = log(2^m/|X_m|),
  - D(mu_m || u_m),

and verify the identity:
  H(N|W) = log d_m + D(mu_m || u_m).

Outputs (LaTeX fragment):
  - sections/generated/folding_entropy_decomposition_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import Dict, List

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import all_xm, cached_degeneracy_map


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def _fmt_sci(x: float) -> str:
    if x == 0.0:
        return "0"
    # Keep this in plain text (no \\times), so it can be safely placed outside math mode.
    return f"{x:.3e}"


def main() -> None:
    rows: List[str] = []
    log2 = math.log(2.0)

    for m in range(6, 17):
        gm: Dict[str, int] = cached_degeneracy_map(m)
        Xm = all_xm(m)
        Xm_card = len(Xm)
        if set(gm.keys()) != set(Xm):
            raise AssertionError("Expected gm keys to match X_m.")

        two_m = float(1 << m)

        # log d_m = log(2^m/|X_m|)
        log_d = (m * log2) - math.log(float(Xm_card))

        # H(N|W) = sum_w mu(w) log g(w), with mu(w)=g(w)/2^m
        H = 0.0

        # D(mu||u) = sum_w mu(w) log(mu(w) / (1/|X_m|))
        D = 0.0
        log_Xm = math.log(float(Xm_card))

        for g in gm.values():
            mu = float(g) / two_m
            H += mu * math.log(float(g))
            D += mu * (math.log(mu) + log_Xm)

        diff = H - (log_d + D)

        rows.append(
            f"{m} & {Xm_card} & {_fmt(log_d)} & {_fmt(H)} & {_fmt(D)} & {_fmt_sci(diff)} \\\\"
        )

    rows.append("\\bottomrule")

    out = generated_dir() / "folding_entropy_decomposition_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/folding_entropy_decomposition_rows.tex")


if __name__ == "__main__":
    main()

