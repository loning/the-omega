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
from composition_tools import bin_value, cpg_rate, dinuc_freq, gc_fraction, l1_distance_16, ta_rate
from genetic_code_tools import (
    BOUNDARY_WORDS,
    GENETIC_CODE,
    STOP_CODONS,
    fold_codon,
    student_t_cdf,
)
from progress_tools import Heartbeat
from stats_tools import bh_fdr, normal_two_sided_p, summarize_mean_diff


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 7
SCRIPT_VERSION = 2


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
        s = f"{p0:.2e}"
        mant, exp = s.split("e", 1)
        try:
            exp_i = int(exp)
        except Exception:
            exp_i = int(float(exp))
        return "=", f"{mant}\\times 10^{{{exp_i}}}"
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


def delta_after_mean_strand(
    seq_dna: str,
    center_pos_1: int,
    k: int,
    *,
    strand: int,
    left_bound_1: int,
    right_bound_1: int,
) -> float | None:
    """
    Mean Delta in k codons after a center codon at center_pos_1 (1-based, low coordinate),
    in the translated orientation of the strand.
    Returns None if the full after-window is not available/valid.
    """
    if strand not in (1, -1):
        raise ValueError("strand must be +1 or -1")
    if k <= 0:
        return None
    step = 3 * strand
    vals: list[float] = []
    for j in range(1, int(k) + 1):
        p = center_pos_1 + step * j
        if p < left_bound_1 or p + 2 > right_bound_1:
            return None
        c = codon_at_strand(seq_dna, p, strand=strand)
        if c is None:
            return None
        f = fold_codon(c.replace("T", "U"), MU_STAR)
        vals.append(float(f.delta))
    return mean(vals)


def codon_window_seq_strand(
    seq_dna: str,
    center_pos_1: int,
    k: int,
    *,
    strand: int,
    left_bound_1: int,
    right_bound_1: int,
    direction: str,
) -> str | None:
    """
    Extract the DNA sequence of k codons immediately before/after a codon starting at center_pos_1 (1-based, low coordinate),
    in the translated orientation of the strand.
    Returns a concatenated DNA string of length 3k, or None if the full window is not available/valid.
    """
    if strand not in (1, -1):
        raise ValueError("strand must be +1 or -1")
    if direction not in ("before", "after"):
        raise ValueError("direction must be 'before' or 'after'")
    if k <= 0:
        return None
    step = 3 * strand
    out: list[str] = []
    # Emit sequence in the translated 5'->3' orientation.
    js = range(1, int(k) + 1) if direction == "after" else range(int(k), 0, -1)
    for j in js:
        p = center_pos_1 + (step * j if direction == "after" else -step * j)
        if p < left_bound_1 or p + 2 > right_bound_1:
            return None
        c = codon_at_strand(seq_dna, p, strand=strand)
        if c is None:
            return None
        out.append(c)
    return "".join(out)


def _cds_strand(location: str) -> int:
    return -1 if location.strip().startswith("complement(") else 1


def _balanced_parens(s: str) -> bool:
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _unwrap_outer_call(s: str, fn: str) -> tuple[bool, str]:
    """
    If s is exactly of the form fn(...), unwrap one level and return (True, inner).
    Case-insensitive for fn.
    """
    t = s.strip()
    if not t:
        return False, s
    fn0 = fn.strip().lower()
    low = t.lower()
    prefix = fn0 + "("
    if low.startswith(prefix) and t.endswith(")"):
        inner = t[len(prefix) : -1]
        # Best-effort sanity: only unwrap when parentheses are balanced.
        if _balanced_parens(inner):
            return True, inner
    return False, s


def _split_top_level_commas(s: str) -> list[str]:
    """
    Split a string by commas that are not nested inside parentheses.
    """
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
            buf.append(ch)
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
            continue
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


@dataclass(frozen=True)
class ParsedCDSLocation:
    raw: str
    strand: int
    spans: list[tuple[int, int]]  # (start,end) 1-based inclusive, in location order

    @property
    def is_join(self) -> bool:
        return len(self.spans) > 1


_LOC_PAIR_ONE = re.compile(r"(\d+)\.\.(\d+)")
_LOC_SINGLE_ONE = re.compile(r"(\d+)")


def parse_cds_location(location: str) -> ParsedCDSLocation | None:
    """
    Parse GenBank CDS location into ordered spans + strand.

    Supported forms (common in practice):
      - 53..733
      - complement(53..733)
      - join(53..100,200..733)
      - complement(join(53..100,200..733))

    Coordinates are 1-based inclusive.
    """
    raw = str(location or "").strip()
    if not raw:
        return None

    # Remove whitespace to simplify parsing; keep raw for output.
    s = raw.replace(" ", "")

    strand = 1
    changed, inner = _unwrap_outer_call(s, "complement")
    while changed:
        strand *= -1
        s = inner
        changed, inner = _unwrap_outer_call(s, "complement")

    # Treat order(...) same as join(...) for our purposes.
    is_join = False
    changed, inner = _unwrap_outer_call(s, "join")
    if changed:
        is_join = True
        s = inner
    else:
        changed2, inner2 = _unwrap_outer_call(s, "order")
        if changed2:
            is_join = True
            s = inner2

    parts = _split_top_level_commas(s) if is_join else [s]
    spans: list[tuple[int, int]] = []
    for part0 in parts:
        part = part0.strip()
        if not part:
            continue
        # Disallow per-segment complement(...) in CDS: too rare and implies mixed orientation.
        if "complement(" in part.lower():
            return None
        part = part.replace("<", "").replace(">", "")
        m = _LOC_PAIR_ONE.search(part)
        if m:
            a = int(m.group(1))
            b = int(m.group(2))
            start, end = (a, b) if a <= b else (b, a)
            spans.append((start, end))
            continue
        m2 = _LOC_SINGLE_ONE.search(part)
        if m2:
            x = int(m2.group(1))
            spans.append((x, x))
            continue
        return None

    if not spans:
        return None
    return ParsedCDSLocation(raw=raw, strand=int(strand), spans=spans)


def build_spliced_cds(
    seq_dna: str,
    spans: list[tuple[int, int]],
    *,
    strand: int,
) -> tuple[str, list[int], dict[int, int]]:
    """
    Build translation-oriented spliced CDS sequence from genomic spans.
    Returns (cds_seq_dna, genomic_pos_by_i, genomic_to_i).
    """
    if strand not in (1, -1):
        raise ValueError("strand must be +1 or -1")
    n = len(seq_dna)

    bases: list[str] = []
    genomic_pos_by_i: list[int] = []

    if strand == 1:
        for a0, b0 in spans:
            a, b = (a0, b0) if a0 <= b0 else (b0, a0)
            if a < 1 or b > n:
                return "", [], {}
            for p in range(a, b + 1):
                bases.append(seq_dna[p - 1])
                genomic_pos_by_i.append(int(p))
    else:
        for a0, b0 in reversed(spans):
            a, b = (a0, b0) if a0 <= b0 else (b0, a0)
            if a < 1 or b > n:
                return "", [], {}
            for p in range(b, a - 1, -1):
                bases.append(seq_dna[p - 1].translate(_COMPLEMENT))
                genomic_pos_by_i.append(int(p))

    cds_seq = "".join(bases).upper()
    genomic_to_i: dict[int, int] = {}
    for i, p in enumerate(genomic_pos_by_i):
        # Keep the earliest mapping if duplicates appear (overlapping spans are malformed anyway).
        if p not in genomic_to_i:
            genomic_to_i[int(p)] = int(i)
    return cds_seq, genomic_pos_by_i, genomic_to_i


def delta_window_means_precomputed(
    delta_by_idx: dict[int, int],
    center_idx: int,
    k: int,
    *,
    translation_start_idx0: int,
    n_codons: int,
) -> tuple[float | None, float | None]:
    """
    Compute mean Delta in k codons before/after a center codon using precomputed deltas
    keyed by codon-start index in the spliced CDS sequence.
    Requires full windows within the translated region.
    """
    if k <= 0:
        return None, None
    if n_codons <= 0:
        return None, None
    if center_idx < translation_start_idx0:
        return None, None
    off = center_idx - translation_start_idx0
    if off % 3 != 0:
        return None, None
    i = off // 3
    if i < k or i + k >= n_codons:
        return None, None
    before: list[float] = []
    after: list[float] = []
    for j in range(1, k + 1):
        idx = translation_start_idx0 + 3 * (i - j)
        if idx not in delta_by_idx:
            return None, None
        before.append(float(delta_by_idx[idx]))
    for j in range(1, k + 1):
        idx = translation_start_idx0 + 3 * (i + j)
        if idx not in delta_by_idx:
            return None, None
        after.append(float(delta_by_idx[idx]))
    return mean(before), mean(after)


def delta_before_mean_precomputed(
    delta_by_idx: dict[int, int],
    center_idx: int,
    k: int,
    *,
    translation_start_idx0: int,
    n_codons: int,
) -> float | None:
    """
    Mean Delta in k codons before center codon (one-sided), using precomputed deltas.
    """
    if k <= 0 or n_codons <= 0:
        return None
    if center_idx < translation_start_idx0:
        return None
    off = center_idx - translation_start_idx0
    if off % 3 != 0:
        return None
    i = off // 3
    if i < k:
        return None
    vals: list[float] = []
    for j in range(1, int(k) + 1):
        idx = translation_start_idx0 + 3 * (i - j)
        if idx not in delta_by_idx:
            return None
        vals.append(float(delta_by_idx[idx]))
    return mean(vals)


def delta_after_mean_precomputed(
    delta_by_idx: dict[int, int],
    center_idx: int,
    k: int,
    *,
    translation_start_idx0: int,
    n_codons: int,
) -> float | None:
    """
    Mean Delta in k codons after center codon (one-sided), using precomputed deltas.
    """
    if k <= 0 or n_codons <= 0:
        return None
    if center_idx < translation_start_idx0:
        return None
    off = center_idx - translation_start_idx0
    if off % 3 != 0:
        return None
    i = off // 3
    if i + k >= n_codons:
        return None
    vals: list[float] = []
    for j in range(1, int(k) + 1):
        idx = translation_start_idx0 + 3 * (i + j)
        if idx not in delta_by_idx:
            return None
        vals.append(float(delta_by_idx[idx]))
    return mean(vals)


def codon_window_seq_spliced(
    cds_seq_dna: str,
    center_idx0: int,
    k: int,
    *,
    translation_start_idx0: int,
    n_codons: int,
    direction: str,
) -> str | None:
    """
    Extract the DNA sequence of k codons immediately before/after a codon at center_idx0 (0-based index into cds_seq_dna),
    in spliced CDS coordinates (already in translated 5'->3' orientation).
    Returns a concatenated DNA string of length 3k, or None if full window is not available.
    """
    if direction not in ("before", "after"):
        raise ValueError("direction must be 'before' or 'after'")
    if k <= 0:
        return None
    if n_codons <= 0:
        return None
    if center_idx0 < translation_start_idx0:
        return None
    off = center_idx0 - translation_start_idx0
    if off % 3 != 0:
        return None
    i = off // 3
    if direction == "before":
        if i < k:
            return None
    else:
        if i + k >= n_codons:
            return None
    # Emit sequence in translated 5'->3' order.
    out: list[str] = []
    if direction == "before":
        js = range(int(k), 0, -1)
        for j in js:
            idx = translation_start_idx0 + 3 * (i - j)
            if idx < 0 or idx + 3 > len(cds_seq_dna):
                return None
            out.append(cds_seq_dna[idx : idx + 3])
    else:
        for j in range(1, int(k) + 1):
            idx = translation_start_idx0 + 3 * (i + j)
            if idx < 0 or idx + 3 > len(cds_seq_dna):
                return None
            out.append(cds_seq_dna[idx : idx + 3])
    s = "".join(out).upper()
    if len(s) != 3 * int(k):
        return None
    if any(ch not in "ACGT" for ch in s):
        return None
    return s


def _dna_to_rna(s: str) -> str:
    return s.upper().replace("T", "U")


def downstream_seq_spliced(cds_seq_dna: str, center_idx0: int, n_nt: int) -> str | None:
    """
    Return the DNA sequence of n_nt immediately downstream of the codon at center_idx0
    (i.e., starting at center_idx0 + 3) in spliced CDS coordinates (translated orientation).
    Returns None if out of range or contains non-ACGT.
    """
    if n_nt <= 0:
        return None
    start = int(center_idx0) + 3
    end = start + int(n_nt)
    if start < 0 or end > len(cds_seq_dna):
        return None
    s = cds_seq_dna[start:end].upper()
    if len(s) != int(n_nt):
        return None
    if any(ch not in "ACGT" for ch in s):
        return None
    return s


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
    # Window sequences (DNA alphabet, translated orientation; k codons each side).
    before_seq_dna: str | None = None
    after_seq_dna: str | None = None
    # Terminal-stop window sequences for this CDS (if available).
    terminal_before_seq_dna: str | None = None
    terminal_after_seq_dna: str | None = None
    # Control window sequences (translated orientation; each entry is 3k nt).
    control_same_codon_before_seqs_dna: list[str] | None = None
    control_same_codon_after_seqs_dna: list[str] | None = None
    control_random_cds_before_seqs_dna: list[str] | None = None
    control_random_cds_after_seqs_dna: list[str] | None = None
    # Composition features of the before/after windows (DNA, translation orientation; k codons each).
    before_gc: float | None = None
    after_gc: float | None = None
    before_cpg: float | None = None
    after_cpg: float | None = None
    before_ta: float | None = None
    after_ta: float | None = None
    before_dinuc: dict[str, float] | None = None
    after_dinuc: dict[str, float] | None = None
    # Composition features for the terminal-stop windows of the same CDS (deduplicated downstream by CDS).
    terminal_before_gc: float | None = None
    terminal_after_gc: float | None = None
    terminal_before_cpg: float | None = None
    terminal_after_cpg: float | None = None
    terminal_before_ta: float | None = None
    terminal_after_ta: float | None = None
    terminal_before_dinuc: dict[str, float] | None = None
    terminal_after_dinuc: dict[str, float] | None = None
    # GC + dinucleotide nearest-neighbor matched controls (within-CDS Control-C pool).
    nn_ctrl_before_mean_delta: float | None = None
    nn_ctrl_after_mean_delta: float | None = None
    nn_before_diff: float | None = None
    nn_after_diff: float | None = None
    nn_before_l1: float | None = None
    nn_after_l1: float | None = None
    nn_before_gc_diff: float | None = None
    nn_after_gc_diff: float | None = None
    nn_before_gc_eps: float | None = None
    nn_after_gc_eps: float | None = None
    # Local downstream mechanism features (translated orientation, CDS-only).
    plus4_nt: str | None = None  # RNA alphabet (A/C/G/U), first nt after the recoding codon
    after_codon1: str | None = None  # next codon (RNA), length 3
    after_nt6: str | None = None  # next 6 nt (RNA), length 6
    analysis_version: int = ANALYSIS_VERSION


@dataclass
class StratBinCollector:
    """
    Stratified GC × (CpG or TA) bin collector for composition-adjusted comparisons.
    Stores per-bin uplift-window means (floats) for recoding vs control samples.
    """

    label: str
    x_name: str  # e.g. "cpg" or "ta"
    gc_edges: list[float]
    x_edges: list[float]
    rec_before: dict[str, list[float]]
    ctrl_before: dict[str, list[float]]
    rec_after: dict[str, list[float]]
    ctrl_after: dict[str, list[float]]

    def _key(self, gc: float | None, x: float | None) -> str | None:
        gb = bin_value(gc, edges=self.gc_edges)
        xb = bin_value(x, edges=self.x_edges)
        if gb is None or xb is None:
            return None
        return f"gc{int(gb)}_{self.x_name}{int(xb)}"

    def add(self, *, group: str, window: str, gc: float | None, x: float | None, value: float) -> None:
        k = self._key(gc, x)
        if k is None:
            return
        if group not in ("rec", "ctrl"):
            return
        if window not in ("before", "after"):
            return
        if group == "rec" and window == "before":
            self.rec_before.setdefault(k, []).append(float(value))
        elif group == "rec" and window == "after":
            self.rec_after.setdefault(k, []).append(float(value))
        elif group == "ctrl" and window == "before":
            self.ctrl_before.setdefault(k, []).append(float(value))
        elif group == "ctrl" and window == "after":
            self.ctrl_after.setdefault(k, []).append(float(value))

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


def extract_recoding_sites_from_record(
    record_text: str,
    *,
    k: int,
    heartbeat: Heartbeat | None = None,
    hb_tag: str = "",
    bin_collectors: list["StratBinCollector"] | None = None,
) -> list[RecodingSite]:
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
    if heartbeat is not None:
        heartbeat.maybe(f"{hb_tag}record={version} feats={len(feats)} k={int(k)}")
    for feat in feats:
        if heartbeat is not None:
            heartbeat.maybe(f"{hb_tag}record={version} k={int(k)} key={feat.key} sites={len(out)}")
        if feat.key != "CDS":
            continue
        if "transl_except" not in feat.qualifiers:
            continue

        ploc = parse_cds_location(feat.location)
        if ploc is None:
            continue
        strand = int(ploc.strand)
        cds_start = int(min(a for a, _ in ploc.spans))
        cds_end = int(max(b for _, b in ploc.spans))
        codon_start = 1
        if "codon_start" in feat.qualifiers and feat.qualifiers["codon_start"]:
            try:
                codon_start = int(feat.qualifiers["codon_start"][0] or "1")
            except ValueError:
                codon_start = 1
        codon_start = 1 if codon_start not in (1, 2, 3) else int(codon_start)

        cds_seq_dna, genomic_pos_by_i, genomic_to_i = build_spliced_cds(seq_dna, ploc.spans, strand=strand)
        if not cds_seq_dna:
            continue
        translation_start_idx0 = int(codon_start - 1)
        if translation_start_idx0 < 0 or translation_start_idx0 + 2 >= len(cds_seq_dna):
            continue
        # Count codons in translated region (including terminal stop when present).
        n_codons = (len(cds_seq_dna) - translation_start_idx0) // 3
        if n_codons <= 0:
            continue

        # For output: keep the legacy definition "low coordinate of the triplet" for the first translated codon.
        translation_start = int(min(genomic_pos_by_i[translation_start_idx0 : translation_start_idx0 + 3]))

        gene = feat.qualifiers.get("gene", [None])[0]
        product = feat.qualifiers.get("product", [None])[0]

        # Precompute codon-level folding for the translated region.
        codon_rna_by_idx: dict[int, str] = {}
        delta_by_idx: dict[int, int] = {}
        for i in range(int(n_codons)):
            idx0 = translation_start_idx0 + 3 * i
            if idx0 + 2 >= len(cds_seq_dna):
                break
            codon_dna = cds_seq_dna[idx0 : idx0 + 3]
            if any(ch not in "ACGT" for ch in codon_dna):
                continue
            codon_rna = codon_dna.replace("T", "U")
            if codon_rna not in GENETIC_CODE:
                continue
            f0 = fold_codon(codon_rna, MU_STAR)
            codon_rna_by_idx[int(idx0)] = codon_rna
            delta_by_idx[int(idx0)] = int(f0.delta)

        # Terminal stop (best-effort): last translated codon.
        term_stop: str | None = None
        term_before: float | None = None
        term_after: float | None = None
        term_before_seq: str | None = None
        term_after_seq: str | None = None
        term_before_gc: float | None = None
        term_after_gc: float | None = None
        term_before_cpg: float | None = None
        term_after_cpg: float | None = None
        term_before_ta: float | None = None
        term_after_ta: float | None = None
        term_before_dinuc: dict[str, float] | None = None
        term_after_dinuc: dict[str, float] | None = None
        last_idx0 = translation_start_idx0 + 3 * (int(n_codons) - 1)
        last_rna = codon_rna_by_idx.get(int(last_idx0))
        if last_rna in STOP_CODONS:
            term_stop = str(last_rna)
            # Before-window is always computed within the translated CDS when possible (independent of UTR availability).
            term_before = delta_before_mean_precomputed(
                delta_by_idx,
                int(last_idx0),
                int(k),
                translation_start_idx0=translation_start_idx0,
                n_codons=int(n_codons),
            )
            if term_before is not None:
                term_before_seq = codon_window_seq_spliced(
                    cds_seq_dna,
                    int(last_idx0),
                    int(k),
                    translation_start_idx0=translation_start_idx0,
                    n_codons=int(n_codons),
                    direction="before",
                )

            # After-window requires bases beyond the terminal stop codon. For spliced genomic CDS we do not
            # assume UTR is present in the record, so keep after as None.
            if not ploc.is_join:
                last_triplet = genomic_pos_by_i[int(last_idx0) : int(last_idx0) + 3]
                if len(last_triplet) == 3:
                    last_start_low = int(min(last_triplet))
                    term_after = delta_after_mean_strand(
                        seq_dna,
                        last_start_low,
                        int(k),
                        strand=strand,
                        left_bound_1=1,
                        right_bound_1=len(seq_dna),
                    )
                    if term_after is not None:
                        term_after_seq = codon_window_seq_strand(
                            seq_dna,
                            last_start_low,
                            int(k),
                            strand=strand,
                            left_bound_1=1,
                            right_bound_1=len(seq_dna),
                            direction="after",
                        )

        # Terminal stop composition (if sequences are available).
        if term_before_seq:
            term_before_gc = gc_fraction(term_before_seq)
            term_before_cpg = cpg_rate(term_before_seq)
            term_before_ta = ta_rate(term_before_seq)
            term_before_dinuc = dinuc_freq(term_before_seq)
        if term_after_seq:
            term_after_gc = gc_fraction(term_after_seq)
            term_after_cpg = cpg_rate(term_after_seq)
            term_after_ta = ta_rate(term_after_seq)
            term_after_dinuc = dinuc_freq(term_after_seq)

        # Resolve recoding site positions (spliced codon indices) first to exclude from controls.
        recoding_positions_idx: set[int] = set()
        recoding_entries: list[tuple[int, int, str, int]] = []  # (pos_start,pos_end,aa,idx0)
        for val in feat.qualifiers.get("transl_except", []):
            m = _TRANSL_EXCEPT_RE.search(val)
            if not m:
                continue
            pos_start = int(m.group("start"))
            pos_end = int(m.group("end"))
            aa_raw = str(m.group("aa"))
            aa_norm = aa_raw.strip()
            if aa_norm.lower() == "sec":
                aa_norm = "Sec"
            elif aa_norm.lower() == "pyl":
                aa_norm = "Pyl"
            if pos_end - pos_start != 2:
                continue
            # For minus-strand codons, the first translated base is at the high coordinate.
            anchor = pos_start if strand == 1 else pos_end
            idx0 = genomic_to_i.get(int(anchor))
            if idx0 is None:
                continue
            idx0_i = int(idx0)
            if idx0_i < translation_start_idx0 or (idx0_i - translation_start_idx0) % 3 != 0:
                continue
            if idx0_i + 2 >= len(cds_seq_dna):
                continue
            # Exclude all transl_except positions from internal controls, even if we don't
            # treat them as Sec/Pyl recoding sites for analysis.
            recoding_positions_idx.add(idx0_i)
            if aa_norm in ("Sec", "Pyl"):
                recoding_entries.append((int(pos_start), int(pos_end), aa_norm, idx0_i))

        # Control-C pool: random internal codon positions within CDS (exclude transl_except + stop codons),
        # with complete k-windows in both directions.
        M = 8
        eligible_random_controls: list[tuple[int, float, float]] = []
        for i in range(int(n_codons)):
            idx0 = translation_start_idx0 + 3 * i
            idx0_i = int(idx0)
            if idx0_i in recoding_positions_idx:
                continue
            r = codon_rna_by_idx.get(idx0_i)
            if r is None or r in STOP_CODONS:
                continue
            b, a = delta_window_means_precomputed(
                delta_by_idx,
                idx0_i,
                int(k),
                translation_start_idx0=translation_start_idx0,
                n_codons=int(n_codons),
            )
            if b is None or a is None:
                continue
            eligible_random_controls.append((idx0_i, float(b), float(a)))

        # NN candidates for within-CDS matching (subsample to control runtime; deterministic).
        NN_POOL_MAX = 2000
        nn_pool = list(eligible_random_controls)
        if len(nn_pool) > NN_POOL_MAX:
            rng_pool = random.Random(_stable_seed_u32(f"{version}:{translation_start}:{k}:nn_pool"))
            rng_pool.shuffle(nn_pool)
            nn_pool = nn_pool[:NN_POOL_MAX]

        # Precompute composition features for NN pool (before/after separately).
        nn_cand_before: list[dict[str, object]] = []
        nn_cand_after: list[dict[str, object]] = []
        for idx0_i, b, a in nn_pool:
            bseq = codon_window_seq_spliced(
                cds_seq_dna,
                int(idx0_i),
                int(k),
                translation_start_idx0=translation_start_idx0,
                n_codons=int(n_codons),
                direction="before",
            )
            aseq = codon_window_seq_spliced(
                cds_seq_dna,
                int(idx0_i),
                int(k),
                translation_start_idx0=translation_start_idx0,
                n_codons=int(n_codons),
                direction="after",
            )
            if bseq:
                nn_cand_before.append(
                    {
                        "idx0": int(idx0_i),
                        "mean": float(b),
                        "gc": gc_fraction(bseq),
                        "dinuc": dinuc_freq(bseq),
                    }
                )
            if aseq:
                nn_cand_after.append(
                    {
                        "idx0": int(idx0_i),
                        "mean": float(a),
                        "gc": gc_fraction(aseq),
                        "dinuc": dinuc_freq(aseq),
                    }
                )

        def _nn_match(
            *,
            target_gc: float | None,
            target_dinuc: dict[str, float] | None,
            candidates: list[dict[str, object]],
            eps_schedule: list[float],
        ) -> tuple[float | None, float | None, float | None, float | None]:
            """
            Return (matched_mean, l1, gc_diff, eps_used).
            """
            if target_gc is None or target_dinuc is None:
                return None, None, None, None
            best_mean: float | None = None
            best_l1: float | None = None
            best_gc_diff: float | None = None
            best_eps: float | None = None
            for eps in eps_schedule:
                for c in candidates:
                    gc0 = c.get("gc")
                    d0 = c.get("dinuc")
                    m0 = c.get("mean")
                    if gc0 is None or d0 is None or m0 is None: continue  # noqa: SIM103
                    if not isinstance(d0, dict): continue  # noqa: SIM103
                    try:
                        gc_f = float(gc0)
                        m_f = float(m0)
                    except Exception: continue  # noqa: BLE001
                    if abs(gc_f - float(target_gc)) > float(eps): continue  # noqa: SIM103
                    l1 = l1_distance_16(target_dinuc, d0)
                    if l1 is None: continue  # noqa: SIM103
                    gc_diff = abs(gc_f - float(target_gc))
                    if (
                        best_l1 is None
                        or float(l1) < float(best_l1)
                        or (float(l1) == float(best_l1) and gc_diff < float(best_gc_diff or 1e9))
                    ):
                        best_mean = float(m_f)
                        best_l1 = float(l1)
                        best_gc_diff = float(gc_diff)
                        best_eps = float(eps)
                if best_mean is not None:
                    break
            return best_mean, best_l1, best_gc_diff, best_eps

        # GC-eps schedule: try tight -> loose.
        GC_EPS_SCHEDULE = [0.05, 0.10, 0.20, 0.30]

        for pos_start, pos_end, aa, idx0_i in recoding_entries:
            codon_dna = cds_seq_dna[idx0_i : idx0_i + 3]
            if any(ch not in "ACGT" for ch in codon_dna):
                continue
            rna = codon_dna.replace("T", "U")
            if rna not in GENETIC_CODE:
                continue
            f = fold_codon(rna, MU_STAR)

            # Local downstream motif features (+4 and short downstream sequences).
            plus4_nt: str | None = None
            after_codon1: str | None = None
            after_nt6: str | None = None
            d3 = downstream_seq_spliced(cds_seq_dna, int(idx0_i), 3)
            if d3 is not None:
                after_codon1 = _dna_to_rna(d3)
                # +4 is the first base of the next codon.
                plus4_nt = after_codon1[0] if len(after_codon1) == 3 else None
            d6 = downstream_seq_spliced(cds_seq_dna, int(idx0_i), 6)
            if d6 is not None:
                after_nt6 = _dna_to_rna(d6)

            before_m, after_m = delta_window_means_precomputed(
                delta_by_idx,
                idx0_i,
                int(k),
                translation_start_idx0=translation_start_idx0,
                n_codons=int(n_codons),
            )

            # Composition features for recoding-site windows.
            before_seq = (
                codon_window_seq_spliced(
                    cds_seq_dna,
                    int(idx0_i),
                    int(k),
                    translation_start_idx0=translation_start_idx0,
                    n_codons=int(n_codons),
                    direction="before",
                )
                if before_m is not None
                else None
            )
            after_seq = (
                codon_window_seq_spliced(
                    cds_seq_dna,
                    int(idx0_i),
                    int(k),
                    translation_start_idx0=translation_start_idx0,
                    n_codons=int(n_codons),
                    direction="after",
                )
                if after_m is not None
                else None
            )
            before_gc = gc_fraction(before_seq) if before_seq else None
            after_gc = gc_fraction(after_seq) if after_seq else None
            before_cpg = cpg_rate(before_seq) if before_seq else None
            after_cpg = cpg_rate(after_seq) if after_seq else None
            before_ta = ta_rate(before_seq) if before_seq else None
            after_ta = ta_rate(after_seq) if after_seq else None
            before_dinuc = dinuc_freq(before_seq) if before_seq else None
            after_dinuc = dinuc_freq(after_seq) if after_seq else None

            # NN-matched controls from within-CDS random pool (Control-C), per window.
            nn_ctrl_before, nn_l1_b, nn_gc_diff_b, nn_eps_b = _nn_match(
                target_gc=before_gc,
                target_dinuc=before_dinuc,
                candidates=nn_cand_before,
                eps_schedule=GC_EPS_SCHEDULE,
            )
            nn_ctrl_after, nn_l1_a, nn_gc_diff_a, nn_eps_a = _nn_match(
                target_gc=after_gc,
                target_dinuc=after_dinuc,
                candidates=nn_cand_after,
                eps_schedule=GC_EPS_SCHEDULE,
            )
            nn_before_diff = (float(before_m) - float(nn_ctrl_before)) if (before_m is not None and nn_ctrl_before is not None) else None
            nn_after_diff = (float(after_m) - float(nn_ctrl_after)) if (after_m is not None and nn_ctrl_after is not None) else None

            # Control-B: same-codon positions inside CDS (exclude all transl_except sites).
            candidate_controls: list[int] = []
            for i in range(int(n_codons)):
                p = int(translation_start_idx0 + 3 * i)
                if p in recoding_positions_idx:
                    continue
                if codon_rna_by_idx.get(p) == rna:
                    candidate_controls.append(p)

            ctrl_before_mean: float | None = None
            ctrl_after_mean: float | None = None
            ctrl_before_seqs: list[str] = []
            ctrl_after_seqs: list[str] = []
            if candidate_controls:
                rng = random.Random(f"{version}:{pos_start}:{k}:same")
                rng.shuffle(candidate_controls)
                picks = candidate_controls[: int(M)]
                ctrl_before_vals: list[float] = []
                ctrl_after_vals: list[float] = []
                for p in picks:
                    b, a = delta_window_means_precomputed(
                        delta_by_idx,
                        int(p),
                        int(k),
                        translation_start_idx0=translation_start_idx0,
                        n_codons=int(n_codons),
                    )
                    if b is None or a is None:
                        continue
                    ctrl_before_vals.append(float(b))
                    ctrl_after_vals.append(float(a))
                    bseq = codon_window_seq_spliced(
                        cds_seq_dna,
                        int(p),
                        int(k),
                        translation_start_idx0=translation_start_idx0,
                        n_codons=int(n_codons),
                        direction="before",
                    )
                    aseq = codon_window_seq_spliced(
                        cds_seq_dna,
                        int(p),
                        int(k),
                        translation_start_idx0=translation_start_idx0,
                        n_codons=int(n_codons),
                        direction="after",
                    )
                    if bseq is not None and aseq is not None:
                        ctrl_before_seqs.append(str(bseq))
                        ctrl_after_seqs.append(str(aseq))
                if ctrl_before_vals and ctrl_after_vals:
                    ctrl_before_mean = mean(ctrl_before_vals)
                    ctrl_after_mean = mean(ctrl_after_vals)

            # Control-C: random internal coding controls from the same CDS.
            rand_before_mean: float | None = None
            rand_after_mean: float | None = None
            rand_before_seqs: list[str] = []
            rand_after_seqs: list[str] = []
            if eligible_random_controls:
                rng = random.Random(f"{version}:{pos_start}:{k}:rand")
                picks = list(eligible_random_controls)
                rng.shuffle(picks)
                picks = picks[: int(M)]
                rand_before_vals = [b for _, b, _ in picks]
                rand_after_vals = [a for _, _, a in picks]
                if rand_before_vals and rand_after_vals:
                    rand_before_mean = mean([float(x) for x in rand_before_vals])
                    rand_after_mean = mean([float(x) for x in rand_after_vals])
                for idx0_i2, _b0, _a0 in picks:
                    bseq = codon_window_seq_spliced(
                        cds_seq_dna,
                        int(idx0_i2),
                        int(k),
                        translation_start_idx0=translation_start_idx0,
                        n_codons=int(n_codons),
                        direction="before",
                    )
                    aseq = codon_window_seq_spliced(
                        cds_seq_dna,
                        int(idx0_i2),
                        int(k),
                        translation_start_idx0=translation_start_idx0,
                        n_codons=int(n_codons),
                        direction="after",
                    )
                    if bseq is not None and aseq is not None:
                        rand_before_seqs.append(str(bseq))
                        rand_after_seqs.append(str(aseq))

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
                    codon_dna=codon_dna,
                    codon_rna=rna,
                    plus4_nt=plus4_nt,
                    after_codon1=after_codon1,
                    after_nt6=after_nt6,
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
                    before_seq_dna=before_seq,
                    after_seq_dna=after_seq,
                    terminal_before_seq_dna=term_before_seq,
                    terminal_after_seq_dna=term_after_seq,
                    control_same_codon_before_seqs_dna=(ctrl_before_seqs if ctrl_before_seqs else None),
                    control_same_codon_after_seqs_dna=(ctrl_after_seqs if ctrl_after_seqs else None),
                    control_random_cds_before_seqs_dna=(rand_before_seqs if rand_before_seqs else None),
                    control_random_cds_after_seqs_dna=(rand_after_seqs if rand_after_seqs else None),
                    before_gc=before_gc,
                    after_gc=after_gc,
                    before_cpg=before_cpg,
                    after_cpg=after_cpg,
                    before_ta=before_ta,
                    after_ta=after_ta,
                    before_dinuc=before_dinuc,
                    after_dinuc=after_dinuc,
                    terminal_before_gc=term_before_gc,
                    terminal_after_gc=term_after_gc,
                    terminal_before_cpg=term_before_cpg,
                    terminal_after_cpg=term_after_cpg,
                    terminal_before_ta=term_before_ta,
                    terminal_after_ta=term_after_ta,
                    terminal_before_dinuc=term_before_dinuc,
                    terminal_after_dinuc=term_after_dinuc,
                    nn_ctrl_before_mean_delta=nn_ctrl_before,
                    nn_ctrl_after_mean_delta=nn_ctrl_after,
                    nn_before_diff=nn_before_diff,
                    nn_after_diff=nn_after_diff,
                    nn_before_l1=nn_l1_b,
                    nn_after_l1=nn_l1_a,
                    nn_before_gc_diff=nn_gc_diff_b,
                    nn_after_gc_diff=nn_gc_diff_a,
                    nn_before_gc_eps=nn_eps_b,
                    nn_after_gc_eps=nn_eps_a,
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
    p.add_argument(
        "--heartbeat-s",
        type=float,
        default=60.0,
        help="Emit a progress heartbeat at least once per this many seconds (0 disables).",
    )
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
        "script_version": int(SCRIPT_VERSION),
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
    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] recoding_sites")
    hb.force(f"start files={len(gb_files)} k_primary={int(k_primary)} k_list={','.join(str(int(x)) for x in k_list)}")
    site_counts: dict[int, int] = {int(k): 0 for k in k_list}
    for i, fp in enumerate(gb_files, start=1):
        text = fp.read_text(encoding="utf-8", errors="replace")
        for k in k_list:
            new_sites = extract_recoding_sites_from_record(
                text,
                k=int(k),
                heartbeat=hb,
                hb_tag=f"file={fp.name} ",
            )
            sites_by_k[int(k)].extend(new_sites)
            site_counts[int(k)] += int(len(new_sites))
        hb.maybe(
            f"files={i}/{len(gb_files)} last_file={fp.name} "
            f"sites_k{int(k_primary)}={int(site_counts.get(int(k_primary), 0))}"
        )
    hb.force(f"done files={len(gb_files)} sites_k{int(k_primary)}={int(site_counts.get(int(k_primary), 0))}")

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

    # Local downstream mechanism features (+4 base and short downstream motifs).
    plus4_counts = Counter((s.plus4_nt if s.plus4_nt is not None else "NA") for s in sites)
    plus4_by_aa: dict[str, Counter[str]] = {}
    plus4_by_domain: dict[str, Counter[str]] = {}
    after_codon1_by_aa: dict[str, Counter[str]] = {}
    after_nt6_by_aa: dict[str, Counter[str]] = {}
    for s in sites:
        aa = str(s.aa)
        dom = str(s.domain or "Unknown")
        plus4 = str(s.plus4_nt) if s.plus4_nt is not None else "NA"
        plus4_by_aa.setdefault(aa, Counter())[plus4] += 1
        plus4_by_domain.setdefault(dom, Counter())[plus4] += 1
        if s.after_codon1 is not None and ("N" not in str(s.after_codon1)):
            after_codon1_by_aa.setdefault(aa, Counter())[str(s.after_codon1)] += 1
        if s.after_nt6 is not None and ("N" not in str(s.after_nt6)):
            after_nt6_by_aa.setdefault(aa, Counter())[str(s.after_nt6)] += 1

    def _top_counter(c: Counter[str], *, k: int) -> list[dict[str, object]]:
        items = sorted(c.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))
        return [{"key": str(k0), "n": int(v0)} for k0, v0 in items[: int(k)]]

    after_codon1_top_by_aa = {aa: _top_counter(c, k=10) for aa, c in after_codon1_by_aa.items()}
    after_nt6_top_by_aa = {aa: _top_counter(c, k=10) for aa, c in after_nt6_by_aa.items()}

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

    def paired_t_p_value_two_sided(diffs: list[float]) -> float | None:
        """
        Paired t-test on paired differences (two-sided). Returns None if not enough samples.
        """
        n = len(diffs)
        if n < 2:
            return None
        m = mean([float(x) for x in diffs])
        v = sample_variance([float(x) for x in diffs])
        if v is None or v <= 0:
            return None
        se = math.sqrt(float(v) / float(n))
        if se <= 0:
            return None
        t = abs(float(m) / float(se))
        df_i = max(1, int(n - 1))
        p = 2.0 * (1.0 - student_t_cdf(t, df=df_i))
        return max(0.0, min(1.0, float(p)))

    def signflip_perm_p_value_two_sided(diffs: list[float], *, n_perm: int, seed: int) -> float | None:
        """
        Paired sign-flip permutation test for mean(diffs) == 0.
        """
        n = len(diffs)
        if n < 2:
            return None
        rng = random.Random(int(seed))
        xs = [float(x) for x in diffs]
        obs = abs(mean(xs))
        ge = 0
        for _ in range(int(n_perm)):
            s = 0.0
            for x in xs:
                s += (x if (rng.getrandbits(1) == 1) else -x)
            if abs(s / float(n)) >= obs:
                ge += 1
        return (ge + 1) / float(int(n_perm) + 1)

    def paired_summary(diffs: list[float], *, n_perm: int, seed: int) -> dict[str, object]:
        xs = [float(x) for x in diffs]
        n = len(xs)
        mu = mean(xs) if n > 0 else float("nan")
        v = sample_variance(xs)
        sd = math.sqrt(float(v)) if (v is not None and v > 0) else float("nan")
        se = (sd / math.sqrt(float(n))) if (n > 0 and sd == sd and sd > 0) else float("nan")
        ci_low = (mu - 1.96 * se) if (se == se) else None
        ci_high = (mu + 1.96 * se) if (se == se) else None
        d = (mu / sd) if (sd == sd and sd > 0) else None
        p_t = paired_t_p_value_two_sided(xs)
        p_perm = signflip_perm_p_value_two_sided(xs, n_perm=int(n_perm), seed=int(seed))
        return {
            "n": int(n),
            "mean_diff": float(mu) if mu == mu else None,
            "sd_diff": (float(sd) if sd == sd else None),
            "ci_low": (float(ci_low) if ci_low is not None else None),
            "ci_high": (float(ci_high) if ci_high is not None else None),
            "d": (float(d) if d is not None else None),
            "p_paired_t": (float(p_t) if p_t is not None else None),
            "p_signflip": (float(p_perm) if p_perm is not None else None),
        }

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

    # Candidate contexts for downstream experimental design: extreme uplift-context contrasts.
    CAND_LIMIT = 20

    def _diff_after_before(s: RecodingSite) -> float | None:
        if s.before_mean_delta is None or s.after_mean_delta is None:
            return None
        return float(s.after_mean_delta) - float(s.before_mean_delta)

    cand_by_aa: dict[str, dict[str, list[RecodingSite]]] = {}
    for aa0 in ("Sec", "Pyl"):
        aa_sites = [
            s
            for s in sites
            if (str(s.aa) == aa0)
            and (s.before_mean_delta is not None)
            and (s.after_mean_delta is not None)
            and (s.before_seq_dna is not None)
            and (s.after_seq_dna is not None)
        ]
        aa_sites.sort(key=lambda s: (-(float(_diff_after_before(s) or 0.0)), str(s.domain or ""), str(s.version), int(s.pos_start)))
        top_diff = aa_sites[: int(CAND_LIMIT)]
        aa_sites.sort(key=lambda s: ((float(_diff_after_before(s) or 0.0)), str(s.domain or ""), str(s.version), int(s.pos_start)))
        bottom_diff = aa_sites[: int(CAND_LIMIT)]
        cand_by_aa[str(aa0)] = {"top_diff": top_diff, "bottom_diff": bottom_diff}

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

    # By recoded amino acid (Sec/Pyl) (primary k)
    for aa in sorted(set(s.aa for s in sites)):
        grp_sites = [s for s in sites if s.aa == aa and (s.before_mean_delta is not None) and (s.after_mean_delta is not None)]
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
                        label=f"By recoded aa {aa} (recoding vs terminal)",
                        window="before",
                        k=k_primary,
                        xs=xs_b,
                        ys=[float(x) for x in term_b],
                        seed=85001 + _stable_seed_u32("recoding:by_aa:before:" + str(aa)),
                    ),
                    _make_test(
                        label=f"By recoded aa {aa} (recoding vs terminal)",
                        window="after",
                        k=k_primary,
                        xs=xs_a,
                        ys=[float(x) for x in term_a],
                        seed=85002 + _stable_seed_u32("recoding:by_aa:after:" + str(aa)),
                    ),
                )
                if t is not None
            ]
        )

    # By terminal stop codon in the same CDS (primary k)
    term_stop_set = sorted({stop for stop, _, _, _ in term_by_cds.values() if stop is not None})
    for tstop in term_stop_set:
        grp_sites = [
            s
            for s in sites
            if (s.terminal_stop == tstop) and (s.before_mean_delta is not None) and (s.after_mean_delta is not None)
        ]
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
                        label=f"By terminal stop $\\mathrm{{{tstop}}}$ (recoding vs terminal)",
                        window="before",
                        k=k_primary,
                        xs=xs_b,
                        ys=[float(x) for x in term_b],
                        seed=87001 + _stable_seed_u32("recoding:by_termstop:before:" + str(tstop)),
                    ),
                    _make_test(
                        label=f"By terminal stop $\\mathrm{{{tstop}}}$ (recoding vs terminal)",
                        window="after",
                        k=k_primary,
                        xs=xs_a,
                        ys=[float(x) for x in term_a],
                        seed=87002 + _stable_seed_u32("recoding:by_termstop:after:" + str(tstop)),
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

    # ---- Composition-adjusted controls (NN matching + stratified binning) ----
    def _quantile_edges(vals: list[float], qs: list[float]) -> list[float]:
        xs = sorted(float(x) for x in vals if x == x)
        if len(xs) < 5:
            return []
        out: list[float] = []
        n = len(xs)
        for q in qs:
            q0 = float(q)
            if q0 <= 0.0 or q0 >= 1.0:
                continue
            idx = int(math.floor(q0 * float(n - 1)))
            v = float(xs[max(0, min(n - 1, idx))])
            if out and v <= out[-1] + 1e-12:
                continue
            out.append(v)
        return out

    def _nn_match_global(
        *,
        target_gc: float | None,
        target_dinuc: dict[str, float] | None,
        candidates: list[dict[str, object]],
        eps_schedule: list[float],
    ) -> tuple[float | None, float | None, float | None, float | None]:
        if target_gc is None or target_dinuc is None:
            return None, None, None, None
        best_mean: float | None = None
        best_l1: float | None = None
        best_gc_diff: float | None = None
        best_eps: float | None = None
        for eps in eps_schedule:
            for c in candidates:
                gc0 = c.get("gc")
                d0 = c.get("dinuc")
                m0 = c.get("mean")
                if gc0 is None or d0 is None or m0 is None:
                    continue
                if not isinstance(d0, dict):
                    continue
                try:
                    gc_f = float(gc0)
                    m_f = float(m0)
                except Exception:
                    continue
                if abs(gc_f - float(target_gc)) > float(eps):
                    continue
                l1 = l1_distance_16(target_dinuc, d0)
                if l1 is None:
                    continue
                gc_diff = abs(gc_f - float(target_gc))
                if (
                    best_l1 is None
                    or float(l1) < float(best_l1)
                    or (float(l1) == float(best_l1) and gc_diff < float(best_gc_diff or 1e9))
                ):
                    best_mean = float(m_f)
                    best_l1 = float(l1)
                    best_gc_diff = float(gc_diff)
                    best_eps = float(eps)
            if best_mean is not None:
                break
        return best_mean, best_l1, best_gc_diff, best_eps

    def _stratified_perm(
        *,
        rec: list[tuple[float, float | None, float | None]],
        ctrl: list[tuple[float, float | None, float | None]],
        gc_edges: list[float],
        x_edges: list[float],
        x_name: str,
        n_perm: int,
        seed: int,
    ) -> dict[str, object]:
        # Bin values.
        bins: dict[str, dict[str, list[float]]] = {}
        for v, gc, x in rec:
            k0 = bin_value(gc, edges=gc_edges)
            x0 = bin_value(x, edges=x_edges)
            if k0 is None or x0 is None:
                continue
            key = f"gc{int(k0)}_{x_name}{int(x0)}"
            bins.setdefault(key, {"rec": [], "ctrl": []})["rec"].append(float(v))
        for v, gc, x in ctrl:
            k0 = bin_value(gc, edges=gc_edges)
            x0 = bin_value(x, edges=x_edges)
            if k0 is None or x0 is None:
                continue
            key = f"gc{int(k0)}_{x_name}{int(x0)}"
            bins.setdefault(key, {"rec": [], "ctrl": []})["ctrl"].append(float(v))

        rows: list[dict[str, object]] = []
        weighted_num = 0.0
        weighted_den = 0.0
        for key, d in sorted(bins.items()):
            xs = d.get("rec") or []
            ys = d.get("ctrl") or []
            if len(xs) < 1 or len(ys) < 1:
                continue
            mx = mean(xs)
            my = mean(ys)
            diff = float(mx - my)
            n1 = int(len(xs))
            n2 = int(len(ys))
            w = (float(n1) * float(n2)) / float(n1 + n2) if (n1 + n2) > 0 else 0.0
            weighted_num += w * diff
            weighted_den += w
            rows.append({"bin": key, "n_rec": n1, "n_ctrl": n2, "mean_rec": float(mx), "mean_ctrl": float(my), "diff": diff, "weight": w})

        obs = (weighted_num / weighted_den) if weighted_den > 0 else float("nan")
        p_perm: float | None = None
        if rows and weighted_den > 0 and n_perm > 0:
            rng = random.Random(int(seed))
            ge = 0
            obs_abs = abs(float(obs))
            # Pre-pack per-bin pools for speed.
            packed: list[tuple[int, list[float], float]] = []
            for r in rows:
                key = str(r["bin"])
                xs = list(bins[key]["rec"])
                ys = list(bins[key]["ctrl"])
                n1 = int(r["n_rec"])
                w = float(r["weight"])
                packed.append((n1, xs + ys, w))
            for _ in range(int(n_perm)):
                num = 0.0
                den = 0.0
                for n1, pool, w in packed:
                    if w <= 0:
                        continue
                    rng.shuffle(pool)
                    x1 = pool[:n1]
                    y1 = pool[n1:]
                    num += w * (mean(x1) - mean(y1))
                    den += w
                stat = (num / den) if den > 0 else 0.0
                if abs(float(stat)) >= obs_abs:
                    ge += 1
            p_perm = (ge + 1) / float(int(n_perm) + 1)

        return {"overall_diff": (float(obs) if obs == obs else None), "p_perm": p_perm, "bins": rows}

    # NN matched within-CDS (Control-C pool; per-site already computed).
    nn_before_diffs = [float(s.nn_before_diff) for s in sites if s.nn_before_diff is not None]
    nn_after_diffs = [float(s.nn_after_diff) for s in sites if s.nn_after_diff is not None]
    nn_within = {
        "before": paired_summary(nn_before_diffs, n_perm=2000, seed=60001),
        "after": paired_summary(nn_after_diffs, n_perm=2000, seed=60002),
        "n_with_before": int(len(nn_before_diffs)),
        "n_with_after": int(len(nn_after_diffs)),
        "mean_l1_before": (mean([float(s.nn_before_l1) for s in sites if s.nn_before_l1 is not None]) if any(s.nn_before_l1 is not None for s in sites) else None),
        "mean_l1_after": (mean([float(s.nn_after_l1) for s in sites if s.nn_after_l1 is not None]) if any(s.nn_after_l1 is not None for s in sites) else None),
    }

    # Terminal-stop composition pool (CDS-deduplicated).
    def build_term_comp_by_cds(
        sites_k: list[RecodingSite],
    ) -> dict[tuple[str, str, int], dict[str, object]]:
        out: dict[tuple[str, str, int], dict[str, object]] = {}
        for s0 in sites_k:
            key0 = cds_key(s0)
            if key0 in out:
                continue
            out[key0] = {
                "stop": s0.terminal_stop,
                "before_mean": s0.terminal_before_mean_delta,
                "after_mean": s0.terminal_after_mean_delta,
                "domain": s0.domain,
                "before_gc": s0.terminal_before_gc,
                "after_gc": s0.terminal_after_gc,
                "before_cpg": s0.terminal_before_cpg,
                "after_cpg": s0.terminal_after_cpg,
                "before_ta": s0.terminal_before_ta,
                "after_ta": s0.terminal_after_ta,
                "before_dinuc": s0.terminal_before_dinuc,
                "after_dinuc": s0.terminal_after_dinuc,
            }
        return out

    term_comp_by_cds = build_term_comp_by_cds(sites)
    term_pool_before: list[dict[str, object]] = []
    term_pool_after: list[dict[str, object]] = []
    for v in term_comp_by_cds.values():
        if v.get("before_mean") is not None and v.get("before_gc") is not None and v.get("before_dinuc") is not None:
            term_pool_before.append({"mean": float(v["before_mean"]), "gc": float(v["before_gc"]), "dinuc": v.get("before_dinuc")})
        if v.get("after_mean") is not None and v.get("after_gc") is not None and v.get("after_dinuc") is not None:
            term_pool_after.append({"mean": float(v["after_mean"]), "gc": float(v["after_gc"]), "dinuc": v.get("after_dinuc")})

    GC_EPS_SCHEDULE = [0.05, 0.10, 0.20, 0.30]
    nn_term_before_diffs: list[float] = []
    nn_term_after_diffs: list[float] = []
    for s in sites:
        if s.before_mean_delta is not None and s.before_gc is not None and s.before_dinuc is not None:
            m0, _l1, _gcd, _eps = _nn_match_global(
                target_gc=float(s.before_gc),
                target_dinuc=(s.before_dinuc if isinstance(s.before_dinuc, dict) else None),
                candidates=term_pool_before,
                eps_schedule=GC_EPS_SCHEDULE,
            )
            if m0 is not None:
                nn_term_before_diffs.append(float(s.before_mean_delta) - float(m0))
        if s.after_mean_delta is not None and s.after_gc is not None and s.after_dinuc is not None:
            m0, _l1, _gcd, _eps = _nn_match_global(
                target_gc=float(s.after_gc),
                target_dinuc=(s.after_dinuc if isinstance(s.after_dinuc, dict) else None),
                candidates=term_pool_after,
                eps_schedule=GC_EPS_SCHEDULE,
            )
            if m0 is not None:
                nn_term_after_diffs.append(float(s.after_mean_delta) - float(m0))

    nn_terminal = {
        "before": paired_summary(nn_term_before_diffs, n_perm=2000, seed=61001),
        "after": paired_summary(nn_term_after_diffs, n_perm=2000, seed=61002),
        "n_with_before": int(len(nn_term_before_diffs)),
        "n_with_after": int(len(nn_term_after_diffs)),
        "term_pool_before": int(len(term_pool_before)),
        "term_pool_after": int(len(term_pool_after)),
    }

    # Stratified GC × (CpG / TA) comparisons: recoding vs terminal stops.
    rec_before_comp = [(float(s.before_mean_delta), s.before_gc, s.before_cpg) for s in sites if (s.before_mean_delta is not None)]
    rec_after_comp = [(float(s.after_mean_delta), s.after_gc, s.after_cpg) for s in sites if (s.after_mean_delta is not None)]
    term_before_comp = [
        (float(v["before_mean"]), v.get("before_gc"), v.get("before_cpg"))
        for v in term_comp_by_cds.values()
        if v.get("before_mean") is not None
    ]
    term_after_comp = [
        (float(v["after_mean"]), v.get("after_gc"), v.get("after_cpg"))
        for v in term_comp_by_cds.values()
        if v.get("after_mean") is not None
    ]

    # Data-driven edges from pooled composition values.
    gc_vals = []
    cpg_vals = []
    ta_vals = []
    for s in sites:
        if s.before_gc is not None:
            gc_vals.append(float(s.before_gc))
        if s.after_gc is not None:
            gc_vals.append(float(s.after_gc))
        if s.before_cpg is not None:
            cpg_vals.append(float(s.before_cpg))
        if s.after_cpg is not None:
            cpg_vals.append(float(s.after_cpg))
        if s.before_ta is not None:
            ta_vals.append(float(s.before_ta))
        if s.after_ta is not None:
            ta_vals.append(float(s.after_ta))
    for v in term_comp_by_cds.values():
        for kx in ("before_gc", "after_gc"):
            if v.get(kx) is not None:
                gc_vals.append(float(v[kx]))
        for kx in ("before_cpg", "after_cpg"):
            if v.get(kx) is not None:
                cpg_vals.append(float(v[kx]))
        for kx in ("before_ta", "after_ta"):
            if v.get(kx) is not None:
                ta_vals.append(float(v[kx]))

    q_grid = [0.2, 0.4, 0.6, 0.8]
    gc_edges = _quantile_edges(gc_vals, q_grid)
    cpg_edges = _quantile_edges(cpg_vals, q_grid)
    ta_edges = _quantile_edges(ta_vals, q_grid)

    strat_gc_cpg = {
        "gc_edges": gc_edges,
        "x_edges": cpg_edges,
        "before": _stratified_perm(rec=rec_before_comp, ctrl=term_before_comp, gc_edges=gc_edges, x_edges=cpg_edges, x_name="cpg", n_perm=2000, seed=62001),
        "after": _stratified_perm(rec=rec_after_comp, ctrl=term_after_comp, gc_edges=gc_edges, x_edges=cpg_edges, x_name="cpg", n_perm=2000, seed=62002),
    }

    rec_before_ta = [(float(s.before_mean_delta), s.before_gc, s.before_ta) for s in sites if (s.before_mean_delta is not None)]
    rec_after_ta = [(float(s.after_mean_delta), s.after_gc, s.after_ta) for s in sites if (s.after_mean_delta is not None)]
    term_before_ta = [
        (float(v["before_mean"]), v.get("before_gc"), v.get("before_ta"))
        for v in term_comp_by_cds.values()
        if v.get("before_mean") is not None
    ]
    term_after_ta = [
        (float(v["after_mean"]), v.get("after_gc"), v.get("after_ta"))
        for v in term_comp_by_cds.values()
        if v.get("after_mean") is not None
    ]
    strat_gc_ta = {
        "gc_edges": gc_edges,
        "x_edges": ta_edges,
        "before": _stratified_perm(rec=rec_before_ta, ctrl=term_before_ta, gc_edges=gc_edges, x_edges=ta_edges, x_name="ta", n_perm=2000, seed=62101),
        "after": _stratified_perm(rec=rec_after_ta, ctrl=term_after_ta, gc_edges=gc_edges, x_edges=ta_edges, x_name="ta", n_perm=2000, seed=62102),
    }

    composition_controls = {
        "nn_within_cds": nn_within,
        "nn_terminal_pool": nn_terminal,
        "stratified_terminal": {"gc_cpg": strat_gc_cpg, "gc_ta": strat_gc_ta},
    }

    # ---- Summary JSON (for caching + fast LaTeX rebuild) ----
    summary_obj: dict[str, object] = {
        "schema_version": 2,
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
            "plus4_counts": {str(k): int(v) for k, v in sorted(plus4_counts.items())},
            "plus4_counts_by_aa": {str(a): {str(k): int(v) for k, v in sorted(c.items())} for a, c in sorted(plus4_by_aa.items())},
            "plus4_counts_by_domain": {str(d): {str(k): int(v) for k, v in sorted(c.items())} for d, c in sorted(plus4_by_domain.items())},
            "after_codon1_top_by_aa": {str(a): lst for a, lst in sorted(after_codon1_top_by_aa.items())},
            "after_nt6_top_by_aa": {str(a): lst for a, lst in sorted(after_nt6_top_by_aa.items())},
            "tests_primary": [t.__dict__ for t in tests_primary],
            "top_rows": [s.__dict__ for s in top_sites],
            "candidate_context_limit": int(CAND_LIMIT),
            "candidate_contexts": {
                str(aa0): {k0: [s.__dict__ for s in lst] for k0, lst in by_k.items()}
                for aa0, by_k in sorted(cand_by_aa.items())
            },
        },
        "multi_k_overall": mk_tests,
        "composition_controls": composition_controls,
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


def _write_recoding_candidate_contexts_tex(
    cand_by_aa: dict[str, dict[str, list[RecodingSite]]],
    *,
    k_primary: int,
    limit: int,
) -> None:
    """
    Emit a compact, self-contained LaTeX block listing candidate contexts for Sec/Pyl assays.
    The intent is experimental design: pick extreme predicted contrasts while keeping contexts explicit.
    """
    lim = int(limit) if int(limit) > 0 else 20

    lines: list[str] = []
    lines.append(f"Candidate recoding contexts (window radius $k={int(k_primary)}$), ranked by $\\overline{{U}}_{{\\mathrm{{after}}}}-\\overline{{U}}_{{\\mathrm{{before}}}}$.")

    # Build one table per amino acid, with top and bottom blocks.
    for aa in ("Sec", "Pyl"):
        by_dir = cand_by_aa.get(aa) or {}
        top = list(by_dir.get("top_diff") or [])[:lim]
        bot = list(by_dir.get("bottom_diff") or [])[:lim]
        if not top and not bot:
            continue

        lines.append("\\begin{center}")
        lines.append("\\scriptsize")
        lines.append("\\setlength{\\tabcolsep}{3pt}")
        lines.append("\\renewcommand{\\arraystretch}{1.10}")
        lines.append("\\resizebox{\\textwidth}{!}{%")
        lines.append("\\begin{tabular}{lllrlllrrrll}")
        lines.append("\\toprule")
        lines.append(
            "aa & rank & domain & pos & record & before seq & codon & $\\overline{U}_{\\mathrm{before}}$ & "
            "$\\overline{U}_{\\mathrm{after}}$ & diff & +4 & after-nt6 \\\\"
        )
        lines.append("\\midrule")

        def _row(s: RecodingSite, *, tag: str) -> str:
            b = float(s.before_mean_delta or 0.0)
            a = float(s.after_mean_delta or 0.0)
            diff = a - b
            rec = s.version or "-"
            dom = s.domain or "-"
            before_seq = s.before_seq_dna or "-"
            codon = s.codon_rna or "-"
            plus4 = s.plus4_nt or "-"
            after_nt6 = s.after_nt6 or "-"
            return (
                f"{aa} & {tag} & {dom} & {int(s.pos_start)} & \\path{{{rec}}} & "
                f"\\texttt{{{before_seq}}} & \\texttt{{{codon}}} & {b:.3f} & {a:.3f} & {diff:+.3f} & "
                f"\\texttt{{{plus4}}} & \\texttt{{{after_nt6}}} \\\\"
            )

        for s in top:
            lines.append(_row(s, tag="top"))
        if top and bot:
            lines.append("\\midrule")
        for s in bot:
            lines.append(_row(s, tag="bottom"))

        lines.append("\\bottomrule")
        lines.append("\\end{tabular}%")
        lines.append("}")
        lines.append("\\end{center}")

    write_text(generated_dir() / "recoding_candidate_contexts.tex", "\n\n".join(lines) + "\n")


def _write_recoding_context_tests_tex(tests_primary: list[Any], *, k_primary: int) -> None:
    lines_primary: list[str] = []
    lines_primary.append(f"Recoding-site context tests (primary window radius $k={int(k_primary)}$).")
    for t in tests_primary:
        # Keep this fragment as the headline comparison only.
        lbl = str(getattr(t, "label", "") or "")
        if lbl != "Recoding vs terminal stops (CDS-deduplicated)":
            continue
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


def _write_recoding_context_tests_stratified_tex(tests_primary: list[Any], *, k_primary: int) -> None:
    """
    Stratified recoding-vs-terminal comparisons (by codon / aa / domain / terminal stop).
    """
    lines: list[str] = []
    lines.append(f"Stratified recoding-site context tests (primary window radius $k={int(k_primary)}$).")
    for t in tests_primary:
        lbl = str(getattr(t, "label", "") or "")
        if not lbl.startswith("By "):
            continue
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
        lines.append(
            f"{lbl} ({getattr(t, 'window', '-')}-window): "
            f"$\\bar{{\\Delta}}_1={float(getattr(t, 'mean1', float('nan'))):.4f}$ vs "
            f"$\\bar{{\\Delta}}_2={float(getattr(t, 'mean2', float('nan'))):.4f}$ "
            f"(diff {float(getattr(t, 'diff', float('nan'))):+.4f}, CI$_{{95\\%}}$={ci_s}, $d={d_s}$, $g={g_s}$, "
            f"Welch $p{op_p}{p_s}$, $q{op_q}{q_s}$, perm $p{op_perm}{perm_s}$; "
            f"$n={int(getattr(t, 'n1', 0) or 0)}$ vs {int(getattr(t, 'n2', 0) or 0)})."
        )
    write_text(generated_dir() / "recoding_context_tests_stratified.tex", "\n\n".join(lines) + "\n")


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

    # Candidate contexts (stored in summary for reproducible rebuild without GenBank parsing).
    cand_ctx = primary.get("candidate_contexts") or {}
    cand_lim = int(primary.get("candidate_context_limit", 20) or 20)
    cand_by_aa: dict[str, dict[str, list[RecodingSite]]] = {}
    if isinstance(cand_ctx, dict):
        for aa, by_dir in cand_ctx.items():
            if not isinstance(by_dir, dict):
                continue
            out_dir: dict[str, list[RecodingSite]] = {}
            for key, rows in by_dir.items():
                if not isinstance(rows, list):
                    continue
                lst: list[RecodingSite] = []
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    try:
                        lst.append(RecodingSite(**r))  # type: ignore[arg-type]
                    except Exception:
                        continue
                out_dir[str(key)] = lst
            cand_by_aa[str(aa)] = out_dir
    _write_recoding_candidate_contexts_tex(cand_by_aa, k_primary=k_primary, limit=cand_lim)

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
    _write_recoding_context_tests_stratified_tex(tests_primary, k_primary=k_primary)

    # Multi-k fragment: reuse the already-rendered per-k tests.
    mk_lines: list[str] = []
    mk_lines.append("Multi-$k$ sensitivity for recoding context tests (overall comparisons).")
    mk = summary.get("multi_k_overall") or []
    if isinstance(mk, list):
        for item in mk:
            if not isinstance(item, dict):
                continue
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
    mech = primary.get("plus4_counts") if isinstance(primary, dict) else None
    if isinstance(mech, dict) and mech:
        # +4 base is the first RNA base after the recoding codon (translated orientation).
        parts = []
        for b in ("A", "C", "G", "U", "NA"):
            if b in mech:
                parts.append(f"\\texttt{{{b}}}:{int(mech[b])}")
        if parts:
            comp.append("Local +4 base (RNA, first nt after recoding codon): " + ", ".join(parts) + ".")

    mech_by_aa = primary.get("plus4_counts_by_aa") if isinstance(primary, dict) else None
    if isinstance(mech_by_aa, dict) and mech_by_aa:
        lines = []
        for aa, d in sorted(mech_by_aa.items(), key=lambda kv: str(kv[0])):
            if not isinstance(d, dict):
                continue
            parts = []
            for b in ("A", "C", "G", "U", "NA"):
                if b in d:
                    parts.append(f"\\texttt{{{b}}}:{int(d[b])}")
            if parts:
                lines.append(f"{aa}(" + ", ".join(parts) + ")")
        if lines:
            comp.append("Local +4 base by recoded aa: " + "; ".join(lines) + ".")

    mech_by_dom = primary.get("plus4_counts_by_domain") if isinstance(primary, dict) else None
    if isinstance(mech_by_dom, dict) and mech_by_dom:
        lines = []
        for dom, d in sorted(mech_by_dom.items(), key=lambda kv: str(kv[0])):
            if not isinstance(d, dict):
                continue
            parts = []
            for b in ("A", "C", "G", "U", "NA"):
                if b in d:
                    parts.append(f"\\texttt{{{b}}}:{int(d[b])}")
            if parts:
                lines.append(f"{dom}(" + ", ".join(parts) + ")")
        if lines:
            comp.append("Local +4 base by domain: " + "; ".join(lines) + ".")

    top_codon = primary.get("after_codon1_top_by_aa") if isinstance(primary, dict) else None
    if isinstance(top_codon, dict) and top_codon:
        for aa, lst in sorted(top_codon.items(), key=lambda kv: str(kv[0])):
            if not isinstance(lst, list) or not lst:
                continue
            items = []
            for it in lst[:10]:
                if not isinstance(it, dict):
                    continue
                k0 = it.get("key")
                n0 = it.get("n")
                if k0 is None or n0 is None:
                    continue
                try:
                    items.append(f"\\texttt{{{str(k0)}}}:{int(n0)}")
                except Exception:
                    continue
            if items:
                comp.append(f"Top downstream codon (+1) for {aa}: " + ", ".join(items) + ".")

    top_nt6 = primary.get("after_nt6_top_by_aa") if isinstance(primary, dict) else None
    if isinstance(top_nt6, dict) and top_nt6:
        for aa, lst in sorted(top_nt6.items(), key=lambda kv: str(kv[0])):
            if not isinstance(lst, list) or not lst:
                continue
            items = []
            for it in lst[:10]:
                if not isinstance(it, dict):
                    continue
                k0 = it.get("key")
                n0 = it.get("n")
                if k0 is None or n0 is None:
                    continue
                try:
                    items.append(f"\\texttt{{{str(k0)}}}:{int(n0)}")
                except Exception:
                    continue
            if items:
                comp.append(f"Top downstream 6-nt motifs (+1..+6) for {aa}: " + ", ".join(items) + ".")
    write_text(generated_dir() / "recoding_dataset_composition.tex", "\n".join(comp) + "\n")

    # Composition-adjusted controls fragment.
    cc = summary.get("composition_controls") or {}
    cc_lines: list[str] = []
    cc_lines.append(f"Composition-adjusted controls for recoding-site context (primary window radius $k={k_primary}$).")
    cc_lines.append("")
    cc_items: list[str] = []
    if isinstance(cc, dict) and cc:
        nnw = cc.get("nn_within_cds") or {}
        if isinstance(nnw, dict):
            b = nnw.get("before") or {}
            a = nnw.get("after") or {}
            if isinstance(b, dict):
                op, p_s = _fmt_p_tex(b.get("p_paired_t"))
                op2, p2_s = _fmt_p_tex(b.get("p_signflip"))
                md = b.get("mean_diff")
                lo = b.get("ci_low")
                hi = b.get("ci_high")
                md_s = f"{float(md):+.4f}" if md is not None else "NA"
                ci_s = f"[{float(lo):.4f},\\allowbreak {float(hi):.4f}]" if (lo is not None and hi is not None) else "NA"
                cc_items.append(
                    "Within-CDS GC+dinuc NN (Control-C), before-window: "
                    f"diff {md_s}; CI$_{{95\\%}}$={ci_s}; paired $p{op}{p_s}$; sign-flip $p{op2}{p2_s}$; $n={int(b.get('n') or 0)}$."
                )
            if isinstance(a, dict):
                op, p_s = _fmt_p_tex(a.get("p_paired_t"))
                op2, p2_s = _fmt_p_tex(a.get("p_signflip"))
                md = a.get("mean_diff")
                lo = a.get("ci_low")
                hi = a.get("ci_high")
                md_s = f"{float(md):+.4f}" if md is not None else "NA"
                ci_s = f"[{float(lo):.4f},\\allowbreak {float(hi):.4f}]" if (lo is not None and hi is not None) else "NA"
                cc_items.append(
                    "Within-CDS GC+dinuc NN (Control-C), after-window: "
                    f"diff {md_s}; CI$_{{95\\%}}$={ci_s}; paired $p{op}{p_s}$; sign-flip $p{op2}{p2_s}$; $n={int(a.get('n') or 0)}$."
                )
        nnt = cc.get("nn_terminal_pool") or {}
        if isinstance(nnt, dict):
            b = nnt.get("before") or {}
            a = nnt.get("after") or {}
            if isinstance(b, dict):
                op, p_s = _fmt_p_tex(b.get("p_paired_t"))
                op2, p2_s = _fmt_p_tex(b.get("p_signflip"))
                md = b.get("mean_diff")
                md_s = f"{float(md):+.4f}" if md is not None else "NA"
                cc_items.append(
                    "GC+dinuc NN to CDS-deduplicated terminal-stop pool, before-window: "
                    f"diff {md_s}; paired $p{op}{p_s}$; sign-flip $p{op2}{p2_s}$; $n={int(b.get('n') or 0)}$."
                )
            if isinstance(a, dict):
                op, p_s = _fmt_p_tex(a.get("p_paired_t"))
                op2, p2_s = _fmt_p_tex(a.get("p_signflip"))
                md = a.get("mean_diff")
                md_s = f"{float(md):+.4f}" if md is not None else "NA"
                cc_items.append(
                    "GC+dinuc NN to CDS-deduplicated terminal-stop pool, after-window: "
                    f"diff {md_s}; paired $p{op}{p_s}$; sign-flip $p{op2}{p2_s}$; $n={int(a.get('n') or 0)}$."
                )
        st = cc.get("stratified_terminal") or {}
        if isinstance(st, dict):
            for key, title in (("gc_cpg", "GC$\\times$CpG"), ("gc_ta", "GC$\\times$TA")):
                sch = st.get(key) or {}
                if not isinstance(sch, dict):
                    continue
                b = sch.get("before") or {}
                a = sch.get("after") or {}
                if isinstance(b, dict):
                    op, p_s = _fmt_p_tex(b.get("p_perm"))
                    od = b.get("overall_diff")
                    od_s = f"{float(od):+.4f}" if od is not None else "NA"
                    cc_items.append(f"Stratified ({title}) recoding vs terminal, before-window: overall diff {od_s}; perm $p{op}{p_s}$.")
                if isinstance(a, dict):
                    op, p_s = _fmt_p_tex(a.get("p_perm"))
                    od = a.get("overall_diff")
                    od_s = f"{float(od):+.4f}" if od is not None else "NA"
                    cc_items.append(f"Stratified ({title}) recoding vs terminal, after-window: overall diff {od_s}; perm $p{op}{p_s}$.")
    if cc_items:
        cc_lines.append("\\begin{itemize}")
        for it in cc_items:
            cc_lines.append("\\item " + it)
        cc_lines.append("\\end{itemize}")
    else:
        cc_lines.append("Composition-adjusted controls unavailable in cached summary.")
    write_text(generated_dir() / "recoding_composition_controls.tex", "\n".join(cc_lines) + "\n")

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
                op_p, p_s = _fmt_p_tex(float(pz))
                bias_lines.append(
                    f"Compared to human RefSeq terminal stops (baseline $n={n2}$, UAA rate {p2:.4f}), "
                    f"recoding-CDS UAA rate {p1:.4f} differs by {p1 - p2:+.4f} "
                    f"(CI$_{{95\\%}}$=[{ci_low:.4f},{ci_high:.4f}], $z={z:.2f}$, $p{op_p}{p_s}$)."
                )
        except Exception:
            bias_lines.append("Human RefSeq baseline comparison was skipped (failed to read transcriptome_summary.json).")
    write_text(generated_dir() / "recoding_terminal_stop_bias.tex", "\n\n".join(bias_lines) + "\n")

    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


