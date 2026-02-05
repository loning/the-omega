#!/usr/bin/env python3
r"""
Scan Fourier coefficients for Fold_m collision/multiplicity, without enumerating Omega_m.

Setup (paper §5):
  - Omega_m = {0,1}^m
  - N(b) = sum_{k=1..m} b_k * F_{k+1}
  - M = F_{m+2}
  - c_m(r) = #{ b : N(b) ≡ r (mod M) }

Key identities (paper §5):
  - \hat c_m(j) = sum_r c_m(r) zeta^{jr} = sum_{b in Omega_m} zeta^{jN(b)}
                = prod_{k=1..m} (1 + zeta^{jF_{k+1}})
  - | \hat c_m(j) |^2 = prod_{k=1..m} |1 + exp(2π i j F_{k+1}/M)|^2
                      = prod_{k=1..m} (2 + 2 cos(2π j F_{k+1}/M))

Outputs:
  - artifacts/fold_collision_fourier_scan/<run_id>/summary.json
  - sections/generated/fold_collision_fourier_scan_summary.tex
  - sections/generated/fold_collision_fourier_scan_summary.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import generated_dir
from common_zeckendorf import fib_zeckendorf_upto


def _parse_ms(s: str) -> List[int]:
    out: List[int] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    out = sorted(set(out))
    if not out:
        raise ValueError("--ms must contain at least one integer, e.g. --ms 12,14,16")
    return out


def _abs2_hat_all_j(m: int) -> Dict[str, Any]:
    """
    Return:
      - M, F_m, F_{m+1}
      - abs2: np.ndarray shape (M,), where abs2[j] = |hat c_m(j)|^2
    """
    if m < 1:
        raise ValueError("m must be >= 1")

    # fib_zeckendorf_upto(k) returns [F2, F3, ..., F_{k+1}] (k terms), with weights [1,2,3,5,...]
    weights = fib_zeckendorf_upto(m)  # [F2..F_{m+1}] == [F_{k+1}]_{k=1..m}
    fib_upto_m2 = fib_zeckendorf_upto(m + 1)  # [F2..F_{m+2}]
    M = int(fib_upto_m2[-1])  # F_{m+2}
    F_m1 = int(fib_upto_m2[-2])  # F_{m+1}
    F_m = int(M - F_m1)  # since F_{m+2}=F_{m+1}+F_m

    j = np.arange(M, dtype=np.int64)
    abs2 = np.ones(M, dtype=np.float64)
    two_pi_over_M = (2.0 * math.pi) / float(M)

    # abs2[j] = ∏_{k=1..m} (2 + 2 cos(2π j F_{k+1}/M))
    for w in weights:
        a = (j * int(w)) % M
        ang = two_pi_over_M * a.astype(np.float64)
        factor = 2.0 + 2.0 * np.cos(ang)
        # Numerical guard: clamp tiny negatives caused by rounding.
        factor = np.maximum(factor, 0.0)
        abs2 *= factor

    # Force exact value at j=0: |hat c_m(0)|^2 = |Omega_m|^2 = 4^m (exact power of 2).
    abs2[0] = float(4**m)

    return {"m": m, "M": M, "F_m": F_m, "F_m1": F_m1, "abs2": abs2}


def _top_indices(values: np.ndarray, k: int) -> np.ndarray:
    """
    Return indices of top-k entries in `values` (descending by value).
    """
    if k <= 0:
        return np.array([], dtype=np.int64)
    k = min(int(k), int(values.size))
    if k == values.size:
        idx = np.argsort(values)
        return idx[::-1]
    idx = np.argpartition(values, -k)[-k:]
    idx = idx[np.argsort(values[idx])[::-1]]
    return idx


def _fmt_float(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{x:.{digits}f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=str, default="12,14,16,18,20,22,24,26", help="Comma-separated m values.")
    ap.add_argument("--topk", type=int, default=10, help="How many top nontrivial characters to report.")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ms = _parse_ms(args.ms)
    topk = int(args.topk)
    if topk < 1:
        raise ValueError("--topk must be >= 1")

    script_path = Path(__file__).resolve()
    params: Dict[str, Any] = {"ms": ms, "topk": topk}
    run = prepare_run(
        experiment="fold_collision_fourier_scan",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "fold_collision_fourier_scan_summary.tex", "fold_collision_fourier_scan_summary.json"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_run_tex = run.run_dir / "fold_collision_fourier_scan_summary.tex"
    out_run_gen_json = run.run_dir / "fold_collision_fourier_scan_summary.json"
    out_tex = generated_dir() / "fold_collision_fourier_scan_summary.tex"
    out_gen_json = generated_dir() / "fold_collision_fourier_scan_summary.json"

    if run.cached:
        print(f"[fold_collision_fourier_scan] cached: {run.run_dir}", flush=True)
        copy_atomic(out_run_tex, out_tex)
        copy_atomic(out_run_gen_json, out_gen_json)
        return

    results: List[Dict[str, Any]] = []
    tex_rows: List[str] = []

    for m in ms:
        pack = _abs2_hat_all_j(m)
        M = int(pack["M"])
        F_m = int(pack["F_m"])
        F_m1 = int(pack["F_m1"])
        abs2: np.ndarray = pack["abs2"]

        # Nontrivial indices j=1..M-1
        tail = abs2[1:]
        tail_sum = float(np.sum(tail))

        top_idx0 = _top_indices(tail, k=min(topk, M - 1))  # indices in 0..M-2
        top_js = (top_idx0 + 1).astype(np.int64)  # shift to 1..M-1

        j1 = int(top_js[0]) if top_js.size >= 1 else -1
        j2 = int(top_js[1]) if top_js.size >= 2 else -1

        top_sum = float(np.sum(abs2[top_js])) if top_js.size else 0.0
        top_frac = (top_sum / tail_sum) if tail_sum > 0.0 else float("nan")

        main_abs2 = float(4**m)
        ratio_max = float(abs2[j1] / main_abs2) if j1 >= 0 else float("nan")
        j_disp_1, j_disp_2 = (sorted([j1, j2]) if (j1 >= 0 and j2 >= 0) else (j1, j2))

        # Symmetry check: |hat(j)|^2 should equal |hat(-j)|^2 = |hat(M-j)|^2
        sym_diff = float(np.max(np.abs(abs2[1:] - abs2[:0:-1]))) if M >= 2 else 0.0

        S2 = float(np.sum(abs2) / float(M))
        S2_main = float(main_abs2 / float(M))
        S2_dev = float(S2 - S2_main)

        expected_pair = sorted([F_m, F_m1])
        got_pair = sorted([j1, j2]) if (j1 >= 0 and j2 >= 0) else [j1, j2]
        hit_pair = (got_pair == expected_pair)

        results.append(
            {
                "m": int(m),
                "M": int(M),
                "F_m": int(F_m),
                "F_m1": int(F_m1),
                "top_js": [int(x) for x in top_js.tolist()],
                "top_abs2": [float(abs2[int(x)]) for x in top_js.tolist()],
                "top_abs2_over_4m": [float(abs2[int(x)] / main_abs2) for x in top_js.tolist()],
                "tail_sum_abs2": float(tail_sum),
                "topk_tail_fraction": float(top_frac),
                "S2": float(S2),
                "S2_main": float(S2_main),
                "S2_deviation": float(S2_dev),
                "symmetry_max_abs_diff": float(sym_diff),
                "top2_hits_expected_pair": bool(hit_pair),
            }
        )

        tex_rows.append(rf"{m} & {M} & {j_disp_1} & {j_disp_2} & {_fmt_float(ratio_max, 6)} & {_fmt_float(top_frac, 4)} \\")

    summary: Dict[str, Any] = {"params": params, "results": results}

    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    out_run_gen_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append(r"\paragraph{Fold 碰撞矩：Fourier 角色扫描（自动生成）}")
    lines.append(
        r"\AuditTag 本片段由 \texttt{scripts/exp\_fold\_collision\_fourier\_scan.py} 生成；"
        rf"使用推论~\ref{{cor:S2_parseval}} 的 Parseval 表达避免枚举 $\Omega_m$；本表取 $K={topk}$。"
    )
    lines.append(r"\begin{center}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{r r r r r r}")
    lines.append(r"\toprule")
    lines.append(
        r"$m$ & $M=F_{m+2}$ & $j_1$ & $j_2$ & $\frac{|\widehat c_m(j_1)|^2}{4^m}$ & $\frac{\sum_{j\in\mathrm{Top}\,K}|\widehat c_m(j)|^2}{\sum_{j\neq 0}|\widehat c_m(j)|^2}$\\"
    )
    lines.append(r"\midrule")
    lines.extend(tex_rows)
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")

    out_run_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
    copy_atomic(out_run_tex, out_tex)
    copy_atomic(out_run_gen_json, out_gen_json)

    manifest = build_base_manifest(
        experiment=run.experiment,
        run_id=run.run_id,
        params=params,
        script_path=script_path,
    )
    manifest = add_output_hashes(
        manifest,
        run_dir=run.run_dir,
        rel_paths=["summary.json", "fold_collision_fourier_scan_summary.tex", "fold_collision_fourier_scan_summary.json"],
    )
    write_manifest(run.run_dir, manifest)

    print(f"[fold_collision_fourier_scan] wrote: {out_tex}", flush=True)


if __name__ == "__main__":
    main()

