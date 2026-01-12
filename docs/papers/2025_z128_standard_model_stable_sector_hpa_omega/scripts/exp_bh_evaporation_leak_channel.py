# -*- coding: utf-8 -*-
"""
BH4: Evaporation/leakage channel summary in the paper's micro/macro objects.

We compute, for an m-sweep, basic information-flow quantities tied to the fixed folding map:
  - |X_m| (stable labels)
  - degeneracy min/max over X_m: g_min, g_max
  - log2|X_m|: coarse record bits per tick (stable label only)
  - m: microstate bits per tick (N in {0,..,2^m-1})
  - H(N|W) in bits under mu_m(w)=g_m(w)/2^m (microstate pushforward)
  - m - log2|X_m|: a minimal coarse-graining gap (bits) between micro and stable label capacities

Outputs (LaTeX fragments):
  - sections/generated/bh_evaporation_rate_rows.tex
  - sections/generated/bh_leak_channel_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import Dict, List

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import all_xm, cached_degeneracy_map


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def main() -> None:
    rows: List[str] = []

    for m in range(6, 17):
        Xm = all_xm(m)
        gm: Dict[str, int] = cached_degeneracy_map(m)
        Xm_card = len(Xm)

        if set(gm.keys()) != set(Xm):
            raise AssertionError("Expected Fold_m degeneracy map keys to match X_m.")

        g_vals = [int(gm[w]) for w in Xm]
        g_min = min(g_vals)
        g_max = max(g_vals)

        log2_X = math.log2(float(Xm_card))

        # H(N|W) = sum_w mu(w) log2 g(w), with mu(w)=g(w)/2^m.
        two_m = float(1 << m)
        H_bits = 0.0
        for w in Xm:
            g = float(gm[w])
            mu = g / two_m
            H_bits += mu * math.log2(g)

        gap_bits = float(m) - log2_X

        rows.append(
            " & ".join(
                [
                    str(m),
                    str(Xm_card),
                    str(g_min),
                    str(g_max),
                    _fmt(log2_X, 6),
                    _fmt(H_bits, 6),
                    _fmt(gap_bits, 6),
                ]
            )
            + r" \\"
        )

    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_evaporation_rate_rows.tex", rows)

    summary_lines = [
        r"\paragraph{BH4 summary (record vs.\ hidden fiber information).} \AuditTag "
        r"At fixed $m$, recording only the stable label $w\in X_m$ exposes at most $\log_2|X_m|$ bits per tick, "
        r"while the microstate index $N\in\{0,\dots,2^m-1\}$ carries $m$ bits per tick. "
        r"The fiber entropy $H(N|W)=\mathbb{E}_{\mu_m}[\log_2 g_m(W)]$ (with $\mu_m(w)=g_m(w)/2^m$) quantifies "
        r"how much micro-information remains hidden inside folding fibers under coarse stable-label readout. "
        r"Any unitarity/recovery claim stated purely at the coarse-record level must therefore specify how "
        r"this hidden fiber information is encoded into externally accessible higher-order record correlations "
        r"or auxiliary record components.",
    ]
    write_lines(generated_dir() / "bh_leak_channel_summary.tex", summary_lines)

    print("Wrote sections/generated/bh_evaporation_rate_rows.tex")
    print("Wrote sections/generated/bh_leak_channel_summary.tex")


if __name__ == "__main__":
    main()

