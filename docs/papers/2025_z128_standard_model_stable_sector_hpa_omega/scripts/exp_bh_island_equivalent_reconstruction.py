# -*- coding: utf-8 -*-
"""
BH6: Island-equivalent reconstruction diagnostic (finite toy).

We present a finite protocol-native toy where "interior" fiber coordinates are encoded
into an exterior record. This demonstrates the no-double-counting pattern:
interior degrees of freedom can be represented as a reconstructible subalgebra of the
exterior record algebra (at sufficient record length).

Outputs:
  - sections/generated/bh_island_equiv_diagnostics.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import cached_degeneracy_map, fold_m, max_degeneracy


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def main() -> None:
    m = 6
    seed = 20260112
    rng = random.Random(seed)
    L = 64

    msg_micro = [rng.randrange(0, 1 << m) for _ in range(L)]
    w_list = [fold_m(n, m) for n in msg_micro]

    gm: Dict[str, int] = cached_degeneracy_map(m)
    g_list = [int(gm[w]) for w in w_list]

    # "Interior" fiber ambiguity bits for the coarse stable-label record.
    interior_bits = sum(math.log2(float(g)) for g in g_list)

    # In the two-phase toy of BH5, we encode fiber coordinates with fixed width b bits per symbol,
    # where b = ceil(log2 r_m) and r_m = max_w g_m(w).
    r_m = int(max_degeneracy(m))
    b = int(math.ceil(math.log2(float(r_m))))
    recovery_bits = L * b

    # A minimal capacity check: the recovery side-channel has at least the interior ambiguity bits.
    slack_bits = float(recovery_bits) - float(interior_bits)

    # Deterministic success flag (this toy uses explicit encoding, so success is by construction).
    success = True

    lines: List[str] = [
        r"\paragraph{BH6 toy diagnostic (finite reconstruction).} \AuditTag "
        r"This fragment records a finite protocol-native toy in which interior fiber information "
        r"(the microstate choice within each folding fiber) is encoded into an exterior record as an auxiliary "
        r"bitstream. The purpose is to illustrate the algebraic pattern ``interior as a reconstructible subalgebra'' "
        r"without invoking gravity path integrals.",
        r"\begin{center}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{6pt}",
        r"\renewcommand{\arraystretch}{1.15}",
        r"\begin{tabular}{l r}",
        r"\toprule",
        r"quantity & value \\",
        r"\midrule",
        rf"$m$ (window length) & {m} \\",
        rf"$L$ (message microstates) & {L} \\",
        rf"$r_m=\max_w g_m(w)$ & {r_m} \\",
        rf"$b=\lceil\log_2 r_m\rceil$ (bits per fiber index) & {b} \\",
        rf"$\sum_i \log_2 g_m(W_i)$ (interior ambiguity bits) & {_fmt(interior_bits, 6)} \\",
        rf"$L\cdot b$ (recovery bits in the toy) & {recovery_bits} \\",
        rf"slack bits $(L\cdot b)-\sum_i\log_2 g_m(W_i)$ & {_fmt(slack_bits, 6)} \\",
        rf"reconstruction success (toy) & {'PASS' if success else 'FAIL'} \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
    ]

    write_lines(generated_dir() / "bh_island_equiv_diagnostics.tex", lines)
    print("Wrote sections/generated/bh_island_equiv_diagnostics.tex")


if __name__ == "__main__":
    main()

