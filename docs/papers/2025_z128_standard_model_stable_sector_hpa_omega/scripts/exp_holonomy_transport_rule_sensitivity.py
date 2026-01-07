# -*- coding: utf-8 -*-
"""
Transport-rule sensitivity audit (padding / truncation / cost tie-breaks).

The finite connection used in Section I_21 (and in the extended holonomy sweeps)
is defined by:
  - selecting a fixed rank-D=4 padded/truncated fiber representative for each stable type,
  - choosing a minimum-cost bijection between endpoint fibers on each edge.

This script audits how sensitive the *gauge-invariant* plaquette holonomy cycle-type
distribution and basic edge-cost statistics are under a bounded counterfactual family
of such transport rules.

We keep the family finite and fully explicit:
  - fiber selection (when |P(w)|>=4): head4 / tail4 / spread4,
  - padding (when |P(w)|<4): pad_last / pad_first / pad_cycle,
  - cost rule: Hamming only, or Hamming with a secondary tie-break (abs diff / weight diff).

We report, for a small set of representative balanced anchors (n,m)=(3,6),(4,8),
the baseline metrics and the min/max envelope across the counterfactual family.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_transport_rule_sensitivity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import exp_foldm_stats as foldm
import exp_hilbert_chirality_index as hil
from common_tex import write_lines


Coord = Tuple[int, int]
Perm4 = Tuple[int, int, int, int]


@dataclass(frozen=True)
class Rule:
    fiber_select: str  # head4 | tail4 | spread4
    pad: str  # pad_last | pad_first | pad_cycle
    cost: str  # H | H+abs | H+wt

    def label(self) -> str:
        return f"{self.fiber_select}/{self.pad}/{self.cost}"


def _tex_escape_texttt(s: str) -> str:
    """
    Minimal escaping for content placed inside \\texttt{...}.
    """
    return s.replace("_", "\\_")


def _quantile(sorted_vals: List[int], q: float) -> int:
    if not sorted_vals:
        raise ValueError("quantile requires a non-empty list.")
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be in [0,1].")
    n = len(sorted_vals)
    idx = int(round(q * float(n - 1)))
    return int(sorted_vals[idx])


def _compose(p: Perm4, q: Perm4) -> Perm4:
    # p ∘ q (apply q then p)
    return (p[q[0]], p[q[1]], p[q[2]], p[q[3]])


def _inv_perm(p: Perm4) -> Perm4:
    inv = [0, 0, 0, 0]
    for i, j in enumerate(p):
        inv[j] = i
    return (inv[0], inv[1], inv[2], inv[3])


def _cycle_type(p: Perm4) -> str:
    # Canonical cycle-type string for S4: 1, 2, 2x2, 3, 4.
    seen = [False, False, False, False]
    lengths: List[int] = []
    for i in range(4):
        if seen[i]:
            continue
        j = i
        k = 0
        while not seen[j]:
            seen[j] = True
            j = p[j]
            k += 1
        lengths.append(k)
    lengths.sort(reverse=True)
    if lengths == [1, 1, 1, 1]:
        return "1"
    if lengths == [2, 1, 1]:
        return "2"
    if lengths == [2, 2]:
        return "2x2"
    if lengths == [3, 1]:
        return "3"
    if lengths == [4]:
        return "4"
    return "other"


def _grid_labels(n_bits: int, m: int, outs: List[str]) -> Dict[Coord, str]:
    path = hil.hilbert_curve(n_bits)
    idx_of: Dict[Coord, int] = {}
    for k, c in enumerate(path):
        idx_of[(int(c[0]), int(c[1]))] = k
    out: Dict[Coord, str] = {}
    for coord, k in idx_of.items():
        out[coord] = outs[k]
    return out


def _preimages(m: int, outs: List[str]) -> Dict[str, List[int]]:
    pre: Dict[str, List[int]] = defaultdict(list)
    for k in range(1 << m):
        pre[outs[k]].append(k)
    for w in pre:
        pre[w] = sorted(pre[w])
    return dict(pre)


def _fiber4(pre: Dict[str, List[int]], w: str, rule: Rule) -> List[int]:
    xs = list(pre[w])
    if not xs:
        raise AssertionError("Empty fiber.")
    xs.sort()
    base: List[int]
    if len(xs) >= 4:
        if rule.fiber_select == "head4":
            base = xs[:4]
        elif rule.fiber_select == "tail4":
            base = xs[-4:]
        elif rule.fiber_select == "spread4":
            # Deterministic spread: two smallest + two largest.
            base = [xs[0], xs[1], xs[-2], xs[-1]]
        else:
            raise ValueError(f"Unknown fiber_select: {rule.fiber_select}")
    else:
        base = xs[:]

    if len(base) == 4:
        return base

    if rule.pad == "pad_last":
        while len(base) < 4:
            base.append(base[-1])
        return base
    if rule.pad == "pad_first":
        while len(base) < 4:
            base.append(base[0])
        return base
    if rule.pad == "pad_cycle":
        if len(base) == 0:
            raise AssertionError("Empty base fiber.")
        k = 0
        while len(base) < 4:
            base.append(base[k % len(xs)])
            k += 1
        return base[:4]
    raise ValueError(f"Unknown pad: {rule.pad}")


def _edge_cost_pair(x: int, y: int) -> Tuple[int, int, int]:
    # (Hamming, abs diff, weight diff)
    h = (x ^ y).bit_count()
    d = abs(x - y)
    w = abs(x.bit_count() - y.bit_count())
    return int(h), int(d), int(w)


def _best_perm(fa: List[int], fb: List[int], rule: Rule) -> Tuple[Perm4, int]:
    """
    Return (perm, primary_hamming_sum).
    Deterministic tie-break includes the permutation itself as the final key.
    """
    best_key = None
    best_perm: Perm4 | None = None
    best_h = 0
    for p in itertools.permutations((0, 1, 2, 3), 4):
        sh = 0
        sd = 0
        sw = 0
        for i in range(4):
            h, d, w = _edge_cost_pair(fa[i], fb[p[i]])
            sh += h
            sd += d
            sw += w
        if rule.cost == "H":
            key = (sh, p)
        elif rule.cost == "H+abs":
            key = (sh, sd, p)
        elif rule.cost == "H+wt":
            key = (sh, sw, p)
        else:
            raise ValueError(f"Unknown cost rule: {rule.cost}")
        if best_key is None or key < best_key:
            best_key = key
            best_perm = p
            best_h = sh
    if best_perm is None:
        raise AssertionError("No permutations enumerated.")
    return best_perm, int(best_h)


def _edge_perm_cache(n_bits: int, m: int, labels: Dict[Coord, str], pre: Dict[str, List[int]], rule: Rule) -> Tuple[Dict[Tuple[Coord, Coord], Perm4], List[int]]:
    """
    Return (oriented edge perms, list of primary costs for undirected edges).
    """
    N = 1 << n_bits
    undirected: Dict[Tuple[Coord, Coord], Perm4] = {}
    costs: List[int] = []

    def key(a: Coord, b: Coord) -> Tuple[Coord, Coord]:
        return (a, b) if a < b else (b, a)

    for x in range(N):
        for y in range(N):
            a = (x, y)
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx >= N or ny >= N:
                    continue
                b = (nx, ny)
                ka, kb = key(a, b)
                if (ka, kb) in undirected:
                    continue
                wa = labels[ka]
                wb = labels[kb]
                fa = _fiber4(pre, wa, rule=rule)
                fb = _fiber4(pre, wb, rule=rule)
                p, cost_h = _best_perm(fa, fb, rule=rule)
                undirected[(ka, kb)] = p
                costs.append(int(cost_h))

    out: Dict[Tuple[Coord, Coord], Perm4] = {}
    for (a, b), p in undirected.items():
        out[(a, b)] = p
        out[(b, a)] = _inv_perm(p)
    return out, costs


@dataclass(frozen=True)
class Metrics:
    edge_q50: int
    edge_q90: int
    cycle_fracs: Dict[str, float]  # keys in {"1","2","2x2","3","4","other"}

    def frac34(self) -> float:
        return float(self.cycle_fracs.get("3", 0.0) + self.cycle_fracs.get("4", 0.0))


def _compute_metrics(n_bits: int, m: int, rule: Rule) -> Metrics:
    outs = foldm.cached_foldm_outputs(m)
    labels = _grid_labels(n_bits=n_bits, m=m, outs=outs)
    pre = _preimages(m=m, outs=outs)
    edge_p, costs = _edge_perm_cache(n_bits=n_bits, m=m, labels=labels, pre=pre, rule=rule)

    costs_sorted = sorted(int(c) for c in costs)
    q50 = _quantile(costs_sorted, 0.50)
    q90 = _quantile(costs_sorted, 0.90)

    N = 1 << n_bits
    hist = Counter()
    total = 0
    for x in range(N - 1):
        for y in range(N - 1):
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)
            p_ab = edge_p[(a, b)]
            p_bc = edge_p[(b, c)]
            p_cd = edge_p[(c, d)]
            p_da = edge_p[(d, a)]
            hol = _compose(p_da, _compose(p_cd, _compose(p_bc, p_ab)))
            hist[_cycle_type(hol)] += 1
            total += 1
    if total <= 0:
        raise AssertionError("No plaquettes.")
    fracs = {k: float(hist.get(k, 0)) / float(total) for k in ["1", "2", "2x2", "3", "4", "other"]}
    return Metrics(edge_q50=int(q50), edge_q90=int(q90), cycle_fracs=fracs)


def _tv_distance(p: Dict[str, float], q: Dict[str, float]) -> float:
    keys = ["1", "2", "2x2", "3", "4", "other"]
    return 0.5 * sum(abs(float(p.get(k, 0.0)) - float(q.get(k, 0.0))) for k in keys)


@dataclass(frozen=True)
class SummaryRow:
    n_bits: int
    m: int
    rules: List[Rule]
    baseline: Rule
    baseline_metrics: Metrics
    frac34_min: float
    frac34_max: float
    frac34_dmax: float
    tv_max: float
    q50_min: int
    q50_max: int
    q50_dmax: int
    worst_tv_rule: Rule


def summarize_block(n_bits: int, m: int, rules: List[Rule], baseline: Rule) -> SummaryRow:
    base = _compute_metrics(n_bits=n_bits, m=m, rule=baseline)
    frac34_min = base.frac34()
    frac34_max = base.frac34()
    frac34_dmax = 0.0
    tv_max = 0.0
    worst_tv_rule = baseline
    q50_min = base.edge_q50
    q50_max = base.edge_q50
    q50_dmax = 0

    for r in rules:
        met = _compute_metrics(n_bits=n_bits, m=m, rule=r)
        f = met.frac34()
        frac34_min = min(frac34_min, f)
        frac34_max = max(frac34_max, f)
        frac34_dmax = max(frac34_dmax, abs(f - base.frac34()))
        tv = _tv_distance(met.cycle_fracs, base.cycle_fracs)
        if tv > tv_max:
            tv_max = tv
            worst_tv_rule = r
        q50_min = min(q50_min, met.edge_q50)
        q50_max = max(q50_max, met.edge_q50)
        q50_dmax = max(q50_dmax, abs(int(met.edge_q50) - int(base.edge_q50)))

    return SummaryRow(
        n_bits=int(n_bits),
        m=int(m),
        rules=list(rules),
        baseline=baseline,
        baseline_metrics=base,
        frac34_min=float(frac34_min),
        frac34_max=float(frac34_max),
        frac34_dmax=float(frac34_dmax),
        tv_max=float(tv_max),
        q50_min=int(q50_min),
        q50_max=int(q50_max),
        q50_dmax=int(q50_dmax),
        worst_tv_rule=worst_tv_rule,
    )


def main() -> None:
    blocks = [(3, 6), (4, 8)]
    baseline = Rule("head4", "pad_last", "H")
    fiber_selects = ["head4", "tail4", "spread4"]
    pads_minimal = ["pad_last", "pad_first"]
    costs_tiebreak = ["H", "H+abs", "H+wt"]

    # Family A (structural counterfactuals): vary fiber selection and minimal padding;
    # keep the objective strictly Hamming (baseline cost) to isolate padding/truncation.
    rules_pad_select = [Rule(fs, pd, "H") for fs in fiber_selects for pd in pads_minimal]

    # Family B (tie-break counterfactuals): vary only the (secondary) tie-break under
    # the same primary Hamming objective; keep padding/selection at the baseline.
    rules_cost_tiebreak = [Rule("head4", "pad_last", cs) for cs in costs_tiebreak]

    rows: List[str] = []
    for n_bits, m in blocks:
        for family_name, fam_rules in [
            ("pad/select (H only)", rules_pad_select),
            ("cost tie-break", rules_cost_tiebreak),
        ]:
            summ = summarize_block(n_bits=n_bits, m=m, rules=fam_rules, baseline=baseline)
            base = summ.baseline_metrics
            frac34_base = base.frac34()
            row = " & ".join(
                [
                    f"$(n,m)=({summ.n_bits},{summ.m})$",
                    f"\\texttt{{{_tex_escape_texttt(family_name)}}}",
                    str(len(fam_rules)),
                    f"\\texttt{{{_tex_escape_texttt(baseline.label())}}}",
                    f"{frac34_base:.3f}",
                    f"{summ.frac34_min:.3f}",
                    f"{summ.frac34_max:.3f}",
                    f"{summ.frac34_dmax:.3f}",
                    f"{summ.tv_max:.3f}",
                    f"{base.edge_q50}",
                    f"{summ.q50_min}",
                    f"{summ.q50_max}",
                    f"{summ.q50_dmax}",
                    f"\\texttt{{{_tex_escape_texttt(summ.worst_tv_rule.label())}}}",
                ]
            )
            rows.append(row + " \\\\")
    rows.append("\\bottomrule")

    out_path = Path(__file__).resolve().parent.parent / "sections" / "generated" / "holonomy_transport_rule_sensitivity_rows.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_lines(out_path, rows)
    print(f"Wrote sections/generated/{out_path.name}")


if __name__ == "__main__":
    main()


