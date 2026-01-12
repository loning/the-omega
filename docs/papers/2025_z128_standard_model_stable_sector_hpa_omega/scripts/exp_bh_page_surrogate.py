# -*- coding: utf-8 -*-
"""
BH5: Page-curve surrogate in the protocol language.

We generate an audit-only two-phase toy:
  - Phase I: emit only coarse stable labels W_i = Fold_m(N_i)
  - Phase II: emit additional recovery bits that encode fiber coordinates, driving ambiguity to zero

Surrogate quantity:
  U(t) = remaining microstate ambiguity in bits given the emitted record prefix up to tick t.

Outputs:
  - sections/generated/bh_page_surrogate_curve_rows.tex
  - figures/bh_page_surrogate.png  (requires matplotlib)

Only standard library is used for computation; matplotlib is used for plotting.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from common_paths import figures_dir, generated_dir
from common_tex import write_lines
from protocol_kernel import cached_degeneracy_map, fold_m, max_degeneracy


def _pack_bits(x: int, width: int) -> List[int]:
    return [(x >> (width - 1 - i)) & 1 for i in range(width)]


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def main() -> None:
    m = 6
    seed = 20260112
    rng = random.Random(seed)

    # Deterministic message length in microstates (not bits): chosen to be modest for plots.
    L = 64
    msg_micro = [rng.randrange(0, 1 << m) for _ in range(L)]

    gm: Dict[str, int] = cached_degeneracy_map(m)
    # Maximum fiber size r_m controls how many bits are needed to encode a fiber coordinate.
    r_m = int(max_degeneracy(m))
    b = int(math.ceil(math.log2(float(r_m))))

    # Phase I: coarse emission (only stable labels)
    w_list = [fold_m(n, m) for n in msg_micro]
    g_list = [int(gm[w]) for w in w_list]

    # Total coarse ambiguity after Phase I: sum log2 g(w)
    U0 = sum(math.log2(float(g)) for g in g_list)

    # Phase II: recovery bitstream encodes fiber coordinates.
    # In this toy, after k symbols have their fiber coordinates revealed, the corresponding terms drop to 0.
    total_recovery_bits = L * b
    total_ticks = L + total_recovery_bits

    # Sampled table rows at a small fixed set of ticks.
    sample_ticks = sorted(
        set(
            [
                0,
                1,
                L // 4,
                L // 2,
                L,
                L + total_recovery_bits // 4,
                L + total_recovery_bits // 2,
                L + (3 * total_recovery_bits) // 4,
                total_ticks,
            ]
        )
    )

    def U_at_tick(t: int) -> float:
        """
        Remaining ambiguity U(t) in bits after t ticks.
        Convention:
          - ticks 0..L: after t coarse labels are emitted, no fiber coords revealed yet.
          - ticks > L: recovery bits reveal fiber coordinates sequentially.
        """
        if t <= 0:
            return float(U0)
        if t <= L:
            # Still only coarse labels; ambiguity unchanged for revealed labels because fiber coords are not emitted.
            return float(U0)
        # Recovery phase: bits beyond L.
        bits_released = min(total_recovery_bits, t - L)
        symbols_recovered = min(L, bits_released // b)
        # Remove ambiguity contributions for recovered symbols.
        return float(sum(math.log2(float(g)) for g in g_list[symbols_recovered:]))

    # Build full curve for plotting.
    xs = list(range(0, total_ticks + 1))
    ys = [U_at_tick(t) for t in xs]

    # Write sampled LaTeX rows.
    rows: List[str] = []
    for t in sample_ticks:
        phase = "coarse" if t <= L else "recovery"
        U = U_at_tick(t)
        recovered = 1.0 - (U / U0) if U0 > 0 else 1.0
        rows.append(f"{t} & {phase} & {_fmt(U, 6)} & {_fmt(recovered, 6)} \\\\")
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_page_surrogate_curve_rows.tex", rows)

    # Plot (matplotlib required).
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        raise RuntimeError("matplotlib is required to generate figures/bh_page_surrogate.png") from e

    figures_dir().mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.2, 3.8))
    plt.plot(xs, ys, linewidth=2.0)
    plt.axvline(L, linestyle="--", linewidth=1.5)
    plt.title("BH Page surrogate (protocol): remaining ambiguity U(t)")
    plt.xlabel("tick t")
    plt.ylabel("U(t) [bits]")
    plt.tight_layout()
    out_png = figures_dir() / "bh_page_surrogate.png"
    plt.savefig(out_png, dpi=180)
    plt.close()

    print("Wrote sections/generated/bh_page_surrogate_curve_rows.tex")
    print("Wrote figures/bh_page_surrogate.png")


if __name__ == "__main__":
    main()

