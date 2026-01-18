# -*- coding: utf-8 -*-
"""
ISA-P4: "Three boundary gates" audit on stop+2nt anchors (m=10 -> m=6).

We reuse the read-level pause-index results already computed by the BAM pausing
pipeline (ISA-P2/ISA-P3 cached JSON) and stratify the boundary-anchor subset by
which m=6 boundary word is hit:
  u6 ∈ {100001, 100101, 101001}.

Primary endpoint:
  Compare pause-index between u6=100101 vs other boundary words pooled.

Inputs (produced by ISA-P2/ISA-P3 scripts):
  - data/_cache/riboseq_pause_bam_window_isa.json
  - (optional) data/_cache/riboseq_pause_bam_window_dinuc_null.json

Outputs:
  - sections/generated/riboseq_pause_bam_window_gate_words.tex (+ meta)
  - data/_cache/riboseq_pause_bam_window_gate_words.json (audit)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import fold_m, is_boundary_word
from stats_tools import cohen_d


SCRIPT_VERSION = 1
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


def _file_fingerprint(path: Path | None) -> dict[str, object]:
    if path is None:
        return {"missing": True}
    if not path.exists():
        return {"name": str(path), "missing": True}
    st = path.stat()
    return {
        "name": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


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


def _normalize_rna(seq: str) -> str:
    return str(seq).strip().upper().replace("T", "U")


def _kmer_bits(seq: str) -> str:
    return "".join(MU_STAR[b] for b in seq)


@dataclass(frozen=True)
class Anchor10to6:
    u6: str
    is_boundary: bool


def stop_plus2_anchor_u6(stop_codon_rna: str, plus4_nt: str, after_nt6: str) -> Anchor10to6 | None:
    stop = _normalize_rna(stop_codon_rna)
    if len(stop) != 3 or any(b not in MU_STAR for b in stop):
        return None
    plus4 = _normalize_rna(plus4_nt)
    nt6 = _normalize_rna(after_nt6)
    plus5 = nt6[1] if len(nt6) >= 2 else ""
    if plus4 not in MU_STAR or plus5 not in MU_STAR:
        return None
    motif5 = f"{stop}{plus4}{plus5}"
    n10 = int(_kmer_bits(motif5), 2)
    w10 = fold_m(n10, 10)
    u6 = str(w10[:6])
    return Anchor10to6(u6=u6, is_boundary=bool(is_boundary_word(u6)))


def _compare(xs_a: list[float], xs_b: list[float], *, min_n: int) -> dict[str, float]:
    a = [float(v) for v in xs_a if np.isfinite(v)]
    b = [float(v) for v in xs_b if np.isfinite(v)]
    if len(a) < int(min_n) or len(b) < int(min_n):
        return {"n1": float(len(a)), "n2": float(len(b)), "cohens_d": float("nan"), "p": float("nan")}
    d = cohen_d(a, b)
    _, p = stats.ttest_ind(a, b, equal_var=False)
    return {
        "n1": float(len(a)),
        "n2": float(len(b)),
        "cohens_d": float(d) if d is not None else float("nan"),
        "p": float(p),
    }


def _random_effects_meta(
    results: list[dict[str, Any]],
    comparison_key: str,
    *,
    min_n: int,
) -> dict[str, Any]:
    """
    Lightweight DerSimonian-Laird random-effects meta-analysis.

    We do not reuse exp_cross_species_stop_context.random_effects_meta here because
    this gate-word stratification is often underpowered per track; we expose the
    min_n threshold explicitly to keep the audit honest.
    """
    effects: list[tuple[float, float, int, int, str]] = []  # (d, se, n1, n2, track_id)
    for r in results:
        comp = (r.get("pairwise_comparisons") or {}).get(comparison_key)
        if not isinstance(comp, dict):
            continue
        try:
            n1 = int(comp.get("n1") or 0)
            n2 = int(comp.get("n2") or 0)
            d = float(comp.get("cohens_d"))
        except Exception:
            continue
        if n1 < int(min_n) or n2 < int(min_n) or (not np.isfinite(d)):
            continue
        se = math.sqrt((n1 + n2) / (n1 * n2) + (d**2) / (2 * (n1 + n2)))
        effects.append((d, se, n1, n2, str(r.get("track_id") or r.get("species") or "")))

    if len(effects) < 2:
        return {"n_studies": len(effects), "insufficient_data": True}

    weights = [1.0 / (se**2) for (_, se, _, _, _) in effects]
    total_w = float(sum(weights))
    fe = float(sum(w * d for (d, se, _, _, _), w in zip(effects, weights)) / total_w)

    Q = float(sum(w * (d - fe) ** 2 for (d, se, _, _, _), w in zip(effects, weights)))
    df = len(effects) - 1
    c = total_w - float(sum(w**2 for w in weights) / total_w)
    tau2 = max(0.0, (Q - df) / c) if c > 0 else 0.0

    re_weights = [1.0 / (se**2 + tau2) for (_, se, _, _, _) in effects]
    re_total = float(sum(re_weights))
    re = float(sum(w * d for (d, se, _, _, _), w in zip(effects, re_weights)) / re_total)
    re_se = math.sqrt(1.0 / re_total)

    ci_low = re - 1.96 * re_se
    ci_high = re + 1.96 * re_se
    I2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0

    return {
        "n_studies": len(effects),
        "comparison": comparison_key,
        "fixed_effect": fe,
        "random_effect": re,
        "random_effect_se": re_se,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "tau2": tau2,
        "Q": Q,
        "I2": I2,
        "I2_percent": I2 * 100.0,
        "per_track": [{"track_id": tid, "effect": d, "se": se, "n1": n1, "n2": n2} for (d, se, n1, n2, tid) in effects],
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ISA-P4: Gate-word stratification on stop+2nt boundary anchors (reuse cached BAM pausing results).")
    ap.add_argument("--min-n", type=int, default=5, help="Min group size for within-track comparisons and meta-analysis.")
    ap.add_argument(
        "--in-isa-json",
        default=str(cache_dir() / "riboseq_pause_bam_window_isa.json"),
        help="Input cache JSON from ISA-P2 (BAM pausing + boundary-anchor split).",
    )
    ap.add_argument(
        "--in-dinuc-json",
        default=str(cache_dir() / "riboseq_pause_bam_window_dinuc_null.json"),
        help="Optional input cache JSON from ISA-P3 (contains zΔU audit; currently used only for provenance).",
    )
    ap.add_argument("--force", action="store_true", help="Force recomputation.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    in_isa = Path(str(args.in_isa_json))
    if not in_isa.is_absolute():
        in_isa = root_dir() / in_isa
    in_dinuc = Path(str(args.in_dinuc_json)) if str(args.in_dinuc_json).strip() else None
    if in_dinuc is not None and not in_dinuc.is_absolute():
        in_dinuc = root_dir() / in_dinuc

    if not in_isa.exists():
        raise SystemExit(
            "Missing input cache. Run ISA-P2 first:\n"
            "  conda run -n omega-ribo python scripts/exp_riboseq_pause_bam_window_isa.py\n"
            f"Expected: {in_isa}"
        )

    out_tex = generated_dir() / "riboseq_pause_bam_window_gate_words.tex"
    out_json = cache_dir() / "riboseq_pause_bam_window_gate_words.json"

    cache_key: dict[str, Any] = {
        "analysis": "riboseq_pause_bam_window_gate_words",
        "version": int(SCRIPT_VERSION),
        "min_n": int(args.min_n),
        "inputs": {
            "isa": _file_fingerprint(in_isa),
            "dinuc": _file_fingerprint(in_dinuc),
        },
    }
    cache_key["cache_key"] = cache_key_digest(cache_key)
    meta = cache_key

    if (not args.force) and cache_hit(out_tex, expected_meta=meta):
        return

    isa = json.loads(in_isa.read_text(encoding="utf-8"))
    tracks = isa.get("tracks") if isinstance(isa, dict) else None
    if not isinstance(tracks, list) or not tracks:
        raise SystemExit(f"Malformed ISA cache: {in_isa}")

    results: list[dict[str, Any]] = []
    for tr in tracks:
        if not isinstance(tr, dict):
            continue
        track_id = str(tr.get("track_id") or "").strip() or "unknown"
        rows = tr.get("rows")
        if not isinstance(rows, list):
            continue

        gate_to_pause: dict[str, list[float]] = {"100001": [], "100101": [], "101001": []}
        for r in rows:
            if not isinstance(r, dict):
                continue
            pi = r.get("pause_index")
            try:
                pi_f = float(pi)
            except Exception:
                continue
            if not np.isfinite(pi_f):
                continue
            a = stop_plus2_anchor_u6(r.get("stop_codon", ""), r.get("plus4_nt", ""), r.get("after_nt6", ""))
            if not a or (not a.is_boundary):
                continue
            if a.u6 in gate_to_pause:
                gate_to_pause[a.u6].append(pi_f)

        n_100001 = len(gate_to_pause["100001"])
        n_100101 = len(gate_to_pause["100101"])
        n_101001 = len(gate_to_pause["101001"])
        n_bdry = n_100001 + n_100101 + n_101001

        other = [*gate_to_pause["100001"], *gate_to_pause["101001"]]
        comp = _compare(gate_to_pause["100101"], other, min_n=int(args.min_n))

        results.append(
            {
                "species": track_id,
                "track_id": track_id,
                "n_bdry": int(n_bdry),
                "gate_counts": {"100001": int(n_100001), "100101": int(n_100101), "101001": int(n_101001)},
                "pairwise_comparisons": {"gate_100101_vs_other_boundary": comp},
            }
        )

    meta_re = _random_effects_meta(results, "gate_100101_vs_other_boundary", min_n=int(args.min_n))

    lines: list[str] = []
    lines.append(r"\paragraph{ISA-P4: Stop+2nt boundary anchors stratified by the three $m=6$ boundary words.}")
    lines.append(
        r"We reuse the cached BAM pause-index results and stratify the boundary-anchor subset by which boundary word is hit"
        r" ($u_6\in\{\texttt{100001},\texttt{100101},\texttt{101001}\}$)."
    )
    lines.append(
        r"We report the within-track effect size comparing \texttt{100101} vs the other two boundary words pooled"
        r" (Cohen's $d$, Welch $t$-test), and a random-effects meta-analysis across tracks."
        + rf" (threshold: $n\geq{int(args.min_n)}$ per group)."
    )
    lines.append("")
    lines.append(r"\begin{center}\small")
    lines.append(r"\begin{tabular}{lrrrrrr}\toprule")
    lines.append(r"Track & $n_{bdry}$ & $n_{100001}$ & $n_{100101}$ & $n_{101001}$ & $d$ & $p$ \\")
    lines.append(r"\midrule")
    for r in results:
        comp = r["pairwise_comparisons"]["gate_100101_vs_other_boundary"]
        lines.append(
            rf"\path{{{r['track_id']}}} & {r['n_bdry']} & {r['gate_counts']['100001']} & {r['gate_counts']['100101']} & {r['gate_counts']['101001']} & "
            rf"{_fmt(comp.get('cohens_d'))} & {_p_fmt(comp.get('p'))} \\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    if meta_re.get("insufficient_data"):
        lines.append(rf"Meta-analysis: insufficient tracks with $n\geq{int(args.min_n)}$ per group.")
    else:
        lines.append(
            r"Meta-analysis (random-effects) on $d$ (\texttt{100101} vs other boundary): "
            + rf"$d={_fmt(meta_re['random_effect'], nd=2)}$ [{_fmt(meta_re['ci_95_low'], nd=2)}, {_fmt(meta_re['ci_95_high'], nd=2)}], "
            + rf"$I^2={_fmt(meta_re['I2_percent'], nd=1)}\%$ (n={int(meta_re['n_studies'])})."
        )

    write_text_atomic(out_tex, "\n".join(lines).strip() + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    write_json_atomic(out_json, {"meta": meta, "tracks": results, "meta_analysis": meta_re})


if __name__ == "__main__":
    main()
