# -*- coding: utf-8 -*-
"""
Recoding-site experiment (Sec/Pyl/readthrough interface).

Parse GenBank flatfiles downloaded under data/recoding_genbank/genbank/*.gb,
extract transl_except annotations, and compute Fold_6 uplift context statistics
under mu*.

Outputs:
  - data/recoding_genbank/recoding_sites.jsonl
  - sections/generated/recoding_sites_rows.tex
  - sections/generated/recoding_sites_summary.tex
  - sections/generated/recoding_context_tests.tex

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import (
    BOUNDARY_WORDS,
    GENETIC_CODE,
    STOP_CODONS,
    fold_codon,
    student_t_cdf,
)
from stats_tools import bh_fdr, normal_two_sided_p, summarize_mean_diff


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 2


def _stable_seed_u32(tag: str) -> int:
    """
    Deterministic 32-bit seed from a string tag (independent of Python's hash randomization).
    """
    h = hashlib.sha256(tag.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_dir() -> Path:
    return root_dir() / "data" / "recoding_genbank"


def genbank_dir() -> Path:
    return data_dir() / "genbank"


def manifest_path() -> Path:
    return root_dir() / "data" / "manifest.json"


def read_manifest() -> dict[str, Any] | None:
    mp = manifest_path()
    if not mp.exists():
        return None
    try:
        obj = json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _fmt_p_tex(p: float | None) -> tuple[str, str]:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "=", "NA"
    p0 = float(p)
    if p0 == 0.0:
        return "<", "10^{-300}"
    if p0 < 1e-4:
        return "=", f"{p0:.2e}"
    return "=", f"{p0:.4f}"


def strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


@dataclass(frozen=True)
class Feature:
    key: str
    location: str
    qualifiers: dict[str, list[str]]


def parse_qualifiers(lines: list[str]) -> dict[str, list[str]]:
    """
    Parse GenBank qualifier lines (already restricted to a feature block).
    """
    out: dict[str, list[str]] = {}
    cur: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal cur, buf
        if cur is None:
            return
        s = "".join(buf).strip()
        name = cur
        value = ""
        if "=" in s:
            name, value = s.split("=", 1)
            name = name.strip()
            value = strip_quotes(value.strip())
        out.setdefault(name, []).append(value)
        cur = None
        buf = []

    for raw in lines:
        t = raw.strip()
        if not t:
            continue
        if t.startswith("/"):
            flush()
            cur = t[1:].strip()
            buf = [cur]
        else:
            if cur is None:
                continue
            buf.append(t)
    flush()
    return out


def parse_features(record_text: str) -> list[Feature]:
    lines = record_text.splitlines()
    try:
        i0 = next(i for i, line in enumerate(lines) if line.startswith("FEATURES"))
    except StopIteration:
        return []
    feats: list[Feature] = []
    i = i0 + 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("ORIGIN"):
            break
        if line.startswith("     ") and not line.startswith("                     "):
            key = line[5:21].strip()
            loc = line[21:].strip()
            i += 1
            qlines: list[str] = []
            while i < len(lines):
                l2 = lines[i]
                if l2.startswith("ORIGIN"):
                    break
                if l2.startswith("     ") and not l2.startswith("                     "):
                    break
                if l2.startswith("                     "):
                    qlines.append(l2)
                i += 1
            quals = parse_qualifiers(qlines)
            feats.append(Feature(key=key, location=loc, qualifiers=quals))
        else:
            i += 1
    return feats


def parse_origin_seq(record_text: str) -> str:
    lines = record_text.splitlines()
    try:
        i0 = next(i for i, line in enumerate(lines) if line.startswith("ORIGIN"))
    except StopIteration:
        return ""
    parts: list[str] = []
    for line in lines[i0 + 1 :]:
        if line.strip() == "//":
            break
        parts.append(re.sub(r"[^A-Za-z]", "", line))
    return "".join(parts).upper()


def parse_version(record_text: str) -> str | None:
    for line in record_text.splitlines():
        if line.startswith("VERSION"):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1].strip()
    for line in record_text.splitlines():
        if line.startswith("ACCESSION"):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1].strip()
    return None


def parse_definition(record_text: str) -> str | None:
    lines = record_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("DEFINITION"):
            s = line[len("DEFINITION") :].strip()
            j = i + 1
            while j < len(lines) and lines[j].startswith("            "):
                s += " " + lines[j].strip()
                j += 1
            return s.strip()
    return None


def parse_organism_and_domain(record_text: str) -> tuple[str | None, str | None]:
    """
    Extract ORGANISM line and its top-level taxonomic domain from the SOURCE block.
    Domain is inferred from the first token of the taxonomy lineage (Eukaryota/Bacteria/Archaea/...).
    """
    lines = record_text.splitlines()
    organism: str | None = None
    dom: str | None = None
    for i, line in enumerate(lines):
        if line.startswith("  ORGANISM"):
            organism = line[len("  ORGANISM") :].strip() or None
            lineage_parts: list[str] = []
            j = i + 1
            while j < len(lines) and lines[j].startswith("            "):
                lineage_parts.append(lines[j].strip())
                j += 1
            lineage = " ".join(lineage_parts).strip()
            if lineage:
                dom = lineage.split(";", 1)[0].strip() or None
            break
    return organism, dom


_COMPLEMENT = str.maketrans({"A": "T", "C": "G", "G": "C", "T": "A", "N": "N"})


def revcomp_dna(s: str) -> str:
    return s.translate(_COMPLEMENT)[::-1]


def codon_at_strand(seq_dna: str, pos_start_1: int, *, strand: int) -> str | None:
    """
    Return the codon DNA triplet in the translated orientation of the CDS strand.
    pos_start_1 is the 1-based coordinate of the low coordinate of the triplet.
    strand is +1 (forward) or -1 (complement).
    """
    i0 = pos_start_1 - 1
    if i0 < 0 or i0 + 3 > len(seq_dna):
        return None
    c = seq_dna[i0 : i0 + 3].upper()
    if any(ch not in "ACGTN" for ch in c):
        return None
    if "N" in c:
        return None
    if strand == -1:
        c = revcomp_dna(c)
    return c


def delta_window_means_strand(
    seq_dna: str,
    center_pos_1: int,
    k: int,
    *,
    strand: int,
    left_bound_1: int,
    right_bound_1: int,
) -> tuple[float | None, float | None]:
    """
    Strand-aware version of delta_window_means.
    Bounds are inclusive base coordinates for allowable codon triplets (require p>=left and p+2<=right).
    """
    if strand not in (1, -1):
        raise ValueError("strand must be +1 or -1")
    step = 3 * strand

    before: list[float] = []
    after: list[float] = []

    for j in range(1, k + 1):
        p = center_pos_1 - step * j
        if p < left_bound_1 or p + 2 > right_bound_1:
            return None, None
        c = codon_at_strand(seq_dna, p, strand=strand)
        if c is None:
            return None, None
        f = fold_codon(c.replace("T", "U"), MU_STAR)
        before.append(float(f.delta))

    for j in range(1, k + 1):
        p = center_pos_1 + step * j
        if p < left_bound_1 or p + 2 > right_bound_1:
            return None, None
        c = codon_at_strand(seq_dna, p, strand=strand)
        if c is None:
            return None, None
        f = fold_codon(c.replace("T", "U"), MU_STAR)
        after.append(float(f.delta))

    return mean(before), mean(after)


def _cds_strand(location: str) -> int:
    return -1 if location.strip().startswith("complement(") else 1


def _translation_start_pos_start(cds_start: int, cds_end: int, codon_start: int, *, strand: int) -> int:
    """
    Return the 1-based codon-start coordinate (low coordinate of the triplet) of the first translated codon.
    Best-effort; most records have codon_start=1.
    """
    if strand == 1:
        return cds_start + (codon_start - 1)
    return (cds_end - (codon_start - 1)) - 2


def _iter_codon_starts(cds_start: int, cds_end: int, first_pos_start: int, *, strand: int) -> list[int]:
    """
    Enumerate codon-start coordinates (low coordinate of each triplet) along the CDS, aligned to the strand.
    """
    if strand == 1:
        p = first_pos_start
        out: list[int] = []
        while p + 2 <= cds_end:
            if p >= cds_start:
                out.append(p)
            p += 3
        return out
    p = first_pos_start
    out = []
    while p >= cds_start:
        if p + 2 <= cds_end:
            out.append(p)
        p -= 3
    return out


_LOC_RE = re.compile(r"(\d+)\.\.(\d+)")


def parse_simple_range(location: str) -> tuple[int, int] | None:
    """
    Minimal location parser: return (start,end) for patterns like 53..733.
    For join()/complement() we fall back to the first/last numeric ranges.
    Coordinates are 1-based inclusive.
    """
    pairs = [(int(a), int(b)) for a, b in _LOC_RE.findall(location)]
    if not pairs:
        return None
    start = min(a for a, _ in pairs)
    end = max(b for _, b in pairs)
    return start, end


_TRANSL_EXCEPT_RE = re.compile(
    r"pos:(?:complement\()?(?P<start>\d+)\.\.(?P<end>\d+)\)?\s*,\s*aa:(?P<aa>[A-Za-z]+)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class RecodingSite:
    version: str
    definition: str
    organism: str | None
    domain: str | None
    cds_location: str
    cds_start: int
    cds_end: int
    cds_strand: int
    translation_start: int
    gene: str | None
    product: str | None
    aa: str
    pos_start: int
    pos_end: int
    codon_dna: str
    codon_rna: str
    n: int
    w: str
    v: int
    delta: int
    is_boundary: bool
    k: int
    before_mean_delta: float | None
    after_mean_delta: float | None
    terminal_stop: str | None
    terminal_before_mean_delta: float | None
    terminal_after_mean_delta: float | None
    # Control-B: same-codon internal controls from the same CDS (if available).
    control_same_codon_before_mean_delta: float | None
    control_same_codon_after_mean_delta: float | None
    # Control-C: random internal coding positions from the same CDS (non-stop, excluding transl_except).
    control_random_cds_before_mean_delta: float | None
    control_random_cds_after_mean_delta: float | None


def mean(xs: list[float]) -> float:
    return float(sum(xs)) / float(len(xs))


def sample_variance(xs: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    return statistics.pvariance(xs) * (n / (n - 1))


def cohen_d_equal_weight(xs: list[float], ys: list[float]) -> float | None:
    """
    Simple standardized mean difference using the average of sample variances:
        d = (mean(xs) - mean(ys)) / sqrt((s_x^2 + s_y^2)/2)
    """
    v1 = sample_variance(xs)
    v2 = sample_variance(ys)
    if v1 is None or v2 is None:
        return None
    denom = math.sqrt((v1 + v2) / 2.0)
    if denom <= 0:
        return None
    return (mean(xs) - mean(ys)) / denom


def welch_t_p_value_two_sided(xs: list[float], ys: list[float]) -> float | None:
    """
    Two-sided Welch t-test p-value.
    Uses a Student-t CDF implementation that expects integer df; df is rounded.
    """
    n1 = len(xs)
    n2 = len(ys)
    if n1 < 2 or n2 < 2:
        return None
    m1 = mean(xs)
    m2 = mean(ys)
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


def codon_at(seq_dna: str, pos_start_1: int) -> str | None:
    i0 = pos_start_1 - 1
    if i0 < 0 or i0 + 3 > len(seq_dna):
        return None
    c = seq_dna[i0 : i0 + 3].upper()
    if any(ch not in "ACGT" for ch in c):
        return None
    return c


def delta_window_means(seq_dna: str, center_pos_1: int, k: int, *, left_bound_1: int, right_bound_1: int) -> tuple[float | None, float | None]:
    """
    Compute mean Delta in k codons before/after a codon that starts at center_pos_1 (1-based),
    using mu*. Bounds are inclusive base coordinates for allowable codon starts (translation region),
    i.e. require pos in [left_bound_1, right_bound_1-2].
    Returns (before_mean, after_mean) or (None,None) if full window is not available/valid.
    """
    before: list[float] = []
    after: list[float] = []

    for j in range(1, k + 1):
        p = center_pos_1 - 3 * j
        if p < left_bound_1 or p + 2 > right_bound_1:
            return None, None
        c = codon_at(seq_dna, p)
        if c is None:
            return None, None
        f = fold_codon(c.replace("T", "U"), MU_STAR)
        before.append(float(f.delta))

    for j in range(1, k + 1):
        p = center_pos_1 + 3 * j
        if p < left_bound_1 or p + 2 > right_bound_1:
            return None, None
        c = codon_at(seq_dna, p)
        if c is None:
            return None, None
        f = fold_codon(c.replace("T", "U"), MU_STAR)
        after.append(float(f.delta))

    return mean(before), mean(after)


def extract_recoding_sites_from_record(record_text: str, *, k: int) -> list[RecodingSite]:
    version = parse_version(record_text)
    if version is None:
        return []
    definition = parse_definition(record_text) or ""
    organism, domain = parse_organism_and_domain(record_text)
    seq_dna = parse_origin_seq(record_text)
    if not seq_dna:
        return []

    feats = parse_features(record_text)
    out: list[RecodingSite] = []
    for feat in feats:
        if feat.key != "CDS":
            continue
        if "transl_except" not in feat.qualifiers:
            continue

        # Skip complex join() locations (common in genomic eukaryotic records) to keep parsing correct.
        if "join(" in feat.location:
            continue

        loc = parse_simple_range(feat.location)
        if loc is None:
            continue
        cds_start, cds_end = loc
        strand = _cds_strand(feat.location)
        codon_start = 1
        if "codon_start" in feat.qualifiers and feat.qualifiers["codon_start"]:
            try:
                codon_start = int(feat.qualifiers["codon_start"][0] or "1")
            except ValueError:
                codon_start = 1
        translation_start = _translation_start_pos_start(cds_start, cds_end, codon_start, strand=strand)
        left_bound_1 = translation_start if strand == 1 else cds_start
        right_bound_1 = cds_end if strand == 1 else (translation_start + 2)

        gene = feat.qualifiers.get("gene", [None])[0]
        product = feat.qualifiers.get("product", [None])[0]

        # Terminal stop (best-effort): last codon inside CDS range.
        term_stop: str | None = None
        term_before: float | None = None
        term_after: float | None = None
        n_codons: int | None = None
        if strand == 1:
            if (cds_end - translation_start + 1) >= 3:
                n_codons = (cds_end - translation_start + 1) // 3
        else:
            if (translation_start - cds_start + 3) >= 3:
                n_codons = (translation_start - cds_start + 3) // 3
        if n_codons and n_codons >= 1:
            last_start = translation_start + (3 * strand) * (n_codons - 1)
            c_last = codon_at_strand(seq_dna, last_start, strand=strand)
            if c_last is not None:
                r_last = c_last.replace("T", "U")
                if r_last in STOP_CODONS:
                    term_stop = r_last
                    # For termination, allow after-window to extend beyond CDS when sequence is present.
                    term_before, term_after = delta_window_means_strand(
                        seq_dna,
                        last_start,
                        k,
                        strand=strand,
                        left_bound_1=1,
                        right_bound_1=len(seq_dna),
                    )

        # Precompute aligned codon-start coordinates in this CDS for Control-B.
        codon_starts = _iter_codon_starts(cds_start, cds_end, translation_start, strand=strand)
        recoding_positions: set[int] = set()
        for val in feat.qualifiers.get("transl_except", []):
            m = _TRANSL_EXCEPT_RE.search(val)
            if not m:
                continue
            recoding_positions.add(int(m.group(1)))

        # Control-C pool: random internal codon positions within CDS (exclude transl_except + stop codons),
        # with complete k-windows in both directions.
        eligible_random_controls: list[tuple[int, float, float]] = []
        for p in codon_starts:
            if p in recoding_positions:
                continue
            c = codon_at_strand(seq_dna, p, strand=strand)
            if c is None:
                continue
            r = c.replace("T", "U")
            if r in STOP_CODONS:
                continue
            b, a = delta_window_means_strand(
                seq_dna,
                p,
                k,
                strand=strand,
                left_bound_1=left_bound_1,
                right_bound_1=right_bound_1,
            )
            if b is None or a is None:
                continue
            eligible_random_controls.append((p, float(b), float(a)))

        for val in feat.qualifiers.get("transl_except", []):
            m = _TRANSL_EXCEPT_RE.search(val)
            if not m:
                continue
            pos_start = int(m.group(1))
            pos_end = int(m.group(2))
            aa = m.group(3)
            if pos_end - pos_start != 2:
                continue
            dna = codon_at_strand(seq_dna, pos_start, strand=strand)
            if dna is None:
                continue
            rna = dna.replace("T", "U")
            # Only keep sites that map to a defined codon; for Pyl/Sec we expect UAG/UGA.
            if rna not in GENETIC_CODE:
                continue
            f = fold_codon(rna, MU_STAR)

            before_m, after_m = delta_window_means_strand(
                seq_dna,
                pos_start,
                k,
                strand=strand,
                left_bound_1=left_bound_1,
                right_bound_1=right_bound_1,
            )

            # Control-B: same-codon positions inside CDS (exclude all transl_except sites).
            M = 8
            candidate_controls: list[int] = []
            for p in codon_starts:
                if p in recoding_positions:
                    continue
                c = codon_at_strand(seq_dna, p, strand=strand)
                if c is None:
                    continue
                if c.replace("T", "U") == rna:
                    candidate_controls.append(p)

            ctrl_before_mean: float | None = None
            ctrl_after_mean: float | None = None
            if candidate_controls:
                rng = random.Random(f"{version}:{pos_start}:{k}")
                rng.shuffle(candidate_controls)
                picks = candidate_controls[:M]
                ctrl_before_vals: list[float] = []
                ctrl_after_vals: list[float] = []
                for p in picks:
                    b, a = delta_window_means_strand(
                        seq_dna,
                        p,
                        k,
                        strand=strand,
                        left_bound_1=left_bound_1,
                        right_bound_1=right_bound_1,
                    )
                    if b is None or a is None:
                        continue
                    ctrl_before_vals.append(float(b))
                    ctrl_after_vals.append(float(a))
                if ctrl_before_vals and ctrl_after_vals:
                    ctrl_before_mean = mean(ctrl_before_vals)
                    ctrl_after_mean = mean(ctrl_after_vals)

            # Control-C: random internal coding controls from the same CDS.
            rand_before_mean: float | None = None
            rand_after_mean: float | None = None
            if eligible_random_controls:
                rng = random.Random(f"{version}:{pos_start}:{k}:rand")
                picks = list(eligible_random_controls)
                rng.shuffle(picks)
                picks = picks[:M]
                rand_before_vals = [b for _, b, _ in picks]
                rand_after_vals = [a for _, _, a in picks]
                if rand_before_vals and rand_after_vals:
                    rand_before_mean = mean([float(x) for x in rand_before_vals])
                    rand_after_mean = mean([float(x) for x in rand_after_vals])

            out.append(
                RecodingSite(
                    version=version,
                    definition=definition,
                    organism=organism,
                    domain=domain,
                    cds_location=feat.location,
                    cds_start=cds_start,
                    cds_end=cds_end,
                    cds_strand=strand,
                    translation_start=translation_start,
                    gene=gene,
                    product=product,
                    aa=aa,
                    pos_start=pos_start,
                    pos_end=pos_end,
                    codon_dna=dna,
                    codon_rna=rna,
                    n=int(f.n),
                    w=str(f.w),
                    v=int(f.v),
                    delta=int(f.delta),
                    is_boundary=bool(f.w in BOUNDARY_WORDS),
                    k=int(k),
                    before_mean_delta=before_m,
                    after_mean_delta=after_m,
                    terminal_stop=term_stop,
                    terminal_before_mean_delta=term_before,
                    terminal_after_mean_delta=term_after,
                    control_same_codon_before_mean_delta=ctrl_before_mean,
                    control_same_codon_after_mean_delta=ctrl_after_mean,
                    control_random_cds_before_mean_delta=rand_before_mean,
                    control_random_cds_after_mean_delta=rand_after_mean,
                )
            )
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recoding sites via transl_except (Sec/Pyl)")
    p.add_argument("--k", type=int, default=10, help="Window radius k for uplift context.")
    p.add_argument(
        "--k-list",
        default="",
        help="Optional comma-separated list of window radii k to compute (e.g. 3,5,10,20). Primary --k is always included.",
    )
    p.add_argument("--max-files", type=int, default=0, help="Optional limit on number of gb files (0=all).")
    p.add_argument("--out-jsonl", default=str(data_dir() / "recoding_sites.jsonl"), help="Output JSONL path.")
    p.add_argument(
        "--out-summary-json",
        default=str(data_dir() / "recoding_sites_summary.json"),
        help="Output JSON summary path (used for caching + fast LaTeX regeneration).",
    )
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    k_primary = int(args.k)
    if k_primary < 1:
        raise SystemExit("--k must be >= 1")
    k_list_raw = str(args.k_list or "").strip()
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
                raise SystemExit(f"Invalid --k-list entry: {p}")
        k_list = sorted({k for k in ks if int(k) >= 1} | {int(k_primary)})
    else:
        k_list = [int(k_primary)]

    gb_files = sorted(genbank_dir().glob("*.gb"))
    if args.max_files:
        gb_files = gb_files[: int(args.max_files)]

    out_jsonl = Path(args.out_jsonl)
    out_summary_json = Path(args.out_summary_json)

    # ---- Cache short-circuit ----
    m = read_manifest()
    sha_by_acc: dict[str, str] = {}
    bytes_by_acc: dict[str, int] = {}
    if m and isinstance(m.get("datasets"), dict):
        ds = (m.get("datasets") or {}).get("ncbi_recoding_genbank")
        if isinstance(ds, dict):
            for e in (ds.get("genbank_files", []) or []):
                if not isinstance(e, dict):
                    continue
                acc = str(e.get("accession") or "").strip()
                sha = str(e.get("sha256") or "").strip()
                if acc and sha:
                    sha_by_acc[acc] = sha
                try:
                    if acc:
                        bytes_by_acc[acc] = int(e.get("bytes", 0) or 0)
                except Exception:
                    pass

    inputs_fp: list[dict[str, object]] = []
    for fp in gb_files:
        acc = fp.name[:-3] if fp.name.endswith(".gb") else fp.name
        st = fp.stat()
        if acc in sha_by_acc:
            inputs_fp.append(
                {
                    "accession": acc,
                    "name": fp.name,
                    "sha256": sha_by_acc[acc],
                    "bytes": int(bytes_by_acc.get(acc, st.st_size) or st.st_size),
                }
            )
        else:
            # Fallback: stable file-stat fingerprint for non-manifest files.
            inputs_fp.append(
                {
                    "accession": acc,
                    "name": fp.name,
                    "bytes": int(st.st_size),
                    "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                }
            )
    inputs_fp.sort(key=lambda x: str(x.get("accession") or x.get("name") or ""))

    cache_key = {
        "analysis": "recoding_sites",
        "analysis_version": int(ANALYSIS_VERSION),
        "k_primary": int(k_primary),
        "k_list": [int(x) for x in k_list],
        "max_files": int(args.max_files or 0),
        "mu_star": MU_STAR,
        "inputs": inputs_fp,
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_summary_json, expected_meta=cache_meta, require_meta=True) and out_jsonl.exists():
        print(f"[cache] hit: {out_summary_json}", flush=True)
        if args.no_latex:
            return
        try:
            summary_cached = json.loads(out_summary_json.read_text(encoding="utf-8"))
        except Exception:
            summary_cached = None
        if not isinstance(summary_cached, dict):
            raise SystemExit("Cached recoding summary JSON is malformed; rerun with --force.")
        _emit_latex_from_cached_summary(summary_cached)
        return

    sites_by_k: dict[int, list[RecodingSite]] = {int(k): [] for k in k_list}
    for fp in gb_files:
        text = fp.read_text(encoding="utf-8", errors="replace")
        for k in k_list:
            sites_by_k[int(k)].extend(extract_recoding_sites_from_record(text, k=int(k)))

    sites = sites_by_k[int(k_primary)]

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for s in sites:
            f.write(json.dumps(s.__dict__, ensure_ascii=False, sort_keys=True) + "\n")

    def cds_key(s: RecodingSite) -> tuple[str, str, int]:
        return (s.version, s.cds_location, s.translation_start)

    def build_term_by_cds(sites_k: list[RecodingSite]) -> dict[tuple[str, str, int], tuple[str | None, float | None, float | None, str | None]]:
    # Deduplicate CDS-level terminal-stop windows (one per CDS, not one per recoding site).
        out: dict[tuple[str, str, int], tuple[str | None, float | None, float | None, str | None]] = {}
        for s0 in sites_k:
            key0 = cds_key(s0)
            if key0 not in out:
                out[key0] = (s0.terminal_stop, s0.terminal_before_mean_delta, s0.terminal_after_mean_delta, s0.domain)
        return out

    term_by_cds = build_term_by_cds(sites)

    # Summary statistics
    aa_counts = Counter(s.aa for s in sites)
    codon_counts = Counter(s.codon_rna for s in sites)
    term_stop_counts = Counter(stop for stop, _, _, _ in term_by_cds.values() if stop is not None)
    domain_counts = Counter((s.domain or "Unknown") for s in sites)
    n_cds = len(term_by_cds)

    def perm_p_value_two_sided(xs: list[float], ys: list[float], *, n_perm: int, seed: int) -> float | None:
        if len(xs) < 2 or len(ys) < 2:
            return None
        rng = random.Random(seed)
        pooled = xs + ys
        n1 = len(xs)
        obs = abs(mean(xs) - mean(ys))
        ge = 0
        for _ in range(int(n_perm)):
            rng.shuffle(pooled)
            x1 = pooled[:n1]
            y1 = pooled[n1:]
            if abs(mean(x1) - mean(y1)) >= obs:
                ge += 1
        return (ge + 1) / float(n_perm + 1)

    def _collect_lists(
        sites_k: list[RecodingSite],
        term_by_cds_k: dict[tuple[str, str, int], tuple[str | None, float | None, float | None, str | None]],
    ) -> dict[str, list[float]]:
        rec_before_f = [float(s.before_mean_delta) for s in sites_k if s.before_mean_delta is not None]
        rec_after_f = [float(s.after_mean_delta) for s in sites_k if s.after_mean_delta is not None]
        term_before_f = [float(b) for _, b, _, _ in term_by_cds_k.values() if b is not None]
        term_after_f = [float(a) for _, _, a, _ in term_by_cds_k.values() if a is not None]
        ctrl_before_f = [float(s.control_same_codon_before_mean_delta) for s in sites_k if s.control_same_codon_before_mean_delta is not None]
        ctrl_after_f = [float(s.control_same_codon_after_mean_delta) for s in sites_k if s.control_same_codon_after_mean_delta is not None]
        rand_before_f = [float(s.control_random_cds_before_mean_delta) for s in sites_k if s.control_random_cds_before_mean_delta is not None]
        rand_after_f = [float(s.control_random_cds_after_mean_delta) for s in sites_k if s.control_random_cds_after_mean_delta is not None]
        return {
            "rec_before": rec_before_f,
            "rec_after": rec_after_f,
            "term_before": term_before_f,
            "term_after": term_after_f,
            "ctrl_before": ctrl_before_f,
            "ctrl_after": ctrl_after_f,
            "rand_before": rand_before_f,
            "rand_after": rand_after_f,
        }

    # ---- Summary / LaTeX outputs are emitted from a cached JSON summary ----
    ROW_LIMIT = 200
    top_sites = sorted(sites, key=lambda x: (x.aa, x.version, x.pos_start))[:ROW_LIMIT]

    @dataclass
    class TestItem:
        label: str
        window: str  # before/after
        k: int
        n1: int
        n2: int
        mean1: float
        mean2: float
        diff: float
        ci_low: float | None
        ci_high: float | None
        d: float | None
        g: float | None
        p_welch: float | None
        q_welch: float | None
        p_perm: float | None

    def _make_test(*, label: str, window: str, k: int, xs: list[float], ys: list[float], seed: int) -> TestItem | None:
        if len(xs) < 2 or len(ys) < 2:
            return None
        summ = summarize_mean_diff(xs, ys)
        if summ is None:
            return None
        p_w = welch_t_p_value_two_sided(xs, ys)
        p_perm = perm_p_value_two_sided(xs, ys, n_perm=2000, seed=int(seed))
        return TestItem(
            label=str(label),
            window=str(window),
            k=int(k),
            n1=int(summ.n_x),
            n2=int(summ.n_y),
            mean1=float(summ.mean_x),
            mean2=float(summ.mean_y),
            diff=float(summ.diff),
            ci_low=(float(summ.ci_low) if summ.ci_low is not None else None),
            ci_high=(float(summ.ci_high) if summ.ci_high is not None else None),
            d=(float(summ.d) if summ.d is not None else None),
            g=(float(summ.g) if summ.g is not None else None),
            p_welch=(float(p_w) if p_w is not None else None),
            q_welch=None,
            p_perm=(float(p_perm) if p_perm is not None else None),
        )

    # ---- Primary-k tests + BH q-values ----
    lists_primary = _collect_lists(sites, term_by_cds)
    rec_before_f = lists_primary["rec_before"]
    rec_after_f = lists_primary["rec_after"]
    term_before_f = lists_primary["term_before"]
    term_after_f = lists_primary["term_after"]
    ctrl_before_f = lists_primary["ctrl_before"]
    ctrl_after_f = lists_primary["ctrl_after"]
    rand_before_f = lists_primary["rand_before"]
    rand_after_f = lists_primary["rand_after"]

    tests_primary: list[TestItem] = []
    # Overall: recoding vs terminal
    for window, xs, ys, seed in (
        ("before", rec_before_f, term_before_f, 50001),
        ("after", rec_after_f, term_after_f, 50002),
    ):
        t0 = _make_test(label="Recoding vs terminal stops (CDS-deduplicated)", window=window, k=k_primary, xs=xs, ys=ys, seed=seed)
        if t0 is not None:
            tests_primary.append(t0)

    # By codon (primary k)
    for codon in sorted(set(s.codon_rna for s in sites)):
        grp_sites = [s for s in sites if s.codon_rna == codon and (s.before_mean_delta is not None) and (s.after_mean_delta is not None)]
        if len(grp_sites) < 2:
            continue
        cds_keys = sorted({cds_key(s) for s in grp_sites})
        term_b = []
        term_a = []
        for k0 in cds_keys:
            if k0 not in term_by_cds:
                continue
            _stop, b0, a0, _dom0 = term_by_cds[k0]
            if b0 is not None:
                term_b.append(float(b0))
            if a0 is not None:
                term_a.append(float(a0))
        xs_b = [float(s.before_mean_delta) for s in grp_sites if s.before_mean_delta is not None]
        xs_a = [float(s.after_mean_delta) for s in grp_sites if s.after_mean_delta is not None]
        tests_primary.extend(
            [
                t
                for t in (
                    _make_test(
                        label=f"By codon $\\mathrm{{{codon}}}$ (recoding vs terminal)",
                        window="before",
                        k=k_primary,
                        xs=xs_b,
                        ys=[float(x) for x in term_b],
                        seed=70001 + _stable_seed_u32("recoding:by_codon:before:" + str(codon)),
                    ),
                    _make_test(
                        label=f"By codon $\\mathrm{{{codon}}}$ (recoding vs terminal)",
                        window="after",
                        k=k_primary,
                        xs=xs_a,
                        ys=[float(x) for x in term_a],
                        seed=70002 + _stable_seed_u32("recoding:by_codon:after:" + str(codon)),
                    ),
                )
                if t is not None
            ]
        )

    # By domain (primary k)
    for dom in sorted(set((s.domain or "Unknown") for s in sites)):
        grp_sites = [s for s in sites if (s.domain or "Unknown") == dom and (s.before_mean_delta is not None) and (s.after_mean_delta is not None)]
        if len(grp_sites) < 2:
            continue
        cds_keys = sorted({cds_key(s) for s in grp_sites})
        term_b = []
        term_a = []
        for k0 in cds_keys:
            if k0 not in term_by_cds:
                continue
            _stop, b0, a0, _dom0 = term_by_cds[k0]
            if b0 is not None:
                term_b.append(float(b0))
            if a0 is not None:
                term_a.append(float(a0))
        xs_b = [float(s.before_mean_delta) for s in grp_sites if s.before_mean_delta is not None]
        xs_a = [float(s.after_mean_delta) for s in grp_sites if s.after_mean_delta is not None]
        tests_primary.extend(
            [
                t
                for t in (
                    _make_test(
                        label=f"By domain {dom} (recoding vs terminal)",
                        window="before",
                        k=k_primary,
                        xs=xs_b,
                        ys=[float(x) for x in term_b],
                        seed=90001 + _stable_seed_u32("recoding:by_domain:before:" + str(dom)),
                    ),
                    _make_test(
                        label=f"By domain {dom} (recoding vs terminal)",
                        window="after",
                        k=k_primary,
                        xs=xs_a,
                        ys=[float(x) for x in term_a],
                        seed=90002 + _stable_seed_u32("recoding:by_domain:after:" + str(dom)),
                    ),
                )
                if t is not None
            ]
        )

    # Controls (primary k): compare recoding vs Control-B / Control-C
    for window, xs, ys, seed, lbl in (
        ("before", rec_before_f, ctrl_before_f, 12345, "Control-B (same CDS, same codon)"),
        ("after", rec_after_f, ctrl_after_f, 23456, "Control-B (same CDS, same codon)"),
        ("before", rec_before_f, rand_before_f, 34567, "Control-C (same CDS, random internal)"),
        ("after", rec_after_f, rand_after_f, 45678, "Control-C (same CDS, random internal)"),
    ):
        t0 = _make_test(label=lbl, window=window, k=k_primary, xs=xs, ys=ys, seed=seed)
        if t0 is not None:
            tests_primary.append(t0)

    # BH-FDR over primary-k Welch p-values.
    pvals = [float(t.p_welch) for t in tests_primary if t.p_welch is not None]
    qvals = bh_fdr(pvals)
    j = 0
    for t in tests_primary:
        if t.p_welch is None:
            continue
        t.q_welch = float(qvals[j])
        j += 1

    # ---- Multi-k sensitivity (overall only; stored in summary JSON) ----
    mk_tests: list[dict[str, object]] = []
    for k in k_list:
        sites_k = sites_by_k[int(k)]
        term_k = build_term_by_cds(sites_k)
        lists_k = _collect_lists(sites_k, term_k)
        for lbl, xs_b, ys_b, xs_a, ys_a, seed_base in (
            ("Recoding vs terminal stops (CDS-deduplicated)", lists_k["rec_before"], lists_k["term_before"], lists_k["rec_after"], lists_k["term_after"], 80000),
            ("Recoding vs random internal (Control-C)", lists_k["rec_before"], lists_k["rand_before"], lists_k["rec_after"], lists_k["rand_after"], 90000),
        ):
            tb = _make_test(label=lbl, window="before", k=int(k), xs=xs_b, ys=ys_b, seed=seed_base + int(k))
            ta = _make_test(label=lbl, window="after", k=int(k), xs=xs_a, ys=ys_a, seed=seed_base + 100 + int(k))
            if tb is None or ta is None:
                continue
            mk_tests.append({"label": str(lbl), "k": int(k), "before": tb.__dict__, "after": ta.__dict__})

    # ---- Summary JSON (for caching + fast LaTeX rebuild) ----
    summary_obj: dict[str, object] = {
        "schema_version": 1,
        "analysis_version": int(ANALYSIS_VERSION),
        "mu_star": MU_STAR,
        "k_primary": int(k_primary),
        "k_list": [int(x) for x in k_list],
        "max_files": int(args.max_files or 0),
        "row_limit": int(ROW_LIMIT),
        "inputs": inputs_fp,
        "out_jsonl": str(out_jsonl),
        "primary": {
            "n_sites": int(len(sites)),
            "n_cds": int(n_cds),
            "aa_counts": {str(k): int(v) for k, v in sorted(aa_counts.items())},
            "codon_counts": {str(k): int(v) for k, v in sorted(codon_counts.items())},
            "domain_counts": {str(k): int(v) for k, v in sorted(domain_counts.items())},
            "term_stop_counts": {str(k): int(v) for k, v in sorted(term_stop_counts.items())},
            "tests_primary": [t.__dict__ for t in tests_primary],
            "top_rows": [s.__dict__ for s in top_sites],
        },
        "multi_k_overall": mk_tests,
    }
    out_summary_json.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_summary_json, summary_obj)
    write_json_atomic(cache_meta_path(out_summary_json), cache_meta)

    print("Wrote:", out_jsonl)
    print("Wrote:", out_summary_json)
    if not args.no_latex:
        _emit_latex_from_cached_summary(summary_obj)


def _write_recoding_rows_tex(top_sites: list[RecodingSite], *, row_limit: int) -> None:
    rows = []
    for s in top_sites[: int(row_limit)]:
        gene = s.gene or "-"
        before_s = f"{s.before_mean_delta:.3f}" if s.before_mean_delta is not None else "-"
        after_s = f"{s.after_mean_delta:.3f}" if s.after_mean_delta is not None else "-"
        rows.append(
            f"{gene} & \\path{{{s.version}}} & {s.aa} & {s.pos_start} & {s.codon_rna} & {s.n} & "
            f"\\texttt{{{s.w}}} & {s.v} & {s.delta} & {before_s} & {after_s} \\\\"
        )
    write_text(generated_dir() / "recoding_sites_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")


def _write_recoding_context_tests_tex(tests_primary: list[Any], *, k_primary: int) -> None:
    lines_primary: list[str] = []
    lines_primary.append(f"Recoding-site context tests (primary window radius $k={int(k_primary)}$).")
    for t in tests_primary:
        op_p, p_s = _fmt_p_tex(getattr(t, "p_welch", None))
        op_q, q_s = _fmt_p_tex(getattr(t, "q_welch", None))
        op_perm, perm_s = _fmt_p_tex(getattr(t, "p_perm", None))
        ci_low = getattr(t, "ci_low", None)
        ci_high = getattr(t, "ci_high", None)
        ci_s = "NA"
        if (ci_low is not None) and (ci_high is not None):
            ci_s = f"[{float(ci_low):.4f},{float(ci_high):.4f}]"
        d = getattr(t, "d", None)
        g = getattr(t, "g", None)
        d_s = f"{float(d):+.3f}" if d is not None else "NA"
        g_s = f"{float(g):+.3f}" if g is not None else "NA"
        lines_primary.append(
            f"{getattr(t, 'label', '-') } ({getattr(t, 'window', '-')}-window): "
            f"$\\bar{{\\Delta}}_1={float(getattr(t, 'mean1', float('nan'))):.4f}$ vs "
            f"$\\bar{{\\Delta}}_2={float(getattr(t, 'mean2', float('nan'))):.4f}$ "
            f"(diff {float(getattr(t, 'diff', float('nan'))):+.4f}, CI$_{{95\\%}}$={ci_s}, $d={d_s}$, $g={g_s}$, "
            f"Welch $p{op_p}{p_s}$, $q{op_q}{q_s}$, perm $p{op_perm}{perm_s}$; "
            f"$n={int(getattr(t, 'n1', 0) or 0)}$ vs {int(getattr(t, 'n2', 0) or 0)})."
        )
    write_text(generated_dir() / "recoding_context_tests.tex", "\n\n".join(lines_primary) + "\n")


def _emit_latex_from_cached_summary(summary: dict[str, object]) -> None:
    """
    Rebuild all LaTeX fragments from cached JSON summary (no GenBank parsing).
    """
    primary = summary.get("primary") or {}
    if not isinstance(primary, dict):
        raise SystemExit("Cached summary is missing primary section.")
    k_primary = int(summary.get("k_primary", 10) or 10)
    k_list = summary.get("k_list") or []
    if not isinstance(k_list, list):
        k_list = []
    row_limit = int(summary.get("row_limit", 200) or 200)

    top_rows = primary.get("top_rows") or []
    top_sites: list[RecodingSite] = []
    if isinstance(top_rows, list):
        for r in top_rows:
            if not isinstance(r, dict):
                continue
            try:
                top_sites.append(RecodingSite(**r))  # type: ignore[arg-type]
            except Exception:
                continue
    _write_recoding_rows_tex(top_sites, row_limit=row_limit)

    # Summary text.
    aa_counts = primary.get("aa_counts") or {}
    codon_counts = primary.get("codon_counts") or {}
    domain_counts = primary.get("domain_counts") or {}
    term_stop_counts = primary.get("term_stop_counts") or {}
    n_sites = int(primary.get("n_sites", 0) or 0)
    n_cds = int(primary.get("n_cds", 0) or 0)
    ks_i: list[int] = []
    for x in k_list:
        try:
            ks_i.append(int(x))
        except Exception:
            continue
    k_set_tex = ",".join(str(int(x)) for x in ks_i)
    summary_lines = []
    summary_lines.append(
        f"From GenBank records containing \\texttt{{transl\\_except}} qualifiers we extracted "
        f"$n={n_sites}$ recoding sites (primary window radius $k={k_primary}$"
        + (f"; multi-$k$ list $\\{{{k_set_tex}\\}}$" if isinstance(k_list, list) and len(k_list) > 1 else "")
        + "). "
        f"Counts by recoded amino acid: "
        + ", ".join(f"{aa}:{int(aa_counts[aa])}" for aa in sorted(aa_counts))
        + ". "
        f"Codon counts: " + ", ".join(f"{c}:{int(codon_counts[c])}" for c in sorted(codon_counts)) + "."
    )
    summary_lines.append(
        f"The LaTeX table lists the first {row_limit} sites; the full list is in "
        "\\path{data/recoding_genbank/recoding_sites.jsonl}."
    )
    summary_lines.append("Domain counts (from GenBank taxonomy lineages): " + ", ".join(f"{d}:{int(domain_counts[d])}" for d in sorted(domain_counts)) + ".")
    if isinstance(term_stop_counts, dict) and term_stop_counts:
        summary_lines.append(
            f"Terminal stop codons in the same CDS set (deduplicated by CDS; $n_\\mathrm{{CDS}}={n_cds}$): "
            + ", ".join(f"{c}:{int(term_stop_counts[c])}" for c in sorted(term_stop_counts))
            + "."
        )
    write_text(generated_dir() / "recoding_sites_summary.tex", "\n".join(summary_lines) + "\n")

    # Primary tests.
    tests_primary: list[object] = []
    tp = primary.get("tests_primary") or []
    if isinstance(tp, list):
        for d in tp:
            if not isinstance(d, dict):
                continue
            t_obj: object | None = None
            try:
                # Rehydrate minimal object-like wrapper.
                class _T:
                    pass

                t = _T()
                for k, v in d.items():
                    setattr(t, k, v)
                t_obj = t
            except Exception:
                t_obj = None
            if t_obj is not None:
                tests_primary.append(t_obj)
    _write_recoding_context_tests_tex(tests_primary, k_primary=k_primary)

    # Multi-k fragment: reuse the already-rendered per-k tests.
    mk_lines: list[str] = []
    mk_lines.append("Multi-$k$ sensitivity for recoding context tests (overall comparisons).")
    mk = summary.get("multi_k_overall") or []
    if isinstance(mk, list):
        for item in mk:
            if not isinstance(item, dict):
                pass
    else:
                lbl = str(item.get("label") or "-")
                kk = int(item.get("k", 0) or 0)
                b = item.get("before") or {}
                a = item.get("after") or {}
                if isinstance(b, dict) and isinstance(a, dict) and kk > 0:
                    op_p, p_s = _fmt_p_tex(b.get("p_welch"))
                    op_p2, p2_s = _fmt_p_tex(a.get("p_welch"))
                    mk_lines.append(
                        f"{lbl} ($k={kk}$): "
                        f"before diff {float(b.get('diff', float('nan'))):+.4f} (Welch $p{op_p}{p_s}$; "
                        f"$n={int(b.get('n1', 0) or 0)}$ vs {int(b.get('n2', 0) or 0)}), "
                        f"after diff {float(a.get('diff', float('nan'))):+.4f} (Welch $p{op_p2}{p2_s}$; "
                        f"$n={int(a.get('n1', 0) or 0)}$ vs {int(a.get('n2', 0) or 0)})."
                    )
    write_text(generated_dir() / "recoding_context_tests_multi_k.tex", "\n\n".join(mk_lines) + "\n")

    # Controls fragment (primary k).
    ctrl_lines: list[str] = []
    has_ctrl_b = any(str(getattr(t, "label", "")).startswith("Control-B") for t in tests_primary)
    if not has_ctrl_b:
        ctrl_lines.append(
            "Control-B (same CDS, same stop codon, excluding transl\\_except sites) could not be evaluated "
            "(insufficient internal same-codon occurrences with complete windows)."
        )
    for t in tests_primary:
        if not str(getattr(t, "label", "")).startswith("Control-"):
            continue
        op_p, p_s = _fmt_p_tex(getattr(t, "p_welch", None))
        op_q, q_s = _fmt_p_tex(getattr(t, "q_welch", None))
        op_perm, perm_s = _fmt_p_tex(getattr(t, "p_perm", None))
        ctrl_lines.append(
            f"{getattr(t, 'label', '-') } ({getattr(t, 'window', '-')}-window, $k={k_primary}$): "
            f"$\\bar{{\\Delta}}_\\mathrm{{rec}}={float(getattr(t, 'mean1', float('nan'))):.4f}$ vs "
            f"$\\bar{{\\Delta}}_\\mathrm{{ctrl}}={float(getattr(t, 'mean2', float('nan'))):.4f}$ "
            f"(diff {float(getattr(t, 'diff', float('nan'))):+.4f}, Welch $p{op_p}{p_s}$, $q{op_q}{q_s}$, "
            f"perm $p{op_perm}{perm_s}$; $n={int(getattr(t, 'n1', 0) or 0)}$ vs {int(getattr(t, 'n2', 0) or 0)})."
        )
    write_text(generated_dir() / "recoding_context_controls.tex", "\n\n".join(ctrl_lines) + "\n")

    # Dataset composition fragment.
    comp = []
    comp.append(
        f"Recoding dataset composition (GenBank \\texttt{{transl\\_except}}, primary window radius $k={k_primary}$): "
        f"sites $n={n_sites}$; codons " + ", ".join(f"{c}:{int(codon_counts[c])}" for c in sorted(codon_counts)) + "; "
        "domains " + ", ".join(f"{d}:{int(domain_counts[d])}" for d in sorted(domain_counts)) + "."
    )
    write_text(generated_dir() / "recoding_dataset_composition.tex", "\n".join(comp) + "\n")

    # Terminal-stop bias fragment: recompute vs current RefSeq baseline if available.
    term_stop_counts_i = Counter({str(k): int(v) for k, v in (term_stop_counts.items() if isinstance(term_stop_counts, dict) else [])})
    n_term = int(sum(term_stop_counts_i.values()))
    uaa_term = int(term_stop_counts_i.get("UAA", 0))
    uaa_rate = (uaa_term / float(n_term)) if n_term else float("nan")
    bias_lines: list[str] = []
    bias_lines.append(
        f"Terminal stop distribution in recoding CDS (deduplicated by CDS; $n_\\mathrm{{CDS}}={n_cds}$): "
        + ", ".join(f"{c}:{term_stop_counts_i[c]}" for c in sorted(term_stop_counts_i))
        + f". Boundary-stop rate (UAA) is {uaa_rate:.4f}."
    )
    refseq_path = root_dir() / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json"
    if refseq_path.exists():
        try:
            ref = json.loads(refseq_path.read_text(encoding="utf-8"))
            base_counts = ref.get("termination_stop_counts", {}) or {}
            n2 = int(sum(int(v) for v in base_counts.values()))
            x2 = int(base_counts.get("UAA", 0) or 0)
            if n_term > 0 and n2 > 0:
                p1 = uaa_term / float(n_term)
                p2 = x2 / float(n2)
                p_pool = (uaa_term + x2) / float(n_term + n2)
                se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / float(n_term) + 1.0 / float(n2))) if 0.0 < p_pool < 1.0 else 0.0
                z = (p1 - p2) / se if se > 0 else 0.0
                pz = normal_two_sided_p(z) if se > 0 else 1.0
                se_diff = math.sqrt(p1 * (1.0 - p1) / float(n_term) + p2 * (1.0 - p2) / float(n2)) if (n_term > 0 and n2 > 0) else 0.0
                ci_low = (p1 - p2) - 1.96 * se_diff
                ci_high = (p1 - p2) + 1.96 * se_diff
                bias_lines.append(
                    f"Compared to human RefSeq terminal stops (baseline $n={n2}$, UAA rate {p2:.4f}), "
                    f"recoding-CDS UAA rate {p1:.4f} differs by {p1 - p2:+.4f} "
                    f"(CI$_{{95\\%}}$=[{ci_low:.4f},{ci_high:.4f}], $z={z:.2f}$, $p={pz:.4g}$)."
                )
        except Exception:
            bias_lines.append("Human RefSeq baseline comparison was skipped (failed to read transcriptome_summary.json).")
    write_text(generated_dir() / "recoding_terminal_stop_bias.tex", "\n\n".join(bias_lines) + "\n")

    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


