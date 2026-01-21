# -*- coding: utf-8 -*-
"""
Scattering vs black-hole Page-surrogate equivalence (toy, deterministic).

Goal:
  Provide a side-by-side "Page-like" information-release audit in the record algebra language:
    - For a black-hole-like stream: coarse stable labels w in X_m hide fiber information;
      late emissions can (in a toy schedule) encode additional digits to reduce ambiguity.
    - For a scattering-like stream: coarse outcomes hide a fixed number of hidden bits per event;
      late emissions encode additional digits similarly.

We do NOT claim a physical replica derivation or a theorem-level equivalence.
This script produces a reproducible comparison artifact that uses the same surrogate functional
U(t) := remaining ambiguity (bits) on record prefixes under an explicitly declared schedule.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/scattering_bh_page_surrogate_rows.tex
  - sections/generated/scattering_bh_page_surrogate_summary.tex
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import all_xm, cached_foldm_outputs

# Reuse the deterministic Page-surrogate helpers (same project, same style).
from exp_black_hole_queue_equivalence import (  # type: ignore
    _cap_select_mixing_params,
    _digits_per_fiber,
    _interleave_schedule,
    _remaining_ambiguity_bits,
    fiber_preimages,
)


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


class _LCG:
    def __init__(self, seed: int) -> None:
        self._s = int(seed) & 0xFFFFFFFFFFFFFFFF

    def u01(self) -> float:
        self._s = (6364136223846793005 * self._s + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return float((self._s >> 11) & ((1 << 53) - 1)) / float(1 << 53)

    def randint(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        return int(self.u01() * float(n))


@dataclass(frozen=True)
class PageParams:
    L: int
    A: int
    t_digits: int
    scramble_delay: int
    exponent: int


def _page_params_from_g_list(g_list: List[int], A: int, t_digits: int) -> PageParams:
    L = len(g_list)
    sel = _cap_select_mixing_params(L=L, t=int(t_digits), g_list=g_list, A=int(A))
    return PageParams(
        L=int(L),
        A=int(A),
        t_digits=int(t_digits),
        scramble_delay=int(sel["scramble_delay"]),
        exponent=int(sel["exponent"]),
    )


def _u_at_checkpoints(g_list: List[int], p: PageParams, checkpoints: List[float]) -> List[Tuple[float, float]]:
    total = int(p.L + p.L * p.t_digits)
    if total <= 0:
        return [(float(a), 0.0) for a in checkpoints]
    sched = _interleave_schedule(L=p.L, t=p.t_digits, scramble_delay=p.scramble_delay, exponent=p.exponent)
    if len(sched) != total:
        raise RuntimeError("schedule length mismatch")

    # Compute U along the prefix, but only record values at target ticks.
    targets = [max(0, min(total, int(round(float(frac) * float(total))))) for frac in checkpoints]
    targets = sorted(set(targets))

    payload = 0
    rec = 0
    out: Dict[int, float] = {0: float(_remaining_ambiguity_bits(g_list, p.A, p.t_digits, 0, 0))}
    for i, tag in enumerate(sched, start=1):
        if tag == "P":
            payload += 1
        else:
            rec += 1
        if i in targets:
            out[i] = float(_remaining_ambiguity_bits(g_list, p.A, p.t_digits, payload, rec))

    pairs: List[Tuple[float, float]] = []
    for frac in checkpoints:
        k = max(0, min(total, int(round(float(frac) * float(total)))))
        pairs.append((float(frac), float(out.get(k, float("nan")))))
    return pairs


def _bh_g_list(m: int, L: int, seed: int) -> Tuple[List[int], PageParams]:
    # Build g_list from true folding degeneracies g_m(w).
    Xm = all_xm(int(m))
    pre = fiber_preimages(int(m))  # pre[w] = list of k with Fold_m(k)=w
    A = len(Xm)
    t_digits = _digits_per_fiber(int(m), pre, Xm)

    # Deterministic message stream: select microstates k and observe coarse stable labels w=Fold_m(k).
    rng = _LCG(int(seed))
    outs = cached_foldm_outputs(int(m))
    g_list: List[int] = []
    for _ in range(int(L)):
        k = int(rng.randint(1 << int(m)))
        w = outs[k]
        g_list.append(int(len(pre[w])))

    p = _page_params_from_g_list(g_list=g_list, A=A, t_digits=int(t_digits))
    return g_list, p


def _scattering_g_list(*, L: int, hidden_bits: int) -> List[int]:
    # Scattering toy: each event hides a fixed hidden_bits microstate among g=2^{hidden_bits}.
    g = 1 << int(hidden_bits)
    return [int(g) for _ in range(int(L))]


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "scattering_bh_page_surrogate_rows.tex"
    sum_path = out_dir / "scattering_bh_page_surrogate_summary.tex"

    # Common checkpoints on the non-vacuum stream length.
    checkpoints = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]

    # Compare at the anchor m=6.
    m = 6
    L = 48
    seed = 20260112

    # Scattering hidden bits per event (toy knob; fixed as an explicit interface quantity).
    hidden_bits = 10  # g=1024

    g_bh, p_bh = _bh_g_list(m=m, L=L, seed=seed)
    g_sc = _scattering_g_list(L=L, hidden_bits=hidden_bits)

    # Use the same alphabet size A=|X_m| to express "recovery digits" in base A.
    A = p_bh.A
    # Minimal digit count for scattering hidden bits.
    # Smallest t with A^t >= 2^{hidden_bits}.
    t_sc = 0
    cap = 1
    while cap < (1 << int(hidden_bits)):
        cap *= int(A)
        t_sc += 1
    p_sc = _page_params_from_g_list(g_list=g_sc, A=A, t_digits=int(t_sc))

    u_bh = _u_at_checkpoints(g_list=g_bh, p=p_bh, checkpoints=checkpoints)
    u_sc = _u_at_checkpoints(g_list=g_sc, p=p_sc, checkpoints=checkpoints)

    # Emit a single table: compare U(frac) across the two toys.
    rows: List[str] = []
    for (frac1, Ubh), (frac2, Usc) in zip(u_bh, u_sc):
        if abs(frac1 - frac2) > 1e-12:
            raise RuntimeError("checkpoint mismatch")
        rows.append(
            " & ".join(
                [
                    _fmt(frac1, 3),
                    _fmt(Ubh, 6),
                    _fmt(Usc, 6),
                ]
            )
            + r" \\"
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])
    write_lines(
        sum_path,
        [
            r"\paragraph{Page-surrogate equivalence (toy): scattering vs black-hole record algebra.} \AuditTag "
            + r"We compare a black-hole-like stable-label record (coarse $w\in X_m$ hiding folding-fiber micro-information) "
            + r"to a scattering-like record hiding a fixed number of hidden bits per event. "
            + r"Both are evaluated under the same auditable schedule template (finite-family selection of a mixing schedule) "
            + r"and the same surrogate functional $U(t)$: remaining ambiguity (bits) on record prefixes under progressive release of base-$|X_m|$ digits.",
            r"\paragraph{Parameters.} \AuditTag "
            + rf"BH anchor $m={m}$, $L={L}$, $|X_m|={A}$, $t_{{\mathrm{{BH}}}}={p_bh.t_digits}$, schedule=(scramble\_delay={p_bh.scramble_delay}, exponent={p_bh.exponent}). "
            + rf"Scattering toy hidden\_bits={hidden_bits} (g={1 << int(hidden_bits)}), $t_{{\mathrm{{SC}}}}={p_sc.t_digits}$, schedule=(scramble\_delay={p_sc.scramble_delay}, exponent={p_sc.exponent}).",
            r"\paragraph{Scope.} \AuditTag "
            + r"This is a record-algebra surrogate comparison and does not assert a physical Page-curve derivation.",
        ],
    )


if __name__ == "__main__":
    main()

