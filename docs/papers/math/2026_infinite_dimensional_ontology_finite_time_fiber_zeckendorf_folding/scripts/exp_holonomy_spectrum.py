#!/usr/bin/env python3
"""
Holonomy spectrum experiment (minimal toy construction).

We build a directed transition graph on X_m using legal single-bit flips (stay in X_m),
define a residual fiber R = Z_q, and assign parallel transport maps P_{x->x'} as affine maps on Z_q.

Interface vs bulk:
  - bulk states: C_m (cycle-legal)
  - interface states: B_m = X_m \\ C_m (equivalently: linear-legal but w_1=w_m=1)
  - a loop is tagged 'interface' if it visits any interface state, else 'bulk'

Outputs:
  - artifacts/holonomy_spectrum/<run_id>/summary.json
  - artifacts/holonomy_spectrum/<run_id>/holonomy_hist.png
  - sections/generated/holonomy_interface_vs_bulk.tex
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_progress import Progress
from common_pylatex import NoEscape, booktabs_tabular, write_tex_fragment
from common_zeckendorf import iter_cycle_no_adjacent_words, iter_no_adjacent_words, no_adjacent_ones_mask_ok, word_bit


def is_in_Cm(x: int, m: int) -> bool:
    if not no_adjacent_ones_mask_ok(x):
        return False
    if m <= 1:
        return True
    return not (word_bit(x, 0) == 1 and word_bit(x, m - 1) == 1)


def build_Xm(m: int) -> List[int]:
    xs = list(iter_no_adjacent_words(m))
    xs.sort()
    return xs


def build_neighbors_single_bit_flip(xs: List[int], m: int) -> Dict[int, List[int]]:
    xset = set(xs)
    adj: Dict[int, List[int]] = {}
    for x in xs:
        nbrs: List[int] = []
        for i in range(m):
            y = x ^ (1 << i)
            if y in xset:
                nbrs.append(y)
        adj[x] = nbrs
    return adj


@dataclass(frozen=True)
class AffineMapZq:
    a: int
    b: int
    q: int

    def apply(self, r: int) -> int:
        return (self.a * r + self.b) % self.q

    def compose(self, other: "AffineMapZq") -> "AffineMapZq":
        # self ∘ other
        if self.q != other.q:
            raise ValueError("q mismatch")
        a = (self.a * other.a) % self.q
        b = (self.a * other.b + self.b) % self.q
        return AffineMapZq(a=a, b=b, q=self.q)

    def is_identity(self) -> bool:
        return (self.a % self.q) == 1 and (self.b % self.q) == 0

    def fixed_point_ratio(self) -> float:
        # For affine map r -> a r + b mod q:
        # fixed points solve (a-1)r = -b (mod q). Count depends on gcd.
        q = self.q
        a1 = (self.a - 1) % q
        b = (-self.b) % q
        if a1 == 0:
            return 1.0 if b == 0 else 0.0
        g = math.gcd(a1, q)
        if b % g != 0:
            return 0.0
        return float(g) / float(q)


def edge_parallel_transport(x: int, y: int, m: int, q: int) -> AffineMapZq:
    """
    Minimal 'connection' that concentrates curvature on interface states.
    We use translation maps (a=1), with b=0 in bulk, b=±1 near interface.
    """
    bulk_x = is_in_Cm(x, m)
    bulk_y = is_in_Cm(y, m)
    if bulk_x and bulk_y:
        return AffineMapZq(a=1, b=0, q=q)

    # Interface involvement: inject a signed increment based on which bit flipped.
    d = x ^ y
    idx = (d.bit_length() - 1) if d != 0 else 0
    b = 1 if (idx % 2 == 0) else (q - 1)  # +1 or -1 mod q
    return AffineMapZq(a=1, b=b, q=q)


def random_closed_walks(
    adj: Dict[int, List[int]],
    starts: List[int],
    ell: int,
    n_samples: int,
    rng: random.Random,
    prog: Progress,
) -> List[List[int]]:
    walks: List[List[int]] = []
    if not starts:
        return walks
    for k in range(n_samples):
        s = starts[rng.randrange(len(starts))]
        path = [s]
        cur = s
        for _ in range(ell):
            nbrs = adj.get(cur, [])
            if not nbrs:
                break
            cur = nbrs[rng.randrange(len(nbrs))]
            path.append(cur)
        if path[-1] == s and len(path) > 1:
            walks.append(path)
        prog.maybe(f"sampling loops {k+1}/{n_samples} (found={len(walks)})")
    return walks


def classify_loop(path: List[int], m: int) -> str:
    for x in path:
        if not is_in_Cm(x, m):
            return "interface"
    return "bulk"


def loop_holonomy(path: List[int], m: int, q: int) -> AffineMapZq:
    H = AffineMapZq(a=1, b=0, q=q)
    for i in range(len(path) - 1):
        x = path[i]
        y = path[i + 1]
        P = edge_parallel_transport(x, y, m=m, q=q)
        H = P.compose(H)
    return H


def write_holonomy_tex(summary: Dict[str, Dict[str, float]], out_path: Path) -> None:
    rows = []
    for cls in ["bulk", "interface", "all"]:
        s = summary.get(cls, {})
        rows.append(
            [
                cls,
                str(int(s.get("N", 0))),
                f"{s.get('id_rate', 0.0):.4f}",
                f"{s.get('fixed_ratio_mean', 0.0):.4f}",
                f"{s.get('abs_b_mean', 0.0):.4f}",
            ]
        )
    tab = booktabs_tabular(
        col_spec="l r r r r",
        header=[
            NoEscape("Class"),
            NoEscape(r"$N$"),
            NoEscape("id-rate"),
            NoEscape("fixed-ratio(avg)"),
            NoEscape(r"$\mathbb{E}[|b|]$"),
        ],
        rows=rows,
    )
    write_tex_fragment(out_path, tab, comment="Auto-generated by scripts/exp_holonomy_spectrum.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=12)
    ap.add_argument("--ell", type=int, default=6)
    ap.add_argument("--q", type=int, default=7)
    ap.add_argument("--samples", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = int(args.m)
    ell = int(args.ell)
    q = int(args.q)
    samples = int(args.samples)
    seed = int(args.seed)

    script_path = Path(__file__).resolve()
    params = {"m": m, "ell": ell, "q": q, "samples": samples, "seed": seed}
    run = prepare_run(
        experiment="holonomy_spectrum",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "holonomy_hist.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_png = run.run_dir / "holonomy_hist.png"
    out_tex = generated_dir() / "holonomy_interface_vs_bulk.tex"

    if run.cached:
        print(f"[holonomy] cached: {run.run_dir}", flush=True)
        return

    prog = Progress(every_seconds=15.0)
    rng = random.Random(seed)

    xs = build_Xm(m)
    adj = build_neighbors_single_bit_flip(xs, m=m)

    bulk_starts = [x for x in xs if is_in_Cm(x, m)]
    interface_starts = [x for x in xs if not is_in_Cm(x, m)]

    # Sample closed walks from both start sets to balance.
    walks_bulk = random_closed_walks(adj, bulk_starts, ell=ell, n_samples=samples // 2, rng=rng, prog=prog)
    walks_int = random_closed_walks(adj, interface_starts, ell=ell, n_samples=samples - samples // 2, rng=rng, prog=prog)
    walks = walks_bulk + walks_int

    per_class: Dict[str, List[AffineMapZq]] = {"bulk": [], "interface": [], "all": []}
    b_values: Dict[str, List[int]] = {"bulk": [], "interface": [], "all": []}

    for idx, w in enumerate(walks):
        cls = classify_loop(w, m=m)
        H = loop_holonomy(w, m=m, q=q)
        per_class[cls].append(H)
        per_class["all"].append(H)
        b_values[cls].append(int(H.b))
        b_values["all"].append(int(H.b))
        prog.maybe(f"holonomy compute {idx+1}/{len(walks)}")

    def summarize(cls: str) -> Dict[str, float]:
        hs = per_class[cls]
        if not hs:
            return {"N": 0.0, "id_rate": 0.0, "fixed_ratio_mean": 0.0, "abs_b_mean": 0.0}
        N = float(len(hs))
        id_rate = sum(1 for h in hs if h.is_identity()) / N
        fixed_ratio_mean = sum(h.fixed_point_ratio() for h in hs) / N
        abs_b_mean = sum(abs(int(b)) for b in b_values[cls]) / N
        return {"N": N, "id_rate": float(id_rate), "fixed_ratio_mean": float(fixed_ratio_mean), "abs_b_mean": float(abs_b_mean)}

    summary = {cls: summarize(cls) for cls in ["bulk", "interface", "all"]}

    # Histogram of b values for all loops (translation amount).
    all_bs = b_values["all"]
    plt.figure(figsize=(7.0, 4.0))
    plt.hist(all_bs, bins=range(0, q + 1), align="left", color="#ff7f0e", alpha=0.9)
    plt.title(f"Holonomy translation b mod q (m={m}, ell={ell}, q={q})")
    plt.xlabel("b mod q")
    plt.ylabel("count")
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=160)
    plt.close()

    payload = {
        "params": params,
        "n_Xm": len(xs),
        "n_bulk": len(bulk_starts),
        "n_interface": len(interface_starts),
        "n_loops": len(walks),
        "summary": summary,
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_holonomy_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("holonomy_spectrum", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "holonomy_hist.png"])
    write_manifest(run.run_dir, manifest)

    prog.done(f"wrote {out_json}, {out_png}, and {out_tex}")


if __name__ == "__main__":
    main()

