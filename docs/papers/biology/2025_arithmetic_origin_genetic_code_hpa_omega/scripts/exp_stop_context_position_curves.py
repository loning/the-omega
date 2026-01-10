# -*- coding: utf-8 -*-
"""
Position-decomposed stop-context curves for terminal stops (Reinforcement 4).

Motivation:
  Window means u_before/u_after can be criticized as "mixing many positions".
  This script computes the mean uplift at each relative position j around terminal
  stop codons, producing shape evidence:

    U_before(s; j) = mean over terminal stops of stop class s of U(i-j)
    U_after(s;  j) = mean over terminal stops of stop class s of U(i+j)

  where i is the terminal stop codon index (in-frame), and U is Δ under μ*.

Dataset:
  Human RefSeq mRNA FASTA shards (data/refseq_hsapiens_mrna/human.*.rna.fna.gz),
  using the best ORF per transcript across frames (same rule as exp_refseq_transcriptome.py).

Outputs:
  - sections/generated/stop_context_position_curves_summary.tex
  - sections/generated/stop_context_position_curves.png
  - data/_cache/stop_context_position_curves_v1.json (+ meta)

Standard library + matplotlib for plotting.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic
from genetic_code_tools import GENETIC_CODE, START_CODON, STOP_CODONS, iter_fasta
from progress_tools import Heartbeat
from stats_tools import bh_fdr, normal_two_sided_p

# Reuse mu* codon Δ values and the best-ORF rule from the RefSeq pipeline.
from exp_refseq_transcriptome import CODON_INFO, best_orf_across_frames


ANALYSIS_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_dir() -> Path:
    return root_dir() / "data" / "refseq_hsapiens_mrna"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def read_manifest_refseq_shards() -> list[Path]:
    mp = root_dir() / "data" / "manifest.json"
    try:
        obj = json.loads(mp.read_text(encoding="utf-8"))
        ds = obj.get("datasets", {}).get("refseq_hsapiens_mrna", {})
        files = ds.get("files", []) or []
        out: list[Path] = []
        for e in files:
            name = e.get("name")
            if not name:
                continue
            out.append(data_dir() / str(name))
        if out:
            return out
    except Exception:
        pass
    return sorted(data_dir().glob("human.*.rna.fna.gz"))


@dataclass
class RunningStats:
    n: int = 0
    mean: float = 0.0
    M2: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        d2 = x - self.mean
        self.M2 += d * d2

    def sample_variance(self) -> float:
        if self.n <= 1:
            return 0.0
        return self.M2 / (self.n - 1)


def _z_p_from_stats(m1: float, v1: float, n1: int, m2: float, v2: float, n2: int) -> tuple[float, float] | None:
    """
    Large-n normal approximation for difference in means.
    Returns (z, p_two_sided) or None if insufficient data.
    """
    if n1 < 2 or n2 < 2:
        return None
    se2 = float(v1) / float(n1) + float(v2) / float(n2)
    if se2 <= 0:
        return None
    z = (float(m2) - float(m1)) / math.sqrt(se2)
    return float(z), float(normal_two_sided_p(float(z)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k-max", type=int, default=60, help="Max relative position j for curves (j=1..k_max).")
    ap.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat interval.")
    ap.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Optional cap on total FASTA records scanned (0 means no cap).",
    )
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    k_max = int(args.k_max)
    max_records = int(args.max_records)

    out_json = cache_dir() / "stop_context_position_curves_v1.json"
    out_sum = generated_dir() / "stop_context_position_curves_summary.tex"
    out_png = generated_dir() / "stop_context_position_curves.png"

    cache_key = {
        "analysis": "stop_context_position_curves",
        "analysis_version": ANALYSIS_VERSION,
        "k_max": k_max,
        "max_records": max_records,
    }
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        write_text(out_sum, str(obj["latex_summary"]) + "\n")
        # Re-render plot deterministically from cached means.
        _write_plot(out_png, obj)
        return

    shards = read_manifest_refseq_shards()
    if not shards:
        raise FileNotFoundError("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/")

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] stop_pos_curves")

    # stats[side][stop][j] where side in {"before","after"}, stop in STOP_CODONS, j in 1..k_max.
    stats: dict[str, dict[str, list[RunningStats]]] = {
        "before": {s: [RunningStats() for _ in range(k_max + 1)] for s in STOP_CODONS},
        "after": {s: [RunningStats() for _ in range(k_max + 1)] for s in STOP_CODONS},
    }
    n_scanned = 0
    n_with_orf = 0
    n_with_stop = 0

    for sp in shards:
        for rid, seq in iter_fasta(str(sp)):
            n_scanned += 1
            if max_records > 0 and n_scanned > max_records:
                break
            hb.maybe(f"scan={n_scanned} file={sp.name} with_orf={n_with_orf} with_stop={n_with_stop}")

            best = best_orf_across_frames(seq)
            if best is None:
                continue
            n_with_orf += 1
            start_base = int(best.start_base)
            stop_base = int(best.stop_base)
            stop_codon = seq[stop_base : stop_base + 3]
            if stop_codon not in STOP_CODONS:
                continue
            n_with_stop += 1

            # Sanity: ensure start codon at the ORF start.
            if seq[start_base : start_base + 3] != START_CODON:
                continue

            # Before-stop positions: within CDS.
            for j in range(1, k_max + 1):
                pos = stop_base - 3 * j
                if pos < start_base:
                    break
                codon = seq[pos : pos + 3]
                if codon not in GENETIC_CODE or GENETIC_CODE[codon] == "Stop":
                    break
                u = float(CODON_INFO[codon]["delta"])
                stats["before"][stop_codon][j].update(u)

            # After-stop positions: codons in the same frame downstream of the stop.
            after0 = stop_base + 3
            for j in range(1, k_max + 1):
                pos = after0 + 3 * (j - 1)
                if pos + 3 > len(seq):
                    break
                codon = seq[pos : pos + 3]
                if codon not in GENETIC_CODE:
                    break
                # In UTR this may incidentally be a stop; keep it (we are in "codon-tiling" mode).
                u = float(CODON_INFO[codon]["delta"])
                stats["after"][stop_codon][j].update(u)

        if max_records > 0 and n_scanned > max_records:
            break

    # Convert stats to plain dicts.
    curves = {}
    for side in ("before", "after"):
        curves[side] = {}
        for stop in STOP_CODONS:
            means = [0.0] * (k_max + 1)
            vars_ = [0.0] * (k_max + 1)
            ns = [0] * (k_max + 1)
            for j in range(1, k_max + 1):
                rs = stats[side][stop][j]
                means[j] = float(rs.mean)
                vars_[j] = float(rs.sample_variance())
                ns[j] = int(rs.n)
            curves[side][stop] = {"mean": means, "var": vars_, "n": ns}

    # Per-position tests (normal approx) + BH-FDR across j for each (side, comparison).
    comparisons = [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]
    tests = {}
    summary_bits: list[str] = []

    def _comp_key(a: str, b: str) -> str:
        return f"{a}_vs_{b}"

    for side in ("before", "after"):
        tests[side] = {}
        for a, b in comparisons:
            pvals: list[float] = []
            diffs: list[float] = []
            zs: list[float] = []
            js: list[int] = []
            for j in range(1, k_max + 1):
                ca = curves[side][a]
                cb = curves[side][b]
                ma, va, na = float(ca["mean"][j]), float(ca["var"][j]), int(ca["n"][j])
                mb, vb, nb = float(cb["mean"][j]), float(cb["var"][j]), int(cb["n"][j])
                diffs.append(mb - ma)
                js.append(j)
                zp = _z_p_from_stats(ma, va, na, mb, vb, nb)
                if zp is None:
                    zs.append(0.0)
                    pvals.append(1.0)
                else:
                    z, p = zp
                    zs.append(float(z))
                    pvals.append(float(p))
            qvals = bh_fdr(pvals)
            tests[side][_comp_key(a, b)] = {
                "j": js,
                "diff": diffs,
                "z": zs,
                "p": pvals,
                "q": qvals,
            }

            # Pre-registered summary: position of maximal absolute difference.
            j_best = 1
            best_abs = -1.0
            for j in range(1, k_max + 1):
                if abs(diffs[j - 1]) > best_abs:
                    best_abs = abs(diffs[j - 1])
                    j_best = j
            idx = j_best - 1
            summary_bits.append(
                f"{side} {_comp_key(a,b)}: max|diff| at j={j_best} (diff={diffs[idx]:+.3f}, q={qvals[idx]:.3g});"
                f" j=1 diff={diffs[0]:+.3f} (q={qvals[0]:.3g})."
            )

    latex_summary = (
        f"Position-decomposed stop-context curves under $\\mu^\\ast$ (Human RefSeq mRNA; best ORF per transcript)."
        f" Relative positions $j=1..{k_max}$ (codons) around terminal stops."
        f" Records scanned={n_scanned}, with ORF={n_with_orf}, with terminal stop={n_with_stop}."
        " Per-position tests use a normal approximation for mean differences, with BH-FDR across $j$ for each comparison."
        "\n"
        + " ".join(summary_bits)
    )

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "k_max": k_max,
        "max_records": max_records,
        "n_scanned": n_scanned,
        "n_with_orf": n_with_orf,
        "n_with_stop": n_with_stop,
        "curves": curves,
        "tests": tests,
        "latex_summary": latex_summary,
        "figure": str(out_png).replace("\\", "/"),
    }
    write_json_atomic(out_json, obj)
    write_json_atomic(cache_meta_path(out_json), expected_meta)
    write_text(out_sum, latex_summary + "\n")
    _write_plot(out_png, obj)

    print(f"Wrote: {out_sum}")
    print(f"Wrote: {out_png}")
    print(f"Wrote: {out_json}")


def _write_plot(path: Path, obj: dict[str, object]) -> None:
    curves = obj.get("curves", {}) or {}
    k_max = int(obj.get("k_max", 0) or 0)
    if k_max <= 0:
        return

    # Plot only the first 30 positions by default (better readability); still computed to k_max.
    k_plot = min(30, k_max)
    xs = list(range(1, k_plot + 1))

    colors = {"UAA": "#4C78A8", "UAG": "#F58518", "UGA": "#54A24B"}

    fig = plt.figure(figsize=(7.2, 5.0), dpi=160)
    ax1 = fig.add_subplot(2, 1, 1)
    ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)

    for stop in STOP_CODONS:
        c_before = curves.get("before", {}).get(stop, {}) or {}
        c_after = curves.get("after", {}).get(stop, {}) or {}
        mb = [float(c_before.get("mean", [0.0])[j]) for j in xs]
        ma = [float(c_after.get("mean", [0.0])[j]) for j in xs]
        ax1.plot(xs, mb, label=stop, color=colors.get(stop, None), linewidth=2.0)
        ax2.plot(xs, ma, label=stop, color=colors.get(stop, None), linewidth=2.0)

    ax1.set_title("Terminal-stop position curves: $\\bar U_{before}(s;j)$ (RefSeq)")
    ax1.set_ylabel("mean $U$ (Δ)")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="upper right", frameon=False)

    ax2.set_title("Terminal-stop position curves: $\\bar U_{after}(s;j)$ (RefSeq)")
    ax2.set_xlabel("relative codon position $j$")
    ax2.set_ylabel("mean $U$ (Δ)")
    ax2.grid(True, alpha=0.25)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    main()

