# -*- coding: utf-8 -*-
"""
Window-level ribosome pausing proxy around terminal stops (human RefSeq).

This is a lightweight (offline) mechanistic-proxy check that complements
`exp_riboseq_pause_analysis.py` (codon-level). We compute a window-level pause
proxy by averaging published codon-level pause scores across the k-codon window
immediately upstream of terminal stops.

Data source:
  - data/refseq_hsapiens_mrna/stop_context_candidates.jsonl
    (includes upstream coding window + downstream UTR window, k=10)

Outputs:
  - sections/generated/riboseq_pause_window_proxy.tex
  - data/_cache/riboseq_pause_window_proxy.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE
from stats_tools import cohen_d

# μ* stop codons (RNA)
STOP_CODONS = {"UAA", "UAG", "UGA"}

# Published codon-level pause scores (same table as exp_riboseq_pause_analysis.py).
#
# NOTE: This is a coarse proxy (not read-level Ribo-seq). We use it to test whether
# window-level patterns are trivially induced by known slow/fast codons.
CODON_PAUSE_SCORES = {
    # High pause (slow codons)
    "CGA": 2.8, "CGC": 1.8, "AGA": 2.1, "AGG": 2.0,  # Arg
    "CCA": 1.9, "CCG": 2.2,  # Pro
    "GGG": 1.7,  # Gly
    "AUA": 1.8,  # Ile
    "CUA": 1.6, "UUA": 1.5,  # Leu
    "UCG": 1.6, "AGU": 1.4,  # Ser
    "ACG": 1.5,  # Thr
    "GUA": 1.4, "GUG": 1.2,  # Val
    # Medium pause
    "CGU": 1.3, "CGG": 1.4,
    "CCC": 1.2, "CCU": 1.1,
    "GGA": 1.2, "GGC": 1.0, "GGU": 1.1,
    "AUU": 1.1, "AUC": 0.9,
    "CUC": 1.0, "CUG": 0.9, "CUU": 1.1, "UUG": 1.0,
    "UCC": 1.0, "UCA": 1.1, "UCU": 1.0, "AGC": 0.9,
    "ACC": 0.9, "ACA": 1.0, "ACU": 1.0,
    "GUC": 0.9, "GUU": 1.0,
    # Low pause (fast codons)
    "UUU": 0.8, "UUC": 0.7,  # Phe
    "UAU": 0.8, "UAC": 0.7,  # Tyr
    "CAU": 0.9, "CAC": 0.8,  # His
    "CAA": 0.9, "CAG": 0.8,  # Gln
    "AAU": 0.9, "AAC": 0.8,  # Asn
    "AAA": 0.9, "AAG": 0.7,  # Lys
    "GAU": 0.9, "GAC": 0.8,  # Asp
    "GAA": 0.9, "GAG": 0.8,  # Glu
    "UGU": 0.9, "UGC": 0.8,  # Cys
    "UGG": 1.0,  # Trp
    "GCU": 0.8, "GCC": 0.7, "GCA": 0.9, "GCG": 1.1,  # Ala
    "AUG": 1.0,  # Met (start)
}


def root_dir() -> Path:
    return SCRIPT_DIR.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_dir() -> Path:
    return root_dir() / "data"


def cache_dir() -> Path:
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pause_map() -> dict[str, float]:
    """
    Return a dense pause score map for all codons:
      - sense codons default to 1.0
      - stop codons excluded by callers (but set to 0.0 for completeness)
      - override with CODON_PAUSE_SCORES where available
    """
    m: dict[str, float] = {}
    for codon in GENETIC_CODE:
        m[codon] = 1.0
    for stop in STOP_CODONS:
        m[stop] = 0.0
    for codon, v in CODON_PAUSE_SCORES.items():
        m[codon] = float(v)
    return m


def _window_pause_mean(seq_dna: str, *, pause_map: dict[str, float]) -> float:
    seq = (seq_dna or "").upper().replace("T", "U")
    n = len(seq) - (len(seq) % 3)
    if n <= 0:
        return float("nan")

    vals: list[float] = []
    for i in range(0, n, 3):
        codon = seq[i : i + 3]
        if len(codon) != 3 or any(c not in "ACGU" for c in codon):
            continue
        if codon in STOP_CODONS:
            continue
        v = pause_map.get(codon)
        if v is None or np.isnan(v):
            continue
        vals.append(float(v))

    return float(np.mean(vals)) if vals else float("nan")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _fmt(x: float | None, *, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    return f"{float(x):.{nd}f}"


def _p_fmt(p: float | None) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "--"
    if p < 0.001:
        return "$<$0.001"
    return f"{p:.3f}"


def _group_stats(xs: list[float]) -> dict[str, float]:
    arr = np.array([x for x in xs if not np.isnan(x)], dtype=float)
    if arr.size == 0:
        return {"n": 0.0, "mean": float("nan"), "std": float("nan")}
    return {"n": float(arr.size), "mean": float(np.mean(arr)), "std": float(np.std(arr))}


def _partial_spearman(x: list[float], y: list[float], controls: list[list[float]]) -> dict[str, float]:
    """
    Partial Spearman correlation via rank-transform + linear residualization.

    Returns Pearson correlation on residual ranks (equivalent to partial Spearman).
    """
    x0 = np.array(x, dtype=float)
    y0 = np.array(y, dtype=float)
    c0 = np.array(controls, dtype=float)
    if c0.ndim == 1:
        c0 = c0.reshape(-1, 1)

    m = np.isfinite(x0) & np.isfinite(y0) & np.all(np.isfinite(c0), axis=1)
    n = int(np.sum(m))
    if n < 10:
        return {"n": float(n), "rho": float("nan"), "p": float("nan")}

    xr = stats.rankdata(x0[m])
    yr = stats.rankdata(y0[m])
    cr_cols = [stats.rankdata(c0[m, j]) for j in range(c0.shape[1])]
    cr = np.column_stack(cr_cols) if cr_cols else np.zeros((n, 0), dtype=float)

    A = np.column_stack([np.ones(n, dtype=float), cr])
    bx, *_ = np.linalg.lstsq(A, xr, rcond=None)
    by, *_ = np.linalg.lstsq(A, yr, rcond=None)
    x_res = xr - A @ bx
    y_res = yr - A @ by

    try:
        r, p = stats.pearsonr(x_res, y_res)
    except Exception:
        return {"n": float(n), "rho": float("nan"), "p": float("nan")}

    return {"n": float(n), "rho": float(r), "p": float(p)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Window-level pause proxy around terminal stops (RefSeq candidates).")
    ap.add_argument("--k", type=int, default=10, help="Window size in codons (must match the JSONL content).")
    ap.add_argument(
        "--in-jsonl",
        default=str(data_dir() / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="Input JSONL containing stop contexts.",
    )
    ap.add_argument(
        "--out-tex",
        default=str(generated_dir() / "riboseq_pause_window_proxy.tex"),
        help="Output LaTeX fragment.",
    )
    ap.add_argument("--force", action="store_true", help="Force recomputation (ignore cached outputs).")
    args = ap.parse_args()

    in_path = Path(args.in_jsonl)
    out_tex = Path(args.out_tex)

    meta = {
        "analysis": "riboseq_pause_window_proxy",
        "k": int(args.k),
        "input": str(in_path).replace(str(root_dir()) + "/", ""),
    }

    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    # Cache short-circuit (optional)
    if out_tex.exists() and cache_meta_path(out_tex).exists() and not args.force:
        try:
            prev = json.loads(cache_meta_path(out_tex).read_text(encoding="utf-8"))
            if isinstance(prev, dict) and prev.get("analysis") == meta["analysis"] and prev.get("k") == meta["k"] and prev.get("input") == meta["input"]:
                print(f"[cache] hit: {out_tex}")
                return
        except Exception:
            pass

    pause_map = _pause_map()
    rows = _read_jsonl(in_path)
    rows = [r for r in rows if int(r.get("k", -1)) == int(args.k)]

    if not rows:
        raise SystemExit(f"No rows with k={args.k} in {in_path}")

    # Compute window pause proxies
    recs: list[dict[str, Any]] = []
    for r in rows:
        before_seq = str(r.get("before_seq_dna") or "")
        after_seq = str(r.get("after_seq_dna") or "")
        recs.append(
            {
                "stop_codon": str(r.get("stop_codon") or ""),
                "group_label": str(r.get("group_label") or ""),
                "u_before": float(r.get("before_mean_delta")) if r.get("before_mean_delta") is not None else float("nan"),
                "u_after": float(r.get("after_mean_delta")) if r.get("after_mean_delta") is not None else float("nan"),
                "diff": float(r.get("diff")) if r.get("diff") is not None else float("nan"),
                "gc_before": float(r.get("before_gc")) if r.get("before_gc") is not None else float("nan"),
                "gc_after": float(r.get("after_gc")) if r.get("after_gc") is not None else float("nan"),
                "pause_before": _window_pause_mean(before_seq, pause_map=pause_map),
                "pause_after": _window_pause_mean(after_seq, pause_map=pause_map),
            }
        )

    # Correlations (window-level)
    def _corr(x_key: str, y_key: str) -> dict[str, float]:
        xs = np.array([float(rr[x_key]) for rr in recs], dtype=float)
        ys = np.array([float(rr[y_key]) for rr in recs], dtype=float)
        m = ~np.isnan(xs) & ~np.isnan(ys)
        if int(np.sum(m)) < 10:
            return {"n": float(np.sum(m)), "rho": float("nan"), "p": float("nan")}
        rho, p = stats.spearmanr(xs[m], ys[m])
        return {"n": float(np.sum(m)), "rho": float(rho), "p": float(p)}

    corr_u_before = _corr("u_before", "pause_before")
    corr_u_after = _corr("u_after", "pause_before")
    corr_diff = _corr("diff", "pause_before")

    # GC-controlled partial correlations (within the same coding window)
    partial_u_before = _partial_spearman(
        [float(rr["u_before"]) for rr in recs],
        [float(rr["pause_before"]) for rr in recs],
        [[float(rr["gc_before"])] for rr in recs],
    )
    partial_diff = _partial_spearman(
        [float(rr["diff"]) for rr in recs],
        [float(rr["pause_before"]) for rr in recs],
        [[float(rr["gc_before"])] for rr in recs],
    )

    # Group-level comparisons (proxy quantile strata from the candidate builder)
    by_group: dict[str, list[float]] = defaultdict(list)
    for rr in recs:
        by_group[rr["group_label"]].append(float(rr["pause_before"]))

    def _compare(g_hi: str, g_lo: str) -> dict[str, float]:
        a = [x for x in by_group.get(g_hi, []) if not np.isnan(x)]
        b = [x for x in by_group.get(g_lo, []) if not np.isnan(x)]
        if len(a) < 10 or len(b) < 10:
            return {"n_hi": float(len(a)), "n_lo": float(len(b)), "d": float("nan"), "p": float("nan"), "mean_hi": float("nan"), "mean_lo": float("nan")}
        d = cohen_d(a, b)
        _, p = stats.ttest_ind(a, b, equal_var=False)
        return {
            "n_hi": float(len(a)),
            "n_lo": float(len(b)),
            "d": float(d) if d is not None else float("nan"),
            "p": float(p),
            "mean_hi": float(np.mean(a)),
            "mean_lo": float(np.mean(b)),
        }

    cmp_high_after = _compare("high_after", "low_after")
    cmp_matched_after = _compare("matched_after_high", "matched_after_low")
    cmp_high_diff = _compare("high_diff", "low_diff")

    # Summaries by stop codon (for context)
    stop_counts: dict[str, int] = defaultdict(int)
    for rr in recs:
        if rr["stop_codon"] in STOP_CODONS:
            stop_counts[rr["stop_codon"]] += 1

    summary = {
        "meta": meta,
        "n_records": int(len(recs)),
        "stop_counts": dict(stop_counts),
        "correlations": {
            "pause_before_vs_u_before": corr_u_before,
            "pause_before_vs_u_after": corr_u_after,
            "pause_before_vs_diff": corr_diff,
            "pause_before_vs_u_before_given_gc_before": partial_u_before,
            "pause_before_vs_diff_given_gc_before": partial_diff,
        },
        "group_comparisons": {
            "high_after_vs_low_after": cmp_high_after,
            "matched_after_high_vs_matched_after_low": cmp_matched_after,
            "high_diff_vs_low_diff": cmp_high_diff,
        },
        "group_stats": {g: _group_stats(xs) for g, xs in sorted(by_group.items())},
    }

    write_json_atomic(cache_dir() / "riboseq_pause_window_proxy.json", summary)

    # Emit LaTeX fragment
    n_total = len(recs)
    n_uaa = stop_counts.get("UAA", 0)
    n_uag = stop_counts.get("UAG", 0)
    n_uga = stop_counts.get("UGA", 0)

    lines = [
        "\\paragraph{Ribosome pausing: window-level proxy (codon-score average).}",
        "As a lightweight window-level check (offline; not read-level Ribo-seq), we averaged published codon pause scores across the $k$-codon window immediately upstream of terminal stops in the human RefSeq candidate set.",
        f"Dataset size: $n={n_total}$ (UAA={n_uaa}, UAG={n_uag}, UGA={n_uga}); $k={int(args.k)}$.",
        "",
        "\\textbf{Correlations (Spearman).}",
        f"Pause$_{{\\mathrm{{before}}}}$ vs $U_{{\\mathrm{{before}}}}$: $\\rho={_fmt(corr_u_before.get('rho'))}$ ($p={_p_fmt(corr_u_before.get('p'))}$).",
        f"Pause$_{{\\mathrm{{before}}}}$ vs $U_{{\\mathrm{{after}}}}$: $\\rho={_fmt(corr_u_after.get('rho'))}$ ($p={_p_fmt(corr_u_after.get('p'))}$).",
        f"Pause$_{{\\mathrm{{before}}}}$ vs $(U_{{\\mathrm{{after}}}}-U_{{\\mathrm{{before}}}})$: $\\rho={_fmt(corr_diff.get('rho'))}$ ($p={_p_fmt(corr_diff.get('p'))}$).",
        "",
        "\\textbf{GC-controlled (partial Spearman).}",
        f"Pause$_{{\\mathrm{{before}}}}$ vs $U_{{\\mathrm{{before}}}}\\mid\\mathrm{{GC}}_{{\\mathrm{{before}}}}$: $\\rho={_fmt(partial_u_before.get('rho'))}$ ($p={_p_fmt(partial_u_before.get('p'))}$).",
        f"Pause$_{{\\mathrm{{before}}}}$ vs $(U_{{\\mathrm{{after}}}}-U_{{\\mathrm{{before}}}})\\mid\\mathrm{{GC}}_{{\\mathrm{{before}}}}$: $\\rho={_fmt(partial_diff.get('rho'))}$ ($p={_p_fmt(partial_diff.get('p'))}$).",
        "",
        "\\textbf{Stratified comparisons (proxy quantiles from candidate sets).}",
        f"High-$U_{{\\mathrm{{after}}}}$ vs low-$U_{{\\mathrm{{after}}}}$: $d={_fmt(cmp_high_after.get('d'), nd=2)}$ ($p={_p_fmt(cmp_high_after.get('p'))}$), means {_fmt(cmp_high_after.get('mean_hi'))} vs {_fmt(cmp_high_after.get('mean_lo'))}.",
        f"Composition-matched high-$U_{{\\mathrm{{after}}}}$ vs low-$U_{{\\mathrm{{after}}}}$: $d={_fmt(cmp_matched_after.get('d'), nd=2)}$ ($p={_p_fmt(cmp_matched_after.get('p'))}$), means {_fmt(cmp_matched_after.get('mean_hi'))} vs {_fmt(cmp_matched_after.get('mean_lo'))}.",
        f"High-$(U_{{\\mathrm{{after}}}}-U_{{\\mathrm{{before}}}})$ vs low: $d={_fmt(cmp_high_diff.get('d'), nd=2)}$ ($p={_p_fmt(cmp_high_diff.get('p'))}$), means {_fmt(cmp_high_diff.get('mean_hi'))} vs {_fmt(cmp_high_diff.get('mean_lo'))}.",
        "",
        "\\textbf{Interpretation.} This proxy tests whether window-level pausing patterns are already implied by known slow/fast codons. It does not replace the planned read-level window pausing analysis from raw Ribo-seq coverage.",
    ]

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")


if __name__ == "__main__":
    main()
