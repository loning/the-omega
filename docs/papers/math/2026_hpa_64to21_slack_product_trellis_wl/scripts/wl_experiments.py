#!/usr/bin/env python3
"""
Reproducible WL experiments for the HPA 64->21 fold/time trellis and macro quotient Q_n.

Outputs (deterministic, reproducible, cacheable):
  - sections/generated/wl_experiments_manifest.json
  - sections/generated/wl_summary.json
  - sections/generated/trellis_wl1.csv
  - sections/generated/trellis_wl2.csv
  - sections/generated/Qn_wl2_weighted.csv
  - sections/generated/wl_table_summary.tex   (generated via PyLaTeX; no manual string assembly)

Caching:
  - scripts/_cache/ stores pickled intermediate results keyed by a content fingerprint.
  - Disable via: export HPA_NO_CACHE=1
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import pylatex
from pylatex import Center, Command, NoEscape, Tabular, Table

from common_cache import cache_disabled, cache_path, load_or_compute
from common_paths import generated_dir, paper_root, scripts_dir
from common_tex import nonempty_file, write_text


def head(x: int, n: int) -> int:
    """Head/fold operator H(x): keep 1s that start a run."""
    mask = (1 << n) - 1
    return x & (~(x >> 1) & mask)


def tail(x: int, n: int) -> int:
    """Tail/time operator T(x): remove run heads; keep the remainder."""
    return x & (x >> 1)


def is_stable(z: int) -> bool:
    """No adjacent 1s (for standard bit adjacency)."""
    return (z & (z >> 1)) == 0


def enumerate_Zn(n: int) -> List[int]:
    """Enumerate all stable macro states Z_n as integers."""
    return [z for z in range(1 << n) if is_stable(z)]


@dataclass(frozen=True)
class Digraph:
    n_vertices: int
    out_edges: List[List[Tuple[int, int]]]
    in_edges: List[List[Tuple[int, int]]]
    edge_type: Dict[Tuple[int, int], int]  # (u,v)->type


def build_trellis(n: int) -> Tuple[Digraph, Dict[int, int], List[int]]:
    """
    Build trellis G_n with vertices V_n = X_n ⊔ Z_n.
    Vertex ids:
      - micro x in {0..2^n-1} mapped to id=x
      - macro z in Z_n mapped to id=2^n + idx(z)
    Edge types:
      0: fold (micro -> macro)
      1: time (micro -> micro)
    """
    Zn = enumerate_Zn(n)
    z_to_idx = {z: i for i, z in enumerate(Zn)}
    micro_count = 1 << n
    V = micro_count + len(Zn)

    out_edges: List[List[Tuple[int, int]]] = [[] for _ in range(V)]
    in_edges: List[List[Tuple[int, int]]] = [[] for _ in range(V)]
    et: Dict[Tuple[int, int], int] = {}

    for x in range(micro_count):
        hz = head(x, n)
        tz = tail(x, n)
        macro_id = micro_count + z_to_idx[hz]
        time_id = tz  # micro

        out_edges[x].append((0, macro_id))
        out_edges[x].append((1, time_id))

        in_edges[macro_id].append((0, x))
        in_edges[time_id].append((1, x))

        et[(x, macro_id)] = 0
        et[(x, time_id)] = 1

    return Digraph(V, out_edges, in_edges, et), z_to_idx, Zn


def build_Qn(n: int) -> Tuple[int, List[int], List[List[Tuple[int, int]]], Dict[Tuple[int, int], int]]:
    """
    Build macro weighted graph Q_n on Z_n.
    Returns (V, Zn, out_edges_with_weights, weight_uv_dict).
    """
    Zn = enumerate_Zn(n)
    V = len(Zn)
    index = {z: i for i, z in enumerate(Zn)}
    outw: List[List[Tuple[int, int]]] = [[] for _ in range(V)]
    wuv: Dict[Tuple[int, int], int] = {}

    # Helper to list 1-positions (LSB=position 1 on right; we need left-to-right positions)
    def one_positions(z: int) -> List[int]:
        pos = []
        for i in range(n):
            # bit i corresponds to position (n-i) from left if written MSB..LSB
            if (z >> (n - 1 - i)) & 1:
                pos.append(i + 1)  # 1-based position from left
        return pos

    for z in Zn:
        i_list = one_positions(z)
        k = len(i_list)
        if k == 0:
            # empty head set: only J=empty; transition stays empty with weight 1
            u = index[z]
            v = u
            outw[u].append((v, 1))
            wuv[(u, v)] = 1
            continue

        # slack components
        s: List[int] = []
        for j in range(k - 1):
            s.append(i_list[j + 1] - i_list[j] - 1)
        s.append(n - i_list[-1] + 1)

        # eligible indices where s_j > 1
        eligible = [j for j, sj in enumerate(s) if sj > 1]
        u = index[z]

        # enumerate subsets via bitmask over eligible indices
        e = len(eligible)
        for mask in range(1 << e):
            head_positions_next = []
            w = 1
            for t in range(e):
                if (mask >> t) & 1:
                    j = eligible[t]
                    head_positions_next.append(i_list[j] + 1)
                    w *= (s[j] - 1)
            # construct z_J
            zJ = 0
            for p in head_positions_next:
                zJ |= 1 << (n - p)  # position p from left -> bit (n-p)
            v = index[zJ]
            outw[u].append((v, w))
            wuv[(u, v)] = wuv.get((u, v), 0) + w

    # merge possible duplicates in outw (should be rare but safe)
    merged: List[List[Tuple[int, int]]] = []
    for u in range(V):
        acc: Dict[int, int] = {}
        for v, w in outw[u]:
            acc[v] = acc.get(v, 0) + w
        merged.append(sorted(acc.items()))
    outw = merged
    wuv = {(u, v): w for u in range(V) for v, w in outw[u]}
    return V, Zn, outw, wuv


def compress_colors(signatures: Iterable[object]) -> List[int]:
    """Map signatures to stable integer colors."""
    mp: Dict[object, int] = {}
    out: List[int] = []
    next_id = 0
    for sig in signatures:
        cid = mp.get(sig)
        if cid is None:
            cid = next_id
            mp[sig] = cid
            next_id += 1
        out.append(cid)
    return out


def wl1_directed_edgecolored(G: Digraph, init_vertex_colors: List[int]) -> Tuple[int, List[int]]:
    """WL-1 (vertex refinement) on edge-colored directed graph."""
    colors = init_vertex_colors[:]
    steps = 0
    while True:
        sigs = []
        for v in range(G.n_vertices):
            out_c = Counter((etype, colors[w]) for etype, w in G.out_edges[v])
            in_c = Counter((etype, colors[u]) for etype, u in G.in_edges[v])
            sigs.append((colors[v], tuple(sorted(out_c.items())), tuple(sorted(in_c.items()))))
        new_colors = compress_colors(sigs)
        steps += 1
        if new_colors == colors:
            return steps - 1, colors
        colors = new_colors


def wl2_on_trellis(G: Digraph, vertex_colors: List[int], max_steps: int = 20) -> Tuple[int, List[int]]:
    """WL-2 on ordered pairs for small trellis graphs (dense O(V^3))."""
    V = G.n_vertices
    V2 = V * V

    # Edge relation type u->v and v->u (at most one edge per direction here)
    et = G.edge_type

    def rel(u: int, v: int) -> int:
        return et.get((u, v), -1)

    init = []
    for u in range(V):
        cu = vertex_colors[u]
        uV = u * V
        for v in range(V):
            init.append((u == v, cu, vertex_colors[v], rel(u, v), rel(v, u)))
    colors = compress_colors(init)

    steps = 0
    while steps < max_steps:
        sigs: List[object] = [None] * V2
        for u in range(V):
            uV = u * V
            for v in range(V):
                base = colors[uV + v]
                cnt: Dict[Tuple[int, int], int] = {}
                for w in range(V):
                    key = (colors[uV + w], colors[w * V + v])
                    cnt[key] = cnt.get(key, 0) + 1
                sigs[uV + v] = (base, tuple(sorted(cnt.items())))
        new_colors = compress_colors(sigs)
        steps += 1
        if new_colors == colors:
            return steps - 1, colors
        colors = new_colors
    return steps, colors


def wl2_weighted_Qn(
    V: int,
    outw: List[List[Tuple[int, int]]],
    wuv: Dict[Tuple[int, int], int],
    init_vertex_color: int = 0,
    max_steps: int = 20,
) -> Tuple[int, List[int]]:
    """WL-2 on Z_n×Z_n using weighted 2-path multiplicities (sparse via 2-path enumeration)."""
    V2 = V * V

    def w(u: int, v: int) -> int:
        return wuv.get((u, v), 0)

    init = []
    for u in range(V):
        uV = u * V
        for v in range(V):
            init.append((u == v, init_vertex_color, init_vertex_color, w(u, v), w(v, u)))
    colors = compress_colors(init)

    steps = 0
    while steps < max_steps:
        sigs: List[object] = [None] * V2
        for u in range(V):
            uV = u * V
            evid: Dict[int, Dict[Tuple[int, int], int]] = {}
            for a, w1 in outw[u]:
                cu_a = colors[uV + a]
                for v, w2 in outw[a]:
                    key = (cu_a, colors[a * V + v])
                    d = evid.get(v)
                    if d is None:
                        d = {}
                        evid[v] = d
                    d[key] = d.get(key, 0) + w1 * w2

            for v in range(V):
                base = colors[uV + v]
                d = evid.get(v)
                if d is None:
                    sigs[uV + v] = (base, ())
                else:
                    sigs[uV + v] = (base, tuple(sorted(d.items())))

        new_colors = compress_colors(sigs)
        steps += 1
        if new_colors == colors:
            return steps - 1, colors
        colors = new_colors

    return steps, colors


SCRIPT_CACHE_VERSION = 2


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_head_sha(paper: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=paper,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            return str(out)
    except Exception:
        pass
    return ""


def _fingerprint(config: dict) -> str:
    """
    A stable fingerprint for caching and manifesting.
    Includes:
      - script content hash
      - config JSON
      - Python version and PyLaTeX version (affects generated .tex)
    """
    p = scripts_dir() / "wl_experiments.py"
    h = hashlib.sha256()
    h.update(b"wl_experiments")
    h.update(b"\0")
    h.update(str(SCRIPT_CACHE_VERSION).encode("utf-8"))
    h.update(b"\0")
    h.update(_sha256_file(p).encode("utf-8"))
    h.update(b"\0")
    h.update(json.dumps(config, sort_keys=True).encode("utf-8"))
    h.update(b"\0")
    h.update(sys.version.encode("utf-8"))
    h.update(b"\0")
    h.update(str(getattr(pylatex, "__version__", "")).encode("utf-8"))
    return h.hexdigest()


def _expected_outputs() -> List[str]:
    return [
        "wl_experiments_manifest.json",
        "wl_summary.json",
        "trellis_wl1.csv",
        "trellis_wl2.csv",
        "Qn_wl2_weighted.csv",
        "wl_table_summary.tex",
    ]


def _have_expected_outputs(gen_dir) -> bool:
    for name in _expected_outputs():
        if not nonempty_file(gen_dir / name):
            return False
    return True


def _write_json(path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _render_summary_table_tex(summary: dict) -> str:
    """
    Build a LaTeX table fragment via PyLaTeX (no manual string concatenation of rows).
    The fragment includes a complete table environment.
    """
    # Index helper maps
    wl1_by_n = {int(r["n"]): r for r in summary.get("trellis_wl1", [])}
    wl2T_by_n = {int(r["n"]): r for r in summary.get("trellis_wl2", [])}
    wl2Q_by_n = {int(r["n"]): r for r in summary.get("Qn_wl2_weighted", [])}

    # Assemble a readable subset for the paper table:
    # show n=6,7,8,12 (same as current section text).
    n_rows = [6, 7, 8, 12]

    table = Table(position="H")
    table.append(Command("centering"))
    table.append(Command("small"))

    tab = Tabular("cccccc")
    tab.append(NoEscape(r"\toprule"))
    tab.add_row(
        [
            NoEscape(r"$n$"),
            NoEscape(r"$\abs{V_n}$"),
            NoEscape(r"$\WL$-1 步数"),
            NoEscape(r"$\WL$-1 颜色类数"),
            NoEscape(r"$\WLTWO$（$Q_n$）步数"),
            NoEscape(r"$\WLTWO$（$G_n$，若计算）步数"),
        ]
    )
    tab.append(NoEscape(r"\midrule"))

    for n in n_rows:
        r1 = wl1_by_n.get(int(n), {})
        v = r1.get("V", "--")
        wl1_steps = r1.get("steps", "--")
        wl1_colors = r1.get("colors", "--")
        q = wl2Q_by_n.get(int(n), {})
        wl2Q_steps = q.get("wl2_steps", "--")
        t = wl2T_by_n.get(int(n), {})
        wl2T_steps = t.get("wl2_steps", "--") if t else "--"

        tab.add_row([str(n), str(v), str(wl1_steps), str(wl1_colors), str(wl2Q_steps), str(wl2T_steps)])

    tab.append(NoEscape(r"\bottomrule"))
    table.append(tab)
    table.add_caption(NoEscape(r"$G_n$ 与 $Q_n$ 上的 $\WL$ 稳定统计（由脚本自动生成）。"))
    return Center(data=[table]).dumps()


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate/cache WL experiment artifacts for this paper.")
    parser.add_argument("--force", action="store_true", help="Force recompute even if manifest matches.")
    args = parser.parse_args(argv)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    config = {
        "trellis_wl1_n_min": 2,
        "trellis_wl1_n_max": 12,
        "trellis_wl2_n_min": 6,
        "trellis_wl2_n_max": 8,
        "Qn_wl2_n_min": 4,
        "Qn_wl2_n_max": 12,
        "wl2_max_steps": 20,
    }

    fp = _fingerprint(config)
    manifest_path = gen / "wl_experiments_manifest.json"
    if (not args.force) and manifest_path.is_file() and _have_expected_outputs(gen):
        try:
            old = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(old, dict) and str(old.get("fingerprint", "")) == fp:
                print("[wl_experiments] SKIP (up-to-date)")
                return
        except Exception:
            pass

    summary = {
        "trellis_wl1": [],
        "trellis_wl2": [],
        "Qn_wl2_weighted": [],
    }

    def _compute_summary() -> dict:
        out = {"trellis_wl1": [], "trellis_wl2": [], "Qn_wl2_weighted": []}

        # WL-1 on trellis
        for n in range(int(config["trellis_wl1_n_min"]), int(config["trellis_wl1_n_max"]) + 1):
            G, _, Zn = build_trellis(n)
            micro_count = 1 << n
            init_colors = [0] * G.n_vertices
            for v in range(micro_count, G.n_vertices):
                init_colors[v] = 1  # macro
            steps, colors = wl1_directed_edgecolored(G, init_colors)
            out["trellis_wl1"].append(
                {
                    "n": int(n),
                    "V": int(G.n_vertices),
                    "X": int(micro_count),
                    "Z": int(len(Zn)),
                    "steps": int(steps),
                    "colors": int(len(set(colors))),
                }
            )

        # WL-2 on trellis (full pair refinement, limited range)
        for n in range(int(config["trellis_wl2_n_min"]), int(config["trellis_wl2_n_max"]) + 1):
            G, _, Zn = build_trellis(n)
            micro_count = 1 << n
            init_vc = [0] * G.n_vertices
            for v in range(micro_count, G.n_vertices):
                init_vc[v] = 1
            wl1_steps, wl1_colors = wl1_directed_edgecolored(G, init_vc)
            wl2_steps, pair_colors = wl2_on_trellis(G, wl1_colors, max_steps=int(config["wl2_max_steps"]))
            out["trellis_wl2"].append(
                {
                    "n": int(n),
                    "V": int(G.n_vertices),
                    "pairs": int(G.n_vertices * G.n_vertices),
                    "wl1_steps": int(wl1_steps),
                    "wl1_colors": int(len(set(wl1_colors))),
                    "wl2_steps": int(wl2_steps),
                    "wl2_pair_colors": int(len(set(pair_colors))),
                }
            )

        # WL-2 on weighted Q_n
        for n in range(int(config["Qn_wl2_n_min"]), int(config["Qn_wl2_n_max"]) + 1):
            V, Zn, outw, wuv = build_Qn(n)
            wl2_steps, pair_colors = wl2_weighted_Qn(V, outw, wuv, max_steps=int(config["wl2_max_steps"]))
            out["Qn_wl2_weighted"].append(
                {
                    "n": int(n),
                    "V": int(V),
                    "pairs": int(V * V),
                    "wl2_steps": int(wl2_steps),
                    "wl2_pair_colors": int(len(set(pair_colors))),
                }
            )

        return out

    # Cache the heavy summary object, but still write all outputs deterministically.
    cache_file = cache_path(f"wl_summary_{fp}.pkl")
    if cache_disabled():
        summary = _compute_summary()
    else:
        summary = load_or_compute(cache_file, _compute_summary)

    # Write artifacts to sections/generated
    _write_json(gen / "wl_summary.json", summary)
    _write_csv(gen / "trellis_wl1.csv", summary["trellis_wl1"], ["n", "V", "X", "Z", "steps", "colors"])
    _write_csv(
        gen / "trellis_wl2.csv",
        summary["trellis_wl2"],
        ["n", "V", "pairs", "wl1_steps", "wl1_colors", "wl2_steps", "wl2_pair_colors"],
    )
    _write_csv(gen / "Qn_wl2_weighted.csv", summary["Qn_wl2_weighted"], ["n", "V", "pairs", "wl2_steps", "wl2_pair_colors"])

    wl_table_tex = _render_summary_table_tex(summary)
    write_text(gen / "wl_table_summary.tex", wl_table_tex)

    manifest = {
        "fingerprint": fp,
        "cache_disabled": bool(cache_disabled()),
        "config": config,
        "python": sys.version,
        "platform": {"python_implementation": platform.python_implementation(), "platform": platform.platform()},
        "versions": {"pylatex": str(getattr(pylatex, "__version__", ""))},
        "git": {"paper_head": _git_head_sha(str(paper_root()))},
        "scripts": {"wl_experiments.py": _sha256_file(scripts_dir() / "wl_experiments.py")},
        "artifacts": _expected_outputs(),
    }
    _write_json(gen / "wl_experiments_manifest.json", manifest)

    print("[wl_experiments] Wrote artifacts to:", str(gen))


if __name__ == "__main__":
    main()

