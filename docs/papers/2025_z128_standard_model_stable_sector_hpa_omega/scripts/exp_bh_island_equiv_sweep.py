# -*- coding: utf-8 -*-
"""
BH6 audit: island-equivalent reconstruction sweep across modes and m.

We treat the "interior" as fiber information beyond coarse stable labels and report:
  - interior ambiguity bits (sum log2 g_i) for a fixed message
  - recovery feasibility in the queue-equivalent single-stream model (exact recovery flag)
  - record overhead diagnostics (ticks, escape_extra)

Outputs:
  - sections/generated/bh_island_equiv_sweep_rows.tex
  - sections/generated/bh_island_equiv_sweep_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import Dict, List

from common_paths import generated_dir
from common_tex import write_lines

import exp_black_hole_queue_equivalence as bhq


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def _interior_ambiguity_bits(m: int, micro: List[int]) -> float:
    pre = bhq.fiber_preimages(m)
    total = 0.0
    for n in micro:
        w = bhq.fold_m(int(n), m)
        g = float(len(pre[w]))
        if g > 1.0:
            total += math.log2(g)
    return float(total)


def main() -> None:
    base_vacuum_mass = 64
    msg_text = "TICK-INFORMATION"

    # Two m values: anchor m=6 and one higher-m representative (12) in the paper's bounded family.
    m_list = [6, 12]
    modes = ["avoid_delim_esc", "cyclic_only"]

    rows: List[str] = []
    for m in m_list:
        for mode in modes:
            bits = bhq._bits_from_ascii(msg_text)
            allowed, _info = bhq._allowed_set_by_mode(m, mode=mode)
            micro = bhq.bits_to_allowed_micro_indices(bits, allowed=allowed)
            U_in = _interior_ambiguity_bits(m, micro)

            _st, radiation_w, meta = bhq.forward_simulate_single_stream(
                base_vacuum_mass=base_vacuum_mass, m=m, message_micro=micro
            )
            rec_micro = bhq.recover_message_from_single_stream(radiation_w=radiation_w, m=m, meta={})
            rec_bits = bhq.allowed_micro_indices_to_bits(rec_micro, allowed=allowed)
            ok = 1 if bhq._bits_to_ascii(rec_bits) == msg_text else 0

            rows.append(
                " & ".join(
                    [
                        str(int(m)),
                        mode,
                        str(int(meta["L"])),
                        _fmt(U_in, 6),
                        str(int(meta["t"])),
                        str(int(meta["escape_extra"])),
                        str(int(len(radiation_w))),
                        str(int(ok)),
                    ]
                )
                + r" \\"
            )

    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_island_equiv_sweep_rows.tex", rows)

    summary = [
        r"\paragraph{BH6 sweep diagnostic (audit).} \AuditTag "
        r"This fragment reports a finite sweep that treats interior degrees of freedom as folding-fiber information "
        r"beyond coarse stable labels. For each $(m,\\texttt{mode})$, it reports the interior ambiguity proxy "
        r"$\\sum_i\\log_2 g_m(W_i)$ together with whether exact reconstruction from the exterior record succeeds "
        r"in the queue-equivalent single-stream model. This is an audit-level diagnostic of the algebraic pattern "
        r"``interior as reconstructible subalgebra of the exterior record''.",
    ]
    write_lines(generated_dir() / "bh_island_equiv_sweep_summary.tex", summary)

    print("Wrote sections/generated/bh_island_equiv_sweep_rows.tex")
    print("Wrote sections/generated/bh_island_equiv_sweep_summary.tex")


if __name__ == "__main__":
    main()

