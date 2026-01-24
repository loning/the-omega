#!/usr/bin/env python3
"""
Compute fold fibers and a Myhill--Nerode-style residual state spectrum for Fold_m.

This implementation focuses on a finite-length right-equivalence notion over prefixes:
two prefixes are equivalent at depth k iff they induce the same output for all suffixes.

Output artifacts:
- sections/generated/summary.json
- sections/generated/residual_state_counts_summary.tex
- sections/generated/fiber_spectrum_summary.tex
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


def fib_up_to(n: int) -> List[int]:
    # Fibonacci numbers with F0=0, F1=1, return [F0..Fn]
    if n < 0:
        return []
    F = [0, 1]
    while len(F) <= n:
        F.append(F[-1] + F[-2])
    return F


def fib(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    F = fib_up_to(n)
    return F[n]

def _subset_sum_reachable(weights: List[int]) -> int:
    """
    Return bitset as Python int: bit s is 1 iff sum s is reachable.
    Uses classic bitset DP: bits |= bits << w.
    """
    bits = 1
    for w in weights:
        if w <= 0:
            raise ValueError("weights must be positive")
        bits |= bits << w
    return bits


def subset_sum_count(weights: List[int]) -> Tuple[int, int]:
    """
    Return (count, max_sum), where count is number of reachable sums.
    """
    bits = _subset_sum_reachable(weights)
    max_sum = sum(weights)
    # Mask to avoid counting bits beyond max_sum (safe)
    mask = (1 << (max_sum + 1)) - 1
    bits &= mask
    return bits.bit_count(), max_sum


def interval_cover_holds(weights: List[int]) -> bool:
    """
    Check sufficient condition used in Lemma subset_sum_interval:
      w1 == 1 and w_{i+1} <= 1 + sum_{j<=i} w_j.
    """
    if not weights:
        return True
    if weights[0] != 1:
        return False
    s = weights[0]
    for w in weights[1:]:
        if w > s + 1:
            return False
        s += w
    return True


def zeckendorf_digits(N: int, F: List[int]) -> Dict[int, int]:
    """
    Return Zeckendorf digits z_k for k>=2 as a dict {k:0/1},
    using greedy on Fibonacci weights F_k.
    """
    if N < 0:
        raise ValueError("N must be non-negative")
    z: Dict[int, int] = {}
    k = len(F) - 1
    while k >= 2 and F[k] > N:
        k -= 1
    while N > 0 and k >= 2:
        if F[k] <= N:
            z[k] = 1
            N -= F[k]
            k -= 2  # skip adjacent
        else:
            k -= 1
    return z


def fold_m_of_bits(bits: List[int], F: List[int]) -> Tuple[int, List[int]]:
    """
    bits: length m list of 0/1, indexed i=1..m as bits[i-1], weight F_{i+1}
    Returns (x_int, x_bits) where x_bits length m is (z2..z_{m+1}).
    """
    m = len(bits)
    N = 0
    for i, b in enumerate(bits, start=1):
        if b:
            N += F[i + 1]
    z = zeckendorf_digits(N, F)

    x_bits = []
    for k in range(2, m + 2):  # z2..z_{m+1}
        x_bits.append(1 if z.get(k, 0) else 0)

    x_int = 0
    for b in x_bits:
        x_int = (x_int << 1) | b
    return x_int, x_bits


def int_to_bits(x: int, m: int) -> List[int]:
    return [(x >> (m - 1 - i)) & 1 for i in range(m)]


@dataclass(frozen=True)
class ScanSummary:
    m: int
    num_inputs: int
    num_outputs_distinct: int
    max_fiber: int
    avg_fiber: float
    H_X: float
    H_Omega_given_X: float
    residual_counts_by_depth: List[int]  # length m+1, depth 0..m
    residual_counts_pred_by_depth: List[int]  # length m+1, depth 0..m
    residual_counts_match_pred: bool

@dataclass(frozen=True)
class GeneralizationRow:
    name: str
    k: int
    sum_w: int
    interval_cover: bool
    reachable_count: int
    predicted_count: int


def residual_spectrum_from_leaf_labels(leaf_labels: List[int], m: int) -> List[int]:
    """
    Build depth-wise right-equivalence classes by bottom-up merging.

    leaf_labels: length 2^m list; label is output id (x_int) for each full word.
    We compute unique signature counts per depth (depth 0..m), without merging across depths.
    """
    if len(leaf_labels) != (1 << m):
        raise ValueError("leaf_labels length must be 2^m")

    # Depth m: leaf state ids are just output labels, but compress to ids per output.
    label_to_id: Dict[int, int] = {}
    ids_depth = [0] * (1 << m)
    next_id = 0
    for i, lab in enumerate(leaf_labels):
        if lab not in label_to_id:
            label_to_id[lab] = next_id
            next_id += 1
        ids_depth[i] = label_to_id[lab]

    counts_by_depth = [0] * (m + 1)
    counts_by_depth[m] = next_id

    # Move upward: at depth k we have 2^k prefixes, each signature is (child0_id, child1_id).
    for k in range(m - 1, -1, -1):
        num_nodes = 1 << k
        sig_to_id: Dict[Tuple[int, int], int] = {}
        ids_next = [0] * num_nodes
        next_id = 0
        for p in range(num_nodes):
            c0 = ids_depth[2 * p]
            c1 = ids_depth[2 * p + 1]
            sig = (c0, c1)
            if sig not in sig_to_id:
                sig_to_id[sig] = next_id
                next_id += 1
            ids_next[p] = sig_to_id[sig]
        counts_by_depth[k] = next_id
        ids_depth = ids_next
    return counts_by_depth


def predicted_residual_counts_by_depth(m: int) -> List[int]:
    """
    Empirically observed closed form for Fold_m right-equivalence:
      |U_{m,k}| = F_{k+3} - 1  for 0 <= k < m,
      |U_{m,m}| = |X_m| = F_{m+2}.

    We compute the corresponding list for k=0..m.
    """
    out = []
    for k in range(0, m):
        out.append(fib(k + 3) - 1)
    out.append(fib(m + 2))
    return out


def _write_tex(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _format_table_residual(summary: List[ScanSummary]) -> str:
    lines = []
    lines.append("% Auto-generated. Do not edit by hand.")
    lines.append("\\begin{remark}")
    lines.append("残差规模扫描摘要（右等价类数）：")
    lines.append("\\end{remark}")
    lines.append("\\begin{center}")
    lines.append("\\begin{tabular}{rrrrr}")
    lines.append("\\toprule")
    lines.append("$m$ & $|X_m|$ & $\\max_x|F_m(x)|$ & $2^m/|X_m|$ & $|U_{m,\\lfloor m/2\\rfloor}|$ \\\\")
    lines.append("\\midrule")
    for s in summary:
        mid = s.residual_counts_by_depth[s.m // 2]
        lines.append(f"{s.m} & {s.num_outputs_distinct} & {s.max_fiber} & {s.avg_fiber:.6g} & {mid} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    return "\n".join(lines) + "\n"

def _format_residual_spectrum_example(s: ScanSummary) -> str:
    lines = []
    lines.append("% Auto-generated. Do not edit by hand.")
    lines.append("\\begin{remark}")
    lines.append(f"残差规模谱示例：取 $m={s.m}$，列出深度 $k$ 与 $|U_{{m,k}}|$。")
    lines.append("\\end{remark}")
    lines.append("\\begin{center}")
    lines.append("\\begin{tabular}{rr}")
    lines.append("\\toprule")
    lines.append("$k$ & $|U_{m,k}|$ \\\\")
    lines.append("\\midrule")
    for k, v in enumerate(s.residual_counts_by_depth):
        lines.append(f"{k} & {v} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    return "\n".join(lines) + "\n"

def _format_residual_pred_check(summary: List[ScanSummary]) -> str:
    lines = []
    lines.append("% Auto-generated. Do not edit by hand.")
    lines.append("\\begin{remark}")
    lines.append("残差规模谱的闭式核对：对每个 $m$，检查观测到的 $|U_{m,k}|$ 是否满足 $|U_{m,k}|=F_{k+3}-1$（$k<m$）且 $|U_{m,m}|=F_{m+2}$。")
    lines.append("\\end{remark}")
    lines.append("\\begin{center}")
    lines.append("\\begin{tabular}{rrrr}")
    lines.append("\\toprule")
    lines.append("$m$ & $\\max_k\\,|U_{m,k}-U^{\\mathrm{pred}}_{m,k}|$ & 是否全匹配 & 备注 \\\\")
    lines.append("\\midrule")
    for s in summary:
        diffs = [abs(a - b) for a, b in zip(s.residual_counts_by_depth, s.residual_counts_pred_by_depth)]
        md = max(diffs) if diffs else 0
        ok = "是" if s.residual_counts_match_pred else "否"
        note = "" if s.residual_counts_match_pred else "存在偏差"
        lines.append(f"{s.m} & {md} & {ok} & {note} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    return "\n".join(lines) + "\n"

def _format_generalization_table(rows: List[GeneralizationRow]) -> str:
    lines: List[str] = []
    lines.append("% Auto-generated. Do not edit by hand.")
    lines.append("\\begin{remark}")
    lines.append("一般化模板的数值核对：给定权重 $w_1,\\dots,w_k$，以恒等编码 $\\mathrm{Enc}(n)=n$ 作为单射窗口例子，")
    lines.append("则深度 $k$ 的右等价类数等于可达子集和个数。若满足区间覆盖条件，则预测值为 $\\sum_i w_i+1$。")
    lines.append("\\end{remark}")
    lines.append("\\begin{center}")
    lines.append("\\begin{tabular}{lrrrrr}")
    lines.append("\\toprule")
    lines.append("family & $k$ & $\\sum w_i$ & interval & reachable & predicted \\\\")
    lines.append("\\midrule")
    for r in rows:
        interval = "是" if r.interval_cover else "否"
        lines.append(f"{r.name} & {r.k} & {r.sum_w} & {interval} & {r.reachable_count} & {r.predicted_count} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    return "\n".join(lines) + "\n"


def _format_fiber_summary(summary: List[ScanSummary]) -> str:
    lines = []
    lines.append("% Auto-generated. Do not edit by hand.")
    lines.append("\\begin{remark}")
    lines.append("纤维谱摘要：给出平均/最大纤维规模，以及输出熵 $H(X_m)$ 与条件熵 $H(\\Omega_m\\mid X_m)=m-H(X_m)$。")
    lines.append("\\end{remark}")
    lines.append("\\begin{center}")
    lines.append("\\begin{tabular}{rrrrrr}")
    lines.append("\\toprule")
    lines.append("$m$ & $|X_m|$ & $\\max_x|F_m(x)|$ & $2^m/|X_m|$ & $H(X_m)$ & $H(\\Omega_m\\mid X_m)$ \\\\")
    lines.append("\\midrule")
    for s in summary:
        lines.append(
            f"{s.m} & {s.num_outputs_distinct} & {s.max_fiber} & {s.avg_fiber:.6g} & {s.H_X:.6g} & {s.H_Omega_given_X:.6g} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    return "\n".join(lines) + "\n"


def run_experiment(paper_dir: Path, mmax: int) -> None:
    gen_dir = paper_dir / "sections" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)

    summaries: List[ScanSummary] = []
    t0 = time.time()
    last_print = t0

    for m in range(1, mmax + 1):
        now = time.time()
        if now - last_print >= 20:
            print(f"[exp] progress m={m}/{mmax} elapsed={now - t0:.1f}s")
            last_print = now

        # Need fib numbers up to about m+5 to be safe.
        F = fib_up_to(m + 6)

        leaf_labels: List[int] = [0] * (1 << m)
        fiber_counts: Dict[int, int] = {}

        for idx in range(1 << m):
            bits = int_to_bits(idx, m)
            x_int, _ = fold_m_of_bits(bits, F)
            leaf_labels[idx] = x_int
            fiber_counts[x_int] = fiber_counts.get(x_int, 0) + 1

        num_outputs_distinct = len(fiber_counts)
        max_fiber = max(fiber_counts.values()) if fiber_counts else 0
        avg_fiber = (1 << m) / max(num_outputs_distinct, 1)

        # Entropy of output distribution induced by uniform over Omega_m
        H_X = 0.0
        for c in fiber_counts.values():
            p = c / (1 << m)
            H_X -= p * math.log2(p)
        H_Omega_given_X = m - H_X

        residual_counts = residual_spectrum_from_leaf_labels(leaf_labels, m)
        residual_counts_pred = predicted_residual_counts_by_depth(m)
        residual_counts_match_pred = residual_counts == residual_counts_pred

        summaries.append(
            ScanSummary(
                m=m,
                num_inputs=(1 << m),
                num_outputs_distinct=num_outputs_distinct,
                max_fiber=max_fiber,
                avg_fiber=avg_fiber,
                H_X=H_X,
                H_Omega_given_X=H_Omega_given_X,
                residual_counts_by_depth=residual_counts,
                residual_counts_pred_by_depth=residual_counts_pred,
                residual_counts_match_pred=residual_counts_match_pred,
            )
        )

    # Generalization sanity-checks for Theorem 5.2 template (Enc = identity).
    general_rows: List[GeneralizationRow] = []
    # Keep k moderate so it runs fast and stays readable.
    for k in [8, 12, 16, 20]:
        # Binary weights: 1,2,4,... satisfy interval condition and give 2^k sums.
        w_bin = [1 << i for i in range(k)]
        cnt, s = subset_sum_count(w_bin)
        general_rows.append(
            GeneralizationRow(
                name="binary",
                k=k,
                sum_w=s,
                interval_cover=interval_cover_holds(w_bin),
                reachable_count=cnt,
                predicted_count=s + 1,
            )
        )

        # Fibonacci weights (shifted): 1,2,3,5,... also satisfy interval condition.
        w_fib = [fib(i + 2) for i in range(1, k + 1)]  # F3..F_{k+2}, starts with 2? adjust to start with 1
        # Make it start with 1 by using F2..F_{k+1}
        w_fib = [fib(i + 1) for i in range(1, k + 1)]  # F2..F_{k+1} = 1,2,3,5,...
        cnt, s = subset_sum_count(w_fib)
        general_rows.append(
            GeneralizationRow(
                name="fibonacci",
                k=k,
                sum_w=s,
                interval_cover=interval_cover_holds(w_fib),
                reachable_count=cnt,
                predicted_count=s + 1,
            )
        )

    summary_json = {
        "paper": "2026_fold_residual_minimal_automaton",
        "mmax": mmax,
        "rows": [
            {
                "m": s.m,
                "num_inputs": s.num_inputs,
                "num_outputs_distinct": s.num_outputs_distinct,
                "max_fiber": s.max_fiber,
                "avg_fiber": s.avg_fiber,
                "H_X": s.H_X,
                "H_Omega_given_X": s.H_Omega_given_X,
                "residual_counts_by_depth": s.residual_counts_by_depth,
                "residual_counts_pred_by_depth": s.residual_counts_pred_by_depth,
                "residual_counts_match_pred": s.residual_counts_match_pred,
            }
            for s in summaries
        ],
        "generalization_rows": [
            {
                "name": r.name,
                "k": r.k,
                "sum_w": r.sum_w,
                "interval_cover": r.interval_cover,
                "reachable_count": r.reachable_count,
                "predicted_count": r.predicted_count,
            }
            for r in general_rows
        ],
    }
    (gen_dir / "summary.json").write_text(json.dumps(summary_json, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_tex(gen_dir / "residual_state_counts_summary.tex", _format_table_residual(summaries))
    _write_tex(gen_dir / "residual_spectrum_example.tex", _format_residual_spectrum_example(summaries[-1]))
    _write_tex(gen_dir / "residual_pred_check.tex", _format_residual_pred_check(summaries))
    _write_tex(gen_dir / "fiber_spectrum_summary.tex", _format_fiber_summary(summaries))
    _write_tex(gen_dir / "generalization_weight_table.tex", _format_generalization_table(general_rows))

    print(f"[exp] wrote {gen_dir / 'summary.json'}")

