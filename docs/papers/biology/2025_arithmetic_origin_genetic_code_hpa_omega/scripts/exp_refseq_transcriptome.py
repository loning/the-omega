# -*- coding: utf-8 -*-
"""
Transcriptome-scale experiments on Human RefSeq mRNA FASTA shards (human.*.rna.fna.gz).

Outputs:
  - JSON summary under data/refseq_hsapiens_mrna/
  - LaTeX fragments under sections/generated/

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from cache_manager import cache_hit, cache_meta_path, cache_key_digest, read_json, write_json_atomic
from genetic_code_tools import (
    BOUNDARY_WORDS,
    GENETIC_CODE,
    START_CODON,
    STOP_CODONS,
    amino_acid_codons,
    fold_codon,
    find_orfs,
    iter_fasta,
    student_t_cdf,
)


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}

# Bump this when the analysis logic (not just speed) changes.
ANALYSIS_VERSION = 2

# Bump this when the output JSON schema changes.
SCHEMA_VERSION = 2

# Precompute codon-level Fold_6 attributes under mu* for speed.
CODON_INFO: dict[str, dict[str, object]] = {}
for c in GENETIC_CODE:
    f = fold_codon(c, MU_STAR)
    CODON_INFO[c] = {
        "aa": f.aa,
        "v": int(f.v),
        "delta": int(f.delta),
        "is_boundary": int(f.w in BOUNDARY_WORDS),
    }


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_dir() -> Path:
    return root_dir() / "data" / "refseq_hsapiens_mrna"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def read_manifest_files() -> list[Path]:
    mp = root_dir() / "data" / "manifest.json"
    obj = json.loads(mp.read_text(encoding="utf-8"))
    ds = obj["datasets"]["refseq_hsapiens_mrna"]
    files = ds.get("files", [])
    out = []
    for e in files:
        name = e["name"]
        out.append(data_dir() / name)
    if out:
        return out
    # Fallback: local directory scan.
    return sorted(data_dir().glob("human.*.rna.fna.gz"))


def manifest_sha256_for_refseq_shard(filename: str) -> str | None:
    """
    Look up sha256 for a RefSeq shard by filename from data/manifest.json.
    """
    mp = root_dir() / "data" / "manifest.json"
    try:
        obj = json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        return None
    ds = obj.get("datasets", {}).get("refseq_hsapiens_mrna", {})
    for e in ds.get("files", []) or []:
        if e.get("name") == filename and e.get("sha256"):
            return str(e["sha256"])
    return None


@dataclass(frozen=True)
class BestOrf:
    frame: int
    start_base: int
    stop_base: int  # first base of stop codon
    length_codons_including_stop: int


@dataclass
class RunningStats:
    """
    Welford online mean/variance accumulator.
    Stores (n, mean, M2) where M2 = sum (x-mean)^2.
    """

    n: int = 0
    mean: float = 0.0
    M2: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2

    def merge(self, other: "RunningStats") -> None:
        if other.n == 0:
            return
        if self.n == 0:
            self.n = other.n
            self.mean = other.mean
            self.M2 = other.M2
            return
        n_a = self.n
        n_b = other.n
        n = n_a + n_b
        delta = other.mean - self.mean
        self.mean = self.mean + delta * (n_b / n)
        self.M2 = self.M2 + other.M2 + delta * delta * (n_a * n_b / n)
        self.n = n

    def sample_variance(self) -> float:
        if self.n <= 1:
            return 0.0
        return self.M2 / (self.n - 1)


def best_orf_across_frames(seq: str) -> BestOrf | None:
    best: BestOrf | None = None
    for frame in (0, 1, 2):
        # Streaming best-ORF finder in a fixed frame (faster than materializing all ORFs).
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
                            frame=frame,
                            start_base=start_pos,
                            stop_base=pos,
                            length_codons_including_stop=length_codons,
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


def _mean(xs: list[float]) -> float:
    if not xs:
        raise ValueError("empty list")
    return float(sum(xs)) / float(len(xs))


def welch_t_p_value_two_sided(xs: list[float], ys: list[float]) -> float | None:
    """
    Two-sided Welch t-test p-value using a t CDF implementation that expects an integer df.
    Returns None if inputs are too small.
    """
    n1 = len(xs)
    n2 = len(ys)
    if n1 < 2 or n2 < 2:
        return None
    m1 = _mean(xs)
    m2 = _mean(ys)
    v1 = statistics.pvariance(xs) * (n1 / (n1 - 1))  # sample variance
    v2 = statistics.pvariance(ys) * (n2 / (n2 - 1))
    se2 = v1 / n1 + v2 / n2
    if se2 <= 0:
        return None
    t = abs(m1 - m2) / math.sqrt(se2)
    num = se2 * se2
    den = (v1 * v1) / (n1 * n1 * (n1 - 1)) + (v2 * v2) / (n2 * n2 * (n2 - 1))
    if den <= 0:
        return None
    df = num / den
    df_i = max(1, int(round(df)))
    p = 2.0 * (1.0 - student_t_cdf(t, df=df_i))
    return max(0.0, min(1.0, p))


def welch_t_p_value_two_sided_from_stats(a: RunningStats, b: RunningStats) -> float | None:
    """
    Two-sided Welch t-test p-value from (n, mean, sample variance).
    Returns None if either sample has n<2 or if the standard error is zero.
    """
    n1 = int(a.n)
    n2 = int(b.n)
    if n1 < 2 or n2 < 2:
        return None
    m1 = float(a.mean)
    m2 = float(b.mean)
    v1 = float(a.sample_variance())
    v2 = float(b.sample_variance())
    se2 = v1 / n1 + v2 / n2
    if se2 <= 0:
        return None
    t = abs(m1 - m2) / math.sqrt(se2)
    num = se2 * se2
    den = (v1 * v1) / (n1 * n1 * (n1 - 1)) + (v2 * v2) / (n2 * n2 * (n2 - 1))
    if den <= 0:
        return None
    df = num / den
    df_i = max(1, int(round(df)))
    p = 2.0 * (1.0 - student_t_cdf(t, df=df_i))
    return max(0.0, min(1.0, p))


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_two_sided_p(z: float) -> float:
    p = 2.0 * (1.0 - normal_cdf(abs(z)))
    return max(0.0, min(1.0, p))


def codon_usage_null_test(
    aa_counts: Counter[str],
    *,
    observed_zbar: float,
    observed_ubar: float,
) -> dict[str, float]:
    """
    Null model: preserve amino-acid composition; within each amino acid, choose synonymous codon uniformly.
    Approximate Zbar and Ubar by a normal distribution via exact mean/variance under independence.
    """
    codons_by_aa = amino_acid_codons()
    total_codons = sum(int(v) for aa, v in aa_counts.items() if aa != "Stop")
    if total_codons <= 0:
        raise ValueError("No coding codons")

    # Precompute codon-level (V,Delta) for mu*.
    v_delta_by_codon: dict[str, tuple[int, int]] = {}
    for codon in GENETIC_CODE:
        f = fold_codon(codon, MU_STAR)
        v_delta_by_codon[codon] = (int(f.v), int(f.delta))

    mu_z = 0.0
    var_z = 0.0
    mu_u = 0.0
    var_u = 0.0

    for aa, n in aa_counts.items():
        if aa == "Stop":
            continue
        n_i = int(n)
        syn = codons_by_aa[aa]
        vs = [float(v_delta_by_codon[c][0]) for c in syn]
        us = [float(v_delta_by_codon[c][1]) for c in syn]

        m_v = sum(vs) / len(vs)
        m_u = sum(us) / len(us)
        mu_z += n_i * m_v
        mu_u += n_i * m_u

        var_v = sum((x - m_v) ** 2 for x in vs) / len(vs)
        var_u_i = sum((x - m_u) ** 2 for x in us) / len(us)
        var_z += n_i * var_v
        var_u += n_i * var_u_i

    mu_zbar = mu_z / total_codons
    mu_ubar = mu_u / total_codons
    sd_zbar = math.sqrt(var_z) / total_codons if var_z > 0 else 0.0
    sd_ubar = math.sqrt(var_u) / total_codons if var_u > 0 else 0.0

    z_z = (observed_zbar - mu_zbar) / sd_zbar if sd_zbar > 0 else 0.0
    z_u = (observed_ubar - mu_ubar) / sd_ubar if sd_ubar > 0 else 0.0

    return {
        "total_codons": float(total_codons),
        "null_mu_zbar": mu_zbar,
        "null_sd_zbar": sd_zbar,
        "obs_zbar": observed_zbar,
        "z_zbar": z_z,
        "p_zbar": normal_two_sided_p(z_z),
        "null_mu_ubar": mu_ubar,
        "null_sd_ubar": sd_ubar,
        "obs_ubar": observed_ubar,
        "z_ubar": z_u,
        "p_ubar": normal_two_sided_p(z_u),
    }


def hist_total(hist: Counter[int]) -> int:
    return int(sum(int(v) for v in hist.values()))


def hist_sum(hist: Counter[int]) -> int:
    return int(sum(int(k) * int(v) for k, v in hist.items()))


def hist_value_at_index(hist: Counter[int], idx0: int) -> int:
    """
    Return the value x[idx0] for the multiset defined by hist, with x sorted ascending.
    idx0 is 0-based and must be in [0, N-1].
    """
    if idx0 < 0:
        raise ValueError("idx0 must be nonnegative")
    acc = 0
    for k in sorted(hist.keys()):
        c = int(hist[k])
        if c <= 0:
            continue
        if acc + c > idx0:
            return int(k)
        acc += c
    raise IndexError("idx0 out of range for histogram")


def hist_quantile_inclusive(hist: Counter[int], p: float) -> float:
    """
    Inclusive linear-interpolated quantile (like a type-7 style quantile):
      h = p*(N-1)
      q = x[floor(h)] + frac*(x[ceil(h)] - x[floor(h)])
    where x is the sorted sample with N points.
    """
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be in [0,1]")
    n = hist_total(hist)
    if n <= 0:
        raise ValueError("empty histogram")
    if n == 1:
        return float(hist_value_at_index(hist, 0))
    h = p * float(n - 1)
    lo = int(math.floor(h))
    hi = int(math.ceil(h))
    frac = float(h - lo)
    x_lo = float(hist_value_at_index(hist, lo))
    x_hi = float(hist_value_at_index(hist, hi))
    return x_lo + frac * (x_hi - x_lo)


def _summarize_float_list(xs: list[float]) -> dict[str, float]:
    """
    Return basic descriptive statistics for a list of floats.
    Uses inclusive quartiles. For n=1, quartiles equal the single value.
    """
    n = len(xs)
    if n == 0:
        return {
            "n": 0.0,
            "mean": float("nan"),
            "median": float("nan"),
            "p25": float("nan"),
            "p75": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }
    mn = float(min(xs))
    mx = float(max(xs))
    mean = float(sum(xs)) / float(n)
    med = float(statistics.median(xs))
    if n == 1:
        p25 = med
        p75 = med
    else:
        qs = statistics.quantiles(xs, n=4, method="inclusive")
        p25 = float(qs[0])
        p75 = float(qs[2])
    return {
        "n": float(n),
        "mean": mean,
        "median": med,
        "p25": p25,
        "p75": p75,
        "min": mn,
        "max": mx,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Human RefSeq transcriptome scan (Fold_6 spectra)")
    p.add_argument(
        "--input",
        default="",
        help="Optional single FASTA(.gz) shard to process; empty means use manifest file list.",
    )
    p.add_argument("--stop-window", type=int, default=10, help="Primary window radius k for stop-context uplift.")
    p.add_argument(
        "--stop-window-list",
        default="",
        help="Optional comma-separated list of window radii k to compute in one pass (e.g. 3,5,10,20).",
    )
    p.add_argument("--max-records", type=int, default=0, help="Optional limit on number of records (0 = no limit).")
    p.add_argument("--out-json", default=str(data_dir() / "transcriptome_summary.json"), help="Output summary JSON path.")
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    p.add_argument(
        "--write-meta",
        action="store_true",
        help="Write/refresh cache meta sidecar next to --out-json (recommended for caching).",
    )
    p.add_argument(
        "--progress-every",
        type=int,
        default=20000,
        help="Print progress every N records (0 disables).",
    )
    p.add_argument(
        "--log",
        default=str(data_dir() / "transcriptome_scan.log"),
        help="Optional log file path (appends).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    k_primary = int(args.stop_window)
    if k_primary < 1:
        raise SystemExit("--stop-window must be >= 1")
    k_list_raw = str(args.stop_window_list or "").strip()
    if k_list_raw:
        parts = re.split(r"[,\s]+", k_list_raw)
        ks = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            try:
                ks.append(int(p))
            except ValueError:
                raise SystemExit(f"Invalid --stop-window-list entry: {p}")
        k_list = sorted({k for k in ks if int(k) >= 1} | {int(k_primary)})
    else:
        k_list = [int(k_primary)]
    k_set = set(int(x) for x in k_list)
    max_k = int(max(k_list)) if k_list else int(k_primary)

    progress_every = int(args.progress_every)
    log_path = Path(args.log) if args.log else None
    log_f = None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_f = log_path.open("a", encoding="utf-8")

    def log(msg: str) -> None:
        print(msg, flush=True)
        if log_f is not None:
            log_f.write(msg + "\n")
            log_f.flush()

    if args.input:
        files = [Path(args.input)]
    else:
        files = read_manifest_files()
    if not files:
        raise SystemExit("No RefSeq FASTA shards found. Run scripts/fetch_datasets.py first.")

    # ---- Cache short-circuit (single input shard mode) ----
    out_json = Path(args.out_json)
    if args.input and not args.force:
        fp0 = files[0]
        input_name = fp0.name
        input_sha = manifest_sha256_for_refseq_shard(input_name)
        cache_key = {
            "analysis": "refseq_transcriptome_shard",
            "analysis_version": ANALYSIS_VERSION,
            "stop_window": int(k_primary),
            "stop_window_list": [int(x) for x in k_list],
            "input_name": input_name,
            "input_sha256": input_sha,
            "mu_star": MU_STAR,
        }
        meta = {
            "cache_key": cache_key,
            "cache_digest": cache_key_digest(cache_key),
        }
        # If the caller requests meta sidecars, require meta match for a cache hit (prevents false hits
        # when parameters change but the output filename stays the same).
        require_meta = bool(args.write_meta)
        if cache_hit(out_json, expected_meta=meta, require_meta=require_meta):
            # Back-compat: if meta is missing, write it (optional).
            if args.write_meta and not cache_meta_path(out_json).exists():
                write_json_atomic(cache_meta_path(out_json), meta)
            print(f"[cache] hit: {out_json}", flush=True)
            return

    # Aggregate stats over best ORF per transcript.
    n_records = 0
    n_with_orf = 0
    total_nt = 0

    orf_len_hist: Counter[int] = Counter()
    term_stop_counts: Counter[str] = Counter()
    term_stop_boundary = 0

    # Coding-region token counts.
    codon_counts: Counter[str] = Counter()
    aa_counts: Counter[str] = Counter()
    v_hist: Counter[int] = Counter()
    delta_hist: Counter[int] = Counter()
    boundary_token_count = 0
    total_coding_tokens = 0

    # Sequence-level Z-spectrum fingerprint metrics over best ORFs (coding tokens, excluding terminal stop).
    orf_boundary_rates: list[float] = []
    orf_entropy_z: list[float] = []
    orf_autocorr_z1: list[float] = []

    # Stop-context window means at terminal stop codons (only best ORF termination).
    # Track multi-k in one pass; keep the primary-k views for legacy fragments/fields.
    before_stats_mk: dict[str, dict[int, RunningStats]] = {s: {kk: RunningStats() for kk in k_list} for s in STOP_CODONS}
    after_stats_mk: dict[str, dict[int, RunningStats]] = {s: {kk: RunningStats() for kk in k_list} for s in STOP_CODONS}
    before_stats: dict[str, RunningStats] = {s: before_stats_mk[s][int(k_primary)] for s in STOP_CODONS}
    after_stats: dict[str, RunningStats] = {s: after_stats_mk[s][int(k_primary)] for s in STOP_CODONS}

    for fp in files:
        if not fp.exists():
            continue
        for rid, seq in iter_fasta(str(fp)):
            n_records += 1
            total_nt += len(seq)
            if args.max_records and n_records > int(args.max_records):
                break
            if progress_every > 0 and (n_records % progress_every == 0):
                log(
                    f"[progress] records={n_records} with_orf={n_with_orf} coding_tokens={total_coding_tokens} "
                    f"boundary_rate={(boundary_token_count / total_coding_tokens) if total_coding_tokens else 0.0:.5f}"
                )

            best = best_orf_across_frames(seq)
            if best is None:
                continue

            # Basic ORF info.
            s = best.start_base
            t = best.stop_base
            frame = best.frame
            start_codon = seq[s : s + 3]
            stop_codon = seq[t : t + 3]
            if start_codon != START_CODON or stop_codon not in STOP_CODONS:
                continue
            n_with_orf += 1

            orf_len_hist[int(best.length_codons_including_stop - 1)] += 1
            term_stop_counts[stop_codon] += 1

            if int(CODON_INFO[stop_codon]["is_boundary"]) == 1:
                term_stop_boundary += 1

            # Coding token loop: from start codon through last sense codon (exclude terminal stop codon).
            local_len = 0
            local_boundary = 0
            local_v_hist: Counter[int] = Counter()
            sum_v_local = 0.0
            sum_v2_local = 0.0
            sum_vv1_local = 0.0
            first_v: int | None = None
            last_v: int | None = None

            for pos in range(s, t, 3):
                codon = seq[pos : pos + 3]
                if codon not in GENETIC_CODE:
                    continue
                info = CODON_INFO[codon]
                aa = str(info["aa"])
                if aa == "Stop":
                    continue

                v_i = int(info["v"])
                local_len += 1
                local_v_hist[v_i] += 1
                sum_v_local += float(v_i)
                sum_v2_local += float(v_i * v_i)
                if first_v is None:
                    first_v = v_i
                if last_v is not None:
                    sum_vv1_local += float(last_v * v_i)
                last_v = v_i

                codon_counts[codon] += 1
                aa_counts[aa] += 1
                v_hist[int(info["v"])] += 1
                delta_hist[int(info["delta"])] += 1
                if int(info["is_boundary"]) == 1:
                    local_boundary += 1
                    boundary_token_count += 1
                total_coding_tokens += 1

            # Sequence-level metrics for this ORF.
            if local_len > 0:
                p_b = local_boundary / float(local_len)
                orf_boundary_rates.append(p_b)

                # Entropy of V distribution within ORF.
                h = 0.0
                for c in local_v_hist.values():
                    p = float(c) / float(local_len)
                    if p > 0:
                        h -= p * math.log2(p)
                orf_entropy_z.append(h)

                # Lag-1 autocorrelation of V along ORF (requires at least 3 tokens -> >=2 pairs).
                if local_len >= 3 and first_v is not None and last_v is not None:
                    n_pairs = local_len - 1
                    sum_x = sum_v_local - float(last_v)
                    sum_y = sum_v_local - float(first_v)
                    sum_x2 = sum_v2_local - float(last_v * last_v)
                    sum_y2 = sum_v2_local - float(first_v * first_v)
                    mx = sum_x / float(n_pairs)
                    my = sum_y / float(n_pairs)
                    cov = (sum_vv1_local / float(n_pairs)) - (mx * my)
                    var_x = (sum_x2 / float(n_pairs)) - (mx * mx)
                    var_y = (sum_y2 / float(n_pairs)) - (my * my)
                    if var_x > 0 and var_y > 0:
                        orf_autocorr_z1.append(cov / math.sqrt(var_x * var_y))

            # Stop-context windows around the terminal stop in the best ORF.
            stop_index = (t - s) // 3  # within ORF (0-based), includes stop position index
            if stop_index >= 1 and max_k >= 1:
                # After-window: scan forward until invalid/out-of-range; this determines which k are feasible.
                after_sums: dict[int, float] = {}
                sum_after = 0.0
                after_len = 0
                for j in range(1, max_k + 1):
                    p = t + 3 * j
                    if p + 3 > len(seq):
                        break
                    c = seq[p : p + 3]
                    if c not in GENETIC_CODE:
                        break
                    sum_after += float(int(CODON_INFO[c]["delta"]))
                    after_len = j
                    if j in k_set:
                        after_sums[j] = sum_after

                # Before-window: scan backward inside ORF (should be valid, but guard anyway).
                before_sums: dict[int, float] = {}
                sum_before = 0.0
                before_len = 0
                j_max_before = min(int(stop_index), int(max_k))
                for j in range(1, j_max_before + 1):
                    p = t - 3 * j
                    c = seq[p : p + 3]
                    if c not in GENETIC_CODE:
                        break
                    sum_before += float(int(CODON_INFO[c]["delta"]))
                    before_len = j
                    if j in k_set:
                        before_sums[j] = sum_before

                # Update only when both sides exist for the same k (matches previous behavior).
                for kk in k_list:
                    kk_i = int(kk)
                    if kk_i <= 0:
                        continue
                    if kk_i > before_len or kk_i > after_len:
                        continue
                    if kk_i not in before_sums or kk_i not in after_sums:
                        continue
                    before_stats_mk[stop_codon][kk_i].update(float(before_sums[kk_i]) / float(kk_i))
                    after_stats_mk[stop_codon][kk_i].update(float(after_sums[kk_i]) / float(kk_i))

        if args.max_records and n_records >= int(args.max_records):
            break

    if total_coding_tokens <= 0 or n_with_orf <= 0:
        raise SystemExit("No coding tokens found; check input FASTA shards.")

    # Derived summary stats.
    n_orf = hist_total(orf_len_hist)
    mean_orf = float(hist_sum(orf_len_hist)) / float(n_orf)
    median_orf = float(hist_quantile_inclusive(orf_len_hist, 0.5))
    p25_orf = float(hist_quantile_inclusive(orf_len_hist, 0.25))
    p75_orf = float(hist_quantile_inclusive(orf_len_hist, 0.75))
    min_orf = int(min(orf_len_hist.keys()))
    max_orf = int(max(orf_len_hist.keys()))

    boundary_rate = boundary_token_count / float(total_coding_tokens)

    # Observed codon-usage statistics.
    sum_v = 0.0
    sum_u = 0.0
    for codon, cnt in codon_counts.items():
        info = CODON_INFO[codon]
        sum_v += float(cnt) * float(info["v"])
        sum_u += float(cnt) * float(info["delta"])
    zbar = sum_v / float(total_coding_tokens)
    ubar = sum_u / float(total_coding_tokens)

    null = codon_usage_null_test(aa_counts, observed_zbar=zbar, observed_ubar=ubar)

    # Stop-context comparisons (Welch t-test).
    stop_ctx_summary: dict[str, dict[str, float | int | None]] = {}
    for s in STOP_CODONS:
        bs = before_stats[s]
        a_s = after_stats[s]
        stop_ctx_summary[s] = {
            "k": int(k_primary),
            "n": int(bs.n),
            "before_mean": (float(bs.mean) if bs.n > 0 else None),
            "after_mean": (float(a_s.mean) if a_s.n > 0 else None),
        }

    p_before = {
        "UAA_vs_UAG": welch_t_p_value_two_sided_from_stats(before_stats["UAA"], before_stats["UAG"]),
        "UAA_vs_UGA": welch_t_p_value_two_sided_from_stats(before_stats["UAA"], before_stats["UGA"]),
        "UAG_vs_UGA": welch_t_p_value_two_sided_from_stats(before_stats["UAG"], before_stats["UGA"]),
    }
    p_after = {
        "UAA_vs_UAG": welch_t_p_value_two_sided_from_stats(after_stats["UAA"], after_stats["UAG"]),
        "UAA_vs_UGA": welch_t_p_value_two_sided_from_stats(after_stats["UAA"], after_stats["UGA"]),
        "UAG_vs_UGA": welch_t_p_value_two_sided_from_stats(after_stats["UAG"], after_stats["UGA"]),
    }

    summary = {
        "schema_version": int(SCHEMA_VERSION),
        "source_files": [str(p) for p in files],
        "records": n_records,
        "records_with_orf": n_with_orf,
        "total_nt": total_nt,
        "coding_tokens": total_coding_tokens,
        "boundary_token_count": boundary_token_count,
        "boundary_rate": boundary_rate,
        "orf_len_codons_excl_stop": {
            "mean": mean_orf,
            "median": median_orf,
            "p25": p25_orf,
            "p75": p75_orf,
            "min": min_orf,
            "max": max_orf,
        },
        "orf_len_hist": {str(k): int(v) for k, v in sorted(orf_len_hist.items())},
        "termination_stop_counts": {k: int(v) for k, v in term_stop_counts.items()},
        "termination_stop_boundary_count": int(term_stop_boundary),
        "stop_window": int(k_primary),
        "stop_window_list": [int(x) for x in k_list],
        "stop_context": stop_ctx_summary,
        "stop_context_welford": {
            s: {
                "before": {"n": int(before_stats[s].n), "mean": float(before_stats[s].mean), "M2": float(before_stats[s].M2)},
                "after": {"n": int(after_stats[s].n), "mean": float(after_stats[s].mean), "M2": float(after_stats[s].M2)},
            }
            for s in STOP_CODONS
        },
        "stop_context_welford_multi_k": {
            s: {
                str(kk): {
                    "before": {
                        "n": int(before_stats_mk[s][int(kk)].n),
                        "mean": float(before_stats_mk[s][int(kk)].mean),
                        "M2": float(before_stats_mk[s][int(kk)].M2),
                    },
                    "after": {
                        "n": int(after_stats_mk[s][int(kk)].n),
                        "mean": float(after_stats_mk[s][int(kk)].mean),
                        "M2": float(after_stats_mk[s][int(kk)].M2),
                    },
                }
                for kk in k_list
            }
            for s in STOP_CODONS
        },
        "stop_context_p_before": p_before,
        "stop_context_p_after": p_after,
        "codon_counts": {k: int(v) for k, v in sorted(codon_counts.items())},
        "aa_counts": {k: int(v) for k, v in sorted(aa_counts.items())},
        "codon_usage": {
            "zbar": zbar,
            "ubar": ubar,
            "null": null,
        },
        "zspectrum_metrics": {
            "boundary_rate": _summarize_float_list(orf_boundary_rates),
            "entropy_Z": _summarize_float_list(orf_entropy_z),
            "autocorr_Z1": _summarize_float_list(orf_autocorr_z1),
        },
        # Store raw samples in shard outputs for exact merge of quantiles across shards.
        "zspectrum_metrics_samples": {
            "boundary_rate": orf_boundary_rates,
            "entropy_Z": orf_entropy_z,
            "autocorr_Z1": orf_autocorr_z1,
        },
        "V_hist": {str(k): int(v) for k, v in sorted(v_hist.items())},
        "Delta_hist": {str(k): int(v) for k, v in sorted(delta_hist.items())},
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_json, summary)
    log(f"[done] wrote {out_json}")

    if args.write_meta and args.input:
        fp0 = files[0]
        input_name = fp0.name
        input_sha = manifest_sha256_for_refseq_shard(input_name)
        cache_key = {
            "analysis": "refseq_transcriptome_shard",
            "analysis_version": ANALYSIS_VERSION,
            "stop_window": int(k_primary),
            "stop_window_list": [int(x) for x in k_list],
            "input_name": input_name,
            "input_sha256": input_sha,
            "mu_star": MU_STAR,
        }
        meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
        write_json_atomic(cache_meta_path(out_json), meta)

    if args.no_latex:
        if log_f is not None:
            log_f.close()
        return

    # ---- LaTeX fragments ----
    # 1) Brief summary paragraph.
    stop_total = sum(term_stop_counts.values())
    uaa = term_stop_counts.get("UAA", 0)
    uag = term_stop_counts.get("UAG", 0)
    uga = term_stop_counts.get("UGA", 0)
    s = []
    s.append(
        "On the human RefSeq mRNA corpus (best-ORF per transcript, $\\mu^\\ast$), "
        f"we analyzed $n={n_with_orf}$ transcripts with a detected ORF (out of $n={n_records}$ records). "
        f"The terminal stop distribution is $\\mathrm{{UAA}}:{uaa}$, $\\mathrm{{UAG}}:{uag}$, $\\mathrm{{UGA}}:{uga}$ "
        f"(total {stop_total}); the boundary-stop rate is {term_stop_boundary}/{stop_total}. "
        f"Across coding tokens (excluding terminal stops), the boundary rate is $\\widehat{{p}}_B={boundary_rate:.4f}$. "
        f"ORF length (codons, excluding stop): mean {mean_orf:.1f}, median {median_orf:.0f}, "
        f"IQR [{p25_orf:.0f},{p75_orf:.0f}]."
    )
    write_text(generated_dir() / "refseq_transcriptome_summary.tex", "\n".join(s) + "\n")

    # 2) Termination stop table rows.
    rows = []
    for codon in STOP_CODONS:
        c = int(term_stop_counts.get(codon, 0))
        frac = (c / stop_total) if stop_total else 0.0
        rows.append(f"{codon} & {c} & {frac:.4f} \\\\")
    write_text(generated_dir() / "refseq_termination_stop_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")

    # 3) Stop-context window rows (primary k only; multi-k handled in merge).
    rows2 = []
    for codon in STOP_CODONS:
        n = int(before_stats[codon].n)
        bm = float(before_stats[codon].mean) if n else float("nan")
        am = float(after_stats[codon].mean) if n else float("nan")
        rows2.append(f"{codon} & {k_primary} & {n} & {bm:.4f} & {am:.4f} \\\\")
    write_text(generated_dir() / "refseq_stop_context_rows.tex", "\n".join(rows2) + "\n\\bottomrule\n")

    # 4) Codon-usage null-model summary (single paragraph).
    null_s = (
        "Codon-usage summary over coding tokens (excluding terminal stops): "
        f"$\\overline{{Z}}={zbar:.4f}$, $\\overline{{U}}={ubar:.4f}$. "
        "Under an amino-acid preserving null (uniform choice among synonymous codons), "
        f"$\\mathbb{{E}}[\\overline{{Z}}]={null['null_mu_zbar']:.4f}$ with $\\mathrm{{sd}}={null['null_sd_zbar']:.6f}$ "
        f"($z={null['z_zbar']:.2f}$, $p={null['p_zbar']:.4g}$), and "
        f"$\\mathbb{{E}}[\\overline{{U}}]={null['null_mu_ubar']:.4f}$ with $\\mathrm{{sd}}={null['null_sd_ubar']:.6f}$ "
        f"($z={null['z_ubar']:.2f}$, $p={null['p_ubar']:.4g}$)."
    )
    write_text(generated_dir() / "refseq_codon_usage_null.tex", null_s + "\n")

    # 5) Z-spectrum fingerprint metrics (single paragraph).
    zfp = summary["zspectrum_metrics"]
    s_fp = (
        "\\begin{tabular}{@{}l@{}}\n"
        "Z-spectrum fingerprint metrics over best ORFs (excluding terminal stops):\\\\\n"
        f"boundary-rate mean {zfp['boundary_rate']['mean']:.4f}, median {zfp['boundary_rate']['median']:.4f}\\\\\n"
        f"entropy $H(Z)$ mean {zfp['entropy_Z']['mean']:.4f}, median {zfp['entropy_Z']['median']:.4f}\\\\\n"
        f"lag-1 autocorrelation $\\rho(Z_i,Z_{{i+1}})$ mean {zfp['autocorr_Z1']['mean']:.4f}, "
        f"median {zfp['autocorr_Z1']['median']:.4f} (n={int(zfp['autocorr_Z1']['n'])}).\n"
        "\\end{tabular}"
    )
    write_text(generated_dir() / "refseq_zspectrum_fingerprint.tex", s_fp + "\n")

    log("[done] wrote LaTeX fragments under sections/generated/")
    if log_f is not None:
        log_f.close()


if __name__ == "__main__":
    main()


