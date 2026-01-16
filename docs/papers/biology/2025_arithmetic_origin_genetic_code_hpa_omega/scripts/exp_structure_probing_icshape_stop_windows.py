# -*- coding: utf-8 -*-
"""
H3-7: Structure probing cross-check at stop windows (icSHAPE .out.txt(.gz)).

This analyzes transcriptome-wide icSHAPE reactivity matrices where each row is:
  transcript_id, length, score, v1, v2, ..., vL
with per-base reactivity values or "NULL".

For each transcript (ENST...), we fetch the Ensembl cDNA sequence (type=cdna),
identify a best ORF (AUG start + canonical stop; longest ORF), then compute:
  - Uplift endpoints: U_before, U_after, ΔU
  - Probing endpoints: R_before, R_after, ΔR
in stop-proximal windows of size k codons.

Example:
  python scripts/exp_structure_probing_icshape_stop_windows.py \
    --study-id GSE132099_icSHAPE_invivo \
    --icshape-out data/probing/GSE132099/GSE132099_icSHAPE_invivo.out.txt.gz \
    --k 10 --force
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy import stats

from cache_manager import cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon, normalize_sequence
from stats_tools import cohen_d


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
CODON_DELTA = {c: int(fold_codon(c, MU_STAR).delta) for c in GENETIC_CODE}

DINUC_ORDER = [a + b for a in "ACGU" for b in "ACGU"]


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return root_dir() / "data"


def cache_dir() -> Path:
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensembl_cache_dir() -> Path:
    d = cache_dir() / "ensembl_cdna"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch_json(url: str, payload: dict[str, Any], *, timeout_s: float, retries: int, sleep_s: float) -> Any:
    body = json.dumps(payload).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(int(retries)):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "the-omega-genetic-code/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 503) and attempt + 1 < int(retries):
                time.sleep(sleep_s * float(attempt + 1))
                continue
            break
        except Exception as e:  # noqa: BLE001 - network layer raises mixed exception types
            last_err = e
            if attempt + 1 < int(retries):
                time.sleep(sleep_s * float(attempt + 1))
                continue
            break
    assert last_err is not None
    raise last_err


def fetch_ensembl_cdna(ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    missing: list[str] = []

    cdir = ensembl_cache_dir()
    for tid in ids:
        p = cdir / f"{tid}.txt"
        if not p.exists():
            missing.append(tid)
            continue
        try:
            seq = p.read_text(encoding="utf-8").strip().upper()
        except Exception:
            missing.append(tid)
            continue
        if seq:
            out[tid] = seq

    if missing:
        url = "https://rest.ensembl.org/sequence/id?type=cdna"

        def fetch_batch(batch: list[str]) -> dict[str, str]:
            if not batch:
                return {}
            try:
                arr = _fetch_json(url, {"ids": batch}, timeout_s=60.0, retries=6, sleep_s=1.5)
            except urllib.error.HTTPError as e:
                # Some batches contain retired/nonexistent IDs; split to salvage the rest.
                if e.code in (400, 404) and len(batch) > 1:
                    mid = len(batch) // 2
                    out0 = fetch_batch(batch[:mid])
                    out1 = fetch_batch(batch[mid:])
                    out0.update(out1)
                    return out0
                return {}
            except Exception:
                return {}

            got: dict[str, str] = {}
            if isinstance(arr, list):
                for obj in arr:
                    if not isinstance(obj, dict):
                        continue
                    tid = str(obj.get("id") or obj.get("query") or "").strip()
                    seq = str(obj.get("seq") or "").strip().upper()
                    if not tid or not seq:
                        continue
                    got[tid] = seq
            return got

        fetched = fetch_batch(missing)
        for tid, seq in fetched.items():
            out[tid] = seq
            try:
                write_text_atomic(cdir / f"{tid}.txt", seq + "\n")
            except Exception:
                pass
    return out


@dataclass(frozen=True)
class Orf:
    frame: int
    start_base: int
    stop_base: int  # first base of stop codon (inclusive)
    length_codons: int


def _best_orf(seq_rna: str, *, min_codons: int) -> Orf | None:
    best: Orf | None = None
    for frame in (0, 1, 2):
        for start, stop in find_orfs(seq_rna, frame=frame, min_codons=int(min_codons)):
            ln = (int(stop) - int(start)) // 3 + 1
            cand = Orf(frame=int(frame), start_base=int(start), stop_base=int(stop), length_codons=int(ln))
            if best is None or cand.length_codons > best.length_codons:
                best = cand
    return best


def _mean_delta(seq_rna: str, start: int, end: int) -> float:
    if end <= start:
        return float("nan")
    acc = 0.0
    n = 0
    for i in range(int(start), int(end), 3):
        codon = seq_rna[i : i + 3]
        d = CODON_DELTA.get(codon)
        if d is None:
            return float("nan")
        acc += float(d)
        n += 1
    if n <= 0:
        return float("nan")
    return float(acc / float(n))


def _mean_reactivity(parts: list[str], *, start0: int, end0: int, min_covered_bases: int) -> tuple[float, int]:
    if end0 <= start0:
        return (float("nan"), 0)
    acc = 0.0
    covered = 0
    # icSHAPE format: 3 leading columns, then per-base values for positions 0..L-1.
    for pos in range(int(start0), int(end0)):
        s = parts[3 + pos]
        if s == "NULL":
            continue
        try:
            v = float(s)
        except Exception:
            continue
        if math.isfinite(v):
            acc += float(v)
            covered += 1
    if covered < int(min_covered_bases):
        return (float("nan"), int(covered))
    return (float(acc / float(covered)), int(covered))


def _gc_fraction(seq_rna: str, start: int, end: int) -> float:
    if end <= start:
        return float("nan")
    s = seq_rna[int(start) : int(end)]
    denom = 0
    gc = 0
    for ch in s:
        if ch in "ACGU":
            denom += 1
            if ch in "GC":
                gc += 1
    if denom <= 0:
        return float("nan")
    return float(gc) / float(denom)


def _dinuc_freq_vec_16(seq_rna: str, start: int, end: int) -> list[float]:
    """
    16-dim dinucleotide frequency vector over A/C/G/U (lexicographic order).
    """
    if end <= start:
        return [float("nan")] * len(DINUC_ORDER)
    s = seq_rna[int(start) : int(end)]
    counts = {k: 0 for k in DINUC_ORDER}
    denom = 0
    for i in range(len(s) - 1):
        a = s[i]
        b = s[i + 1]
        if a in "ACGU" and b in "ACGU":
            counts[a + b] += 1
            denom += 1
    if denom <= 0:
        return [float("nan")] * len(DINUC_ORDER)
    return [float(counts[k]) / float(denom) for k in DINUC_ORDER]


def _spearman(x: Iterable[float], y: Iterable[float], *, min_n: int) -> dict[str, float]:
    xs = np.array(list(x), dtype=float)
    ys = np.array(list(y), dtype=float)
    m = np.isfinite(xs) & np.isfinite(ys)
    n = int(np.sum(m))
    if n < int(min_n):
        return {"n": float(n), "rho": float("nan"), "p": float("nan")}
    rho, p = stats.spearmanr(xs[m], ys[m])
    return {"n": float(n), "rho": float(rho), "p": float(p)}


def _partial_spearman(
    x: Iterable[float],
    y: Iterable[float],
    controls: list[Iterable[float]],
    *,
    min_n: int,
) -> dict[str, float]:
    xs = np.array(list(x), dtype=float)
    ys = np.array(list(y), dtype=float)
    zs = [np.array(list(z), dtype=float) for z in controls]

    m = np.isfinite(xs) & np.isfinite(ys)
    for z in zs:
        m = m & np.isfinite(z)
    n = int(np.sum(m))
    if n < int(min_n):
        return {"n": float(n), "rho": float("nan"), "p": float("nan")}

    xr = stats.rankdata(xs[m])
    yr = stats.rankdata(ys[m])
    Zr = [stats.rankdata(z[m]) for z in zs]

    X = np.column_stack([np.ones(int(n), dtype=float)] + [np.asarray(z, dtype=float) for z in Zr])
    bx = np.linalg.lstsq(X, xr, rcond=None)[0]
    by = np.linalg.lstsq(X, yr, rcond=None)[0]
    rx = xr - X @ bx
    ry = yr - X @ by

    rho, p = stats.pearsonr(rx, ry)
    return {"n": float(n), "rho": float(rho), "p": float(p)}


def _compare(xs_hi: list[float], xs_lo: list[float]) -> dict[str, float]:
    a = [float(v) for v in xs_hi if np.isfinite(v)]
    b = [float(v) for v in xs_lo if np.isfinite(v)]
    if len(a) < 10 or len(b) < 10:
        return {"n1": float(len(a)), "n2": float(len(b)), "cohens_d": float("nan"), "p": float("nan")}
    d = cohen_d(a, b)
    _, p = stats.ttest_ind(a, b, equal_var=False)
    return {"n1": float(len(a)), "n2": float(len(b)), "cohens_d": float(d) if d is not None else float("nan"), "p": float(p)}


def _fmt(x: float | None, *, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "--"
    return f"{float(x):.{nd}f}"


def _p_fmt(p: float | None) -> str:
    if p is None or (isinstance(p, float) and not np.isfinite(p)):
        return "--"
    if p < 0.001:
        return "$<$0.001"
    return f"{p:.3f}"


def main() -> None:
    ap = argparse.ArgumentParser(description="H3-7: stop-window structure probing cross-check (icSHAPE .out.txt).")
    ap.add_argument("--study-id", required=True, help="Dataset ID for table/caching and output naming.")
    ap.add_argument("--icshape-out", required=True, help="Path to icSHAPE .out.txt(.gz) file.")
    ap.add_argument("--k", type=int, default=10, help="Window size in codons.")
    ap.add_argument("--min-orf-codons", type=int, default=30, help="Minimum ORF length (codons) to consider a transcript coding.")
    ap.add_argument("--min-covered-bases", type=int, default=10, help="Minimum non-NULL bases required per window.")
    ap.add_argument("--min-n-corr", type=int, default=200, help="Minimum n required to report Spearman correlations.")
    ap.add_argument("--quantile", type=float, default=0.2, help="Quantile for high/low ΔU stratification (0<q<0.5).")
    ap.add_argument("--batch-size", type=int, default=50, help="Ensembl REST batch size (<=50 recommended).")
    ap.add_argument("--max-transcripts", type=int, default=0, help="Optional cap on number of transcripts processed (0=all).")
    ap.add_argument("--force", action="store_true", help="Overwrite existing outputs.")
    args = ap.parse_args()

    in_path = Path(str(args.icshape_out))
    if not in_path.exists():
        raise SystemExit(f"Missing icSHAPE file: {in_path}")

    study_id = str(args.study_id).strip()
    if not study_id:
        raise SystemExit("--study-id must be non-empty")

    out_tex = generated_dir() / f"structure_probing_stop_windows_{study_id}.tex"
    out_json = cache_dir() / f"structure_probing_stop_windows_{study_id}.json"
    if out_tex.exists() and out_json.exists() and not bool(args.force):
        print(f"Exists: {out_tex} (use --force to overwrite)", flush=True)
        return

    k_nt = 3 * int(args.k)
    batch_size = int(args.batch_size)
    if batch_size <= 0 or batch_size > 50:
        raise SystemExit("--batch-size must be in [1,50] for Ensembl REST")

    out_rows: list[dict[str, Any]] = []
    n_read = 0
    n_seq = 0
    n_orf = 0
    n_used = 0

    def process_lines(lines: list[str]) -> None:
        nonlocal n_seq, n_orf, n_used
        if not lines:
            return
        ids: list[str] = []
        for ln in lines:
            tid = ln.split("\t", 1)[0].strip()
            if tid:
                ids.append(tid)
        seqs = fetch_ensembl_cdna(ids)
        n_seq += int(len(seqs))

        for ln in lines:
            parts = ln.split("\t")
            if len(parts) < 4:
                continue
            tid = str(parts[0]).strip()
            if not tid:
                continue
            try:
                L = int(parts[1])
            except Exception:
                continue
            if len(parts) != 3 + L:
                continue
            seq_dna = seqs.get(tid)
            if not seq_dna:
                continue
            if len(seq_dna) != L:
                # Allow tiny length mismatches (rare); assume extra suffix bases.
                if abs(len(seq_dna) - L) <= 5:
                    seq_dna = seq_dna[:L]
                else:
                    continue

            seq_rna = normalize_sequence(seq_dna)
            orf = _best_orf(seq_rna, min_codons=int(args.min_orf_codons))
            if orf is None:
                continue
            n_orf += 1

            stop_base = int(orf.stop_base)
            start_base = int(orf.start_base)

            before_t0 = stop_base - k_nt
            before_t1 = stop_base
            after_t0 = stop_base + 3
            after_t1 = after_t0 + k_nt

            if before_t0 < start_base:
                continue
            if after_t1 > len(seq_rna):
                continue

            u_before = _mean_delta(seq_rna, before_t0, before_t1)
            u_after = _mean_delta(seq_rna, after_t0, after_t1)
            if not (np.isfinite(u_before) and np.isfinite(u_after)):
                continue

            gc_before = _gc_fraction(seq_rna, before_t0, before_t1)
            gc_after = _gc_fraction(seq_rna, after_t0, after_t1)
            if not (np.isfinite(gc_before) and np.isfinite(gc_after)):
                continue

            dinuc_before = _dinuc_freq_vec_16(seq_rna, before_t0, before_t1)
            dinuc_after = _dinuc_freq_vec_16(seq_rna, after_t0, after_t1)
            if not (all(np.isfinite(x) for x in dinuc_before) and all(np.isfinite(x) for x in dinuc_after)):
                continue

            r_before, cov_before = _mean_reactivity(
                parts,
                start0=before_t0,
                end0=before_t1,
                min_covered_bases=int(args.min_covered_bases),
            )
            r_after, cov_after = _mean_reactivity(
                parts,
                start0=after_t0,
                end0=after_t1,
                min_covered_bases=int(args.min_covered_bases),
            )
            if not (np.isfinite(r_before) and np.isfinite(r_after)):
                continue

            n_used += 1
            out_rows.append(
                {
                    "transcript_id": tid,
                    "length": int(L),
                    "orf_frame": int(orf.frame),
                    "start_base": int(start_base),
                    "stop_base": int(stop_base),
                    "stop_codon": str(seq_rna[stop_base : stop_base + 3]),
                    "u_before": float(u_before),
                    "u_after": float(u_after),
                    "diff": float(u_after - u_before),
                    "gc_before": float(gc_before),
                    "gc_after": float(gc_after),
                    "dinuc_before": [float(x) for x in dinuc_before],
                    "dinuc_after": [float(x) for x in dinuc_after],
                    "react_before": float(r_before),
                    "react_after": float(r_after),
                    "react_diff": float(r_after - r_before),
                    "covered_before": int(cov_before),
                    "covered_after": int(cov_after),
                }
            )

    opener = gzip.open if in_path.name.lower().endswith(".gz") else open
    lines: list[str] = []
    max_tx = int(args.max_transcripts)
    with opener(in_path, "rt", encoding="utf-8", errors="replace") as f:
        for ln in f:
            if max_tx > 0 and n_read >= max_tx:
                break
            ln = ln.rstrip("\n")
            if not ln:
                continue
            lines.append(ln)
            n_read += 1
            if len(lines) >= batch_size:
                process_lines(lines)
                lines = []
    if lines:
        process_lines(lines)

    corr = {
        "react_before_vs_u_before": _spearman(
            [rr["react_before"] for rr in out_rows],
            [rr["u_before"] for rr in out_rows],
            min_n=int(args.min_n_corr),
        ),
        "react_diff_vs_diff": _spearman(
            [rr["react_diff"] for rr in out_rows],
            [rr["diff"] for rr in out_rows],
            min_n=int(args.min_n_corr),
        ),
    }
    corr_partial = {
        "react_before_vs_u_before_gc": _partial_spearman(
            [rr["react_before"] for rr in out_rows],
            [rr["u_before"] for rr in out_rows],
            [[rr["gc_before"] for rr in out_rows]],
            min_n=int(args.min_n_corr),
        ),
        "react_diff_vs_diff_gc": _partial_spearman(
            [rr["react_diff"] for rr in out_rows],
            [rr["diff"] for rr in out_rows],
            [[rr["gc_before"] for rr in out_rows], [rr["gc_after"] for rr in out_rows]],
            min_n=int(args.min_n_corr),
        ),
        "react_before_vs_u_before_dinuc": _partial_spearman(
            [rr["react_before"] for rr in out_rows],
            [rr["u_before"] for rr in out_rows],
            [[rr["dinuc_before"][j] for rr in out_rows] for j in range(len(DINUC_ORDER))],
            min_n=int(args.min_n_corr),
        ),
        "react_diff_vs_diff_dinuc": _partial_spearman(
            [rr["react_diff"] for rr in out_rows],
            [rr["diff"] for rr in out_rows],
            (
                [[rr["dinuc_before"][j] for rr in out_rows] for j in range(len(DINUC_ORDER))]
                + [[rr["dinuc_after"][j] for rr in out_rows] for j in range(len(DINUC_ORDER))]
            ),
            min_n=int(args.min_n_corr),
        ),
    }

    diffs = np.array([float(rr["diff"]) for rr in out_rows if np.isfinite(float(rr["diff"]))], dtype=float)
    comps: dict[str, dict[str, float]] = {}
    q = float(args.quantile)
    if len(diffs) >= 50 and 0.0 < q < 0.5:
        lo = float(np.quantile(diffs, q))
        hi = float(np.quantile(diffs, 1.0 - q))
        xs_hi = [float(rr["react_diff"]) for rr in out_rows if np.isfinite(float(rr["react_diff"])) and float(rr["diff"]) >= hi]
        xs_lo = [float(rr["react_diff"]) for rr in out_rows if np.isfinite(float(rr["react_diff"])) and float(rr["diff"]) <= lo]
        comps["high_diff_vs_low_diff"] = _compare(xs_hi, xs_lo)

    out = {
        "study_id": study_id,
        "icshape_out": str(in_path),
        "k_codons": int(args.k),
        "min_orf_codons": int(args.min_orf_codons),
        "min_covered_bases": int(args.min_covered_bases),
        "min_n_corr": int(args.min_n_corr),
        "quantile": float(args.quantile),
        "batch_size": int(args.batch_size),
        "max_transcripts": int(args.max_transcripts),
        "n_read": int(n_read),
        "n_sequences_fetched": int(n_seq),
        "n_with_orf": int(n_orf),
        "n_used": int(n_used),
        "correlations": corr,
        "partial_correlations": corr_partial,
        "pairwise_comparisons": comps,
        "rows": out_rows,
    }
    write_json_atomic(out_json, out)

    comp = comps.get("high_diff_vs_low_diff", {})
    lines_tex: list[str] = [
        "\\paragraph{Structure probing cross-check (icSHAPE transcriptome reactivity).}",
        "We analyzed a transcriptome-wide icSHAPE reactivity matrix (per-transcript, per-base) and computed mean reactivity in stop-proximal windows (k codons) using Ensembl cDNA sequences to locate the best-ORF terminal stop.",
        "We report correlations against Uplift window endpoints and a stratified effect size on the probing window difference $\\Delta R = R_{\\mathrm{after}}-R_{\\mathrm{before}}$ (top vs bottom quantiles of $\\Delta U$).",
        "",
        "\\begin{center}\\small",
        "\\begin{tabular}{lrrrrr}\\toprule",
        "Dataset & $n$ & $\\rho(R_{\\mathrm{before}}, U_{\\mathrm{before}})$ & $\\rho(\\Delta R,\\Delta U)$ & $d(\\Delta U\\uparrow\\downarrow;\\Delta R)$ & $p$ \\\\",
        "\\midrule",
        f"\\path{{{study_id}}} & {int(n_used)} & "
        f"{_fmt(corr['react_before_vs_u_before'].get('rho'))} & "
        f"{_fmt(corr['react_diff_vs_diff'].get('rho'))} & "
        f"{_fmt(comp.get('cohens_d'), nd=2)} & {_p_fmt(comp.get('p'))} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
    ]
    pc1 = corr_partial.get("react_before_vs_u_before_gc", {})
    pc2 = corr_partial.get("react_diff_vs_diff_gc", {})
    pc3 = corr_partial.get("react_before_vs_u_before_dinuc", {})
    pc4 = corr_partial.get("react_diff_vs_diff_dinuc", {})
    if np.isfinite(float(pc1.get("rho", float("nan")))) or np.isfinite(float(pc2.get("rho", float("nan")))):
        lines_tex.append(
            "\\emph{GC-controlled partial correlations:} "
            f"$\\rho(R_{{\\mathrm{{before}}}},U_{{\\mathrm{{before}}}}\\mid GC_{{\\mathrm{{before}}}})={_fmt(pc1.get('rho'))}$; "
            f"$\\rho(\\Delta R,\\Delta U\\mid GC_{{\\mathrm{{before}}}},GC_{{\\mathrm{{after}}}})={_fmt(pc2.get('rho'))}$."
        )
    if np.isfinite(float(pc3.get("rho", float("nan")))) or np.isfinite(float(pc4.get("rho", float("nan")))):
        lines_tex.append(
            "\\emph{Dinucleotide-controlled partial correlations:} "
            f"$\\rho(R_{{\\mathrm{{before}}}},U_{{\\mathrm{{before}}}}\\mid \\mathrm{{dinuc}}_{{\\mathrm{{before}}}})={_fmt(pc3.get('rho'))}$; "
            f"$\\rho(\\Delta R,\\Delta U\\mid \\mathrm{{dinuc}}_{{\\mathrm{{before}}}},\\mathrm{{dinuc}}_{{\\mathrm{{after}}}})={_fmt(pc4.get('rho'))}$."
        )

    write_text_atomic(out_tex, "\n".join(lines_tex) + "\n")
    meta_key = {
        "analysis": "structure_probing_icshape_stop_windows",
        "study_id": study_id,
        "k": int(args.k),
        "min_orf_codons": int(args.min_orf_codons),
        "min_covered_bases": int(args.min_covered_bases),
        "min_n_corr": int(args.min_n_corr),
        "quantile": float(args.quantile),
        "batch_size": int(args.batch_size),
        "max_transcripts": int(args.max_transcripts),
        "icshape_out": str(in_path),
    }
    write_json_atomic(cache_meta_path(out_tex), {**meta_key, "cache_digest": cache_key_digest(meta_key)})

    print(f"Wrote: {out_tex}", flush=True)


if __name__ == "__main__":
    main()
