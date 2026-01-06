# -*- coding: utf-8 -*-
"""
Stratified AUC analysis for recoding vs within-CDS random internal controls (Control-C) across Fold_m.

Motivation:
  The aggregate Control-C AUC can flip sign between m (e.g. m=6/7 vs m=8).
  This script localizes which strata drive the flip, using the same window-sequence
  based Fold_m computation as exp_recoding_discrimination_foldm.py.

We focus on Control-C only, and on the metrics most relevant to the observed flips:
  - U_before
  - U_after - U_before

Strata:
  - by aa (Sec/Pyl)
  - by domain (Eukaryota/Bacteria/Archaea/...)
  - by codon_rna (UGA/UAG/...)

Outputs:
  - sections/generated/recoding_controlc_foldm_stratified_summary.tex
  - sections/generated/recoding_controlc_foldm_stratified_table.tex
  - sections/generated/recoding_controlc_foldm_stratified_flips.tex
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, fold_codon_m
from progress_tools import Heartbeat


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def recoding_jsonl_default() -> Path:
    return root_dir() / "data" / "recoding_genbank" / "recoding_sites.jsonl"


def _file_fingerprint(path: Path) -> dict[str, object]:
    st = path.stat()
    return {
        "path": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _parse_m_list(s: str) -> list[int]:
    ms: list[int] = []
    for p in str(s).split(","):
        p = p.strip()
        if not p:
            continue
        ms.append(int(p))
    ms = sorted({int(m) for m in ms if int(m) > 0})
    if not ms:
        raise SystemExit("--m-list must contain positive integers")
    return ms


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


def _fmt_float_signed(x: object, *, nd: int = 4) -> str:
    if not _is_num(x):
        return "-"
    v = float(x)
    s = f"{v:.{int(nd)}f}"
    return s if s.startswith("-") else ("+" + s)


def _tex_escape(s: str) -> str:
    return str(s).replace("_", "\\_")


def _sign(x: float, *, eps: float = 1e-12) -> int:
    if abs(float(x)) <= float(eps):
        return 0
    return 1 if float(x) > 0 else -1


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
        avg = 0.5 * (r + (r + (j - i) - 1))
        for k in range(i, j):
            ranks[order[k]] = float(avg)
        r += (j - i)
        i = j
    return ranks


@dataclass(frozen=True)
class AucResult:
    auc: float
    se: float
    ci_low: float
    ci_high: float
    n_pos: int
    n_neg: int


def auc_mann_whitney(pos: list[float], neg: list[float]) -> AucResult:
    """
    AUC as the Mann–Whitney concordance probability.
    SE via Hanley–McNeil approximation.
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

    q1 = auc / (2.0 - auc) if (2.0 - auc) != 0 else 0.0
    q2 = (2.0 * auc * auc) / (1.0 + auc) if (1.0 + auc) != 0 else 0.0
    var = (auc * (1.0 - auc) + (n1 - 1) * (q1 - auc * auc) + (n0 - 1) * (q2 - auc * auc)) / float(n1 * n0)
    se = math.sqrt(max(0.0, float(var)))

    z = 1.96
    ci_low = max(0.0, auc - z * se)
    ci_high = min(1.0, auc + z * se)
    return AucResult(auc=auc, se=se, ci_low=ci_low, ci_high=ci_high, n_pos=n1, n_neg=n0)


def _mean_delta_from_window_seq(seq_dna: str, *, m: int, delta_table: dict[int, dict[str, int]]) -> float | None:
    """
    Mean Delta_m over codons in a 3k-nt DNA window (already in translated orientation).
    Returns None if invalid length/codon encountered.
    """
    s = str(seq_dna).upper()
    if len(s) == 0 or (len(s) % 3) != 0:
        return None
    k = len(s) // 3
    if k <= 0:
        return None
    tot = 0
    for i in range(0, len(s), 3):
        c = s[i : i + 3]
        if len(c) != 3:
            return None
        if any(ch not in "ACGT" for ch in c):
            return None
        rna = c.replace("T", "U")
        d = delta_table[int(m)].get(rna)
        if d is None:
            return None
        tot += int(d)
    return float(tot) / float(k)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stratified Control-C AUC across Fold_m for recoding dataset.")
    p.add_argument("--in-jsonl", default=str(recoding_jsonl_default()), help="Input JSONL with recoding sites.")
    p.add_argument("--analysis-version", type=int, default=7, help="Filter: analysis_version.")
    p.add_argument("--k", type=int, default=10, help="Filter: window radius k.")
    p.add_argument("--m-list", default="6,7,8", help="Comma-separated Zeckendorf window lengths m.")
    p.add_argument("--min-n", type=int, default=40, help="Minimum n_pos to report a stratum.")
    p.add_argument("--top-max", type=int, default=50, help="Max number of strata per group type to print (by n_pos).")
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "recoding_controlc_foldm_stratified_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "recoding_controlc_foldm_stratified_table.tex"),
        help="Output LaTeX table fragment path.",
    )
    p.add_argument(
        "--out-flips",
        default=str(generated_dir() / "recoding_controlc_foldm_stratified_flips.tex"),
        help="Output LaTeX flips fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_jsonl = Path(args.in_jsonl)
    out_summary = Path(args.out_summary)
    out_table = Path(args.out_table)
    out_flips = Path(args.out_flips)
    ms = _parse_m_list(str(args.m_list))
    if not in_jsonl.exists():
        raise SystemExit(f"Input not found: {in_jsonl}")

    cache_key = {
        "analysis": "recoding_controlc_foldm_stratified",
        "version": int(SCRIPT_VERSION),
        "analysis_version": int(args.analysis_version),
        "k": int(args.k),
        "m_list": ms,
        "min_n": int(args.min_n),
        "top_max": int(args.top_max),
        "in_jsonl": _file_fingerprint(in_jsonl),
        "out_summary": str(out_summary),
        "out_table": str(out_table),
        "out_flips": str(out_flips),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_table, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_table}", flush=True)
        return

    # Precompute delta tables for all codons (RNA alphabet) for each m.
    delta_table: dict[int, dict[str, int]] = {}
    for m in ms:
        delta_table[int(m)] = {}
        for codon in GENETIC_CODE:
            delta_table[int(m)][codon] = int(fold_codon_m(codon, MU_STAR, m=int(m)).delta)

    # group_type -> group_value -> metric -> m -> list
    # We compute Control-C only: pos = recoding; neg = control_random_cds (site-averaged).
    metrics = ["before", "diff"]

    def _mk() -> dict[str, dict[int, list[float]]]:
        return {metric: {int(m): [] for m in ms} for metric in metrics}

    pos: dict[str, dict[str, dict[str, dict[int, list[float]]]]] = defaultdict(lambda: defaultdict(_mk))
    neg: dict[str, dict[str, dict[str, dict[int, list[float]]]]] = defaultdict(lambda: defaultdict(_mk))

    # Track n_pos by group for sorting.
    npos_counter: dict[tuple[str, str], int] = defaultdict(int)

    hb = Heartbeat(every_s=60.0, prefix="[progress] recoding_controlc_foldm_stratified")
    hb.force(f"start av={int(args.analysis_version)} k={int(args.k)} m={','.join(str(x) for x in ms)}")

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

            aa = str(r.get("aa") or "-").strip() or "-"
            domain = str(r.get("domain") or "-").strip() or "-"
            codon_rna = str(r.get("codon_rna") or "-").strip() or "-"

            group_map = {
                "aa": aa,
                "domain": domain,
                "codon": codon_rna,
            }

            before_seq = r.get("before_seq_dna")
            after_seq = r.get("after_seq_dna")

            cb_seqs = r.get("control_random_cds_before_seqs_dna")
            ca_seqs = r.get("control_random_cds_after_seqs_dna")

            # Compute control site-averaged before/after values once per m.
            ctrl_before_m: dict[int, float] = {}
            ctrl_after_m: dict[int, float] = {}
            if isinstance(cb_seqs, list) and isinstance(ca_seqs, list) and cb_seqs and ca_seqs:
                n_pair = min(len(cb_seqs), len(ca_seqs))
                if n_pair > 0:
                    for m in ms:
                        b_vals: list[float] = []
                        a_vals: list[float] = []
                        for i in range(n_pair):
                            sb = cb_seqs[i]
                            sa = ca_seqs[i]
                            if not isinstance(sb, str) or not isinstance(sa, str):
                                continue
                            b0 = _mean_delta_from_window_seq(sb, m=int(m), delta_table=delta_table)
                            a0 = _mean_delta_from_window_seq(sa, m=int(m), delta_table=delta_table)
                            if b0 is not None:
                                b_vals.append(float(b0))
                            if a0 is not None:
                                a_vals.append(float(a0))
                        if b_vals:
                            ctrl_before_m[int(m)] = float(sum(b_vals) / float(len(b_vals)))
                        if a_vals:
                            ctrl_after_m[int(m)] = float(sum(a_vals) / float(len(a_vals)))

            # Recoding (pos) and control (neg) contributions.
            # Metric before: require before_seq and ctrl_before.
            if isinstance(before_seq, str):
                added_any = False
                for m in ms:
                    b = _mean_delta_from_window_seq(before_seq, m=int(m), delta_table=delta_table)
                    cb = ctrl_before_m.get(int(m))
                    if b is None or cb is None:
                        continue
                    for gtype, gval in group_map.items():
                        pos[gtype][gval]["before"][int(m)].append(float(b))
                        neg[gtype][gval]["before"][int(m)].append(float(cb))
                    added_any = True
                if added_any:
                    npos_counter[("aa", aa)] += 1
                    npos_counter[("domain", domain)] += 1
                    npos_counter[("codon", codon_rna)] += 1

            # Metric diff: require before_seq+after_seq and ctrl_before+ctrl_after.
            if isinstance(before_seq, str) and isinstance(after_seq, str):
                for m in ms:
                    b = _mean_delta_from_window_seq(before_seq, m=int(m), delta_table=delta_table)
                    a = _mean_delta_from_window_seq(after_seq, m=int(m), delta_table=delta_table)
                    cb = ctrl_before_m.get(int(m))
                    ca = ctrl_after_m.get(int(m))
                    if b is None or a is None or cb is None or ca is None:
                        continue
                    d_pos = float(a) - float(b)
                    d_neg = float(ca) - float(cb)
                    for gtype, gval in group_map.items():
                        pos[gtype][gval]["diff"][int(m)].append(d_pos)
                        neg[gtype][gval]["diff"][int(m)].append(d_neg)

    hb.force(f"parsed lines={n_lines}")

    # Build report rows: for each group type and value, compute AUCs for m values.
    out_rows: list[dict[str, object]] = []
    flip_rows: list[dict[str, object]] = []

    for gtype in ["aa", "domain", "codon"]:
        # Sort group values by n_pos desc (metric=before at first m).
        values = list(pos[gtype].keys())
        values.sort(key=lambda v: npos_counter.get((gtype, v), 0), reverse=True)
        values = values[: int(args.top_max)]
        for gval in values:
            for metric in metrics:
                # Ensure enough data and full m coverage.
                ok = True
                for m in ms:
                    if len(pos[gtype][gval][metric][int(m)]) == 0 or len(neg[gtype][gval][metric][int(m)]) == 0:
                        ok = False
                        break
                if not ok:
                    continue
                n_pos = len(pos[gtype][gval][metric][int(ms[0])])
                n_neg = len(neg[gtype][gval][metric][int(ms[0])])
                if n_pos < int(args.min_n):
                    continue
                aucs: dict[int, float] = {}
                for m in ms:
                    res = auc_mann_whitney(pos[gtype][gval][metric][int(m)], neg[gtype][gval][metric][int(m)])
                    aucs[int(m)] = float(res.auc)
                # flip between first and last m in list
                m0 = int(ms[0])
                mL = int(ms[-1])
                s0 = _sign(float(aucs[m0]) - 0.5)
                sL = _sign(float(aucs[mL]) - 0.5)
                flip = (s0 != 0 and sL != 0 and s0 != sL)
                out_rows.append(
                    {
                        "group_type": gtype,
                        "group": gval,
                        "metric": metric,
                        "n_pos": n_pos,
                        "n_neg": n_neg,
                        **{f"auc_{int(m)}": float(aucs[int(m)]) for m in ms},
                        "flip": bool(flip),
                    }
                )
                if flip:
                    flip_rows.append(
                        {
                            "group_type": gtype,
                            "group": gval,
                            "metric": metric,
                            "auc_m0": float(aucs[m0]),
                            "auc_mL": float(aucs[mL]),
                        }
                    )

    # Summary
    m_str = ",".join(str(int(m)) for m in ms)
    s = (
        "Stratified Control-C discrimination (AUC) across Fold$_m$ for recoding vs within-CDS random internal controls "
        f"(metrics: $\\overline{{U}}_{{\\mathrm{{before}}}}$, $\\overline{{U}}_{{\\mathrm{{after}}}}-\\overline{{U}}_{{\\mathrm{{before}}}}$; "
        f"$m\\in\\{{{m_str}\\}}$)."
    )
    write_text_atomic(out_summary, s + "\n")

    # LaTeX table (main)
    out_rows.sort(key=lambda r: (str(r["group_type"]), str(r["metric"]), -int(r["n_pos"]), str(r["group"])))
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    # columns: group_type, group, metric, n_pos, n_neg, auc_m... , flip
    col_spec = "l l l r r " + " ".join(["r" for _ in ms]) + " l"
    lines.append(f"\\begin{{longtable}}{{{col_spec}}}")
    lines.append("\\toprule")
    header = ["group", "value", "metric", "$n_1$", "$n_0$"] + [f"AUC$_{{m={int(m)}}}$" for m in ms] + ["flip"]
    lines.append(" & ".join(header) + " \\\\")
    lines.append("\\midrule")
    for r in out_rows:
        metric_tex = "$\\overline{U}_{\\mathrm{before}}$" if str(r["metric"]) == "before" else "$\\overline{U}_{\\mathrm{after}}-\\overline{U}_{\\mathrm{before}}$"
        flip_s = "yes" if bool(r["flip"]) else "no"
        row = [
            _tex_escape(str(r["group_type"])),
            _tex_escape(str(r["group"])),
            metric_tex,
            _fmt_int(r["n_pos"]),
            _fmt_int(r["n_neg"]),
        ] + [_fmt_float(r.get(f"auc_{int(m)}"), nd=4) for m in ms] + [flip_s]
        lines.append(" & ".join(row) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")
    write_text_atomic(out_table, "\n".join(lines) + "\n")

    # LaTeX flips table
    fl: list[str] = []
    fl.append("\\begingroup")
    fl.append("\\hbadness=10000")
    fl.append("\\small")
    fl.append("\\setlength{\\tabcolsep}{6pt}")
    fl.append("\\renewcommand{\\arraystretch}{1.15}")
    fl.append("\\setlength{\\LTleft}{0pt}")
    fl.append("\\setlength{\\LTright}{0pt}")
    fl.append("\\begin{longtable}{l l l r r}")
    fl.append("\\toprule")
    fl.append(f"group & value & metric & AUC$_{{m={int(ms[0])}}}$ & AUC$_{{m={int(ms[-1])}}}$ \\\\")
    fl.append("\\midrule")
    flip_rows.sort(key=lambda r: (str(r["group_type"]), str(r["metric"]), str(r["group"])))
    if flip_rows:
        for r in flip_rows:
            metric_tex = "$\\overline{U}_{\\mathrm{before}}$" if str(r["metric"]) == "before" else "$\\overline{U}_{\\mathrm{after}}-\\overline{U}_{\\mathrm{before}}$"
            fl.append(
                f"{_tex_escape(str(r['group_type']))} & {_tex_escape(str(r['group']))} & {metric_tex} & "
                f"{_fmt_float(r['auc_m0'], nd=4)} & {_fmt_float(r['auc_mL'], nd=4)} \\\\"
            )
    else:
        fl.append("\\multicolumn{5}{l}{No sign flips at the stratum level.} \\\\")
    fl.append("\\bottomrule")
    fl.append("\\end{longtable}")
    fl.append("\\endgroup")
    fl.append("")
    write_text_atomic(out_flips, "\n".join(fl) + "\n")

    write_json_atomic(cache_meta_path(out_table), cache_meta)
    print("Wrote:", out_summary)
    print("Wrote:", out_table)
    print("Wrote:", out_flips)


if __name__ == "__main__":
    main()


