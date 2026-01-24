#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export ambiguous micro pairs under WL1 for selected m (hypercube)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from closure_graph import build_closure_graph
from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, paper_root
from micro_models import hypercube_neighbors
from wl1 import micro_ambiguous_pairs, wl1_refine


def _write_pairs_txt(path: Path, m: int, pairs: List[tuple[int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    diffs = sorted({b - a for (a, b) in pairs})
    lines = []
    lines.append(f"m={m} ambiguous micro pairs under WL1 on combined graph")
    lines.append(f"count_pairs={len(pairs)}")
    lines.append(f"diffs={diffs}")
    lines.append("")
    for a, b in pairs:
        lines.append(f"{a},{b}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compute_pairs(m: int) -> List[tuple[int, int]]:
    n = 1 << m
    adj = hypercube_neighbors(n=n, m=m)
    clo = build_closure_graph(m=m, micro_adj=adj)

    # initial colors:
    # - micro vertices share one color (0)
    # - each macro vertex gets a unique color (1 + macro_idx)
    init_colors = [0] * clo.n_total
    for v in clo.macro_range:
        init_colors[v] = 1 + (v - clo.n_micro)

    stats = wl1_refine(
        n_nodes=clo.n_total,
        neighbors=clo.neighbors,
        init_colors=init_colors,
        micro_nodes=clo.micro_range,
        max_iter=200,
        progress_every=2 if m >= 9 else 1,
    )
    return micro_ambiguous_pairs(stats.colors, clo.micro_range)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=str, default="6,9")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ms = [int(x.strip()) for x in args.ms.split(",") if x.strip()]

    script_path = Path(__file__).resolve()
    params = {"ms": ms}
    out_names = [f"m{m}_hypercube_ambiguous_pairs.txt" for m in ms]

    run = prepare_run(
        experiment="hypercube_ambiguous_pairs",
        params=params,
        script_path=script_path,
        required_files=out_names,
        force=args.force,
    )

    if run.cached:
        print(f"[exp_hypercube_ambiguous_pairs] cached: {run.run_dir.name}", flush=True)
        for nm in out_names:
            copy_atomic(run.run_dir / nm, export_dir() / nm)
        return

    for m in ms:
        print(f"[exp_hypercube_ambiguous_pairs] m={m}", flush=True)
        pairs = _compute_pairs(m)
        _write_pairs_txt(run.run_dir / f"m{m}_hypercube_ambiguous_pairs.txt", m=m, pairs=pairs)

    manifest = build_base_manifest("hypercube_ambiguous_pairs", run.run_id, params, script_path)
    manifest = add_output_hashes(manifest, run.run_dir, out_names)
    write_manifest(run.run_dir, manifest)

    for nm in out_names:
        copy_atomic(run.run_dir / nm, export_dir() / nm)
    print("[exp_hypercube_ambiguous_pairs] done", flush=True)


if __name__ == "__main__":
    main()

