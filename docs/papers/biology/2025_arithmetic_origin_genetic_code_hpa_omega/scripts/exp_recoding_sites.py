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
import json
import math
import random
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from genetic_code_tools import (
    BOUNDARY_WORDS,
    GENETIC_CODE,
    STOP_CODONS,
    fold_codon,
    student_t_cdf,
)


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


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


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


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
    p.add_argument("--max-files", type=int, default=0, help="Optional limit on number of gb files (0=all).")
    p.add_argument("--out-jsonl", default=str(data_dir() / "recoding_sites.jsonl"), help="Output JSONL path.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    k = int(args.k)
    if k < 1:
        raise SystemExit("--k must be >= 1")

    gb_files = sorted(genbank_dir().glob("*.gb"))
    if args.max_files:
        gb_files = gb_files[: int(args.max_files)]

    sites: list[RecodingSite] = []
    for fp in gb_files:
        text = fp.read_text(encoding="utf-8", errors="replace")
        sites.extend(extract_recoding_sites_from_record(text, k=k))

    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for s in sites:
            f.write(json.dumps(s.__dict__, ensure_ascii=False, sort_keys=True) + "\n")

    # Deduplicate CDS-level terminal-stop windows (one per CDS, not one per recoding site).
    cds_key = lambda s: (s.version, s.cds_location, s.translation_start)
    term_by_cds: dict[tuple[str, str, int], tuple[str | None, float | None, float | None, str | None]] = {}
    for s in sites:
        key = cds_key(s)
        if key not in term_by_cds:
            term_by_cds[key] = (s.terminal_stop, s.terminal_before_mean_delta, s.terminal_after_mean_delta, s.domain)

    # Summary statistics
    aa_counts = Counter(s.aa for s in sites)
    codon_counts = Counter(s.codon_rna for s in sites)
    term_stop_counts = Counter(stop for stop, _, _, _ in term_by_cds.values() if stop is not None)
    domain_counts = Counter((s.domain or "Unknown") for s in sites)
    n_cds = len(term_by_cds)

    # Context comparisons: recoding sites vs terminal stops (within this dataset).
    rec_before = [s.before_mean_delta for s in sites if s.before_mean_delta is not None]
    rec_after = [s.after_mean_delta for s in sites if s.after_mean_delta is not None]
    term_before = [b for _, b, _, _ in term_by_cds.values() if b is not None]
    term_after = [a for _, _, a, _ in term_by_cds.values() if a is not None]
    # Coerce to float lists
    rec_before_f = [float(x) for x in rec_before]
    rec_after_f = [float(x) for x in rec_after]
    term_before_f = [float(x) for x in term_before]
    term_after_f = [float(x) for x in term_after]

    p_before = welch_t_p_value_two_sided(rec_before_f, term_before_f)
    p_after = welch_t_p_value_two_sided(rec_after_f, term_after_f)

    # Control-B comparisons: recoding sites vs same-codon internal controls.
    ctrl_before = [s.control_same_codon_before_mean_delta for s in sites if s.control_same_codon_before_mean_delta is not None]
    ctrl_after = [s.control_same_codon_after_mean_delta for s in sites if s.control_same_codon_after_mean_delta is not None]
    ctrl_before_f = [float(x) for x in ctrl_before]
    ctrl_after_f = [float(x) for x in ctrl_after]
    p_ctrl_before = welch_t_p_value_two_sided(rec_before_f, ctrl_before_f) if ctrl_before_f else None
    p_ctrl_after = welch_t_p_value_two_sided(rec_after_f, ctrl_after_f) if ctrl_after_f else None

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

    perm_before = perm_p_value_two_sided(rec_before_f, ctrl_before_f, n_perm=2000, seed=12345) if ctrl_before_f else None
    perm_after = perm_p_value_two_sided(rec_after_f, ctrl_after_f, n_perm=2000, seed=23456) if ctrl_after_f else None
    perm_term_before = perm_p_value_two_sided(rec_before_f, term_before_f, n_perm=2000, seed=11111) if term_before_f else None
    perm_term_after = perm_p_value_two_sided(rec_after_f, term_after_f, n_perm=2000, seed=22222) if term_after_f else None

    # Control-C comparisons: recoding sites vs random internal coding controls (same CDS).
    rand_before = [s.control_random_cds_before_mean_delta for s in sites if s.control_random_cds_before_mean_delta is not None]
    rand_after = [s.control_random_cds_after_mean_delta for s in sites if s.control_random_cds_after_mean_delta is not None]
    rand_before_f = [float(x) for x in rand_before]
    rand_after_f = [float(x) for x in rand_after]
    p_rand_before = welch_t_p_value_two_sided(rec_before_f, rand_before_f) if rand_before_f else None
    p_rand_after = welch_t_p_value_two_sided(rec_after_f, rand_after_f) if rand_after_f else None
    perm_rand_before = perm_p_value_two_sided(rec_before_f, rand_before_f, n_perm=2000, seed=34567) if rand_before_f else None
    perm_rand_after = perm_p_value_two_sided(rec_after_f, rand_after_f, n_perm=2000, seed=45678) if rand_after_f else None

    # ---- LaTeX fragments ----
    # Keep PDF size bounded: emit only the first N rows in the LaTeX table.
    ROW_LIMIT = 200
    rows = []
    for s in sorted(sites, key=lambda x: (x.aa, x.version, x.pos_start))[:ROW_LIMIT]:
        gene = s.gene or "-"
        before_s = f"{s.before_mean_delta:.3f}" if s.before_mean_delta is not None else "-"
        after_s = f"{s.after_mean_delta:.3f}" if s.after_mean_delta is not None else "-"
        rows.append(
            f"{gene} & \\path{{{s.version}}} & {s.aa} & {s.pos_start} & {s.codon_rna} & {s.n} & "
            f"\\texttt{{{s.w}}} & {s.v} & {s.delta} & {before_s} & {after_s} \\\\"
        )
    write_text(generated_dir() / "recoding_sites_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")

    summary_lines = []
    summary_lines.append(
        f"From GenBank records containing \\texttt{{transl\\_except}} qualifiers we extracted "
        f"$n={len(sites)}$ recoding sites (window radius $k={k}$). "
        f"Counts by recoded amino acid: "
        + ", ".join(f"{aa}:{aa_counts[aa]}" for aa in sorted(aa_counts))
        + ". "
        f"Codon counts: " + ", ".join(f"{c}:{codon_counts[c]}" for c in sorted(codon_counts)) + "."
    )
    summary_lines.append(
        f"The LaTeX table lists the first {ROW_LIMIT} sites; the full list is in "
        "\\path{data/recoding_genbank/recoding_sites.jsonl}."
    )
    summary_lines.append(
        "Domain counts (from GenBank taxonomy lineages): " + ", ".join(f"{d}:{domain_counts[d]}" for d in sorted(domain_counts)) + "."
    )
    if term_stop_counts:
        summary_lines.append(
            f"Terminal stop codons in the same CDS set (deduplicated by CDS; $n_\\mathrm{{CDS}}={n_cds}$): "
            + ", ".join(f"{c}:{term_stop_counts[c]}" for c in sorted(term_stop_counts))
            + "."
        )
    write_text(generated_dir() / "recoding_sites_summary.tex", "\n".join(summary_lines) + "\n")

    def _summarize_pair(
        *,
        label: str,
        x_before: list[float],
        y_before: list[float],
        x_after: list[float],
        y_after: list[float],
        seed_base: int,
    ) -> str | None:
        if len(x_before) < 2 or len(y_before) < 2 or len(x_after) < 2 or len(y_after) < 2:
            return None
        xb = mean(x_before)
        yb = mean(y_before)
        xa = mean(x_after)
        ya = mean(y_after)
        pb = welch_t_p_value_two_sided(x_before, y_before)
        pa = welch_t_p_value_two_sided(x_after, y_after)
        permb = perm_p_value_two_sided(x_before, y_before, n_perm=2000, seed=seed_base + 1)
        perma = perm_p_value_two_sided(x_after, y_after, n_perm=2000, seed=seed_base + 2)
        db = cohen_d_equal_weight(x_before, y_before)
        da = cohen_d_equal_weight(x_after, y_after)
        if pb is None or pa is None:
            return None
        parts = []
        parts.append(f"{label} (window radius $k={k}$):")
        parts.append(
            f"before-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={xb:.4f}$ vs $\\bar{{\\Delta}}_\\mathrm{{ref}}={yb:.4f}$ "
            f"(difference {xb - yb:+.4f}"
            + (f", $d={db:+.3f}$" if db is not None else "")
            + f", Welch $p={pb:.4g}$"
            + (f", perm $p={permb:.4g}$" if permb is not None else "")
            + f"; n={len(x_before)} vs {len(y_before)}), "
            f"after-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={xa:.4f}$ vs $\\bar{{\\Delta}}_\\mathrm{{ref}}={ya:.4f}$ "
            f"(difference {xa - ya:+.4f}"
            + (f", $d={da:+.3f}$" if da is not None else "")
            + f", Welch $p={pa:.4g}$"
            + (f", perm $p={perma:.4g}$" if perma is not None else "")
            + f"; n={len(x_after)} vs {len(y_after)})."
        )
        return " ".join(parts)

    tests: list[str] = []

    overall = _summarize_pair(
        label="Recoding sites vs terminal stops (CDS-deduplicated)",
        x_before=rec_before_f,
        y_before=term_before_f,
        x_after=rec_after_f,
        y_after=term_after_f,
        seed_base=50000,
    )
    if overall is not None:
        tests.append(overall)
    else:
        tests.append(
            "Recoding vs terminal-stop tests were not run (insufficient complete windows after CDS deduplication)."
        )

    # By recoding codon (UGA/UAG/UAA).
    for codon in sorted(set(s.codon_rna for s in sites)):
        grp_sites = [s for s in sites if s.codon_rna == codon and (s.before_mean_delta is not None) and (s.after_mean_delta is not None)]
        if len(grp_sites) < 2:
            continue
        cds_keys = {cds_key(s) for s in grp_sites}
        term_b = [b for (st, b, _, _) in (term_by_cds[k0] for k0 in cds_keys if k0 in term_by_cds) if b is not None]
        term_a = [a for (st, _, a, _) in (term_by_cds[k0] for k0 in cds_keys if k0 in term_by_cds) if a is not None]
        line = _summarize_pair(
            label=f"By codon $\\mathrm{{{codon}}}$",
            x_before=[float(s.before_mean_delta) for s in grp_sites if s.before_mean_delta is not None],
            y_before=[float(x) for x in term_b],
            x_after=[float(s.after_mean_delta) for s in grp_sites if s.after_mean_delta is not None],
            y_after=[float(x) for x in term_a],
            seed_base=70000 + (abs(hash(codon)) % 10000),
        )
        if line is not None:
            tests.append(line)

    # By domain.
    for dom in sorted(set((s.domain or "Unknown") for s in sites)):
        grp_sites = [s for s in sites if (s.domain or "Unknown") == dom and (s.before_mean_delta is not None) and (s.after_mean_delta is not None)]
        if len(grp_sites) < 2:
            continue
        cds_keys = {cds_key(s) for s in grp_sites}
        term_b = [b for (st, b, _, _) in (term_by_cds[k0] for k0 in cds_keys if k0 in term_by_cds) if b is not None]
        term_a = [a for (st, _, a, _) in (term_by_cds[k0] for k0 in cds_keys if k0 in term_by_cds) if a is not None]
        line = _summarize_pair(
            label=f"By domain {dom}",
            x_before=[float(s.before_mean_delta) for s in grp_sites if s.before_mean_delta is not None],
            y_before=[float(x) for x in term_b],
            x_after=[float(s.after_mean_delta) for s in grp_sites if s.after_mean_delta is not None],
            y_after=[float(x) for x in term_a],
            seed_base=90000 + (abs(hash(dom)) % 10000),
        )
        if line is not None:
            tests.append(line)

    write_text(generated_dir() / "recoding_context_tests.tex", "\n\n".join(tests) + "\n")

    # New: Control-B summary fragment.
    ctrl_lines = []
    if ctrl_before_f and (p_ctrl_before is not None) and (p_ctrl_after is not None):
        ctrl_lines.append(
            "Control-B (same CDS, same stop codon, excluding transl\\_except sites): "
            f"$n_\\mathrm{{ctrl}}={len(ctrl_before_f)}$ windows. "
            f"Before-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={mean(rec_before_f):.4f}$ vs "
            f"$\\bar{{\\Delta}}_\\mathrm{{ctrl}}={mean(ctrl_before_f):.4f}$ "
            f"(difference {mean(rec_before_f)-mean(ctrl_before_f):+.4f}, Welch $p={p_ctrl_before:.4g}$"
            + (f", perm $p={perm_before:.4g}$" if perm_before is not None else "")
            + "). "
            f"After-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={mean(rec_after_f):.4f}$ vs "
            f"$\\bar{{\\Delta}}_\\mathrm{{ctrl}}={mean(ctrl_after_f):.4f}$ "
            f"(difference {mean(rec_after_f)-mean(ctrl_after_f):+.4f}, Welch $p={p_ctrl_after:.4g}$"
            + (f", perm $p={perm_after:.4g}$" if perm_after is not None else "")
            + ")."
        )
    else:
        ctrl_lines.append(
            "Control-B (same CDS, same stop codon, excluding transl\\_except sites) could not be evaluated "
            "(insufficient internal same-codon occurrences with complete windows)."
        )

    if rand_before_f and (p_rand_before is not None) and (p_rand_after is not None):
        ctrl_lines.append(
            "Control-C (same CDS, random internal coding positions; non-stop, excluding transl\\_except): "
            f"$n_\\mathrm{{rand}}={len(rand_before_f)}$ windows. "
            f"Before-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={mean(rec_before_f):.4f}$ vs "
            f"$\\bar{{\\Delta}}_\\mathrm{{rand}}={mean(rand_before_f):.4f}$ "
            f"(difference {mean(rec_before_f)-mean(rand_before_f):+.4f}, Welch $p={p_rand_before:.4g}$"
            + (f", perm $p={perm_rand_before:.4g}$" if perm_rand_before is not None else "")
            + "). "
            f"After-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={mean(rec_after_f):.4f}$ vs "
            f"$\\bar{{\\Delta}}_\\mathrm{{rand}}={mean(rand_after_f):.4f}$ "
            f"(difference {mean(rec_after_f)-mean(rand_after_f):+.4f}, Welch $p={p_rand_after:.4g}$"
            + (f", perm $p={perm_rand_after:.4g}$" if perm_rand_after is not None else "")
            + ")."
        )
    else:
        ctrl_lines.append(
            "Control-C (same CDS, random internal coding positions) could not be evaluated "
            "(insufficient eligible internal controls)."
        )
    write_text(generated_dir() / "recoding_context_controls.tex", "\n".join(ctrl_lines) + "\n")

    # New: dataset composition fragment (compact).
    comp = []
    comp.append(
        f"Recoding dataset composition (GenBank \\texttt{{transl\\_except}}, window radius $k={k}$): "
        f"sites $n={len(sites)}$; codons " + ", ".join(f"{c}:{codon_counts[c]}" for c in sorted(codon_counts)) + "; "
        "domains " + ", ".join(f"{d}:{domain_counts[d]}" for d in sorted(domain_counts)) + "."
    )
    write_text(generated_dir() / "recoding_dataset_composition.tex", "\n".join(comp) + "\n")

    print("Wrote:", out_jsonl)
    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


