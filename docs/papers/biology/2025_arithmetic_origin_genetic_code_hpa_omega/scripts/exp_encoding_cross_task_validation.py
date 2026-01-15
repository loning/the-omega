# -*- coding: utf-8 -*-
"""
24-encoding cross-task validation (Reinforcement 1).

Goal:
  Demonstrate whether the identified encoding μ* is unusually strong on multiple
  *independent validation tasks* that do NOT reuse the control-boundary identification
  objective (K-boundary hit counting).

Pre-registered tasks (scores "higher is better"):
  Task A (RefSeq stop-context; primary = multi-k D):
    For each k in K_ref={3,5,10,20}, compute the stop-context contrast feature
      D(k) = u_after(k) - u_before(k)
    at terminal stops, and evaluate AUC for discriminating UGA vs UAA under μ.
    Score = mean_{k in K_ref} |AUC(D(k)) - 0.5|.
    (Exploratory: report the k=10 AUCs for u_before, u_after, and D separately.)
  Task B (transl_except): AUC for discriminating recoding sites vs CDS-deduplicated
    terminal stops using D = u_after(k) - u_before(k) computed under μ (k fixed by the dataset).
    Score = |AUC(D) - 0.5|.
    (Exploratory: report the k=10 AUCs for u_before, u_after, and D separately.)
  Task C (nonstandard codes): Fisher score over translation tables using stop-set
    boundary-hit enrichment under μ (table-level hypergeometric tail p-values combined
    by Fisher's statistic). Score = Fisher statistic (larger is better).

Outputs:
  - sections/generated/encoding_cross_task_validation_summary.tex
  - sections/generated/encoding_cross_task_validation_table.tex
  - data/_cache/encoding_cross_task_validation_v1.json (+ meta)

Standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import (
    GENETIC_CODE,
    START_CODON,
    STOP_CODONS,
    all_encodings,
    encoding_to_str,
    fold_codon,
    is_boundary_word,
    normalize_sequence,
)
from progress_tools import Heartbeat

from exp_nonstandard_codes import codons_for_table, parse_gc_prt


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


def data_root() -> Path:
    return root_dir() / "data"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _stable_u64(tag: str) -> int:
    h = hashlib.sha256(tag.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _is_num(x: object) -> bool:
    return isinstance(x, (int, float)) and (not isinstance(x, bool)) and math.isfinite(float(x))


@dataclass(frozen=True)
class AucResult:
    auc: float
    n_pos: int
    n_neg: int


def _rankdata(values: list[float]) -> list[float]:
    """
    Average ranks for ties, 1-based.
    """
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    r = 1
    while i < n:
        j = i
        v = values[order[i]]
        while j < n and values[order[j]] == v:
            j += 1
        avg = 0.5 * (r + (r + (j - i) - 1))
        for k in range(i, j):
            ranks[order[k]] = float(avg)
        r += (j - i)
        i = j
    return ranks


def auc_mann_whitney(pos: list[float], neg: list[float]) -> AucResult:
    """
    AUC = P(X_pos > X_neg) + 0.5 P(X_pos = X_neg).
    """
    n1 = int(len(pos))
    n0 = int(len(neg))
    if n1 <= 0 or n0 <= 0:
        raise ValueError("Need at least one positive and one negative sample.")
    all_vals = pos + neg
    ranks = _rankdata(all_vals)
    r_pos = sum(ranks[:n1])
    u = r_pos - (n1 * (n1 + 1)) / 2.0
    auc = float(u) / float(n1 * n0)
    auc = min(1.0, max(0.0, auc))
    return AucResult(auc=float(auc), n_pos=n1, n_neg=n0)


def _delta_map_for_mu(mu: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for codon in GENETIC_CODE.keys():
        out[codon] = int(fold_codon(codon, mu).delta)
    if len(out) != 64:
        raise AssertionError("Expected 64 codon deltas.")
    return out


def _mean_delta_from_rna_codons(codons: bytes, *, delta_by_id: list[int], k: int) -> float:
    # codons are codon IDs (0..63), length=k.
    if len(codons) != k:
        raise ValueError("window length mismatch")
    return float(sum(delta_by_id[int(x)] for x in codons)) / float(k)


CODONS_SORTED = sorted(GENETIC_CODE.keys())
CODON_ID = {c: i for i, c in enumerate(CODONS_SORTED)}


def _iter_refseq_fasta_shards() -> list[Path]:
    d = data_root() / "refseq_hsapiens_mrna"
    return sorted(d.glob("human.*.rna.fna.gz"))


@dataclass(frozen=True)
class BestOrf:
    frame: int
    start_base: int
    stop_base: int  # first base of stop codon
    length_codons_including_stop: int


def _best_orf_across_frames(seq: str) -> BestOrf | None:
    best: BestOrf | None = None
    for frame in (0, 1, 2):
        in_orf = False
        start_pos: int | None = None
        best_frame: BestOrf | None = None
        for pos in range(frame, len(seq) - 2, 3):
            codon = seq[pos : pos + 3]
            if codon not in GENETIC_CODE:
                in_orf = False
                start_pos = None
                continue
            if not in_orf:
                if codon == START_CODON:
                    in_orf = True
                    start_pos = pos
            else:
                if codon in STOP_CODONS:
                    if start_pos is not None:
                        length_codons = (pos - start_pos) // 3 + 1
                        cand = BestOrf(
                            frame=int(frame),
                            start_base=int(start_pos),
                            stop_base=int(pos),
                            length_codons_including_stop=int(length_codons),
                        )
                        if best_frame is None:
                            best_frame = cand
                        else:
                            key = (cand.length_codons_including_stop, -cand.start_base, -cand.frame)
                            key_best = (
                                best_frame.length_codons_including_stop,
                                -best_frame.start_base,
                                -best_frame.frame,
                            )
                            if key > key_best:
                                best_frame = cand
                    in_orf = False
                    start_pos = None

        if best_frame is None:
            continue
        if best is None:
            best = best_frame
            continue
        key = (best_frame.length_codons_including_stop, -best_frame.start_base, -best_frame.frame)
        key_best = (best.length_codons_including_stop, -best.start_base, -best.frame)
        if key > key_best:
            best = best_frame
    return best


@dataclass(frozen=True)
class RefseqWin:
    stop: str  # UAA or UGA
    before_ids: bytes  # length=k_max
    after_ids: bytes  # length=k_max


def _reservoir_add(
    heap: list[tuple[int, RefseqWin]],
    *,
    item: RefseqWin,
    key_u64: int,
    n_max: int,
) -> None:
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


def _refseq_task_windows(*, k_list: list[int], target_per_class: int, seed: int, heartbeat_s: float) -> dict[str, list[RefseqWin]]:
    """
    Deterministic sample of terminal-stop windows for UAA and UGA, storing
    before/after windows at k_max=max(k_list) to support multi-k evaluation.
    """
    if not k_list:
        raise ValueError("empty k_list")
    k_list = sorted(set(int(x) for x in k_list))
    k_max = max(k_list)
    shards = _iter_refseq_fasta_shards()
    if not shards:
        raise FileNotFoundError("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/. Run with --download.")
    hb = Heartbeat(every_s=float(heartbeat_s), prefix="[progress] cross_task_refseq")

    heaps: dict[str, list[tuple[int, RefseqWin]]] = {"UAA": [], "UGA": []}
    n_scanned = 0

    for fp in shards:
        with gzip.open(str(fp), "rt", encoding="utf-8", newline="") as f:
            rid = None
            chunks: list[str] = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith(">"):
                    if rid is not None:
                        seq = normalize_sequence("".join(chunks))
                        _maybe_add_refseq_record(
                            rid=str(rid),
                            seq=seq,
                            k_max=k_max,
                            target_per_class=target_per_class,
                            seed=seed,
                            heaps=heaps,
                        )
                        n_scanned += 1
                        hb.maybe(
                            f"scan={n_scanned} file={fp.name} sample(UAA,UGA)=({len(heaps['UAA'])},{len(heaps['UGA'])})"
                        )
                    rid = line[1:].split()[0] or "record"
                    chunks = []
                else:
                    chunks.append(line)
            if rid is not None:
                seq = normalize_sequence("".join(chunks))
                _maybe_add_refseq_record(
                    rid=str(rid),
                    seq=seq,
                    k_max=k_max,
                    target_per_class=target_per_class,
                    seed=seed,
                    heaps=heaps,
                )
                n_scanned += 1

    out: dict[str, list[RefseqWin]] = {}
    for stop in ("UAA", "UGA"):
        items = [it for (_neg, it) in heaps[stop]]
        items.sort(key=lambda x: (x.before_ids, x.after_ids))  # deterministic
        out[stop] = items
    # Basic sanity.
    if len(out["UAA"]) < max(500, min(2000, target_per_class // 4)) or len(out["UGA"]) < max(500, min(2000, target_per_class // 4)):
        raise RuntimeError(f"Insufficient RefSeq windows: n(UAA)={len(out['UAA'])}, n(UGA)={len(out['UGA'])}")
    return out


def _maybe_add_refseq_record(
    *,
    rid: str,
    seq: str,
    k_max: int,
    target_per_class: int,
    seed: int,
    heaps: dict[str, list[tuple[int, RefseqWin]]],
) -> None:
    best = _best_orf_across_frames(seq)
    if best is None:
        return
    if best.length_codons_including_stop < k_max + 1:
        return
    start_base = int(best.start_base)
    stop_base = int(best.stop_base)
    stop = seq[stop_base : stop_base + 3]
    if stop not in ("UAA", "UGA"):
        return
    win_start = stop_base - 3 * k_max
    win_end = stop_base
    if win_start < start_base:
        return
    codons_before = [seq[i : i + 3] for i in range(win_start, win_end, 3)]
    if len(codons_before) != k_max:
        return
    if any(c not in GENETIC_CODE for c in codons_before):
        return

    # After window (k_max codons immediately after stop)
    after_start = stop_base + 3
    after_end = after_start + 3 * k_max
    if after_end > len(seq):
        return
    codons_after = [seq[i : i + 3] for i in range(after_start, after_end, 3)]
    if len(codons_after) != k_max:
        return
    if any(c not in GENETIC_CODE for c in codons_after):
        return

    try:
        ids_before = bytes([CODON_ID[c] for c in codons_before])
        ids_after = bytes([CODON_ID[c] for c in codons_after])
    except Exception:
        return
    it = RefseqWin(stop=stop, before_ids=ids_before, after_ids=ids_after)
    key = _stable_u64(f"{rid}|{seed}|{stop}|kmax{k_max}")
    _reservoir_add(heaps[stop], item=it, key_u64=key, n_max=target_per_class)


def _parse_recoding_windows(
    *, k: int, analysis_version: int
) -> tuple[list[bytes], list[bytes], list[tuple[bytes, bytes]], list[bytes], list[bytes], list[tuple[bytes, bytes]]]:
    """
    Return windows as codon-id bytes:
      - rec_before: list[bytes]
      - rec_after:  list[bytes]
      - rec_both:   list[(before, after)] where both exist
      - term_before: list[bytes] (CDS-deduplicated)
      - term_after:  list[bytes] (CDS-deduplicated)
      - term_both:   list[(before, after)] CDS-dedup where both exist
    """
    in_jsonl = data_root() / "recoding_genbank" / "recoding_sites.jsonl"
    if not in_jsonl.exists():
        raise FileNotFoundError(f"Missing {in_jsonl}. Run exp_recoding_sites.py or run_all.py --download.")

    rec_before: list[bytes] = []
    rec_after: list[bytes] = []
    rec_both: list[tuple[bytes, bytes]] = []
    term_by_cds: dict[tuple[str, str, int], dict[str, bytes]] = {}

    def to_ids(seq_dna: str | None) -> bytes | None:
        if not seq_dna:
            return None
        s = str(seq_dna).upper().replace("T", "U")
        if len(s) != 3 * k:
            return None
        try:
            return bytes([CODON_ID[s[i : i + 3]] for i in range(0, len(s), 3)])
        except Exception:
            return None

    with in_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if not isinstance(r, dict):
                continue
            if int(r.get("analysis_version") or 0) != int(analysis_version):
                continue
            if int(r.get("k") or 0) != int(k):
                continue

            version = str(r.get("version") or "").strip()
            cds_location = str(r.get("cds_location") or "").strip()
            ts = r.get("translation_start")
            if (not version) or (not cds_location) or (not isinstance(ts, int)):
                continue
            group = (version, cds_location, int(ts))

            rec_b = to_ids(r.get("before_seq_dna"))
            rec_a = to_ids(r.get("after_seq_dna"))
            if rec_b is not None:
                rec_before.append(rec_b)
            if rec_a is not None:
                rec_after.append(rec_a)
            if (rec_b is not None) and (rec_a is not None):
                rec_both.append((rec_b, rec_a))

            tb = to_ids(r.get("terminal_before_seq_dna"))
            ta = to_ids(r.get("terminal_after_seq_dna"))
            if tb is not None or ta is not None:
                cur = term_by_cds.get(group) or {}
                if tb is not None:
                    cur["before"] = tb
                if ta is not None:
                    cur["after"] = ta
                term_by_cds[group] = cur

    term_before = [d["before"] for d in term_by_cds.values() if "before" in d]
    term_after = [d["after"] for d in term_by_cds.values() if "after" in d]
    term_both = [(d["before"], d["after"]) for d in term_by_cds.values() if ("before" in d and "after" in d)]
    return rec_before, rec_after, rec_both, term_before, term_after, term_both


def _hypergeom_tail_p(*, N: int, K: int, n: int, k: int) -> float:
    if k <= 0:
        return 1.0
    if n <= 0 or K <= 0:
        return 1.0
    if k > min(K, n):
        return 0.0
    denom = math.comb(N, n)
    s = 0
    for x in range(k, min(K, n) + 1):
        s += math.comb(K, x) * math.comb(N - K, n - x)
    return float(s) / float(denom)


def _nonstandard_fisher_score(mu: dict[str, str]) -> tuple[float, float]:
    """
    Return (Fisher statistic, mean-hit/table) for stop-set boundary enrichment across tables.
    """
    tables = parse_gc_prt((data_root() / "gc.prt").read_text(encoding="utf-8"))
    table_rows = []
    for t in tables:
        codons = codons_for_table(t)
        stops = [codons[i] for i, aa in enumerate(t.ncbieaa) if aa == "*"]
        if not stops:
            continue
        table_rows.append(stops)

    N = 64
    K_boundary = 6
    p_list = []
    hits_total = 0
    for stops in table_rows:
        n_stop = len(stops)
        k_obs = 0
        for c in stops:
            w = str(fold_codon(str(c), mu).w)
            if is_boundary_word(w):
                k_obs += 1
        hits_total += int(k_obs)
        p = _hypergeom_tail_p(N=N, K=K_boundary, n=int(n_stop), k=int(k_obs))
        p_list.append(max(1e-300, float(p)))

    fisher = -2.0 * sum(math.log(p) for p in p_list) if p_list else 0.0
    mean_hit = float(hits_total) / float(len(table_rows)) if table_rows else 0.0
    return float(fisher), float(mean_hit)


def _fisher_stat(ps: list[float]) -> float:
    return -2.0 * sum(math.log(max(1e-300, float(p))) for p in ps)


def main() -> None:
    ap = argparse.ArgumentParser(description="24-encoding cross-task validation (no control-objective reuse).")
    ap.add_argument("--k", type=int, default=10, help="Window radius k (codons) for u_before.")
    ap.add_argument("--refseq-k-list", type=str, default="3,5,10,20", help="Comma-separated k list for RefSeq Task A (primary = mean over k of AUC(D(k))).")
    ap.add_argument(
        "--analysis-version",
        type=int,
        default=7,
        help="Filter for recoding_sites.jsonl: analysis_version (should match exp_recoding_sites.py output).",
    )
    ap.add_argument("--refseq-target-per-class", type=int, default=5000, help="Deterministic target per stop class (UAA/UGA) in RefSeq task.")
    ap.add_argument("--seed", type=int, default=0, help="Deterministic seed for RefSeq sampling.")
    ap.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat interval for RefSeq scan.")
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cached.")
    args = ap.parse_args()

    k = int(args.k)
    analysis_version = int(args.analysis_version)
    refseq_target = int(args.refseq_target_per_class)
    seed = int(args.seed)
    k_list_ref = [int(x) for x in str(args.refseq_k_list).split(",") if str(x).strip()]
    k_list_ref = sorted(set(k_list_ref))
    if not k_list_ref:
        raise SystemExit("Empty --refseq-k-list")
    k_max_ref = max(k_list_ref)

    out_json = cache_dir() / "encoding_cross_task_validation_v1.json"
    out_table = generated_dir() / "encoding_cross_task_validation_table.tex"
    out_sum = generated_dir() / "encoding_cross_task_validation_summary.tex"

    cache_key = {
        "analysis": "encoding_cross_task_validation",
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "refseq_k_list": k_list_ref,
        "analysis_version_recoding": analysis_version,
        "refseq_target_per_class": refseq_target,
        "seed": seed,
    }
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = json.loads(out_json.read_text(encoding="utf-8"))
        write_text(out_table, str(obj["latex_table"]) + "\n")
        write_text(out_sum, str(obj["latex_summary"]) + "\n")
        return

    # ----- Task A: RefSeq stop-context AUC (UGA as positive), primary=mean over k of AUC(D(k)). -----
    refseq = _refseq_task_windows(k_list=k_list_ref, target_per_class=refseq_target, seed=seed, heartbeat_s=float(args.heartbeat_s))
    ref_uaa = refseq["UAA"]
    ref_uga = refseq["UGA"]

    # ----- Task B: Recoding vs terminal AUC -----
    rec_before, rec_after, rec_both, term_before, term_after, term_both = _parse_recoding_windows(
        k=k, analysis_version=analysis_version
    )

    # ----- Task C: nonstandard Fisher score -----
    encs = all_encodings()
    rows = []

    # Precompute delta_by_id for each encoding (aligned to CODONS_SORTED).
    delta_by_mu = []
    for mu in encs:
        dm = _delta_map_for_mu(mu)
        delta_by_mu.append([int(dm[c]) for c in CODONS_SORTED])

    # Compute all task scores per encoding.
    for idx, mu in enumerate(encs):
        d = delta_by_mu[idx]
        # Task A: primary score = mean_k |AUC(D(k)) - 0.5| where D=u_after-u_before.
        scores_A = []
        aucA_k10_before = float("nan")
        aucA_k10_after = float("nan")
        aucA_k10_D = float("nan")
        for kk in k_list_ref:
            pos_D = []
            neg_D = []
            for it in ref_uga:
                ub = _mean_delta_from_rna_codons(it.before_ids[-kk:], delta_by_id=d, k=kk)
                ua = _mean_delta_from_rna_codons(it.after_ids[:kk], delta_by_id=d, k=kk)
                pos_D.append(float(ua - ub))
            for it in ref_uaa:
                ub = _mean_delta_from_rna_codons(it.before_ids[-kk:], delta_by_id=d, k=kk)
                ua = _mean_delta_from_rna_codons(it.after_ids[:kk], delta_by_id=d, k=kk)
                neg_D.append(float(ua - ub))
            auc = auc_mann_whitney(pos_D, neg_D).auc
            scores_A.append(abs(float(auc) - 0.5))

            if kk == 10:
                # Exploratory: k=10 AUCs for u_before/u_after/D.
                pos_b = [_mean_delta_from_rna_codons(it.before_ids[-kk:], delta_by_id=d, k=kk) for it in ref_uga]
                neg_b = [_mean_delta_from_rna_codons(it.before_ids[-kk:], delta_by_id=d, k=kk) for it in ref_uaa]
                pos_a = [_mean_delta_from_rna_codons(it.after_ids[:kk], delta_by_id=d, k=kk) for it in ref_uga]
                neg_a = [_mean_delta_from_rna_codons(it.after_ids[:kk], delta_by_id=d, k=kk) for it in ref_uaa]
                aucA_k10_before = auc_mann_whitney(pos_b, neg_b).auc
                aucA_k10_after = auc_mann_whitney(pos_a, neg_a).auc
                aucA_k10_D = auc

        sA = float(sum(scores_A)) / float(len(scores_A)) if scores_A else 0.0

        # Task B: primary score uses D = u_after - u_before (k fixed by dataset).
        posB_D = [
            float(
                _mean_delta_from_rna_codons(a, delta_by_id=d, k=k) - _mean_delta_from_rna_codons(b, delta_by_id=d, k=k)
            )
            for (b, a) in rec_both
        ]
        negB_D = [
            float(
                _mean_delta_from_rna_codons(a, delta_by_id=d, k=k) - _mean_delta_from_rna_codons(b, delta_by_id=d, k=k)
            )
            for (b, a) in term_both
        ]
        aucB_D = auc_mann_whitney(posB_D, negB_D).auc
        sB = abs(float(aucB_D) - 0.5)

        # Exploratory: k=10 AUCs for u_before and u_after.
        posB_b = [_mean_delta_from_rna_codons(w, delta_by_id=d, k=k) for w in rec_before]
        negB_b = [_mean_delta_from_rna_codons(w, delta_by_id=d, k=k) for w in term_before]
        aucB_before = auc_mann_whitney(posB_b, negB_b).auc
        posB_a = [_mean_delta_from_rna_codons(w, delta_by_id=d, k=k) for w in rec_after]
        negB_a = [_mean_delta_from_rna_codons(w, delta_by_id=d, k=k) for w in term_after]
        aucB_after = auc_mann_whitney(posB_a, negB_a).auc

        # Task C: nonstandard Fisher score (uses boundary hits, but not the K-identification objective).
        fisherC, mean_hitC = _nonstandard_fisher_score(mu)
        sC = float(fisherC)

        rows.append(
            {
                "mu": encoding_to_str(mu),
                "mu_bits": mu,
                "is_mu_star": bool(all(mu.get(b) == MU_STAR[b] for b in ("A", "C", "G", "U"))),
                "taskA_score": float(sA),
                "taskA_k_list": list(k_list_ref),
                "taskA_auc_k10_before": float(aucA_k10_before),
                "taskA_auc_k10_after": float(aucA_k10_after),
                "taskA_auc_k10_D": float(aucA_k10_D),
                "taskB_auc_D": float(aucB_D),
                "taskB_auc_before": float(aucB_before),
                "taskB_auc_after": float(aucB_after),
                "taskB_score": float(sB),
                "taskC_fisher": float(sC),
                "taskC_mean_hit_table": float(mean_hitC),
            }
        )

    # Rank each task (descending by score; average ranks for ties).
    def avg_ranks(values: list[float]) -> list[float]:
        n = len(values)
        order = sorted(range(n), key=lambda i: values[i], reverse=True)
        r = [0.0] * n
        i = 0
        rank = 1
        while i < n:
            j = i
            v = values[order[i]]
            while j < n and values[order[j]] == v:
                j += 1
            avg = 0.5 * (rank + (rank + (j - i) - 1))
            for k0 in range(i, j):
                r[order[k0]] = float(avg)
            rank += (j - i)
            i = j
        return r

    rA = avg_ranks([float(r["taskA_score"]) for r in rows])
    rB = avg_ranks([float(r["taskB_score"]) for r in rows])
    rC = avg_ranks([float(r["taskC_fisher"]) for r in rows])
    for i, r in enumerate(rows):
        r["rankA"] = float(rA[i])
        r["rankB"] = float(rB[i])
        r["rankC"] = float(rC[i])
        r["sum_rank"] = float(rA[i] + rB[i] + rC[i])

    rows_sorted = sorted(rows, key=lambda r: float(r["sum_rank"]))

    # Extract μ* ranks and conservative p-values (uniform encoding prior).
    mu_star_row = next(r for r in rows if bool(r["is_mu_star"]))
    rankA_mu = int(round(float(mu_star_row["rankA"])))
    rankB_mu = int(round(float(mu_star_row["rankB"])))
    rankC_mu = int(round(float(mu_star_row["rankC"])))
    pA = float(rankA_mu) / 24.0
    pB = float(rankB_mu) / 24.0
    pC = float(rankC_mu) / 24.0

    # Exact encoding-null for Fisher combination of the three per-task p's (enumerate 24 encodings).
    fisher_mu = _fisher_stat([pA, pB, pC])
    fisher_all = []
    for r in rows:
        piA = float(int(round(float(r["rankA"])))) / 24.0
        piB = float(int(round(float(r["rankB"])))) / 24.0
        piC = float(int(round(float(r["rankC"])))) / 24.0
        fisher_all.append(_fisher_stat([piA, piB, piC]))
    p_comb = sum(1 for s in fisher_all if s >= fisher_mu) / 24.0

    # ----- LaTeX table -----
    tbl = []
    tbl.append(r"\begin{center}")
    tbl.append(r"\scriptsize")
    tbl.append(r"\setlength{\tabcolsep}{4pt}")
    tbl.append(r"\renewcommand{\arraystretch}{1.10}")
    tbl.append(r"\resizebox{\textwidth}{!}{%")
    tbl.append(r"\begin{tabular}{rccccrrrrrrrl}")
    tbl.append(r"\toprule")
    tbl.append(
        r"rank & $A$ & $C$ & $G$ & $U$ & A $\overline{|\mathrm{AUC}_D-0.5|}$ & B $|\mathrm{AUC}_D-0.5|$ & C Fisher & rA & rB & rC & sum-rank & tag \\"
    )
    tbl.append(r"\midrule")
    for i, r in enumerate(rows_sorted, start=1):
        mu = r["mu_bits"]
        tag = r"$\mu^\ast$" if bool(r["is_mu_star"]) else "-"
        tbl.append(
            f"{i} & \\texttt{{{mu['A']}}} & \\texttt{{{mu['C']}}} & \\texttt{{{mu['G']}}} & \\texttt{{{mu['U']}}}"
            f" & {float(r['taskA_score']):.4f} & {float(r['taskB_score']):.4f} & {float(r['taskC_fisher']):.2f}"
            f" & {float(r['rankA']):.0f} & {float(r['rankB']):.0f} & {float(r['rankC']):.0f} & {float(r['sum_rank']):.0f} & {tag} \\\\"
        )
    tbl.append(r"\bottomrule")
    tbl.append(r"\end{tabular}")
    tbl.append(r"}")
    tbl.append(r"\end{center}")
    latex_table = "\n".join(tbl)

    summary = []
    summary.append(
        "Cross-task validation across three non-identification tasks (RefSeq stop-context AUC; transl\\_except recoding AUC; nonstandard-table Fisher score), evaluated over all $24$ encodings."
        f" Task A (primary): mean over $k\\in\\{{{', '.join(str(x) for x in k_list_ref)}\\}}$ of $|\\mathrm{{AUC}}(D(k))-0.5|$ with $D=u_{{after}}-u_{{before}}$ at terminal stops."
        f" Sample sizes: n(UGA)={len(ref_uga)}, n(UAA)={len(ref_uaa)} (k\\_max={k_max_ref})."
        f" Task B (primary): $|\\mathrm{{AUC}}(D)-0.5|$ on transl\\_except windows (k={k}), using only sites with both before/after windows."
        f" Sample sizes: n(recoding)={len(rec_both)}, n(terminal)={len(term_both)}."
        f" Under the uniform encoding prior, $\\mu^\\ast$ ranks {rankA_mu}/24 (A), {rankB_mu}/24 (B), {rankC_mu}/24 (C),"
        f" giving p-values $p_A={pA:.4f}$, $p_B={pB:.4f}$, $p_C={pC:.4f}$."
        f" Combining the three with Fisher's statistic yields $p_\\mathrm{{comb}}={p_comb:.4f}$ under the exact encoding-null (enumeration over 24 encodings)."
    )
    latex_summary = "\n".join(summary)

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "analysis_version_recoding": analysis_version,
        "refseq_target_per_class": refseq_target,
        "seed": seed,
        "taskA": {"n_uga": len(ref_uga), "n_uaa": len(ref_uaa)},
        "taskB": {"n_rec_both": len(rec_both), "n_term_both": len(term_both), "k": k},
        "mu_star_ranks": {"A": rankA_mu, "B": rankB_mu, "C": rankC_mu, "p_comb": p_comb},
        "rows": rows_sorted,
        "latex_table": latex_table,
        "latex_summary": latex_summary,
    }
    write_json_atomic(out_json, obj)
    write_json_atomic(cache_meta_path(out_json), expected_meta)
    write_text(out_table, latex_table + "\n")
    write_text(out_sum, latex_summary + "\n")
    print(f"Wrote: {out_sum}")
    print(f"Wrote: {out_table}")
    print(f"Wrote: {out_json}")


if __name__ == "__main__":
    main()
