# -*- coding: utf-8 -*-
"""
Multi-resolution discrimination summaries (AUC) for the recoding dataset (standard library only).

Goal:
  - quantify how well Fold_m uplift-window statistics separate recoding sites from
    (i) CDS-deduplicated terminal-stop windows and (ii) within-CDS random internal controls.

Inputs:
  - data/recoding_genbank/recoding_sites.jsonl (site-level rows; requires window sequences)

Outputs:
  - sections/generated/recoding_discrimination_summary_foldm.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from cache_manager import cache_hit, cache_meta_path, cache_key_digest, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, fold_codon_m
from progress_tools import Heartbeat


SCRIPT_VERSION = 2
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


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

    SE via the Hanley–McNeil approximation (ties ignored in the variance model).
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
    p = argparse.ArgumentParser(description="Recoding discrimination summary (Fold_m AUC) from recoding_sites.jsonl.")
    p.add_argument("--in-jsonl", default=str(recoding_jsonl_default()), help="Input JSONL with recoding sites.")
    p.add_argument("--analysis-version", type=int, default=7, help="Filter: analysis_version.")
    p.add_argument("--k", type=int, default=10, help="Filter: window radius k.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated Zeckendorf window lengths m.")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "recoding_discrimination_summary_foldm.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_jsonl = Path(args.in_jsonl)
    out_tex = Path(args.out_tex)
    ms = _parse_m_list(str(args.m_list))

    if not in_jsonl.exists():
        raise SystemExit(f"Input not found: {in_jsonl}")

    cache_key = {
        "analysis": "recoding_discrimination_foldm",
        "version": int(SCRIPT_VERSION),
        "analysis_version": int(args.analysis_version),
        "k": int(args.k),
        "m_list": ms,
        "in_jsonl": _file_fingerprint(in_jsonl),
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    # Precompute delta tables for all codons (RNA alphabet) for each m.
    delta_table: dict[int, dict[str, int]] = {}
    for m in ms:
        delta_table[int(m)] = {}
        for codon in GENETIC_CODE:
            delta_table[int(m)][codon] = int(fold_codon_m(codon, MU_STAR, m=int(m)).delta)

    hb = Heartbeat(every_s=60.0, prefix="[progress] recoding_discrimination_foldm")
    hb.force(f"start av={int(args.analysis_version)} k={int(args.k)} m={','.join(str(x) for x in ms)}")

    # Per-m distributions
    rec_before: dict[int, list[float]] = {int(m): [] for m in ms}
    rec_after: dict[int, list[float]] = {int(m): [] for m in ms}
    rec_diff: dict[int, list[float]] = {int(m): [] for m in ms}

    ctrl_before: dict[int, list[float]] = {int(m): [] for m in ms}
    ctrl_after: dict[int, list[float]] = {int(m): [] for m in ms}
    ctrl_diff: dict[int, list[float]] = {int(m): [] for m in ms}

    # CDS-deduplicated terminal-stop windows keyed by (version, cds_location, translation_start).
    term_by_cds: dict[tuple[str, str, int], dict[str, object]] = {}

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

            before_seq = r.get("before_seq_dna")
            after_seq = r.get("after_seq_dna")
            if isinstance(before_seq, str) and isinstance(after_seq, str):
                for m in ms:
                    b = _mean_delta_from_window_seq(before_seq, m=int(m), delta_table=delta_table)
                    a = _mean_delta_from_window_seq(after_seq, m=int(m), delta_table=delta_table)
                    if b is not None:
                        rec_before[int(m)].append(float(b))
                    if a is not None:
                        rec_after[int(m)].append(float(a))
                    if b is not None and a is not None:
                        rec_diff[int(m)].append(float(a) - float(b))

            # Control-C: within-CDS random controls (mean across stored pick windows).
            cb_seqs = r.get("control_random_cds_before_seqs_dna")
            ca_seqs = r.get("control_random_cds_after_seqs_dna")
            if isinstance(cb_seqs, list) and isinstance(ca_seqs, list) and cb_seqs and ca_seqs:
                # Ensure equal-length pairing; fall back to min length.
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
                            ctrl_before[int(m)].append(sum(b_vals) / float(len(b_vals)))
                        if a_vals:
                            ctrl_after[int(m)].append(sum(a_vals) / float(len(a_vals)))
                        if b_vals and a_vals:
                            ctrl_diff[int(m)].append((sum(a_vals) / float(len(a_vals))) - (sum(b_vals) / float(len(b_vals))))

            # Terminal windows per CDS
            version = str(r.get("version") or "").strip()
            cds_location = str(r.get("cds_location") or "").strip()
            ts = r.get("translation_start")
            if version and cds_location and isinstance(ts, int):
                key = (version, cds_location, int(ts))
                if key not in term_by_cds:
                    term_by_cds[key] = {
                        "before_seq": r.get("terminal_before_seq_dna"),
                        "after_seq": r.get("terminal_after_seq_dna"),
                    }

    # Terminal distributions (deduplicated)
    term_before: dict[int, list[float]] = {int(m): [] for m in ms}
    term_after: dict[int, list[float]] = {int(m): [] for m in ms}
    term_diff: dict[int, list[float]] = {int(m): [] for m in ms}
    for v in term_by_cds.values():
        bseq = v.get("before_seq")
        aseq = v.get("after_seq")
        if isinstance(bseq, str):
            for m in ms:
                b = _mean_delta_from_window_seq(bseq, m=int(m), delta_table=delta_table)
                if b is not None:
                    term_before[int(m)].append(float(b))
        if isinstance(aseq, str):
            for m in ms:
                a = _mean_delta_from_window_seq(aseq, m=int(m), delta_table=delta_table)
                if a is not None:
                    term_after[int(m)].append(float(a))
        if isinstance(bseq, str) and isinstance(aseq, str):
            for m in ms:
                b = _mean_delta_from_window_seq(bseq, m=int(m), delta_table=delta_table)
                a = _mean_delta_from_window_seq(aseq, m=int(m), delta_table=delta_table)
                if b is not None and a is not None:
                    term_diff[int(m)].append(float(a) - float(b))

    hb.force(
        "parsed "
        + " ".join(
            [
                f"lines={n_lines}",
                " ".join([f"m{m}:rec={len(rec_before[int(m)])}/{len(rec_after[int(m)])}/{len(rec_diff[int(m)])}" for m in ms]),
                " ".join([f"m{m}:term={len(term_before[int(m)])}/{len(term_after[int(m)])}/{len(term_diff[int(m)])}" for m in ms]),
                " ".join([f"m{m}:ctrl={len(ctrl_before[int(m)])}/{len(ctrl_after[int(m)])}/{len(ctrl_diff[int(m)])}" for m in ms]),
            ]
        )
    )

    rows_out: list[tuple[int, str, str, AucResult]] = []

    def _safe_auc(pos: list[float], neg: list[float]) -> AucResult | None:
        if len(pos) <= 0 or len(neg) <= 0:
            return None
        return auc_mann_whitney(pos, neg)

    for m in ms:
        m_i = int(m)
        # Recoding vs terminal (CDS-deduplicated)
        for metric, pos, neg in [
            ("$\\overline{U}_{\\mathrm{before}}$", rec_before[m_i], term_before[m_i]),
            ("$\\overline{U}_{\\mathrm{after}}$", rec_after[m_i], term_after[m_i]),
            ("$\\overline{U}_{\\mathrm{after}}-\\overline{U}_{\\mathrm{before}}$", rec_diff[m_i], term_diff[m_i]),
        ]:
            res = _safe_auc(pos, neg)
            if res is not None:
                rows_out.append((m_i, "Recoding vs terminal (CDS-deduplicated)", metric, res))
        # Recoding vs random internal control
        for metric, pos, neg in [
            ("$\\overline{U}_{\\mathrm{before}}$", rec_before[m_i], ctrl_before[m_i]),
            ("$\\overline{U}_{\\mathrm{after}}$", rec_after[m_i], ctrl_after[m_i]),
            ("$\\overline{U}_{\\mathrm{after}}-\\overline{U}_{\\mathrm{before}}$", rec_diff[m_i], ctrl_diff[m_i]),
        ]:
            res = _safe_auc(pos, neg)
            if res is not None:
                rows_out.append((m_i, "Recoding vs random internal (Control-C)", metric, res))

    # LaTeX output
    lines: list[str] = []
    lines.append(
        "Rank-based discrimination summaries (AUC) for uplift-window statistics in the recoding dataset across Fold$_m$ (AUC as Mann--Whitney concordance probability; 95\\% normal CI)."
    )
    lines.append("")
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{r l l r r r}")
    lines.append("\\toprule")
    lines.append("$m$ & comparison & metric & $n_1$ & $n_0$ & AUC [95\\% CI] \\\\")
    lines.append("\\midrule")
    for m_i, comp, metric, res in rows_out:
        auc_s = _fmt_float(res.auc, nd=4)
        lo_s = _fmt_float(res.ci_low, nd=4)
        hi_s = _fmt_float(res.ci_high, nd=4)
        lines.append(
            f"{_fmt_int(m_i)} & {comp} & {metric} & {_fmt_int(res.n_pos)} & {_fmt_int(res.n_neg)} & {auc_s} [{lo_s},{hi_s}] \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    hb.force(f"wrote {out_tex}")


if __name__ == "__main__":
    main()


