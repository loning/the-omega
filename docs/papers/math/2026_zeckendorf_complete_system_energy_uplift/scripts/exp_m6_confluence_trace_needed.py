#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detect a concrete confluence witness showing why trace is necessary (m=6, y=0^6).

We search for a depth d and tail-head t such that there exist two distinct traces
tr0 != tr1 with nodes (t, tr0) and (t, tr1) both reachable in the bubble graph.

This provides a program-auditable witness for Proposition `prop:log_needed_for_reversibility`:
the projection pi(t,tr)=t is not injective, hence forgetting trace destroys reversibility.

Outputs
-------
- sections/generated/tab_m6_confluence_example.tex
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment


def _no_adjacent_ones(x: int) -> bool:
    return (x & (x << 1)) == 0


def _bits_c7c8c9(t: int) -> str:
    c7 = (t >> 0) & 1
    c8 = (t >> 1) & 1
    c9 = (t >> 2) & 1
    return f"{c7}{c8}{c9}"


def _micro_N_for_y0_m6(t: int) -> int:
    c7 = (t >> 0) & 1
    c8 = (t >> 1) & 1
    c9 = (t >> 2) & 1
    return 21 * int(c7) + 34 * int(c8) + 55 * int(c9)


@dataclass(frozen=True)
class Node:
    depth: int
    t: int
    tr: str


def _expand(frontier: List[Node], depth: int) -> List[Node]:
    assert all(n.depth == depth for n in frontier)
    mask = 0b111  # L=3 for m=6
    nxt: List[Node] = []
    seen = set()
    for n in frontier:
        for b in (0, 1):
            tp = ((n.t << 1) & mask) | b
            if not _no_adjacent_ones(tp):
                continue
            Np = _micro_N_for_y0_m6(tp)
            if not (0 <= Np <= 63):
                continue
            trp = n.tr + str(b)
            nd = Node(depth=depth + 1, t=tp, tr=trp)
            key = (nd.depth, nd.t, nd.tr)
            if key in seen:
                continue
            seen.add(key)
            nxt.append(nd)
    return nxt


def _find_confluence(depth_max: int) -> Optional[Tuple[int, int, str, str]]:
    root = Node(depth=0, t=0, tr="")
    frontier = [root]
    for d in range(0, depth_max + 1):
        # Check confluence at current depth.
        by_t: Dict[int, List[str]] = {}
        for n in frontier:
            by_t.setdefault(n.t, []).append(n.tr)
        for t, trs in by_t.items():
            if len(trs) >= 2:
                # Choose two distinct traces.
                tr0 = trs[0]
                for tr1 in trs[1:]:
                    if tr1 != tr0:
                        return d, t, tr0, tr1

        if d == depth_max:
            break
        frontier = _expand(frontier, depth=d)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth_max", type=int, default=10, help="max search depth")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    params = {"m": 6, "y": "0^6", "depth_max": int(args.depth_max)}
    out_tab = "tab_m6_confluence_example.tex"

    script_path = Path(__file__).resolve()
    run = prepare_run(
        experiment="m6_confluence_trace_needed",
        params=params,
        script_path=script_path,
        required_files=[out_tab],
        force=bool(args.force),
        extra_fingerprint=None,
    )

    generated_dir().mkdir(parents=True, exist_ok=True)

    if run.cached:
        print(f"[exp_m6_confluence_trace_needed] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        return

    wit = _find_confluence(depth_max=int(args.depth_max))
    if wit is None:
        print("[exp_m6_confluence_trace_needed] no confluence found (unexpected)", flush=True)
        row = ["-", "-", "-", "-"]
    else:
        d, t, tr0, tr1 = wit
        t_bits = _bits_c7c8c9(int(t))
        tr0_disp = tr0 if tr0 != "" else r"\epsilon"
        tr1_disp = tr1 if tr1 != "" else r"\epsilon"
        print(
            f"[exp_m6_confluence_trace_needed] found: depth={d} t={t_bits} tr0={tr0_disp} tr1={tr1_disp}",
            flush=True,
        )
        row = [str(d), t_bits, tr0_disp, tr1_disp]

    out_tab_path = run.run_dir / out_tab
    write_tabular_fragment(
        out_tab_path,
        column_spec="r l l l",
        header=[r"\textbf{depth $d$}", r"\textbf{$t=c_7c_8c_9$}", r"\textbf{$\mathsf{tr}_0$}", r"\textbf{$\mathsf{tr}_1$}"],
        rows=[row],
        booktabs=True,
    )

    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_tab])
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_tab_path, generated_dir() / out_tab)
    print("[exp_m6_confluence_trace_needed] done", flush=True)


if __name__ == "__main__":
    main()

