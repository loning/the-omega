# -*- coding: utf-8 -*-
"""
K4 -> alpha linkage audit (data-facing, deterministic).

This script tests whether the m=6 exit-weight table (U(1),SU(2),SU(3) channel weights)
admits any low-complexity aggregate mapping that can nontrivially align with
alpha targets already used elsewhere in the paper.

Outputs (LaTeX fragments):
  - sections/generated/k4_alpha_link_rows.tex
  - sections/generated/k4_alpha_link_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from common_constants import ALPHA_INV_CODATA_2022, ALPHAZ_INV_PDG
from common_paths import generated_dir, paper_root
from common_tex import write_lines


def _read_lines(rel: str) -> List[str]:
    p = paper_root() / rel
    return p.read_text(encoding="utf-8").splitlines()


def _tex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
    )


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


@dataclass(frozen=True)
class TrapWeights:
    p_u1: float
    p_su2: float
    p_su3: float


def _parse_m6_rows() -> List[TrapWeights]:
    rows = _read_lines("sections/generated/leakage_kernel_m6_trap_exit_rows.tex")
    out: List[TrapWeights] = []
    for raw in rows:
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        if not line.endswith(r"\\"):
            continue
        parts = [x.strip() for x in line[:-2].split("&")]
        if len(parts) < 5:
            continue
        p_u1 = float(parts[3])
        pair = parts[4].strip()
        if not (pair.startswith("(") and pair.endswith(")")):
            continue
        a, b = pair[1:-1].split(",")
        p_su2 = float(a)
        p_su3 = float(b)
        out.append(TrapWeights(p_u1=p_u1, p_su2=p_su2, p_su3=p_su3))
    assert len(out) == 18, f"Expected 18 trap rows, got {len(out)}"
    return out


def _safe_log(x: float) -> float:
    return math.log(max(1e-300, float(x)))


def _aggregate(weights: Sequence[TrapWeights], agg_id: str, k: int) -> float:
    ps = [w.p_u1 for w in weights]
    if agg_id == "mean_p":
        return float(sum(ps) / len(ps))
    if agg_id == "mean_inv_p":
        return float(sum(1.0 / max(1e-12, p) for p in ps) / len(ps))
    if agg_id == "mean_inv_p_pow":
        return float(sum((1.0 / max(1e-12, p)) ** k for p in ps) / len(ps))
    if agg_id == "sum_neg_log_p":
        return float(sum(-_safe_log(p) for p in ps))
    raise ValueError(agg_id)


def _candidates() -> List[Tuple[str, int]]:
    # Finite family of low-complexity aggregations.
    out: List[Tuple[str, int]] = [
        ("mean_p", 1),
        ("mean_inv_p", 1),
        ("sum_neg_log_p", 1),
    ]
    for k in (1, 2, 3):
        out.append(("mean_inv_p_pow", k))
    return out


def _scale_family() -> List[float]:
    # Coarse bounded scale family in log10 space.
    return [10.0 ** e for e in range(-6, 7)]


def main() -> None:
    w = _parse_m6_rows()
    alpha_low = float(ALPHA_INV_CODATA_2022)
    alpha_z = float(ALPHAZ_INV_PDG)

    rows: List[str] = []
    scored: List[Tuple[Tuple[float, float, int], str, float, float, float]] = []

    for agg_id, k in _candidates():
        base = _aggregate(w, agg_id=agg_id, k=int(k))
        # Try scales to align with alpha targets; choose minimax mismatch to both targets.
        best = None
        for s in _scale_family():
            pred = float(s) * float(base)
            e_low = abs(math.log(pred / alpha_low))
            e_z = abs(math.log(pred / alpha_z))
            e_inf = max(e_low, e_z)
            key = (e_inf, e_low + e_z, len(agg_id) + int(k))
            if best is None or key < best[0]:
                best = (key, pred, e_low, e_z, s)
        assert best is not None
        key, pred, e_low, e_z, s = best
        label = f"{agg_id}(k={k})"
        scored.append((key, label, pred, e_low, e_z))

    scored.sort(key=lambda t: t[0])
    for i, (key, label, pred, e_low, e_z) in enumerate(scored, start=1):
        rows.append(
            " & ".join(
                [
                    str(i),
                    _tex_escape(label),
                    _fmt(pred, 6),
                    _fmt(e_low, 6),
                    _fmt(e_z, 6),
                ]
            )
            + r" \\"
        )

    out = generated_dir()
    write_lines(out / "k4_alpha_link_rows.tex", rows if rows else ["% (no rows)"])

    best = scored[0]
    summary = [
        r"\paragraph{Audit summary (K4 $\to$ $\alpha$ link).} \AuditTag "
        r"We test a finite family of low-complexity aggregations of the $m=6$ $U(1)$ exit weights "
        r"(from the trap/exit table in Appendix~\ref{app:leakage_kernel}) and allow only a coarse bounded scale family. "
        r"Each candidate reports log mismatches to $\alpha_{\mathrm{em}}^{-1}$ (CODATA) and $\alpha^{-1}(m_Z)$ (PDG).",
        r"\noindent\AuditTag "
        + rf"Selected candidate: \texttt{{{_tex_escape(best[1])}}} with predicted value {_fmt(best[2],6)} "
        + rf"and mismatches $(e_{{\mathrm{{low}}}},e_Z)=({_fmt(best[3],6)},{_fmt(best[4],6)})$.",
    ]
    write_lines(out / "k4_alpha_link_summary.tex", summary)


if __name__ == "__main__":
    main()

