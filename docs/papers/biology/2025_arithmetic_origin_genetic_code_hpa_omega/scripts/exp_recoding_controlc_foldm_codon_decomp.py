# -*- coding: utf-8 -*-
"""
Codon-level linear decomposition of Control-C paired differences across Fold_m (standard library only).

For a fixed stratum (default: Sec/UGA/Eukaryota) and fixed window length k:
  - Let U(seq,m) be the mean Delta_m over codons in the window sequence.
  - Define paired differences vs within-CDS random internal controls (Control-C):
      dU_before(i,m) = U(rec_before_i,m) - mean_j U(ctrl_before_ij,m)
      dU_diff(i,m)   = (U(rec_after_i,m)-U(rec_before_i,m)) - (mean_j U(ctrl_after_ij,m)-mean_j U(ctrl_before_ij,m))

Because U is linear in codon frequencies, mean paired differences admit a codon decomposition:
  mean_i dU_before(i,m) = sum_c Delta_m(c) * mean_i [ f_rec_before_i(c) - mean_j f_ctrl_before_ij(c) ]
  mean_i dU_diff(i,m)   = sum_c Delta_m(c) * mean_i [ (f_rec_after_i(c)-mean_j f_ctrl_after_ij(c)) - (f_rec_before_i(c)-mean_j f_ctrl_before_ij(c)) ]

We output top codon drivers (by absolute contribution) for:
  - dU_before (for each m)
  - dU_diff   (for each m)
and also the top codons explaining the change in dU_diff contributions from m=6 to m=8.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
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
    try:
        v = float(x)  # type: ignore[arg-type]
    except Exception:
        return False
    return (not math.isnan(v)) and math.isfinite(v)


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


def _mean(xs: list[float]) -> float | None:
    return (sum(xs) / float(len(xs))) if xs else None


def _codon_counts(seq_dna: str) -> dict[str, int] | None:
    s = str(seq_dna).upper()
    if len(s) == 0 or (len(s) % 3) != 0:
        return None
    if any(ch not in "ACGT" for ch in s):
        return None
    counts: dict[str, int] = defaultdict(int)
    for i in range(0, len(s), 3):
        c = s[i : i + 3]
        if len(c) != 3:
            return None
        rna = c.replace("T", "U")
        counts[rna] += 1
    return dict(counts)


def _mean_delta_from_counts(counts: dict[str, int], *, k: int, delta_map: dict[str, int]) -> float:
    tot = 0
    for codon, n in counts.items():
        tot += int(n) * int(delta_map[codon])
    return float(tot) / float(k)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Codon decomposition of Control-C paired differences across Fold_m.")
    p.add_argument("--in-jsonl", default=str(recoding_jsonl_default()), help="Input recoding_sites.jsonl.")
    p.add_argument("--analysis-version", type=int, default=7, help="Filter: analysis_version.")
    p.add_argument("--k", type=int, default=10, help="Filter: k.")
    p.add_argument("--aa", default="Sec", help="Filter: aa.")
    p.add_argument("--codon-rna", default="UGA", help="Filter: codon_rna.")
    p.add_argument("--domain", default="Eukaryota", help="Filter: domain.")
    p.add_argument("--m-list", default="6,7,8", help="Comma-separated m values to analyze.")
    p.add_argument("--min-n", type=int, default=200, help="Minimum paired samples required to report.")
    p.add_argument("--top-n", type=int, default=12, help="Top codons per m (by absolute contribution) to include; union is reported.")
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "recoding_controlc_foldm_codon_decomp_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-before",
        default=str(generated_dir() / "recoding_controlc_foldm_codon_decomp_before_top.tex"),
        help="Output LaTeX table fragment for dU_before codon drivers.",
    )
    p.add_argument(
        "--out-diff",
        default=str(generated_dir() / "recoding_controlc_foldm_codon_decomp_diff_top.tex"),
        help="Output LaTeX table fragment for dU_diff codon drivers.",
    )
    p.add_argument(
        "--out-drivers",
        default=str(generated_dir() / "recoding_controlc_foldm_codon_decomp_m6_to_m8_drivers.tex"),
        help="Output LaTeX table fragment for m=6->8 change drivers (dU_diff).",
    )
    return p.parse_args()


def _select_top_union(contrib_by_m: dict[int, dict[str, float]], *, ms: list[int], top_n: int) -> list[str]:
    sel: set[str] = set()
    for m in ms:
        items = list(contrib_by_m[int(m)].items())
        items.sort(key=lambda kv: abs(float(kv[1])), reverse=True)
        for codon, _v in items[: int(top_n)]:
            sel.add(str(codon))
    # stable ordering: descending max abs across m
    def key(c: str) -> float:
        return max(abs(float(contrib_by_m[int(m)].get(c, 0.0))) for m in ms)

    return sorted(sel, key=key, reverse=True)


def _latex_longtable_top(
    *,
    title: str,
    codons: list[str],
    ms: list[int],
    mean_dfreq: dict[str, float],
    contrib_by_m: dict[int, dict[str, float]],
    delta_by_m: dict[int, dict[str, int]],
    k: int,
    include_delta_cols: bool = False,
) -> str:
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append(f"\\noindent\\textbf{{{title}}}\\\\")

    colspec = "l l r" + (" r" * len(ms))
    if include_delta_cols:
        colspec = "l l r" + (" r" * len(ms)) + (" r" * len(ms))
    lines.append(f"\\begin{{longtable}}{{{colspec}}}")
    lines.append("\\toprule")
    header = ["codon", "AA", "$100\\,\\overline{df}\\,(\\%)$"]
    for m in ms:
        header.append(f"$\\Delta_{{{int(m)}}}\\cdot\\overline{{df}}$")
    if include_delta_cols:
        for m in ms:
            header.append(f"$\\Delta_{{{int(m)}}}$")
    lines.append(" & ".join(header) + " \\\\")
    lines.append("\\midrule")
    for codon in codons:
        aa = GENETIC_CODE.get(codon, "?")
        df = float(mean_dfreq.get(codon, 0.0))
        row = [codon, aa, _fmt_float_signed(100.0 * df, nd=2)]
        for m in ms:
            row.append(_fmt_float_signed(contrib_by_m[int(m)].get(codon, 0.0), nd=4))
        if include_delta_cols:
            for m in ms:
                row.append(str(int(delta_by_m[int(m)].get(codon, 0))))
        lines.append(" & ".join(row) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")
    return "\n".join(lines) + "\n"


def _latex_longtable_m6_to_m8(
    *,
    title: str,
    codons: list[str],
    mean_dfreq: dict[str, float],
    contrib_m6: dict[str, float],
    contrib_m8: dict[str, float],
    delta6: dict[str, int],
    delta8: dict[str, int],
) -> str:
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append(f"\\noindent\\textbf{{{title}}}\\\\")
    lines.append("\\begin{longtable}{l l r r r r r}")
    lines.append("\\toprule")
    lines.append("codon & AA & $100\\,\\overline{df}_{\\Delta}\\,(\\%)$ & $\\Delta_6$ & $\\Delta_8$ & $c_6$ & $c_8-c_6$ \\\\")
    lines.append("\\midrule")
    for codon in codons:
        aa = GENETIC_CODE.get(codon, "?")
        df = float(mean_dfreq.get(codon, 0.0))
        c6 = float(contrib_m6.get(codon, 0.0))
        c8 = float(contrib_m8.get(codon, 0.0))
        lines.append(
            " & ".join(
                [
                    codon,
                    aa,
                    _fmt_float_signed(100.0 * df, nd=2),
                    str(int(delta6.get(codon, 0))),
                    str(int(delta8.get(codon, 0))),
                    _fmt_float_signed(c6, nd=4),
                    _fmt_float_signed(c8 - c6, nd=4),
                ]
            )
            + " \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    in_jsonl = Path(args.in_jsonl)
    out_summary = Path(args.out_summary)
    out_before = Path(args.out_before)
    out_diff = Path(args.out_diff)
    out_drivers = Path(args.out_drivers)
    ms = _parse_m_list(str(args.m_list))

    if not in_jsonl.exists():
        raise SystemExit(f"Missing input: {in_jsonl}")

    cache_key = {
        "analysis": "recoding_controlc_foldm_codon_decomp",
        "version": int(SCRIPT_VERSION),
        "analysis_version": int(args.analysis_version),
        "k": int(args.k),
        "aa": str(args.aa),
        "codon_rna": str(args.codon_rna),
        "domain": str(args.domain),
        "m_list": ms,
        "min_n": int(args.min_n),
        "top_n": int(args.top_n),
        "in_jsonl": _file_fingerprint(in_jsonl),
        "out_summary": str(out_summary),
        "out_before": str(out_before),
        "out_diff": str(out_diff),
        "out_drivers": str(out_drivers),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_before, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_before}", flush=True)
        return

    # Precompute Delta_m(codon) for all codons.
    delta_by_m: dict[int, dict[str, int]] = {}
    for m in ms:
        delta_by_m[int(m)] = {codon: int(fold_codon_m(codon, MU_STAR, m=int(m)).delta) for codon in GENETIC_CODE}

    # Accumulate mean frequency differences across records.
    codons_all = list(GENETIC_CODE.keys())
    sum_dfreq_before: dict[str, float] = {c: 0.0 for c in codons_all}
    sum_dfreq_after: dict[str, float] = {c: 0.0 for c in codons_all}
    sum_dfreq_diff: dict[str, float] = {c: 0.0 for c in codons_all}

    # Optional sanity check via direct dU per record.
    dU_before_by_m: dict[int, list[float]] = {int(m): [] for m in ms}
    dU_diff_by_m: dict[int, list[float]] = {int(m): [] for m in ms}

    hb = Heartbeat(every_s=60.0, prefix="[progress] recoding_controlc_foldm_codon_decomp")
    hb.force(f"start aa={args.aa} codon={args.codon_rna} domain={args.domain} k={int(args.k)} m={','.join(str(x) for x in ms)}")

    n_lines = 0
    n_used = 0
    with in_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            if n_lines % 20000 == 0:
                hb.maybe(f"lines={n_lines} used={n_used}")
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
            if str(r.get("aa") or "") != str(args.aa):
                continue
            if str(r.get("codon_rna") or "") != str(args.codon_rna):
                continue
            if str(r.get("domain") or "") != str(args.domain):
                continue

            before_seq = r.get("before_seq_dna")
            after_seq = r.get("after_seq_dna")
            cb_seqs = r.get("control_random_cds_before_seqs_dna")
            ca_seqs = r.get("control_random_cds_after_seqs_dna")
            if not (isinstance(before_seq, str) and isinstance(after_seq, str) and isinstance(cb_seqs, list) and isinstance(ca_seqs, list)):
                continue
            if not cb_seqs or not ca_seqs:
                continue

            c_rec_b = _codon_counts(before_seq)
            c_rec_a = _codon_counts(after_seq)
            if c_rec_b is None or c_rec_a is None:
                continue
            k_cod = len(before_seq) // 3
            if k_cod != int(args.k):
                continue

            # Control counts: include only valid sequences.
            ctrl_b_list: list[dict[str, int]] = []
            ctrl_a_list: list[dict[str, int]] = []
            for s in cb_seqs:
                if not isinstance(s, str):
                    continue
                cc = _codon_counts(s)
                if cc is not None and (len(s) // 3) == k_cod:
                    ctrl_b_list.append(cc)
            for s in ca_seqs:
                if not isinstance(s, str):
                    continue
                cc = _codon_counts(s)
                if cc is not None and (len(s) // 3) == k_cod:
                    ctrl_a_list.append(cc)

            if not ctrl_b_list or not ctrl_a_list:
                continue

            sum_ctrl_b: dict[str, int] = defaultdict(int)
            for cc in ctrl_b_list:
                for codon, n in cc.items():
                    sum_ctrl_b[codon] += int(n)
            sum_ctrl_a: dict[str, int] = defaultdict(int)
            for cc in ctrl_a_list:
                for codon, n in cc.items():
                    sum_ctrl_a[codon] += int(n)

            ncb = float(len(ctrl_b_list))
            nca = float(len(ctrl_a_list))

            # Record-level dfreq.
            df_b: dict[str, float] = {}
            df_a: dict[str, float] = {}
            df_d: dict[str, float] = {}
            for codon in codons_all:
                f_rec_b = float(c_rec_b.get(codon, 0)) / float(k_cod)
                f_ctrl_b = float(sum_ctrl_b.get(codon, 0)) / (float(k_cod) * ncb)
                f_rec_a = float(c_rec_a.get(codon, 0)) / float(k_cod)
                f_ctrl_a = float(sum_ctrl_a.get(codon, 0)) / (float(k_cod) * nca)
                df_b[codon] = f_rec_b - f_ctrl_b
                df_a[codon] = f_rec_a - f_ctrl_a
                df_d[codon] = (f_rec_a - f_ctrl_a) - (f_rec_b - f_ctrl_b)

            for codon in codons_all:
                sum_dfreq_before[codon] += float(df_b[codon])
                sum_dfreq_after[codon] += float(df_a[codon])
                sum_dfreq_diff[codon] += float(df_d[codon])

            # Sanity: direct dU from counts.
            for m in ms:
                dm = delta_by_m[int(m)]
                u_rec_b = _mean_delta_from_counts(c_rec_b, k=k_cod, delta_map=dm)
                u_rec_a = _mean_delta_from_counts(c_rec_a, k=k_cod, delta_map=dm)
                u_ctrl_b = _mean([_mean_delta_from_counts(cc, k=k_cod, delta_map=dm) for cc in ctrl_b_list])
                u_ctrl_a = _mean([_mean_delta_from_counts(cc, k=k_cod, delta_map=dm) for cc in ctrl_a_list])
                if u_ctrl_b is None or u_ctrl_a is None:
                    continue
                dU_before_by_m[int(m)].append(float(u_rec_b) - float(u_ctrl_b))
                dU_diff_by_m[int(m)].append((float(u_rec_a) - float(u_rec_b)) - (float(u_ctrl_a) - float(u_ctrl_b)))

            n_used += 1

    hb.force(f"done lines={n_lines} used={n_used}")

    if n_used < int(args.min_n):
        raise SystemExit(f"Only {n_used} usable records (< min-n={int(args.min_n)}).")

    mean_dfreq_before = {c: float(sum_dfreq_before[c]) / float(n_used) for c in codons_all}
    mean_dfreq_diff = {c: float(sum_dfreq_diff[c]) / float(n_used) for c in codons_all}

    # Contributions per m.
    contrib_before_by_m: dict[int, dict[str, float]] = {int(m): {} for m in ms}
    contrib_diff_by_m: dict[int, dict[str, float]] = {int(m): {} for m in ms}
    for m in ms:
        dm = delta_by_m[int(m)]
        for codon in codons_all:
            contrib_before_by_m[int(m)][codon] = float(dm[codon]) * float(mean_dfreq_before[codon])
            contrib_diff_by_m[int(m)][codon] = float(dm[codon]) * float(mean_dfreq_diff[codon])

    # Totals and sanity.
    totals = []
    for m in ms:
        total_before = sum(contrib_before_by_m[int(m)].values())
        total_diff = sum(contrib_diff_by_m[int(m)].values())
        direct_before = statistics.mean(dU_before_by_m[int(m)]) if dU_before_by_m[int(m)] else float("nan")
        direct_diff = statistics.mean(dU_diff_by_m[int(m)]) if dU_diff_by_m[int(m)] else float("nan")
        totals.append((int(m), total_before, direct_before, total_diff, direct_diff))

    # Selection: union of top drivers per m.
    top_codons_before = _select_top_union(contrib_before_by_m, ms=ms, top_n=int(args.top_n))
    top_codons_diff = _select_top_union(contrib_diff_by_m, ms=ms, top_n=int(args.top_n))

    # m=6 -> m=8 change drivers for dU_diff (if both present).
    if 6 in ms and 8 in ms:
        delta_change = {c: float(contrib_diff_by_m[8][c]) - float(contrib_diff_by_m[6][c]) for c in codons_all}
        items = list(delta_change.items())
        items.sort(key=lambda kv: abs(float(kv[1])), reverse=True)
        top_codons_change = [c for c, _v in items[: int(args.top_n)]]
    else:
        top_codons_change = []

    # Summary text.
    m_str = ",".join(str(int(m)) for m in ms)
    lines = []
    lines.append(
        "Codon-level decomposition of Control-C paired differences in the dominant recoding stratum "
        f"({args.aa}/{args.codon_rna}/{args.domain}), "
        f"$m\\in\\{{{m_str}\\}}$, $k={int(args.k)}$, analysis version {int(args.analysis_version)}."
    )
    lines.append("Reconstruction check (sum of codon contributions vs direct mean over records):")
    for (m, total_b, direct_b, total_d, direct_d) in totals:
        lines.append(
            f"$m={m}$: $\\overline{{dU}}_{{\\mathrm{{before}}}}$={_fmt_float_signed(direct_b, nd=4)} "
            f"(sum={_fmt_float_signed(total_b, nd=4)}), "
            f"$\\overline{{dU}}_{{\\Delta}}$={_fmt_float_signed(direct_d, nd=4)} "
            f"(sum={_fmt_float_signed(total_d, nd=4)})."
        )
    write_text_atomic(out_summary, "\n".join(lines) + "\n")

    # Tables.
    before_title = "Top codon contributions to $\\overline{dU}_{\\mathrm{before}}$ (Control-C paired difference)"
    diff_title = "Top codon contributions to $\\overline{dU}_{\\Delta}$ (Control-C paired difference)"
    write_text_atomic(
        out_before,
        _latex_longtable_top(
            title=before_title,
            codons=top_codons_before,
            ms=ms,
            mean_dfreq=mean_dfreq_before,
            contrib_by_m=contrib_before_by_m,
            delta_by_m=delta_by_m,
            k=int(args.k),
            include_delta_cols=False,
        ),
    )
    write_text_atomic(
        out_diff,
        _latex_longtable_top(
            title=diff_title,
            codons=top_codons_diff,
            ms=ms,
            mean_dfreq=mean_dfreq_diff,
            contrib_by_m=contrib_diff_by_m,
            delta_by_m=delta_by_m,
            k=int(args.k),
            include_delta_cols=False,
        ),
    )

    if top_codons_change:
        drivers_title = "Top codons explaining the change in $\\overline{dU}_{\\Delta}$ contributions from $m=6$ to $m=8$"
        write_text_atomic(
            out_drivers,
            _latex_longtable_m6_to_m8(
                title=drivers_title,
                codons=top_codons_change,
                mean_dfreq=mean_dfreq_diff,
                contrib_m6=contrib_diff_by_m[6],
                contrib_m8=contrib_diff_by_m[8],
                delta6=delta_by_m[6],
                delta8=delta_by_m[8],
            ),
        )
    else:
        write_text_atomic(out_drivers, "")

    write_json_atomic(cache_meta_path(out_before), cache_meta)
    print("Wrote:", out_summary)
    print("Wrote:", out_before)
    print("Wrote:", out_diff)
    print("Wrote:", out_drivers)


if __name__ == "__main__":
    main()


