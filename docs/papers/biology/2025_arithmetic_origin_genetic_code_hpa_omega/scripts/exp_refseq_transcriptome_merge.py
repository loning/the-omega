# -*- coding: utf-8 -*-
"""
Merge shard-level transcriptome summaries produced by exp_refseq_transcriptome.py
and regenerate the final JSON summary + LaTeX fragments.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
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
    write_text,
)
from genetic_code_tools import BOUNDARY_WORDS, GENETIC_CODE, STOP_CODONS, amino_acid_codons, fold_codon
from stats_tools import (
    aa_preserving_null_decomposition,
    bh_fdr,
    cohen_d_from_stats,
    hedges_g_from_stats,
    mean_diff_ci_normal_from_stats,
)

MERGE_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge RefSeq transcriptome shard summaries")
    p.add_argument(
        "--in-dir",
        default=str(root_dir() / "data" / "refseq_hsapiens_mrna" / "shards"),
        help="Directory containing shard JSON summaries.",
    )
    p.add_argument(
        "--out-json",
        default=str(root_dir() / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json"),
        help="Output merged JSON path.",
    )
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--force", action="store_true", help="Force merge and LaTeX regeneration (ignore cache).")
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
        return "=", f"{p0:.2e}"
    return "=", f"{p0:.4f}"


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

    null_s = (
        "Codon-usage summary over coding tokens (excluding terminal stops): "
        f"$\\overline{{Z}}={zbar:.4f}$, $\\overline{{U}}={ubar:.4f}$. "
        "Under an amino-acid preserving null (uniform choice among synonymous codons), "
        f"$\\mathbb{{E}}[\\overline{{Z}}]={float(null.get('null_mu_zbar', float('nan'))):.4f}$ with "
        f"$\\mathrm{{sd}}={float(null.get('null_sd_zbar', float('nan'))):.6f}$ "
        f"($z={float(null.get('z_zbar', float('nan'))):.2f}$, $p={float(null.get('p_zbar', float('nan'))):.4g}$), and "
        f"$\\mathbb{{E}}[\\overline{{U}}]={float(null.get('null_mu_ubar', float('nan'))):.4f}$ with "
        f"$\\mathrm{{sd}}={float(null.get('null_sd_ubar', float('nan'))):.6f}$ "
        f"($z={float(null.get('z_ubar', float('nan'))):.2f}$, $p={float(null.get('p_ubar', float('nan'))):.4g}$)."
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
        pq = f"{op_p}{p_s}/{op_q}{q_s}"
        eff_lines.append(
            f"{window} & {kk_i} & {n1} & {n2} & {pair} & {m1:.4f} & {m2:.4f} & {diff:+.4f} & {ci_s} & {d_s} & {g_s} & {pq} \\\\"
        )
    eff_lines.append("\\bottomrule")
    eff_lines.append("\\end{tabular}%")
    eff_lines.append("}")
    eff_lines.append("\\end{center}")
    write_text(generated_dir() / "refseq_stop_context_effects_table.tex", "\n".join(eff_lines) + "\n")

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
    u_lines.append(
        "Amino-acid preserving null decomposition for $\\overline{U}$ (coding tokens, excluding terminal stops). "
        f"Observed $\\overline{{U}}={decomp_u.obs_mean:.4f}$ vs null $\\mathbb{{E}}[\\overline{{U}}]={decomp_u.null_mean:.4f}$ "
        f"($\\mathrm{{sd}}={decomp_u.null_sd:.6f}$, $z={decomp_u.z_score:.2f}$, $p={decomp_u.p_value:.4g}$)."
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
    k_primary_seen: int | None = None
    k_list_seen: list[int] | None = None

    # Z-spectrum fingerprint metrics samples (exact merge).
    br_samples: list[float] = []
    hz_samples: list[float] = []
    rho_samples: list[float] = []

    source_files: list[str] = []

    for fp in files:
        obj = json.loads(fp.read_text(encoding="utf-8"))
        shard_schema = int(obj.get("schema_version", 0) or 0)
        if shard_schema not in (1, 2):
            raise SystemExit(f"Unexpected schema_version in {fp}: {shard_schema}")

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

        zsm = obj.get("zspectrum_metrics_samples", {}) or {}
        for x in zsm.get("boundary_rate", []) or []:
            br_samples.append(float(x))
        for x in zsm.get("entropy_Z", []) or []:
            hz_samples.append(float(x))
        for x in zsm.get("autocorr_Z1", []) or []:
            rho_samples.append(float(x))

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

    summary = {
        "schema_version": 2,
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
        "codon_counts": {k: int(v) for k, v in sorted(codon_counts.items())},
        "aa_counts": {k: int(v) for k, v in sorted(aa_counts.items())},
        "codon_usage": {"zbar": zbar, "ubar": ubar, "null": null},
        "zspectrum_metrics": {
            "boundary_rate": _summarize_float_list(br_samples),
            "entropy_Z": _summarize_float_list(hz_samples),
            "autocorr_Z1": _summarize_float_list(rho_samples),
        },
        "V_hist": {str(k): int(v) for k, v in sorted(v_hist.items())},
        "Delta_hist": {str(k): int(v) for k, v in sorted(delta_hist.items())},
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_json, summary)
    print("Wrote:", out_json)

    if args.no_latex:
        write_json_atomic(cache_meta_path(out_json), merge_meta)
        return

    _emit_outputs_from_summary(summary)
    print("Wrote LaTeX fragments into:", generated_dir())
    write_json_atomic(cache_meta_path(out_json), merge_meta)


if __name__ == "__main__":
    main()


