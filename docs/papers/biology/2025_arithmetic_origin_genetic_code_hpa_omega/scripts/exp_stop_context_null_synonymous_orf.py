# -*- coding: utf-8 -*-
"""
Protein-preserving synonymous-codon permutation null for stop-context uplift windows.

Goal (Reinforcement 3A):
  Test whether terminal-stop window statistics (e.g. U_before at k=10) can be
  explained purely by the protein sequence (and the within-ORF codon-usage
  multiset), by permuting synonymous codons *within each ORF* while keeping the
  amino-acid sequence fixed.

Null model implemented here:
  For each ORF, for each amino acid AA, the multiset of codons used for AA in the ORF
  is kept fixed, and is uniformly permuted across AA-positions.
  We do not materialize full permuted sequences; for the last-k codons before the
  terminal stop, this is equivalent to sampling without replacement from each AA pool.

Outputs:
  - sections/generated/stop_context_synonymous_null_summary.tex
  - sections/generated/stop_context_synonymous_null_hist.png
  - data/_cache/stop_context_synonymous_null_v1.json (+ meta)

This script is standard-library except for matplotlib (for the figure).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic
from genetic_code_tools import GENETIC_CODE, STOP_CODONS, iter_fasta
from progress_tools import Heartbeat

# Reuse the same mu* codon Fold_6 attributes as the main RefSeq pipeline.
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


def _stable_u64(tag: str) -> int:
    h = hashlib.sha256(tag.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def read_manifest_refseq_shards() -> list[Path]:
    """
    Return FASTA shard paths listed in data/manifest.json (fallback: local scan).
    """
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


@dataclass(frozen=True)
class OrfWindowItem:
    rid: str
    stop_codon: str
    k: int
    u_before_obs: float
    # For each AA that appears in the window: (m, pool_deltas list)
    aa_m_and_pool: dict[str, tuple[int, list[int]]]


def _window_codons_before_stop(seq: str, *, start_base: int, stop_base: int, k: int) -> list[str] | None:
    """
    Return the k codons immediately before the stop codon.
    Assumes seq is normalized RNA alphabet and start/stop are in-frame.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    # stop_base is first base of stop codon.
    win_start = stop_base - 3 * k
    win_end = stop_base  # exclusive
    if win_start < start_base:
        return None
    if win_end > len(seq):
        return None
    codons = [seq[i : i + 3] for i in range(win_start, win_end, 3)]
    if len(codons) != k:
        return None
    if any(c not in GENETIC_CODE for c in codons):
        return None
    if any(GENETIC_CODE[c] == "Stop" for c in codons):
        # Internal stop: shouldn't happen in a valid ORF, but be strict.
        return None
    return codons


def _collect_orf_item(seq: str, *, rid: str, k: int) -> OrfWindowItem | None:
    """
    Extract the best ORF and the terminal-stop before-window statistics plus AA pools
    needed for the synonymous-permutation null.
    """
    best = best_orf_across_frames(seq)
    if best is None:
        return None
    if best.length_codons_including_stop < k + 1:
        return None

    start_base = int(best.start_base)
    stop_base = int(best.stop_base)
    stop_codon = seq[stop_base : stop_base + 3]
    if stop_codon not in STOP_CODONS:
        return None

    win_codons = _window_codons_before_stop(seq, start_base=start_base, stop_base=stop_base, k=k)
    if win_codons is None:
        return None

    # Observed U_before.
    deltas_obs = [int(CODON_INFO[c]["delta"]) for c in win_codons]
    u_before_obs = float(sum(deltas_obs)) / float(k)

    # AA multiset in the window.
    aa_counts_window: dict[str, int] = {}
    aa_set_window: set[str] = set()
    for c in win_codons:
        aa = str(CODON_INFO[c]["aa"])
        aa_set_window.add(aa)
        aa_counts_window[aa] = aa_counts_window.get(aa, 0) + 1

    # Pool deltas per AA across the whole CDS (excluding stop), but only for AAs in the window.
    aa_pools: dict[str, list[int]] = {aa: [] for aa in aa_set_window}
    for pos in range(start_base, stop_base, 3):
        codon = seq[pos : pos + 3]
        if codon not in GENETIC_CODE:
            return None
        aa = str(CODON_INFO[codon]["aa"])
        if aa in aa_pools:
            aa_pools[aa].append(int(CODON_INFO[codon]["delta"]))

    aa_m_and_pool: dict[str, tuple[int, list[int]]] = {}
    for aa, m in aa_counts_window.items():
        pool = aa_pools.get(aa, [])
        if len(pool) < m:
            return None
        aa_m_and_pool[aa] = (int(m), list(pool))

    return OrfWindowItem(
        rid=str(rid),
        stop_codon=str(stop_codon),
        k=int(k),
        u_before_obs=float(u_before_obs),
        aa_m_and_pool=aa_m_and_pool,
    )


def _reservoir_add(
    heap: list[tuple[int, OrfWindowItem]],
    *,
    item: OrfWindowItem,
    key_u64: int,
    k_max: int,
) -> None:
    """
    Keep smallest keys (deterministic pseudo-random sample).
    heap stores (-key, item) so heap[0] is current worst (largest key).
    """
    if k_max <= 0:
        raise ValueError("k_max must be positive")
    neg = -int(key_u64)
    if len(heap) < k_max:
        import heapq

        heapq.heappush(heap, (neg, item))
        return
    worst_neg = heap[0][0]
    worst_key = -worst_neg
    if key_u64 < worst_key:
        import heapq

        heapq.heapreplace(heap, (neg, item))


def _two_sided_perm_p(obs: float, sims: list[float]) -> float:
    """
    Two-sided empirical p-value for a statistic under an arbitrary (non-centered, non-symmetric)
    null distribution: p = 2 * min(P(T<=t_obs), P(T>=t_obs)).
    """
    if not sims:
        return 1.0
    n = len(sims)
    le = sum(1 for x in sims if float(x) <= float(obs))
    ge = sum(1 for x in sims if float(x) >= float(obs))
    p_left = (le + 1) / float(n + 1)
    p_right = (ge + 1) / float(n + 1)
    p = 2.0 * min(p_left, p_right)
    return max(0.0, min(1.0, p))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10, help="Window radius k for U_before at terminal stops.")
    ap.add_argument(
        "--n-per-stop",
        type=int,
        default=2000,
        help="Deterministic sample size per stop codon (UAA/UAG/UGA).",
    )
    ap.add_argument("--n-perm", type=int, default=200, help="Number of null simulations (permutation replicates).")
    ap.add_argument("--seed", type=int, default=0, help="Deterministic seed for sampling + permutations.")
    ap.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Optional cap on total FASTA records scanned (0 means no cap).",
    )
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    k = int(args.k)
    n_per_stop = int(args.n_per_stop)
    n_perm = int(args.n_perm)
    seed = int(args.seed)
    max_records = int(args.max_records)

    out_json = cache_dir() / "stop_context_synonymous_null_v1.json"
    out_sum = generated_dir() / "stop_context_synonymous_null_summary.tex"
    out_png = generated_dir() / "stop_context_synonymous_null_hist.png"

    cache_key = {
        "analysis": "stop_context_synonymous_null",
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "n_per_stop": n_per_stop,
        "n_perm": n_perm,
        "seed": seed,
        "max_records": max_records,
    }
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        # Rebuild summary from cached sims to avoid rescanning if this script is updated.
        sims = obj.get("sims", {}) or {}
        obs = obj.get("obs", {}) or {}
        obs_means = obj.get("obs_means", {}) or {}
        ns = obj.get("n_per_stop", {}) or {}

        pvals = {
            name: _two_sided_perm_p(obs=float(obs[name]), sims=[float(x) for x in (sims.get(name, []) or [])])
            for name in ("UAG_minus_UAA", "UGA_minus_UAA", "UGA_minus_UAG")
            if name in obs
        }
        null_stats = {}
        for name, xs in sims.items():
            xs = [float(x) for x in (xs or [])]
            null_stats[name] = {
                "mean": float(statistics.mean(xs)) if xs else 0.0,
                "sd": float(statistics.pstdev(xs)) if xs else 0.0,
            }

        lines: list[str] = []
        lines.append(
            "Synonymous-codon permutation null (protein-preserving; within-ORF codon multiset preserved) for terminal-stop"
            f" $\\overline{{U}}_{{\\mathrm{{before}}}}(k={k})$ in Human RefSeq mRNA."
            f" Deterministic sample: n(UAA)={int(ns.get('UAA', 0))}, n(UAG)={int(ns.get('UAG', 0))}, n(UGA)={int(ns.get('UGA', 0))}."
            f" Null sims: n={int(obj.get('n_perm', 0) or 0)}."
        )
        if obs_means:
            lines.append(
                f" Observed means: UAA={float(obs_means.get('UAA', 0.0)):.4f},"
                f" UAG={float(obs_means.get('UAG', 0.0)):.4f},"
                f" UGA={float(obs_means.get('UGA', 0.0)):.4f}."
            )
        if pvals:
            lines.append(
                " Differences vs the synonymous-permutation null (two-sided empirical $p=2\\min\\{\\Pr(T\\le t),\\Pr(T\\ge t)\\}$):"
                f" UAG-UAA={float(obs.get('UAG_minus_UAA', 0.0)):+.4f} (null {null_stats.get('UAG_minus_UAA', {}).get('mean', 0.0):+.4f}"
                f"$\\pm${null_stats.get('UAG_minus_UAA', {}).get('sd', 0.0):.4f}, p={pvals.get('UAG_minus_UAA', 1.0):.4g}),"
                f" UGA-UAA={float(obs.get('UGA_minus_UAA', 0.0)):+.4f} (null {null_stats.get('UGA_minus_UAA', {}).get('mean', 0.0):+.4f}"
                f"$\\pm${null_stats.get('UGA_minus_UAA', {}).get('sd', 0.0):.4f}, p={pvals.get('UGA_minus_UAA', 1.0):.4g}),"
                f" UGA-UAG={float(obs.get('UGA_minus_UAG', 0.0)):+.4f} (null {null_stats.get('UGA_minus_UAG', {}).get('mean', 0.0):+.4f}"
                f"$\\pm${null_stats.get('UGA_minus_UAG', {}).get('sd', 0.0):.4f}, p={pvals.get('UGA_minus_UAG', 1.0):.4g})."
            )
        latex_summary = "\n".join(lines)

        obj["p_perm_two_sided"] = pvals
        obj["null_stats"] = null_stats
        obj["latex_summary"] = latex_summary
        write_json_atomic(out_json, obj)
        write_text(out_sum, latex_summary + "\n")

        # Plot is deterministic from cached sims.
        sim_main = sims.get("UGA_minus_UAA", []) or []
        if sim_main and "UGA_minus_UAA" in obs:
            _write_hist(out_png, [float(x) for x in sim_main], obs=float(obs["UGA_minus_UAA"]))
        return

    shards = read_manifest_refseq_shards()
    if not shards:
        raise FileNotFoundError("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/")

    hb = Heartbeat(every_s=60.0, prefix="[progress] stop_syn_null")

    heaps: dict[str, list[tuple[int, OrfWindowItem]]] = {s: [] for s in STOP_CODONS}
    n_scanned = 0
    n_with_item = 0

    for sp in shards:
        for rid, seq in iter_fasta(str(sp)):
            n_scanned += 1
            if max_records > 0 and n_scanned > max_records:
                break
            hb.maybe(
                f"scan={n_scanned} file={sp.name} sample(UAA,UAG,UGA)="
                f"({len(heaps['UAA'])},{len(heaps['UAG'])},{len(heaps['UGA'])})"
            )

            it = _collect_orf_item(seq, rid=rid, k=k)
            if it is None:
                continue
            n_with_item += 1

            stop = it.stop_codon
            if stop not in heaps:
                continue
            # Deterministic pseudo-random key for sampling.
            key = _stable_u64(f"{rid}|{seed}|{stop}|k{k}")
            _reservoir_add(heaps[stop], item=it, key_u64=key, k_max=n_per_stop)

        if max_records > 0 and n_scanned > max_records:
            break

    items_by_stop: dict[str, list[OrfWindowItem]] = {}
    for stop in STOP_CODONS:
        # heap stores (-key, item)
        items = [it for (_neg, it) in heaps[stop]]
        items.sort(key=lambda x: x.rid)
        items_by_stop[stop] = items

    ns = {s: len(items_by_stop[s]) for s in STOP_CODONS}
    if any(ns[s] < max(10, min(100, n_per_stop // 10)) for s in STOP_CODONS):
        raise RuntimeError(f"Insufficient samples per stop: {ns} (increase scan or reduce --n-per-stop)")

    # Observed means.
    obs_means = {s: statistics.mean([it.u_before_obs for it in items_by_stop[s]]) for s in STOP_CODONS}
    obs_diffs = {
        "UAG_minus_UAA": obs_means["UAG"] - obs_means["UAA"],
        "UGA_minus_UAA": obs_means["UGA"] - obs_means["UAA"],
        "UGA_minus_UAG": obs_means["UGA"] - obs_means["UAG"],
    }

    # Null simulations: for each replicate, sample window deltas from AA pools within each ORF.
    sims: dict[str, list[float]] = {k: [] for k in obs_diffs.keys()}
    for r in range(n_perm):
        rng = random.Random(seed + 1000 + r)
        means_r: dict[str, float] = {}
        for stop in STOP_CODONS:
            ss = 0.0
            for it in items_by_stop[stop]:
                total = 0
                for _aa, (m, pool) in it.aa_m_and_pool.items():
                    # Sample without replacement (AA-local permutation null).
                    if m == 1:
                        total += int(rng.choice(pool))
                    else:
                        total += int(sum(rng.sample(pool, k=m)))
                ss += float(total) / float(k)
            means_r[stop] = ss / float(len(items_by_stop[stop]))
        sims["UAG_minus_UAA"].append(means_r["UAG"] - means_r["UAA"])
        sims["UGA_minus_UAA"].append(means_r["UGA"] - means_r["UAA"])
        sims["UGA_minus_UAG"].append(means_r["UGA"] - means_r["UAG"])

    pvals = {name: _two_sided_perm_p(obs=float(obs_diffs[name]), sims=sims[name]) for name in obs_diffs}
    null_stats: dict[str, dict[str, float]] = {}
    for name, xs in sims.items():
        if xs:
            null_stats[name] = {
                "mean": float(statistics.mean(xs)),
                "sd": float(statistics.pstdev(xs)),
            }
        else:
            null_stats[name] = {"mean": 0.0, "sd": 0.0}

    # Build LaTeX summary (keep concise; numbers are the point).
    lines: list[str] = []
    lines.append(
        "Synonymous-codon permutation null (protein-preserving; within-ORF codon multiset preserved) for terminal-stop"
        f" $\\overline{{U}}_{{\\mathrm{{before}}}}(k={k})$ in Human RefSeq mRNA."
        f" Deterministic sample: n(UAA)={ns['UAA']}, n(UAG)={ns['UAG']}, n(UGA)={ns['UGA']}."
        f" Null sims: n={n_perm}."
    )
    lines.append(
        f" Observed means: UAA={obs_means['UAA']:.4f}, UAG={obs_means['UAG']:.4f}, UGA={obs_means['UGA']:.4f}."
    )
    lines.append(
        " Differences vs the synonymous-permutation null (two-sided empirical $p=2\\min\\{\\Pr(T\\le t),\\Pr(T\\ge t)\\}$):"
        f" UAG-UAA={obs_diffs['UAG_minus_UAA']:+.4f} (null {null_stats['UAG_minus_UAA']['mean']:+.4f}"
        f"$\\pm${null_stats['UAG_minus_UAA']['sd']:.4f}, p={pvals['UAG_minus_UAA']:.4g}),"
        f" UGA-UAA={obs_diffs['UGA_minus_UAA']:+.4f} (null {null_stats['UGA_minus_UAA']['mean']:+.4f}"
        f"$\\pm${null_stats['UGA_minus_UAA']['sd']:.4f}, p={pvals['UGA_minus_UAA']:.4g}),"
        f" UGA-UAG={obs_diffs['UGA_minus_UAG']:+.4f} (null {null_stats['UGA_minus_UAG']['mean']:+.4f}"
        f"$\\pm${null_stats['UGA_minus_UAG']['sd']:.4f}, p={pvals['UGA_minus_UAG']:.4g})."
    )
    latex_summary = "\n".join(lines)

    # Figure: main contrast histogram (UGA-UAA).
    _write_hist(out_png, sims["UGA_minus_UAA"], obs=float(obs_diffs["UGA_minus_UAA"]))

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "n_perm": n_perm,
        "seed": seed,
        "max_records": max_records,
        "n_scanned": n_scanned,
        "n_with_item": n_with_item,
        "n_per_stop": ns,
        "obs": obs_diffs,
        "obs_means": obs_means,
        "p_perm_two_sided": pvals,
        "null_stats": null_stats,
        "sims": sims,
        "latex_summary": latex_summary,
        "figure": str(out_png).replace("\\", "/"),
    }
    write_json_atomic(out_json, obj)
    write_json_atomic(cache_meta_path(out_json), expected_meta)
    write_text(out_sum, latex_summary + "\n")

    print(f"Wrote: {out_sum}")
    print(f"Wrote: {out_png}")
    print(f"Wrote: {out_json}")


def _write_hist(path: Path, sims: list[float], *, obs: float) -> None:
    if not sims:
        return
    xs = [float(x) for x in sims]
    fig = plt.figure(figsize=(6.2, 3.2), dpi=160)
    ax = fig.add_subplot(1, 1, 1)
    ax.hist(xs, bins=30, color="#4C78A8", alpha=0.85, edgecolor="white")
    ax.axvline(float(obs), color="black", linewidth=2.0, label="observed")
    ax.set_title("Synonymous-permutation null: (UGA - UAA) for $\\overline{U}_{before}$")
    ax.set_xlabel("difference in mean $\\overline{U}_{before}$")
    ax.set_ylabel("count")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    main()

