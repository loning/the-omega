# -*- coding: utf-8 -*-
"""
ISA-H3C1: Centerwired control-flow features vs BAM pausing (cache-only).

Goal
----
Stress-test the Z128/ISA "control alphabet" interpretation quantitatively by
deriving simple gate/refinement features from the terminal-stop codon stream and
testing association with the read-level BAM pause index under strong controls.

We reuse:
  - ISA-P3 cache: data/_cache/riboseq_pause_bam_window_dinuc_null.json
    (pause-index per track + dinuc-null zΔU per transcript)
  - stop-context candidates with local sequences:
    data/refseq_hsapiens_mrna/stop_context_candidates.jsonl

Outputs:
  - sections/generated/centerwired_gate_features_vs_pausing.tex (+ meta)
  - data/_cache/centerwired_gate_features_vs_pausing.json (audit)

Notes
-----
We apply the same gate state machine as the centerwired decoder visualization:
  - boundary words are control records (forced to m=6)
  - 101001 enters refined mode; 100101 and 100001 exit/reset refined mode
  - in refined mode: m=10 if Δ in {55} else m=8

Here we compute these features on the local stop-context codon stream
(k_before=10, stop, k_after=10), and test whether "any refined-mode codon in the
after window" predicts pause index, including after residualizing pause index on
zΔU (dinucleotide-preserving null-of-null).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import BOUNDARY_WORDS, fold_codon
from stats_tools import cohen_d


SCRIPT_VERSION = 2
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return SCRIPT_DIR.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprint_file(path: Path) -> dict[str, object]:
    st = path.stat()
    return {"name": path.name, "bytes": int(st.st_size), "sha256": _sha256_file(path)}


def _fmt(x: float | None, *, nd: int = 2) -> str:
    if x is None:
        return "--"
    try:
        v = float(x)
    except Exception:
        return "--"
    if not np.isfinite(v):
        return "--"
    return f"{v:.{nd}f}"


def _p_fmt(p: float | None) -> str:
    if p is None:
        return "--"
    try:
        v = float(p)
    except Exception:
        return "--"
    if not np.isfinite(v):
        return "--"
    if v < 0.001:
        return "$<$0.001"
    return f"{v:.3f}"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ISA-H3C1: centerwired gate/refinement features vs BAM pausing (cache-only).")
    ap.add_argument(
        "--in-dinuc-json",
        default=str(cache_dir() / "riboseq_pause_bam_window_dinuc_null.json"),
        help="Input cache JSON from ISA-P3 (pause-index + zΔU).",
    )
    ap.add_argument(
        "--candidates-jsonl",
        default=str(root_dir() / "data" / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="Stop-context candidate windows JSONL (contains before/stop/after sequences).",
    )
    ap.add_argument("--delta-m10", default="55", help="Comma-separated Δ values that trigger m=10 in refined mode.")
    ap.add_argument("--min-n", type=int, default=10, help="Minimum group size per track for reporting a comparison.")
    ap.add_argument("--force", action="store_true", help="Force recomputation.")
    return ap.parse_args()


def _sanitize_codon_dna(b3: str) -> str:
    b3 = str(b3).upper().replace("U", "T")
    if len(b3) != 3:
        return "AAA"
    return "".join(ch if ch in "ACGT" else "A" for ch in b3)


@dataclass(frozen=True)
class CenterwiredFeatures:
    k_before: int
    k_after: int
    stop_index: int
    refined_after_count: int
    m10_after_count: int
    gate_counts_total: dict[str, int]
    gate_counts_after: dict[str, int]


def _centerwired_features_from_context(
    *,
    before_seq_dna: str,
    stop_codon_dna: str,
    after_seq_dna: str,
    delta_to_m10: set[int],
) -> CenterwiredFeatures:
    before = str(before_seq_dna or "").upper()
    after = str(after_seq_dna or "").upper()
    stop = str(stop_codon_dna or "").upper()
    seq = before + stop + after
    L = (len(seq) // 3) * 3
    seq = seq[:L]
    codons = [_sanitize_codon_dna(seq[i : i + 3]) for i in range(0, len(seq), 3)]
    k_before = len(before) // 3
    k_after = len(after) // 3
    stop_index = int(k_before)

    refined = False
    m_eff: list[int] = []
    gate_counts_total = {w: 0 for w in sorted(BOUNDARY_WORDS)}
    gate_counts_after = {w: 0 for w in sorted(BOUNDARY_WORDS)}

    for i, codon_dna in enumerate(codons):
        f = fold_codon(codon_dna.replace("T", "U"), MU_STAR)
        w = str(f.w)
        delta = int(f.delta)
        if w in gate_counts_total:
            gate_counts_total[w] += 1
            if i > stop_index:
                gate_counts_after[w] += 1

        if w == "101001":
            refined = True
            m_eff.append(6)
            continue
        if w in ("100101", "100001"):
            refined = False
            m_eff.append(6)
            continue
        if refined:
            m_eff.append(10 if delta in delta_to_m10 else 8)
        else:
            m_eff.append(6)

    # After window: k codons immediately after the stop (exclude stop codon itself).
    after_idx = [i for i in range(stop_index + 1, min(stop_index + 1 + int(k_after), len(m_eff)))]
    refined_after_count = sum(1 for i in after_idx if m_eff[i] in (8, 10))
    m10_after_count = sum(1 for i in after_idx if m_eff[i] == 10)

    return CenterwiredFeatures(
        k_before=int(k_before),
        k_after=int(k_after),
        stop_index=int(stop_index),
        refined_after_count=int(refined_after_count),
        m10_after_count=int(m10_after_count),
        gate_counts_total=gate_counts_total,
        gate_counts_after=gate_counts_after,
    )


def _residualize_y_on_x(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    X = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def _compare_groups(xs: list[float], ys: list[float], *, min_n: int) -> dict[str, Any]:
    out: dict[str, Any] = {"n1": int(len(xs)), "n2": int(len(ys))}
    if len(xs) < int(min_n) or len(ys) < int(min_n):
        out["insufficient_data"] = True
        return out
    d = cohen_d(xs, ys)
    out["cohens_d"] = float(d) if d is not None and math.isfinite(float(d)) else None
    try:
        t = stats.ttest_ind(xs, ys, equal_var=False)
        out["t"] = float(t.statistic)
        out["p"] = float(t.pvalue)
    except Exception:
        out["t"] = None
        out["p"] = None
    out["mean1"] = float(statistics.mean(xs)) if xs else None
    out["mean2"] = float(statistics.mean(ys)) if ys else None
    return out


def _random_effects_meta(
    track_results: list[dict[str, Any]],
    comparison_key: str,
    *,
    min_n: int,
) -> dict[str, Any]:
    """
    Lightweight DerSimonian-Laird random-effects meta-analysis on Cohen's d.
    Uses the same SE approximation as other pipeline modules.
    """
    effects: list[tuple[float, float, int, int, str]] = []  # (d, se, n1, n2, track_id)
    for tr in track_results:
        comp = (tr.get("pairwise_comparisons") or {}).get(comparison_key)
        if not isinstance(comp, dict):
            continue
        n1 = int(comp.get("n1") or 0)
        n2 = int(comp.get("n2") or 0)
        d = comp.get("cohens_d")
        if d is None:
            continue
        try:
            d0 = float(d)
        except Exception:
            continue
        if not math.isfinite(d0):
            continue
        if n1 < int(min_n) or n2 < int(min_n):
            continue
        se = math.sqrt((n1 + n2) / (n1 * n2) + d0**2 / (2 * (n1 + n2)))
        effects.append((d0, float(se), n1, n2, str(tr.get("track_id") or "")))

    if len(effects) < 2:
        return {"n_studies": len(effects), "insufficient_data": True}

    weights = [1.0 / (se**2) for (_d, se, _n1, _n2, _tid) in effects]
    total_w = float(sum(weights))
    fe = float(sum(w * d for (d, _se, _n1, _n2, _tid), w in zip(effects, weights)) / total_w)

    Q = float(sum(w * (d - fe) ** 2 for (d, _se, _n1, _n2, _tid), w in zip(effects, weights)))
    df = int(len(effects) - 1)
    c = float(total_w - sum(w**2 for w in weights) / total_w) if total_w > 0 else 0.0
    tau2 = max(0.0, (Q - float(df)) / c) if c > 0 else 0.0

    re_w = [1.0 / (se**2 + tau2) for (_d, se, _n1, _n2, _tid) in effects]
    re_total = float(sum(re_w))
    re = float(sum(w * d for (d, _se, _n1, _n2, _tid), w in zip(effects, re_w)) / re_total)
    re_se = float(math.sqrt(1.0 / re_total))
    ci_low = re - 1.96 * re_se
    ci_high = re + 1.96 * re_se
    I2 = max(0.0, (Q - float(df)) / Q) if Q > 0 else 0.0

    return {
        "n_studies": int(len(effects)),
        "comparison": str(comparison_key),
        "fixed_effect": fe,
        "random_effect": re,
        "random_effect_se": re_se,
        "ci_95_low": float(ci_low),
        "ci_95_high": float(ci_high),
        "tau2": float(tau2),
        "Q": float(Q),
        "I2": float(I2),
        "I2_percent": float(I2 * 100.0),
        "per_track": [
            {"track_id": tid, "effect": d, "se": se, "n1": n1, "n2": n2} for (d, se, n1, n2, tid) in effects
        ],
    }


def _load_candidate_contexts(path: Path) -> dict[str, dict[str, Any]]:
    """
    Map record_id -> {before_seq_dna, stop_codon_dna, after_seq_dna, k}.
    Deduplicate by taking the first occurrence per record_id (k=10 expected).
    """
    out: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            rid = str(obj.get("record_id") or "").strip()
            if not rid or rid in out:
                continue
            out[rid] = {
                "k": int(obj.get("k") or 0),
                "before_seq_dna": str(obj.get("before_seq_dna") or ""),
                "stop_codon_dna": str(obj.get("stop_codon_dna") or ""),
                "after_seq_dna": str(obj.get("after_seq_dna") or ""),
            }
    return out


def main() -> None:
    args = parse_args()

    in_dinuc = Path(str(args.in_dinuc_json))
    if not in_dinuc.is_absolute():
        in_dinuc = root_dir() / in_dinuc
    if not in_dinuc.exists():
        raise SystemExit(f"Missing ISA-P3 cache: {in_dinuc}")

    cand = Path(str(args.candidates_jsonl))
    if not cand.is_absolute():
        cand = root_dir() / cand
    if not cand.exists():
        raise SystemExit(f"Missing candidates JSONL: {cand}")

    delta_to_m10: set[int] = set()
    for p in str(args.delta_m10).split(","):
        p = p.strip()
        if not p:
            continue
        delta_to_m10.add(int(p))
    if not delta_to_m10:
        delta_to_m10 = {55}

    out_tex = generated_dir() / "centerwired_gate_features_vs_pausing.tex"
    out_json = cache_dir() / "centerwired_gate_features_vs_pausing.json"

    cache_key: dict[str, Any] = {
        "analysis": "centerwired_gate_features_vs_pausing",
        "script_version": int(SCRIPT_VERSION),
        "delta_to_m10": sorted(int(x) for x in delta_to_m10),
        "min_n": int(args.min_n),
        "inputs": {
            "dinuc": _fingerprint_file(in_dinuc),
            "candidates": _fingerprint_file(cand),
        },
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        return

    dinuc_obj = json.loads(in_dinuc.read_text(encoding="utf-8"))
    tracks = dinuc_obj.get("tracks") if isinstance(dinuc_obj, dict) else None
    z_by_rid = dinuc_obj.get("z_by_rid") if isinstance(dinuc_obj, dict) else None
    if not isinstance(tracks, list) or not isinstance(z_by_rid, dict):
        raise SystemExit(f"Malformed dinuc cache: {in_dinuc}")

    contexts = _load_candidate_contexts(cand)

    # Precompute features per record_id (shared across tracks).
    rid_to_feat: dict[str, CenterwiredFeatures] = {}
    for rid, c0 in contexts.items():
        try:
            rid_to_feat[rid] = _centerwired_features_from_context(
                before_seq_dna=str(c0.get("before_seq_dna") or ""),
                stop_codon_dna=str(c0.get("stop_codon_dna") or ""),
                after_seq_dna=str(c0.get("after_seq_dna") or ""),
                delta_to_m10=delta_to_m10,
            )
        except Exception:
            continue

    track_results: list[dict[str, Any]] = []
    for tr in tracks:
        if not isinstance(tr, dict):
            continue
        track_id = str(tr.get("track_id") or "").strip() or "unknown"
        rows = tr.get("rows")
        if not isinstance(rows, list) or not rows:
            continue

        ys_raw: list[float] = []
        zs: list[float] = []
        has_refined: list[bool] = []
        has_m10: list[bool] = []

        for r in rows:
            if not isinstance(r, dict):
                continue
            rid = str(r.get("record_id") or "").strip()
            if not rid:
                continue
            pi = r.get("pause_index")
            try:
                y = float(pi)
            except Exception:
                continue
            if not np.isfinite(y):
                continue
            z0 = z_by_rid.get(rid)
            if not isinstance(z0, dict):
                continue
            try:
                z = float(z0.get("z_diff"))
            except Exception:
                continue
            if not np.isfinite(z):
                continue

            feat = rid_to_feat.get(rid)
            if feat is None:
                continue

            ys_raw.append(float(y))
            zs.append(float(z))
            has_refined.append(bool(feat.refined_after_count > 0))
            has_m10.append(bool(feat.m10_after_count > 0))

        if len(ys_raw) < 20:
            track_results.append({"species": track_id, "track_id": track_id, "n": int(len(ys_raw)), "pairwise_comparisons": {}})
            continue

        y_arr = np.array(ys_raw, dtype=float)
        z_arr = np.array(zs, dtype=float)
        y_resid = _residualize_y_on_x(y_arr, z_arr)

        # Group splits (primary: any refined-after vs none).
        grp_ref = [float(v) for v, flag in zip(y_arr.tolist(), has_refined) if flag]
        grp_none = [float(v) for v, flag in zip(y_arr.tolist(), has_refined) if not flag]
        grp_ref_r = [float(v) for v, flag in zip(y_resid.tolist(), has_refined) if flag]
        grp_none_r = [float(v) for v, flag in zip(y_resid.tolist(), has_refined) if not flag]

        comp_raw = _compare_groups(grp_ref, grp_none, min_n=int(args.min_n))
        comp_resid = _compare_groups(grp_ref_r, grp_none_r, min_n=int(args.min_n))

        # Secondary: m=10 hits (rarer).
        grp_m10 = [float(v) for v, flag in zip(y_arr.tolist(), has_m10) if flag]
        grp_nom10 = [float(v) for v, flag in zip(y_arr.tolist(), has_m10) if not flag]
        grp_m10_r = [float(v) for v, flag in zip(y_resid.tolist(), has_m10) if flag]
        grp_nom10_r = [float(v) for v, flag in zip(y_resid.tolist(), has_m10) if not flag]
        comp_m10_raw = _compare_groups(grp_m10, grp_nom10, min_n=int(args.min_n))
        comp_m10_resid = _compare_groups(grp_m10_r, grp_nom10_r, min_n=int(args.min_n))

        # Diagnostic: correlation between the feature and zΔU (confounding check).
        feat_ref_arr = np.array([1.0 if f else 0.0 for f in has_refined], dtype=float)
        try:
            rho_ref_z, p_ref_z = stats.spearmanr(feat_ref_arr, z_arr)
        except Exception:
            rho_ref_z, p_ref_z = (float("nan"), float("nan"))

        track_results.append(
            {
                "species": track_id,
                "track_id": track_id,
                "n": int(len(y_arr)),
                "n_refined_after": int(sum(1 for f in has_refined if f)),
                "n_m10_after": int(sum(1 for f in has_m10 if f)),
                "spearman_refined_after_vs_zdiff": {"rho": float(rho_ref_z), "p": float(p_ref_z)},
                "pairwise_comparisons": {
                    "refined_after_vs_none_raw": comp_raw,
                    "refined_after_vs_none_resid_on_zdiff": comp_resid,
                    "m10_after_vs_none_raw": comp_m10_raw,
                    "m10_after_vs_none_resid_on_zdiff": comp_m10_resid,
                },
            }
        )

    meta = {
        "refined_after_vs_none_raw": _random_effects_meta(track_results, "refined_after_vs_none_raw", min_n=int(args.min_n)),
        "refined_after_vs_none_resid_on_zdiff": _random_effects_meta(
            track_results, "refined_after_vs_none_resid_on_zdiff", min_n=int(args.min_n)
        ),
        "m10_after_vs_none_raw": _random_effects_meta(track_results, "m10_after_vs_none_raw", min_n=int(args.min_n)),
        "m10_after_vs_none_resid_on_zdiff": _random_effects_meta(track_results, "m10_after_vs_none_resid_on_zdiff", min_n=int(args.min_n)),
    }

    lines: list[str] = []
    lines.append(r"\paragraph{ISA-H3C1: Centerwired control-flow features vs BAM pausing.}")
    lines.append(
        r"We derive simple control-flow features by running the ``centerwired gates'' state machine on the local terminal-stop codon stream"
        r" (10 codons before, stop, 10 codons after; $\mu^\ast$)."
        r" The primary feature is whether any downstream codon is labeled as refined mode ($m\in\{8,10\}$) under the gate rules."
        r" We report within-track effect sizes comparing refined-after vs none (Cohen's $d$, Welch $t$-test)"
        + rf" with a minimum group size threshold $n\geq{int(args.min_n)}$,"
        r" and additionally report results after residualizing pause index on the dinucleotide-null $z\Delta U$ (ISA-P3)."
    )
    lines.append("")
    lines.append(r"\begin{center}\small")
    lines.append(r"\begin{tabular}{lrrrrrrrr}\toprule")
    lines.append(r"Track & $n$ & $n_{ref}$ & $d$ & $p$ & $d_{res}$ & $p_{res}$ & $\rho(ref,z)$ & $p$ \\")
    lines.append(r"\midrule")
    for tr in track_results:
        comp = tr.get("pairwise_comparisons", {}).get("refined_after_vs_none_raw") or {}
        comp_r = tr.get("pairwise_comparisons", {}).get("refined_after_vs_none_resid_on_zdiff") or {}
        rho = (tr.get("spearman_refined_after_vs_zdiff") or {}).get("rho")
        pr = (tr.get("spearman_refined_after_vs_zdiff") or {}).get("p")
        lines.append(
            rf"\path{{{tr.get('track_id','')}}} & {int(tr.get('n',0))} & {int(tr.get('n_refined_after',0))} & "
            rf"{_fmt(comp.get('cohens_d'))} & {_p_fmt(comp.get('p'))} & "
            rf"{_fmt(comp_r.get('cohens_d'))} & {_p_fmt(comp_r.get('p'))} & "
            rf"{_fmt(rho, nd=2)} & {_p_fmt(pr)} \\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")

    for key, label in [
        ("refined_after_vs_none_raw", r"refined-after vs none (raw)"),
        ("refined_after_vs_none_resid_on_zdiff", r"refined-after vs none (residualized on $z\Delta U$)"),
    ]:
        mr = meta.get(key) or {}
        if mr.get("insufficient_data"):
            lines.append(rf"Meta-analysis ({label}): insufficient tracks.")
        else:
            lines.append(
                rf"Meta-analysis ({label}): "
                + rf"$d={_fmt(mr.get('random_effect'), nd=2)}$ "
                + rf"[{_fmt(mr.get('ci_95_low'), nd=2)}, {_fmt(mr.get('ci_95_high'), nd=2)}], "
                + rf"$I^2={_fmt(mr.get('I2_percent'), nd=1)}\%$ (n={int(mr.get('n_studies',0))})."
            )

    write_text_atomic(out_tex, "\n".join(lines).strip() + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    write_json_atomic(out_json, {"meta": cache_meta, "tracks": track_results, "meta_analysis": meta})


if __name__ == "__main__":
    main()
