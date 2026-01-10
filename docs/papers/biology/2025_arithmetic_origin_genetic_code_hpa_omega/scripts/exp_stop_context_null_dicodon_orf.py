# -*- coding: utf-8 -*-
"""
Dicodon-preserving ORF-level shuffle null for terminal-stop windows (Reinforcement 3B).

Critique addressed:
  U-window means may reflect codon/dicodon structure of coding sequences rather than
  any new "folding-layer" effect. A strong null is to preserve the entire ORF dicodon
  multiset (codon->codon transition counts) while randomizing order via an Eulerian
  trail shuffle, then re-evaluate boundary-aligned window statistics (last-k codons
  before the terminal stop).

Null model (per ORF):
  - Extract the best ORF (across frames) as in exp_refseq_transcriptome.py.
  - Let the ORF codon sequence include the terminal stop codon (length L).
  - Build the directed multigraph of dicodon edges (L-1 edges).
  - Generate a randomized Eulerian trail by shuffling outgoing-edge order and
    running Hierholzer’s algorithm starting at the ORF start codon.
  - The stop codon has outdegree 0, so it remains the unique end node.

Statistic:
  For each stop class s ∈ {UAA,UAG,UGA}, compute the mean uplift of the last-k
  codons before stop: mean(U_before(s;k)). Compare contrasts (UGA-UAA, etc.)
  against the null distribution over permutations.

Outputs:
  - sections/generated/stop_context_dicodon_null_summary.tex
  - sections/generated/stop_context_dicodon_null_hist.png
  - data/_cache/stop_context_dicodon_null_v1.json (+ meta)

Uses matplotlib for the figure; otherwise standard library.
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

# Best-ORF rule matches the RefSeq scan.
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


CODONS_SORTED = sorted(GENETIC_CODE.keys())
CODON_ID = {c: i for i, c in enumerate(CODONS_SORTED)}
DELTA_BY_ID = [int(CODON_INFO[c]["delta"]) for c in CODONS_SORTED]


@dataclass(frozen=True)
class OrfItem:
    rid: str
    stop: str
    k: int
    codon_ids: bytes  # includes stop at end
    adj_template: tuple[tuple[int, ...], ...]  # 64-tuples of outgoing targets


def _two_sided_emp_p(obs: float, sims: list[float]) -> float:
    if not sims:
        return 1.0
    n = len(sims)
    le = sum(1 for x in sims if float(x) <= float(obs))
    ge = sum(1 for x in sims if float(x) >= float(obs))
    p_left = (le + 1) / float(n + 1)
    p_right = (ge + 1) / float(n + 1)
    p = 2.0 * min(p_left, p_right)
    return max(0.0, min(1.0, p))


def _reservoir_add(
    heap: list[tuple[int, OrfItem]],
    *,
    item: OrfItem,
    key_u64: int,
    n_max: int,
) -> None:
    """
    Keep smallest keys (deterministic pseudo-random sample).
    heap stores (-key, item) so heap[0] is current worst (largest key).
    """
    if n_max <= 0:
        raise ValueError("n_max must be positive")
    neg = -int(key_u64)
    if len(heap) < n_max:
        import heapq

        heapq.heappush(heap, (neg, item))
        return
    worst_neg = heap[0][0]
    worst_key = -worst_neg
    if key_u64 < worst_key:
        import heapq

        heapq.heapreplace(heap, (neg, item))


def _hierholzer_trail(start: int, adj: list[list[int]]) -> list[int]:
    """
    Eulerian trail in a directed multigraph with adjacency lists.
    Uses stack-based Hierholzer; consumes edges by popping from adj lists.
    """
    stack = [int(start)]
    out: list[int] = []
    while stack:
        v = stack[-1]
        if adj[v]:
            stack.append(adj[v].pop())
        else:
            out.append(stack.pop())
    out.reverse()
    return out


def _window_mean_before(nodes: list[int], *, k: int) -> float:
    # nodes includes stop codon at end.
    if len(nodes) < k + 1:
        raise ValueError("sequence too short for window")
    win = nodes[-(k + 1) : -1]
    return float(sum(DELTA_BY_ID[int(x)] for x in win)) / float(k)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10, help="Window radius (last-k codons before terminal stop).")
    ap.add_argument("--n-per-stop", type=int, default=1000, help="Deterministic sample size per stop class.")
    ap.add_argument("--n-perm", type=int, default=100, help="Number of permutation replicates.")
    ap.add_argument("--seed", type=int, default=0, help="Deterministic seed for sampling and permutations.")
    ap.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat interval.")
    ap.add_argument("--max-records", type=int, default=0, help="Optional cap on FASTA records scanned (0=all).")
    ap.add_argument("--max-codons", type=int, default=0, help="Optional cap on ORF length in codons incl stop (0=no cap).")
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    k = int(args.k)
    n_per_stop = int(args.n_per_stop)
    n_perm = int(args.n_perm)
    seed = int(args.seed)
    max_records = int(args.max_records)
    max_codons = int(args.max_codons)

    out_json = cache_dir() / "stop_context_dicodon_null_v1.json"
    out_sum = generated_dir() / "stop_context_dicodon_null_summary.tex"
    out_png = generated_dir() / "stop_context_dicodon_null_hist.png"

    cache_key = {
        "analysis": "stop_context_dicodon_null",
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "n_per_stop": n_per_stop,
        "n_perm": n_perm,
        "seed": seed,
        "max_records": max_records,
        "max_codons": max_codons,
    }
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        write_text(out_sum, str(obj["latex_summary"]) + "\n")
        sims = obj.get("sims", {}) or {}
        if sims.get("UGA_minus_UAA"):
            _write_hist(out_png, [float(x) for x in sims["UGA_minus_UAA"]], obs=float(obj["obs"]["UGA_minus_UAA"]))
        return

    shards = read_manifest_refseq_shards()
    if not shards:
        raise FileNotFoundError("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/")

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] dicodon_null")

    heaps: dict[str, list[tuple[int, OrfItem]]] = {s: [] for s in STOP_CODONS}
    n_scanned = 0
    n_with_orf = 0
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

            best = best_orf_across_frames(seq)
            if best is None:
                continue
            n_with_orf += 1
            if best.length_codons_including_stop < k + 1:
                continue
            if max_codons > 0 and best.length_codons_including_stop > max_codons:
                continue

            start_base = int(best.start_base)
            stop_base = int(best.stop_base)
            stop = seq[stop_base : stop_base + 3]
            if stop not in heaps:
                continue

            # Materialize ORF codons including stop.
            codons: list[str] = []
            ok = True
            for pos in range(start_base, stop_base + 3, 3):
                c = seq[pos : pos + 3]
                if c not in GENETIC_CODE:
                    ok = False
                    break
                codons.append(c)
            if not ok or len(codons) < k + 1 or codons[-1] != stop:
                continue

            try:
                codon_ids = bytes([CODON_ID[c] for c in codons])
            except Exception:
                continue

            # Build adjacency template of dicodon edges (64 nodes).
            adj: list[list[int]] = [[] for _ in range(64)]
            for i in range(len(codon_ids) - 1):
                a = int(codon_ids[i])
                b = int(codon_ids[i + 1])
                adj[a].append(b)
            adj_t = tuple(tuple(lst) for lst in adj)

            item = OrfItem(rid=str(rid), stop=str(stop), k=k, codon_ids=codon_ids, adj_template=adj_t)
            n_with_item += 1

            key = _stable_u64(f"{rid}|{seed}|{stop}|k{k}")
            _reservoir_add(heaps[stop], item=item, key_u64=key, n_max=n_per_stop)

        if max_records > 0 and n_scanned > max_records:
            break

    items_by_stop: dict[str, list[OrfItem]] = {}
    for stop in STOP_CODONS:
        items = [it for (_neg, it) in heaps[stop]]
        items.sort(key=lambda x: x.rid)
        items_by_stop[stop] = items

    ns = {s: len(items_by_stop[s]) for s in STOP_CODONS}
    if any(ns[s] < max(50, min(200, n_per_stop // 5)) for s in STOP_CODONS):
        raise RuntimeError(f"Insufficient samples per stop: {ns} (reduce --n-per-stop or increase scan)")

    # Observed means.
    obs_means = {}
    for stop in STOP_CODONS:
        vals = []
        for it in items_by_stop[stop]:
            nodes = list(it.codon_ids)
            vals.append(_window_mean_before(nodes, k=k))
        obs_means[stop] = float(statistics.mean(vals))

    obs_diffs = {
        "UAG_minus_UAA": obs_means["UAG"] - obs_means["UAA"],
        "UGA_minus_UAA": obs_means["UGA"] - obs_means["UAA"],
        "UGA_minus_UAG": obs_means["UGA"] - obs_means["UAG"],
    }

    sims: dict[str, list[float]] = {name: [] for name in obs_diffs}
    # Null simulations.
    for r in range(n_perm):
        rng = random.Random(seed + 1000 + r)
        means_r: dict[str, float] = {}
        for stop in STOP_CODONS:
            ss = 0.0
            for it in items_by_stop[stop]:
                # Copy adjacency lists.
                adj = [list(t) for t in it.adj_template]
                for lst in adj:
                    if len(lst) > 1:
                        rng.shuffle(lst)
                start = int(it.codon_ids[0])
                nodes = _hierholzer_trail(start, adj)
                ss += _window_mean_before(nodes, k=k)
            means_r[stop] = ss / float(len(items_by_stop[stop]))
        sims["UAG_minus_UAA"].append(means_r["UAG"] - means_r["UAA"])
        sims["UGA_minus_UAA"].append(means_r["UGA"] - means_r["UAA"])
        sims["UGA_minus_UAG"].append(means_r["UGA"] - means_r["UAG"])

        if (r + 1) % max(1, n_perm // 5) == 0:
            hb.force(f"perm {r+1}/{n_perm}")

    pvals = {name: _two_sided_emp_p(obs_diffs[name], sims[name]) for name in obs_diffs}
    null_stats = {name: {"mean": float(statistics.mean(sims[name])), "sd": float(statistics.pstdev(sims[name]))} for name in obs_diffs}

    latex_lines = []
    latex_lines.append(
        "Dicodon-preserving ORF shuffle null (Eulerian-trail permutation of the full CDS+stop dicodon multiset) for"
        f" terminal-stop $\\overline{{U}}_{{\\mathrm{{before}}}}(k={k})$ in Human RefSeq mRNA."
        f" Deterministic sample: n(UAA)={ns['UAA']}, n(UAG)={ns['UAG']}, n(UGA)={ns['UGA']}."
        f" Null perms: n={n_perm}."
    )
    latex_lines.append(
        f" Observed means: UAA={obs_means['UAA']:.4f}, UAG={obs_means['UAG']:.4f}, UGA={obs_means['UGA']:.4f}."
    )
    latex_lines.append(
        " Contrasts vs null (two-sided empirical $p=2\\min\\{\\Pr(T\\le t),\\Pr(T\\ge t)\\}$):"
        f" UAG-UAA={obs_diffs['UAG_minus_UAA']:+.4f} (null {null_stats['UAG_minus_UAA']['mean']:+.4f}"
        f"$\\pm${null_stats['UAG_minus_UAA']['sd']:.4f}, p={pvals['UAG_minus_UAA']:.4g}),"
        f" UGA-UAA={obs_diffs['UGA_minus_UAA']:+.4f} (null {null_stats['UGA_minus_UAA']['mean']:+.4f}"
        f"$\\pm${null_stats['UGA_minus_UAA']['sd']:.4f}, p={pvals['UGA_minus_UAA']:.4g}),"
        f" UGA-UAG={obs_diffs['UGA_minus_UAG']:+.4f} (null {null_stats['UGA_minus_UAG']['mean']:+.4f}"
        f"$\\pm${null_stats['UGA_minus_UAG']['sd']:.4f}, p={pvals['UGA_minus_UAG']:.4g})."
    )
    latex_summary = "\n".join(latex_lines)

    _write_hist(out_png, sims["UGA_minus_UAA"], obs=float(obs_diffs["UGA_minus_UAA"]))

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "n_perm": n_perm,
        "seed": seed,
        "max_records": max_records,
        "max_codons": max_codons,
        "n_scanned": n_scanned,
        "n_with_orf": n_with_orf,
        "n_with_item": n_with_item,
        "n_per_stop": ns,
        "obs_means": obs_means,
        "obs": obs_diffs,
        "null_stats": null_stats,
        "p_perm_two_sided": pvals,
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
    ax.set_title("Dicodon-ORF shuffle null: (UGA - UAA) for $\\overline{U}_{before}$")
    ax.set_xlabel("difference in mean $\\overline{U}_{before}$")
    ax.set_ylabel("count")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    main()

