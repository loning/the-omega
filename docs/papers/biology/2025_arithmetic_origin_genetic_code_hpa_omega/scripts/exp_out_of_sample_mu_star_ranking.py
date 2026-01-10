# -*- coding: utf-8 -*-
"""
Out-of-sample validation for mu* (purely computational).

Goal (reviewer-facing):
  - keep identification fixed (K-based reverse compilation over 24 encodings),
  - evaluate mu* on independent validation buckets/tasks that DO NOT use the identification objective.

We compute a mu* rank among the 24 encodings for three pre-registered buckets:
  (B1) RefSeq (human mRNA): discriminate terminal-stop class UGA vs UAA using u_before(k)
  (B2) transl_except recoding (GenBank): discriminate recoding vs CDS-deduplicated terminal stops using u_before(k)
  (B3) nonstandard translation tables (NCBI gc.prt): mean number of boundary-hit stop codons per translation table

For B1/B2 we use a rank-based AUC (Mann–Whitney concordance) and score = |AUC-0.5|.
For B3 we use score = (total boundary-hit stop codons across all tables) / (number of tables).

We then:
  - compute mu* ranks (1..24, smaller is better),
  - compute per-bucket empirical p_i := #{mu: score(mu) >= score(mu*)}/24 (tie-aware, conservative),
  - combine the three p-values with Fisher's statistic and report an exact encoding-null p-value
    by enumerating all 24 encodings (mu* treated as uniform under the null).

Outputs (sections/generated/):
  - out_of_sample_combined_p.tex
  - out_of_sample_mu_star_ranking_table.tex
  - out_of_sample_mu_star_ranking_summary.json  (data/_cache/)

Notes:
  - This script intentionally trades completeness for auditability and fixed rules.
  - RefSeq sampling is deterministic (first N per class under the file order) unless overridden.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from exp_nonstandard_codes import codons_for_table, parse_gc_prt
from genetic_code_tools import GENETIC_CODE, START_CODON, STOP_CODONS, all_encodings, codon_bits, fold6, normalize_sequence, zeckendorf_value
from progress_tools import Heartbeat


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
SCRIPT_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def _file_fingerprint(path: Path) -> dict[str, object]:
    st = path.stat()
    return {
        "path": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _latex_encoding(mu: dict[str, str]) -> str:
    return (
        f"A\\mapsto \\texttt{{{mu['A']}}},\\ "
        f"C\\mapsto \\texttt{{{mu['C']}}},\\ "
        f"G\\mapsto \\texttt{{{mu['G']}}},\\ "
        f"U\\mapsto \\texttt{{{mu['U']}}}"
    )


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
    """
    Map codon -> delta under Fold_6 and a given nucleotide encoding mu.
    """
    out: dict[str, int] = {}
    for codon in GENETIC_CODE.keys():
        bits = codon_bits(codon, mu)
        n = int(bits, 2)
        w = fold6(n)
        v = zeckendorf_value(w)
        out[codon] = int(n - int(v))
    if len(out) != 64:
        raise AssertionError("Expected 64 codon deltas.")
    return out


def _mean_delta_from_dna_window(seq_dna: str | None, delta_map: dict[str, int]) -> float | None:
    if not seq_dna:
        return None
    s = str(seq_dna).upper().replace("T", "U")
    if len(s) % 3 != 0:
        return None
    vals: list[int] = []
    for i in range(0, len(s), 3):
        codon = s[i : i + 3]
        if codon not in delta_map:
            return None
        vals.append(int(delta_map[codon]))
    if not vals:
        return None
    return float(sum(vals)) / float(len(vals))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Out-of-sample mu* ranking across independent validation buckets.")
    p.add_argument("--k", type=int, default=10, help="Window radius k (codons) for u_before.")
    p.add_argument("--analysis-version", type=int, default=7, help="Filter for recoding_sites.jsonl: analysis_version.")
    p.add_argument(
        "--refseq-target-per-class",
        type=int,
        default=20000,
        help="Target number of ORFs per terminal-stop class (UAA and UGA) in the RefSeq bucket.",
    )
    p.add_argument(
        "--refseq-max-shards",
        type=int,
        default=0,
        help="Optional limit on number of RefSeq shard files to scan (0=all).",
    )
    p.add_argument(
        "--refseq-max-records",
        type=int,
        default=0,
        help="Optional max FASTA records to process across RefSeq shards (0=no limit).",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def _refseq_shards() -> list[Path]:
    d = data_root() / "refseq_hsapiens_mrna"
    return sorted(d.glob("human.*.rna.fna.gz"))


def _iter_fasta_gz(path: Path) -> Iterable[tuple[str, str]]:
    rid = None
    chunks: list[str] = []
    with gzip.open(str(path), "rt", encoding="utf-8", newline="") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if rid is not None:
                    yield rid, normalize_sequence("".join(chunks))
                rid = line[1:].split()[0] or "record"
                chunks = []
            else:
                chunks.append(line)
    if rid is not None:
        yield rid, normalize_sequence("".join(chunks))


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


def _collect_refseq_contexts(
    *,
    k: int,
    target_per_class: int,
    max_shards: int,
    max_records: int,
) -> tuple[list[list[str]], list[list[str]]]:
    """
    Return (contexts_uga, contexts_uaa), where each context is the list of k codons before the terminal stop.
    Deterministic: we scan shard files in sorted order and take the first target_per_class ORFs per class.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    shards = _refseq_shards()
    if max_shards and max_shards > 0:
        shards = shards[: int(max_shards)]
    if not shards:
        raise SystemExit("No RefSeq shards found under data/refseq_hsapiens_mrna/. Run fetch_datasets.py first.")

    ctx_uga: list[list[str]] = []
    ctx_uaa: list[list[str]] = []

    n_seen = 0
    hb = Heartbeat(every_s=30.0, prefix="[progress] out_of_sample_refseq")
    hb.force(f"start shards={len(shards)} k={k} target_per_class={target_per_class}")

    for fp in shards:
        for rid, seq in _iter_fasta_gz(fp):
            n_seen += 1
            if max_records and max_records > 0 and n_seen > int(max_records):
                hb.force("hit max_records; stopping")
                break
            if (len(ctx_uga) >= target_per_class) and (len(ctx_uaa) >= target_per_class):
                break
            if n_seen % 2000 == 0:
                hb.maybe(f"records={n_seen} uaa={len(ctx_uaa)} uga={len(ctx_uga)}")

            best = _best_orf_across_frames(seq)
            if best is None:
                continue
            if best.length_codons_including_stop < int(k) + 1:
                continue
            stop = seq[best.stop_base : best.stop_base + 3]
            if stop not in ("UAA", "UGA"):
                continue
            w0 = best.stop_base - 3 * int(k)
            if w0 < 0:
                continue
            before = seq[w0 : best.stop_base]
            if len(before) != 3 * int(k):
                continue
            codons: list[str] = []
            ok = True
            for i in range(0, len(before), 3):
                c = before[i : i + 3]
                if c not in GENETIC_CODE:
                    ok = False
                    break
                codons.append(c)
            if not ok or len(codons) != int(k):
                continue
            if stop == "UGA" and len(ctx_uga) < target_per_class:
                ctx_uga.append(codons)
            elif stop == "UAA" and len(ctx_uaa) < target_per_class:
                ctx_uaa.append(codons)

        if max_records and max_records > 0 and n_seen > int(max_records):
            break
        if (len(ctx_uga) >= target_per_class) and (len(ctx_uaa) >= target_per_class):
            break

    hb.force(f"done records={n_seen} uaa={len(ctx_uaa)} uga={len(ctx_uga)}")
    return ctx_uga, ctx_uaa


def _rank_best(values: list[float], *, target: float) -> int:
    """
    1 + number of values strictly greater than target.
    (So ties give the best possible rank.)
    """
    return 1 + sum(1 for v in values if v > target)


def _fisher_stat(ps: list[float]) -> float:
    return -2.0 * sum(math.log(max(1e-300, float(p))) for p in ps)

def _p_ge(scores: list[float], *, target: float) -> float:
    """
    Conservative right-tail probability under the uniform encoding prior:
      p = #{mu: score(mu) >= score(target)}/24
    """
    return sum(1 for s in scores if s >= target) / float(len(scores) or 1)


def main() -> None:
    args = parse_args()

    k = int(args.k)
    if k <= 0:
        raise SystemExit("--k must be positive")

    rec_jsonl = data_root() / "recoding_genbank" / "recoding_sites.jsonl"
    gc_prt = data_root() / "gc.prt"
    refseq_dir = data_root() / "refseq_hsapiens_mrna"
    if not rec_jsonl.exists():
        raise SystemExit(f"Missing recoding JSONL: {rec_jsonl}")
    if not gc_prt.exists():
        raise SystemExit(f"Missing gc.prt: {gc_prt}")
    if not refseq_dir.exists():
        raise SystemExit(f"Missing RefSeq dir: {refseq_dir}")

    out_tex = generated_dir() / "out_of_sample_combined_p.tex"
    out_tbl = generated_dir() / "out_of_sample_mu_star_ranking_table.tex"
    cache_file = data_root() / "_cache" / f"out_of_sample_mu_star_ranking_v{int(SCRIPT_VERSION)}.json"

    cache_key = {
        "analysis": "out_of_sample_mu_star_ranking",
        "version": int(SCRIPT_VERSION),
        "k": int(k),
        "analysis_version": int(args.analysis_version),
        "refseq_target_per_class": int(args.refseq_target_per_class),
        "refseq_max_shards": int(args.refseq_max_shards),
        "refseq_max_records": int(args.refseq_max_records),
        "inputs": {
            "recoding_jsonl": _file_fingerprint(rec_jsonl),
            "gc_prt": _file_fingerprint(gc_prt),
            # RefSeq is huge; fingerprint just the directory listing signature.
            "refseq_shards": [_file_fingerprint(p) for p in _refseq_shards()[: (int(args.refseq_max_shards) or 999999)]],
        },
        "out": [str(out_tex), str(out_tbl)],
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and out_tex.exists() and out_tbl.exists() and cache_hit(cache_file, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {cache_file}")
        return

    mus = all_encodings()
    if len(mus) != 24:
        raise AssertionError("Expected 24 encodings.")
    mu_star_idx = next((i for i, m in enumerate(mus) if m == MU_STAR), None)
    if mu_star_idx is None:
        raise AssertionError("Failed to locate mu* among encodings.")

    # ---- Bucket B1: RefSeq stop-context (UGA vs UAA) ----
    ctx_uga, ctx_uaa = _collect_refseq_contexts(
        k=int(k),
        target_per_class=int(args.refseq_target_per_class),
        max_shards=int(args.refseq_max_shards),
        max_records=int(args.refseq_max_records),
    )

    # ---- Bucket B2: recoding vs terminal (CDS-deduplicated) ----
    hb = Heartbeat(every_s=30.0, prefix="[progress] out_of_sample_recoding")
    hb.force(f"start k={k} av={int(args.analysis_version)}")
    rec_before_seq: list[str] = []
    term_by_cds: dict[tuple[str, str, int], str] = {}

    n_lines = 0
    with rec_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            if n_lines % 5000 == 0:
                hb.maybe(f"lines={n_lines} rec={len(rec_before_seq)} term_cds={len(term_by_cds)}")
            r = json.loads(line)
            if not isinstance(r, dict):
                continue
            if int(r.get("analysis_version") or 0) != int(args.analysis_version):
                continue
            if int(r.get("k") or 0) != int(k):
                continue
            bseq = r.get("before_seq_dna")
            if isinstance(bseq, str) and bseq:
                rec_before_seq.append(bseq)

            version = str(r.get("version") or "").strip()
            cds_location = str(r.get("cds_location") or "").strip()
            ts = r.get("translation_start")
            if version and cds_location and isinstance(ts, int):
                tseq = r.get("terminal_before_seq_dna")
                if isinstance(tseq, str) and tseq:
                    term_by_cds[(version, cds_location, int(ts))] = str(tseq)
    hb.force(f"done lines={n_lines} rec={len(rec_before_seq)} term_cds={len(term_by_cds)}")

    # ---- Bucket B3: nonstandard translation tables ----
    text = gc_prt.read_text(encoding="utf-8", errors="replace")
    tables = parse_gc_prt(text)
    if not tables:
        raise SystemExit("Failed to parse any translation tables from data/gc.prt")
    n_tables = len(tables)

    # Precompute stop sets per table (RNA codons).
    stop_sets: list[list[str]] = []
    for t in tables:
        codons = codons_for_table(t)
        stops = [codons[i] for i, aa in enumerate(t.ncbieaa) if aa == "*"]
        stop_sets.append(stops)

    # ---- Evaluate all 24 encodings ----
    rows: list[dict[str, object]] = []
    hb = Heartbeat(every_s=30.0, prefix="[progress] out_of_sample_scan24")
    hb.force("start encodings=24")

    refseq_scores: list[float] = []
    rec_scores: list[float] = []
    nonstd_scores: list[float] = []

    for idx, mu in enumerate(mus):
        hb.maybe(f"mu={idx+1}/24")
        delta_map = _delta_map_for_mu(mu)

        # B1: RefSeq AUC (UGA as positive).
        pos1 = [float(sum(delta_map[c] for c in ctx) / float(len(ctx))) for ctx in ctx_uga]
        neg1 = [float(sum(delta_map[c] for c in ctx) / float(len(ctx))) for ctx in ctx_uaa]
        auc1 = auc_mann_whitney(pos1, neg1).auc
        score1 = abs(float(auc1) - 0.5)

        # B2: Recoding vs terminal AUC (recoding as positive).
        pos2 = []
        for s in rec_before_seq:
            v = _mean_delta_from_dna_window(s, delta_map)
            if v is not None:
                pos2.append(float(v))
        neg2 = []
        for s in term_by_cds.values():
            v = _mean_delta_from_dna_window(s, delta_map)
            if v is not None:
                neg2.append(float(v))
        auc2 = auc_mann_whitney(pos2, neg2).auc
        score2 = abs(float(auc2) - 0.5)

        # B3: nonstandard tables: mean number of boundary-hit stop codons per table (not clipped).
        total_hits = 0
        for stops in stop_sets:
            for c in stops:
                bits = codon_bits(c, mu)
                n = int(bits, 2)
                w = fold6(n)
                if (w[0] == "1") and (w[-1] == "1"):  # boundary word check, equivalent to w in X6^bdry
                    total_hits += 1
        mean_hits = float(total_hits) / float(n_tables) if n_tables > 0 else float("nan")
        score3 = float(mean_hits)

        refseq_scores.append(float(score1))
        rec_scores.append(float(score2))
        nonstd_scores.append(float(score3))

        rows.append(
            {
                "idx": int(idx),
                "mu": dict(mu),
                "refseq_auc": float(auc1),
                "refseq_score": float(score1),
                "recoding_auc": float(auc2),
                "recoding_score": float(score2),
                "nonstd_mean_hits": float(mean_hits),
            }
        )

    # Compute mu* ranks (best-rank under ties) + conservative tail probabilities.
    mu_star = rows[int(mu_star_idx)]
    r_ref = _rank_best(refseq_scores, target=float(mu_star["refseq_score"]))
    r_rec = _rank_best(rec_scores, target=float(mu_star["recoding_score"]))
    r_ns = _rank_best(nonstd_scores, target=float(mu_star["nonstd_mean_hits"]))
    p_ref = _p_ge(refseq_scores, target=float(mu_star["refseq_score"]))
    p_rec = _p_ge(rec_scores, target=float(mu_star["recoding_score"]))
    p_ns = _p_ge(nonstd_scores, target=float(mu_star["nonstd_mean_hits"]))

    # Fisher-combined statistic for mu*.
    fisher_stat_mu = _fisher_stat([p_ref, p_rec, p_ns])
    # Exact encoding-null p-value: mu* treated as uniform among the 24 encodings.
    fisher_stats_all: list[float] = []
    for i in range(24):
        pi_ref = _p_ge(refseq_scores, target=float(refseq_scores[i]))
        pi_rec = _p_ge(rec_scores, target=float(rec_scores[i]))
        pi_ns = _p_ge(nonstd_scores, target=float(nonstd_scores[i]))
        fisher_stats_all.append(_fisher_stat([pi_ref, pi_rec, pi_ns]))
    p_comb = sum(1 for s in fisher_stats_all if s >= fisher_stat_mu) / 24.0

    # ---- Write LaTeX summary ----
    lines: list[str] = []
    lines.append(
        "Out-of-sample validation across three independent buckets (no use of the control-boundary identification objective). "
        f"Bucket B1 (RefSeq human mRNA): AUC for discriminating terminal-stop class $\\mathrm{{UGA}}$ vs $\\mathrm{{UAA}}$ "
        f"using $\\overline{{U}}_{{\\mathrm{{before}}}}(k={k})$ on $n_\\mathrm{{UGA}}={len(ctx_uga)}$ and $n_\\mathrm{{UAA}}={len(ctx_uaa)}$ ORFs; "
        f"score $=|\\mathrm{{AUC}}-0.5|$. "
        f"Bucket B2 (GenBank \\texttt{{transl\\_except}}): AUC for discriminating recoding sites vs CDS-deduplicated terminal stops "
        f"using $\\overline{{U}}_{{\\mathrm{{before}}}}(k={k})$ on $n_1={len(rec_before_seq)}$ and $n_0={len(term_by_cds)}$; score $=|\\mathrm{{AUC}}-0.5|$. "
        f"Bucket B3 (NCBI \\texttt{{gc.prt}}): mean number of boundary-hit stop codons per translation table under the encoding. "
        f"Across the 24 encodings, $\\mu^\\ast$ ranks "
        f"{r_ref}/24 (B1), {r_rec}/24 (B2), and {r_ns}/24 (B3), "
        f"giving conservative tail probabilities (uniform encoding prior) $p_\\mathrm{{B1}}={p_ref:.4f}$, $p_\\mathrm{{B2}}={p_rec:.4f}$, $p_\\mathrm{{B3}}={p_ns:.4f}$. "
        f"Combining the three p-values with Fisher's statistic yields $p_\\mathrm{{comb}}={p_comb:.4f}$ under the exact encoding-null "
        "(enumeration over 24 encodings)."
    )
    write_text_atomic(out_tex, "\n".join(lines).strip() + "\n")

    # ---- Write table (sorted by Fisher-like score: sum of ranks) ----
    for r in rows:
        r["rank_refseq"] = 1 + sum(1 for x in refseq_scores if x > float(r["refseq_score"]))
        r["rank_recoding"] = 1 + sum(1 for x in rec_scores if x > float(r["recoding_score"]))
        r["rank_nonstd"] = 1 + sum(1 for x in nonstd_scores if x > float(r["nonstd_mean_hits"]))
        r["rank_sum"] = int(r["rank_refseq"]) + int(r["rank_recoding"]) + int(r["rank_nonstd"])
        r["tag"] = "$\\mu^\\ast$" if r["mu"] == MU_STAR else "-"

    rows.sort(key=lambda r: (int(r["rank_sum"]), int(r["rank_refseq"]), int(r["rank_recoding"]), int(r["rank_nonstd"])))

    tbl: list[str] = []
    tbl.append("\\begin{center}")
    tbl.append("\\scriptsize")
    tbl.append("\\setlength{\\tabcolsep}{4pt}")
    tbl.append("\\renewcommand{\\arraystretch}{1.10}")
    tbl.append("\\resizebox{\\textwidth}{!}{%")
    tbl.append("\\begin{tabular}{rccccrrrrl}")
    tbl.append("\\toprule")
    tbl.append("rank & $A$ & $C$ & $G$ & $U$ & B1 $|\\mathrm{AUC}-0.5|$ & B2 $|\\mathrm{AUC}-0.5|$ & B3 mean-hit & sum-rank & tag \\\\")
    tbl.append("\\midrule")
    for i, r in enumerate(rows, start=1):
        mu = r["mu"]
        assert isinstance(mu, dict)
        tbl.append(
            f"{i} & \\texttt{{{mu['A']}}} & \\texttt{{{mu['C']}}} & \\texttt{{{mu['G']}}} & \\texttt{{{mu['U']}}} & "
            f"{float(r['refseq_score']):.4f} & {float(r['recoding_score']):.4f} & {float(r['nonstd_mean_hits']):.4f} & "
            f"{int(r['rank_sum'])} & {str(r['tag'])} \\\\"
        )
    tbl.append("\\bottomrule")
    tbl.append("\\end{tabular}")
    tbl.append("}")
    tbl.append("\\end{center}")
    tbl.append("")
    write_text_atomic(out_tbl, "\n".join(tbl) + "\n")

    # ---- Write cache JSON + meta ----
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        cache_file,
        {
            "ok": True,
            "script_version": int(SCRIPT_VERSION),
            "k": int(k),
            "refseq": {"n_uga": len(ctx_uga), "n_uaa": len(ctx_uaa)},
            "recoding": {"n_recoding": len(rec_before_seq), "n_terminal_cds": len(term_by_cds)},
            "nonstandard": {"n_tables": int(n_tables)},
            "mu_star_idx": int(mu_star_idx),
            "mu_star_ranks": {"B1": int(r_ref), "B2": int(r_rec), "B3": int(r_ns)},
            "mu_star_bucket_p": {"B1": float(p_ref), "B2": float(p_rec), "B3": float(p_ns)},
            "combined": {"fisher_p_encoding_null": float(p_comb)},
            "rows": rows,
        },
    )
    write_json_atomic(cache_meta_path(cache_file), cache_meta)

    print("Wrote:", out_tex)
    print("Wrote:", out_tbl)


if __name__ == "__main__":
    main()

