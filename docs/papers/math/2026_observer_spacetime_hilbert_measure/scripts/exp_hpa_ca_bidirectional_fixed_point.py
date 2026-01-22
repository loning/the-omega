#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bidirectional conservative observer experiment on HPA-CA/Fold6.

Goal
----
Given an observed *visible* stable slice at time t (symbol sequence y on ring),
recover some compatible preimage x (and hence hidden uplift labels) by a
fixed-point style solver:
  - domain reduction (arc consistency / message passing on binary constraints)
  - greedy commitments (finite observer)

We compare against the DFS baseline from the existing observer-time prototype.

Outputs
-------
- artifacts/export/hpa_ca_fixed_point_stats.csv
- artifacts/export/hpa_ca_fixed_point_energy_curve.png
- sections/generated/tab_hpa_ca_bidirectional_fixed_point.tex
- sections/generated/fig_hpa_ca_fixed_point_energy_curve.tex
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_hash import sha256_file
from common_paths import export_dir, generated_dir, paper_root
from common_tex_pylatex import write_lines_as_fragment, write_tabular_fragment


def _import_hpa_ca_tooling() -> Tuple[object, object, object]:
    """Import hpa_ca_lossless / hpa_ca_preimage_count / hpa_ca_inverse_search from the Fold6 paper."""
    this_root = Path(__file__).resolve().parents[1]
    math_root = this_root.parent
    ext_scripts = math_root / "2026_hpa_ca_fold6_lossless" / "scripts"
    if not ext_scripts.is_dir():
        raise RuntimeError(f"Missing external scripts dir: {ext_scripts}")
    if str(ext_scripts) not in sys.path:
        sys.path.insert(0, str(ext_scripts))

    import hpa_ca_lossless  # type: ignore
    import hpa_ca_preimage_count  # type: ignore
    import hpa_ca_inverse_search  # type: ignore

    return hpa_ca_lossless, hpa_ca_preimage_count, hpa_ca_inverse_search


def _bitcount(mask: int) -> int:
    return int(mask.bit_count())


def _pick_lowest_bit(mask: int) -> int:
    # mask != 0
    return int((mask & -mask).bit_length() - 1)


@dataclass(frozen=True)
class FixedPointRun:
    found: bool
    iters: int
    commits: int
    final_ambiguity: int
    curve: List[int]  # ambiguity curve per iteration/commit stage


@dataclass(frozen=True)
class BacktrackRun:
    found: bool
    nodes_visited: int
    backtracks: int
    depth: int
    final_ambiguity: int
    curve: List[int]


def build_succ_masks(succ: List[List[List[int]]]) -> Tuple[List[List[int]], List[List[int]]]:
    """Precompute masks for succ/pred for each y and a/b."""
    A = len(succ)
    succ_mask: List[List[int]] = [[0 for _ in range(A)] for _ in range(A)]
    pred_mask: List[List[int]] = [[0 for _ in range(A)] for _ in range(A)]
    for y in range(A):
        for a in range(A):
            m = 0
            for b in succ[y][a]:
                m |= 1 << int(b)
            succ_mask[y][a] = m
        for b in range(A):
            m = 0
            for a in range(A):
                if (succ_mask[y][a] >> b) & 1:
                    m |= 1 << a
            pred_mask[y][b] = m
    return succ_mask, pred_mask


def ac3_prune(dom: List[int], y: Sequence[int], succ_mask: List[List[int]], pred_mask: List[List[int]]) -> bool:
    """Enforce arc consistency on ring constraints y_i = f(x_i, x_{i+1})."""
    n = len(y)
    # queue contains edge indices i; we will attempt revise both directions on edge i
    q = list(range(n))
    in_q = [True] * n

    def revise_left(i: int) -> bool:
        """Revise dom[i] using dom[i+1] and succ_mask[y_i][a]."""
        nonlocal dom
        changed = False
        yi = int(y[i])
        j = (i + 1) % n
        Dj = dom[j]
        Di = dom[i]
        new_Di = 0
        # keep a if exists b in Dj with f(a,b)=y_i
        m = Di
        while m:
            a = _pick_lowest_bit(m)
            m &= m - 1
            if Dj & succ_mask[yi][a]:
                new_Di |= 1 << a
        if new_Di != Di:
            dom[i] = new_Di
            changed = True
        return changed

    def revise_right(i: int) -> bool:
        """Revise dom[i+1] using dom[i] and pred_mask[y_i][b]."""
        nonlocal dom
        changed = False
        yi = int(y[i])
        j = (i + 1) % n
        Di = dom[i]
        Dj = dom[j]
        new_Dj = 0
        m = Dj
        while m:
            b = _pick_lowest_bit(m)
            m &= m - 1
            if Di & pred_mask[yi][b]:
                new_Dj |= 1 << b
        if new_Dj != Dj:
            dom[j] = new_Dj
            changed = True
        return changed

    while q:
        i = q.pop()
        in_q[i] = False
        # if any domain becomes empty => infeasible
        if dom[i] == 0 or dom[(i + 1) % n] == 0:
            return False

        changed = False
        if revise_left(i):
            changed = True
        if revise_right(i):
            changed = True
        if changed:
            # neighboring edges affected
            for e in ((i - 1) % n, i, (i + 1) % n):
                if not in_q[e]:
                    q.append(e)
                    in_q[e] = True
    return True


def fixed_point_greedy(
    y: Sequence[int],
    succ_mask: List[List[int]],
    pred_mask: List[List[int]],
    max_iters: int,
) -> FixedPointRun:
    """Greedy fixed-point solver: AC-3 prune + greedy commits until singleton or failure."""
    n = len(y)
    A = len(succ_mask)
    full = (1 << A) - 1
    dom = [full] * n

    curve: List[int] = []
    commits = 0
    iters = 0

    def ambiguity() -> int:
        return sum(max(0, _bitcount(d) - 1) for d in dom)

    # initial prune
    if not ac3_prune(dom, y=y, succ_mask=succ_mask, pred_mask=pred_mask):
        return FixedPointRun(found=False, iters=0, commits=0, final_ambiguity=ambiguity(), curve=[ambiguity()])
    curve.append(ambiguity())

    while iters < max_iters:
        iters += 1
        amb = ambiguity()
        if amb == 0:
            return FixedPointRun(found=True, iters=iters, commits=commits, final_ambiguity=0, curve=curve)

        # choose var with smallest domain size > 1
        best_i = -1
        best_sz = 10**9
        for i, d in enumerate(dom):
            sz = _bitcount(d)
            if 1 < sz < best_sz:
                best_sz = sz
                best_i = i
        if best_i < 0:
            break

        # greedy choose a value deterministically (lowest)
        chosen = _pick_lowest_bit(dom[best_i])
        dom[best_i] = 1 << chosen
        commits += 1

        if not ac3_prune(dom, y=y, succ_mask=succ_mask, pred_mask=pred_mask):
            curve.append(ambiguity())
            return FixedPointRun(found=False, iters=iters, commits=commits, final_ambiguity=ambiguity(), curve=curve)
        curve.append(ambiguity())

    return FixedPointRun(found=(ambiguity() == 0), iters=iters, commits=commits, final_ambiguity=ambiguity(), curve=curve)


def fixed_point_bounded_backtracking(
    y: Sequence[int],
    succ_mask: List[List[int]],
    pred_mask: List[List[int]],
    max_depth: int,
    max_nodes: int,
    progress_every_nodes: int = 50000,
) -> BacktrackRun:
    """Bounded backtracking on top of AC-3 pruning (finite observer).

    - max_depth: maximum number of commitments along a branch
    - max_nodes: maximum node expansions (commit+propagate attempts)
    """

    n = len(y)
    A = len(succ_mask)
    full = (1 << A) - 1
    dom0 = [full] * n

    def ambiguity(dom: List[int]) -> int:
        return sum(max(0, _bitcount(d) - 1) for d in dom)

    if not ac3_prune(dom0, y=y, succ_mask=succ_mask, pred_mask=pred_mask):
        return BacktrackRun(found=False, nodes_visited=0, backtracks=0, depth=0, final_ambiguity=ambiguity(dom0), curve=[ambiguity(dom0)])

    nodes = 0
    backtracks = 0

    def choose_var(dom: List[int]) -> int:
        best_i = -1
        best_sz = 10**9
        for i, d in enumerate(dom):
            sz = _bitcount(d)
            if 1 < sz < best_sz:
                best_sz = sz
                best_i = i
        return best_i

    def iter_values(mask: int) -> List[int]:
        vals: List[int] = []
        m = mask
        while m:
            v = _pick_lowest_bit(m)
            vals.append(v)
            m &= m - 1
        return vals

    def rec(dom: List[int], depth: int, curve: List[int]) -> Tuple[bool, List[int], int]:
        nonlocal nodes, backtracks
        if nodes >= max_nodes:
            return False, curve, depth
        amb = ambiguity(dom)
        if amb == 0:
            return True, curve, depth
        if depth >= max_depth:
            return False, curve, depth

        i = choose_var(dom)
        if i < 0:
            return amb == 0, curve, depth

        for v in iter_values(dom[i]):
            if nodes >= max_nodes:
                return False, curve, depth
            nodes += 1
            if progress_every_nodes > 0 and nodes % progress_every_nodes == 0:
                print(f"[fp_bt] nodes={nodes} depth={depth} amb={amb}", flush=True)

            dom2 = dom.copy()
            dom2[i] = 1 << v
            ok = ac3_prune(dom2, y=y, succ_mask=succ_mask, pred_mask=pred_mask)
            c2 = curve + [ambiguity(dom2)]
            if not ok:
                backtracks += 1
                continue
            found, out_curve, out_depth = rec(dom2, depth + 1, c2)
            if found:
                return True, out_curve, out_depth
            backtracks += 1

        return False, curve, depth

    curve0 = [ambiguity(dom0)]
    found, curve_out, depth_out = rec(dom0, 0, curve0)
    return BacktrackRun(
        found=bool(found),
        nodes_visited=int(nodes),
        backtracks=int(backtracks),
        depth=int(depth_out),
        final_ambiguity=int(curve_out[-1] if curve_out else ambiguity(dom0)),
        curve=curve_out if curve_out else curve0,
    )


def pad_and_mean(curves: List[List[int]]) -> Tuple[List[int], List[float]]:
    if not curves:
        return [], []
    m = max(len(c) for c in curves)
    xs = list(range(m))
    ys: List[float] = []
    for i in range(m):
        vals = []
        for c in curves:
            vals.append(float(c[i] if i < len(c) else c[-1]))
        ys.append(float(np.mean(vals)))
    return xs, ys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=300)
    ap.add_argument("--T", type=int, default=200)
    ap.add_argument("--p", type=float, default=0.5)
    ap.add_argument("--t", type=int, default=200)
    ap.add_argument("--seeds", type=str, default="1,2,3,4,5")
    ap.add_argument("--max_iters", type=int, default=200)
    ap.add_argument("--bt_max_depth", type=int, default=80, help="bounded backtracking max depth (commitments)")
    ap.add_argument("--bt_max_nodes", type=int, default=200000, help="bounded backtracking node cap")
    ap.add_argument("--max_nodes_dfs", type=int, default=200000, help="DFS node cap (0 means unlimited)")
    ap.add_argument("--shuffle_dfs", action="store_true", help="shuffle DFS branching order")
    ap.add_argument("--shuffle_seed", type=int, default=1, help="RNG seed for DFS shuffling")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")
    if args.t < 1:
        raise SystemExit("t must be >= 1")

    hpa_ca_lossless, hpa_ca_preimage_count, hpa_ca_inverse_search = _import_hpa_ca_tooling()
    ext_dir = Path(hpa_ca_lossless.__file__).resolve().parent  # type: ignore[attr-defined]
    ext_files = ["hpa_ca_lossless.py", "hpa_ca_preimage_count.py", "hpa_ca_inverse_search.py"]
    extra = {nm: sha256_file(ext_dir / nm) for nm in ext_files if (ext_dir / nm).is_file()}

    script_path = Path(__file__).resolve()
    params = {
        "L": int(args.L),
        "T": int(args.T),
        "p": float(args.p),
        "t": int(args.t),
        "seeds": args.seeds,
        "max_iters": int(args.max_iters),
        "bt_max_depth": int(args.bt_max_depth),
        "bt_max_nodes": int(args.bt_max_nodes),
        "max_nodes_dfs": int(args.max_nodes_dfs),
        "shuffle_dfs": bool(args.shuffle_dfs),
        "shuffle_seed": int(args.shuffle_seed),
    }

    out_csv = "hpa_ca_fixed_point_stats.csv"
    out_png = "hpa_ca_fixed_point_energy_curve.png"
    out_tab = "tab_hpa_ca_bidirectional_fixed_point.tex"
    out_fig = "fig_hpa_ca_fixed_point_energy_curve.tex"

    run = prepare_run(
        experiment="hpa_ca_bidirectional_fixed_point",
        params=params,
        script_path=script_path,
        required_files=[out_csv, out_png, out_tab, out_fig],
        force=bool(args.force),
        extra_fingerprint={"external": extra},
    )

    if run.cached:
        print(f"[exp_hpa_ca_bidirectional_fixed_point] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        copy_atomic(run.run_dir / out_fig, generated_dir() / out_fig)
        copy_atomic(run.run_dir / out_csv, export_dir() / out_csv)
        copy_atomic(run.run_dir / out_png, export_dir() / out_png)
        return

    words = hpa_ca_preimage_count.stable_words_x6()  # type: ignore[attr-defined]
    idx = {w: i for i, w in enumerate(words)}
    out_f, _upl = hpa_ca_preimage_count.f_pair(words)  # type: ignore[attr-defined]
    succ = hpa_ca_preimage_count.build_succ_table(out_f)  # type: ignore[attr-defined]
    succ_mask, pred_mask = build_succ_masks(succ)
    A = len(succ_mask)
    bits_per_symbol = float(math.log2(A))

    # DFS baseline
    dfs = hpa_ca_inverse_search.dfs_find_one_preimage  # type: ignore[attr-defined]
    count_k1 = hpa_ca_preimage_count.count_preimages_k1_ring  # type: ignore[attr-defined]
    words_from_bits = hpa_ca_preimage_count.words_from_state_bits  # type: ignore[attr-defined]

    stable_offset = 0 if ((int(args.t) - 1) % 2 == 0) else 3

    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    if not seeds:
        raise SystemExit("No seeds provided")

    rows: List[Dict[str, object]] = []
    curves_greedy: List[List[int]] = []
    curves_bt: List[List[int]] = []

    for sd in seeds:
        print(f"[exp_hpa_ca_bidirectional_fixed_point] seed={sd} start", flush=True)
        res = hpa_ca_lossless.evolve(L=int(args.L), T=int(args.T), seed=int(sd), p=float(args.p))  # type: ignore[attr-defined]
        state_t = res.states[int(args.t)]
        out_words = words_from_bits(state_t, offset=stable_offset)
        if not all(w in idx for w in out_words):
            # No valid symbolic slice
            rows.append(
                {
                    "seed": sd,
                    "found_fp": 0,
                    "iters_fp": 0,
                    "commits_fp": 0,
                    "final_amb_fp": -1,
                    "found_dfs": 0,
                    "nodes_dfs": 0,
                    "backtracks_dfs": 0,
                    "exact_k1": 0,
                }
            )
            continue

        out_seq = [idx[w] for w in out_words]
        exact = int(count_k1(out_seq, succ))

        fp = fixed_point_greedy(out_seq, succ_mask=succ_mask, pred_mask=pred_mask, max_iters=int(args.max_iters))
        bt = fixed_point_bounded_backtracking(
            out_seq,
            succ_mask=succ_mask,
            pred_mask=pred_mask,
            max_depth=int(args.bt_max_depth),
            max_nodes=int(args.bt_max_nodes),
        )
        max_nodes = None if int(args.max_nodes_dfs) <= 0 else int(args.max_nodes_dfs)
        rng = np.random.default_rng(int(args.shuffle_seed)) if bool(args.shuffle_dfs) else None
        _x_pre, dfs_stats = dfs(out_seq, succ, rng=rng, max_nodes=max_nodes)
        dfs_truncated = 1 if (max_nodes is not None and int(dfs_stats.nodes_visited) >= int(max_nodes) and not bool(dfs_stats.found)) else 0

        rows.append(
            {
                "seed": sd,
                "found_fp": int(fp.found),
                "iters_fp": int(fp.iters),
                "commits_fp": int(fp.commits),
                "final_amb_fp": int(fp.final_ambiguity),
                "tau_fp_bits": float(fp.commits) * bits_per_symbol,
                "found_bt": int(bt.found),
                "nodes_bt": int(bt.nodes_visited),
                "backtracks_bt": int(bt.backtracks),
                "depth_bt": int(bt.depth),
                "final_amb_bt": int(bt.final_ambiguity),
                "tau_bt_bits": float(bt.depth) * bits_per_symbol if bool(bt.found) else float("nan"),
                "found_dfs": int(dfs_stats.found),
                "nodes_dfs": int(dfs_stats.nodes_visited),
                "backtracks_dfs": int(dfs_stats.backtracks),
                "truncated_dfs": int(dfs_truncated),
                "exact_k1": exact,
            }
        )
        curves_greedy.append(fp.curve)
        curves_bt.append(bt.curve)
        print(
            f"[exp_hpa_ca_bidirectional_fixed_point] seed={sd} done fp_found={int(fp.found)} bt_found={int(bt.found)} bt_nodes={bt.nodes_visited} dfs_nodes={dfs_stats.nodes_visited}",
            flush=True,
        )

    # Write CSV
    out_csv_path = run.run_dir / out_csv
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "seed",
                "found_fp",
                "iters_fp",
                "commits_fp",
                "final_amb_fp",
                "tau_fp_bits",
                "found_bt",
                "nodes_bt",
                "backtracks_bt",
                "depth_bt",
                "final_amb_bt",
                "tau_bt_bits",
                "found_dfs",
                "nodes_dfs",
                "backtracks_dfs",
                "truncated_dfs",
                "exact_k1",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Plot mean ambiguity curves (greedy vs bounded backtracking)
    xs_g, ys_g = pad_and_mean(curves_greedy)
    xs_b, ys_b = pad_and_mean(curves_bt)
    out_png_path = run.run_dir / out_png
    out_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.2, 3.4))
    if xs_g:
        plt.plot(xs_g, ys_g, marker="o", linewidth=1.6, label="greedy")
    if xs_b:
        plt.plot(xs_b, ys_b, marker="s", linewidth=1.6, label="bounded_backtracking")
    plt.xlabel("iteration (prune/commit stages)")
    plt.ylabel("mean ambiguity  Σ(|D_i|-1)")
    plt.title("HPA-CA fixed-point ambiguity curves (mean over seeds)")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(out_png_path, dpi=170)
    plt.close()

    # LaTeX figure fragment
    out_fig_path = run.run_dir / out_fig
    write_lines_as_fragment(
        out_fig_path,
        [
            r"\centering",
            rf"\includegraphics[width=0.85\linewidth]{{artifacts/export/{out_png}}}",
        ],
    )

    # Aggregate summary table
    n_total = len(rows)
    n_fp = sum(int(r["found_fp"]) for r in rows)
    n_bt = sum(int(r["found_bt"]) for r in rows)
    n_dfs = sum(int(r["found_dfs"]) for r in rows)
    n_trunc = sum(int(r["truncated_dfs"]) for r in rows)
    mean_nodes = float(np.mean([int(r["nodes_dfs"]) for r in rows])) if rows else 0.0
    mean_iters = float(np.mean([int(r["iters_fp"]) for r in rows])) if rows else 0.0
    mean_amb = float(np.mean([int(r["final_amb_fp"]) for r in rows if int(r["final_amb_fp"]) >= 0])) if rows else 0.0
    mean_bt_nodes = float(np.mean([int(r["nodes_bt"]) for r in rows])) if rows else 0.0
    mean_bt_backtracks = float(np.mean([int(r["backtracks_bt"]) for r in rows])) if rows else 0.0
    mean_tau_fp_bits = float(np.mean([float(r["tau_fp_bits"]) for r in rows])) if rows else 0.0
    tau_bt_vals = [float(r["tau_bt_bits"]) for r in rows if not (isinstance(r["tau_bt_bits"], float) and math.isnan(float(r["tau_bt_bits"])))]
    mean_tau_bt_bits = float(np.mean(tau_bt_vals)) if tau_bt_vals else float("nan")

    tab_rows = [
        [
            str(n_total),
            f"{n_fp}/{n_total}",
            f"{n_bt}/{n_total}",
            f"{n_dfs}/{n_total}",
            f"{n_trunc}/{n_total}",
            f"{mean_iters:.2f}",
            f"{mean_tau_fp_bits:.2f}",
            (f"{mean_tau_bt_bits:.2f}" if not math.isnan(mean_tau_bt_bits) else r"\textemdash"),
            f"{mean_bt_nodes:.1f}",
            f"{mean_bt_backtracks:.1f}",
            f"{mean_nodes:.1f}",
            f"{mean_amb:.2f}",
        ]
    ]

    out_tab_path = run.run_dir / out_tab
    write_tabular_fragment(
        out_tab_path,
        column_spec="r r r r r r r r r r r r",
        header=[
            r"$N$",
            r"\textbf{FP found}",
            r"\textbf{BT found}",
            r"\textbf{DFS found}",
            r"\textbf{DFS truncated}",
            r"\textbf{FP iters (mean)}",
            r"\textbf{$\tau$ FP (bits, mean)}",
            r"\textbf{$\tau$ BT (bits, mean)}",
            r"\textbf{BT nodes (mean)}",
            r"\textbf{BT backtracks (mean)}",
            r"\textbf{DFS nodes (mean)}",
            r"\textbf{FP final ambiguity (mean)}",
        ],
        rows=tab_rows,
        booktabs=True,
    )

    # Manifest
    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_csv, out_png, out_tab, out_fig])
    write_manifest(run.run_dir, manifest)

    # Export/copy
    copy_atomic(out_tab_path, generated_dir() / out_tab)
    copy_atomic(out_fig_path, generated_dir() / out_fig)
    copy_atomic(out_csv_path, export_dir() / out_csv)
    copy_atomic(out_png_path, export_dir() / out_png)
    print("[exp_hpa_ca_bidirectional_fixed_point] done", flush=True)


if __name__ == "__main__":
    main()

