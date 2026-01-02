# -*- coding: utf-8 -*-
"""
Mechanistic follow-up: GC-coupling of Control-C paired differences across Fold_m (standard library only).

We focus on the dominant stratum driving Control-C AUC flips:
  - aa = Sec
  - codon_rna = UGA
  - domain = Eukaryota

For each record i, we compute paired differences between recoding windows and the
within-CDS random internal controls (Control-C), for each m:
  U_before:  dU_before(i,m) = U_rec_before(i,m) - U_ctrl_before(i,m)
  U_diff:    dU_diff(i,m)   = (U_rec_after-U_rec_before) - (U_ctrl_after-U_ctrl_before)

We also compute paired GC differences:
  dGC_before(i) = GC_rec_before - mean(GC_ctrl_before_seqs)
  dGC_diff(i)   = (GC_rec_after-GC_rec_before) - (mean(GC_ctrl_after)-mean(GC_ctrl_before))

We then summarize, for each m:
  - mean/median of dU
  - sign-positive rate of dU
  - Pearson/Spearman correlation between dU and dGC

Outputs:
  - sections/generated/recoding_controlc_foldm_gc_coupling_summary.tex
  - sections/generated/recoding_controlc_foldm_gc_coupling_table.tex
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
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


def _fmt_percent(x: object, *, nd: int = 1) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}\\%"


def _sign(x: float, *, eps: float = 1e-12) -> int:
    if abs(float(x)) <= float(eps):
        return 0
    return 1 if float(x) > 0 else -1


def _gc_fraction(seq_dna: str) -> float | None:
    s = str(seq_dna).upper()
    if not s:
        return None
    if any(ch not in "ACGT" for ch in s):
        return None
    gc = sum(1 for ch in s if ch in ("G", "C"))
    return float(gc) / float(len(s))


def _mean_delta_from_window_seq(seq_dna: str, *, m: int, delta_table: dict[int, dict[str, int]]) -> float | None:
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


def _pearsonr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys):
        raise ValueError("length mismatch")
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / float(n)
    my = sum(ys) / float(n)
    sxx = 0.0
    syy = 0.0
    sxy = 0.0
    for x, y in zip(xs, ys):
        dx = float(x) - mx
        dy = float(y) - my
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy
    if sxx <= 0.0 or syy <= 0.0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _rankdata(values: list[float]) -> list[float]:
    n = len(values)
    pairs = [(float(v), i) for i, v in enumerate(values)]
    pairs.sort(key=lambda x: x[0])
    ranks = [0.0] * n
    i = 0
    rank = 1
    while i < n:
        j = i + 1
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        r_lo = rank
        r_hi = rank + (j - i) - 1
        r_avg = 0.5 * (float(r_lo) + float(r_hi))
        for k in range(i, j):
            _v, idx = pairs[k]
            ranks[idx] = r_avg
        rank += (j - i)
        i = j
    return ranks


def _spearmanr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys):
        raise ValueError("length mismatch")
    if len(xs) < 2:
        return None
    rx = _rankdata(xs)
    ry = _rankdata(ys)
    return _pearsonr(rx, ry)


@dataclass(frozen=True)
class PairRow:
    dU_before: float
    dU_diff: float
    dGC_before: float
    dGC_diff: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GC coupling of Control-C paired differences across Fold_m (Sec/UGA/Eukaryota subset).")
    p.add_argument("--in-jsonl", default=str(recoding_jsonl_default()), help="Input recoding_sites.jsonl.")
    p.add_argument("--analysis-version", type=int, default=7, help="Filter: analysis_version.")
    p.add_argument("--k", type=int, default=10, help="Filter: k.")
    p.add_argument("--m-list", default="6,7,8", help="Comma-separated m values to analyze.")
    p.add_argument("--min-n", type=int, default=200, help="Minimum paired samples required to report.")
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "recoding_controlc_foldm_gc_coupling_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "recoding_controlc_foldm_gc_coupling_table.tex"),
        help="Output LaTeX table fragment path.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_jsonl = Path(args.in_jsonl)
    out_summary = Path(args.out_summary)
    out_table = Path(args.out_table)
    ms = _parse_m_list(str(args.m_list))
    if not in_jsonl.exists():
        raise SystemExit(f"Missing input: {in_jsonl}")

    cache_key = {
        "analysis": "recoding_controlc_foldm_gc_coupling",
        "version": int(SCRIPT_VERSION),
        "analysis_version": int(args.analysis_version),
        "k": int(args.k),
        "m_list": ms,
        "min_n": int(args.min_n),
        "in_jsonl": _file_fingerprint(in_jsonl),
        "out_summary": str(out_summary),
        "out_table": str(out_table),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_table, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_table}", flush=True)
        return

    # Precompute delta tables.
    delta_table: dict[int, dict[str, int]] = {}
    for m in ms:
        delta_table[int(m)] = {codon: int(fold_codon_m(codon, MU_STAR, m=int(m)).delta) for codon in GENETIC_CODE}

    hb = Heartbeat(every_s=60.0, prefix="[progress] recoding_controlc_foldm_gc_coupling")
    hb.force(f"start av={int(args.analysis_version)} k={int(args.k)} m={','.join(str(x) for x in ms)}")

    # per m -> list of PairRow (dU computed for that m)
    pairs_by_m: dict[int, list[PairRow]] = {int(m): [] for m in ms}

    n_lines = 0
    n_keep = 0
    with in_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            if n_lines % 20000 == 0:
                hb.maybe(f"lines={n_lines} keep={n_keep}")
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
            if str(r.get("aa") or "") != "Sec":
                continue
            if str(r.get("domain") or "") != "Eukaryota":
                continue
            if str(r.get("codon_rna") or "") != "UGA":
                continue

            before_seq = r.get("before_seq_dna")
            after_seq = r.get("after_seq_dna")
            cb_seqs = r.get("control_random_cds_before_seqs_dna")
            ca_seqs = r.get("control_random_cds_after_seqs_dna")
            if not (isinstance(before_seq, str) and isinstance(after_seq, str)):
                continue
            if not (isinstance(cb_seqs, list) and isinstance(ca_seqs, list) and cb_seqs and ca_seqs):
                continue

            # Paired GC stats.
            gc_b = _gc_fraction(before_seq)
            gc_a = _gc_fraction(after_seq)
            if gc_b is None or gc_a is None:
                continue
            n_pair = min(len(cb_seqs), len(ca_seqs))
            if n_pair <= 0:
                continue
            gc_cb_vals: list[float] = []
            gc_ca_vals: list[float] = []
            for i in range(n_pair):
                sb = cb_seqs[i]
                sa = ca_seqs[i]
                if not isinstance(sb, str) or not isinstance(sa, str):
                    continue
                gb = _gc_fraction(sb)
                ga = _gc_fraction(sa)
                if gb is not None:
                    gc_cb_vals.append(float(gb))
                if ga is not None:
                    gc_ca_vals.append(float(ga))
            if not gc_cb_vals or not gc_ca_vals:
                continue
            gc_cb = sum(gc_cb_vals) / float(len(gc_cb_vals))
            gc_ca = sum(gc_ca_vals) / float(len(gc_ca_vals))
            dgc_before = float(gc_b) - float(gc_cb)
            dgc_diff = (float(gc_a) - float(gc_b)) - (float(gc_ca) - float(gc_cb))

            # For each m compute paired dU.
            for m in ms:
                b = _mean_delta_from_window_seq(before_seq, m=int(m), delta_table=delta_table)
                a = _mean_delta_from_window_seq(after_seq, m=int(m), delta_table=delta_table)
                if b is None or a is None:
                    continue
                # control averages per m
                cb_vals: list[float] = []
                ca_vals: list[float] = []
                for i in range(n_pair):
                    sb = cb_seqs[i]
                    sa = ca_seqs[i]
                    if not isinstance(sb, str) or not isinstance(sa, str):
                        continue
                    b0 = _mean_delta_from_window_seq(sb, m=int(m), delta_table=delta_table)
                    a0 = _mean_delta_from_window_seq(sa, m=int(m), delta_table=delta_table)
                    if b0 is not None:
                        cb_vals.append(float(b0))
                    if a0 is not None:
                        ca_vals.append(float(a0))
                if not cb_vals or not ca_vals:
                    continue
                cb_mean = sum(cb_vals) / float(len(cb_vals))
                ca_mean = sum(ca_vals) / float(len(ca_vals))
                du_before = float(b) - float(cb_mean)
                du_diff = (float(a) - float(b)) - (float(ca_mean) - float(cb_mean))
                pairs_by_m[int(m)].append(PairRow(dU_before=du_before, dU_diff=du_diff, dGC_before=dgc_before, dGC_diff=dgc_diff))

            n_keep += 1

    hb.force(f"done lines={n_lines} kept={n_keep}")

    # Summarize per m.
    rows: list[dict[str, object]] = []
    for m in ms:
        ps = pairs_by_m[int(m)]
        if len(ps) < int(args.min_n):
            continue

        dU_b = [p.dU_before for p in ps]
        dU_d = [p.dU_diff for p in ps]
        dGC_b = [p.dGC_before for p in ps]
        dGC_d = [p.dGC_diff for p in ps]

        def _median(xs: list[float]) -> float:
            return float(statistics.median(xs)) if xs else 0.0

        def _pos_rate(xs: list[float]) -> float:
            if not xs:
                return 0.0
            return float(sum(1 for x in xs if _sign(x) > 0)) / float(len(xs))

        rows.append(
            {
                "m": int(m),
                "n": int(len(ps)),
                "mean_dgc_before": float(sum(dGC_b) / float(len(dGC_b))),
                "mean_dgc_diff": float(sum(dGC_d) / float(len(dGC_d))),
                "before_mean_du": float(sum(dU_b) / float(len(dU_b))),
                "before_med_du": _median(dU_b),
                "before_pos": _pos_rate(dU_b),
                "before_pearson": _pearsonr(dU_b, dGC_b),
                "before_spearman": _spearmanr(dU_b, dGC_b),
                "diff_mean_du": float(sum(dU_d) / float(len(dU_d))),
                "diff_med_du": _median(dU_d),
                "diff_pos": _pos_rate(dU_d),
                "diff_pearson": _pearsonr(dU_d, dGC_d),
                "diff_spearman": _spearmanr(dU_d, dGC_d),
            }
        )

    if not rows:
        raise SystemExit("No rows met min-n; consider lowering --min-n.")

    rows.sort(key=lambda r: int(r["m"]))

    m_str = ",".join(str(int(m)) for m in ms)
    s = (
        "GC coupling of Control-C paired differences in the dominant recoding stratum (Sec/UGA/Eukaryota): "
        f"$m\\in\\{{{m_str}\\}}$, $k={int(args.k)}$, analysis version {int(args.analysis_version)}."
    )
    write_text_atomic(out_summary, s + "\n")

    # LaTeX table.
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{r r r r r r r r r r r r}")
    lines.append("\\toprule")
    lines.append(
        "$m$ & $n$ & $\\overline{dGC}_{\\mathrm{before}}$ & $\\overline{dGC}_{\\Delta}$ & "
        "$\\overline{dU}_{\\mathrm{before}}$ & med & $\\%\\,dU_{\\mathrm{before}}>0$ & $r$ & $\\rho$ & "
        "$\\overline{dU}_{\\Delta}$ & med & $\\%\\,dU_{\\Delta}>0$ \\\\"
    )
    lines.append("\\midrule")
    for r in rows:
        lines.append(
            f"{int(r['m'])} & {int(r['n'])} & {_fmt_float_signed(r['mean_dgc_before'], nd=4)} & {_fmt_float_signed(r['mean_dgc_diff'], nd=4)} & "
            f"{_fmt_float_signed(r['before_mean_du'], nd=4)} & {_fmt_float_signed(r['before_med_du'], nd=4)} & {_fmt_percent(100.0*float(r['before_pos']), nd=1)} & "
            f"{_fmt_float(r['before_pearson'], nd=3)} & {_fmt_float(r['before_spearman'], nd=3)} & "
            f"{_fmt_float_signed(r['diff_mean_du'], nd=4)} & {_fmt_float_signed(r['diff_med_du'], nd=4)} & {_fmt_percent(100.0*float(r['diff_pos']), nd=1)} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")
    write_text_atomic(out_table, "\n".join(lines) + "\n")

    write_json_atomic(cache_meta_path(out_table), cache_meta)
    print("Wrote:", out_summary)
    print("Wrote:", out_table)


if __name__ == "__main__":
    main()



