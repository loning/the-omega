# -*- coding: utf-8 -*-
"""
Merge shard-level transcriptome summaries produced by exp_refseq_transcriptome.py
and regenerate the final JSON summary + LaTeX fragments.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import heapq
import math
import random
import statistics
from collections import Counter
from pathlib import Path

from cache_manager import cache_hit, cache_meta_path, cache_key_digest, write_json_atomic
from exp_refseq_transcriptome import (
    MU_STAR,
    ANALYSIS_VERSION,
    RunningStats,
    _summarize_float_list,
    codon_usage_null_test,
    generated_dir,
    hist_quantile_inclusive,
    hist_sum,
    hist_total,
    welch_t_p_value_two_sided_from_stats,
    student_t_cdf,
    write_text,
)
from genetic_code_tools import BOUNDARY_WORDS, GENETIC_CODE, STOP_CODONS, amino_acid_codons, fold_codon
from progress_tools import Heartbeat
from stats_tools import (
    aa_preserving_null_decomposition,
    bh_fdr,
    cohen_d_from_stats,
    hedges_g_from_stats,
    mean_diff_ci_normal_from_stats,
    normal_two_sided_p,
)

MERGE_VERSION = 4


def _stable_seed_u32(tag: str) -> int:
    h = hashlib.sha256(tag.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


DINUC_ORDER = [a + b for a in "ACGT" for b in "ACGT"]


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge RefSeq transcriptome shard summaries")
    p.add_argument(
        "--in-dir",
        default=str(root_dir() / "data" / "refseq_hsapiens_mrna" / "shards" / f"k10_v{int(ANALYSIS_VERSION)}"),
        help="Directory containing shard JSON summaries.",
    )
    p.add_argument(
        "--out-json",
        default=str(root_dir() / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json"),
        help="Output merged JSON path.",
    )
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--force", action="store_true", help="Force merge and LaTeX regeneration (ignore cache).")
    p.add_argument("--candidate-limit", type=int, default=20, help="Per-stop candidate count for high/low context lists.")
    p.add_argument("--candidate-set", default="reporter_v1", help="Candidate set label (for exports / Supabase).")
    p.add_argument(
        "--candidate-set-coding",
        default="reporter_coding_v1",
        help="Candidate set label for protein-coding-only (NM/XM) stop-context candidates.",
    )
    p.add_argument(
        "--heartbeat-s",
        type=float,
        default=60.0,
        help="Emit a progress heartbeat at least once per this many seconds (0 disables).",
    )
    return p.parse_args()


def _load_stats(d: dict[str, object]) -> RunningStats:
    return RunningStats(
        n=int(d.get("n", 0) or 0),
        mean=float(d.get("mean", 0.0) or 0.0),
        M2=float(d.get("M2", 0.0) or 0.0),
    )


def _fmt_p_tex(p: float | None) -> tuple[str, str]:
    """
    Format a p-value for LaTeX.
    Returns (op, value) with a short scientific notation for very small p.
    """
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "=", "NA"
    p0 = float(p)
    if p0 == 0.0:
        return "<", "10^{-300}"
    if p0 < 1e-4:
        s = f"{p0:.2e}"
        mant, exp = s.split("e", 1)
        try:
            exp_i = int(exp)
        except Exception:
            exp_i = int(float(exp))
        return "=", f"{mant}\\times 10^{{{exp_i}}}"
    return "=", f"{p0:.4f}"


def _logspace(lo: float, hi: float, n: int) -> list[float]:
    if n <= 1:
        return [float(lo)]
    lo0 = float(lo)
    hi0 = float(hi)
    if lo0 <= 0 or hi0 <= 0:
        raise ValueError("logspace bounds must be positive")
    a = math.log(lo0)
    b = math.log(hi0)
    out = []
    for i in range(int(n)):
        t = i / float(int(n) - 1)
        out.append(math.exp(a + (b - a) * t))
    return out


def _fit_saturating_exp(ks: list[int], ys: list[float]) -> dict[str, float] | None:
    """
    Fit D(k) = D_inf - A * exp(-k/kappa) by least squares.
    Uses a grid search over kappa and closed-form linear regression for (D_inf, A) at fixed kappa.
    Returns dict with keys: n, d_inf, kappa, r2 (plus sse).
    """
    if len(ks) != len(ys) or len(ks) < 3:
        return None
    xs_k = [float(k) for k in ks]
    y = [float(v) for v in ys]
    n = len(y)
    y_mean = sum(y) / float(n)
    sst = sum((v - y_mean) ** 2 for v in y)
    best: dict[str, float] | None = None

    for kappa in _logspace(0.5, 200.0, 240):
        x = [math.exp(-k / float(kappa)) for k in xs_k]
        x_mean = sum(x) / float(n)
        var_x = sum((u - x_mean) ** 2 for u in x)
        if var_x <= 0:
            continue
        cov_xy = sum((u - x_mean) * (v - y_mean) for u, v in zip(x, y))
        b = cov_xy / var_x  # slope in y = a + b x
        a = y_mean - b * x_mean  # intercept, equals D_inf
        sse = sum((v - (a + b * u)) ** 2 for u, v in zip(x, y))
        r2 = 1.0 - (sse / sst) if sst > 0 else 1.0
        if best is None or sse < best["sse"]:
            best = {"n": float(n), "d_inf": float(a), "kappa": float(kappa), "r2": float(r2), "sse": float(sse)}

    return best


def _write_tsv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out_lines = ["\t".join(header)]
    for r in rows:
        out_lines.append("\t".join("" if v is None else str(v) for v in r))
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def _emit_outputs_from_summary(summary: dict[str, object]) -> None:
    """
    Regenerate LaTeX fragments + TSVs from an already-merged transcriptome_summary.json.
    This enables fast rebuilds when the merged JSON is cached.
    """
    records = int(summary.get("records", 0) or 0)
    records_with_orf = int(summary.get("records_with_orf", 0) or 0)
    coding_tokens = int(summary.get("coding_tokens", 0) or 0)
    boundary_token_count = int(summary.get("boundary_token_count", 0) or 0)
    boundary_rate = float(summary.get("boundary_rate", 0.0) or 0.0)

    term_stop_counts = Counter({str(k): int(v) for k, v in (summary.get("termination_stop_counts", {}) or {}).items()})
    term_stop_boundary_count = int(summary.get("termination_stop_boundary_count", 0) or 0)

    # ORF length stats from histogram.
    orf_len_hist_raw = summary.get("orf_len_hist", {}) or {}
    if not isinstance(orf_len_hist_raw, dict):
        orf_len_hist_raw = {}
    orf_len_hist: Counter[int] = Counter()
    for k, v in orf_len_hist_raw.items():
        try:
            orf_len_hist[int(k)] += int(v)
        except Exception:
            continue
    n_orf = hist_total(orf_len_hist)
    mean_orf = (hist_sum(orf_len_hist) / float(n_orf)) if n_orf else float("nan")
    median_orf = float(hist_quantile_inclusive(orf_len_hist, 0.5)) if n_orf else float("nan")
    p25_orf = float(hist_quantile_inclusive(orf_len_hist, 0.25)) if n_orf else float("nan")
    p75_orf = float(hist_quantile_inclusive(orf_len_hist, 0.75)) if n_orf else float("nan")

    # Stop-context config.
    k_primary = int(summary.get("stop_window", 0) or 0)
    k_list_obj = summary.get("stop_window_list")
    k_list: list[int] = []
    if isinstance(k_list_obj, list):
        for x in k_list_obj:
            try:
                k_list.append(int(x))
            except Exception:
                continue
    if k_primary <= 0:
        # Back-compat: infer from stop_context.
        sc = summary.get("stop_context", {}) or {}
        if isinstance(sc, dict):
            for s in STOP_CODONS:
                if s in sc and isinstance(sc.get(s), dict):
                    try:
                        k_primary = int((sc.get(s) or {}).get("k", 0) or 0)  # type: ignore[assignment]
                    except Exception:
                        k_primary = 0
                    break
    if k_primary <= 0:
        raise SystemExit("Missing stop-window k in transcriptome_summary.json")
    if not k_list:
        k_list = [int(k_primary)]
    k_list = sorted({int(x) for x in k_list if int(x) >= 1} | {int(k_primary)})

    # Load Welford stats for multi-k.
    w_mk = summary.get("stop_context_welford_multi_k")
    if not isinstance(w_mk, dict) or not w_mk:
        # Back-compat: rebuild from stop_context_welford (single k only).
        w1 = summary.get("stop_context_welford")
        if not isinstance(w1, dict) or not w1:
            raise SystemExit("Missing stop-context Welford stats in transcriptome_summary.json")
        w_mk = {s: {str(int(k_primary)): (w1.get(s) or {})} for s in STOP_CODONS}

    before_stats_mk: dict[str, dict[int, RunningStats]] = {s: {} for s in STOP_CODONS}
    after_stats_mk: dict[str, dict[int, RunningStats]] = {s: {} for s in STOP_CODONS}
    for s in STOP_CODONS:
        sm = w_mk.get(s)
        if not isinstance(sm, dict):
            raise SystemExit(f"Malformed stop_context_welford_multi_k for {s}")
        for kk in k_list:
            entry = sm.get(str(int(kk)))
            if not isinstance(entry, dict):
                raise SystemExit(f"Missing stop_context_welford_multi_k[{s}][{kk}]")
            before_stats_mk[s][int(kk)] = _load_stats(entry.get("before", {}) or {})
            after_stats_mk[s][int(kk)] = _load_stats(entry.get("after", {}) or {})

    before_stats = {s: before_stats_mk[s][int(k_primary)] for s in STOP_CODONS}
    after_stats = {s: after_stats_mk[s][int(k_primary)] for s in STOP_CODONS}

    # Start-context Welford stats (multi-k).
    start_mk_raw = summary.get("start_context_welford_multi_k")
    start_before_stats_mk: dict[int, RunningStats] = {}
    start_after_stats_mk: dict[int, RunningStats] = {}
    if isinstance(start_mk_raw, dict) and start_mk_raw:
        for kk in k_list:
            entry = start_mk_raw.get(str(int(kk)))
            if not isinstance(entry, dict):
                raise SystemExit(f"Missing start_context_welford_multi_k[{kk}]")
            start_before_stats_mk[int(kk)] = _load_stats(entry.get("before", {}) or {})
            start_after_stats_mk[int(kk)] = _load_stats(entry.get("after", {}) or {})

    # P-values (Welch) for primary-k.
    p_before_raw = summary.get("stop_context_p_before", {}) or {}
    p_after_raw = summary.get("stop_context_p_after", {}) or {}
    p_before = {str(k): (None if v is None else float(v)) for k, v in (p_before_raw.items() if isinstance(p_before_raw, dict) else [])}
    p_after = {str(k): (None if v is None else float(v)) for k, v in (p_after_raw.items() if isinstance(p_after_raw, dict) else [])}

    # Codon usage null / counts.
    codon_counts_raw = summary.get("codon_counts", {}) or {}
    aa_counts_raw = summary.get("aa_counts", {}) or {}
    codon_counts = Counter({str(k): int(v) for k, v in (codon_counts_raw.items() if isinstance(codon_counts_raw, dict) else [])})
    aa_counts = Counter({str(k): int(v) for k, v in (aa_counts_raw.items() if isinstance(aa_counts_raw, dict) else [])})

    codon_usage = summary.get("codon_usage", {}) or {}
    if not isinstance(codon_usage, dict):
        codon_usage = {}
    zbar = float(codon_usage.get("zbar", float("nan")))
    ubar = float(codon_usage.get("ubar", float("nan")))
    null = codon_usage.get("null", {}) or {}
    if not isinstance(null, dict):
        null = {}

    # Z-spectrum fingerprint.
    zfp = summary.get("zspectrum_metrics", {}) or {}
    if not isinstance(zfp, dict):
        zfp = {}

    # ---- LaTeX fragments (same filenames as the single-pass script) ----
    stop_total = int(sum(term_stop_counts.values()))
    uaa = int(term_stop_counts.get("UAA", 0))
    uag = int(term_stop_counts.get("UAG", 0))
    uga = int(term_stop_counts.get("UGA", 0))

    s = []
    s.append(
        "On the human RefSeq mRNA corpus (best-ORF per transcript, $\\mu^\\ast$), "
        f"we analyzed $n={records_with_orf}$ transcripts with a detected ORF (out of $n={records}$ records). "
        f"The terminal stop distribution is $\\mathrm{{UAA}}:{uaa}$, $\\mathrm{{UAG}}:{uag}$, $\\mathrm{{UGA}}:{uga}$ "
        f"(total {stop_total}); the boundary-stop rate is {term_stop_boundary_count}/{stop_total}. "
        f"Across coding tokens (excluding terminal stops), the boundary rate is $\\widehat{{p}}_B={boundary_rate:.4f}$. "
        f"ORF length (codons, excluding stop): mean {mean_orf:.1f}, median {median_orf:.0f}, "
        f"IQR [{p25_orf:.0f},{p75_orf:.0f}]."
    )
    write_text(generated_dir() / "refseq_transcriptome_summary.tex", "\n".join(s) + "\n")

    rows = []
    for codon in STOP_CODONS:
        c = int(term_stop_counts.get(codon, 0))
        frac = (c / float(stop_total)) if stop_total else 0.0
        rows.append(f"{codon} & {c} & {frac:.4f} \\\\")
    write_text(generated_dir() / "refseq_termination_stop_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")

    rows2 = []
    for codon in STOP_CODONS:
        n = int(before_stats[codon].n)
        bm = float(before_stats[codon].mean) if n else float("nan")
        am = float(after_stats[codon].mean) if n else float("nan")
        rows2.append(f"{codon} & {k_primary} & {n} & {bm:.4f} & {am:.4f} \\\\")
    write_text(generated_dir() / "refseq_stop_context_rows.tex", "\n".join(rows2) + "\n\\bottomrule\n")

    # Start-context (AUG) row at primary k.
    if start_before_stats_mk and start_after_stats_mk:
        sb = start_before_stats_mk[int(k_primary)]
        sa = start_after_stats_mk[int(k_primary)]
        nb = int(sb.n)
        na = int(sa.n)
        bm = float(sb.mean) if nb else float("nan")
        am = float(sa.mean) if na else float("nan")
        row_start = [f"AUG & {k_primary} & {nb} & {bm:.4f} & {na} & {am:.4f} \\\\"]
        write_text(generated_dir() / "refseq_start_context_rows.tex", "\n".join(row_start) + "\n\\bottomrule\n")

    tests_lines = []
    tests_lines.append(
        "Welch tests (two-sided) for stop-context window means (window radius "
        f"$k={k_primary}$) across terminal stops in the RefSeq corpus."
    )
    op, val = _fmt_p_tex(p_before.get("UAA_vs_UAG"))
    op2, val2 = _fmt_p_tex(p_before.get("UAA_vs_UGA"))
    op3, val3 = _fmt_p_tex(p_before.get("UAG_vs_UGA"))
    tests_lines.append(
        "Before-window: "
        f"$p(\\mathrm{{UAA}}\\!\\neq\\!\\mathrm{{UAG}}){op}{val}$, "
        f"$p(\\mathrm{{UAA}}\\!\\neq\\!\\mathrm{{UGA}}){op2}{val2}$, "
        f"$p(\\mathrm{{UAG}}\\!\\neq\\!\\mathrm{{UGA}}){op3}{val3}$."
    )
    op, val = _fmt_p_tex(p_after.get("UAA_vs_UAG"))
    op2, val2 = _fmt_p_tex(p_after.get("UAA_vs_UGA"))
    op3, val3 = _fmt_p_tex(p_after.get("UAG_vs_UGA"))
    tests_lines.append(
        "After-window: "
        f"$p(\\mathrm{{UAA}}\\!\\neq\\!\\mathrm{{UAG}}){op}{val}$, "
        f"$p(\\mathrm{{UAA}}\\!\\neq\\!\\mathrm{{UGA}}){op2}{val2}$, "
        f"$p(\\mathrm{{UAG}}\\!\\neq\\!\\mathrm{{UGA}}){op3}{val3}$."
    )
    write_text(generated_dir() / "refseq_stop_context_tests.tex", " ".join(tests_lines) + "\n")

    # ---- Stop-context candidate sets for reporter assays (from merged summary) ----
    cand = summary.get("stop_context_candidates")
    cand_coding = summary.get("stop_context_candidates_coding")
    bundles: list[tuple[str, dict[str, object]]] = []
    if isinstance(cand, dict) and cand:
        bundles.append(("refseq_stop_context_candidates", cand))
    if isinstance(cand_coding, dict) and cand_coding:
        bundles.append(("refseq_stop_context_candidates_coding", cand_coding))

    if bundles:
        try:
            out_rows: list[dict[str, object]] = []

            def _emit_candidate_set(cand_obj: dict[str, object], *, stem: str) -> None:
                k_cand = int(cand_obj.get("k", k_primary) or k_primary)
                cand_set = str(cand_obj.get("candidate_set") or "reporter_v1")
                by_stop = cand_obj.get("by_stop") or {}
                if not isinstance(by_stop, dict):
                    by_stop = {}
                matched_after = cand_obj.get("matched_after") or {}
                if not isinstance(matched_after, dict):
                    matched_after = {}

                # Candidate table.
                lines: list[str] = []
                title = "Stop-context candidate sets for reporter assays"
                if stem.endswith("_coding"):
                    title = "Protein-coding stop-context candidate sets for reporter assays (NM/XM)"
                lines.append(f"{title}.")
                lines.append("")
                cand_tt = str(cand_set).replace("_", "\\_\\allowbreak{}")
                lines.append(f"Candidate set: \\texttt{{{cand_tt}}}; $k={int(k_cand)}$.")
                lines.append("Sequences are DNA (U$\\mapsto$T).")
                lines.append("")
                def _emit_rows(stop: str, group: str, rows: list[dict[str, object]]) -> None:
                    for j, r in enumerate(rows, start=1):
                        rec = str(r.get("record_id") or "-")
                        pos1 = int(r.get("stop_base", 0) or 0) + 1
                        before_seq = str(r.get("before_seq_dna") or "-")
                        stop_dna = str(r.get("stop_codon_dna") or "-")
                        after_seq = str(r.get("after_seq_dna") or "-")
                        b = r.get("before_mean")
                        a = r.get("after_mean")
                        d = r.get("diff")
                        plus4 = str(r.get("plus4_nt") or "-")
                        nt6 = str(r.get("after_nt6") or "-")
                        b_s = f"{float(b):.3f}" if b is not None else "-"
                        a_s = f"{float(a):.3f}" if a is not None else "-"
                        d_s = f"{float(d):+.3f}" if d is not None else "-"
                        lines.append(
                            f"{stop} & {group} & {j} & {pos1} & \\path{{{rec}}} & "
                            f"\\texttt{{{before_seq}}} & \\texttt{{{stop_dna}}} & \\texttt{{{after_seq}}} & "
                            f"{b_s} & {a_s} & {d_s} & \\texttt{{{plus4}}} & \\texttt{{{nt6}}} \\\\"
                        )

                def _emit_table(stop: str, *, high_rows: list[dict[str, object]], low_rows: list[dict[str, object]]) -> None:
                    lines.append("\\begin{center}")
                    lines.append("\\scriptsize")
                    lines.append("\\setlength{\\tabcolsep}{3pt}")
                    lines.append("\\renewcommand{\\arraystretch}{1.10}")
                    lines.append("\\resizebox{\\textwidth}{!}{%")
                    lines.append("\\begin{tabular}{lllrllllrrrll}")
                    lines.append("\\toprule")
                    lines.append(
                        "stop & group & rank & pos (1-based) & record & before seq & stop & after seq & "
                        "$\\overline{U}_{\\mathrm{before}}$ & $\\overline{U}_{\\mathrm{after}}$ & diff & +4 & after-nt6 \\\\"
                    )
                    lines.append("\\midrule")
                    if high_rows:
                        _emit_rows(stop, "high", high_rows)
                    if low_rows:
                        _emit_rows(stop, "low", low_rows)
                    lines.append("\\bottomrule")
                    lines.append("\\end{tabular}%")
                    lines.append("}")
                    lines.append("\\end{center}")

                first = True
                for stop in STOP_CODONS:
                    entry = by_stop.get(stop) or {}
                    if not isinstance(entry, dict):
                        continue
                    high_rows = [r for r in (entry.get("high_after") or []) if isinstance(r, dict)]
                    low_rows = [r for r in (entry.get("low_after") or []) if isinstance(r, dict)]
                    if not high_rows and not low_rows:
                        continue
                    if not first:
                        lines.append("\\medskip")
                    first = False
                    lines.append(f"\\noindent\\textbf{{$\\mathrm{{{stop}}}$}}")
                    _emit_table(stop, high_rows=high_rows, low_rows=low_rows)

                if first:
                    lines.append("Stop-context candidate sets unavailable.")
                write_text(generated_dir() / f"{stem}.tex", "\n".join(lines) + "\n")

                # Matched pairs (after-window GC + dinuc).
                m_lines: list[str] = []
                m_lines.append("Composition-matched high/low candidate pairs using after-window GC+dinucleotide.")
                cand_tt2 = str(cand_set).replace("_", "\\_\\allowbreak{}")
                m_lines.append(f"Candidate set: \\texttt{{{cand_tt2}}}; $k={int(k_cand)}$.")
                m_lines.append("")
                m_lines.append("\\begin{center}")
                m_lines.append("\\scriptsize")
                m_lines.append("\\setlength{\\tabcolsep}{3pt}")
                m_lines.append("\\renewcommand{\\arraystretch}{1.10}")
                m_lines.append("\\resizebox{\\textwidth}{!}{%")
                m_lines.append("\\begin{tabular}{lrrllrrllrrr}")
                m_lines.append("\\toprule")
                m_lines.append(
                    "stop & rank & pos$_H$ & record$_H$ & after-nt6$_H$ & $\\overline{U}_{\\mathrm{after},H}$ & "
                    "pos$_L$ & record$_L$ & after-nt6$_L$ & $\\overline{U}_{\\mathrm{after},L}$ & "
                    "$\\epsilon_{GC}$ & $\\ell_1$ \\\\"
                )
                m_lines.append("\\midrule")
                for stop in STOP_CODONS:
                    pairs = matched_after.get(stop) or []
                    if not isinstance(pairs, list):
                        continue
                    for p in pairs:
                        if not isinstance(p, dict):
                            continue
                        h = p.get("high") or {}
                        l = p.get("low") or {}
                        if not isinstance(h, dict) or not isinstance(l, dict):
                            continue
                        rank = int(p.get("rank", 0) or 0)
                        eps_used = p.get("eps_used")
                        l1 = p.get("l1")

                        pos_h = int(h.get("stop_base", 0) or 0) + 1
                        rec_h = str(h.get("record_id") or "-")
                        nt6_h = str(h.get("after_nt6") or "-")
                        ua_h = h.get("after_mean")
                        ua_h_s = f"{float(ua_h):.3f}" if ua_h is not None else "-"

                        pos_l = int(l.get("stop_base", 0) or 0) + 1
                        rec_l = str(l.get("record_id") or "-")
                        nt6_l = str(l.get("after_nt6") or "-")
                        ua_l = l.get("after_mean")
                        ua_l_s = f"{float(ua_l):.3f}" if ua_l is not None else "-"

                        eps_s = f"{float(eps_used):.2f}" if eps_used is not None else "-"
                        l1_s = f"{float(l1):.3f}" if l1 is not None else "-"
                        m_lines.append(
                            f"{stop} & {rank} & {pos_h} & \\path{{{rec_h}}} & \\texttt{{{nt6_h}}} & {ua_h_s} & "
                            f"{pos_l} & \\path{{{rec_l}}} & \\texttt{{{nt6_l}}} & {ua_l_s} & {eps_s} & {l1_s} \\\\"
                        )
                m_lines.append("\\bottomrule")
                m_lines.append("\\end{tabular}%")
                m_lines.append("}")
                m_lines.append("\\end{center}")
                write_text(generated_dir() / f"{stem}_matched.tex", "\n".join(m_lines) + "\n")

                # ---- Candidate summary stats (plus4 / motifs / prefixes) ----
                stat_lines: list[str] = []
                stat_lines.append(f"Candidate summary statistics (candidate set \\path{{{cand_set}}}, window radius $k={int(k_cand)}$).")

                def _plus4_counts(rows: list[dict[str, object]]) -> Counter[str]:
                    c: Counter[str] = Counter()
                    for r in rows:
                        v = r.get("plus4_nt")
                        if not isinstance(v, str) or not v:
                            continue
                        c[str(v)] += 1
                    return c

                def _top_nt6(rows: list[dict[str, object]], *, top_k: int = 5) -> list[tuple[str, int]]:
                    c: Counter[str] = Counter()
                    for r in rows:
                        v = r.get("after_nt6")
                        if not isinstance(v, str) or not v:
                            continue
                        c[str(v)] += 1
                    return c.most_common(int(top_k))

                def _prefix_counts(rows: list[dict[str, object]]) -> Counter[str]:
                    c: Counter[str] = Counter()
                    for r in rows:
                        rid = r.get("record_id")
                        if not isinstance(rid, str) or not rid:
                            continue
                        prefix = rid.split("_", 1)[0] if "_" in rid else rid[:2]
                        c[str(prefix)] += 1
                    return c

                for stop in STOP_CODONS:
                    entry = by_stop.get(stop) or {}
                    if not isinstance(entry, dict):
                        continue
                    high = entry.get("high_after") if isinstance(entry.get("high_after"), list) else []
                    low = entry.get("low_after") if isinstance(entry.get("low_after"), list) else []
                    high_rows = [r for r in high if isinstance(r, dict)]
                    low_rows = [r for r in low if isinstance(r, dict)]

                    c_hi = _plus4_counts(high_rows)
                    c_lo = _plus4_counts(low_rows)
                    hi_s = ", ".join(f"\\texttt{{{k}}}:{v}" for k, v in c_hi.most_common()) if c_hi else "NA"
                    lo_s = ", ".join(f"\\texttt{{{k}}}:{v}" for k, v in c_lo.most_common()) if c_lo else "NA"
                    top_hi = _top_nt6(high_rows, top_k=5)
                    top_lo = _top_nt6(low_rows, top_k=5)
                    top_hi_s = ", ".join(f"\\texttt{{{k}}}:{v}" for k, v in top_hi) if top_hi else "NA"
                    top_lo_s = ", ".join(f"\\texttt{{{k}}}:{v}" for k, v in top_lo) if top_lo else "NA"

                    p_hi = _prefix_counts(high_rows)
                    p_lo = _prefix_counts(low_rows)
                    p_hi_s = ", ".join(f"\\texttt{{{k}}}:{v}" for k, v in p_hi.most_common()) if p_hi else "NA"
                    p_lo_s = ", ".join(f"\\texttt{{{k}}}:{v}" for k, v in p_lo.most_common()) if p_lo else "NA"

                    stat_lines.append(
                        f"{stop}: high-after ($n={len(high_rows)}$) id-prefix: {p_hi_s}. +4 counts: {hi_s}. Top after-nt6: {top_hi_s}."
                    )
                    stat_lines.append(
                        f"{stop}: low-after ($n={len(low_rows)}$) id-prefix: {p_lo_s}. +4 counts: {lo_s}. Top after-nt6: {top_lo_s}."
                    )

                write_text(generated_dir() / f"{stem}_stats.tex", "\n\n".join(stat_lines) + "\n")

                # ---- Matched-pair effect summary ----
                matched_stats: list[str] = []
                matched_stats.append(
                    f"Matched-pair summaries (after-window GC+dinucleotide matching, candidate set \\path{{{cand_set}}}, $k={int(k_cand)}$)."
                )
                for stop in STOP_CODONS:
                    pairs = matched_after.get(stop) or []
                    if not isinstance(pairs, list):
                        continue
                    diffs: list[float] = []
                    for p in pairs:
                        if not isinstance(p, dict):
                            continue
                        h = p.get("high") or {}
                        l = p.get("low") or {}
                        if not isinstance(h, dict) or not isinstance(l, dict):
                            continue
                        ah = h.get("after_mean")
                        al = l.get("after_mean")
                        if ah is None or al is None:
                            continue
                        try:
                            diffs.append(float(ah) - float(al))
                        except Exception:
                            continue
                    if not diffs:
                        continue
                    diffs.sort()
                    n = len(diffs)
                    mean = sum(diffs) / float(n)
                    med = diffs[n // 2] if (n % 2 == 1) else 0.5 * (diffs[n // 2 - 1] + diffs[n // 2])
                    matched_stats.append(
                        f"{stop}: matched pairs $n={n}$, mean $\\Delta\\overline{{U}}_{{\\mathrm{{after}}}}={mean:+.3f}$, median {med:+.3f}."
                    )
                write_text(generated_dir() / f"{stem}_matched_stats.tex", "\n\n".join(matched_stats) + "\n")

                # JSONL export rows for Supabase import / downstream selection.
                for stop in STOP_CODONS:
                    entry = by_stop.get(stop) or {}
                    if not isinstance(entry, dict):
                        continue
                    for group_key in ("high_after", "low_after", "high_diff", "low_diff"):
                        lst = entry.get(group_key) or []
                        if not isinstance(lst, list):
                            continue
                        for rank, r in enumerate(lst, start=1):
                            if not isinstance(r, dict):
                                continue
                            out_rows.append(
                                {
                                    "dataset": "human_refseq_mrna",
                                    "analysis_version": int(ANALYSIS_VERSION),
                                    "candidate_set": str(cand_set),
                                    "k": int(k_cand),
                                    "stop_codon": str(stop),
                                    "group_label": str(group_key),
                                    "rank": int(rank),
                                    "record_id": r.get("record_id"),
                                    "frame": r.get("frame"),
                                    "start_base": r.get("start_base"),
                                    "stop_base": r.get("stop_base"),
                                    "before_seq_dna": r.get("before_seq_dna"),
                                    "stop_codon_dna": r.get("stop_codon_dna"),
                                    "after_seq_dna": r.get("after_seq_dna"),
                                    "plus4_nt": r.get("plus4_nt"),
                                    "after_nt6": r.get("after_nt6"),
                                    "before_mean_delta": r.get("before_mean"),
                                    "after_mean_delta": r.get("after_mean"),
                                    "diff": r.get("diff"),
                                    "before_gc": r.get("before_gc"),
                                    "after_gc": r.get("after_gc"),
                                    "before_dinuc": r.get("before_dinuc"),
                                    "after_dinuc": r.get("after_dinuc"),
                                    "payload": r,
                                }
                            )
                    # Matched pairs -> two rows per pair (high/low), with match metadata in payload.
                    pairs = matched_after.get(stop) or []
                    if isinstance(pairs, list):
                        for p in pairs:
                            if not isinstance(p, dict):
                                continue
                            rank = int(p.get("rank", 0) or 0)
                            eps_used = p.get("eps_used")
                            l1 = p.get("l1")
                            h = p.get("high") or {}
                            l = p.get("low") or {}
                            if isinstance(h, dict):
                                payload_h = dict(h)
                                payload_h["match"] = {"eps_used": eps_used, "l1": l1, "role": "high"}
                                out_rows.append(
                                    {
                                        "dataset": "human_refseq_mrna",
                                        "analysis_version": int(ANALYSIS_VERSION),
                                        "candidate_set": str(cand_set),
                                        "k": int(k_cand),
                                        "stop_codon": str(stop),
                                        "group_label": "matched_after_high",
                                        "rank": int(rank),
                                        "record_id": h.get("record_id"),
                                        "frame": h.get("frame"),
                                        "start_base": h.get("start_base"),
                                        "stop_base": h.get("stop_base"),
                                        "before_seq_dna": h.get("before_seq_dna"),
                                        "stop_codon_dna": h.get("stop_codon_dna"),
                                        "after_seq_dna": h.get("after_seq_dna"),
                                        "plus4_nt": h.get("plus4_nt"),
                                        "after_nt6": h.get("after_nt6"),
                                        "before_mean_delta": h.get("before_mean"),
                                        "after_mean_delta": h.get("after_mean"),
                                        "diff": h.get("diff"),
                                        "before_gc": h.get("before_gc"),
                                        "after_gc": h.get("after_gc"),
                                        "before_dinuc": h.get("before_dinuc"),
                                        "after_dinuc": h.get("after_dinuc"),
                                        "payload": payload_h,
                                    }
                                )
                            if isinstance(l, dict):
                                payload_l = dict(l)
                                payload_l["match"] = {"eps_used": eps_used, "l1": l1, "role": "low"}
                                out_rows.append(
                                    {
                                        "dataset": "human_refseq_mrna",
                                        "analysis_version": int(ANALYSIS_VERSION),
                                        "candidate_set": str(cand_set),
                                        "k": int(k_cand),
                                        "stop_codon": str(stop),
                                        "group_label": "matched_after_low",
                                        "rank": int(rank),
                                        "record_id": l.get("record_id"),
                                        "frame": l.get("frame"),
                                        "start_base": l.get("start_base"),
                                        "stop_base": l.get("stop_base"),
                                        "before_seq_dna": l.get("before_seq_dna"),
                                        "stop_codon_dna": l.get("stop_codon_dna"),
                                        "after_seq_dna": l.get("after_seq_dna"),
                                        "plus4_nt": l.get("plus4_nt"),
                                        "after_nt6": l.get("after_nt6"),
                                        "before_mean_delta": l.get("before_mean"),
                                        "after_mean_delta": l.get("after_mean"),
                                        "diff": l.get("diff"),
                                        "before_gc": l.get("before_gc"),
                                        "after_gc": l.get("after_gc"),
                                        "before_dinuc": l.get("before_dinuc"),
                                        "after_dinuc": l.get("after_dinuc"),
                                        "payload": payload_l,
                                    }
                                )

            for stem, cand_obj in bundles:
                _emit_candidate_set(cand_obj, stem=stem)

            # Write combined JSONL export once (covers all candidate_set labels found in the merged summary).
            out_jsonl = root_dir() / "data" / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"
            out_jsonl.parent.mkdir(parents=True, exist_ok=True)
            out_rows.sort(
                key=lambda r: (
                    str(r.get("candidate_set") or ""),
                    str(r.get("stop_codon") or ""),
                    str(r.get("group_label") or ""),
                    int(r.get("rank") or 0),
                    str(r.get("record_id") or ""),
                    int(r.get("stop_base") or 0),
                )
            )
            with out_jsonl.open("w", encoding="utf-8") as f:
                for r in out_rows:
                    f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        except Exception:
            for stem, _ in bundles:
                write_text(generated_dir() / f"{stem}.tex", "Stop-context candidate sets unavailable.\n")
                write_text(generated_dir() / f"{stem}_matched.tex", "Stop-context candidate sets unavailable.\n")
                write_text(generated_dir() / f"{stem}_stats.tex", "Stop-context candidate sets unavailable.\n")
                write_text(generated_dir() / f"{stem}_matched_stats.tex", "Stop-context candidate sets unavailable.\n")
    else:
        # Back-compat: keep the original filenames present even when candidates are unavailable.
        write_text(generated_dir() / "refseq_stop_context_candidates.tex", "Stop-context candidate sets unavailable.\n")
        write_text(generated_dir() / "refseq_stop_context_candidates_matched.tex", "Stop-context candidate sets unavailable.\n")
        write_text(generated_dir() / "refseq_stop_context_candidates_stats.tex", "Stop-context candidate sets unavailable.\n")
        write_text(generated_dir() / "refseq_stop_context_candidates_matched_stats.tex", "Stop-context candidate sets unavailable.\n")

    op_pz, pz_s = _fmt_p_tex(float(null.get("p_zbar", float("nan"))))
    op_pu, pu_s = _fmt_p_tex(float(null.get("p_ubar", float("nan"))))
    null_s = (
        "Codon-usage summary over coding tokens (excluding terminal stops): "
        f"$\\overline{{Z}}={zbar:.4f}$, $\\overline{{U}}={ubar:.4f}$. "
        "Under an amino-acid preserving null (uniform choice among synonymous codons), "
        f"$\\mathbb{{E}}[\\overline{{Z}}]={float(null.get('null_mu_zbar', float('nan'))):.4f}$ with "
        f"$\\mathrm{{sd}}={float(null.get('null_sd_zbar', float('nan'))):.6f}$ "
        f"($z={float(null.get('z_zbar', float('nan'))):.2f}$, $p{op_pz}{pz_s}$), and "
        f"$\\mathbb{{E}}[\\overline{{U}}]={float(null.get('null_mu_ubar', float('nan'))):.4f}$ with "
        f"$\\mathrm{{sd}}={float(null.get('null_sd_ubar', float('nan'))):.6f}$ "
        f"($z={float(null.get('z_ubar', float('nan'))):.2f}$, $p{op_pu}{pu_s}$)."
    )
    write_text(generated_dir() / "refseq_codon_usage_null.tex", null_s + "\n")

    # ---- Multi-k table (means only) ----
    mk_lines = []
    mk_lines.append("\\begin{center}")
    mk_lines.append("\\small")
    mk_lines.append("\\setlength{\\tabcolsep}{6pt}")
    mk_lines.append("\\renewcommand{\\arraystretch}{1.15}")
    mk_lines.append("\\begin{tabular}{lrrrr}")
    mk_lines.append("\\toprule")
    mk_lines.append("stop codon & $k$ & $n$ & $\\overline{U}_{\\mathrm{before}}$ & $\\overline{U}_{\\mathrm{after}}$ \\\\")
    mk_lines.append("\\midrule")
    for kk in k_list:
        for codon in STOP_CODONS:
            bs = before_stats_mk[codon][int(kk)]
            a_s = after_stats_mk[codon][int(kk)]
            n = int(bs.n)
            bm = float(bs.mean) if n else float("nan")
            am = float(a_s.mean) if n else float("nan")
            mk_lines.append(f"{codon} & {int(kk)} & {n} & {bm:.4f} & {am:.4f} \\\\")
    mk_lines.append("\\bottomrule")
    mk_lines.append("\\end{tabular}")
    mk_lines.append("\\end{center}")
    write_text(generated_dir() / "refseq_stop_context_multi_k_table.tex", "\n".join(mk_lines) + "\n")

    # ---- Start-context multi-k table (means only) ----
    if start_before_stats_mk and start_after_stats_mk:
        mk2 = []
        mk2.append("\\begin{center}")
        mk2.append("\\small")
        mk2.append("\\setlength{\\tabcolsep}{6pt}")
        mk2.append("\\renewcommand{\\arraystretch}{1.15}")
        mk2.append("\\begin{tabular}{lrrrrr}")
        mk2.append("\\toprule")
        mk2.append("start codon & $k$ & $n_{\\mathrm{before}}$ & $\\overline{U}_{\\mathrm{before}}$ & $n_{\\mathrm{after}}$ & $\\overline{U}_{\\mathrm{after}}$ \\\\")
        mk2.append("\\midrule")
        for kk in k_list:
            sb = start_before_stats_mk[int(kk)]
            sa = start_after_stats_mk[int(kk)]
            nb = int(sb.n)
            na = int(sa.n)
            bm = float(sb.mean) if nb else float("nan")
            am = float(sa.mean) if na else float("nan")
            mk2.append(f"AUG & {int(kk)} & {nb} & {bm:.4f} & {na} & {am:.4f} \\\\")
        mk2.append("\\bottomrule")
        mk2.append("\\end{tabular}")
        mk2.append("\\end{center}")
        write_text(generated_dir() / "refseq_start_context_multi_k_table.tex", "\n".join(mk2) + "\n")

    # ---- Pairwise effects across multi-k ----
    tests = []
    pairs = [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]
    for kk in k_list:
        kk_i = int(kk)
        for window in ("before", "after"):
            for a, b in pairs:
                sa = (before_stats_mk[a][kk_i] if window == "before" else after_stats_mk[a][kk_i])
                sb = (before_stats_mk[b][kk_i] if window == "before" else after_stats_mk[b][kk_i])
                n1 = int(sa.n)
                n2 = int(sb.n)
                m1 = float(sa.mean)
                m2 = float(sb.mean)
                v1 = float(sa.sample_variance())
                v2 = float(sb.sample_variance())
                p = welch_t_p_value_two_sided_from_stats(sa, sb)
                ci = mean_diff_ci_normal_from_stats(n1=n1, mean1=m1, var1=v1, n2=n2, mean2=m2, var2=v2)
                d = cohen_d_from_stats(n1=n1, mean1=m1, var1=v1, n2=n2, mean2=m2, var2=v2)
                g = hedges_g_from_stats(n1=n1, mean1=m1, var1=v1, n2=n2, mean2=m2, var2=v2)
                tests.append(
                    {
                        "window": window,
                        "k": kk_i,
                        "pair": f"{a}_vs_{b}",
                        "n1": n1,
                        "n2": n2,
                        "mean1": m1,
                        "mean2": m2,
                        "diff": (m1 - m2),
                        "ci_low": (ci[0] if ci else None),
                        "ci_high": (ci[1] if ci else None),
                        "d": d,
                        "g": g,
                        "p": p,
                        "q": None,
                    }
                )

    pvals = []
    idx_map = []
    for i, t in enumerate(tests):
        if t["p"] is None:
            continue
        pvals.append(float(t["p"]))
        idx_map.append(i)
    qvals = bh_fdr(pvals)
    for j, i in enumerate(idx_map):
        tests[i]["q"] = float(qvals[j])

    eff_lines = []
    eff_lines.append("\\begin{center}")
    eff_lines.append("\\scriptsize")
    eff_lines.append("\\setlength{\\tabcolsep}{4pt}")
    eff_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    eff_lines.append("\\resizebox{\\textwidth}{!}{%")
    eff_lines.append("\\begin{tabular}{lrrrlrrrlrrl}")
    eff_lines.append("\\toprule")
    eff_lines.append(
        "window & $k$ & $n_1$ & $n_2$ & pair & $\\bar{U}_1$ & $\\bar{U}_2$ & diff & CI$_{95\\%}$ & $d$ & $g$ & $p$/$q$ \\\\"
    )
    eff_lines.append("\\midrule")
    for t in tests:
        window = "before" if t["window"] == "before" else "after"
        kk_i = int(t["k"])
        n1 = int(t["n1"])
        n2 = int(t["n2"])
        pair = str(t["pair"]).replace("_vs_", "$\\,$vs$\\,$")
        m1 = float(t["mean1"])
        m2 = float(t["mean2"])
        diff = float(t["diff"])
        ci_low = t["ci_low"]
        ci_high = t["ci_high"]
        ci_s = "NA"
        if (ci_low is not None) and (ci_high is not None):
            ci_s = f"[{float(ci_low):.4f}, {float(ci_high):.4f}]"
        d_s = f"{float(t['d']):+.3f}" if t["d"] is not None else "NA"
        g_s = f"{float(t['g']):+.3f}" if t["g"] is not None else "NA"
        op_p, p_s = _fmt_p_tex(t["p"])
        op_q, q_s = _fmt_p_tex(t["q"])
        # Wrap p/q values in math mode so expressions like 10^{-300} are valid TeX.
        pq = f"${op_p}{p_s}$/${op_q}{q_s}$"
        eff_lines.append(
            f"{window} & {kk_i} & {n1} & {n2} & {pair} & {m1:.4f} & {m2:.4f} & {diff:+.4f} & {ci_s} & {d_s} & {g_s} & {pq} \\\\"
        )
    eff_lines.append("\\bottomrule")
    eff_lines.append("\\end{tabular}%")
    eff_lines.append("}")
    eff_lines.append("\\end{center}")
    write_text(generated_dir() / "refseq_stop_context_effects_table.tex", "\n".join(eff_lines) + "\n")

    # ---- Stop-context response curve fit: D(s;k) = U_after(s;k) - U_before(s;k) ----
    fit_rows: list[str] = []
    fit_rows.append("\\begin{center}")
    fit_rows.append("\\small")
    fit_rows.append("\\setlength{\\tabcolsep}{6pt}")
    fit_rows.append("\\renewcommand{\\arraystretch}{1.15}")
    fit_rows.append("\\begin{tabular}{lrrrr}")
    fit_rows.append("\\toprule")
    fit_rows.append("stop & points & $D_{\\infty}$ & $\\kappa$ & $R^2$ \\\\")
    fit_rows.append("\\midrule")

    for s0 in STOP_CODONS:
        ks_fit: list[int] = []
        ys_fit: list[float] = []
        for kk in k_list:
            bs = before_stats_mk[str(s0)][int(kk)]
            a_s = after_stats_mk[str(s0)][int(kk)]
            if int(bs.n) <= 0 or int(a_s.n) <= 0:
                continue
            ys_fit.append(float(a_s.mean) - float(bs.mean))
            ks_fit.append(int(kk))
        fit = _fit_saturating_exp(ks_fit, ys_fit)
        if fit is None:
            fit_rows.append(f"{s0} & {len(ks_fit)} & - & - & - \\\\")
            continue
        fit_rows.append(
            f"{s0} & {int(fit['n'])} & {float(fit['d_inf']):.4f} & {float(fit['kappa']):.3f} & {float(fit['r2']):.4f} \\\\"
        )

    fit_rows.append("\\bottomrule")
    fit_rows.append("\\end{tabular}")
    fit_rows.append("\\end{center}")
    fit_note = (
        "Stop-context response fit using $D(s;k)=\\overline{U}_{\\mathrm{after}}(s;k)-\\overline{U}_{\\mathrm{before}}(s;k)$ "
        f"over $k\\in\\{{{', '.join(str(int(x)) for x in k_list)}\\}}$ (Appendix~\\ref{{app:stop_context_fit}})."
    )
    write_text(generated_dir() / "refseq_stop_context_response_fit.tex", fit_note + "\n" + "\n".join(fit_rows) + "\n")

    # ---- Composition-adjusted controls (stratified bins + NN sample cross-check) ----
    comp = summary.get("stop_context_composition")
    comp_lines: list[str] = []
    if not isinstance(comp, dict) or not comp:
        comp_lines.append("Composition-adjusted stop-context controls unavailable.")
    else:
        schemes = comp.get("schemes") or {}
        strat = comp.get("stratified") or {}
        nn = (comp.get("nn_samples") or {}).get("results") if isinstance(comp.get("nn_samples"), dict) else None
        pairs = ["UAA_vs_UAG", "UAA_vs_UGA", "UAG_vs_UGA"]
        if isinstance(schemes, dict) and isinstance(strat, dict):
            for sk in sorted(schemes.keys()):
                meta = schemes.get(sk) or {}
                x_name = str(meta.get("x_name") or "")
                sk_tex = str(sk).replace("_", "\\_")
                comp_lines.append(
                    f"Composition-adjusted stop-context comparisons (scheme {sk_tex}, GC$\\times${x_name}, primary $k={k_primary}$)."
                )
                for window in ("before", "after"):
                    w0 = strat.get(sk, {}).get(window, {}) if isinstance(strat.get(sk), dict) else {}
                    if not isinstance(w0, dict):
                        continue
                    for pair in pairs:
                        r = w0.get(pair) or {}
                        if not isinstance(r, dict):
                            continue
                        diff = r.get("diff")
                        p = r.get("p")
                        bins_used = int(r.get("bins_used", 0) or 0)
                        diff_s = f"{float(diff):+.4f}" if diff is not None else "NA"
                        op, p_s = _fmt_p_tex(p)
                        pair_tex = pair.replace("_vs_", "$\\,$vs$\\,$")
                        comp_lines.append(
                            f"Stratified ({window}-window): {pair_tex} diff {diff_s} (bins {bins_used}, $p{op}{p_s}$)."
                        )
        if isinstance(nn, dict):
            comp_lines.append("GC+dinuc nearest-neighbor matching on bounded reservoirs (cross-check).")
            for window in ("before", "after"):
                w0 = nn.get(window, {}) or {}
                if not isinstance(w0, dict):
                    continue
                for pair in pairs:
                    r = w0.get(pair) or {}
                    if not isinstance(r, dict):
                        continue
                    diff = r.get("mean_diff")
                    p = r.get("p")
                    n = int(r.get("n", 0) or 0)
                    diff_s = f"{float(diff):+.4f}" if diff is not None else "NA"
                    op, p_s = _fmt_p_tex(p)
                    pair_tex = pair.replace("_vs_", "$\\,$vs$\\,$")
                    comp_lines.append(
                        f"NN ({window}-window): {pair_tex} diff {diff_s} (n={n}, $p{op}{p_s}$)."
                    )
    write_text(generated_dir() / "refseq_stop_context_composition_controls.tex", "\n\n".join(comp_lines) + "\n")

    out_tsv = root_dir() / "data" / "refseq_hsapiens_mrna" / "stop_context_pairwise_effects.tsv"
    tsv_rows = []
    for t in tests:
        tsv_rows.append(
            [
                t["window"],
                t["k"],
                t["pair"],
                t["n1"],
                t["n2"],
                f"{float(t['mean1']):.10f}",
                f"{float(t['mean2']):.10f}",
                f"{float(t['diff']):.10f}",
                ("" if t["ci_low"] is None else f"{float(t['ci_low']):.10f}"),
                ("" if t["ci_high"] is None else f"{float(t['ci_high']):.10f}"),
                ("" if t["d"] is None else f"{float(t['d']):.10f}"),
                ("" if t["g"] is None else f"{float(t['g']):.10f}"),
                ("" if t["p"] is None else f"{float(t['p']):.16g}"),
                ("" if t["q"] is None else f"{float(t['q']):.16g}"),
            ]
        )
    _write_tsv(
        out_tsv,
        [
            "window",
            "k",
            "pair",
            "n1",
            "n2",
            "mean1",
            "mean2",
            "diff",
            "ci_low",
            "ci_high",
            "cohen_d",
            "hedges_g",
            "p_welch",
            "q_bh",
        ],
        tsv_rows,
    )

    # ---- Codon-usage null decomposition (AA + codon contributions) ----
    codons_by_aa = amino_acid_codons()
    codon_delta = {}
    codon_v = {}
    for codon in GENETIC_CODE:
        f = fold_codon(codon, MU_STAR)
        codon_delta[codon] = float(f.delta)
        codon_v[codon] = float(f.v)

    aa_counts_i = {str(a): int(v) for a, v in aa_counts.items()}
    codon_counts_i = {str(c): int(v) for c, v in codon_counts.items()}

    decomp_u = aa_preserving_null_decomposition(
        aa_counts=aa_counts_i,
        codon_counts=codon_counts_i,
        codons_by_aa=codons_by_aa,
        genetic_code=GENETIC_CODE,
        codon_value=codon_delta,
        exclude_aas={"Stop"},
    )
    decomp_z = aa_preserving_null_decomposition(
        aa_counts=aa_counts_i,
        codon_counts=codon_counts_i,
        codons_by_aa=codons_by_aa,
        genetic_code=GENETIC_CODE,
        codon_value=codon_v,
        exclude_aas={"Stop"},
    )

    out_u_aa = root_dir() / "data" / "refseq_hsapiens_mrna" / "codon_usage_null_decomp_U_aa.tsv"
    out_u_c = root_dir() / "data" / "refseq_hsapiens_mrna" / "codon_usage_null_decomp_U_codon.tsv"
    _write_tsv(
        out_u_aa,
        ["aa", "n", "obs_mean", "null_mean", "contrib"],
        [[x.aa, x.n, f"{x.obs_mean:.10f}", f"{x.null_mean:.10f}", f"{x.contrib:.10f}"] for x in decomp_u.aa_contribs],
    )
    _write_tsv(
        out_u_c,
        ["codon", "aa", "obs_count", "null_count", "contrib"],
        [
            [x.codon, x.aa, x.obs_count, f"{x.null_count:.10f}", f"{x.contrib:.10f}"]
            for x in decomp_u.codon_contribs
        ],
    )
    out_z_aa = root_dir() / "data" / "refseq_hsapiens_mrna" / "codon_usage_null_decomp_Z_aa.tsv"
    out_z_c = root_dir() / "data" / "refseq_hsapiens_mrna" / "codon_usage_null_decomp_Z_codon.tsv"
    _write_tsv(
        out_z_aa,
        ["aa", "n", "obs_mean", "null_mean", "contrib"],
        [[x.aa, x.n, f"{x.obs_mean:.10f}", f"{x.null_mean:.10f}", f"{x.contrib:.10f}"] for x in decomp_z.aa_contribs],
    )
    _write_tsv(
        out_z_c,
        ["codon", "aa", "obs_count", "null_count", "contrib"],
        [
            [x.codon, x.aa, x.obs_count, f"{x.null_count:.10f}", f"{x.contrib:.10f}"]
            for x in decomp_z.codon_contribs
        ],
    )

    TOP_AA = 10
    TOP_CODON = 20
    u_lines = []
    op_p_u, p_u_s = _fmt_p_tex(float(decomp_u.p_value))
    u_lines.append(
        "Amino-acid preserving null decomposition for $\\overline{U}$ (coding tokens, excluding terminal stops). "
        f"Observed $\\overline{{U}}={decomp_u.obs_mean:.4f}$ vs null $\\mathbb{{E}}[\\overline{{U}}]={decomp_u.null_mean:.4f}$ "
        f"($\\mathrm{{sd}}={decomp_u.null_sd:.6f}$, $z={decomp_u.z_score:.2f}$, $p{op_p_u}{p_u_s}$)."
    )
    u_lines.append("\\begin{center}")
    u_lines.append("\\scriptsize")
    u_lines.append("\\setlength{\\tabcolsep}{4pt}")
    u_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    u_lines.append("\\begin{tabular}{lrrrr}")
    u_lines.append("\\toprule")
    u_lines.append("AA & $n$ & $\\bar{U}_{\\mathrm{obs}}$ & $\\bar{U}_{\\mathrm{null}}$ & contrib \\\\")
    u_lines.append("\\midrule")
    for x in decomp_u.aa_contribs[:TOP_AA]:
        u_lines.append(f"{x.aa} & {x.n} & {x.obs_mean:.4f} & {x.null_mean:.4f} & {x.contrib:+.5f} \\\\")
    u_lines.append("\\bottomrule")
    u_lines.append("\\end{tabular}")
    u_lines.append("\\end{center}")
    u_lines.append("\\begin{center}")
    u_lines.append("\\scriptsize")
    u_lines.append("\\setlength{\\tabcolsep}{4pt}")
    u_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    u_lines.append("\\begin{tabular}{llrrr}")
    u_lines.append("\\toprule")
    u_lines.append("codon & AA & $c_{\\mathrm{obs}}$ & $c_{\\mathrm{null}}$ & contrib \\\\")
    u_lines.append("\\midrule")
    for x in decomp_u.codon_contribs[:TOP_CODON]:
        u_lines.append(f"{x.codon} & {x.aa} & {x.obs_count} & {x.null_count:.1f} & {x.contrib:+.5f} \\\\")
    u_lines.append("\\bottomrule")
    u_lines.append("\\end{tabular}")
    u_lines.append("\\end{center}")
    write_text(generated_dir() / "refseq_codon_usage_null_decomposition.tex", "\n".join(u_lines) + "\n")

    # Z-spectrum fingerprint metrics fragment.
    try:
        s_fp = (
            "\\begin{tabular}{@{}l@{}}\n"
            "Z-spectrum fingerprint metrics over best ORFs (excluding terminal stops):\\\\\n"
            f"boundary-rate mean {float((zfp.get('boundary_rate') or {}).get('mean')):.4f}, "
            f"median {float((zfp.get('boundary_rate') or {}).get('median')):.4f}\\\\\n"
            f"entropy $H(Z)$ mean {float((zfp.get('entropy_Z') or {}).get('mean')):.4f}, "
            f"median {float((zfp.get('entropy_Z') or {}).get('median')):.4f}\\\\\n"
            f"lag-1 autocorrelation $\\rho(Z_i,Z_{{i+1}})$ mean {float((zfp.get('autocorr_Z1') or {}).get('mean')):.4f}, "
            f"median {float((zfp.get('autocorr_Z1') or {}).get('median')):.4f} "
            f"(n={int(float((zfp.get('autocorr_Z1') or {}).get('n')))}).\n"
            "\\end{tabular}"
        )
    except Exception:
        s_fp = "\\begin{tabular}{@{}l@{}}Z-spectrum fingerprint metrics unavailable.\\end{tabular}"
    write_text(generated_dir() / "refseq_zspectrum_fingerprint.tex", s_fp + "\n")


def main() -> None:
    args = parse_args()
    in_dir = Path(args.in_dir)
    # Only include shard outputs (exclude *.meta.json sidecars and any other json without meta).
    files = []
    for fp in sorted(in_dir.glob("*.json")):
        if fp.name.endswith(".meta.json"):
            continue
        if not cache_meta_path(fp).exists():
            continue
        files.append(fp)
    if not files:
        raise SystemExit(f"No shard JSON files found in {in_dir}")

    # ---- Cache short-circuit ----
    out_json = Path(args.out_json)
    # Use shard meta digests when available (fast) to decide if merge can be skipped.
    shard_meta: list[dict[str, object]] = []
    for fp in files:
        mp = cache_meta_path(fp)
        if mp.exists():
            try:
                shard_meta.append(json.loads(mp.read_text(encoding="utf-8")))
            except Exception:
                shard_meta.append({"path": str(fp), "size": fp.stat().st_size})
        else:
            shard_meta.append({"path": str(fp), "size": fp.stat().st_size})
    merge_key = {
        "analysis": "refseq_transcriptome_merge",
        "merge_version": int(MERGE_VERSION),
        "analysis_version": ANALYSIS_VERSION,
        "in_dir": str(in_dir),
        "shards": shard_meta,
        "mu_star": MU_STAR,
        "candidate_limit": int(args.candidate_limit),
        "candidate_set": str(args.candidate_set),
        "candidate_set_coding": str(args.candidate_set_coding),
    }
    merge_meta = {"cache_key": merge_key, "cache_digest": cache_key_digest(merge_key)}
    if (not args.force) and cache_hit(out_json, expected_meta=merge_meta, require_meta=True):
        if not cache_meta_path(out_json).exists():
            write_json_atomic(cache_meta_path(out_json), merge_meta)
        print(f"[cache] hit: {out_json}")
        if args.no_latex:
            return
        try:
            summary_cached = json.loads(out_json.read_text(encoding="utf-8"))
        except Exception:
            summary_cached = None
        if isinstance(summary_cached, dict):
            _emit_outputs_from_summary(summary_cached)
            print("Wrote LaTeX fragments into:", generated_dir())
            write_json_atomic(cache_meta_path(out_json), merge_meta)
            return

    records = 0
    records_with_orf = 0
    total_nt = 0
    coding_tokens = 0
    boundary_token_count = 0

    orf_len_hist: Counter[int] = Counter()
    term_stop_counts: Counter[str] = Counter()
    term_stop_boundary_count = 0

    codon_counts: Counter[str] = Counter()
    aa_counts: Counter[str] = Counter()
    v_hist: Counter[int] = Counter()
    delta_hist: Counter[int] = Counter()

    before_stats_mk: dict[str, dict[int, RunningStats]] | None = None
    after_stats_mk: dict[str, dict[int, RunningStats]] | None = None
    before_stats: dict[str, RunningStats] = {}
    after_stats: dict[str, RunningStats] = {}
    start_before_stats_mk: dict[int, RunningStats] | None = None
    start_after_stats_mk: dict[int, RunningStats] | None = None
    k_primary_seen: int | None = None
    k_list_seen: list[int] | None = None

    # Z-spectrum fingerprint metrics samples (exact merge).
    br_samples: list[float] = []
    hz_samples: list[float] = []
    rho_samples: list[float] = []

    # Composition-adjusted stop-context merge (schema v3+).
    comp_schemes_seen: dict[str, dict[str, object]] = {}
    comp_before_merged: dict[str, dict[str, dict[str, RunningStats]]] = {}
    comp_after_merged: dict[str, dict[str, dict[str, RunningStats]]] = {}

    NN_SAMPLE_MAX_PER_STOP = 2000
    nn_seen: dict[str, int] = {s: 0 for s in STOP_CODONS}
    nn_samples: dict[str, list[dict[str, object]]] = {s: [] for s in STOP_CODONS}
    rng_nn = random.Random(_stable_seed_u32(f"refseq:merge:nn:{ANALYSIS_VERSION}:{MERGE_VERSION}"))

    # Candidate pools (merged from shard extrema) for reporter assay selection.
    cand_limit = max(1, int(args.candidate_limit))
    cand_set = str(args.candidate_set or "reporter_v1")
    cand_set_coding = str(args.candidate_set_coding or "reporter_coding_v1")
    CAND_POOL_MAX_PER_STOP = 1000
    cand_seen: dict[str, set[tuple[str, int, int]]] = {s: set() for s in STOP_CODONS}
    cand_top_after: dict[str, list[tuple[float, str, int, int, dict[str, object]]]] = {s: [] for s in STOP_CODONS}
    cand_bottom_after: dict[str, list[tuple[float, str, int, int, dict[str, object]]]] = {s: [] for s in STOP_CODONS}
    cand_top_diff: dict[str, list[tuple[float, str, int, int, dict[str, object]]]] = {s: [] for s in STOP_CODONS}
    cand_bottom_diff: dict[str, list[tuple[float, str, int, int, dict[str, object]]]] = {s: [] for s in STOP_CODONS}

    def _push_topk(
        heap: list[tuple[float, str, int, int, dict[str, object]]],
        *,
        score: float,
        rid: str,
        stop_base: int,
        frame: int,
        item: dict[str, object],
        limit: int,
    ) -> None:
        heapq.heappush(heap, (float(score), str(rid), int(stop_base), int(frame), item))
        if len(heap) > int(limit):
            heapq.heappop(heap)

    source_files: list[str] = []

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] refseq_transcriptome_merge")
    hb.force(f"start shards={len(files)} in_dir={in_dir.name}")

    for i, fp in enumerate(files, start=1):
        obj = json.loads(fp.read_text(encoding="utf-8"))
        shard_schema = int(obj.get("schema_version", 0) or 0)
        if shard_schema not in (1, 2, 3, 4, 5):
            raise SystemExit(f"Unexpected schema_version in {fp}: {shard_schema}")
        hb.maybe(f"merged_shards={i}/{len(files)} records={records} coding_tokens={coding_tokens}")

        # Stop-context k configuration (primary k + optional multi-k list).
        k_primary = int(obj.get("stop_window", 0) or 0)
        k_list_obj = obj.get("stop_window_list")
        k_list: list[int] = []
        if isinstance(k_list_obj, list):
            for x in k_list_obj:
                try:
                    k_list.append(int(x))
                except Exception:
                    continue

        # Back-compat: schema v1 does not carry stop_window fields; infer from stop_context.
        if k_primary <= 0:
            sc = obj.get("stop_context", {}) or {}
            for s in STOP_CODONS:
                if s in sc:
                    try:
                        k_primary = int(sc[s].get("k", 0) or 0)  # type: ignore[index]
                    except Exception:
                        k_primary = 0
                    break
        if k_primary <= 0:
            raise SystemExit(f"Missing stop-window k in shard: {fp}")
        if not k_list:
            k_list = [int(k_primary)]
        k_list = sorted({int(x) for x in k_list if int(x) >= 1} | {int(k_primary)})

        if k_primary_seen is None:
            k_primary_seen = int(k_primary)
            k_list_seen = [int(x) for x in k_list]
            before_stats_mk = {s: {kk: RunningStats() for kk in k_list_seen} for s in STOP_CODONS}
            after_stats_mk = {s: {kk: RunningStats() for kk in k_list_seen} for s in STOP_CODONS}
            before_stats = {s: before_stats_mk[s][int(k_primary_seen)] for s in STOP_CODONS}
            after_stats = {s: after_stats_mk[s][int(k_primary_seen)] for s in STOP_CODONS}
            start_before_stats_mk = {kk: RunningStats() for kk in k_list_seen}
            start_after_stats_mk = {kk: RunningStats() for kk in k_list_seen}
        else:
            assert k_list_seen is not None
            if int(k_primary) != int(k_primary_seen):
                raise SystemExit(f"Mismatched stop-window k across shards: {k_primary_seen} vs {k_primary} in {fp}")
            if [int(x) for x in k_list] != [int(x) for x in k_list_seen]:
                raise SystemExit(f"Mismatched stop-window k_list across shards in {fp}")

        source_files.extend([str(x) for x in obj.get("source_files", [])])
        records += int(obj.get("records", 0) or 0)
        records_with_orf += int(obj.get("records_with_orf", 0) or 0)
        total_nt += int(obj.get("total_nt", 0) or 0)
        coding_tokens += int(obj.get("coding_tokens", 0) or 0)
        boundary_token_count += int(obj.get("boundary_token_count", 0) or 0)

        term_stop_boundary_count += int(obj.get("termination_stop_boundary_count", 0) or 0)
        for c, v in (obj.get("termination_stop_counts", {}) or {}).items():
            term_stop_counts[str(c)] += int(v)

        for k, v in (obj.get("orf_len_hist", {}) or {}).items():
            orf_len_hist[int(k)] += int(v)

        for c, v in (obj.get("codon_counts", {}) or {}).items():
            codon_counts[str(c)] += int(v)
        for a, v in (obj.get("aa_counts", {}) or {}).items():
            aa_counts[str(a)] += int(v)
        for k, v in (obj.get("V_hist", {}) or {}).items():
            v_hist[int(k)] += int(v)
        for k, v in (obj.get("Delta_hist", {}) or {}).items():
            delta_hist[int(k)] += int(v)

        if before_stats_mk is None or after_stats_mk is None or k_list_seen is None or k_primary_seen is None:
            raise SystemExit("Internal error: stop-context structures not initialized")
        if start_before_stats_mk is None or start_after_stats_mk is None:
            raise SystemExit("Internal error: start-context structures not initialized")

        w_mk = obj.get("stop_context_welford_multi_k")
        if isinstance(w_mk, dict) and w_mk:
            # Preferred path: multi-k Welford stats (schema v2).
            for s in STOP_CODONS:
                sm = w_mk.get(s)
                if not isinstance(sm, dict):
                    raise SystemExit(f"Malformed stop_context_welford_multi_k for {s} in {fp}")
                for kk in k_list_seen:
                    entry = sm.get(str(int(kk)))
                    if not isinstance(entry, dict):
                        raise SystemExit(f"Missing multi-k stop_context stats for {s}, k={kk} in {fp}")
                    before_stats_mk[s][int(kk)].merge(_load_stats(entry.get("before", {}) or {}))  # type: ignore[arg-type]
                    after_stats_mk[s][int(kk)].merge(_load_stats(entry.get("after", {}) or {}))  # type: ignore[arg-type]
        else:
            # Back-compat: schema v1 (or v2 without multi-k) only contains primary-k stats.
            if len(k_list_seen) != 1:
                raise SystemExit(
                    f"Shard {fp} lacks stop_context_welford_multi_k but merge expects multiple k values: {k_list_seen}"
                )
            w = obj.get("stop_context_welford", {}) or {}
            for s in STOP_CODONS:
                if s not in w:
                    continue
                before_stats_mk[s][int(k_primary_seen)].merge(_load_stats(w[s]["before"]))  # type: ignore[index]
                after_stats_mk[s][int(k_primary_seen)].merge(_load_stats(w[s]["after"]))  # type: ignore[index]

        sc_mk = obj.get("start_context_welford_multi_k")
        if isinstance(sc_mk, dict) and sc_mk:
            for kk in k_list_seen:
                entry = sc_mk.get(str(int(kk)))
                if not isinstance(entry, dict):
                    raise SystemExit(f"Missing start_context_welford_multi_k[{kk}] in {fp}")
                start_before_stats_mk[int(kk)].merge(_load_stats(entry.get("before", {}) or {}))
                start_after_stats_mk[int(kk)].merge(_load_stats(entry.get("after", {}) or {}))
        else:
            # Back-compat: shards without start-context stats.
            pass

        zsm = obj.get("zspectrum_metrics_samples", {}) or {}
        for x in zsm.get("boundary_rate", []) or []:
            br_samples.append(float(x))
        for x in zsm.get("entropy_Z", []) or []:
            hz_samples.append(float(x))
        for x in zsm.get("autocorr_Z1", []) or []:
            rho_samples.append(float(x))

        # Composition-adjusted stop-context bins + samples (schema v3+).
        comp = obj.get("stop_context_composition")
        if isinstance(comp, dict) and comp:
            for sk, meta in comp.items():
                if not isinstance(sk, str) or not isinstance(meta, dict):
                    continue
                x_name = str(meta.get("x_name") or "")
                gc_edges = meta.get("gc_edges") or []
                x_edges = meta.get("x_edges") or []
                if sk not in comp_schemes_seen:
                    comp_schemes_seen[sk] = {"x_name": x_name, "gc_edges": gc_edges, "x_edges": x_edges}
                    comp_before_merged[sk] = {s: {} for s in STOP_CODONS}
                    comp_after_merged[sk] = {s: {} for s in STOP_CODONS}
                else:
                    prev = comp_schemes_seen[sk]
                    if (
                        str(prev.get("x_name") or "") != x_name
                        or prev.get("gc_edges") != gc_edges
                        or prev.get("x_edges") != x_edges
                    ):
                        raise SystemExit(f"Mismatched stop_context_composition scheme '{sk}' across shards in {fp}")

                before = meta.get("before") or {}
                after = meta.get("after") or {}
                if not isinstance(before, dict) or not isinstance(after, dict):
                    continue
                for s in STOP_CODONS:
                    bmap = before.get(s) or {}
                    amap = after.get(s) or {}
                    if isinstance(bmap, dict):
                        for bk, st in bmap.items():
                            if not isinstance(st, dict):
                                continue
                            comp_before_merged[sk][s].setdefault(str(bk), RunningStats()).merge(_load_stats(st))
                    if isinstance(amap, dict):
                        for bk, st in amap.items():
                            if not isinstance(st, dict):
                                continue
                            comp_after_merged[sk][s].setdefault(str(bk), RunningStats()).merge(_load_stats(st))

        samp = obj.get("stop_context_composition_samples") or {}
        if isinstance(samp, dict):
            by_stop = samp.get("by_stop") or {}
            if isinstance(by_stop, dict):
                for s in STOP_CODONS:
                    lst = by_stop.get(s) or []
                    if not isinstance(lst, list):
                        continue
                    for item in lst:
                        if not isinstance(item, dict):
                            continue
                        seen = int(nn_seen.get(s, 0)) + 1
                        nn_seen[s] = int(seen)
                        rsv = nn_samples[s]
                        if len(rsv) < int(NN_SAMPLE_MAX_PER_STOP):
                            rsv.append(item)
                        else:
                            j = rng_nn.randrange(int(seen))
                            if j < int(NN_SAMPLE_MAX_PER_STOP):
                                rsv[int(j)] = item

        # Reporter-candidate pools (extrema from shards; schema v5+).
        cand_pool = obj.get("stop_context_candidate_pool") or {}
        if isinstance(cand_pool, dict):
            by_stop = cand_pool.get("by_stop") or {}
            if isinstance(by_stop, dict):
                for s in STOP_CODONS:
                    entry = by_stop.get(s) or {}
                    if not isinstance(entry, dict):
                        continue
                    for key0 in ("top_after", "bottom_after", "top_diff", "bottom_diff"):
                        lst = entry.get(key0) or []
                        if not isinstance(lst, list):
                            continue
                        for it in lst:
                            if not isinstance(it, dict):
                                continue
                            rid = it.get("record_id")
                            stop_base = it.get("stop_base")
                            frame = it.get("frame", 0)
                            if not isinstance(rid, str) or not rid.strip():
                                continue
                            try:
                                stop_base_i = int(stop_base)  # type: ignore[arg-type]
                                frame_i = int(frame)  # type: ignore[arg-type]
                            except Exception:
                                continue
                            key = (str(rid), int(stop_base_i), int(frame_i))
                            if key in cand_seen[s]:
                                continue
                            cand_seen[s].add(key)

                            a = it.get("after_mean")
                            b = it.get("before_mean")
                            d = it.get("diff")
                            try:
                                a_f = float(a)  # type: ignore[arg-type]
                                b_f = float(b)  # type: ignore[arg-type]
                            except Exception:
                                continue
                            d_f = float(d) if d is not None else (a_f - b_f)

                            _push_topk(
                                cand_top_after[s],
                                score=float(a_f),
                                rid=str(rid),
                                stop_base=int(stop_base_i),
                                frame=int(frame_i),
                                item=it,
                                limit=int(CAND_POOL_MAX_PER_STOP),
                            )
                            _push_topk(
                                cand_bottom_after[s],
                                score=-float(a_f),
                                rid=str(rid),
                                stop_base=int(stop_base_i),
                                frame=int(frame_i),
                                item=it,
                                limit=int(CAND_POOL_MAX_PER_STOP),
                            )
                            _push_topk(
                                cand_top_diff[s],
                                score=float(d_f),
                                rid=str(rid),
                                stop_base=int(stop_base_i),
                                frame=int(frame_i),
                                item=it,
                                limit=int(CAND_POOL_MAX_PER_STOP),
                            )
                            _push_topk(
                                cand_bottom_diff[s],
                                score=-float(d_f),
                                rid=str(rid),
                                stop_base=int(stop_base_i),
                                frame=int(frame_i),
                                item=it,
                                limit=int(CAND_POOL_MAX_PER_STOP),
                            )

    if coding_tokens <= 0 or hist_total(orf_len_hist) <= 0:
        raise SystemExit("Merged shard summaries contain no coding tokens / ORFs.")

    boundary_rate = boundary_token_count / float(coding_tokens)

    mean_orf = float(hist_sum(orf_len_hist)) / float(hist_total(orf_len_hist))
    median_orf = float(hist_quantile_inclusive(orf_len_hist, 0.5))
    p25_orf = float(hist_quantile_inclusive(orf_len_hist, 0.25))
    p75_orf = float(hist_quantile_inclusive(orf_len_hist, 0.75))
    min_orf = int(min(orf_len_hist.keys()))
    max_orf = int(max(orf_len_hist.keys()))

    # Codon-usage statistics.
    sum_v = 0.0
    sum_u = 0.0
    for codon, cnt in codon_counts.items():
        if codon not in GENETIC_CODE:
            continue
        f = fold_codon(codon, MU_STAR)
        sum_v += float(cnt) * float(f.v)
        sum_u += float(cnt) * float(f.delta)
    zbar = sum_v / float(coding_tokens)
    ubar = sum_u / float(coding_tokens)
    null = codon_usage_null_test(aa_counts, observed_zbar=zbar, observed_ubar=ubar)

    # Stop-context summary and tests.
    if k_primary_seen is None or k_list_seen is None or before_stats_mk is None or after_stats_mk is None:
        raise SystemExit("Stop-context k configuration missing from shard set.")
    k_primary = int(k_primary_seen)
    k_list = [int(x) for x in k_list_seen]

    stop_ctx_summary: dict[str, dict[str, float | int | None]] = {}
    for s in STOP_CODONS:
        stop_ctx_summary[s] = {
            "k": int(k_primary),
            "n": int(before_stats[s].n),
            "before_mean": (float(before_stats[s].mean) if before_stats[s].n > 0 else None),
            "after_mean": (float(after_stats[s].mean) if after_stats[s].n > 0 else None),
        }

    p_before = {
        "UAA_vs_UAG": welch_t_p_value_two_sided_from_stats(before_stats["UAA"], before_stats["UAG"]),
        "UAA_vs_UGA": welch_t_p_value_two_sided_from_stats(before_stats["UAA"], before_stats["UGA"]),
        "UAG_vs_UGA": welch_t_p_value_two_sided_from_stats(before_stats["UAG"], before_stats["UGA"]),
    }
    p_after = {
        "UAA_vs_UAG": welch_t_p_value_two_sided_from_stats(after_stats["UAA"], after_stats["UAG"]),
        "UAA_vs_UGA": welch_t_p_value_two_sided_from_stats(after_stats["UAA"], after_stats["UGA"]),
        "UAG_vs_UGA": welch_t_p_value_two_sided_from_stats(after_stats["UAG"], after_stats["UGA"]),
    }

    def _heap_items(heap: list[tuple[float, str, int, int, dict[str, object]]]) -> list[dict[str, object]]:
        return [it[-1] for it in sorted(heap, key=lambda x: (float(x[0]), str(x[1]), int(x[2]), int(x[3])), reverse=True)]

    def _seq_sig(r: dict[str, object]) -> tuple[str, str, str]:
        return (
            str(r.get("before_seq_dna") or ""),
            str(r.get("stop_codon_dna") or ""),
            str(r.get("after_seq_dna") or ""),
        )

    def _dedup_by_seq(rows: list[dict[str, object]], *, limit: int) -> list[dict[str, object]]:
        """
        Deduplicate candidates by explicit context sequence (before + stop + after).
        Keeps order (already ranked by score).
        """
        out: list[dict[str, object]] = []
        seen: set[tuple[str, str, str]] = set()
        for r in rows:
            sig = _seq_sig(r)
            if not sig[0] or not sig[2]:
                continue
            if sig in seen:
                continue
            seen.add(sig)
            out.append(r)
            if len(out) >= int(limit):
                break
        return out

    def _match_after_gc_dinuc(
        *,
        high: list[dict[str, object]],
        low: list[dict[str, object]],
        gc_eps_schedule: list[float],
        limit: int,
    ) -> list[dict[str, object]]:
        """
        Build composition-matched pairs using after-window (GC + 16-dinuc L1).
        Returns a list of pairs: {rank, high, low, eps_used, l1}.
        """
        out: list[dict[str, object]] = []
        used_low: set[tuple[str, int, int]] = set()
        for h in high:
            if len(out) >= int(limit):
                break
            gc_h = h.get("after_gc")
            vec_h = h.get("after_dinuc")
            if gc_h is None or vec_h is None or (not isinstance(vec_h, list)) or len(vec_h) != 16:
                continue
            try:
                gc_h_f = float(gc_h)
                vec_h_f = [float(x) for x in vec_h]
            except Exception:
                continue

            best: dict[str, object] | None = None
            best_l1: float | None = None
            best_eps: float | None = None
            for eps in gc_eps_schedule:
                for l in low:
                    rid_l = l.get("record_id")
                    stop_base_l = l.get("stop_base")
                    frame_l = l.get("frame")
                    if not isinstance(rid_l, str) or rid_l.strip() == "":
                        continue
                    try:
                        key_l = (rid_l, int(stop_base_l or 0), int(frame_l or 0))
                    except Exception:
                        continue
                    if key_l in used_low:
                        continue

                    gc_l = l.get("after_gc")
                    vec_l = l.get("after_dinuc")
                    if gc_l is None or vec_l is None or (not isinstance(vec_l, list)) or len(vec_l) != 16:
                        continue
                    try:
                        gc_l_f = float(gc_l)
                        vec_l_f = [float(x) for x in vec_l]
                    except Exception:
                        continue
                    if abs(gc_l_f - gc_h_f) > float(eps):
                        continue
                    l1 = float(sum(abs(a - b) for a, b in zip(vec_h_f, vec_l_f)))
                    if best_l1 is None or l1 < best_l1:
                        best_l1 = float(l1)
                        best_eps = float(eps)
                        best = l
                if best is not None:
                    break

            if best is None or best_l1 is None or best_eps is None:
                continue

            rid_l = str(best.get("record_id") or "")
            used_low.add((rid_l, int(best.get("stop_base") or 0), int(best.get("frame") or 0)))
            out.append({"rank": int(len(out) + 1), "high": h, "low": best, "eps_used": float(best_eps), "l1": float(best_l1)})
        return out

    stop_context_candidates = {
        "candidate_set": str(cand_set),
        "k": int(k_primary),
        "limit_per_stop": int(cand_limit),
        "by_stop": {
            s: {
                "high_after": _dedup_by_seq(_heap_items(cand_top_after.get(s, [])), limit=int(cand_limit)),
                "low_after": _dedup_by_seq(_heap_items(cand_bottom_after.get(s, [])), limit=int(cand_limit)),
                "high_diff": _dedup_by_seq(_heap_items(cand_top_diff.get(s, [])), limit=int(cand_limit)),
                "low_diff": _dedup_by_seq(_heap_items(cand_bottom_diff.get(s, [])), limit=int(cand_limit)),
            }
            for s in STOP_CODONS
        },
    }

    # Add after-window matched pairs (GC + dinuc) for the high/low-after sets.
    gc_eps_schedule = [0.05, 0.10, 0.20, 0.30]
    stop_context_candidates["matched_after"] = {
        s: _match_after_gc_dinuc(
            high=list((stop_context_candidates.get("by_stop") or {}).get(s, {}).get("high_after") or []),
            low=list((stop_context_candidates.get("by_stop") or {}).get(s, {}).get("low_after") or []),
            gc_eps_schedule=gc_eps_schedule,
            limit=int(cand_limit),
        )
        for s in STOP_CODONS
    }

    def _is_protein_coding_rid(rid: str) -> bool:
        pref = rid.split("_", 1)[0] if "_" in rid else rid[:2]
        return pref in ("NM", "XM")

    def _filter_coding(rows: list[dict[str, object]]) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for r in rows:
            rid = r.get("record_id")
            if not isinstance(rid, str) or not rid:
                continue
            if _is_protein_coding_rid(rid):
                out.append(r)
        return out

    # Protein-coding-only candidate sets (NM/XM), derived from the same merged pools.
    stop_context_candidates_coding = {
        "candidate_set": str(cand_set_coding),
        "k": int(k_primary),
        "limit_per_stop": int(cand_limit),
        "by_stop": {
            s: {
                "high_after": _dedup_by_seq(_filter_coding(_heap_items(cand_top_after.get(s, []))), limit=int(cand_limit)),
                "low_after": _dedup_by_seq(_filter_coding(_heap_items(cand_bottom_after.get(s, []))), limit=int(cand_limit)),
                "high_diff": _dedup_by_seq(_filter_coding(_heap_items(cand_top_diff.get(s, []))), limit=int(cand_limit)),
                "low_diff": _dedup_by_seq(_filter_coding(_heap_items(cand_bottom_diff.get(s, []))), limit=int(cand_limit)),
            }
            for s in STOP_CODONS
        },
    }
    stop_context_candidates_coding["matched_after"] = {
        s: _match_after_gc_dinuc(
            high=list((stop_context_candidates_coding.get("by_stop") or {}).get(s, {}).get("high_after") or []),
            low=list((stop_context_candidates_coding.get("by_stop") or {}).get(s, {}).get("low_after") or []),
            gc_eps_schedule=gc_eps_schedule,
            limit=int(cand_limit),
        )
        for s in STOP_CODONS
    }

    # ---- Composition-adjusted stop-context (stratified bins + NN sample cross-check) ----
    def _paired_summary(diffs: list[float]) -> dict[str, object]:
        n = len(diffs)
        if n <= 0:
            return {"n": 0, "mean_diff": None, "ci_low": None, "ci_high": None, "p": None}
        xs = [float(x) for x in diffs]
        mu = sum(xs) / float(n)
        if n < 2:
            return {"n": int(n), "mean_diff": float(mu), "ci_low": None, "ci_high": None, "p": None}
        v = statistics.pvariance(xs) * (n / (n - 1))  # sample variance
        se = math.sqrt(v / float(n)) if v > 0 else 0.0
        ci_low = mu - 1.96 * se if se > 0 else None
        ci_high = mu + 1.96 * se if se > 0 else None
        t = abs(mu) / se if se > 0 else 0.0
        df_i = max(1, int(n - 1))
        p = 2.0 * (1.0 - student_t_cdf(t, df=df_i)) if se > 0 else 1.0
        return {"n": int(n), "mean_diff": float(mu), "ci_low": ci_low, "ci_high": ci_high, "p": float(p)}

    def _l1_16(a: list[float], b: list[float]) -> float:
        return float(sum(abs(float(x) - float(y)) for x, y in zip(a, b)))

    def _nn_match_one(
        *,
        target_gc: float,
        target_vec: list[float],
        candidates: list[dict[str, object]],
        window: str,
        gc_eps_schedule: list[float],
    ) -> float | None:
        best: float | None = None
        best_l1: float | None = None
        for eps in gc_eps_schedule:
            for c in candidates:
                gc0 = c.get(f"{window}_gc")
                vec0 = c.get(f"{window}_dinuc")
                mean0 = c.get(f"{window}_mean")
                if gc0 is None or vec0 is None or mean0 is None:
                    continue
                try:
                    gc_f = float(gc0)
                    m_f = float(mean0)
                except Exception:
                    continue
                if abs(gc_f - float(target_gc)) > float(eps):
                    continue
                if not isinstance(vec0, list) or len(vec0) != 16:
                    continue
                l1 = _l1_16(target_vec, [float(x) for x in vec0])
                if best_l1 is None or l1 < best_l1:
                    best_l1 = float(l1)
                    best = float(m_f)
            if best is not None:
                break
        return best

    comp_results: dict[str, object] | None = None
    if comp_schemes_seen:
        # Stratified (full-data) meta-analysis across bins.
        stratified: dict[str, dict[str, dict[str, object]]] = {}
        pairs = [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]
        for sk in sorted(comp_schemes_seen.keys()):
            stratified[sk] = {"before": {}, "after": {}}
            for window, merged in (("before", comp_before_merged), ("after", comp_after_merged)):
                for a, b in pairs:
                    num = 0.0
                    den = 0.0
                    bins_used = 0
                    for bk in sorted(set(merged.get(sk, {}).get(a, {}).keys()) & set(merged.get(sk, {}).get(b, {}).keys())):
                        sa = merged[sk][a][bk]
                        sb = merged[sk][b][bk]
                        n1 = int(sa.n)
                        n2 = int(sb.n)
                        if n1 < 2 or n2 < 2:
                            continue
                        v1 = float(sa.sample_variance())
                        v2 = float(sb.sample_variance())
                        var = (v1 / float(n1)) + (v2 / float(n2))
                        if var <= 0:
                            continue
                        w = 1.0 / var
                        num += w * (float(sa.mean) - float(sb.mean))
                        den += w
                        bins_used += 1
                    if den <= 0 or bins_used <= 0:
                        stratified[sk][window][f"{a}_vs_{b}"] = {"diff": None, "se": None, "z": None, "p": None, "bins_used": 0}
                        continue
                    diff = num / den
                    se = math.sqrt(1.0 / den)
                    z = diff / se if se > 0 else 0.0
                    p = normal_two_sided_p(z) if se > 0 else 1.0
                    stratified[sk][window][f"{a}_vs_{b}"] = {
                        "diff": float(diff),
                        "se": float(se),
                        "z": float(z),
                        "p": float(p),
                        "bins_used": int(bins_used),
                    }

        # NN sample cross-check (bounded reservoirs).
        gc_eps_schedule = [0.05, 0.10, 0.20, 0.30]
        nn: dict[str, dict[str, dict[str, object]]] = {"before": {}, "after": {}}
        # Normalize samples to a simpler form.
        samples_norm: dict[str, list[dict[str, object]]] = {s: [] for s in STOP_CODONS}
        for s in STOP_CODONS:
            for it in nn_samples.get(s, []):
                if not isinstance(it, dict):
                    continue
                # The shard sampler stores 'before_mean'/'after_mean' and 'before_gc'/'after_gc' etc.
                # Normalize field names to '{window}_mean/gc/dinuc'.
                out = {
                    "before_mean": it.get("before_mean"),
                    "after_mean": it.get("after_mean"),
                    "before_gc": it.get("before_gc"),
                    "after_gc": it.get("after_gc"),
                    "before_dinuc": it.get("before_dinuc"),
                    "after_dinuc": it.get("after_dinuc"),
                }
                samples_norm[s].append(out)

        for window in ("before", "after"):
            for a, b in pairs:
                diffs: list[float] = []
                cand_b = samples_norm.get(b, [])
                for it in samples_norm.get(a, []):
                    gc0 = it.get(f"{window}_gc")
                    vec0 = it.get(f"{window}_dinuc")
                    mean0 = it.get(f"{window}_mean")
                    if gc0 is None or vec0 is None or mean0 is None:
                        continue
                    if not isinstance(vec0, list) or len(vec0) != 16:
                        continue
                    try:
                        gc_f = float(gc0)
                        m_f = float(mean0)
                    except Exception:
                        continue
                    m_match = _nn_match_one(
                        target_gc=gc_f,
                        target_vec=[float(x) for x in vec0],
                        candidates=cand_b,
                        window=window,
                        gc_eps_schedule=gc_eps_schedule,
                    )
                    if m_match is None:
                        continue
                    diffs.append(float(m_f) - float(m_match))
                nn[window][f"{a}_vs_{b}"] = _paired_summary(diffs)

        comp_results = {
            "schemes": comp_schemes_seen,
            "stratified": stratified,
            "nn_samples": {
                "max_per_stop": int(NN_SAMPLE_MAX_PER_STOP),
                "n_per_stop": {s: int(len(nn_samples.get(s, []))) for s in STOP_CODONS},
                "results": nn,
            },
        }

    if start_before_stats_mk is None or start_after_stats_mk is None:
        raise SystemExit("Missing merged start-context stats (start_context_welford_multi_k).")

    summary = {
        "schema_version": 6,
        "analysis_version": int(ANALYSIS_VERSION),
        "merge_version": int(MERGE_VERSION),
        "mu_star": MU_STAR,
        "source_files": sorted(set(source_files)),
        "records": records,
        "records_with_orf": records_with_orf,
        "total_nt": total_nt,
        "coding_tokens": coding_tokens,
        "boundary_token_count": boundary_token_count,
        "boundary_rate": boundary_rate,
        "orf_len_codons_excl_stop": {
            "mean": mean_orf,
            "median": median_orf,
            "p25": p25_orf,
            "p75": p75_orf,
            "min": min_orf,
            "max": max_orf,
        },
        "orf_len_hist": {str(k): int(v) for k, v in sorted(orf_len_hist.items())},
        "termination_stop_counts": {k: int(v) for k, v in sorted(term_stop_counts.items())},
        "termination_stop_boundary_count": int(term_stop_boundary_count),
        "stop_window": int(k_primary),
        "stop_window_list": [int(x) for x in k_list],
        "start_context": {
            "k": int(k_primary),
            "before": {
                "n": int(start_before_stats_mk[int(k_primary)].n),
                "mean": (float(start_before_stats_mk[int(k_primary)].mean) if start_before_stats_mk[int(k_primary)].n > 0 else None),
            },
            "after": {
                "n": int(start_after_stats_mk[int(k_primary)].n),
                "mean": (float(start_after_stats_mk[int(k_primary)].mean) if start_after_stats_mk[int(k_primary)].n > 0 else None),
            },
        },
        "start_context_welford": {
            "before": {
                "n": int(start_before_stats_mk[int(k_primary)].n),
                "mean": float(start_before_stats_mk[int(k_primary)].mean),
                "M2": float(start_before_stats_mk[int(k_primary)].M2),
            },
            "after": {
                "n": int(start_after_stats_mk[int(k_primary)].n),
                "mean": float(start_after_stats_mk[int(k_primary)].mean),
                "M2": float(start_after_stats_mk[int(k_primary)].M2),
            },
        },
        "start_context_welford_multi_k": {
            str(int(kk)): {
                "before": {
                    "n": int(start_before_stats_mk[int(kk)].n),
                    "mean": float(start_before_stats_mk[int(kk)].mean),
                    "M2": float(start_before_stats_mk[int(kk)].M2),
                },
                "after": {
                    "n": int(start_after_stats_mk[int(kk)].n),
                    "mean": float(start_after_stats_mk[int(kk)].mean),
                    "M2": float(start_after_stats_mk[int(kk)].M2),
                },
            }
            for kk in k_list
        },
        "stop_context": stop_ctx_summary,
        "stop_context_welford": {
            s: {
                "before": {"n": int(before_stats[s].n), "mean": float(before_stats[s].mean), "M2": float(before_stats[s].M2)},
                "after": {"n": int(after_stats[s].n), "mean": float(after_stats[s].mean), "M2": float(after_stats[s].M2)},
            }
            for s in STOP_CODONS
        },
        "stop_context_welford_multi_k": {
            s: {
                str(int(kk)): {
                    "before": {
                        "n": int(before_stats_mk[s][int(kk)].n),
                        "mean": float(before_stats_mk[s][int(kk)].mean),
                        "M2": float(before_stats_mk[s][int(kk)].M2),
                    },
                    "after": {
                        "n": int(after_stats_mk[s][int(kk)].n),
                        "mean": float(after_stats_mk[s][int(kk)].mean),
                        "M2": float(after_stats_mk[s][int(kk)].M2),
                    },
                }
                for kk in k_list
            }
            for s in STOP_CODONS
        },
        "stop_context_p_before": p_before,
        "stop_context_p_after": p_after,
        "stop_context_candidates": stop_context_candidates,
        "stop_context_candidates_coding": stop_context_candidates_coding,
        "codon_counts": {k: int(v) for k, v in sorted(codon_counts.items())},
        "aa_counts": {k: int(v) for k, v in sorted(aa_counts.items())},
        "codon_usage": {"zbar": zbar, "ubar": ubar, "null": null},
        "zspectrum_metrics": {
            "boundary_rate": _summarize_float_list(br_samples),
            "entropy_Z": _summarize_float_list(hz_samples),
            "autocorr_Z1": _summarize_float_list(rho_samples),
        },
        "stop_context_composition": comp_results,
        "V_hist": {str(k): int(v) for k, v in sorted(v_hist.items())},
        "Delta_hist": {str(k): int(v) for k, v in sorted(delta_hist.items())},
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_json, summary)
    print("Wrote:", out_json)
    hb.force(f"wrote_summary records={records} coding_tokens={coding_tokens}")

    if args.no_latex:
        write_json_atomic(cache_meta_path(out_json), merge_meta)
        hb.force("done")
        return

    _emit_outputs_from_summary(summary)
    print("Wrote LaTeX fragments into:", generated_dir())
    write_json_atomic(cache_meta_path(out_json), merge_meta)
    hb.force("done")


if __name__ == "__main__":
    main()


