#!/usr/bin/env python3
"""
Hilbert recursive scale truncation experiment (m_from -> m_to), under Zeckendorf encoding.

We treat microstates as Omega_{m_from} = {0,1}^{m_from} (packed as ints 0..2^{m_from}-1),
and the observable space as X_{m_to} (stable words, no adjacent 1s).

We compare three scale-compression families:
  - hilbert2d: 2D Hilbert coarse-graining of the address, then Fold_{m_to} (Space_m) to X_{m_to}
  - hilbert3d: 3D Hilbert coarse-graining of the address, then Fold_{m_to}
  - hilbert2d_and_3d: both 2D and 3D constraints active (not mixed); choose x by CAP min-cost,
                      and carry both decompositions as time residual evidence.

Outputs:
  - artifacts/hilbert_scale_truncation/<run_id>/summary.json
  - sections/generated/hilbert_scale_truncation_m{m_from}_to_m{m_to}_compare.tex
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from hilbertcurve.hilbertcurve import HilbertCurve

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_progress import Progress
from common_pylatex import NoEscape, booktabs_tabular, write_tex_fragment
from common_zeckendorf import build_fold_domain
from truncations import get_truncation


def entropy_base2_from_probs(ps: List[float]) -> float:
    h = 0.0
    for p in ps:
        if p > 0.0:
            h -= p * math.log(p, 2.0)
    return h


def hamming_upto_m(a: int, b: int, m: int) -> int:
    x = (int(a) ^ int(b)) & ((1 << int(m)) - 1)
    return int(x.bit_count())


def _bit_tape(m_from: int, seed: int) -> List[int]:
    """
    Deterministic pseudo-random tape B(t) in {0,1}^{2^m_from}.
    Use SHA256(seed||t) to avoid global RNG dependence.
    """
    n = 1 << int(m_from)
    out = [0 for _ in range(n)]
    s0 = int(seed).to_bytes(8, "little", signed=False)
    for t in range(n):
        h = hashlib.sha256(s0 + int(t).to_bytes(8, "little", signed=False)).digest()
        out[t] = 1 if (h[0] & 1) else 0
    return out


def _pack_bits_lsb(bits: List[int], m: int) -> int:
    x = 0
    for i in range(int(m)):
        if i < len(bits) and (int(bits[i]) & 1):
            x |= 1 << i
    return int(x)


def _mean(xs: List[float]) -> float:
    return float(sum(xs) / float(len(xs))) if xs else 0.0


def _std_pop(xs: List[float]) -> float:
    if not xs:
        return 0.0
    mu = _mean(xs)
    return float(math.sqrt(sum((x - mu) * (x - mu) for x in xs) / float(len(xs))))


def _compute_seed(
    *,
    m_from: int,
    m_to: int,
    seed: int,
    hc2_from: HilbertCurve,
    hc3_from: HilbertCurve,
    tr_fold,
    X_all: List[int],
) -> Tuple[Dict[str, Counter[int]], Dict[str, Counter[int]], Dict[str, Dict[int, Counter[int]]]]:
    B = _bit_tape(m_from=m_from, seed=seed)
    families = ("hilbert2d", "hilbert3d", "hilbert2d_and_3d")
    counts_x: Dict[str, Counter[int]] = {k: Counter() for k in families}
    counts_u: Dict[str, Counter[int]] = {k: Counter() for k in families}
    x_to_u: Dict[str, Dict[int, Counter[int]]] = {k: {} for k in families}

    n_micro = 1 << int(m_from)
    for t in range(n_micro):
        # 2D neighborhood samples (center + 4-neigh + time-neigh).
        p2_from = m_from // 2
        side2 = 1 << int(p2_from)
        pt2 = tuple(int(v) for v in hc2_from.point_from_distance(int(t)))
        b2_bits: List[int] = [int(B[t])]
        for nb in _neighbors_2d((pt2[0], pt2[1]), side=side2):
            tnb = int(hc2_from.distance_from_point([int(nb[0]), int(nb[1])]))
            b2_bits.append(int(B[tnb]))
        t_next = (int(t) + 1) & (int(n_micro) - 1)
        b2_bits.append(int(B[t_next]))
        b2 = _pack_bits_lsb(b2_bits, m=m_to)
        votes2: List[int] = [int(tr_fold.space_word(int(b2), m=m_to))]
        for nb in _neighbors_2d((pt2[0], pt2[1]), side=side2):
            tnb = int(hc2_from.distance_from_point([int(nb[0]), int(nb[1])]))
            pnb = tuple(int(v) for v in hc2_from.point_from_distance(int(tnb)))
            nb_bits: List[int] = [int(B[tnb])]
            for nb2 in _neighbors_2d((pnb[0], pnb[1]), side=side2):
                t2 = int(hc2_from.distance_from_point([int(nb2[0]), int(nb2[1])]))
                nb_bits.append(int(B[t2]))
            t2n = (int(tnb) + 1) & (int(n_micro) - 1)
            nb_bits.append(int(B[t2n]))
            bnb = _pack_bits_lsb(nb_bits, m=m_to)
            votes2.append(int(tr_fold.space_word(int(bnb), m=m_to)))
        x2 = _cap_choose_x_from_local_votes(X_all=X_all, votes=votes2, m_to=m_to)

        # 3D neighborhood samples (center + up to 5 axial neigh; pad with time-neigh if needed).
        p3_from = m_from // 3
        side3 = 1 << int(p3_from)
        pt3 = tuple(int(v) for v in hc3_from.point_from_distance(int(t)))
        b3_bits: List[int] = [int(B[t])]
        for nb in _neighbors_3d((pt3[0], pt3[1], pt3[2]), side=side3):
            tnb = int(hc3_from.distance_from_point([int(nb[0]), int(nb[1]), int(nb[2])]))
            b3_bits.append(int(B[tnb]))
            if len(b3_bits) >= int(m_to):
                break
        while len(b3_bits) < int(m_to):
            t_next = (int(t) + 1) & (int(n_micro) - 1)
            b3_bits.append(int(B[t_next]))
        b3 = _pack_bits_lsb(b3_bits, m=m_to)
        votes3: List[int] = [int(tr_fold.space_word(int(b3), m=m_to))]
        for nb in _neighbors_3d((pt3[0], pt3[1], pt3[2]), side=side3):
            tnb = int(hc3_from.distance_from_point([int(nb[0]), int(nb[1]), int(nb[2])]))
            pnb = tuple(int(v) for v in hc3_from.point_from_distance(int(tnb)))
            nb_bits: List[int] = [int(B[tnb])]
            for nb3 in _neighbors_3d((pnb[0], pnb[1], pnb[2]), side=side3):
                t2 = int(hc3_from.distance_from_point([int(nb3[0]), int(nb3[1]), int(nb3[2])]))
                nb_bits.append(int(B[t2]))
                if len(nb_bits) >= int(m_to):
                    break
            while len(nb_bits) < int(m_to):
                t2n = (int(tnb) + 1) & (int(n_micro) - 1)
                nb_bits.append(int(B[t2n]))
            bnb = _pack_bits_lsb(nb_bits, m=m_to)
            votes3.append(int(tr_fold.space_word(int(bnb), m=m_to)))
        x3 = _cap_choose_x_from_local_votes(X_all=X_all, votes=votes3, m_to=m_to)

        # U carries the local micro word and the chosen x (as evidence).
        u2 = int(int(b2) | (int(x2) << int(m_to)))
        u3 = int(int(b3) | (int(x3) << int(m_to)))
        x23 = _cap_choose_x_from_local_votes(X_all=X_all, votes=[x2, x3], m_to=m_to)
        u23 = int(u2) | (int(u3) << (2 * int(m_to)))

        counts_x["hilbert2d"][x2] += 1
        counts_u["hilbert2d"][u2] += 1
        x_to_u["hilbert2d"].setdefault(x2, Counter())[u2] += 1

        counts_x["hilbert3d"][x3] += 1
        counts_u["hilbert3d"][u3] += 1
        x_to_u["hilbert3d"].setdefault(x3, Counter())[u3] += 1

        counts_x["hilbert2d_and_3d"][x23] += 1
        counts_u["hilbert2d_and_3d"][u23] += 1
        x_to_u["hilbert2d_and_3d"].setdefault(x23, Counter())[u23] += 1

    return counts_x, counts_u, x_to_u

def _neighbors_2d(point: Tuple[int, int], side: int) -> List[Tuple[int, int]]:
    x, y = int(point[0]), int(point[1])
    out: List[Tuple[int, int]] = []
    if x - 1 >= 0:
        out.append((x - 1, y))
    if x + 1 < side:
        out.append((x + 1, y))
    if y - 1 >= 0:
        out.append((x, y - 1))
    if y + 1 < side:
        out.append((x, y + 1))
    return out


def _neighbors_3d(point: Tuple[int, int, int], side: int) -> List[Tuple[int, int, int]]:
    x, y, z = int(point[0]), int(point[1]), int(point[2])
    out: List[Tuple[int, int, int]] = []
    if x - 1 >= 0:
        out.append((x - 1, y, z))
    if x + 1 < side:
        out.append((x + 1, y, z))
    if y - 1 >= 0:
        out.append((x, y - 1, z))
    if y + 1 < side:
        out.append((x, y + 1, z))
    if z - 1 >= 0:
        out.append((x, y, z - 1))
    if z + 1 < side:
        out.append((x, y, z + 1))
    return out


def _cap_choose_x_from_local_votes(X_all: List[int], votes: List[int], m_to: int) -> int:
    """
    CAP min-cost representative:
      minimize sum_{v in votes} d_H(x, v) (Hamming on m_to bits),
      tie-break by smaller integer x.
    """
    best_x = None
    best_cost = None
    for cand in X_all:
        c = 0
        for v in votes:
            c += hamming_upto_m(int(cand), int(v), m=m_to)
        if best_cost is None or c < best_cost or (c == best_cost and int(cand) < int(best_x)):
            best_cost = int(c)
            best_x = int(cand)
    assert best_x is not None
    return int(best_x)


def _make_fold_fiber_index(m_to: int) -> Tuple[Dict[int, List[int]], Dict[Tuple[int, int], int]]:
    """
    Build:
      - fiber_map[x] = sorted list of b in Omega_{m_to} such that Fold_{m_to}(b)=x
      - idx_map[(x,b)] = index of b within fiber_map[x]
    """
    tr = get_truncation("zeck_window")
    fiber_map: Dict[int, List[int]] = {}
    for b in range(1 << int(m_to)):
        x = tr.space_word(b, m=int(m_to))
        fiber_map.setdefault(int(x), []).append(int(b))
    idx_map: Dict[Tuple[int, int], int] = {}
    for x, bs in fiber_map.items():
        bs.sort()
        for i, b in enumerate(bs):
            idx_map[(int(x), int(b))] = int(i)
    return fiber_map, idx_map


def _project_2d(m_from: int, m_to: int, t_from: int, hc_from: HilbertCurve, hc_to: HilbertCurve) -> Tuple[int, int]:
    # m must be divisible by 2 for 2D Hilbert resolution.
    p_from = int(m_from) // 2
    p_to = int(m_to) // 2
    if 2 * p_from != int(m_from) or 2 * p_to != int(m_to):
        raise ValueError("2D Hilbert projection requires m_from and m_to divisible by 2")
    if p_to > p_from:
        raise ValueError("m_to must be <= m_from for projection")
    shift = p_from - p_to
    x, y = [int(v) for v in hc_from.point_from_distance(int(t_from))]
    if shift == 0:
        t_to = int(hc_to.distance_from_point([x, y]))
        return t_to, 0
    mask = (1 << shift) - 1
    xc, yc = x >> shift, y >> shift
    xr, yr = x & mask, y & mask
    t_to = int(hc_to.distance_from_point([int(xc), int(yc)]))
    r = int(xr) | (int(yr) << shift)  # shift+shift bits
    return t_to, r


def _project_3d(m_from: int, m_to: int, t_from: int, hc_from: HilbertCurve, hc_to: HilbertCurve) -> Tuple[int, int]:
    # m must be divisible by 3 for 3D Hilbert resolution.
    p_from = int(m_from) // 3
    p_to = int(m_to) // 3
    if 3 * p_from != int(m_from) or 3 * p_to != int(m_to):
        raise ValueError("3D Hilbert projection requires m_from and m_to divisible by 3")
    if p_to > p_from:
        raise ValueError("m_to must be <= m_from for projection")
    shift = p_from - p_to
    x, y, z = [int(v) for v in hc_from.point_from_distance(int(t_from))]
    if shift == 0:
        t_to = int(hc_to.distance_from_point([x, y, z]))
        return t_to, 0
    mask = (1 << shift) - 1
    xc, yc, zc = x >> shift, y >> shift, z >> shift
    xr, yr, zr = x & mask, y & mask, z & mask
    t_to = int(hc_to.distance_from_point([int(xc), int(yc), int(zc)]))
    r = int(xr) | (int(yr) << shift) | (int(zr) << (2 * shift))  # shift*3 bits
    return t_to, r


def _compute_stats(
    m_from: int,
    m_to: int,
    family: str,
    counts_x: Counter[int],
    counts_u: Counter[int],
    x_to_u: Dict[int, Counter[int]],
) -> Dict[str, float]:
    n_micro = 1 << int(m_from)
    domain = build_fold_domain(int(m_to))
    fiber_sizes = [int(counts_x.get(x, 0)) for x in domain.macro_words]
    ps = [c / float(n_micro) for c in fiber_sizes if c > 0]
    H_X = entropy_base2_from_probs(ps)
    H_cond = float(m_from) - H_X

    pu = [c / float(n_micro) for c in counts_u.values() if c > 0]
    H_U = entropy_base2_from_probs(pu)

    H_U_given_X = 0.0
    u_support_weighted = 0.0
    for x in domain.macro_words:
        cx = float(counts_x.get(x, 0))
        if cx <= 0.0:
            continue
        cu = x_to_u.get(x, Counter())
        us = [float(c) / cx for c in cu.values() if c > 0]
        H_U_given_X += (cx / float(n_micro)) * entropy_base2_from_probs(us)
        u_support_weighted += (cx / float(n_micro)) * float(len(cu))

    return {
        "m_from": float(m_from),
        "m_to": float(m_to),
        "H_X": float(H_X),
        "H_cond": float(H_cond),
        "H_U": float(H_U),
        "H_U_given_X": float(H_U_given_X),
        "u_support_mean_px": float(u_support_weighted),
        "n_macro": float(len(domain.macro_words)),
    }


def write_compare_tex(
    m_from: int,
    m_to: int,
    rows: List[Tuple[str, Dict[str, float]]],
    out_path: Path,
    seeds: List[int],
) -> None:
    def _tt(s: str) -> str:
        # Minimal LaTeX escaping for \texttt{...}
        return str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_")

    tab_rows = []
    for name, st in rows:
        tab_rows.append(
            [
                NoEscape(rf"\texttt{{{_tt(name)}}}"),
                NoEscape(rf"{st['H_X_mean']:.6f} $\pm$ {st['H_X_std']:.6f}"),
                NoEscape(rf"{st['H_cond_mean']:.6f} $\pm$ {st['H_cond_std']:.6f}"),
                NoEscape(rf"{st['H_U_mean']:.6f} $\pm$ {st['H_U_std']:.6f}"),
                NoEscape(rf"{st['H_U_given_X_mean']:.6f} $\pm$ {st['H_U_given_X_std']:.6f}"),
                NoEscape(rf"{st['u_support_mean_px_mean']:.4f} $\pm$ {st['u_support_mean_px_std']:.4f}"),
            ]
        )
    tab = booktabs_tabular(
        col_spec="l r r r r r",
        header=[
            NoEscape("family"),
            NoEscape(r"$H(X_{m})$"),
            NoEscape(r"$H(\Omega_{m'}\mid X_{m})$"),
            NoEscape(r"$H(U)$"),
            NoEscape(r"$H(U\mid X_{m})$"),
            NoEscape(r"$\mathbb{E}[\#\mathrm{supp}(U\mid x)]$"),
        ],
        rows=tab_rows,
    )
    header = "\n".join(
        [
            rf"\paragraph{{Hilbert 尺度压缩对照（自动生成，$m'={m_from}$ 到 $m={m_to}$）}}",
            r"\AuditTag 本片段由 \texttt{scripts/exp\_hilbert\_scale\_truncation.py} 生成。",
            rf"\AuditTag 本实验对种子集合 \texttt{{{_tt(','.join(str(s) for s in seeds))}}} 聚合统计（均值 $\pm$ 标准差）。值带 $B(t)\in\{{0,1\}}$（长度 $2^{{m'}}$）由种子确定，2D/3D 分别在网格邻域取样拼成 $m$ 位微观字 $b$，再折叠并以 CAP 选取空间代表。",
            "",
        ]
    )
    write_tex_fragment(
        out_path,
        header + tab.dumps() + "\n",
        comment="Auto-generated by scripts/exp_hilbert_scale_truncation.py",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m-from", type=int, default=12)
    ap.add_argument("--m-to", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0, help="Seed for deterministic pseudo-random tape B(t).")
    ap.add_argument("--seeds", type=str, default="", help="Comma-separated seeds (overrides --seed), e.g. 0,1,2,3,4,5,6,7")
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
    if m_from < 1 or m_to < 1:
        raise ValueError("m must be >= 1")
    if m_to >= m_from:
        raise ValueError("require m_to < m_from")
    if (m_from % 2) != 0 or (m_to % 2) != 0:
        raise ValueError("this experiment requires m_from and m_to divisible by 2 (for 2D family)")
    if (m_from % 3) != 0 or (m_to % 3) != 0:
        raise ValueError("this experiment requires m_from and m_to divisible by 3 (for 3D family)")

    script_path = Path(__file__).resolve()
    params = {"m_from": m_from, "m_to": m_to, "seeds": seeds}
    run = prepare_run(
        experiment="hilbert_scale_truncation",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "compare.tex"],
        force=bool(args.force),
    )
    out_json = run.run_dir / "summary.json"
    out_run_tex = run.run_dir / "compare.tex"
    out_tex = generated_dir() / f"hilbert_scale_truncation_m{m_from}_to_m{m_to}_compare.tex"

    if run.cached:
        print(f"[hilbert_scale_truncation] cached: {run.run_dir}", flush=True)
        # Ensure the generated fragment exists for LaTeX input.
        out_tex.write_text(out_run_tex.read_text(encoding="utf-8"), encoding="utf-8")
        return

    prog = Progress(every_seconds=15.0)

    # Hilbert curves for (m_from -> m_to) projections.
    hc2_from = HilbertCurve(p=m_from // 2, n=2)
    hc2_to = HilbertCurve(p=m_to // 2, n=2)
    hc3_from = HilbertCurve(p=m_from // 3, n=3)
    hc3_to = HilbertCurve(p=m_to // 3, n=3)

    # Fold_m_to is the paper's Space_m (default zeck_window instance).
    tr_fold = get_truncation("zeck_window")
    fiber_map, idx_map = _make_fold_fiber_index(m_to=m_to)
    domain = build_fold_domain(int(m_to))
    X_all = list(domain.macro_words)

    families = ("hilbert2d", "hilbert3d", "hilbert2d_and_3d")
    per_seed_stats: Dict[int, Dict[str, Dict[str, float]]] = {}
    for sd in seeds:
        prog.maybe(f"seed={sd}")
        counts_x, counts_u, x_to_u = _compute_seed(
            m_from=m_from,
            m_to=m_to,
            seed=int(sd),
            hc2_from=hc2_from,
            hc3_from=hc3_from,
            tr_fold=tr_fold,
            X_all=X_all,
        )
        per_seed_stats[int(sd)] = {}
        for fam in families:
            per_seed_stats[int(sd)][fam] = _compute_stats(
                m_from=m_from,
                m_to=m_to,
                family=fam,
                counts_x=counts_x[fam],
                counts_u=counts_u[fam],
                x_to_u=x_to_u[fam],
            )

    # Aggregate mean/std per family.
    agg_by_family: Dict[str, Dict[str, float]] = {}
    for fam in families:
        H_Xs = [float(per_seed_stats[sd][fam]["H_X"]) for sd in per_seed_stats.keys()]
        H_conds = [float(per_seed_stats[sd][fam]["H_cond"]) for sd in per_seed_stats.keys()]
        H_Us = [float(per_seed_stats[sd][fam]["H_U"]) for sd in per_seed_stats.keys()]
        H_UgXs = [float(per_seed_stats[sd][fam]["H_U_given_X"]) for sd in per_seed_stats.keys()]
        supps = [float(per_seed_stats[sd][fam]["u_support_mean_px"]) for sd in per_seed_stats.keys()]
        agg_by_family[fam] = {
            "H_X_mean": _mean(H_Xs),
            "H_X_std": _std_pop(H_Xs),
            "H_cond_mean": _mean(H_conds),
            "H_cond_std": _std_pop(H_conds),
            "H_U_mean": _mean(H_Us),
            "H_U_std": _std_pop(H_Us),
            "H_U_given_X_mean": _mean(H_UgXs),
            "H_U_given_X_std": _std_pop(H_UgXs),
            "u_support_mean_px_mean": _mean(supps),
            "u_support_mean_px_std": _std_pop(supps),
        }

    rows = [(fam, agg_by_family[fam]) for fam in families]
    rows.sort(key=lambda kv: kv[0])
    write_compare_tex(m_from=m_from, m_to=m_to, rows=rows, out_path=out_run_tex, seeds=seeds)
    out_tex.write_text(out_run_tex.read_text(encoding="utf-8"), encoding="utf-8")

    payload = {
        "params": params,
        "n_micro": int(1 << int(m_from)),
        "per_seed": per_seed_stats,
        "agg": agg_by_family,
        "families": {
            fam: {
                "stats": agg_by_family[fam],
            }
            for fam in families
        },
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest = build_base_manifest("hilbert_scale_truncation", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "compare.tex"])
    write_manifest(run.run_dir, manifest)

    prog.done(f"wrote {out_json} and {out_tex}")


if __name__ == "__main__":
    main()

