# -*- coding: utf-8 -*-
"""
Discrimination-style summary for the recoding dataset (standard library only).

Goal:
  - quantify how well uplift-window statistics separate recoding sites from
    CDS-deduplicated terminal-stop baselines using a rank-based AUC.

Inputs:
  - data/recoding_genbank/recoding_sites.jsonl (site-level rows)

Outputs:
  - sections/generated/recoding_discrimination_summary.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from cache_manager import cache_hit, cache_meta_path, cache_key_digest, write_json_atomic, write_text_atomic
from progress_tools import Heartbeat


SCRIPT_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    return root_dir() / "sections" / "generated"


def recoding_jsonl_default() -> Path:
    return root_dir() / "data" / "recoding_genbank" / "recoding_sites.jsonl"


def _file_fingerprint(path: Path) -> dict[str, object]:
    st = path.stat()
    return {
        "path": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _is_num(x: object) -> bool:
    return isinstance(x, (int, float)) and (not isinstance(x, bool)) and math.isfinite(float(x))


def _fmt_int(x: object) -> str:
    try:
        return str(int(x))
    except Exception:
        return "-"


def _fmt_float(x: object, *, nd: int = 4) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}"


@dataclass(frozen=True)
class AucResult:
    auc: float
    se: float
    ci_low: float
    ci_high: float
    n_pos: int
    n_neg: int


def _rankdata(values: list[float]) -> list[float]:
    """
    Average ranks for ties, 1-based.
    """
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    r = 1
    while i < n:
        j = i
        v = values[order[i]]
        while j < n and values[order[j]] == v:
            j += 1
        # average of ranks r..(r+(j-i)-1)
        avg = 0.5 * (r + (r + (j - i) - 1))
        for k in range(i, j):
            ranks[order[k]] = float(avg)
        r += (j - i)
        i = j
    return ranks


def auc_mann_whitney(pos: list[float], neg: list[float]) -> AucResult:
    """
    AUC as the Mann–Whitney concordance probability:
      AUC = P(X_pos > X_neg) + 0.5 P(X_pos = X_neg).

    SE via the Hanley–McNeil approximation (works well for large n; ties ignored in the model).
    """
    n1 = int(len(pos))
    n0 = int(len(neg))
    if n1 <= 0 or n0 <= 0:
        raise ValueError("Need at least one positive and one negative sample.")
    all_vals = pos + neg
    ranks = _rankdata(all_vals)
    r_pos = sum(ranks[:n1])
    u = r_pos - (n1 * (n1 + 1)) / 2.0
    auc = float(u) / float(n1 * n0)
    auc = min(1.0, max(0.0, auc))

    # Hanley–McNeil variance approximation (AUC treated as continuous).
    q1 = auc / (2.0 - auc) if (2.0 - auc) != 0 else 0.0
    q2 = (2.0 * auc * auc) / (1.0 + auc) if (1.0 + auc) != 0 else 0.0
    var = (auc * (1.0 - auc) + (n1 - 1) * (q1 - auc * auc) + (n0 - 1) * (q2 - auc * auc)) / float(n1 * n0)
    se = math.sqrt(max(0.0, float(var)))

    z = 1.96
    ci_low = max(0.0, auc - z * se)
    ci_high = min(1.0, auc + z * se)
    return AucResult(auc=auc, se=se, ci_low=ci_low, ci_high=ci_high, n_pos=n1, n_neg=n0)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recoding discrimination summary (AUC) from recoding_sites.jsonl.")
    p.add_argument("--in-jsonl", default=str(recoding_jsonl_default()), help="Input JSONL with recoding sites.")
    p.add_argument("--analysis-version", type=int, default=7, help="Filter: analysis_version.")
    p.add_argument("--k", type=int, default=10, help="Filter: window radius k.")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "recoding_discrimination_summary.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_jsonl = Path(args.in_jsonl)
    out_tex = Path(args.out_tex)

    if not in_jsonl.exists():
        raise SystemExit(f"Input not found: {in_jsonl}")

    cache_key = {
        "analysis": "recoding_discrimination",
        "version": int(SCRIPT_VERSION),
        "analysis_version": int(args.analysis_version),
        "k": int(args.k),
        "in_jsonl": _file_fingerprint(in_jsonl),
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    hb = Heartbeat(every_s=60.0, prefix="[progress] recoding_discrimination")
    hb.force(f"start av={int(args.analysis_version)} k={int(args.k)}")

    rec_before: list[float] = []
    rec_after: list[float] = []
    rec_diff: list[float] = []

    ctrl_before: list[float] = []
    ctrl_after: list[float] = []
    ctrl_diff: list[float] = []

    # CDS-deduplicated terminal-stop windows.
    # Key aligns with exp_recoding_sites.py: (version, cds_location, translation_start).
    term_by_cds: dict[tuple[str, str, int], tuple[float | None, float | None]] = {}

    n_lines = 0
    with in_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            if n_lines % 20000 == 0:
                hb.maybe(f"lines={n_lines}")
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not isinstance(r, dict):
                continue
            if int(r.get("analysis_version") or 0) != int(args.analysis_version):
                continue
            if int(r.get("k") or 0) != int(args.k):
                continue

            b = r.get("before_mean_delta")
            a = r.get("after_mean_delta")
            if _is_num(b):
                rec_before.append(float(b))
            if _is_num(a):
                rec_after.append(float(a))
            if _is_num(b) and _is_num(a):
                rec_diff.append(float(a) - float(b))

            cb = r.get("control_random_cds_before_mean_delta")
            ca = r.get("control_random_cds_after_mean_delta")
            if _is_num(cb):
                ctrl_before.append(float(cb))
            if _is_num(ca):
                ctrl_after.append(float(ca))
            if _is_num(cb) and _is_num(ca):
                ctrl_diff.append(float(ca) - float(cb))

            version = str(r.get("version") or "").strip()
            cds_location = str(r.get("cds_location") or "").strip()
            ts = r.get("translation_start")
            if version and cds_location and isinstance(ts, int):
                kb = r.get("terminal_before_mean_delta")
                ka = r.get("terminal_after_mean_delta")
                tb = float(kb) if _is_num(kb) else None
                ta = float(ka) if _is_num(ka) else None
                term_by_cds[(version, cds_location, int(ts))] = (tb, ta)

    term_before: list[float] = []
    term_after: list[float] = []
    term_diff: list[float] = []
    for (tb, ta) in term_by_cds.values():
        if _is_num(tb):
            term_before.append(float(tb))
        if _is_num(ta):
            term_after.append(float(ta))
        if _is_num(tb) and _is_num(ta):
            term_diff.append(float(ta) - float(tb))

    hb.force(
        "parsed "
        + " ".join(
            [
                f"lines={n_lines}",
                f"rec_before={len(rec_before)} rec_after={len(rec_after)} rec_diff={len(rec_diff)}",
                f"term_before={len(term_before)} term_after={len(term_after)} term_diff={len(term_diff)}",
                f"ctrl_before={len(ctrl_before)} ctrl_after={len(ctrl_after)} ctrl_diff={len(ctrl_diff)}",
            ]
        )
    )

    # Compute AUCs (recoding as positive class).
    rows: list[tuple[str, str, AucResult]] = []

    def _safe_auc(pos: list[float], neg: list[float]) -> AucResult | None:
        if len(pos) <= 0 or len(neg) <= 0:
            return None
        return auc_mann_whitney(pos, neg)

    for metric, pos, neg in [
        ("$\\overline{U}_{\\mathrm{before}}$", rec_before, term_before),
        ("$\\overline{U}_{\\mathrm{after}}$", rec_after, term_after),
        ("$\\overline{U}_{\\mathrm{after}}-\\overline{U}_{\\mathrm{before}}$", rec_diff, term_diff),
    ]:
        res = _safe_auc(pos, neg)
        if res:
            rows.append(("Recoding vs terminal (CDS-deduplicated)", metric, res))

    for metric, pos, neg in [
        ("$\\overline{U}_{\\mathrm{before}}$", rec_before, ctrl_before),
        ("$\\overline{U}_{\\mathrm{after}}$", rec_after, ctrl_after),
        ("$\\overline{U}_{\\mathrm{after}}-\\overline{U}_{\\mathrm{before}}$", rec_diff, ctrl_diff),
    ]:
        res = _safe_auc(pos, neg)
        if res:
            rows.append(("Recoding vs random internal (Control-C)", metric, res))

    # Build LaTeX.
    lines: list[str] = []
    lines.append(
        "Rank-based discrimination summaries (AUC) for uplift-window statistics in the recoding dataset (AUC as Mann--Whitney concordance probability; 95\\% normal CI)."
    )
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{l l r r r}")
    lines.append("\\toprule")
    lines.append("comparison & metric & $n_1$ & $n_0$ & AUC [95\\% CI] \\\\")
    lines.append("\\midrule")
    for comp, metric, res in rows:
        auc_s = _fmt_float(res.auc, nd=4)
        lo_s = _fmt_float(res.ci_low, nd=4)
        hi_s = _fmt_float(res.ci_high, nd=4)
        lines.append(f"{comp} & {metric} & {_fmt_int(res.n_pos)} & {_fmt_int(res.n_neg)} & {auc_s} [{lo_s},{hi_s}] \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    hb.force(f"wrote {out_tex}")


if __name__ == "__main__":
    main()


