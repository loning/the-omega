# -*- coding: utf-8 -*-
"""
BH5 RB-D audit: robustness of Page-like surrogate shape across (m, mode, seed).

We treat the Page surrogate as the remaining ambiguity U(t) computed from folding fibers under
the queue-equivalent single-stream schedule (CAP-selected).

We sweep:
  - m in {6, 12}
  - absorption mode in {avoid_delim_esc, cyclic_only, unrestricted}
  - seed in a small fixed family

We report:
  - whether exact recovery succeeds (ok)
  - whether U(t) exhibits a Page-like shape (increase then decrease to 0)
  - peak location fraction t*/T (non-vacuum)
  - escape overhead and total ticks

Outputs:
  - sections/generated/bh_page_surrogate_rb_d_rows.tex
  - sections/generated/bh_page_surrogate_rb_d_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines

import exp_black_hole_queue_equivalence as bhq


def _page_like(U: List[float], tol: float = 1e-9) -> Tuple[bool, int]:
    """
    Page-like surrogate criterion:
      - U is nondecreasing up to its first maximizer
      - U is nonincreasing after that maximizer
      - final value is ~0
    Returns (ok, peak_index).
    """
    if not U:
        return (False, 0)
    peak = 0
    best = -1.0
    for i, u in enumerate(U):
        if u > best + tol:
            best = u
            peak = i
    # monotone checks
    for i in range(1, peak + 1):
        if U[i] + tol < U[i - 1]:
            return (False, peak)
    for i in range(peak + 1, len(U)):
        if U[i] > U[i - 1] + tol:
            return (False, peak)
    if abs(U[-1]) > 1e-6:
        return (False, peak)
    return (True, peak)


def _run(m: int, mode: str, seed: int) -> Dict[str, str]:
    base_vacuum_mass = 64
    # Deterministic pseudo-random message text from a fixed seed (ASCII uppercase).
    rng = random.Random(int(seed))
    msg = "".join(chr(ord("A") + rng.randrange(0, 26)) for _ in range(16))
    bits = bhq._bits_from_ascii(msg)
    allowed, _info = bhq._allowed_set_by_mode(m, mode=mode)
    micro = bhq.bits_to_allowed_micro_indices(bits, allowed=allowed)

    _st, radiation_w, meta = bhq.forward_simulate_single_stream(
        base_vacuum_mass=base_vacuum_mass, m=m, message_micro=micro
    )
    rec_micro = bhq.recover_message_from_single_stream(radiation_w=radiation_w, m=m, meta={})
    rec_bits = bhq.allowed_micro_indices_to_bits(rec_micro, allowed=allowed)
    ok = 1 if bhq._bits_to_ascii(rec_bits) == msg else 0

    # Build U(t) over non-vacuum ticks using the internal schedule.
    L = int(meta["L"])
    t = int(meta["t"])
    sched = bhq._interleave_schedule(
        L=L, t=t, scramble_delay=int(meta["scramble_delay"]), exponent=int(meta["exponent"])
    )
    pre = bhq.fiber_preimages(m)
    g_list = [len(pre[bhq.fold_m(n, m)]) for n in micro]
    U_vals: List[float] = []
    p_emit = 0
    r_emit = 0
    for tag in sched:
        if tag == "P":
            p_emit += 1
        else:
            r_emit += 1
        U_vals.append(
            bhq._remaining_ambiguity_bits(
                g_list=g_list,
                A=len(bhq.all_xm(m)),
                t=t,
                payload_emitted=p_emit,
                recovery_emitted=r_emit,
            )
        )
    page_ok, peak_idx = _page_like(U_vals)
    nonvac_len = len(U_vals)
    peak_frac = float(peak_idx + 1) / float(nonvac_len) if nonvac_len > 0 else 0.0

    return {
        "m": str(int(m)),
        "mode": mode,
        "seed": str(int(seed)),
        "ok": str(int(ok)),
        "page_ok": "1" if page_ok else "0",
        "peak_frac": f"{peak_frac:.6f}",
        "t_digits": str(int(meta["t"])),
        "escape_extra": str(int(meta["escape_extra"])),
        "ticks": str(int(len(radiation_w))),
    }


def main() -> None:
    rows: List[str] = []
    m_list = [6, 12]
    modes = ["avoid_delim_esc", "cyclic_only", "unrestricted"]
    seeds = [1, 2, 3, 5, 8]

    for m in m_list:
        for mode in modes:
            for seed in seeds:
                r = _run(m=m, mode=mode, seed=seed)
                rows.append(
                    " & ".join(
                        [
                            r["m"],
                            r["mode"],
                            r["seed"],
                            r["ok"],
                            r["page_ok"],
                            r["peak_frac"],
                            r["t_digits"],
                            r["escape_extra"],
                            r["ticks"],
                        ]
                    )
                    + r" \\"
                )
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_page_surrogate_rb_d_rows.tex", rows)

    summary = [
        r"\paragraph{BH5 RB-D robustness audit (Page surrogate).} \AuditTag "
        r"This fragment sweeps $(m,\\texttt{mode},\\texttt{seed})$ for the queue-equivalent single-stream model and "
        r"reports (i) exact recovery success and (ii) whether the surrogate $U(t)$ exhibits a Page-like shape "
        r"(increase to a peak then decrease to $0$) under the CAP-selected schedule parameters. "
        r"This provides an RB-D style robustness diagnostic for the record-level Page surrogate.",
    ]
    write_lines(generated_dir() / "bh_page_surrogate_rb_d_summary.tex", summary)

    print("Wrote sections/generated/bh_page_surrogate_rb_d_rows.tex")
    print("Wrote sections/generated/bh_page_surrogate_rb_d_summary.tex")


if __name__ == "__main__":
    main()

