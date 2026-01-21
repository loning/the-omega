# -*- coding: utf-8 -*-
"""
Cluster/robustness summary for strong numeric-match searches (SM-Hilbert).

This script reads a strong-search report JSON produced by:
  exp_hilbert_sm_numeric_match_strong_search.py

and generates compact, auditable LaTeX fragments that summarize:
  - top-K candidates (leaderboard entries)
  - cluster statistics by GI signature (type/full) to assess non-uniqueness

Outputs (LaTeX fragments; English-only output):
  - sections/generated/sm_hilbert_numeric_match_strong_topk_<tag>_rows.tex
  - sections/generated/sm_hilbert_numeric_match_strong_clusters_<tag>_rows.tex
  - sections/generated/sm_hilbert_numeric_match_strong_clusters_<tag>_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _short(s: Optional[str], n: int = 10) -> str:
    t = str(s or "")
    if len(t) <= int(n):
        return t
    return t[: int(n)] + "…"


def _tag_from_report_path(p: Path) -> str:
    name = p.name
    stem = name
    if stem.endswith(".json"):
        stem = stem[: -len(".json")]
    prefix = "sm_hilbert_numeric_match_strong_search_report_"
    if stem.startswith(prefix):
        tag = stem[len(prefix) :]
        return tag or "default"
    return stem


def _get_nested(d: Dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


@dataclass(frozen=True)
class CandRow:
    score: float
    ew_score: float
    u1_score: float
    sig_type: str
    sig_full: str
    gi_level: str
    u1_candidate: str
    u1_scale: float
    pred0: float
    predz: float
    e_low: float
    e_z: float
    n_edges_2d_coarse: int
    n_edges_3d_coarse: int
    n_changed: int
    n_switches: int
    max_m: int


def _extract_candidate(c: Dict[str, Any]) -> Optional[CandRow]:
    try:
        score = float(c.get("score", float("nan")))
        ew_score = float(c.get("ew_score", float("nan")))
        u1_score = float(c.get("u1_score", float("nan")))
        gi_level = str(_get_nested(c, "gi", "level") or "")
        sig_type = str(_get_nested(c, "gi", "sig_type_2d") or "")
        sig_full = str(_get_nested(c, "gi", "sig_full_2d") or "")

        jb = _get_nested(c, "u1", "joint_best") or {}
        u1_cand = str(jb.get("candidate") or "")
        u1_scale = float(jb.get("scale", float("nan")))

        # Prefer per-graph coarse stats (stable schema), fallback to pred*_by_group.
        best2 = _get_nested(c, "u1", "per_graph", "graph2d", "coarse", "best_joint") or {}
        best3 = _get_nested(c, "u1", "per_graph", "graph3d", "coarse", "best_joint") or {}
        pred0 = float(best2.get("pred0", jb.get("pred0", float("nan"))))
        predz = float(best2.get("predz", jb.get("predz", float("nan"))))
        e_low = float(best2.get("e_low", float("nan")))
        e_z = float(best2.get("e_z", float("nan")))
        n2 = int(_get_nested(c, "u1", "per_graph", "graph2d", "coarse", "n_edges") or 0)
        n3 = int(_get_nested(c, "u1", "per_graph", "graph3d", "coarse", "n_edges") or 0)

        sst = c.get("schedule_stats_klo_khi") or {}
        n_changed = int(sst.get("n_changed", 0))
        n_switches = int(sst.get("n_switches", 0))
        max_m = int(sst.get("max_m", 0))

        if not math.isfinite(score):
            return None
        return CandRow(
            score=score,
            ew_score=ew_score,
            u1_score=u1_score,
            sig_type=sig_type,
            sig_full=sig_full if sig_full != "None" else "",
            gi_level=gi_level,
            u1_candidate=u1_cand,
            u1_scale=u1_scale,
            pred0=pred0,
            predz=predz,
            e_low=e_low,
            e_z=e_z,
            n_edges_2d_coarse=n2,
            n_edges_3d_coarse=n3,
            n_changed=n_changed,
            n_switches=n_switches,
            max_m=max_m,
        )
    except Exception:
        return None


def _sort_key(r: CandRow) -> Tuple[float, float, float, int]:
    return (float(r.score), float(r.u1_score), float(r.ew_score), int(r.n_changed))


def _cluster_key(r: CandRow) -> Tuple[str, str, str]:
    # Cluster by GI level + type signature, and include full signature if present.
    # (If gi_level=type, sig_full will be empty.)
    return (str(r.gi_level), str(r.sig_type), str(r.sig_full))


def _latex_tt(s: str) -> str:
    # Keep it simple: wrap in \texttt{} and replace underscores.
    return r"\texttt{" + str(s).replace("_", r"\_") + "}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=str, required=True, help="Path to sm_hilbert_numeric_match_strong_search_report*.json")
    ap.add_argument("--top-k", type=int, default=20, help="How many leaderboard candidates to list.")
    ap.add_argument("--cluster-k", type=int, default=12, help="How many clusters to list.")
    args = ap.parse_args()

    report_path = Path(str(args.report))
    rep = _read_json(report_path)
    tag = _tag_from_report_path(report_path)

    # Prefer schedule_leaderboard when present; else use best only.
    raw = rep.get("schedule_leaderboard")
    if not isinstance(raw, list):
        raw = [rep.get("best")] if isinstance(rep.get("best"), dict) else []

    rows_all: List[CandRow] = []
    for x in raw:
        if not isinstance(x, dict):
            continue
        r = _extract_candidate(x)
        if r is not None:
            rows_all.append(r)
    rows_all.sort(key=_sort_key)

    top_k = max(1, int(args.top_k))
    top_rows = rows_all[:top_k]

    # Cluster stats.
    clusters: Dict[Tuple[str, str, str], List[CandRow]] = {}
    for r in rows_all:
        clusters.setdefault(_cluster_key(r), []).append(r)
    # Sort clusters by best candidate.
    cluster_items: List[Tuple[Tuple[str, str, str], List[CandRow]]] = list(clusters.items())
    cluster_items.sort(key=lambda kv: _sort_key(sorted(kv[1], key=_sort_key)[0]))

    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Top-K table fragment.
    tex_top: List[str] = []
    tex_top.append(r"\toprule")
    tex_top.append(
        r"rank & GI & sig & score & $e_{\mathrm{EW}}$ & $e_{U(1)}$ & pred$_0$ & pred$_Z$ & $e_{\mathrm{low}}$ & $e_Z$ & $n_{\times m}^{(2D)}$ & $n_{\times m}^{(3D)}$ \\"
    )
    tex_top.append(r"\midrule")
    for i, r in enumerate(top_rows, start=1):
        sig = _short(r.sig_type or "-", 10) if r.gi_level != "off" else "-"
        gi = _latex_tt(r.gi_level or "-")
        tex_top.append(
            " & ".join(
                [
                    str(i),
                    gi,
                    _latex_tt(sig),
                    _fmt(r.score, 6),
                    _fmt(r.ew_score, 6),
                    _fmt(r.u1_score, 6),
                    _fmt(r.pred0, 6),
                    _fmt(r.predz, 6),
                    _fmt(r.e_low, 6),
                    _fmt(r.e_z, 6),
                    str(int(r.n_edges_2d_coarse)),
                    str(int(r.n_edges_3d_coarse)),
                ]
            )
            + r" \\"
        )
    tex_top.append(r"\bottomrule")
    out_top = out_dir / f"sm_hilbert_numeric_match_strong_topk_{tag}_rows.tex"
    write_lines(out_top, tex_top)

    # Cluster table fragment.
    tex_cl: List[str] = []
    tex_cl.append(r"\toprule")
    tex_cl.append(r"rank & GI & sig & $n$ & best score & best $e_{U(1)}$ & best pred$_0$ & best pred$_Z$ & best cand & scale \\")
    tex_cl.append(r"\midrule")
    for i, (ck, members) in enumerate(cluster_items[: max(1, int(args.cluster_k))], start=1):
        gi_level, sig_type, sig_full = ck
        mem_sorted = sorted(members, key=_sort_key)
        best = mem_sorted[0]
        sig = _short(sig_type or "-", 10) if gi_level != "off" else "-"
        tex_cl.append(
            " & ".join(
                [
                    str(i),
                    _latex_tt(gi_level or "-"),
                    _latex_tt(sig),
                    str(len(members)),
                    _fmt(best.score, 6),
                    _fmt(best.u1_score, 6),
                    _fmt(best.pred0, 6),
                    _fmt(best.predz, 6),
                    _latex_tt(_short(best.u1_candidate or "-", 18)),
                    _fmt(best.u1_scale, 6),
                ]
            )
            + r" \\"
        )
    tex_cl.append(r"\bottomrule")
    out_cl = out_dir / f"sm_hilbert_numeric_match_strong_clusters_{tag}_rows.tex"
    write_lines(out_cl, tex_cl)

    # Summary fragment.
    summary: List[str] = []
    summary.append(
        r"\paragraph{Cluster summary (strong numeric match; GI-signature clusters).} \AuditTag "
        + rf"We summarize a strong-search leaderboard (tag { _latex_tt(tag) }) and cluster candidates by GI signature. "
        + rf"Total leaderboard candidates: {len(rows_all)}; clusters: {len(clusters)}; top-K shown: {top_k}."
    )
    out_sum = out_dir / f"sm_hilbert_numeric_match_strong_clusters_{tag}_summary.tex"
    write_lines(out_sum, summary)

    print(f"Wrote sections/generated/{out_top.name}")
    print(f"Wrote sections/generated/{out_cl.name}")
    print(f"Wrote sections/generated/{out_sum.name}")


if __name__ == "__main__":
    main()

