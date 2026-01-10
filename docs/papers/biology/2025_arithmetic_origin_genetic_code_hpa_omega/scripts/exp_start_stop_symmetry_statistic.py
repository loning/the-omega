# -*- coding: utf-8 -*-
"""
Corpus-level start/stop symmetry statistic under μ* with 24-encoding negative control (Reinforcement 8).

We make the "start/stop interface" claim falsifiable at the corpus level by defining
a pre-registered symmetry statistic over ORFs:

  For a window radius k, define for each ORF i:
    d_start(i;k) = u_after(start;k) - u_before(start;k)
    d_stop(i;k)  = u_after(stop;k)  - u_before(stop;k)
    t(i;k)       = d_start(i;k) + d_stop(i;k)
  and the corpus statistic:
    T_k(μ) = mean_i t(i;k) computed under encoding μ (via Δ_μ on codons).

To avoid reliance on parametric assumptions, we evaluate T_k for all 24 encodings and
use the exact encoding-null (uniform over 24) to assess how extreme μ* is.

Sampling:
  To keep runtime bounded, we use a deterministic, hash-based sample of ORFs that have
  complete start/stop windows for k_max=max(k_list) on both sides (before/after).

Outputs:
  - sections/generated/start_stop_symmetry_statistic.tex
  - data/_cache/start_stop_symmetry_statistic_v1.json (+ meta)

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic
from genetic_code_tools import GENETIC_CODE, STOP_CODONS, all_encodings, encoding_to_str, fold_codon, iter_fasta
from progress_tools import Heartbeat

from exp_refseq_transcriptome import best_orf_across_frames


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
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


@dataclass(frozen=True)
class OrfWindows:
    rid: str
    stop_codon: str  # UAA/UAG/UGA
    k_max: int
    start_before: bytes  # length k_max (closest codon to start is last)
    start_after: bytes  # length k_max (closest codon to start is first)
    stop_before: bytes  # length k_max (closest codon to stop is last)
    stop_after: bytes  # length k_max (closest codon to stop is first)


def _encode_codons(codons: list[str]) -> bytes | None:
    try:
        return bytes([CODON_ID[c] for c in codons])
    except Exception:
        return None


def _extract_window(seq: str, *, start_base: int, k: int) -> list[str] | None:
    """
    Extract k in-frame codons starting at start_base (inclusive).
    Requires all codons in GENETIC_CODE.
    """
    if start_base < 0 or start_base + 3 * k > len(seq):
        return None
    out = []
    for i in range(k):
        codon = seq[start_base + 3 * i : start_base + 3 * i + 3]
        if codon not in GENETIC_CODE:
            return None
        out.append(codon)
    return out


def _collect_orf_windows(seq: str, *, rid: str, k_max: int) -> OrfWindows | None:
    best = best_orf_across_frames(seq)
    if best is None:
        return None
    start_base = int(best.start_base)
    stop_base = int(best.stop_base)
    stop_codon = seq[stop_base : stop_base + 3]
    if stop_codon not in STOP_CODONS:
        return None

    # Define the four windows (in the ORF frame).
    # - before windows are the k codons immediately preceding the boundary.
    # - after windows are the k codons immediately following the boundary.
    sb = _extract_window(seq, start_base=start_base - 3 * k_max, k=k_max)  # ends at start_base-3
    sa = _extract_window(seq, start_base=start_base + 3, k=k_max)
    tb = _extract_window(seq, start_base=stop_base - 3 * k_max, k=k_max)  # ends at stop_base-3
    ta = _extract_window(seq, start_base=stop_base + 3, k=k_max)
    if sb is None or sa is None or tb is None or ta is None:
        return None

    # Sanity: ensure the last codon of sb is immediately before start, and similarly for stop.
    if seq[start_base - 3 : start_base] != sb[-1]:
        return None
    if seq[stop_base - 3 : stop_base] != tb[-1]:
        return None

    sb_b = _encode_codons(sb)
    sa_b = _encode_codons(sa)
    tb_b = _encode_codons(tb)
    ta_b = _encode_codons(ta)
    if sb_b is None or sa_b is None or tb_b is None or ta_b is None:
        return None

    return OrfWindows(
        rid=str(rid),
        stop_codon=str(stop_codon),
        k_max=int(k_max),
        start_before=sb_b,
        start_after=sa_b,
        stop_before=tb_b,
        stop_after=ta_b,
    )


def _reservoir_add(
    heap: list[tuple[int, str, OrfWindows]],
    *,
    item: OrfWindows,
    key_u64: int,
    n_max: int,
) -> None:
    """
    Keep smallest hash keys (deterministic pseudo-random sample).
    heap stores (-key, rid, item) so heap[0] is current worst (largest key).
    """
    if n_max <= 0:
        raise ValueError("n_max must be positive")
    neg = -int(key_u64)
    if len(heap) < n_max:
        import heapq

        heapq.heappush(heap, (neg, item.rid, item))
        return
    worst_neg = heap[0][0]
    worst_key = -worst_neg
    if key_u64 < worst_key:
        import heapq

        heapq.heapreplace(heap, (neg, item.rid, item))


def _is_mu_star(mu: dict[str, str]) -> bool:
    return all(mu.get(b) == MU_STAR[b] for b in ("A", "C", "G", "U"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k-list", type=str, default="3,5,10,20", help="Comma-separated window radii.")
    ap.add_argument("--n-sample", type=int, default=20000, help="Deterministic ORF sample size.")
    ap.add_argument("--seed", type=int, default=0, help="Deterministic sampling seed.")
    ap.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat interval.")
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    k_list = [int(x) for x in str(args.k_list).split(",") if str(x).strip()]
    k_list = sorted(set(k_list))
    if not k_list:
        raise SystemExit("Empty --k-list")
    k_max = max(k_list)
    n_sample = int(args.n_sample)
    seed = int(args.seed)

    out_json = cache_dir() / "start_stop_symmetry_statistic_v1.json"
    out_tex = generated_dir() / "start_stop_symmetry_statistic.tex"

    cache_key = {"analysis": "start_stop_symmetry_statistic", "analysis_version": ANALYSIS_VERSION, "k_list": k_list, "n_sample": n_sample, "seed": seed}
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        write_text(out_tex, str(obj["latex"]) + "\n")
        return

    shards = read_manifest_refseq_shards()
    if not shards:
        raise FileNotFoundError("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/")

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] start_stop_sym")

    heap: list[tuple[int, str, OrfWindows]] = []
    n_scanned = 0
    n_with_orf = 0
    n_with_windows = 0

    for sp in shards:
        for rid, seq in iter_fasta(str(sp)):
            n_scanned += 1
            hb.maybe(f"scan={n_scanned} file={sp.name} sample={len(heap)}/{n_sample} with_orf={n_with_orf} with_windows={n_with_windows}")

            best = best_orf_across_frames(seq)
            if best is None:
                continue
            n_with_orf += 1

            it = _collect_orf_windows(seq, rid=rid, k_max=k_max)
            if it is None:
                continue
            n_with_windows += 1
            key = _stable_u64(f"{rid}|{seed}|kmax{k_max}")
            _reservoir_add(heap, item=it, key_u64=key, n_max=n_sample)

    items = [it for (_neg, _rid, it) in heap]
    items.sort(key=lambda x: x.rid)
    if len(items) < max(2000, n_sample // 4):
        raise RuntimeError(f"Too few ORFs with complete windows: got {len(items)} (n_sample={n_sample}).")

    # Precompute Δ tables for each encoding and codon-id.
    encs = all_encodings()
    delta_by_mu: list[list[int]] = []
    for mu in encs:
        row = []
        for codon in CODONS_SORTED:
            row.append(int(fold_codon(codon, mu).delta))
        delta_by_mu.append(row)

    # Accumulate T_k for each encoding, for all stops and for UAA-only subset.
    out_rows = []
    for mu_idx, mu in enumerate(encs):
        dm = delta_by_mu[mu_idx]
        stats_all = {k: {"sum": 0.0, "n": 0} for k in k_list}
        stats_uaa = {k: {"sum": 0.0, "n": 0} for k in k_list}

        for it in items:
            is_uaa = it.stop_codon == "UAA"
            for k in k_list:
                # Sums without slicing (avoid allocations).
                i0 = it.k_max - k
                sb_sum = 0
                sa_sum = 0
                tb_sum = 0
                ta_sum = 0
                for j in range(k):
                    sa_sum += dm[it.start_after[j]]
                    ta_sum += dm[it.stop_after[j]]
                for j in range(i0, it.k_max):
                    sb_sum += dm[it.start_before[j]]
                    tb_sum += dm[it.stop_before[j]]
                # Differences of means.
                d_start = (sa_sum / float(k)) - (sb_sum / float(k))
                d_stop = (ta_sum / float(k)) - (tb_sum / float(k))
                t = float(d_start + d_stop)
                stats_all[k]["sum"] += t
                stats_all[k]["n"] += 1
                if is_uaa:
                    stats_uaa[k]["sum"] += t
                    stats_uaa[k]["n"] += 1

        T_all = {k: (stats_all[k]["sum"] / stats_all[k]["n"]) for k in k_list}
        T_uaa = {k: (stats_uaa[k]["sum"] / stats_uaa[k]["n"]) for k in k_list if stats_uaa[k]["n"] > 0}

        score_primary = abs(T_uaa.get(10, T_all.get(10, 0.0)))  # primary: k=10, prefer UAA subset if present
        score_multi = sum(abs(T_uaa.get(k, T_all.get(k, 0.0))) for k in k_list)

        out_rows.append(
            {
                "mu": encoding_to_str(mu),
                "is_mu_star": bool(_is_mu_star(mu)),
                "n_all": int(stats_all[k_list[0]]["n"]),
                "n_uaa": int(stats_uaa[k_list[0]]["n"]),
                "T_all": {str(k): float(T_all[k]) for k in k_list},
                "T_uaa": {str(k): float(T_uaa.get(k, float("nan"))) for k in k_list},
                "score_primary": float(score_primary),
                "score_multi": float(score_multi),
            }
        )

    # Ranking under exact encoding-null.
    def rank_by(key: str) -> tuple[int, float]:
        rows_sorted = sorted(out_rows, key=lambda r: float(r[key]), reverse=True)
        r_mu = None
        for i, r in enumerate(rows_sorted, start=1):
            if bool(r["is_mu_star"]):
                r_mu = i
                break
        if r_mu is None:
            raise AssertionError("μ* missing from encoding list")
        p = float(r_mu) / 24.0
        return int(r_mu), float(p)

    r_primary, p_primary = rank_by("score_primary")
    r_multi, p_multi = rank_by("score_multi")

    mu_star_row = next(r for r in out_rows if bool(r["is_mu_star"]))
    n_all = int(mu_star_row["n_all"])
    n_uaa = int(mu_star_row["n_uaa"])

    # LaTeX fragment
    tex = []
    tex.append(
        "Start/stop symmetry statistic on a deterministic RefSeq ORF sample (best ORF per transcript; complete windows on both sides)."
        f" Sample size: n={n_all} ORFs (UAA subset: n={n_uaa})."
        f" Radii $k\\in\\{{{', '.join(str(k) for k in k_list)}\\}}$, using $T_k=\\mathbb{{E}}[d_\\mathrm{{start}}(k)+d_\\mathrm{{stop}}(k)]$ where $d=\\overline{{U}}_\\mathrm{{after}}-\\overline{{U}}_\\mathrm{{before}}$."
        f" Under the exact encoding-null over 24 encodings, $\\mu^\\ast$ ranks {r_primary}/24 by the primary score $|T_{{10}}|$ (p={p_primary:.4f}),"
        f" and ranks {r_multi}/24 by the multi-$k$ score $\\sum_k |T_k|$ (p={p_multi:.4f})."
    )

    # Report μ* values.
    t_uaa = mu_star_row["T_uaa"]
    t_all = mu_star_row["T_all"]
    tex.append(
        " For $\\mu^\\ast$, $T_k$ (UAA subset) = "
        + ", ".join([f"{k}:{float(t_uaa[str(k)]):+.4f}" for k in k_list])
        + "; (all stops) = "
        + ", ".join([f"{k}:{float(t_all[str(k)]):+.4f}" for k in k_list])
        + "."
    )

    # Top-5 by primary score.
    rows_primary = sorted(out_rows, key=lambda r: float(r["score_primary"]), reverse=True)[:5]
    tex.append(r"\begin{center}")
    tex.append(r"\small")
    tex.append(r"\setlength{\tabcolsep}{6pt}")
    tex.append(r"\renewcommand{\arraystretch}{1.15}")
    tex.append(r"\begin{tabular}{rllrr}")
    tex.append(r"\toprule")
    tex.append(r"rank & $A,C,G,U$ bits & tag & $|T_{10}|$ & $\sum_k |T_k|$ \\")
    tex.append(r"\midrule")
    for i, r in enumerate(rows_primary, start=1):
        tag = r"$\mu^\ast$" if bool(r["is_mu_star"]) else "-"
        tex.append(
            f"{i} & \\texttt{{{r['mu']}}} & {tag} & {float(r['score_primary']):.4f} & {float(r['score_multi']):.4f} \\\\"
        )
    tex.append(r"\bottomrule")
    tex.append(r"\end{tabular}")
    tex.append(r"\end{center}")
    latex = "\n".join(tex)

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "k_list": k_list,
        "k_max": k_max,
        "n_sample": n_sample,
        "seed": seed,
        "n_scanned": n_scanned,
        "n_with_orf": n_with_orf,
        "n_with_windows": n_with_windows,
        "n_used": len(items),
        "mu_star_rank_primary": r_primary,
        "mu_star_p_primary": p_primary,
        "mu_star_rank_multi": r_multi,
        "mu_star_p_multi": p_multi,
        "rows": out_rows,
        "mu_star": mu_star_row,
        "latex": latex,
    }
    write_json_atomic(out_json, obj)
    write_json_atomic(cache_meta_path(out_json), expected_meta)
    write_text(out_tex, latex + "\n")
    print(f"Wrote: {out_tex}")
    print(f"Wrote: {out_json}")


if __name__ == "__main__":
    main()

