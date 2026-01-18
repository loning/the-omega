# -*- coding: utf-8 -*-
"""
ISA-M4: Hilbert locality as a testable hypothesis (m=6, N in [0,63]).

We map the 6-bit microstate index N to 2D Hilbert(n=3) coordinates on an 8x8 grid:
  N -> (x,y) where (x,y) ∈ {0..7}^2 and n=3 means 2^3=8.

We then test two purely-combinatorial hypotheses:

1) AA clustering: codons encoding the same amino acid (payload class) are
   unusually clustered on the Hilbert plane compared to nulls.
   - Metric: within-AA mean pairwise Manhattan distance (weighted by #pairs).
   - Metric: within-AA mean nearest-neighbor Manhattan distance (per codon).
   - Nulls:
       (a) encoding-null: all 24 two-bit encodings (genetic code fixed)
       (b) code-null: Monte Carlo random genetic codes preserving codon counts

2) Mutation locality: single-nucleotide substitutions correspond to short Hilbert
   jumps more often at position-3 than at positions 1/2 (wobble-style locality).

Outputs:
  - sections/generated/hilbert_locality_audit.tex
  - sections/generated/hilbert_locality_audit.tex.meta.json

Standard library only.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import BASES, GENETIC_CODE, all_encodings, fold_codon


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _mutate(codon: str, pos0: int, base: str) -> str:
    return codon[:pos0] + base + codon[pos0 + 1 :]


def _rot(s: int, x: int, y: int, rx: int, ry: int) -> tuple[int, int]:
    if ry == 0:
        if rx == 1:
            x = s - 1 - x
            y = s - 1 - y
        x, y = y, x
    return x, y


def hilbert_d2xy(n_side: int, d: int) -> tuple[int, int]:
    """
    Convert Hilbert curve index d to (x,y) on an n_side x n_side grid, where n_side is a power of 2.
    Reference algorithm: Wikipedia "Hilbert curve" d2xy.
    """
    if n_side <= 0 or (n_side & (n_side - 1)) != 0:
        raise ValueError("n_side must be a power of 2")
    if d < 0 or d >= n_side * n_side:
        raise ValueError("d out of range")
    x = 0
    y = 0
    t = int(d)
    s = 1
    while s < n_side:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        x, y = _rot(s, x, y, int(rx), int(ry))
        x += s * int(rx)
        y += s * int(ry)
        t //= 4
        s *= 2
    return int(x), int(y)


def _coords_by_codon(mu: dict[str, str]) -> dict[str, tuple[int, int]]:
    coords: dict[str, tuple[int, int]] = {}
    for codon in sorted(GENETIC_CODE.keys()):
        n = int(fold_codon(codon, mu).n)
        coords[codon] = hilbert_d2xy(8, n)
    return coords


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))


def _aa_groups(code: dict[str, str], coords: dict[str, tuple[int, int]], *, exclude_stop: bool) -> dict[str, list[tuple[int, int]]]:
    groups: dict[str, list[tuple[int, int]]] = {}
    for codon, aa in code.items():
        if exclude_stop and aa == "Stop":
            continue
        groups.setdefault(aa, []).append(coords[codon])
    return groups


def _within_group_mean_pairwise_distance(groups: dict[str, list[tuple[int, int]]]) -> float | None:
    total_pairs = 0
    total_dist = 0
    for pts in groups.values():
        m = len(pts)
        if m < 2:
            continue
        for i in range(m):
            for j in range(i + 1, m):
                total_dist += _manhattan(pts[i], pts[j])
                total_pairs += 1
    if total_pairs <= 0:
        return None
    return float(total_dist) / float(total_pairs)


def _within_group_mean_nearest_neighbor_distance(groups: dict[str, list[tuple[int, int]]]) -> float | None:
    total = 0
    total_dist = 0
    for pts in groups.values():
        m = len(pts)
        if m < 2:
            continue
        for i in range(m):
            best = None
            for j in range(m):
                if i == j:
                    continue
                d = _manhattan(pts[i], pts[j])
                if best is None or d < best:
                    best = int(d)
            if best is None:
                continue
            total_dist += int(best)
            total += 1
    if total <= 0:
        return None
    return float(total_dist) / float(total)


def _random_code_preserving_degeneracy(
    *, rng: random.Random, codons: list[str], degeneracy: Counter[str]
) -> dict[str, str]:
    labels: list[str] = []
    for aa in sorted(degeneracy.keys()):
        labels.extend([aa] * int(degeneracy[aa]))
    if len(labels) != len(codons):
        raise AssertionError("Degeneracy counts do not sum to 64.")
    rng.shuffle(labels)
    return {codons[i]: labels[i] for i in range(len(codons))}


def _empirical_p_one_sided_low(obs: float, nulls: list[float]) -> float:
    """
    One-sided p-value for "obs is unusually low" under the null (plus-one smoothing).
    """
    if not nulls:
        return float("nan")
    le = sum(1 for v in nulls if v <= obs)
    return float((le + 1) / (len(nulls) + 1))


def _fmt_float(x: float | None, *, nd: int = 3) -> str:
    if x is None or math.isnan(float(x)):
        return "NA"
    return f"{float(x):.{int(nd)}f}"


def _fmt_p(p: float | None) -> str:
    if p is None or math.isnan(float(p)):
        return "NA"
    if float(p) < 1e-4:
        return "$<10^{-4}$"
    return f"{float(p):.4f}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ISA-M4: Hilbert locality audit on N∈[0,63].")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "hilbert_locality_audit.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--n-null", type=int, default=20000, help="Number of random-code null samples (degeneracy-preserving).")
    p.add_argument("--seed", type=int, default=0, help="RNG seed for code-null Monte Carlo.")
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_tex = Path(args.out_tex)

    cache_key: dict[str, Any] = {
        "analysis": "hilbert_locality_audit",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "n_null": int(args.n_null),
        "seed": int(args.seed),
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    codons = sorted(GENETIC_CODE.keys())
    degeneracy = Counter(GENETIC_CODE.values())

    # AA clustering metrics under μ*.
    coords_mu_star = _coords_by_codon(MU_STAR)
    groups_mu_star = _aa_groups(GENETIC_CODE, coords_mu_star, exclude_stop=True)
    within_pair_mu = _within_group_mean_pairwise_distance(groups_mu_star)
    within_nn_mu = _within_group_mean_nearest_neighbor_distance(groups_mu_star)

    # Encoding-null over 24 encodings (genetic code fixed).
    enc_within_pair: list[float] = []
    enc_within_nn: list[float] = []
    for mu in all_encodings():
        coords = _coords_by_codon(mu)
        groups = _aa_groups(GENETIC_CODE, coords, exclude_stop=True)
        v_pair = _within_group_mean_pairwise_distance(groups)
        v_nn = _within_group_mean_nearest_neighbor_distance(groups)
        if v_pair is not None:
            enc_within_pair.append(float(v_pair))
        if v_nn is not None:
            enc_within_nn.append(float(v_nn))

    # Rank of μ* among 24 encodings (smaller = more clustered).
    def rank_asc(values: list[float], target: float | None) -> int | None:
        if target is None or not values:
            return None
        s = sorted(values)
        return int(1 + sum(1 for v in s if v < float(target)))

    rank_pair = rank_asc(enc_within_pair, within_pair_mu)
    rank_nn = rank_asc(enc_within_nn, within_nn_mu)

    # Code-null: degeneracy-preserving random genetic codes (coords fixed to μ*).
    rng = random.Random(int(args.seed))
    null_pair: list[float] = []
    null_nn: list[float] = []
    for _ in range(int(args.n_null)):
        code_rnd = _random_code_preserving_degeneracy(rng=rng, codons=codons, degeneracy=degeneracy)
        groups = _aa_groups(code_rnd, coords_mu_star, exclude_stop=True)
        v_pair = _within_group_mean_pairwise_distance(groups)
        v_nn = _within_group_mean_nearest_neighbor_distance(groups)
        if v_pair is not None:
            null_pair.append(float(v_pair))
        if v_nn is not None:
            null_nn.append(float(v_nn))

    null_pair_mean = statistics.mean(null_pair) if null_pair else None
    null_pair_std = statistics.pstdev(null_pair) if len(null_pair) >= 2 else None
    null_nn_mean = statistics.mean(null_nn) if null_nn else None
    null_nn_std = statistics.pstdev(null_nn) if len(null_nn) >= 2 else None

    p_pair = _empirical_p_one_sided_low(float(within_pair_mu), null_pair) if within_pair_mu is not None else None
    p_nn = _empirical_p_one_sided_low(float(within_nn_mu), null_nn) if within_nn_mu is not None else None

    # Mutation locality under μ*: Hilbert jump distances for single-nucleotide substitutions.
    jump_hist: dict[int, Counter[int]] = {0: Counter(), 1: Counter(), 2: Counter()}
    jump_mean: dict[int, float] = {}
    jump_local_rate: dict[int, float] = {}
    for pos0 in (0, 1, 2):
        dists: list[int] = []
        for codon in codons:
            p0 = coords_mu_star[codon]
            for b in BASES:
                if b == codon[pos0]:
                    continue
                codon2 = _mutate(codon, pos0, b)
                p1 = coords_mu_star[codon2]
                d = int(_manhattan(p0, p1))
                dists.append(d)
                jump_hist[pos0][d] += 1
        jump_mean[pos0] = float(sum(dists) / len(dists)) if dists else float("nan")
        jump_local_rate[pos0] = float(sum(1 for d in dists if d <= 1) / len(dists)) if dists else float("nan")

    # Emit LaTeX.
    lines: list[str] = []
    lines.append("\\paragraph{ISA-M4: Hilbert locality audit (n=3 on $N\\in[0,63]$).}")
    lines.append(
        "Map the 6-bit microstate index $N$ to Hilbert(n=3) coordinates on an $8\\times 8$ grid and test whether "
        "payload classes (AA; excluding Stop) are unusually clustered on this plane."
    )
    lines.append("")

    lines.append("\\noindent AA clustering metrics (smaller means more clustered):")
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\begin{tabular}{l r r r r r}")
    lines.append("\\toprule")
    lines.append("metric & value $(\\mu^\\ast)$ & rank$_{24}$ & null mean$\\pm$sd & $p_{\\mathrm{null}}$ & enc range \\\\")
    lines.append("\\midrule")
    lines.append(
        "within-AA mean pairwise $L_1$ & "
        f"{_fmt_float(within_pair_mu)} & {('NA' if rank_pair is None else str(int(rank_pair)) + '/24')} & "
        f"{_fmt_float(null_pair_mean)}$\\pm${_fmt_float(null_pair_std)} & {_fmt_p(p_pair)} & "
        f"[{_fmt_float(min(enc_within_pair) if enc_within_pair else None)}, {_fmt_float(max(enc_within_pair) if enc_within_pair else None)}] \\\\"
    )
    lines.append(
        "within-AA mean nearest-neighbor $L_1$ & "
        f"{_fmt_float(within_nn_mu)} & {('NA' if rank_nn is None else str(int(rank_nn)) + '/24')} & "
        f"{_fmt_float(null_nn_mean)}$\\pm${_fmt_float(null_nn_std)} & {_fmt_p(p_nn)} & "
        f"[{_fmt_float(min(enc_within_nn) if enc_within_nn else None)}, {_fmt_float(max(enc_within_nn) if enc_within_nn else None)}] \\\\"
    )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append(
        f"\\noindent Null details: encoding-null over 24 two-bit encodings; code-null is {int(args.n_null)} "
        f"degeneracy-preserving random codes (seed={int(args.seed)}), one-sided $p$ for lower clustering metrics."
    )
    lines.append("")

    # Mutation locality summary.
    lines.append("\\noindent Single-nucleotide mutation Hilbert jumps under $\\mu^\\ast$ (directed mutations; 192 per position):")
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\begin{tabular}{r r r l}")
    lines.append("\\toprule")
    lines.append("pos & $\\mathbb{E}\\,d_1$ & $p(d_1\\le 1)$ & histogram \\\\")
    lines.append("\\midrule")
    for pos0 in (0, 1, 2):
        parts = [f"{k}:{jump_hist[pos0][k]}" for k in sorted(jump_hist[pos0].keys())]
        lines.append(
            f"{pos0+1} & {_fmt_float(jump_mean[pos0])} & {_fmt_float(jump_local_rate[pos0], nd=4)} & $\\{{{', '.join(parts)}\\}}$ \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"[write] {out_tex}", flush=True)


if __name__ == "__main__":
    main()
