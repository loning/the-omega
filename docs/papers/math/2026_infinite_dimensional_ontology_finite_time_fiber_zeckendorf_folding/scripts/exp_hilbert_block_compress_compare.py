#!/usr/bin/env python3
"""
Compare several block-level compression algorithms for m_from -> m_to under 2D vs 3D Hilbert layouts.

Model (data-first, as per discussion):
  - We have a single data tape B(t) for t=0..2^m_from-1, B(t)∈{0,1}.
  - A layout (2D or 3D Hilbert) maps t <-> coordinates on a fine grid.
  - A scale compression m_from -> m_to groups the fine grid into coarse blocks
    (2D: block side 2^{(m_from-m_to)/2}; 3D: block side 2^{(m_from-m_to)/3}).
  - Each coarse block emits one coarse bit via an aggregation rule Agg.
  - The truncated information is the per-block residual pattern (time fiber evidence).

We evaluate (for a fixed, deterministic pseudo-random tape):
  - recon_error: fraction of fine bits mismatching the expanded coarse bits
  - smoothness: fraction of adjacent coarse blocks with same coarse bit
  - H_residual_emp: empirical entropy of hashed residual patterns across blocks (64 samples)

Outputs:
  - artifacts/hilbert_block_compress_compare/<run_id>/summary.json
  - sections/generated/hilbert_block_compress_compare_m{m_from}_to_m{m_to}.tex
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
from hilbertcurve.hilbertcurve import HilbertCurve

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_progress import Progress
from common_pylatex import NoEscape, booktabs_tabular, write_tex_fragment


def entropy_base2_from_counts(counts: Dict[int, int]) -> float:
    n = float(sum(counts.values()))
    if n <= 0.0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = float(c) / n
        if p > 0.0:
            h -= p * math.log(p, 2.0)
    return float(h)


def _bit_tape(m_from: int, seed: int) -> np.ndarray:
    """
    Deterministic pseudo-random tape B(t) in {0,1}^{2^m_from}.
    We use SHA256(seed||t) to avoid global RNG dependence.
    """
    n = 1 << int(m_from)
    out = np.zeros(n, dtype=np.uint8)
    s0 = int(seed).to_bytes(8, "little", signed=False)
    for t in range(n):
        h = hashlib.sha256(s0 + int(t).to_bytes(8, "little", signed=False)).digest()
        out[t] = 1 if (h[0] & 1) else 0
    return out


def _neighbors_2d(side: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    edges: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    for y in range(side):
        for x in range(side):
            if x + 1 < side:
                edges.append(((x, y), (x + 1, y)))
            if y + 1 < side:
                edges.append(((x, y), (x, y + 1)))
    return edges


def _neighbors_3d(side: int) -> List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
    edges: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = []
    for z in range(side):
        for y in range(side):
            for x in range(side):
                if x + 1 < side:
                    edges.append(((x, y, z), (x + 1, y, z)))
                if y + 1 < side:
                    edges.append(((x, y, z), (x, y + 1, z)))
                if z + 1 < side:
                    edges.append(((x, y, z), (x, y, z + 1)))
    return edges


def _hash_residual(bits: np.ndarray) -> int:
    # Hash a residual pattern to an int label for empirical entropy across blocks.
    b = bytes(int(x) & 1 for x in bits.tolist())
    h = hashlib.sha256(b).digest()
    return int.from_bytes(h[:8], "little", signed=False)


@dataclass(frozen=True)
class AlgoResult:
    recon_error: float
    smoothness: float
    H_residual_emp: float
    residual_energy: float
    H_residual_bitpos_mean: float


def _binary_entropy(p: float) -> float:
    p = float(p)
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return float(-(p * math.log(p, 2.0) + (1.0 - p) * math.log(1.0 - p, 2.0)))


def _agg_majority(block: np.ndarray) -> int:
    return 1 if float(np.mean(block)) >= 0.5 else 0


def _agg_threshold(block: np.ndarray, theta: float) -> int:
    return 1 if float(np.mean(block)) >= float(theta) else 0


def _agg_parity(block: np.ndarray) -> int:
    return int(int(np.sum(block)) & 1)


def _smooth_iter(coarse: np.ndarray, neighbor_lists: List[List[int]], lam: float, iters: int) -> np.ndarray:
    y = coarse.astype(np.float64)
    for _ in range(int(iters)):
        y2 = y.copy()
        for i, nbrs in enumerate(neighbor_lists):
            if not nbrs:
                continue
            nbr_mean = float(np.mean(y[nbrs]))
            score = (1.0 - lam) * float(y[i]) + lam * nbr_mean
            y2[i] = 1.0 if score >= 0.5 else 0.0
        y = y2
    return y.astype(np.uint8)


def _eval_2d(m_from: int, m_to: int, B: np.ndarray, algo: str, seed: int) -> AlgoResult:
    p_from = m_from // 2
    p_to = m_to // 2
    side_f = 1 << int(p_from)
    side_c = 1 << int(p_to)
    block_side = 1 << int(p_from - p_to)
    hc = HilbertCurve(p=int(p_from), n=2)

    # Gather blocks, then compute residuals against the FINAL coarse bits (after optional smoothing).
    coarse = np.zeros((side_c, side_c), dtype=np.uint8)
    blocks: List[np.ndarray] = [np.zeros((block_side * block_side,), dtype=np.uint8) for _ in range(side_c * side_c)]
    for yc in range(side_c):
        for xc in range(side_c):
            bits: List[int] = []
            for dy in range(block_side):
                for dx in range(block_side):
                    x = xc * block_side + dx
                    y = yc * block_side + dy
                    t = int(hc.distance_from_point([x, y]))
                    bits.append(int(B[t]))
            block = np.array(bits, dtype=np.uint8)
            blocks[int(yc) * int(side_c) + int(xc)] = block
            if algo == "majority" or algo.startswith("majority_smooth_"):
                cb = _agg_majority(block)
            elif algo == "threshold_0.6":
                cb = _agg_threshold(block, theta=0.6)
            elif algo == "parity":
                cb = _agg_parity(block)
            else:
                raise ValueError(f"unknown algo: {algo}")
            coarse[yc, xc] = int(cb)

    # Optional smoothing on coarse adjacency for a variant (data term = initial coarse).
    if algo.startswith("majority_smooth_"):
        lam = float(algo.split("_")[-1])
        # neighbor lists for 4-neighborhood on coarse grid
        neighbor_lists: List[List[int]] = []
        for yy in range(side_c):
            for xx in range(side_c):
                nbrs: List[int] = []
                if xx - 1 >= 0:
                    nbrs.append(yy * side_c + (xx - 1))
                if xx + 1 < side_c:
                    nbrs.append(yy * side_c + (xx + 1))
                if yy - 1 >= 0:
                    nbrs.append((yy - 1) * side_c + xx)
                if yy + 1 < side_c:
                    nbrs.append((yy + 1) * side_c + xx)
                neighbor_lists.append(nbrs)
        flat = coarse.reshape(-1)
        flat2 = _smooth_iter(flat, neighbor_lists=neighbor_lists, lam=lam, iters=12)
        coarse = flat2.reshape((side_c, side_c))

    # Residual statistics (computed against FINAL coarse bits).
    residual_labels: Dict[int, int] = {}
    res_ones_total = 0
    res_pos_ones = np.zeros((block_side * block_side,), dtype=np.int64)
    for yc in range(side_c):
        for xc in range(side_c):
            cb = int(coarse[yc, xc])
            block = blocks[int(yc) * int(side_c) + int(xc)]
            res = block ^ int(cb)
            lbl = _hash_residual(res)
            residual_labels[lbl] = residual_labels.get(lbl, 0) + 1
            res_ones_total += int(np.sum(res))
            res_pos_ones += res.astype(np.int64)

    # reconstruction error (expand coarse to fine grid)
    mism = 0
    total = side_f * side_f
    for y in range(side_f):
        yc = y // block_side
        for x in range(side_f):
            xc = x // block_side
            cb = int(coarse[yc, xc])
            t = int(hc.distance_from_point([x, y]))
            mism += 1 if int(B[t]) != cb else 0
    recon = float(mism) / float(total)

    # smoothness on coarse adjacency (4-neighbor)
    edges = _neighbors_2d(side_c)
    same = 0
    for (a, b) in edges:
        xa, ya = a
        xb, yb = b
        same += 1 if int(coarse[ya, xa]) == int(coarse[yb, xb]) else 0
    smooth = float(same) / float(len(edges)) if edges else 0.0
    Hres = entropy_base2_from_counts(residual_labels)
    n_blocks = int(side_c) * int(side_c)
    block_size = int(block_side) * int(block_side)
    p_res = float(res_ones_total) / float(n_blocks * block_size)
    Hbitpos = float(np.mean([_binary_entropy(float(c) / float(n_blocks)) for c in res_pos_ones.tolist()]))
    return AlgoResult(recon_error=recon, smoothness=smooth, H_residual_emp=Hres, residual_energy=p_res, H_residual_bitpos_mean=Hbitpos)


def _eval_3d(m_from: int, m_to: int, B: np.ndarray, algo: str, seed: int) -> AlgoResult:
    p_from = m_from // 3
    p_to = m_to // 3
    side_f = 1 << int(p_from)
    side_c = 1 << int(p_to)
    block_side = 1 << int(p_from - p_to)
    hc = HilbertCurve(p=int(p_from), n=3)

    coarse = np.zeros((side_c, side_c, side_c), dtype=np.uint8)
    blocks: List[np.ndarray] = [np.zeros((block_side * block_side * block_side,), dtype=np.uint8) for _ in range(side_c * side_c * side_c)]
    for zc in range(side_c):
        for yc in range(side_c):
            for xc in range(side_c):
                bits: List[int] = []
                for dz in range(block_side):
                    for dy in range(block_side):
                        for dx in range(block_side):
                            x = xc * block_side + dx
                            y = yc * block_side + dy
                            z = zc * block_side + dz
                            t = int(hc.distance_from_point([x, y, z]))
                            bits.append(int(B[t]))
                block = np.array(bits, dtype=np.uint8)
                blocks[int(zc) * (int(side_c) * int(side_c)) + int(yc) * int(side_c) + int(xc)] = block
                if algo == "majority" or algo.startswith("majority_smooth_"):
                    cb = _agg_majority(block)
                elif algo == "threshold_0.6":
                    cb = _agg_threshold(block, theta=0.6)
                elif algo == "parity":
                    cb = _agg_parity(block)
                else:
                    raise ValueError(f"unknown algo: {algo}")
                coarse[zc, yc, xc] = int(cb)

    if algo.startswith("majority_smooth_"):
        lam = float(algo.split("_")[-1])
        neighbor_lists: List[List[int]] = []
        for zz in range(side_c):
            for yy in range(side_c):
                for xx in range(side_c):
                    nbrs: List[int] = []
                    if xx - 1 >= 0:
                        nbrs.append(zz * (side_c * side_c) + yy * side_c + (xx - 1))
                    if xx + 1 < side_c:
                        nbrs.append(zz * (side_c * side_c) + yy * side_c + (xx + 1))
                    if yy - 1 >= 0:
                        nbrs.append(zz * (side_c * side_c) + (yy - 1) * side_c + xx)
                    if yy + 1 < side_c:
                        nbrs.append(zz * (side_c * side_c) + (yy + 1) * side_c + xx)
                    if zz - 1 >= 0:
                        nbrs.append((zz - 1) * (side_c * side_c) + yy * side_c + xx)
                    if zz + 1 < side_c:
                        nbrs.append((zz + 1) * (side_c * side_c) + yy * side_c + xx)
                    neighbor_lists.append(nbrs)
        flat = coarse.reshape(-1)
        flat2 = _smooth_iter(flat, neighbor_lists=neighbor_lists, lam=lam, iters=12)
        coarse = flat2.reshape((side_c, side_c, side_c))

    residual_labels: Dict[int, int] = {}
    res_ones_total = 0
    res_pos_ones = np.zeros((block_side * block_side * block_side,), dtype=np.int64)
    for zc in range(side_c):
        for yc in range(side_c):
            for xc in range(side_c):
                cb = int(coarse[zc, yc, xc])
                block = blocks[int(zc) * (int(side_c) * int(side_c)) + int(yc) * int(side_c) + int(xc)]
                res = block ^ int(cb)
                lbl = _hash_residual(res)
                residual_labels[lbl] = residual_labels.get(lbl, 0) + 1
                res_ones_total += int(np.sum(res))
                res_pos_ones += res.astype(np.int64)

    mism = 0
    total = side_f * side_f * side_f
    for z in range(side_f):
        zc = z // block_side
        for y in range(side_f):
            yc = y // block_side
            for x in range(side_f):
                xc = x // block_side
                cb = int(coarse[zc, yc, xc])
                t = int(hc.distance_from_point([x, y, z]))
                mism += 1 if int(B[t]) != cb else 0
    recon = float(mism) / float(total)

    edges = _neighbors_3d(side_c)
    same = 0
    for (a, b) in edges:
        xa, ya, za = a
        xb, yb, zb = b
        same += 1 if int(coarse[za, ya, xa]) == int(coarse[zb, yb, xb]) else 0
    smooth = float(same) / float(len(edges)) if edges else 0.0
    Hres = entropy_base2_from_counts(residual_labels)
    n_blocks = int(side_c) * int(side_c) * int(side_c)
    block_size = int(block_side) * int(block_side) * int(block_side)
    p_res = float(res_ones_total) / float(n_blocks * block_size)
    Hbitpos = float(np.mean([_binary_entropy(float(c) / float(n_blocks)) for c in res_pos_ones.tolist()]))
    return AlgoResult(recon_error=recon, smoothness=smooth, H_residual_emp=Hres, residual_energy=p_res, H_residual_bitpos_mean=Hbitpos)


def write_tex(m_from: int, m_to: int, rows: List[List[str]], out_path: Path) -> None:
    tab = booktabs_tabular(
        col_spec="l l r r r r r",
        header=[
            NoEscape("layout"),
            NoEscape("algo"),
            NoEscape(r"recon\_error"),
            NoEscape("smoothness"),
            NoEscape(r"$H(\mathrm{res})$"),
            NoEscape(r"res\_energy"),
            NoEscape(r"$\overline{H_{\mathrm{bit}}}$"),
        ],
        rows=[[NoEscape(c) if i < 2 else NoEscape(c) for i, c in enumerate(r)] for r in rows],
    )
    header = "\n".join(
        [
            rf"\paragraph{{Hilbert 块压缩算法对照（自动生成，$m'={m_from}$ 到 $m={m_to}$）}}",
            r"\AuditTag 本片段由 \texttt{scripts/exp\_hilbert\_block\_compress\_compare.py} 生成。",
            r"\AuditTag 使用一条确定性伪随机数据带 $B(t)$（长度 $2^{m'}$）。对每个 coarse 块输出 1 bit；残差为块内模式相对 coarse bit 的 XOR，并报告其跨块经验熵。",
            "",
        ]
    )
    write_tex_fragment(out_path, header + tab.dumps() + "\n", comment="Auto-generated by scripts/exp_hilbert_block_compress_compare.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m-from", type=int, default=12)
    ap.add_argument("--m-to", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--seeds",
        type=str,
        default="",
        help="Comma-separated seeds (overrides --seed) for aggregated statistics, e.g. 0,1,2,3,4,5,6,7",
    )
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m_from = int(args.m_from)
    m_to = int(args.m_to)
    seeds_raw = str(args.seeds).strip()
    if seeds_raw:
        seeds = [int(s.strip()) for s in seeds_raw.split(",") if s.strip() != ""]
    else:
        seeds = [int(args.seed)]
    if not seeds:
        raise ValueError("no seeds provided")
    if m_to >= m_from:
        raise ValueError("require m_to < m_from")

    if (m_from % 2) != 0 or (m_to % 2) != 0:
        raise ValueError("2D layout requires m_from and m_to divisible by 2")
    if (m_from % 3) != 0 or (m_to % 3) != 0:
        raise ValueError("3D layout requires m_from and m_to divisible by 3")

    script_path = Path(__file__).resolve()
    params = {"m_from": m_from, "m_to": m_to, "seeds": seeds}
    run = prepare_run(
        experiment="hilbert_block_compress_compare",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "table.tex"],
        force=bool(args.force),
    )
    out_json = run.run_dir / "summary.json"
    out_run_tex = run.run_dir / "table.tex"
    out_tex = generated_dir() / f"hilbert_block_compress_compare_m{m_from}_to_m{m_to}.tex"

    if run.cached:
        print(f"[hilbert_block_compress_compare] cached: {run.run_dir}", flush=True)
        out_tex.write_text(out_run_tex.read_text(encoding="utf-8"), encoding="utf-8")
        return

    prog = Progress(every_seconds=15.0)
    prog.maybe(f"evaluating {len(seeds)} seeds")

    algos = ["majority", "majority_smooth_0.30", "majority_smooth_0.60", "threshold_0.6", "parity"]
    # Collect per-seed metrics then aggregate.
    per_seed: Dict[int, Dict[str, Dict[str, AlgoResult]]] = {}
    for sd in seeds:
        prog.maybe(f"seed={sd}")
        B = _bit_tape(m_from=m_from, seed=int(sd))
        per_seed[int(sd)] = {"2d": {}, "3d": {}}
        for algo in algos:
            per_seed[int(sd)]["2d"][algo] = _eval_2d(m_from=m_from, m_to=m_to, B=B, algo=algo, seed=int(sd))
            per_seed[int(sd)]["3d"][algo] = _eval_3d(m_from=m_from, m_to=m_to, B=B, algo=algo, seed=int(sd))

    def _agg(layout: str, algo: str) -> Dict[str, float]:
        vals = [per_seed[sd][layout][algo] for sd in per_seed.keys()]
        recon = np.array([v.recon_error for v in vals], dtype=np.float64)
        smooth = np.array([v.smoothness for v in vals], dtype=np.float64)
        hres = np.array([v.H_residual_emp for v in vals], dtype=np.float64)
        rene = np.array([v.residual_energy for v in vals], dtype=np.float64)
        hbit = np.array([v.H_residual_bitpos_mean for v in vals], dtype=np.float64)
        return {
            "recon_mean": float(np.mean(recon)),
            "recon_std": float(np.std(recon, ddof=0)),
            "smooth_mean": float(np.mean(smooth)),
            "smooth_std": float(np.std(smooth, ddof=0)),
            "Hres_mean": float(np.mean(hres)),
            "Hres_std": float(np.std(hres, ddof=0)),
            "res_energy_mean": float(np.mean(rene)),
            "res_energy_std": float(np.std(rene, ddof=0)),
            "Hbit_mean": float(np.mean(hbit)),
            "Hbit_std": float(np.std(hbit, ddof=0)),
        }

    rows: List[List[str]] = []
    summary: Dict[str, Dict[str, Dict[str, float]]] = {"2d": {}, "3d": {}}
    for layout in ("2d", "3d"):
        for algo in algos:
            st = _agg(layout=layout, algo=algo)
            summary[layout][algo] = dict(st)
            rows.append(
                [
                    r"\texttt{2D}" if layout == "2d" else r"\texttt{3D}",
                    rf"\texttt{{{algo.replace('_', r'\_')}}}",
                    rf"{st['recon_mean']:.4f} $\pm$ {st['recon_std']:.4f}",
                    rf"{st['smooth_mean']:.4f} $\pm$ {st['smooth_std']:.4f}",
                    rf"{st['Hres_mean']:.4f} $\pm$ {st['Hres_std']:.4f}",
                    rf"{st['res_energy_mean']:.4f} $\pm$ {st['res_energy_std']:.4f}",
                    rf"{st['Hbit_mean']:.4f} $\pm$ {st['Hbit_std']:.4f}",
                ]
            )

    write_tex(m_from=m_from, m_to=m_to, rows=rows, out_path=out_run_tex)
    out_tex.write_text(out_run_tex.read_text(encoding="utf-8"), encoding="utf-8")
    payload = {"params": params, "summary": summary, "seeds": list(seeds)}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest = build_base_manifest("hilbert_block_compress_compare", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "table.tex"])
    write_manifest(run.run_dir, manifest)

    prog.done(f"wrote {out_json} and {out_tex}")


if __name__ == "__main__":
    main()

