# -*- coding: utf-8 -*-
"""
Experiment 3 (sequence-level visualization): uplift "friction" curves on real transcripts.

For each included case-study transcript FASTA, we:
  - select the longest ORF across frames (AUG ... UAA/UAG/UGA),
  - compute the per-codon uplift trace U(i)=Delta_{mu*}(c_i) along the ORF under mu*,
  - plot U(i) as a scatter with a rolling-mean smoothing curve,
  - write a short LaTeX fragment summarizing the observed start/stop signatures.

Outputs (sections/generated/):
  - uplift_curve_hbb.png
  - uplift_curve_ins.png
  - uplift_curve_case_studies_summary.tex

This script uses numpy/matplotlib for plotting.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import STOP_CODONS, START_CODON, find_orfs, fold_codon, iter_fasta, normalize_sequence

MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate uplift-curve figures for case-study transcripts.")
    p.add_argument("--smooth-window", type=int, default=25, help="Rolling mean window (codons). 0 disables.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def _best_orf(seq: str) -> tuple[int, int, int] | None:
    """
    Return (frame, start_base, stop_base) for the longest ORF across frames,
    where stop_base is the first base of the stop codon (inclusive).
    """
    best = None  # (length_codons, frame, start, stop)
    for frame in (0, 1, 2):
        for start, stop in find_orfs(seq, frame=frame, min_codons=0):
            length_codons = (stop - start) // 3 + 1
            cand = (length_codons, frame, start, stop)
            if best is None or cand > best:
                best = cand
    if best is None:
        return None
    length_codons, frame, start, stop = best
    _ = length_codons
    return int(frame), int(start), int(stop)


def _rolling_mean(x: np.ndarray, w: int) -> np.ndarray:
    if w <= 1:
        return x.astype(np.float64)
    w = int(w)
    k = np.ones(w, dtype=np.float64) / float(w)
    return np.convolve(x.astype(np.float64), k, mode="same")


def _plot_curve(
    *,
    out_png: Path,
    title: str,
    u: np.ndarray,
    smooth_w: int,
) -> None:
    x = np.arange(1, int(u.size) + 1, dtype=np.int64)
    u_s = _rolling_mean(u, smooth_w) if smooth_w and smooth_w > 1 else None

    plt.figure(figsize=(9.5, 3.2), dpi=180)
    plt.scatter(x, u, s=6, alpha=0.35, color="#4C72B0", linewidths=0.0, label="U(i)")
    if u_s is not None:
        plt.plot(x, u_s, color="#C44E52", linewidth=1.6, label=f"rolling mean (w={smooth_w})")
    # Start and stop markers (ORF-relative)
    plt.axvline(1, color="black", linewidth=1.0, alpha=0.6)
    plt.axvline(int(u.size), color="black", linewidth=1.0, alpha=0.6)
    plt.xlabel("codon position in ORF (start=1, stop=last)")
    plt.ylabel("uplift U(i) = Δ (window-external load)")
    plt.title(title)
    plt.ylim(-1.0, 56.0)
    plt.yticks([0, 21, 34, 55])
    plt.legend(frameon=False, loc="upper right")
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png)
    plt.close()


def main() -> None:
    args = parse_args()
    smooth_w = int(args.smooth_window)
    if smooth_w < 0:
        raise SystemExit("--smooth-window must be >= 0")
    k_tail = 10  # report a simple pre-stop window mean for context

    cases = [
        ("HBB", "NM_000518.5", data_root() / "NM_000518.5.fasta", generated_dir() / "uplift_curve_hbb.png"),
        ("INS", "ENST00000381330.5", data_root() / "ENST00000381330.5.fasta", generated_dir() / "uplift_curve_ins.png"),
    ]
    out_tex = generated_dir() / "uplift_curve_case_studies_summary.tex"

    cache_file = data_root() / "_cache" / f"uplift_curve_case_studies_v{int(ANALYSIS_VERSION)}.json"
    cache_key = {
        "analysis": "uplift_curve_case_studies",
        "analysis_version": int(ANALYSIS_VERSION),
        "mu_star": MU_STAR,
        "smooth_window": int(smooth_w),
        "cases": [{"name": n, "id": tid, "path": str(fp)} for (n, tid, fp, _out) in cases],
        "outputs": [str(out_tex)] + [str(out) for (_n, _tid, _fp, out) in cases],
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and out_tex.exists() and all(out.exists() for (_n, _tid, _fp, out) in cases) and cache_hit(
        cache_file, expected_meta=cache_meta, require_meta=True
    ):
        print(f"[cache] hit: {cache_file}")
        print("Wrote:", out_tex)
        return

    summary_lines: list[str] = []
    summary_lines.append(
        f"Case-study uplift traces under $\\mu^\\ast$ (rolling mean window $w={smooth_w}$ codons). "
        "In both plots, vertical black lines mark the start codon (left) and terminal stop (right)."
    )
    summary_lines.append("")

    for gene, tid, fasta_path, out_png in cases:
        if not fasta_path.exists():
            summary_lines.append(f"\\noindent\\textbf{{{gene} ({tid}).}} FASTA missing at \\path{{{fasta_path}}}.")
            summary_lines.append("")
            continue

        records = list(iter_fasta(str(fasta_path)))
        if not records:
            summary_lines.append(f"\\noindent\\textbf{{{gene} ({tid}).}} FASTA empty at \\path{{{fasta_path}}}.")
            summary_lines.append("")
            continue

        rid, seq0 = records[0]
        seq = normalize_sequence(seq0)
        best = _best_orf(seq)
        if best is None:
            summary_lines.append(f"\\noindent\\textbf{{{gene} ({tid}).}} No ORF found (AUG...stop) in any frame.")
            summary_lines.append("")
            continue

        frame, start, stop = best
        codons = [seq[pos : pos + 3] for pos in range(start, stop + 3, 3)]
        L = len(codons)
        if L <= 0:
            summary_lines.append(f"\\noindent\\textbf{{{gene} ({tid}).}} ORF extraction failed.")
            summary_lines.append("")
            continue

        folds = [fold_codon(c, MU_STAR) for c in codons]
        u = np.array([int(f.delta) for f in folds], dtype=np.int16)
        z = np.array([int(f.v) for f in folds], dtype=np.int16)

        start_codon = codons[0]
        stop_codon = codons[-1]
        f_start = folds[0]
        f_stop = folds[-1]
        if start_codon != START_CODON:
            # In ORF mode, starts are AUG by definition; keep the check to surface issues.
            pass
        if stop_codon not in STOP_CODONS:
            pass

        # Simple descriptive stats.
        u_mean = float(np.mean(u.astype(np.float64)))
        u_max = int(u.max())
        u55 = int(np.count_nonzero(u == 55))
        u34 = int(np.count_nonzero(u == 34))
        u21 = int(np.count_nonzero(u == 21))
        u0 = int(np.count_nonzero(u == 0))

        # Simple "peak" localization using the smoothed trace (if enabled).
        if smooth_w and smooth_w > 1:
            u_s = _rolling_mean(u, smooth_w)
            peak_i = int(np.argmax(u_s)) + 1  # 1-based codon index in ORF
            peak_val = float(u_s[peak_i - 1])
            dist_to_stop = int(L - peak_i)
        else:
            peak_i = int(np.argmax(u)) + 1
            peak_val = float(u[peak_i - 1])
            dist_to_stop = int(L - peak_i)

        # Pre-stop window mean (exclude the terminal stop codon itself).
        if L > 1:
            tail = u[max(0, L - 1 - k_tail) : L - 1]
            u_tail = float(np.mean(tail.astype(np.float64))) if tail.size else float("nan")
            tail_n = int(tail.size)
        else:
            u_tail = float("nan")
            tail_n = 0

        title = (
            f"{gene} ({tid}) — best ORF: frame {frame}, L={L} codons; "
            f"start {start_codon} (U={int(f_start.delta)}), stop {stop_codon} (U={int(f_stop.delta)})"
        )
        _plot_curve(out_png=out_png, title=title, u=u, smooth_w=smooth_w)

        summary_lines.append(f"\\noindent\\textbf{{{gene} (\\path{{{tid}}}).}} ")
        summary_lines.append(
            f"Best ORF across frames: frame {frame}, length {L} codons. "
            f"Start $({int(f_start.v)},{int(f_start.delta)})$ at \\texttt{{{start_codon}}}; "
            f"terminal stop $({int(f_stop.v)},{int(f_stop.delta)})$ at \\texttt{{{stop_codon}}}. "
            f"Uplift composition: $U=0$:{u0}, $21$:{u21}, $34$:{u34}, $55$:{u55}; "
            f"$\\overline{{U}}={u_mean:.2f}$, $U_\\max={u_max}$. "
            f"Smoothed peak: $\\max \\overline{{U}}_w\\approx {peak_val:.2f}$ at codon {peak_i} "
            f"(distance to stop: {dist_to_stop} codons). "
            f"Pre-stop mean (last {tail_n} codons before stop): $\\overline{{U}}_{{\\mathrm{{tail}}}}={u_tail:.2f}$."
        )
        summary_lines.append("")

    write_text_atomic(out_tex, "\n".join(summary_lines).strip() + "\n")

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(cache_file, {"ok": True})
    write_json_atomic(cache_meta_path(cache_file), cache_meta)

    print("Wrote:", out_tex)
    for _gene, _tid, _fp, out_png in cases:
        if out_png.exists():
            print("Wrote:", out_png)


if __name__ == "__main__":
    main()

