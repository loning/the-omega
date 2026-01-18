# -*- coding: utf-8 -*-
"""
m=6 trap/exit audit rows (18 cyclic trap states + 3 boundary exit channels).

This script treats:
  - 18 cyclic stable types at m=6 as trap categories,
  - 3 boundary stable types as exit channels, assigned to U(1), SU(2), SU(3)
    by the SM labeling closure.

Outputs (LaTeX fragments):
  - sections/generated/leakage_kernel_m6_trap_exit_rows.tex
  - sections/generated/leakage_kernel_m6_trap_exit_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


BOUNDARY_WORDS = ("100001", "101001", "100101")

# Boundary intrinsic values at m=6 (Remark rem:boundary_value_order in the SM labeling closure section):
BOUNDARY_V = {
    "U(1)": 14,
    "SU(2)": 17,
    "SU(3)": 19,
}


@dataclass(frozen=True)
class Trap:
    w: str
    v: int
    label: str


def _parse_sm_labeling_rows() -> List[Trap]:
    """
    Parse sections/generated/sm_labeling_rows.tex to extract:
      - stable type w (col 1),
      - Zeckendorf value V(w) (col 2),
      - label (col 7).
    """
    p = paper_root() / "sections/generated/sm_labeling_rows.tex"
    text = p.read_text(encoding="utf-8")
    traps: List[Trap] = []
    def unwrap_word(s: str) -> str:
        t = s.strip()
        # Expect \texttt{010101} formatting in the generated table.
        if t.startswith(r"\texttt{") and t.endswith("}"):
            return t[len(r"\texttt{") : -1]
        return t

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        if not line.endswith(r"\\"):
            continue
        parts = [x.strip() for x in line[:-2].split("&")]
        if len(parts) < 7:
            continue
        w_raw = unwrap_word(parts[0])
        if w_raw in BOUNDARY_WORDS:
            continue
        try:
            v = int(parts[1])
        except Exception:
            continue
        label = parts[6]
        traps.append(Trap(w=w_raw, v=v, label=label))
    # Deterministic sort by intrinsic value then word.
    traps.sort(key=lambda t: (t.v, t.w))
    # Expect 18 cyclic trap types for m=6.
    assert len(traps) == 18, f"Expected 18 cyclic trap rows, got {len(traps)}"
    return traps


def _delay_level(traps: Sequence[Trap]) -> Dict[str, int]:
    """
    Deterministic coarse delay level based on intrinsic rank:
      1 = low, 2 = mid, 3 = high (terciles).
    """
    n = len(traps)
    out: Dict[str, int] = {}
    for i, t in enumerate(traps):
        # i in [0, n-1]
        frac = (i + 1) / n
        if frac <= 1.0 / 3.0:
            out[t.w] = 1
        elif frac <= 2.0 / 3.0:
            out[t.w] = 2
        else:
            out[t.w] = 3
    return out


def _weights_for_trap(v: int, p: int) -> Tuple[float, float, float]:
    """
    Affinity weights by intrinsic-value proximity to boundary intrinsic values.
    """
    def w(delta: int) -> float:
        return 1.0 / ((1 + abs(int(delta))) ** int(p))

    wu1 = w(v - BOUNDARY_V["U(1)"])
    wsu2 = w(v - BOUNDARY_V["SU(2)"])
    wsu3 = w(v - BOUNDARY_V["SU(3)"])
    s = wu1 + wsu2 + wsu3
    return (wu1 / s, wsu2 / s, wsu3 / s)


def _monotone_violation_cost(traps: Sequence[Trap], p: int) -> float:
    """
    Cost that penalizes violations of monotonicity of the expected channel-complexity
    score as intrinsic value increases.
    """
    # Channel complexity scores (audit convention).
    scores = (1.0, 2.0, 3.0)  # U(1), SU(2), SU(3)
    exp_score: List[Tuple[int, float]] = []
    for t in traps:
        pu1, psu2, psu3 = _weights_for_trap(t.v, p)
        e = pu1 * scores[0] + psu2 * scores[1] + psu3 * scores[2]
        exp_score.append((t.v, float(e)))
    exp_score.sort(key=lambda x: x[0])
    cost = 0.0
    for i in range(len(exp_score)):
        for j in range(i + 1, len(exp_score)):
            vi, ei = exp_score[i]
            vj, ej = exp_score[j]
            if vi < vj and ei > ej:
                cost += (ei - ej)
    return float(cost)


def _cap_select_p(traps: Sequence[Trap]) -> Tuple[int, float]:
    """
    Finite-family CAP selection over p in {1,2,3} with key:
      (monotone_violation_cost, p).
    """
    best = None
    for p in (1, 2, 3):
        c = _monotone_violation_cost(traps, p)
        key = (c, int(p))
        if best is None or key < best[0]:
            best = (key, (p, c))
    assert best is not None
    return best[1]


def _fmt(x: float, digits: int = 3) -> str:
    return f"{float(x):.{int(digits)}f}"


def main() -> None:
    traps = _parse_sm_labeling_rows()
    delay = _delay_level(traps)
    p_star, cost = _cap_select_p(traps)

    lines: List[str] = []
    for t in traps:
        pu1, psu2, psu3 = _weights_for_trap(t.v, p_star)
        lines.append(
            " & ".join(
                [
                    t.w,
                    t.label,
                    str(int(delay[t.w])),
                    _fmt(pu1, 3),
                    f"({_fmt(psu2, 3)},{_fmt(psu3, 3)})",
                ]
            )
            + r" \\"
        )

    write_lines(
        generated_dir() / "leakage_kernel_m6_trap_exit_rows.tex",
        lines if lines else ["% (no rows)"],
    )

    summary_lines = [
        r"\paragraph{Audit summary (m=6 trap/exit table).} \AuditTag "
        r"This fragment treats the 18 cyclic stable types at $m=6$ as trap categories and the 3 boundary types as exit channels. "
        r"Exit weights are computed by intrinsic-value proximity to the boundary intrinsic values "
        r"$V(100001)=14$, $V(101001)=17$, $V(100101)=19$ (assigned to $U(1),SU(2),SU(3)$ by the SM labeling closure). "
        rf"A finite family over exponent $p\in\{{1,2,3\}}$ is CAP-selected by minimizing a monotonicity-violation cost; "
        rf"the selected value is $p^\ast={p_star}$ with cost {_fmt(cost, 6)}.",
    ]
    write_lines(generated_dir() / "leakage_kernel_m6_trap_exit_summary.tex", summary_lines)


if __name__ == "__main__":
    main()

