# -*- coding: utf-8 -*-
"""
BH5: Page-curve surrogate (mixed single-stream record).

This script generates an audit-only surrogate curve U(t) for a self-describing,
single-stream radiation record where payload coarse labels and recovery digits are
interleaved deterministically.

Outputs:
  - sections/generated/bh_page_surrogate_mixed_curve_rows.tex
  - sections/generated/bh_page_surrogate_mixed_summary.tex
  - figures/bh_page_surrogate_mixed.png  (requires matplotlib)

Only standard library is used for computation; matplotlib is used for plotting.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List

from common_paths import figures_dir, generated_dir
from common_tex import write_lines
from protocol_kernel import all_xm, cached_degeneracy_map, fold_m, max_degeneracy


def _encode_base_A(x: int, A: int, t: int) -> List[int]:
    if t <= 0:
        return []
    if x < 0:
        raise ValueError("x must be nonnegative")
    digits = [0] * t
    y = int(x)
    for i in range(t - 1, -1, -1):
        digits[i] = y % A
        y //= A
    if y != 0:
        raise ValueError("x does not fit in t base-A digits")
    return digits


def _digits_per_fiber(A: int, g_max: int) -> int:
    if A <= 1:
        raise ValueError("A must be >= 2")
    if g_max <= 1:
        return 0
    t = 0
    cap = 1
    while cap < g_max:
        cap *= A
        t += 1
    return t


def _interleave_schedule(L: int, t: int, scramble_delay: int, exponent: int) -> List[str]:
    if L < 0 or t < 0:
        raise ValueError("L and t must be nonnegative")
    if exponent < 1:
        raise ValueError("exponent must be >= 1")
    p_rem = int(L)
    r_rem = int(L) * int(t)
    total = p_rem + r_rem
    sched: List[str] = []
    warm = min(int(scramble_delay), p_rem)

    for i in range(total):
        if p_rem <= 0:
            sched.append("R")
            r_rem -= 1
            continue
        if r_rem <= 0:
            sched.append("P")
            p_rem -= 1
            continue
        if i < warm:
            sched.append("P")
            p_rem -= 1
            continue

        pw = float(p_rem) ** float(exponent)
        rw = float(r_rem)
        if pw >= rw:
            sched.append("P")
            p_rem -= 1
        else:
            sched.append("R")
            r_rem -= 1

    if p_rem != 0 or r_rem != 0:
        raise RuntimeError("Schedule construction failed to place all emissions")
    return sched


def _remaining_ambiguity_bits(
    g_list: List[int], A: int, t: int, payload_emitted: int, recovery_emitted: int
) -> float:
    if payload_emitted < 0 or recovery_emitted < 0:
        raise ValueError("emitted counts must be nonnegative")
    if t < 0:
        raise ValueError("t must be nonnegative")
    if A <= 1:
        raise ValueError("A must be >= 2")

    L = len(g_list)
    p = min(L, int(payload_emitted))
    r = min(L * t, int(recovery_emitted))
    if t == 0:
        return 0.0

    U = 0.0
    for i in range(p):
        g = int(g_list[i])
        k = min(t, max(0, r - i * t))
        denom = 1
        for _ in range(int(k)):
            denom *= A
        rem = (g + denom - 1) // denom
        if rem > 1:
            U += math.log2(float(rem))
    return float(U)


def _cap_select_mixing_params(L: int, t: int, A: int) -> Dict[str, int]:
    """
    Deterministic finite-family selection for (scramble_delay, exponent).
    Uses a maximally conservative ambiguity model, independent of the particular message.
    """
    if L <= 0:
        return {"scramble_delay": 0, "exponent": 1}
    if t < 0:
        raise ValueError("t must be >= 0")

    total_nonvac = L + (L * t)
    target_peak = 0.5 * float(total_nonvac)

    delay_ratios = [0.0, 0.25, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.75]
    exponents = [1, 2, 3]

    # Conservative g model: g = A^t for all payload symbols.
    g = int(A**t) if t > 0 else 1
    g_list = [g for _ in range(L)]

    best_key = None
    best = None

    for r0 in delay_ratios:
        scramble_delay = int(math.floor(float(r0) * float(L)))
        for exponent in exponents:
            sched = _interleave_schedule(L=L, t=t, scramble_delay=scramble_delay, exponent=exponent)
            payload_emitted = 0
            recovery_emitted = 0
            peak_idx = 0
            peak_val = -1.0
            for i, tag in enumerate(sched):
                if tag == "P":
                    payload_emitted += 1
                else:
                    recovery_emitted += 1
                U = _remaining_ambiguity_bits(
                    g_list=g_list,
                    A=A,
                    t=t,
                    payload_emitted=payload_emitted,
                    recovery_emitted=recovery_emitted,
                )
                if U > peak_val + 1e-12:
                    peak_val = U
                    peak_idx = i
            peak_tick = float(peak_idx + 1)
            peak_mismatch = abs(peak_tick - target_peak)
            key = (peak_mismatch, -scramble_delay, int(exponent))
            if best_key is None or key < best_key:
                best_key = key
                best = {"scramble_delay": int(scramble_delay), "exponent": int(exponent)}

    assert best is not None
    return best


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def main() -> None:
    m = 6
    seed = 20260112
    rng = random.Random(seed)
    L = 128  # microstates
    base_vacuum_mass = 256  # keep a long tail of vacuum ticks

    Xm = all_xm(m)
    A = len(Xm)
    gm = cached_degeneracy_map(m)
    g_max = int(max_degeneracy(m))
    t = _digits_per_fiber(A=A, g_max=g_max)

    msg_micro = [rng.randrange(0, 1 << m) for _ in range(L)]
    w_list = [fold_m(n, m) for n in msg_micro]
    g_list = [int(gm[w]) for w in w_list]

    params = _cap_select_mixing_params(L=L, t=t, A=A)
    scramble_delay = int(params["scramble_delay"])
    exponent = int(params["exponent"])
    sched = _interleave_schedule(L=L, t=t, scramble_delay=scramble_delay, exponent=exponent)

    # Compute U(t) over the non-vacuum region.
    U_vals: List[float] = []
    payload_emitted = 0
    recovery_emitted = 0
    for tag in sched:
        if tag == "P":
            payload_emitted += 1
        else:
            recovery_emitted += 1
        U_vals.append(
            _remaining_ambiguity_bits(
                g_list=g_list,
                A=A,
                t=t,
                payload_emitted=payload_emitted,
                recovery_emitted=recovery_emitted,
            )
        )

    # Sample rows for LaTeX.
    total_nonvac = len(sched)
    sample_ticks = sorted(
        set(
            [
                0,
                total_nonvac // 8,
                total_nonvac // 4,
                total_nonvac // 2,
                (3 * total_nonvac) // 4,
                (7 * total_nonvac) // 8,
                total_nonvac,
            ]
        )
    )
    rows: List[str] = []
    for tick in sample_ticks:
        if tick == 0:
            p_emit = 0
            r_emit = 0
            U = 0.0
        else:
            p_emit = 0
            r_emit = 0
            for tag in sched[:tick]:
                if tag == "P":
                    p_emit += 1
                else:
                    r_emit += 1
            U = U_vals[tick - 1]
        frac = 1.0 - (U / max(U_vals)) if U_vals and max(U_vals) > 0 else 1.0
        rows.append(f"{tick} & {p_emit} & {r_emit} & {_fmt(U, 6)} & {_fmt(frac, 6)} \\\\")
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_page_surrogate_mixed_curve_rows.tex", rows)

    summary_lines = [
        r"\paragraph{BH5 mixed single-stream surrogate (audit).} \AuditTag "
        r"This fragment reports a Page-like surrogate curve $U(t)$ (remaining micro-ambiguity bits) for a "
        r"self-describing, single-stream radiation model: payload coarse labels and recovery digits are interleaved "
        r"deterministically under a CAP-selected finite family. "
        rf"Parameters used: $m={m}$, $L={L}$ microstates, $|X_m|={A}$, $t={t}$ base-$|X_m|$ digits per fiber index, "
        rf"scramble\_delay={scramble_delay}, exponent={exponent}.",
    ]
    write_lines(generated_dir() / "bh_page_surrogate_mixed_summary.tex", summary_lines)

    # Plot (matplotlib required).
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        raise RuntimeError("matplotlib is required to generate figures/bh_page_surrogate_mixed.png") from e

    figures_dir().mkdir(parents=True, exist_ok=True)
    xs = list(range(1, total_nonvac + 1))
    plt.figure(figsize=(7.2, 3.8))
    plt.plot(xs, U_vals, linewidth=2.0)
    plt.axvline(int(total_nonvac // 2), linestyle="--", linewidth=1.5)
    plt.title("BH Page surrogate (mixed single-stream): remaining ambiguity U(t)")
    plt.xlabel("tick t (non-vacuum)")
    plt.ylabel("U(t) [bits]")
    plt.tight_layout()
    out_png = figures_dir() / "bh_page_surrogate_mixed.png"
    plt.savefig(out_png, dpi=180)
    plt.close()

    print("Wrote sections/generated/bh_page_surrogate_mixed_curve_rows.tex")
    print("Wrote sections/generated/bh_page_surrogate_mixed_summary.tex")
    print("Wrote figures/bh_page_surrogate_mixed.png")


if __name__ == "__main__":
    main()

