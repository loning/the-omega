#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify and summarize higher collision-moment recurrences S_k(m).

We work with the Fold_m fiber multiplicities d_m(x)=|Fold_m^{-1}(x)| and define:
  S_k(m) = sum_x d_m(x)^k.

The paper already treats k=2 (A2 kernel) and k=3 (A3 kernel).
This script verifies the proposed exact integer recurrences for k=4..8 against
enumerated S_k(m), and writes a small LaTeX table for auditability.

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from common_paths import export_dir, generated_dir
from common_phi_fold import Progress, fold_m, word_to_str


def collision_counts(m: int, progress: Progress | None = None) -> Dict[str, int]:
    from itertools import product

    counts: Dict[str, int] = {}
    total = 1 << m
    for i, bits in enumerate(product([0, 1], repeat=m), start=1):
        x = word_to_str(fold_m(bits))
        counts[x] = counts.get(x, 0) + 1
        if progress is not None:
            progress.tick(f"m={m} i={i}/{total} distinct={len(counts)}")
    return counts


def s_k_from_counts(counts: Dict[str, int], k: int) -> int:
    if k == 2:
        return sum(v * v for v in counts.values())
    if k == 3:
        return sum(v * v * v for v in counts.values())
    return sum(int(v**k) for v in counts.values())


def enumerate_S(m_min: int, m_max: int, k_max: int, prog: Progress) -> Dict[int, Dict[int, int]]:
    S: Dict[int, Dict[int, int]] = {k: {} for k in range(2, k_max + 1)}
    for m in range(m_min, m_max + 1):
        counts = collision_counts(m, progress=prog)
        for k in range(2, k_max + 1):
            S[k][m] = s_k_from_counts(counts, k)
        print(f"[moment-rec] m={m} |X_m|={len(counts)}", flush=True)
    return S


def verify_recurrence(seq: Dict[int, int], coeffs: List[int], m0: int) -> List[Tuple[int, int, int]]:
    """Return list of (m,lhs,rhs) mismatches for m>=m0."""
    d = len(coeffs)
    ms = sorted(seq.keys())
    mism: List[Tuple[int, int, int]] = []
    for m in ms:
        if m < m0:
            continue
        rhs = 0
        for i, c in enumerate(coeffs, start=1):
            rhs += c * seq[m - i]
        lhs = seq[m]
        if lhs != rhs:
            mism.append((m, lhs, rhs))
    return mism


@dataclass(frozen=True)
class RecSpec:
    k: int
    order: int
    m0_hint: int
    coeffs: List[int]  # S(m)=sum_{i=1..d} coeffs[i-1]*S(m-i)


RECS: List[RecSpec] = [
    RecSpec(k=4, order=5, m0_hint=13, coeffs=[2, 7, 0, 2, -2]),
    RecSpec(k=5, order=5, m0_hint=13, coeffs=[2, 11, 8, 20, -10]),
    RecSpec(k=6, order=7, m0_hint=15, coeffs=[2, 17, 28, 88, -26, 4, -4]),
    RecSpec(k=7, order=7, m0_hint=15, coeffs=[2, 26, 74, 311, -34, 84, -42]),
    RecSpec(k=8, order=9, m0_hint=17, coeffs=[2, 40, 174, 969, 2, 428, -174, 4, -4]),
]

def earliest_valid_start(seq: Dict[int, int], coeffs: List[int]) -> int:
    """Earliest m0 such that recurrence holds for all m>=m0 in the available window."""
    d = len(coeffs)
    ms = sorted(seq.keys())
    m_min = ms[0]
    m_max = ms[-1]
    start = max(m_min + d, d)
    for m0 in range(start, m_max + 1):
        ok = True
        for m in range(m0, m_max + 1):
            rhs = 0
            for i, c in enumerate(coeffs, start=1):
                rhs += c * seq[m - i]
            if seq[m] != rhs:
                ok = False
                break
        if ok:
            return m0
    return start


def write_table_tex(path: Path, recs: List[RecSpec]) -> None:
    def fmt_coeffs(cs: List[int]) -> str:
        # compact: c1,c2,...,cd
        return ", ".join(str(c) for c in cs)

    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Verified exact integer recurrences for higher collision moments "
        "$S_k(m)=\\sum_x d_m(x)^k$ (Fold$_m$ fibers). "
        "Coefficients are in the form $S(m)=\\sum_{i=1}^d c_i S(m-i)$.}"
    )
    lines.append("\\label{tab:fold_collision_moment_recursions}")
    lines.append("\\begin{tabular}{r r r l}")
    lines.append("\\toprule")
    lines.append("$k$ & order $d$ & starts at $m\\ge$ & $(c_1,\\dots,c_d)$\\\\")
    lines.append("\\midrule")
    for r in recs:
        # m0 is filled in main() by computing earliest_valid_start on verified data
        lines.append(f"{r.k} & {r.order} & {r.m0_hint} & ({fmt_coeffs(r.coeffs)})\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify higher-moment recurrences S_k(m) for Fold_m.")
    parser.add_argument("--m-min", type=int, default=0)
    parser.add_argument("--m-max", type=int, default=22)
    parser.add_argument("--k-max", type=int, default=8)
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "fold_collision_moment_recursions.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_fold_collision_moment_recursions.tex"),
        help="Output LaTeX table path.",
    )
    args = parser.parse_args()

    prog = Progress("moment-rec", every_seconds=20.0)
    S = enumerate_S(args.m_min, args.m_max, args.k_max, prog)

    # Verify recurrences (k=4..8) if we have those moments.
    verified: List[Dict[str, object]] = []
    for rec in RECS:
        if rec.k > args.k_max:
            continue
        m0 = earliest_valid_start(S[rec.k], rec.coeffs)
        mism = verify_recurrence(S[rec.k], rec.coeffs, m0)
        ok = len(mism) == 0
        verified.append(
            {
                "k": rec.k,
                "order": rec.order,
                "m0": m0,
                "coeffs": rec.coeffs,
                "ok": ok,
                "mismatches": mism[:5],
            }
        )
        if not ok:
            raise SystemExit(f"Recurrence verification failed for k={rec.k}: {mism[:3]}")

    payload: Dict[str, object] = {
        "m_min": args.m_min,
        "m_max": args.m_max,
        "k_max": args.k_max,
        "S_k": {str(k): {str(m): int(v) for m, v in S[k].items()} for k in range(2, args.k_max + 1)},
        "verified_recursions": verified,
    }
    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[moment-rec] wrote {jout}", flush=True)

    # Always write the summary table for k=4..min(k_max,8).
    # Replace m0_hint by computed earliest starts for the table.
    m0_map = {v["k"]: int(v["m0"]) for v in verified}
    recs: List[RecSpec] = []
    for r in RECS:
        if r.k > args.k_max:
            continue
        recs.append(RecSpec(k=r.k, order=r.order, m0_hint=m0_map[r.k], coeffs=r.coeffs))
    write_table_tex(Path(args.tex_out), recs)
    print(f"[moment-rec] wrote {args.tex_out}", flush=True)


if __name__ == "__main__":
    main()

