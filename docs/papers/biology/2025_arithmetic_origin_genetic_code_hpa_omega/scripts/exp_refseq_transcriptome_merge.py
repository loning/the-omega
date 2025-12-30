# -*- coding: utf-8 -*-
"""
Merge shard-level transcriptome summaries produced by exp_refseq_transcriptome.py
and regenerate the final JSON summary + LaTeX fragments.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
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
from genetic_code_tools import BOUNDARY_WORDS, GENETIC_CODE, STOP_CODONS, fold_codon


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
    return p.parse_args()


def _load_stats(d: dict[str, object]) -> RunningStats:
    return RunningStats(
        n=int(d.get("n", 0) or 0),
        mean=float(d.get("mean", 0.0) or 0.0),
        M2=float(d.get("M2", 0.0) or 0.0),
    )


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
        "analysis_version": ANALYSIS_VERSION,
        "in_dir": str(in_dir),
        "shards": shard_meta,
        "mu_star": MU_STAR,
    }
    merge_meta = {"cache_key": merge_key, "cache_digest": cache_key_digest(merge_key)}
    if not args.no_latex and cache_hit(out_json, expected_meta=merge_meta, require_meta=True):
        # Back-compat: if meta missing, write it.
        if not cache_meta_path(out_json).exists():
            write_json_atomic(cache_meta_path(out_json), merge_meta)
        print(f"[cache] hit: {out_json}")
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

    before_stats = {s: RunningStats() for s in STOP_CODONS}
    after_stats = {s: RunningStats() for s in STOP_CODONS}
    k_seen: int | None = None

    # Z-spectrum fingerprint metrics samples (exact merge).
    br_samples: list[float] = []
    hz_samples: list[float] = []
    rho_samples: list[float] = []

    source_files: list[str] = []

    for fp in files:
        obj = json.loads(fp.read_text(encoding="utf-8"))
        if int(obj.get("schema_version", 0) or 0) != 1:
            raise SystemExit(f"Unexpected schema_version in {fp}")

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

        sc = obj.get("stop_context", {}) or {}
        for s in STOP_CODONS:
            if s in sc:
                k_i = int(sc[s].get("k", 0) or 0)
                if k_seen is None:
                    k_seen = k_i
                elif k_seen != k_i:
                    raise SystemExit(f"Mismatched stop-window k across shards: {k_seen} vs {k_i}")

        w = obj.get("stop_context_welford", {}) or {}
        for s in STOP_CODONS:
            if s not in w:
                continue
            before_stats[s].merge(_load_stats(w[s]["before"]))  # type: ignore[index]
            after_stats[s].merge(_load_stats(w[s]["after"]))  # type: ignore[index]

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
    stop_ctx_summary: dict[str, dict[str, float | int | None]] = {}
    k = int(k_seen or 0)
    for s in STOP_CODONS:
        stop_ctx_summary[s] = {
            "k": k,
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
        "schema_version": 1,
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
        "stop_context": stop_ctx_summary,
        "stop_context_welford": {
            s: {
                "before": {"n": int(before_stats[s].n), "mean": float(before_stats[s].mean), "M2": float(before_stats[s].M2)},
                "after": {"n": int(after_stats[s].n), "mean": float(after_stats[s].mean), "M2": float(after_stats[s].M2)},
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

    # ---- LaTeX fragments (same filenames as the single-pass script) ----
    stop_total = sum(term_stop_counts.values())
    uaa = term_stop_counts.get("UAA", 0)
    uag = term_stop_counts.get("UAG", 0)
    uga = term_stop_counts.get("UGA", 0)

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
        frac = (c / stop_total) if stop_total else 0.0
        rows.append(f"{codon} & {c} & {frac:.4f} \\\\")
    write_text(generated_dir() / "refseq_termination_stop_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")

    rows2 = []
    for codon in STOP_CODONS:
        n = int(before_stats[codon].n)
        bm = float(before_stats[codon].mean) if n else float("nan")
        am = float(after_stats[codon].mean) if n else float("nan")
        rows2.append(f"{codon} & {k} & {n} & {bm:.4f} & {am:.4f} \\\\")
    write_text(generated_dir() / "refseq_stop_context_rows.tex", "\n".join(rows2) + "\n\\bottomrule\n")

    null_s = (
        "Codon-usage summary over coding tokens (excluding terminal stops): "
        f"$\\overline{{Z}}={zbar:.4f}$, $\\overline{{U}}={ubar:.4f}$. "
        "Under an amino-acid preserving null (uniform choice among synonymous codons), "
        f"$\\mathbb{{E}}[\\overline{{Z}}]={null['null_mu_zbar']:.4f}$ with $\\mathrm{{sd}}={null['null_sd_zbar']:.6f}$ "
        f"($z={null['z_zbar']:.2f}$, $p={null['p_zbar']:.4g}$), and "
        f"$\\mathbb{{E}}[\\overline{{U}}]={null['null_mu_ubar']:.4f}$ with $\\mathrm{{sd}}={null['null_sd_ubar']:.6f}$ "
        f"($z={null['z_ubar']:.2f}$, $p={null['p_ubar']:.4g}$)."
    )
    write_text(generated_dir() / "refseq_codon_usage_null.tex", null_s + "\n")

    zfp = summary["zspectrum_metrics"]
    s_fp = (
        "\\begin{tabular}{@{}l@{}}\n"
        "Z-spectrum fingerprint metrics over best ORFs (excluding terminal stops):\\\\\n"
        f"boundary-rate mean {zfp['boundary_rate']['mean']:.4f}, median {zfp['boundary_rate']['median']:.4f}\\\\\n"
        f"entropy $H(Z)$ mean {zfp['entropy_Z']['mean']:.4f}, median {zfp['entropy_Z']['median']:.4f}\\\\\n"
        f"lag-1 autocorrelation $\\rho(Z_i,Z_{{i+1}})$ mean {zfp['autocorr_Z1']['mean']:.4f}, "
        f"median {zfp['autocorr_Z1']['median']:.4f} (n={int(zfp['autocorr_Z1']['n'])}).\n"
        "\\end{tabular}"
    )
    write_text(generated_dir() / "refseq_zspectrum_fingerprint.tex", s_fp + "\n")

    print("Wrote LaTeX fragments into:", generated_dir())
    write_json_atomic(cache_meta_path(out_json), merge_meta)


if __name__ == "__main__":
    main()


