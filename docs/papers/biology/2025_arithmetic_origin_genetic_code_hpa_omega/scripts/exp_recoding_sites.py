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


def mean(xs: list[float]) -> float:
    return float(sum(xs)) / float(len(xs))


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

        loc = parse_simple_range(feat.location)
        if loc is None:
            continue
        cds_start, cds_end = loc
        codon_start = 1
        if "codon_start" in feat.qualifiers and feat.qualifiers["codon_start"]:
            try:
                codon_start = int(feat.qualifiers["codon_start"][0] or "1")
            except ValueError:
                codon_start = 1
        translation_start = cds_start + (codon_start - 1)

        gene = feat.qualifiers.get("gene", [None])[0]
        product = feat.qualifiers.get("product", [None])[0]

        # Terminal stop (best-effort): last codon inside CDS range.
        term_stop: str | None = None
        term_before: float | None = None
        term_after: float | None = None
        if (cds_end - translation_start + 1) >= 3:
            n_codons = (cds_end - translation_start + 1) // 3
            last_start = translation_start + 3 * (n_codons - 1)
            c_last = codon_at(seq_dna, last_start)
            if c_last is not None:
                r_last = c_last.replace("T", "U")
                if r_last in STOP_CODONS:
                    term_stop = r_last
                    term_before, term_after = delta_window_means(
                        seq_dna,
                        last_start,
                        k,
                        left_bound_1=translation_start,
                        right_bound_1=len(seq_dna),
                    )

        for val in feat.qualifiers.get("transl_except", []):
            m = _TRANSL_EXCEPT_RE.search(val)
            if not m:
                continue
            pos_start = int(m.group(1))
            pos_end = int(m.group(2))
            aa = m.group(3)
            if pos_end - pos_start != 2:
                continue
            dna = codon_at(seq_dna, pos_start)
            if dna is None:
                continue
            rna = dna.replace("T", "U")
            # Only keep sites that map to a defined codon; for Pyl/Sec we expect UAG/UGA.
            if rna not in GENETIC_CODE:
                continue
            f = fold_codon(rna, MU_STAR)

            before_m, after_m = delta_window_means(
                seq_dna,
                pos_start,
                k,
                left_bound_1=translation_start,
                right_bound_1=len(seq_dna),
            )

            out.append(
                RecodingSite(
                    version=version,
                    definition=definition,
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

    # Summary statistics
    aa_counts = Counter(s.aa for s in sites)
    codon_counts = Counter(s.codon_rna for s in sites)
    term_stop_counts = Counter(s.terminal_stop for s in sites if s.terminal_stop is not None)

    # Context comparisons: recoding sites vs terminal stops (within this dataset).
    rec_before = [s.before_mean_delta for s in sites if s.before_mean_delta is not None]
    rec_after = [s.after_mean_delta for s in sites if s.after_mean_delta is not None]
    term_before = [s.terminal_before_mean_delta for s in sites if s.terminal_before_mean_delta is not None]
    term_after = [s.terminal_after_mean_delta for s in sites if s.terminal_after_mean_delta is not None]
    # Coerce to float lists
    rec_before_f = [float(x) for x in rec_before]
    rec_after_f = [float(x) for x in rec_after]
    term_before_f = [float(x) for x in term_before]
    term_after_f = [float(x) for x in term_after]

    p_before = welch_t_p_value_two_sided(rec_before_f, term_before_f)
    p_after = welch_t_p_value_two_sided(rec_after_f, term_after_f)

    # ---- LaTeX fragments ----
    rows = []
    for s in sorted(sites, key=lambda x: (x.aa, x.version, x.pos_start)):
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
    if term_stop_counts:
        summary_lines.append(
            "Terminal stop codons in the same records: "
            + ", ".join(f"{c}:{term_stop_counts[c]}" for c in sorted(term_stop_counts))
            + "."
        )
    write_text(generated_dir() / "recoding_sites_summary.tex", "\n".join(summary_lines) + "\n")

    tests = []
    if rec_before_f and term_before_f and p_before is not None:
        rb = mean(rec_before_f)
        tb = mean(term_before_f)
        ra = mean(rec_after_f) if rec_after_f else float("nan")
        ta = mean(term_after_f) if term_after_f else float("nan")
        tests.append(
            "Welch tests (two-sided) comparing recoding-site vs terminal-stop window means "
            f"(window radius $k={k}$): "
            f"before-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={rb:.4f}$ vs $\\bar{{\\Delta}}_\\mathrm{{stop}}={tb:.4f}$ "
            f"(difference {rb - tb:+.4f}, $p={p_before:.4g}$; n={len(rec_before_f)} vs {len(term_before_f)}), "
            f"after-window $\\bar{{\\Delta}}_\\mathrm{{rec}}={ra:.4f}$ vs $\\bar{{\\Delta}}_\\mathrm{{stop}}={ta:.4f}$ "
            f"(difference {ra - ta:+.4f}, $p={p_after:.4g}$; n={len(rec_after_f)} vs {len(term_after_f)})."
        )
    else:
        tests.append(
            "Welch tests (two-sided) comparing recoding-site vs terminal-stop window means were not run "
            "(insufficient complete windows)."
        )
    write_text(generated_dir() / "recoding_context_tests.tex", "\n".join(tests) + "\n")

    print("Wrote:", out_jsonl)
    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


