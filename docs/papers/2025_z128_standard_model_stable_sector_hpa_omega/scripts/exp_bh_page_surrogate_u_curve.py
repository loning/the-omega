# -*- coding: utf-8 -*-
"""
BH5: Page surrogate U(t) curve for the queue-equivalent single-stream model.

We treat the queue model as the protocol-level generator of a single stable-label record stream w in X_m.
We compute a deterministic surrogate U(t) (remaining micro-ambiguity bits) over the non-vacuum portion
under the internal schedule (payload vs recovery emissions).

Outputs:
  - sections/generated/bh_page_surrogate_u_curve_rows.tex
  - sections/generated/bh_page_surrogate_u_curve_summary.tex
  - figures/bh_page_surrogate_u_curve.png (optional; requires matplotlib)

Only standard library is used for computation; matplotlib is used for plotting if available.
"""

from __future__ import annotations

from typing import Dict, List

from common_paths import figures_dir, generated_dir
from common_tex import write_lines

import exp_black_hole_queue_equivalence as bhq


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def _tex_escape_text(s: str) -> str:
    """
    Minimal LaTeX text-mode escaping for generated fragments.
    """
    return str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_")


def main() -> None:
    m = 6
    base_vacuum_mass = 64
    msg_text = "TICK-INFORMATION"
    mode = "cyclic_only"

    # Run a case to obtain the record and parameters (we only use meta for reporting).
    bits = bhq._bits_from_ascii(msg_text)
    allowed, _info = bhq._allowed_set_by_mode(m, mode=mode)
    msg_micro = bhq.bits_to_allowed_micro_indices(bits, allowed=allowed)

    _st, radiation_w, meta = bhq.forward_simulate_single_stream(
        base_vacuum_mass=base_vacuum_mass, m=m, message_micro=msg_micro
    )

    # For U(t) we use the internal schedule (payload/recovery) at fixed (L,t,scramble_delay,exponent).
    L = int(meta["L"])
    t = int(meta["t"])
    sched = bhq._interleave_schedule(
        L=L, t=t, scramble_delay=int(meta["scramble_delay"]), exponent=int(meta["exponent"])
    )

    # g_i for each payload symbol i (computed from Fold_m fibers).
    pre = bhq.fiber_preimages(m)
    g_list = [len(pre[bhq.fold_m(n, m)]) for n in msg_micro]

    # Compute U over non-vacuum ticks.
    nonvac_len = L + (L * t)
    payload_emitted = 0
    recovery_emitted = 0
    U_vals: List[float] = []
    for tag in sched:
        if tag == "P":
            payload_emitted += 1
        else:
            recovery_emitted += 1
        U_vals.append(
            bhq._remaining_ambiguity_bits(
                g_list=g_list,
                A=len(bhq.all_xm(m)),
                t=t,
                payload_emitted=payload_emitted,
                recovery_emitted=recovery_emitted,
            )
        )

    # Sample rows.
    sample = sorted(set([0, nonvac_len // 8, nonvac_len // 4, nonvac_len // 2, (3 * nonvac_len) // 4, nonvac_len]))
    rows: List[str] = []
    U_max = max(U_vals) if U_vals else 0.0
    for tick in sample:
        if tick <= 0:
            p = 0
            r = 0
            U = 0.0
        else:
            p = 0
            r = 0
            for tag in sched[:tick]:
                if tag == "P":
                    p += 1
                else:
                    r += 1
            U = U_vals[tick - 1]
        frac = 1.0 - (U / U_max) if U_max > 0 else 1.0
        rows.append(f"{tick} & {p} & {r} & {_fmt(U, 6)} & {_fmt(frac, 6)} \\\\")
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_page_surrogate_u_curve_rows.tex", rows)

    summary = [
        r"\paragraph{BH5 Page surrogate $U(t)$ (queue-equivalent single-stream model).} \AuditTag "
        r"This fragment reports a deterministic record-level surrogate $U(t)$ (remaining micro-ambiguity bits) "
        r"computed from the folding fibers under a CAP-selected emission schedule (payload vs recovery). "
        rf"Parameters: mode=\texttt{{{_tex_escape_text(mode)}}}, $m={m}$, $L={L}$, $t={t}$, "
        rf"scramble\_delay={int(meta['scramble_delay'])}, exponent={int(meta['exponent'])}, "
        rf"vacuum tail={base_vacuum_mass}.",
    ]
    write_lines(generated_dir() / "bh_page_surrogate_u_curve_summary.tex", summary)

    # Optional plot.
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        print("matplotlib not available; skipping figures/bh_page_surrogate_u_curve.png")
        return

    figures_dir().mkdir(parents=True, exist_ok=True)
    xs = list(range(1, nonvac_len + 1))
    plt.figure(figsize=(7.2, 3.8))
    plt.plot(xs, U_vals, linewidth=2.0)
    plt.axvline(int(nonvac_len // 2), linestyle="--", linewidth=1.5)
    plt.title("BH Page surrogate U(t) (queue-equivalent single-stream)")
    plt.xlabel("tick t (non-vacuum)")
    plt.ylabel("U(t) [bits]")
    plt.tight_layout()
    out_png = figures_dir() / "bh_page_surrogate_u_curve.png"
    plt.savefig(out_png, dpi=180)
    plt.close()
    print("Wrote figures/bh_page_surrogate_u_curve.png")


if __name__ == "__main__":
    main()

