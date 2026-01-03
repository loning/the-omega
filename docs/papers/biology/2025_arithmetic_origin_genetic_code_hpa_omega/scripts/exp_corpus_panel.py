# -*- coding: utf-8 -*-
"""
Cross-domain corpus panel scan for Fold_6 spectra.

This script reads panel definitions from data/manifest.json and produces:
  - a JSON summary (data/panel/...)
  - LaTeX fragments under sections/generated/

Modes:
  - refseq_mrna_best_orf: best ORF across frames per transcript (AUG start, UAA/UAG/UGA stops)
  - cds_fasta: in-frame CDS FASTA records; terminal stop is detected from the translation table (gc.prt)

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import BOUNDARY_WORDS, GENETIC_CODE, START_CODON, STOP_CODONS, fold_codon, iter_fasta
from progress_tools import Heartbeat
from stats_tools import (
    aa_preserving_null_decomposition,
    cohen_d_from_stats,
    hedges_g_from_stats,
    mean_diff_ci_normal_from_stats,
    normal_two_sided_p,
)


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
# Bump this when the analysis logic (not just speed) changes.
ANALYSIS_VERSION = 2


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def corpus_panel_item_cache_dir() -> Path:
    """
    Per-item cache for corpus panel scans.

    Rationale: panel-level cache invalidates when any item changes (including reuse digests),
    but we want to avoid rescanning unrelated corpora.
    """
    d = data_root() / "panel" / "_cache" / f"corpus_panel_items_v{int(ANALYSIS_VERSION)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _read_json_dict(path: Path) -> dict[str, object] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _refseq_transcriptome_summary_to_panel_summary(
    ref: dict[str, object],
    *,
    stop_codons: set[str],
    k_list: list[int],
) -> dict[str, object] | None:
    """
    Convert exp_refseq_transcriptome_merge.py output (transcriptome_summary.json)
    to the summary schema expected by scan_refseq_mrna_best_orf in this script.
    """
    # Basic required fields.
    try:
        records = int(ref.get("records", 0) or 0)
        records_with_orf = int(ref.get("records_with_orf", 0) or 0)
        coding_tokens = int(ref.get("coding_tokens", 0) or 0)
        boundary_token_count = int(ref.get("boundary_token_count", 0) or 0)
        boundary_rate = float(ref.get("boundary_rate", float("nan")))
    except Exception:
        return None

    term_counts_raw = ref.get("termination_stop_counts", {}) or {}
    term_counts: dict[str, int] = {}
    if isinstance(term_counts_raw, dict):
        for k, v in term_counts_raw.items():
            try:
                term_counts[str(k)] = int(v)
            except Exception:
                continue
    term_stop_boundary = int(ref.get("termination_stop_boundary_count", 0) or 0)
    stop_total = int(sum(term_counts.values()))
    term_stop_rates = {c: (float(term_counts.get(c, 0)) / float(stop_total) if stop_total else 0.0) for c in sorted(term_counts)}

    # Stop-context multi-k from Welford stats.
    w_mk = ref.get("stop_context_welford_multi_k")
    if not isinstance(w_mk, dict) or not w_mk:
        return None
    ks = sorted({int(x) for x in k_list if int(x) >= 1})
    stop_ctx: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for kk in ks:
        stop_ctx[str(int(kk))] = {}
        for codon in sorted(stop_codons):
            sm = w_mk.get(str(codon))
            if not isinstance(sm, dict):
                return None
            entry = sm.get(str(int(kk)))
            if not isinstance(entry, dict):
                return None
            b = entry.get("before", {}) or {}
            a = entry.get("after", {}) or {}
            if not isinstance(b, dict) or not isinstance(a, dict):
                return None
            try:
                n = int(b.get("n", 0) or 0)
            except Exception:
                n = 0
            bm = None
            am = None
            if n > 0:
                try:
                    bm = float(b.get("mean", float("nan")))
                except Exception:
                    bm = None
                try:
                    am = float(a.get("mean", float("nan")))
                except Exception:
                    am = None
            stop_ctx[str(int(kk))][str(codon)] = {"n": int(n), "before_mean": bm, "after_mean": am}

    codon_counts_raw = ref.get("codon_counts", {}) or {}
    aa_counts_raw = ref.get("aa_counts", {}) or {}
    v_hist_raw = ref.get("V_hist", {}) or {}
    d_hist_raw = ref.get("Delta_hist", {}) or {}

    codon_counts: dict[str, int] = {}
    if isinstance(codon_counts_raw, dict):
        for k, v in codon_counts_raw.items():
            try:
                codon_counts[str(k)] = int(v)
            except Exception:
                continue

    aa_counts: dict[str, int] = {}
    if isinstance(aa_counts_raw, dict):
        for k, v in aa_counts_raw.items():
            try:
                aa_counts[str(k)] = int(v)
            except Exception:
                continue

    v_hist: dict[str, int] = {}
    if isinstance(v_hist_raw, dict):
        for k, v in v_hist_raw.items():
            try:
                v_hist[str(k)] = int(v)
            except Exception:
                continue

    d_hist: dict[str, int] = {}
    if isinstance(d_hist_raw, dict):
        for k, v in d_hist_raw.items():
            try:
                d_hist[str(k)] = int(v)
            except Exception:
                continue

    zfp = ref.get("zspectrum_metrics", {}) or {}
    if not isinstance(zfp, dict):
        zfp = {}

    # Start-context multi-k from Welford stats (AUG).
    sc_mk = ref.get("start_context_welford_multi_k")
    if not isinstance(sc_mk, dict) or not sc_mk:
        return None
    start_ctx: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for kk in ks:
        entry = sc_mk.get(str(int(kk)))
        if not isinstance(entry, dict):
            return None
        b = entry.get("before", {}) or {}
        a = entry.get("after", {}) or {}
        if not isinstance(b, dict) or not isinstance(a, dict):
            return None
        nb = int(b.get("n", 0) or 0)
        na = int(a.get("n", 0) or 0)
        bm = None if nb <= 0 else float(b.get("mean", float("nan")))
        am = None if na <= 0 else float(a.get("mean", float("nan")))
        start_ctx[str(int(kk))] = {
            "before": {"n": int(nb), "mean": (None if bm is None or math.isnan(float(bm)) else float(bm))},
            "after": {"n": int(na), "mean": (None if am is None or math.isnan(float(am)) else float(am))},
        }

    # Stop-context effect sizes (from Welford stats; multi-k).
    stop_effects: dict[str, dict[str, dict[str, object]]] = {"before": {}, "after": {}}
    for kk in ks:
        stop_effects["before"][str(int(kk))] = {}
        stop_effects["after"][str(int(kk))] = {}
        for c1, c2 in _STOP_PAIRS:
            pair = f"{c1}_vs_{c2}"
            if c1 not in stop_codons or c2 not in stop_codons:
                stop_effects["before"][str(int(kk))][pair] = {
                    "n1": 0,
                    "n2": 0,
                    "mean1": None,
                    "mean2": None,
                    "diff": None,
                    "ci_low": None,
                    "ci_high": None,
                    "d": None,
                    "g": None,
                    "z": None,
                    "p": None,
                }
                stop_effects["after"][str(int(kk))][pair] = {
                    "n1": 0,
                    "n2": 0,
                    "mean1": None,
                    "mean2": None,
                    "diff": None,
                    "ci_low": None,
                    "ci_high": None,
                    "d": None,
                    "g": None,
                    "z": None,
                    "p": None,
                }
                continue

            sm1 = w_mk.get(c1)
            sm2 = w_mk.get(c2)
            if not isinstance(sm1, dict) or not isinstance(sm2, dict):
                return None
            e1 = sm1.get(str(int(kk)))
            e2 = sm2.get(str(int(kk)))
            if not isinstance(e1, dict) or not isinstance(e2, dict):
                return None
            b1 = e1.get("before", {}) or {}
            a1 = e1.get("after", {}) or {}
            b2 = e2.get("before", {}) or {}
            a2 = e2.get("after", {}) or {}
            if not isinstance(b1, dict) or not isinstance(a1, dict) or not isinstance(b2, dict) or not isinstance(a2, dict):
                return None
            rs_b1 = RunningStats(n=int(b1.get("n", 0) or 0), mean=float(b1.get("mean", 0.0) or 0.0), M2=float(b1.get("M2", 0.0) or 0.0))
            rs_b2 = RunningStats(n=int(b2.get("n", 0) or 0), mean=float(b2.get("mean", 0.0) or 0.0), M2=float(b2.get("M2", 0.0) or 0.0))
            rs_a1 = RunningStats(n=int(a1.get("n", 0) or 0), mean=float(a1.get("mean", 0.0) or 0.0), M2=float(a1.get("M2", 0.0) or 0.0))
            rs_a2 = RunningStats(n=int(a2.get("n", 0) or 0), mean=float(a2.get("mean", 0.0) or 0.0), M2=float(a2.get("M2", 0.0) or 0.0))
            stop_effects["before"][str(int(kk))][pair] = _mean_diff_effects_from_stats(rs_b1, rs_b2)
            stop_effects["after"][str(int(kk))][pair] = _mean_diff_effects_from_stats(rs_a1, rs_a2)

    return {
        "records": int(records),
        "records_with_orf": int(records_with_orf),
        "coding_tokens": int(coding_tokens),
        "boundary_token_count": int(boundary_token_count),
        "boundary_rate": float(boundary_rate),
        "termination_stop_counts": {k: int(v) for k, v in sorted(term_counts.items())},
        "termination_stop_boundary_count": int(term_stop_boundary),
        "termination_stop_rates": {k: float(v) for k, v in sorted(term_stop_rates.items())},
        "stop_context_multi_k": stop_ctx,
        "stop_context_effects_multi_k": stop_effects,
        "start_context_multi_k": start_ctx,
        "codon_counts": {k: int(v) for k, v in sorted(codon_counts.items())},
        "aa_counts": {k: int(v) for k, v in sorted(aa_counts.items())},
        "V_hist": {str(k): int(v) for k, v in sorted(v_hist.items())},
        "Delta_hist": {str(k): int(v) for k, v in sorted(d_hist.items())},
        "zspectrum_metrics": zfp,
    }


def _maybe_reuse_hsapiens_refseq_summary(
    *,
    m: dict[str, Any],
    present_files: list[Path],
    stop_codons: set[str],
    k_list: list[int],
) -> dict[str, object] | None:
    """
    If the human RefSeq transcriptome summary exists and matches the current
    panel configuration, reuse it instead of rescanning the FASTA shards.
    """
    ref_path = root_dir() / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json"
    ref = _read_json_dict(ref_path)
    if ref is None:
        return None
    mu = ref.get("mu_star")
    if mu is not None:
        if mu != MU_STAR:
            return None
    else:
        # Back-compat: older merged summaries may omit mu_star; validate via the cache meta sidecar.
        mp = cache_meta_path(ref_path)
        meta = _read_json_dict(mp) if mp.exists() else None
        if not isinstance(meta, dict):
            return None
        ck = meta.get("cache_key")
        if not isinstance(ck, dict):
            return None
        if ck.get("mu_star") != MU_STAR:
            return None

    # Require that the precomputed summary contains at least the k values requested by the panel.
    swl = ref.get("stop_window_list")
    if not isinstance(swl, list):
        return None
    try:
        have_ks = {int(x) for x in swl if int(x) >= 1}
    except Exception:
        return None
    want_ks = {int(x) for x in k_list if int(x) >= 1}
    if not want_ks.issubset(have_ks):
        return None

    # Ensure summary corresponds to exactly the currently present shard set (avoid accidental partial reuse).
    src = ref.get("source_files")
    if not isinstance(src, list):
        return None
    src_set = {str(x) for x in src if isinstance(x, str) and x}
    try:
        present_rel = {str(fp.relative_to(root_dir()).as_posix()) for fp in present_files}
    except Exception:
        present_rel = {str(fp) for fp in present_files}
    if src_set != present_rel:
        return None

    return _refseq_transcriptome_summary_to_panel_summary(ref, stop_codons=stop_codons, k_list=k_list)


def read_manifest() -> dict[str, Any]:
    mp = data_root() / "manifest.json"
    return json.loads(mp.read_text(encoding="utf-8"))


# Precompute fold attributes for all 64 codons under mu* (independent of translation tables).
FOLD_INFO: dict[str, dict[str, object]] = {}
for codon in GENETIC_CODE:
    f = fold_codon(codon, MU_STAR)
    FOLD_INFO[codon] = {
        "v": int(f.v),
        "delta": int(f.delta),
        "w": str(f.w),
        "is_boundary": int(str(f.w) in BOUNDARY_WORDS),
    }


@dataclass(frozen=True)
class BestOrf:
    frame: int
    start_base: int
    stop_base: int  # first base of stop codon
    length_codons_including_stop: int


def best_orf_across_frames(seq: str) -> BestOrf | None:
    """
    Best ORF across frames using AUG start and UAA/UAG/UGA stops.
    Matches exp_refseq_transcriptome logic (length, earliest start tie-breaker).
    """
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


@dataclass
class RunningStats:
    n: int = 0
    mean: float = 0.0
    M2: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        d2 = x - self.mean
        self.M2 += d * d2

    def sample_variance(self) -> float:
        if self.n <= 1:
            return 0.0
        return self.M2 / (self.n - 1)


_STOP_PAIRS: list[tuple[str, str]] = [
    ("UAA", "UAG"),
    ("UAA", "UGA"),
    ("UAG", "UGA"),
]


def _mean_diff_effects_from_stats(a: RunningStats, b: RunningStats) -> dict[str, object]:
    """
    Summarize mean difference and standardized effect sizes from Welford stats.

    Returns a JSON-serializable dict with keys:
      n1,n2,mean1,mean2,diff,ci_low,ci_high,d,g,z,p
    """
    n1 = int(a.n)
    n2 = int(b.n)
    if n1 <= 0 and n2 <= 0:
        return {
            "n1": 0,
            "n2": 0,
            "mean1": None,
            "mean2": None,
            "diff": None,
            "ci_low": None,
            "ci_high": None,
            "d": None,
            "g": None,
            "z": None,
            "p": None,
        }
    mean1 = float(a.mean) if n1 > 0 else None
    mean2 = float(b.mean) if n2 > 0 else None
    if n1 < 2 or n2 < 2 or mean1 is None or mean2 is None:
        return {
            "n1": n1,
            "n2": n2,
            "mean1": mean1,
            "mean2": mean2,
            "diff": None,
            "ci_low": None,
            "ci_high": None,
            "d": None,
            "g": None,
            "z": None,
            "p": None,
        }
    var1 = float(a.sample_variance())
    var2 = float(b.sample_variance())
    diff = float(mean1 - mean2)
    ci = mean_diff_ci_normal_from_stats(n1=n1, mean1=float(mean1), var1=var1, n2=n2, mean2=float(mean2), var2=var2)
    d = cohen_d_from_stats(n1=n1, mean1=float(mean1), var1=var1, n2=n2, mean2=float(mean2), var2=var2)
    g = hedges_g_from_stats(n1=n1, mean1=float(mean1), var1=var1, n2=n2, mean2=float(mean2), var2=var2)
    se2 = (var1 / float(n1)) + (var2 / float(n2))
    if se2 > 0:
        z = diff / math.sqrt(se2)
        p = normal_two_sided_p(z)
    else:
        z = None
        p = None
    return {
        "n1": n1,
        "n2": n2,
        "mean1": float(mean1),
        "mean2": float(mean2),
        "diff": diff,
        "ci_low": (float(ci[0]) if ci is not None else None),
        "ci_high": (float(ci[1]) if ci is not None else None),
        "d": (float(d) if d is not None else None),
        "g": (float(g) if g is not None else None),
        "z": (float(z) if z is not None else None),
        "p": (float(p) if p is not None else None),
    }


def _summarize_float_list(xs: list[float]) -> dict[str, float]:
    if not xs:
        return {"n": 0.0, "mean": float("nan"), "median": float("nan"), "p25": float("nan"), "p75": float("nan")}
    n = len(xs)
    mean = float(sum(xs)) / float(n)
    med = float(statistics.median(xs))
    if n == 1:
        p25 = med
        p75 = med
    else:
        qs = statistics.quantiles(xs, n=4, method="inclusive")
        p25 = float(qs[0])
        p75 = float(qs[2])
    return {"n": float(n), "mean": mean, "median": med, "p25": p25, "p75": p75, "min": float(min(xs)), "max": float(max(xs))}


AA1_TO_AA3 = {
    "A": "Ala",
    "C": "Cys",
    "D": "Asp",
    "E": "Glu",
    "F": "Phe",
    "G": "Gly",
    "H": "His",
    "I": "Ile",
    "K": "Lys",
    "L": "Leu",
    "M": "Met",
    "N": "Asn",
    "P": "Pro",
    "Q": "Gln",
    "R": "Arg",
    "S": "Ser",
    "T": "Thr",
    "V": "Val",
    "W": "Trp",
    "Y": "Tyr",
    "*": "Stop",
}


@dataclass(frozen=True)
class CodeTable:
    code_id: int
    ncbieaa: str
    base1: str
    base2: str
    base3: str


def _parse_gc_prt(text: str) -> list[CodeTable]:
    """
    Minimal gc.prt parser (enough to extract id/ncbieaa/base1/base2/base3).
    """
    lines = text.splitlines()
    depth = 0
    cur: dict[str, str] | None = None
    tables: list[CodeTable] = []

    def _quoted(s: str) -> str | None:
        m = None
        if '"' in s:
            try:
                m = s.split('"', 2)[1]
            except Exception:
                m = None
        return m

    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if s.startswith("Genetic-code-table") and s.endswith("{"):
            depth = 1
            continue
        if s.startswith("Genetic-code-table"):
            continue
        if s == "{":
            depth += 1
            if depth == 2:
                cur = {}
            continue
        if s.startswith("}"):
            s0 = s.replace(" ", "")
            if s0 not in ("}", "},"):
                continue
            if depth == 2 and cur is not None:
                try:
                    tables.append(
                        CodeTable(
                            code_id=int(cur["id"]),
                            ncbieaa=str(cur["ncbieaa"]),
                            base1=str(cur["base1"]),
                            base2=str(cur["base2"]),
                            base3=str(cur["base3"]),
                        )
                    )
                except Exception:
                    pass
                cur = None
            depth -= 1
            continue
        if cur is None or depth != 2:
            continue
        if s.startswith("id "):
            parts = s.replace(",", "").split()
            if len(parts) >= 2:
                cur["id"] = parts[1]
            continue
        if s.startswith("ncbieaa"):
            q = _quoted(s)
            if q is not None:
                cur["ncbieaa"] = q
            continue
        if s.startswith("-- Base1"):
            cur["base1"] = s.split(None, 2)[2].strip()
            continue
        if s.startswith("-- Base2"):
            cur["base2"] = s.split(None, 2)[2].strip()
            continue
        if s.startswith("-- Base3"):
            cur["base3"] = s.split(None, 2)[2].strip()
            continue

    out = []
    for t in tables:
        if len(t.ncbieaa) == 64 and len(t.base1) == 64 and len(t.base2) == 64 and len(t.base3) == 64:
            out.append(t)
    out.sort(key=lambda x: x.code_id)
    return out


def _codons_for_table(t: CodeTable) -> list[str]:
    out = []
    for i in range(64):
        dna = (t.base1[i] + t.base2[i] + t.base3[i]).upper()
        out.append(dna.replace("T", "U"))
    return out


def load_translation_tables() -> dict[int, tuple[dict[str, str], set[str]]]:
    """
    Return mapping: code_id -> (codon_to_aa3, stop_codons_set)
    """
    gc_path = data_root() / "gc.prt"
    if not gc_path.exists():
        # Fallback: standard code only.
        codon_to_aa3 = {c: str(GENETIC_CODE[c]) for c in GENETIC_CODE}
        return {1: (codon_to_aa3, set(STOP_CODONS)), 11: (codon_to_aa3, set(STOP_CODONS))}

    text = gc_path.read_text(encoding="utf-8", errors="replace")
    tables = _parse_gc_prt(text)
    out: dict[int, tuple[dict[str, str], set[str]]] = {}
    for t in tables:
        codons = _codons_for_table(t)
        codon_to_aa3: dict[str, str] = {}
        stops: set[str] = set()
        for i, codon in enumerate(codons):
            aa1 = t.ncbieaa[i]
            aa3 = AA1_TO_AA3.get(aa1, str(aa1))
            codon_to_aa3[codon] = aa3
            if aa3 == "Stop":
                stops.add(codon)
        out[int(t.code_id)] = (codon_to_aa3, stops)
    return out


def dataset_files_from_manifest(m: dict[str, Any], dataset_key: str) -> list[Path]:
    ds = (m.get("datasets") or {}).get(dataset_key)
    if not isinstance(ds, dict):
        raise SystemExit(f"Missing dataset in manifest: {dataset_key}")
    t = str(ds.get("type") or "")
    if t == "ncbi_refseq_dir":
        local_dir = root_dir() / str(ds["local_dir"])
        files = []
        for e in (ds.get("files", []) or []):
            if not isinstance(e, dict):
                continue
            name = e.get("name")
            if isinstance(name, str) and name:
                files.append(local_dir / name)
        if files:
            return files
        # Fallback: scan local dir for *.gz
        return sorted(local_dir.glob("*.gz"))
    if t == "ncbi_refseq_assembly_files":
        local_dir = root_dir() / str(ds["local_dir"])
        files = []
        for e in (ds.get("files", []) or []):
            if not isinstance(e, dict):
                continue
            name = e.get("name")
            if isinstance(name, str) and name:
                files.append(local_dir / name)
        if files:
            return files
        # Fallback: scan local dir for gz
        return sorted(local_dir.glob("*.gz"))
    # local-only small files
    lp = ds.get("local_path")
    if isinstance(lp, str):
        return [root_dir() / lp]
    return []


def codons_by_aa_from_map(codon_to_aa: dict[str, str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for codon, aa in codon_to_aa.items():
        out.setdefault(str(aa), []).append(str(codon))
    for aa in out:
        out[aa].sort()
    return out


def scan_refseq_mrna_best_orf(
    files: list[Path],
    *,
    k_list: list[int],
    codon_to_aa: dict[str, str],
    stop_codons: set[str],
    max_records: int = 0,
    heartbeat_s: float = 60.0,
    progress_label: str = "refseq_mrna_best_orf",
) -> dict[str, object]:
    # Aggregate stats over best ORF per transcript.
    n_records = 0
    n_with_orf = 0
    coding_tokens = 0
    boundary_token_count = 0

    term_stop_counts: Counter[str] = Counter()
    term_stop_boundary = 0

    codon_counts: Counter[str] = Counter()
    aa_counts: Counter[str] = Counter()

    v_hist: Counter[int] = Counter()
    delta_hist: Counter[int] = Counter()

    # fingerprint metrics over ORFs (excluding terminal stop)
    orf_boundary_rates: list[float] = []
    orf_entropy_z: list[float] = []
    orf_autocorr_z1: list[float] = []

    # stop-context stats per stop codon per k
    ks = sorted({int(k) for k in k_list if int(k) >= 1})
    before_stats_mk: dict[str, dict[int, RunningStats]] = {c: {k: RunningStats() for k in ks} for c in stop_codons}
    after_stats_mk: dict[str, dict[int, RunningStats]] = {c: {k: RunningStats() for k in ks} for c in stop_codons}
    max_k = max(ks) if ks else 0

    # start-context stats (AUG only in this mode), tracked independently for before/after windows.
    start_before_stats_mk: dict[int, RunningStats] = {k: RunningStats() for k in ks}
    start_after_stats_mk: dict[int, RunningStats] = {k: RunningStats() for k in ks}

    hb = Heartbeat(every_s=float(heartbeat_s), prefix=f"[progress] corpus_panel:{progress_label}")
    hb.force(f"start files={len(files)} max_records={int(max_records)}")

    for fp in files:
        for _rid, seq in iter_fasta(str(fp)):
            n_records += 1
            if max_records and n_records > int(max_records):
                break
            hb.maybe(f"file={fp.name} records={n_records} with_orf={n_with_orf} coding_tokens={coding_tokens}")
            best = best_orf_across_frames(seq)
            if best is None:
                continue
            s = best.start_base
            t = best.stop_base
            start_codon = seq[s : s + 3]
            stop_codon = seq[t : t + 3]
            if start_codon != START_CODON:
                continue
            if stop_codon not in stop_codons:
                continue
            n_with_orf += 1
            term_stop_counts[stop_codon] += 1
            if int(FOLD_INFO[stop_codon]["is_boundary"]) == 1:
                term_stop_boundary += 1

            # Coding token loop: start through last sense codon (exclude terminal stop codon).
            local_len = 0
            local_boundary = 0
            local_v_hist: Counter[int] = Counter()
            sum_v = 0.0
            sum_v2 = 0.0
            sum_vv1 = 0.0
            first_v: int | None = None
            last_v: int | None = None

            for pos in range(s, t, 3):
                codon = seq[pos : pos + 3]
                if codon not in GENETIC_CODE:
                    continue
                aa = codon_to_aa.get(codon)
                if aa is None:
                    continue
                if aa == "Stop":
                    continue
                info = FOLD_INFO[codon]
                v_i = int(info["v"])
                d_i = int(info["delta"])
                local_len += 1
                local_v_hist[v_i] += 1
                sum_v += float(v_i)
                sum_v2 += float(v_i * v_i)
                if first_v is None:
                    first_v = v_i
                if last_v is not None:
                    sum_vv1 += float(last_v * v_i)
                last_v = v_i

                codon_counts[codon] += 1
                aa_counts[str(aa)] += 1
                v_hist[v_i] += 1
                delta_hist[d_i] += 1
                if int(info["is_boundary"]) == 1:
                    local_boundary += 1
                    boundary_token_count += 1
                coding_tokens += 1

            if local_len > 0:
                orf_boundary_rates.append(local_boundary / float(local_len))
                # entropy of V
                h = 0.0
                for c in local_v_hist.values():
                    p = float(c) / float(local_len)
                    if p > 0:
                        h -= p * math.log2(p)
                orf_entropy_z.append(h)
                # lag-1 autocorrelation of V
                if local_len >= 3 and first_v is not None and last_v is not None:
                    n_pairs = local_len - 1
                    sum_x = sum_v - float(last_v)
                    sum_y = sum_v - float(first_v)
                    sum_x2 = sum_v2 - float(last_v * last_v)
                    sum_y2 = sum_v2 - float(first_v * first_v)
                    mx = sum_x / float(n_pairs)
                    my = sum_y / float(n_pairs)
                    cov = (sum_vv1 / float(n_pairs)) - (mx * my)
                    var_x = (sum_x2 / float(n_pairs)) - (mx * mx)
                    var_y = (sum_y2 / float(n_pairs)) - (my * my)
                    if var_x > 0 and var_y > 0:
                        orf_autocorr_z1.append(cov / math.sqrt(var_x * var_y))

            # Start-context windows around start codon (AUG) in the selected frame.
            # Before-window: in-frame codons upstream of AUG (typically 5' UTR in mRNA).
            # After-window: in-frame codons downstream of AUG inside the ORF (excluding terminal stop).
            if max_k >= 1:
                start_after_vals: list[int] = []
                for j in range(1, max_k + 1):
                    p = s + 3 * j
                    if p >= t:
                        break
                    if p + 3 > len(seq):
                        break
                    c = seq[p : p + 3]
                    if c not in GENETIC_CODE:
                        break
                    start_after_vals.append(int(FOLD_INFO[c]["delta"]))

                start_before_vals: list[int] = []
                for j in range(1, max_k + 1):
                    p = s - 3 * j
                    if p < 0:
                        break
                    c = seq[p : p + 3]
                    if c not in GENETIC_CODE:
                        break
                    start_before_vals.append(int(FOLD_INFO[c]["delta"]))

                for k in ks:
                    if k <= len(start_before_vals):
                        start_before_stats_mk[k].update(float(sum(start_before_vals[:k])) / float(k))
                    if k <= len(start_after_vals):
                        start_after_stats_mk[k].update(float(sum(start_after_vals[:k])) / float(k))

            # Stop-context windows around terminal stop.
            stop_index = (t - s) // 3
            if stop_index >= 1 and max_k >= 1:
                # after-window values in transcript
                after_vals: list[int] = []
                for j in range(1, max_k + 1):
                    p = t + 3 * j
                    if p + 3 > len(seq):
                        break
                    c = seq[p : p + 3]
                    if c not in GENETIC_CODE:
                        break
                    after_vals.append(int(FOLD_INFO[c]["delta"]))
                # before-window values inside ORF
                before_vals: list[int] = []
                j_max_before = min(int(stop_index), int(max_k))
                for j in range(1, j_max_before + 1):
                    p = t - 3 * j
                    c = seq[p : p + 3]
                    if c not in GENETIC_CODE:
                        break
                    before_vals.append(int(FOLD_INFO[c]["delta"]))

                for k in ks:
                    if k <= len(before_vals) and k <= len(after_vals):
                        before_stats_mk[stop_codon][k].update(float(sum(before_vals[:k])) / float(k))
                        after_stats_mk[stop_codon][k].update(float(sum(after_vals[:k])) / float(k))

        if max_records and n_records > int(max_records):
            break

    hb.force(f"done records={n_records} with_orf={n_with_orf} coding_tokens={coding_tokens}")
    boundary_rate = boundary_token_count / float(coding_tokens) if coding_tokens > 0 else float("nan")
    stop_total = int(sum(term_stop_counts.values()))
    term_stop_rates = {c: (float(term_stop_counts.get(c, 0)) / float(stop_total) if stop_total else 0.0) for c in sorted(term_stop_counts)}

    stop_ctx: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for k in ks:
        stop_ctx[str(k)] = {}
        for codon in sorted(stop_codons):
            bs = before_stats_mk[codon][k]
            a_s = after_stats_mk[codon][k]
            stop_ctx[str(k)][codon] = {
                "n": int(bs.n),
                "before_mean": (float(bs.mean) if bs.n > 0 else None),
                "after_mean": (float(a_s.mean) if a_s.n > 0 else None),
            }

    start_ctx: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for k in ks:
        b = start_before_stats_mk[k]
        a = start_after_stats_mk[k]
        start_ctx[str(k)] = {
            "before": {"n": int(b.n), "mean": (float(b.mean) if b.n > 0 else None)},
            "after": {"n": int(a.n), "mean": (float(a.mean) if a.n > 0 else None)},
        }

    stop_effects: dict[str, dict[str, dict[str, object]]] = {"before": {}, "after": {}}
    for k in ks:
        stop_effects["before"][str(k)] = {}
        stop_effects["after"][str(k)] = {}
        for c1, c2 in _STOP_PAIRS:
            pair = f"{c1}_vs_{c2}"
            if c1 not in stop_codons or c2 not in stop_codons:
                stop_effects["before"][str(k)][pair] = {
                    "n1": 0,
                    "n2": 0,
                    "mean1": None,
                    "mean2": None,
                    "diff": None,
                    "ci_low": None,
                    "ci_high": None,
                    "d": None,
                    "g": None,
                    "z": None,
                    "p": None,
                }
                stop_effects["after"][str(k)][pair] = {
                    "n1": 0,
                    "n2": 0,
                    "mean1": None,
                    "mean2": None,
                    "diff": None,
                    "ci_low": None,
                    "ci_high": None,
                    "d": None,
                    "g": None,
                    "z": None,
                    "p": None,
                }
                continue
            stop_effects["before"][str(k)][pair] = _mean_diff_effects_from_stats(before_stats_mk[c1][k], before_stats_mk[c2][k])
            stop_effects["after"][str(k)][pair] = _mean_diff_effects_from_stats(after_stats_mk[c1][k], after_stats_mk[c2][k])

    return {
        "records": int(n_records),
        "records_with_orf": int(n_with_orf),
        "coding_tokens": int(coding_tokens),
        "boundary_token_count": int(boundary_token_count),
        "boundary_rate": float(boundary_rate),
        "termination_stop_counts": {k: int(v) for k, v in sorted(term_stop_counts.items())},
        "termination_stop_boundary_count": int(term_stop_boundary),
        "termination_stop_rates": {k: float(v) for k, v in sorted(term_stop_rates.items())},
        "stop_context_multi_k": stop_ctx,
        "stop_context_effects_multi_k": stop_effects,
        "start_context_multi_k": start_ctx,
        "codon_counts": {k: int(v) for k, v in sorted(codon_counts.items())},
        "aa_counts": {k: int(v) for k, v in sorted(aa_counts.items())},
        "V_hist": {str(k): int(v) for k, v in sorted(v_hist.items())},
        "Delta_hist": {str(k): int(v) for k, v in sorted(delta_hist.items())},
        "zspectrum_metrics": {
            "boundary_rate": _summarize_float_list(orf_boundary_rates),
            "entropy_Z": _summarize_float_list(orf_entropy_z),
            "autocorr_Z1": _summarize_float_list(orf_autocorr_z1),
        },
    }


def scan_cds_fasta(
    files: list[Path],
    *,
    k_list: list[int],
    codon_to_aa: dict[str, str],
    stop_codons: set[str],
    max_records: int = 0,
    heartbeat_s: float = 60.0,
    progress_label: str = "cds_fasta",
) -> dict[str, object]:
    n_records = 0
    n_used = 0
    n_invalid = 0
    n_no_terminal_stop = 0
    n_internal_stop = 0

    coding_tokens = 0
    boundary_token_count = 0
    term_stop_counts: Counter[str] = Counter()
    term_stop_boundary = 0

    codon_counts: Counter[str] = Counter()
    aa_counts: Counter[str] = Counter()
    v_hist: Counter[int] = Counter()
    delta_hist: Counter[int] = Counter()

    # fingerprint metrics over CDS (excluding terminal stop)
    seg_boundary_rates: list[float] = []
    seg_entropy_z: list[float] = []
    seg_autocorr_z1: list[float] = []

    ks = sorted({int(k) for k in k_list if int(k) >= 1})
    before_stats_mk: dict[str, dict[int, RunningStats]] = {c: {k: RunningStats() for k in ks} for c in stop_codons}

    # Start-context stats at the first codon in each CDS record.
    # For CDS FASTA records the upstream sequence is not available, so only after windows are evaluated.
    start_after_stats_mk: dict[int, RunningStats] = {k: RunningStats() for k in ks}

    hb = Heartbeat(every_s=float(heartbeat_s), prefix=f"[progress] corpus_panel:{progress_label}")
    hb.force(f"start files={len(files)} max_records={int(max_records)}")

    for fp in files:
        for _rid, seq in iter_fasta(str(fp)):
            n_records += 1
            if max_records and n_records > int(max_records):
                break
            hb.maybe(
                f"file={fp.name} records={n_records} used={n_used} invalid={n_invalid} "
                f"no_terminal_stop={n_no_terminal_stop} internal_stop={n_internal_stop}"
            )

            # In-frame codons from base 0.
            L = (len(seq) // 3) * 3
            if L < 6:
                n_invalid += 1
                continue
            codons = [seq[i : i + 3] for i in range(0, L, 3)]
            if any(c not in GENETIC_CODE for c in codons):
                n_invalid += 1
                continue

            terminal = codons[-1]
            if terminal not in stop_codons:
                n_no_terminal_stop += 1
                continue
            if any(c in stop_codons for c in codons[:-1]):
                n_internal_stop += 1
                continue

            n_used += 1
            term_stop_counts[terminal] += 1
            if int(FOLD_INFO[terminal]["is_boundary"]) == 1:
                term_stop_boundary += 1

            # Coding tokens: exclude terminal stop.
            local_len = 0
            local_boundary = 0
            local_v_hist: Counter[int] = Counter()
            sum_v = 0.0
            sum_v2 = 0.0
            sum_vv1 = 0.0
            first_v: int | None = None
            last_v: int | None = None

            for codon in codons[:-1]:
                aa = codon_to_aa.get(codon)
                if aa is None:
                    continue
                if aa == "Stop":
                    # should not happen after internal-stop check
                    continue
                info = FOLD_INFO[codon]
                v_i = int(info["v"])
                d_i = int(info["delta"])
                local_len += 1
                local_v_hist[v_i] += 1
                sum_v += float(v_i)
                sum_v2 += float(v_i * v_i)
                if first_v is None:
                    first_v = v_i
                if last_v is not None:
                    sum_vv1 += float(last_v * v_i)
                last_v = v_i

                codon_counts[codon] += 1
                aa_counts[str(aa)] += 1
                v_hist[v_i] += 1
                delta_hist[d_i] += 1
                if int(info["is_boundary"]) == 1:
                    local_boundary += 1
                    boundary_token_count += 1
                coding_tokens += 1

            if local_len > 0:
                seg_boundary_rates.append(local_boundary / float(local_len))
                h = 0.0
                for c in local_v_hist.values():
                    p = float(c) / float(local_len)
                    if p > 0:
                        h -= p * math.log2(p)
                seg_entropy_z.append(h)
                if local_len >= 3 and first_v is not None and last_v is not None:
                    n_pairs = local_len - 1
                    sum_x = sum_v - float(last_v)
                    sum_y = sum_v - float(first_v)
                    sum_x2 = sum_v2 - float(last_v * last_v)
                    sum_y2 = sum_v2 - float(first_v * first_v)
                    mx = sum_x / float(n_pairs)
                    my = sum_y / float(n_pairs)
                    cov = (sum_vv1 / float(n_pairs)) - (mx * my)
                    var_x = (sum_x2 / float(n_pairs)) - (mx * mx)
                    var_y = (sum_y2 / float(n_pairs)) - (my * my)
                    if var_x > 0 and var_y > 0:
                        seg_autocorr_z1.append(cov / math.sqrt(var_x * var_y))

            # Stop-context before-window only (terminal stop).
            # Use uplift (Delta) of preceding codons.
            deltas = [int(FOLD_INFO[c]["delta"]) for c in codons[:-1]]
            stop_idx = len(codons) - 1
            for k in ks:
                if stop_idx >= k:
                    before = float(sum(deltas[-k:])) / float(k)
                    before_stats_mk[terminal][k].update(before)

            # Start-context after-window only (first codon in CDS).
            # Use uplift (Delta) of subsequent in-frame codons, excluding the start codon itself.
            for k in ks:
                if len(deltas) >= (k + 1):
                    after = float(sum(deltas[1 : 1 + k])) / float(k)
                    start_after_stats_mk[k].update(after)

        if max_records and n_records > int(max_records):
            break

    hb.force(f"done records={n_records} used={n_used} invalid={n_invalid}")
    boundary_rate = boundary_token_count / float(coding_tokens) if coding_tokens > 0 else float("nan")
    stop_total = int(sum(term_stop_counts.values()))
    term_stop_rates = {c: (float(term_stop_counts.get(c, 0)) / float(stop_total) if stop_total else 0.0) for c in sorted(term_stop_counts)}

    stop_ctx: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for k in ks:
        stop_ctx[str(k)] = {}
        for codon in sorted(stop_codons):
            bs = before_stats_mk[codon][k]
            stop_ctx[str(k)][codon] = {
                "n": int(bs.n),
                "before_mean": (float(bs.mean) if bs.n > 0 else None),
                "after_mean": None,
            }

    start_ctx: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for k in ks:
        a = start_after_stats_mk[k]
        start_ctx[str(k)] = {
            "before": {"n": 0, "mean": None},
            "after": {"n": int(a.n), "mean": (float(a.mean) if a.n > 0 else None)},
        }

    stop_effects: dict[str, dict[str, dict[str, object]]] = {"before": {}, "after": {}}
    for k in ks:
        stop_effects["before"][str(k)] = {}
        stop_effects["after"][str(k)] = {}
        for c1, c2 in _STOP_PAIRS:
            pair = f"{c1}_vs_{c2}"
            if c1 not in stop_codons or c2 not in stop_codons:
                stop_effects["before"][str(k)][pair] = {
                    "n1": 0,
                    "n2": 0,
                    "mean1": None,
                    "mean2": None,
                    "diff": None,
                    "ci_low": None,
                    "ci_high": None,
                    "d": None,
                    "g": None,
                    "z": None,
                    "p": None,
                }
                stop_effects["after"][str(k)][pair] = {
                    "n1": 0,
                    "n2": 0,
                    "mean1": None,
                    "mean2": None,
                    "diff": None,
                    "ci_low": None,
                    "ci_high": None,
                    "d": None,
                    "g": None,
                    "z": None,
                    "p": None,
                }
                continue
            stop_effects["before"][str(k)][pair] = _mean_diff_effects_from_stats(before_stats_mk[c1][k], before_stats_mk[c2][k])
            # CDS records do not have after-windows at the terminal stop.
            stop_effects["after"][str(k)][pair] = {
                "n1": 0,
                "n2": 0,
                "mean1": None,
                "mean2": None,
                "diff": None,
                "ci_low": None,
                "ci_high": None,
                "d": None,
                "g": None,
                "z": None,
                "p": None,
            }

    return {
        "records": int(n_records),
        "records_used": int(n_used),
        "records_invalid": int(n_invalid),
        "records_no_terminal_stop": int(n_no_terminal_stop),
        "records_internal_stop": int(n_internal_stop),
        "coding_tokens": int(coding_tokens),
        "boundary_token_count": int(boundary_token_count),
        "boundary_rate": float(boundary_rate),
        "termination_stop_counts": {k: int(v) for k, v in sorted(term_stop_counts.items())},
        "termination_stop_boundary_count": int(term_stop_boundary),
        "termination_stop_rates": {k: float(v) for k, v in sorted(term_stop_rates.items())},
        "stop_context_multi_k": stop_ctx,
        "stop_context_effects_multi_k": stop_effects,
        "start_context_multi_k": start_ctx,
        "codon_counts": {k: int(v) for k, v in sorted(codon_counts.items())},
        "aa_counts": {k: int(v) for k, v in sorted(aa_counts.items())},
        "V_hist": {str(k): int(v) for k, v in sorted(v_hist.items())},
        "Delta_hist": {str(k): int(v) for k, v in sorted(delta_hist.items())},
        "zspectrum_metrics": {
            "boundary_rate": _summarize_float_list(seg_boundary_rates),
            "entropy_Z": _summarize_float_list(seg_entropy_z),
            "autocorr_Z1": _summarize_float_list(seg_autocorr_z1),
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cross-domain corpus panel scan (Fold_6 spectra)")
    p.add_argument("--panel", default="corpus_panel_v1", help="Panel name under manifest.panels.")
    p.add_argument("--out-json", default=str(root_dir() / "data" / "panel" / "corpus_panel_summary.json"), help="Output JSON path.")
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--max-records", type=int, default=0, help="Optional max records per dataset (0 = no limit).")
    p.add_argument(
        "--heartbeat-s",
        type=float,
        default=60.0,
        help="Emit a progress heartbeat at least once per this many seconds (0 disables).",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def _emit_latex_from_summary(out: dict[str, object]) -> None:
    items = out.get("items") or []
    if not isinstance(items, list):
        items = []
    k_list = out.get("k_list") or []
    if not isinstance(k_list, list):
        k_list = []
    panel = str(out.get("panel") or "")

    def tex_path(s: object) -> str:
        t = str(s) if s is not None else ""
        if not t or t == "-":
            return "-"
        return f"\\path{{{t}}}"

    def _is_num(x: object) -> bool:
        try:
            v = float(x)  # type: ignore[arg-type]
        except Exception:
            return False
        return (not math.isnan(v)) and math.isfinite(v)

    def _fmt_float(x: object, *, nd: int = 4) -> str:
        if not _is_num(x):
            return "-"
        return f"{float(x):.{int(nd)}f}"

    def _fmt_float_signed(x: object, *, nd: int = 4) -> str:
        if not _is_num(x):
            return "-"
        v = float(x)
        s = f"{v:.{int(nd)}f}"
        return s if s.startswith("-") else ("+" + s)

    def _fmt_z(x: object) -> str:
        if not _is_num(x):
            return "-"
        return f"{float(x):.2f}"

    def _fmt_p(p: object) -> str:
        if not _is_num(p):
            return "-"
        p0 = float(p)
        if p0 == 0.0:
            return "<1e-300"
        if p0 < 1e-4:
            return f"{p0:.2e}"
        return f"{p0:.4f}"

    # LaTeX rows: one per item (compact).
    # Columns: label, domain, mode, code_id, n_used, boundary_rate, term UAA/UAG/UGA fractions, U null delta
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if not it.get("present"):
            rows.append(
                f"{tex_path(it.get('label','-'))} & {it.get('domain','-')} & {tex_path(it.get('mode','-'))} & {it.get('code_id','-')} & - & - & - & - & - & - & - \\\\"
            )
            continue
        summ = it.get("summary") or {}
        if not isinstance(summ, dict):
            summ = {}
        mode = str(it.get("mode") or "")
        n_used = int(summ.get("records_with_orf", 0) or 0) if mode == "refseq_mrna_best_orf" else int(summ.get("records_used", 0) or 0)
        br = float(summ.get("boundary_rate", float("nan")))
        rates = summ.get("termination_stop_rates") or {}
        if not isinstance(rates, dict):
            rates = {}
        uaa = float(rates.get("UAA", 0.0) or 0.0)
        uag = float(rates.get("UAG", 0.0) or 0.0)
        uga = float(rates.get("UGA", 0.0) or 0.0)
        cu = it.get("codon_usage_null") or {}
        if not isinstance(cu, dict):
            cu = {}
        uobs = float(((cu.get("U") or {}).get("obs_mean") or float("nan")))  # type: ignore[union-attr]
        unull = float(((cu.get("U") or {}).get("null_mean") or float("nan")))  # type: ignore[union-attr]
        du = uobs - unull if (not math.isnan(uobs) and not math.isnan(unull)) else float("nan")
        rows.append(
            f"{tex_path(it.get('label','-'))} & {it.get('domain','-')} & {tex_path(it.get('mode','-'))} & {it.get('code_id','-')} & "
            f"{n_used} & {br:.4f} & {uaa:.4f} & {uag:.4f} & {uga:.4f} & {uobs:.4f} & {du:+.4f} \\\\"
        )
    write_text(generated_dir() / "corpus_panel_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")

    ks = []
    for x in k_list:
        try:
            ks.append(int(x))
        except Exception:
            continue
    k_primary = 10 if 10 in ks else (min(ks) if ks else 10)
    ks_s = ",".join(str(int(x)) for x in ks)
    summary_lines = [f"Corpus panel {tex_path(panel)} generated $n={len(items)}$ item summaries with $k\\in\\{{{ks_s}\\}}$."]
    write_text(generated_dir() / "corpus_panel_summary.tex", "\n".join(summary_lines) + "\n")

    # Codon-usage null-model deviations summary across the panel (amino-acid preserving).
    # Columns: label, domain, mode, code id, n, dZ, zZ, dU, zU.
    null_lines: list[str] = []
    null_lines.append("Codon-usage null-model deviations (amino-acid preserving) across the corpus panel.")
    null_lines.append("")
    null_lines.append("\\begin{center}")
    null_lines.append("\\scriptsize")
    null_lines.append("\\setlength{\\tabcolsep}{4pt}")
    null_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    null_lines.append("\\resizebox{\\textwidth}{!}{%")
    null_lines.append("\\begin{tabular}{lllrrrrrr}")
    null_lines.append("\\toprule")
    null_lines.append("label & domain & mode & code id & $n$ & $\\Delta\\overline{Z}$ & $z_Z$ & $\\Delta\\overline{U}$ & $z_U$ \\\\")
    null_lines.append("\\midrule")
    for it in items:
        if not isinstance(it, dict):
            continue
        label = tex_path(it.get("label", "-"))
        domain = str(it.get("domain") or "-")
        mode = tex_path(it.get("mode", "-"))
        code_id = it.get("code_id", "-")
        if not it.get("present"):
            null_lines.append(f"{label} & {domain} & {mode} & {code_id} & - & - & - & - & - \\\\")
            continue
        summ = it.get("summary") or {}
        if not isinstance(summ, dict):
            summ = {}
        cu = it.get("codon_usage_null") or {}
        if not isinstance(cu, dict):
            cu = {}
        u = cu.get("U") or {}
        z = cu.get("Z") or {}
        if not isinstance(u, dict) or not isinstance(z, dict):
            u = {} if not isinstance(u, dict) else u
            z = {} if not isinstance(z, dict) else z
        n = int(summ.get("coding_tokens", 0) or 0)
        dz = (float(z.get("obs_mean")) - float(z.get("null_mean"))) if (_is_num(z.get("obs_mean")) and _is_num(z.get("null_mean"))) else None
        du2 = (float(u.get("obs_mean")) - float(u.get("null_mean"))) if (_is_num(u.get("obs_mean")) and _is_num(u.get("null_mean"))) else None
        null_lines.append(
            f"{label} & {domain} & {mode} & {code_id} & {n} & {_fmt_float(dz, nd=4)} & {_fmt_z(z.get('z'))} & {_fmt_float(du2, nd=4)} & {_fmt_z(u.get('z'))} \\\\"
        )
    null_lines.append("\\bottomrule")
    null_lines.append("\\end{tabular}%")
    null_lines.append("}")
    null_lines.append("\\end{center}")
    null_lines.append("")
    write_text(generated_dir() / "corpus_panel_codon_usage_null_summary.tex", "\n".join(null_lines) + "\n")

    # Codon-usage null decomposition for U (top-k contributions).
    # We recompute decomposition from the stored codon/aa counts so the LaTeX can be re-emitted on cache hits.
    tt = load_translation_tables()
    codon_u = {c: float(FOLD_INFO[c]["delta"]) for c in GENETIC_CODE}

    # 1) Top-5 AA contributions per dataset.
    aa_lines: list[str] = []
    aa_lines.append("Amino-acid preserving null decomposition for $\\overline{U}$ across the corpus panel (top-5 AA contributions per dataset; code id varies).")
    aa_lines.append("")
    aa_lines.append("\\begingroup")
    aa_lines.append("\\hbadness=10000")
    aa_lines.append("\\scriptsize")
    aa_lines.append("\\setlength{\\tabcolsep}{2pt}")
    aa_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    aa_lines.append("\\setlength{\\LTleft}{0pt}")
    aa_lines.append("\\setlength{\\LTright}{0pt}")
    aa_lines.append(
        "\\begin{longtable}{>{\\raggedright\\arraybackslash}p{2.9cm} l >{\\raggedright\\arraybackslash}p{2.7cm} r l r r r r}"
    )
    aa_lines.append("\\toprule")
    aa_lines.append("label & domain & mode & code id & AA & $n$ & $\\bar{U}_{\\mathrm{obs}}$ & $\\bar{U}_{\\mathrm{null}}$ & contrib \\\\")
    aa_lines.append("\\midrule")
    for it in items:
        if not isinstance(it, dict) or not it.get("present"):
            continue
        code_id = int(it.get("code_id") or 1)
        if code_id not in tt:
            continue
        codon_to_aa, _stop_codons = tt[code_id]
        summ = it.get("summary") or {}
        if not isinstance(summ, dict):
            continue
        codon_counts = summ.get("codon_counts") or {}
        aa_counts = summ.get("aa_counts") or {}
        if not isinstance(codon_counts, dict) or not isinstance(aa_counts, dict):
            continue
        codons_by_aa = codons_by_aa_from_map(codon_to_aa)
        try:
            decomp_u = aa_preserving_null_decomposition(
                aa_counts={str(k): int(v) for k, v in aa_counts.items()},
                codon_counts={str(k): int(v) for k, v in codon_counts.items()},
                codons_by_aa=codons_by_aa,
                genetic_code=codon_to_aa,
                codon_value=codon_u,
                exclude_aas={"Stop"},
            )
        except Exception:
            continue
        top = decomp_u.aa_contribs[:5]
        for r in top:
            aa_lines.append(
                f"{tex_path(it.get('label','-'))} & {str(it.get('domain') or '-')} & {tex_path(it.get('mode','-'))} & {int(code_id)} & "
                f"{str(r.aa)} & {int(r.n)} & {_fmt_float(r.obs_mean, nd=4)} & {_fmt_float(r.null_mean, nd=4)} & {_fmt_float_signed(r.contrib, nd=5)} \\\\"
            )
    aa_lines.append("\\bottomrule")
    aa_lines.append("\\end{longtable}")
    aa_lines.append("\\endgroup")
    aa_lines.append("")
    write_text(generated_dir() / "corpus_panel_codon_usage_null_decomp_u_aa_top5.tex", "\n".join(aa_lines) + "\n")

    # 2) Top-10 codon contributions per dataset.
    codon_lines: list[str] = []
    codon_lines.append("Amino-acid preserving null decomposition for $\\overline{U}$ across the corpus panel (top-10 codon contributions per dataset; code id varies).")
    codon_lines.append("")
    codon_lines.append("\\begingroup")
    codon_lines.append("\\hbadness=10000")
    codon_lines.append("\\scriptsize")
    codon_lines.append("\\setlength{\\tabcolsep}{2pt}")
    codon_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    codon_lines.append("\\setlength{\\LTleft}{0pt}")
    codon_lines.append("\\setlength{\\LTright}{0pt}")
    codon_lines.append(
        "\\begin{longtable}{>{\\raggedright\\arraybackslash}p{2.9cm} l >{\\raggedright\\arraybackslash}p{2.7cm} r l l r r r}"
    )
    codon_lines.append("\\toprule")
    codon_lines.append("label & domain & mode & code id & codon & AA & $c_{\\mathrm{obs}}$ & $c_{\\mathrm{null}}$ & contrib \\\\")
    codon_lines.append("\\midrule")
    for it in items:
        if not isinstance(it, dict) or not it.get("present"):
            continue
        code_id = int(it.get("code_id") or 1)
        if code_id not in tt:
            continue
        codon_to_aa, _stop_codons = tt[code_id]
        summ = it.get("summary") or {}
        if not isinstance(summ, dict):
            continue
        codon_counts = summ.get("codon_counts") or {}
        aa_counts = summ.get("aa_counts") or {}
        if not isinstance(codon_counts, dict) or not isinstance(aa_counts, dict):
            continue
        codons_by_aa = codons_by_aa_from_map(codon_to_aa)
        try:
            decomp_u = aa_preserving_null_decomposition(
                aa_counts={str(k): int(v) for k, v in aa_counts.items()},
                codon_counts={str(k): int(v) for k, v in codon_counts.items()},
                codons_by_aa=codons_by_aa,
                genetic_code=codon_to_aa,
                codon_value=codon_u,
                exclude_aas={"Stop"},
            )
        except Exception:
            continue
        top = decomp_u.codon_contribs[:10]
        for r in top:
            codon_lines.append(
                f"{tex_path(it.get('label','-'))} & {str(it.get('domain') or '-')} & {tex_path(it.get('mode','-'))} & {int(code_id)} & "
                f"{str(r.codon)} & {str(r.aa)} & {int(r.obs_count)} & {_fmt_float(r.null_count, nd=1)} & {_fmt_float_signed(r.contrib, nd=5)} \\\\"
            )
    codon_lines.append("\\bottomrule")
    codon_lines.append("\\end{longtable}")
    codon_lines.append("\\endgroup")
    codon_lines.append("")
    write_text(generated_dir() / "corpus_panel_codon_usage_null_decomp_u_codon_top10.tex", "\n".join(codon_lines) + "\n")

    # Start-context rows (primary k only).
    # Columns: label, domain, mode, code_id, n_used, k, n_before, before_mean, n_after, after_mean
    start_rows: list[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if not it.get("present"):
            start_rows.append(
                f"{tex_path(it.get('label','-'))} & {it.get('domain','-')} & {tex_path(it.get('mode','-'))} & {it.get('code_id','-')} & - & {k_primary} & - & - & - & - \\\\"
            )
            continue
        summ = it.get("summary") or {}
        if not isinstance(summ, dict):
            summ = {}
        mode = str(it.get("mode") or "")
        n_used = int(summ.get("records_with_orf", 0) or 0) if mode == "refseq_mrna_best_orf" else int(summ.get("records_used", 0) or 0)
        sc = summ.get("start_context_multi_k") or {}
        entry = (sc.get(str(int(k_primary))) if isinstance(sc, dict) else None) or {}
        b = (entry.get("before") if isinstance(entry, dict) else None) or {}
        a = (entry.get("after") if isinstance(entry, dict) else None) or {}
        nb = int(b.get("n", 0) or 0) if isinstance(b, dict) else 0
        na = int(a.get("n", 0) or 0) if isinstance(a, dict) else 0
        mb = b.get("mean") if (isinstance(b, dict) and nb > 0) else None
        ma = a.get("mean") if (isinstance(a, dict) and na > 0) else None
        mb_s = "-" if mb is None else f"{float(mb):.4f}"
        ma_s = "-" if ma is None else f"{float(ma):.4f}"
        start_rows.append(
            f"{tex_path(it.get('label','-'))} & {it.get('domain','-')} & {tex_path(it.get('mode','-'))} & {it.get('code_id','-')} & "
            f"{n_used} & {k_primary} & {nb} & {mb_s} & {na} & {ma_s} \\\\"
        )
    write_text(generated_dir() / "corpus_panel_start_context_rows.tex", "\n".join(start_rows) + "\n\\bottomrule\n")

    # Stop-context effects rows (primary k only), before/after separately.
    # Columns: label, domain, mode, code_id, k, pair, n1, n2, diff, ci_low, ci_high, g, p
    def _emit_effect_rows(side: str) -> list[str]:
        out_rows: list[str] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            if not it.get("present"):
                for c1, c2 in _STOP_PAIRS:
                    pair_key = f"{c1}_vs_{c2}"
                    pair_tex = pair_key.replace("_vs_", "$\\,$vs$\\,$")
                    out_rows.append(
                        f"{tex_path(it.get('label','-'))} & {it.get('domain','-')} & {tex_path(it.get('mode','-'))} & {it.get('code_id','-')} & "
                        f"{k_primary} & {pair_tex} & - & - & - & - & - & - & - \\\\"
                    )
                continue
            summ = it.get("summary") or {}
            if not isinstance(summ, dict):
                summ = {}
            eff = summ.get("stop_context_effects_multi_k") or {}
            side_obj = (eff.get(str(side)) if isinstance(eff, dict) else None) or {}
            k_obj = (side_obj.get(str(int(k_primary))) if isinstance(side_obj, dict) else None) or {}
            for c1, c2 in _STOP_PAIRS:
                pair_key = f"{c1}_vs_{c2}"
                pair_tex = pair_key.replace("_vs_", "$\\,$vs$\\,$")
                r = (k_obj.get(pair_key) if isinstance(k_obj, dict) else None) or {}
                n1 = int(r.get("n1", 0) or 0) if isinstance(r, dict) else 0
                n2 = int(r.get("n2", 0) or 0) if isinstance(r, dict) else 0
                diff = r.get("diff") if isinstance(r, dict) else None
                ci_low = r.get("ci_low") if isinstance(r, dict) else None
                ci_high = r.get("ci_high") if isinstance(r, dict) else None
                g = r.get("g") if isinstance(r, dict) else None
                p = r.get("p") if isinstance(r, dict) else None
                out_rows.append(
                    f"{tex_path(it.get('label','-'))} & {it.get('domain','-')} & {tex_path(it.get('mode','-'))} & {it.get('code_id','-')} & "
                    f"{k_primary} & {pair_tex} & {n1} & {n2} & {_fmt_float(diff)} & {_fmt_float(ci_low)} & {_fmt_float(ci_high)} & {_fmt_float(g)} & {_fmt_p(p)} \\\\"
                )
        return out_rows

    write_text(
        generated_dir() / "corpus_panel_stop_context_effects_before_rows.tex",
        "\n".join(_emit_effect_rows("before")) + "\n\\bottomrule\n",
    )
    write_text(
        generated_dir() / "corpus_panel_stop_context_effects_after_rows.tex",
        "\n".join(_emit_effect_rows("after")) + "\n\\bottomrule\n",
    )

    # Fixed-effect meta-analysis (by domain) for stop-context differences.
    # Uses normal-approximation SE derived from the reported CI width.
    def _meta_rows(*, ks: list[int]) -> list[str]:
        out_rows: list[str] = []
        for domain in sorted({str(it.get("domain") or "") for it in items if isinstance(it, dict) and it.get("domain")}):
            for side in ("after", "before"):
                for c1, c2 in _STOP_PAIRS:
                    pair_key = f"{c1}_vs_{c2}"
                    pair_tex = pair_key.replace("_vs_", "$\\,$vs$\\,$")
                    for k in ks:
                        diffs: list[float] = []
                        ses: list[float] = []
                        for it in items:
                            if not isinstance(it, dict) or not it.get("present"):
                                continue
                            if str(it.get("domain") or "") != domain:
                                continue
                            summ = it.get("summary") or {}
                            if not isinstance(summ, dict):
                                continue
                            eff = summ.get("stop_context_effects_multi_k") or {}
                            side_obj = (eff.get(str(side)) if isinstance(eff, dict) else None) or {}
                            k_obj = (side_obj.get(str(int(k))) if isinstance(side_obj, dict) else None) or {}
                            r = (k_obj.get(pair_key) if isinstance(k_obj, dict) else None) or {}
                            if not isinstance(r, dict):
                                continue
                            d = r.get("diff")
                            lo = r.get("ci_low")
                            hi = r.get("ci_high")
                            if (d is None) or (lo is None) or (hi is None):
                                continue
                            if not (_is_num(d) and _is_num(lo) and _is_num(hi)):
                                continue
                            lo_f = float(lo)
                            hi_f = float(hi)
                            if hi_f <= lo_f:
                                continue
                            se = (hi_f - lo_f) / (2.0 * 1.96)
                            if se <= 0:
                                continue
                            diffs.append(float(d))
                            ses.append(float(se))
                        if not diffs:
                            continue
                        wsum = 0.0
                        wdiff = 0.0
                        for d, se in zip(diffs, ses):
                            w = 1.0 / (se * se)
                            wsum += w
                            wdiff += w * float(d)
                        if wsum <= 0:
                            continue
                        meta_diff = wdiff / wsum
                        meta_se = math.sqrt(1.0 / wsum)
                        z = meta_diff / meta_se if meta_se > 0 else float("nan")
                        p = normal_two_sided_p(float(z)) if meta_se > 0 else float("nan")
                        out_rows.append(
                            f"{domain} & {side} & {pair_tex} & {int(k)} & {len(diffs)} & {_fmt_float(meta_diff, nd=4)} & {_fmt_float(meta_se, nd=4)} & {_fmt_z(z)} & {_fmt_p(p)} \\\\"
                        )
        return out_rows

    ks_all = sorted({int(x) for x in k_list if int(x) >= 1})
    ks_k10 = [10] if 10 in ks_all else ([] if not ks_all else [min(ks_all)])

    # k=10 only
    meta_k10_lines: list[str] = []
    meta_k10_lines.append("Fixed-effect meta-analysis of stop-context differences (by domain; $k=10$).")
    meta_k10_lines.append("")
    meta_k10_lines.append("\\begingroup")
    meta_k10_lines.append("\\hbadness=10000")
    meta_k10_lines.append("\\scriptsize")
    meta_k10_lines.append("\\setlength{\\tabcolsep}{4pt}")
    meta_k10_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    meta_k10_lines.append("\\setlength{\\LTleft}{0pt}")
    meta_k10_lines.append("\\setlength{\\LTright}{0pt}")
    meta_k10_lines.append("\\begin{longtable}{lllrlrrrr}")
    meta_k10_lines.append("\\toprule")
    meta_k10_lines.append("domain & window & pair & $k$ & $n$ & meta diff & meta se & $z$ & $p$ \\\\")
    meta_k10_lines.append("\\midrule")
    meta_k10_lines.extend(_meta_rows(ks=ks_k10))
    meta_k10_lines.append("\\bottomrule")
    meta_k10_lines.append("\\end{longtable}")
    meta_k10_lines.append("\\endgroup")
    meta_k10_lines.append("")
    write_text(generated_dir() / "corpus_panel_stop_context_meta_k10.tex", "\n".join(meta_k10_lines) + "\n")

    # multi-k
    meta_mk_lines: list[str] = []
    meta_mk_lines.append("Fixed-effect meta-analysis of stop-context differences (by domain; multi-$k$).")
    meta_mk_lines.append("")
    meta_mk_lines.append("\\begingroup")
    meta_mk_lines.append("\\hbadness=10000")
    meta_mk_lines.append("\\scriptsize")
    meta_mk_lines.append("\\setlength{\\tabcolsep}{4pt}")
    meta_mk_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    meta_mk_lines.append("\\setlength{\\LTleft}{0pt}")
    meta_mk_lines.append("\\setlength{\\LTright}{0pt}")
    meta_mk_lines.append("\\begin{longtable}{lllrlrrrr}")
    meta_mk_lines.append("\\toprule")
    meta_mk_lines.append("domain & window & pair & $k$ & $n$ & meta diff & meta se & $z$ & $p$ \\\\")
    meta_mk_lines.append("\\midrule")
    meta_mk_lines.extend(_meta_rows(ks=ks_all))
    meta_mk_lines.append("\\bottomrule")
    meta_mk_lines.append("\\end{longtable}")
    meta_mk_lines.append("\\endgroup")
    meta_mk_lines.append("")
    write_text(generated_dir() / "corpus_panel_stop_context_meta_multi_k.tex", "\n".join(meta_mk_lines) + "\n")


def main() -> None:
    args = parse_args()
    m = read_manifest()
    out_json = Path(args.out_json)

    panels = m.get("panels") or {}
    if not isinstance(panels, dict):
        panels = {}
    pdef = panels.get(str(args.panel))

    # Fallback: some data bundles may ship without manifest.panels. If an existing panel summary JSON
    # is present, reuse it as the authoritative definition/output and only re-emit LaTeX.
    if not isinstance(pdef, dict):
        if out_json.exists():
            cached = _read_json_dict(out_json)
            if cached is None:
                raise SystemExit(f"Missing panel: {args.panel} (and cached summary is malformed: {out_json})")
            if not args.no_latex:
                _emit_latex_from_summary(cached)
                print("Wrote LaTeX fragments into:", generated_dir())
            print(f"[reuse] panel: manifest.panels missing '{args.panel}', using cached summary: {out_json}", flush=True)
            return
        raise SystemExit(f"Missing panel: {args.panel}")

    k_list = [int(x) for x in (pdef.get("default_stop_window_list") or []) if int(x) >= 1]
    if not k_list:
        k_list = [10]
    k_list = sorted({int(x) for x in k_list})

    items = pdef.get("items") or []
    if not isinstance(items, list) or not items:
        raise SystemExit(f"Panel has no items: {args.panel}")

    # ---- Cache short-circuit ----
    datasets = m.get("datasets") if isinstance(m.get("datasets"), dict) else {}
    gc_sha: str | None = None
    if isinstance(datasets, dict):
        ds_gc = datasets.get("ncbi_gc_prt")
        if isinstance(ds_gc, dict):
            sha = ds_gc.get("sha256")
            if isinstance(sha, str) and sha:
                gc_sha = sha
    if gc_sha is None:
        gc_path = data_root() / "gc.prt"
        if gc_path.exists():
            st = gc_path.stat()
            gc_sha = f"stat:{st.st_size}:{getattr(st, 'st_mtime_ns', int(st.st_mtime * 1e9))}"

    item_fps: list[dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        dataset_key = str(it.get("dataset") or "")
        if not dataset_key:
            continue
        files = dataset_files_from_manifest(m, dataset_key)
        present = [fp for fp in files if fp.exists()]
        ds = datasets.get(dataset_key) if isinstance(datasets, dict) else None
        file_meta_by_name: dict[str, dict[str, object]] = {}
        if isinstance(ds, dict):
            if isinstance(ds.get("files"), list):
                for e in (ds.get("files") or []):
                    if not isinstance(e, dict):
                        continue
                    nm = e.get("name")
                    if isinstance(nm, str) and nm:
                        file_meta_by_name[nm] = dict(e)
            lp = ds.get("local_path")
            if isinstance(lp, str) and lp:
                file_meta_by_name[Path(lp).name] = {
                    "name": Path(lp).name,
                    "sha256": ds.get("sha256"),
                    "bytes": ds.get("bytes"),
                }
        fp_list: list[dict[str, object]] = []
        for fp in present:
            e = file_meta_by_name.get(fp.name) or {}
            sha = e.get("sha256")
            if isinstance(sha, str) and sha:
                fp_list.append({"name": fp.name, "sha256": sha, "bytes": int(e.get("bytes", fp.stat().st_size) or fp.stat().st_size)})
            else:
                st = fp.stat()
                fp_list.append({"name": fp.name, "bytes": int(st.st_size), "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))})
        fp_list.sort(key=lambda x: str(x.get("name") or ""))
        mode = str(it.get("mode") or "")
        code_id = int(it.get("code_id") or 1)
        entry: dict[str, object] = {
            "dataset": dataset_key,
            "mode": mode,
            "code_id": code_id,
            "present_n": int(len(present)),
            "files": fp_list,
        }
        # If we may reuse the upstream human RefSeq transcriptome summary, include its cache digest
        # so the panel cache invalidates when the upstream summary changes (even if raw FASTA is unchanged).
        if (int(args.max_records) == 0) and dataset_key == "refseq_hsapiens_mrna" and mode == "refseq_mrna_best_orf" and int(code_id) == 1:
            ref_sum = root_dir() / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json"
            mp = cache_meta_path(ref_sum)
            if mp.exists():
                meta = _read_json_dict(mp)
                if meta is not None and isinstance(meta.get("cache_digest"), str):
                    entry["refseq_transcriptome_summary_cache_digest"] = str(meta.get("cache_digest"))
                else:
                    entry["refseq_transcriptome_summary_cache_digest"] = f"stat:{mp.stat().st_size}:{getattr(mp.stat(),'st_mtime_ns', int(mp.stat().st_mtime*1e9))}"
            elif ref_sum.exists():
                st = ref_sum.stat()
                entry["refseq_transcriptome_summary_cache_digest"] = f"stat:{st.st_size}:{getattr(st,'st_mtime_ns', int(st.st_mtime*1e9))}"
            else:
                entry["refseq_transcriptome_summary_cache_digest"] = None
        item_fps.append(entry)
    item_fps.sort(key=lambda x: str(x.get("dataset") or ""))

    # Map for per-item caches: key=(dataset, mode, code_id) -> file fingerprint entry.
    item_fp_map: dict[tuple[str, str, int], dict[str, object]] = {}
    for e in item_fps:
        try:
            ds = str(e.get("dataset") or "")
            md = str(e.get("mode") or "")
            cid = int(e.get("code_id") or 1)
        except Exception:
            continue
        if ds:
            item_fp_map[(ds, md, int(cid))] = e

    cache_key = {
        "analysis": "corpus_panel",
        "analysis_version": int(ANALYSIS_VERSION),
        "panel": str(args.panel),
        "max_records": int(args.max_records),
        "mu_star": MU_STAR,
        "gc_prt": gc_sha,
        "items": item_fps,
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_json, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_json}")
        if args.no_latex:
            return
        try:
            cached = json.loads(out_json.read_text(encoding="utf-8"))
        except Exception:
            cached = None
        if not isinstance(cached, dict):
            raise SystemExit("Cached corpus panel JSON is malformed; rerun with --force.")
        _emit_latex_from_summary(cached)
        print("Wrote LaTeX fragments into:", generated_dir())
        return

    # ---- Per-item caches (avoid rescanning unaffected corpora) ----
    item_cache_dir = corpus_panel_item_cache_dir()

    # Best-effort: seed per-item caches from an existing panel summary JSON (even if panel cache miss),
    # so formatting-only changes or upstream reuse-digest changes do not force a full rescan.
    if (not args.force) and out_json.exists():
        old = _read_json_dict(out_json)
        if (
            isinstance(old, dict)
            and int(old.get("analysis_version", 0) or 0) == int(ANALYSIS_VERSION)
            and str(old.get("panel") or "") == str(args.panel)
            and isinstance(old.get("k_list"), list)
        ):
            try:
                old_k_list = [int(x) for x in (old.get("k_list") or [])]  # type: ignore[arg-type]
            except Exception:
                old_k_list = []
            if old_k_list == [int(x) for x in k_list]:
                old_items = old.get("items") or []
                if isinstance(old_items, list):
                    for oit in old_items:
                        if not isinstance(oit, dict) or not oit.get("present"):
                            continue
                        ds0 = str(oit.get("dataset") or "")
                        md0 = str(oit.get("mode") or "")
                        cid0 = int(oit.get("code_id") or 1)
                        # Do not seed the special human RefSeq reuse item (depends on upstream transcriptome digest).
                        if (
                            int(args.max_records) == 0
                            and ds0 == "refseq_hsapiens_mrna"
                            and md0 == "refseq_mrna_best_orf"
                            and int(cid0) == 1
                        ):
                            continue
                        summ0 = oit.get("summary")
                        null0 = oit.get("codon_usage_null")
                        if not isinstance(summ0, dict) or not isinstance(null0, dict):
                            continue
                        fp0 = item_fp_map.get((ds0, md0, int(cid0))) or {}
                        item_cache_key0 = {
                            "analysis": "corpus_panel_item",
                            "analysis_version": int(ANALYSIS_VERSION),
                            "dataset": ds0,
                            "mode": md0,
                            "code_id": int(cid0),
                            "k_list": [int(x) for x in k_list],
                            "max_records": int(args.max_records),
                            "mu_star": MU_STAR,
                            "gc_prt": gc_sha,
                            "fingerprint": fp0,
                        }
                        meta0 = {"cache_key": item_cache_key0, "cache_digest": cache_key_digest(item_cache_key0)}
                        item_json0 = item_cache_dir / f"{meta0['cache_digest']}.json"
                        if item_json0.exists() and cache_meta_path(item_json0).exists():
                            continue
                        write_json_atomic(item_json0, {"summary": summ0, "codon_usage_null": null0})
                        write_json_atomic(cache_meta_path(item_json0), meta0)

    tt = load_translation_tables()

    out_items = []
    for it in items:
        if not isinstance(it, dict):
            continue
        dataset_key = str(it.get("dataset") or "")
        if not dataset_key:
            continue
        mode = str(it.get("mode") or "")
        label = str(it.get("label") or dataset_key)
        domain = str(it.get("domain") or "")
        code_id = int(it.get("code_id") or 1)

        if code_id not in tt:
            raise SystemExit(f"Missing translation table code_id={code_id} (need data/gc.prt)")
        codon_to_aa, stop_codons = tt[code_id]
        if not stop_codons:
            raise SystemExit(f"Translation table code_id={code_id} has empty stop set")

        files = dataset_files_from_manifest(m, dataset_key)
        present = [fp for fp in files if fp.exists()]
        if not present:
            out_items.append(
                {
                    "dataset": dataset_key,
                    "label": label,
                    "domain": domain,
                    "mode": mode,
                    "code_id": code_id,
                    "files": [str(fp) for fp in files],
                    "present": False,
                    "error": "missing_files",
                }
            )
            continue

        # Per-item cache.
        fp_entry = item_fp_map.get((dataset_key, mode, int(code_id))) or {
            "dataset": dataset_key,
            "mode": mode,
            "code_id": int(code_id),
            "present_n": int(len(present)),
            "files": [{"name": fp.name} for fp in present],
        }
        item_cache_key = {
            "analysis": "corpus_panel_item",
            "analysis_version": int(ANALYSIS_VERSION),
            "dataset": dataset_key,
            "mode": mode,
            "code_id": int(code_id),
            "k_list": [int(x) for x in k_list],
            "max_records": int(args.max_records),
            "mu_star": MU_STAR,
            "gc_prt": gc_sha,
            "fingerprint": fp_entry,
        }
        item_meta = {"cache_key": item_cache_key, "cache_digest": cache_key_digest(item_cache_key)}
        item_json = item_cache_dir / f"{item_meta['cache_digest']}.json"
        if (not args.force) and cache_hit(item_json, expected_meta=item_meta, require_meta=True):
            cached_item = _read_json_dict(item_json) or {}
            res_cached = cached_item.get("summary")
            null_cached = cached_item.get("codon_usage_null")
            if isinstance(res_cached, dict) and isinstance(null_cached, dict):
                out_items.append(
                    {
                        "dataset": dataset_key,
                        "label": label,
                        "domain": domain,
                        "mode": mode,
                        "code_id": code_id,
                        "files": [str(fp) for fp in present],
                        "present": True,
                        "summary": res_cached,
                        "codon_usage_null": null_cached,
                    }
                )
                continue

        res: dict[str, object] | None = None
        # Lightweight cross-script reuse: if the upstream human RefSeq transcriptome summary exists
        # (produced by exp_refseq_transcriptome_merge.py), use it to avoid rescanning the large corpus.
        if (
            (int(args.max_records) == 0)
            and dataset_key == "refseq_hsapiens_mrna"
            and mode == "refseq_mrna_best_orf"
            and int(code_id) == 1
        ):
            res = _maybe_reuse_hsapiens_refseq_summary(
                m=m,
                present_files=present,
                stop_codons=set(stop_codons),
                k_list=k_list,
            )
            if res is not None:
                print("[reuse] panel: using data/refseq_hsapiens_mrna/transcriptome_summary.json for refseq_hsapiens_mrna", flush=True)

        if res is None:
            if mode == "refseq_mrna_best_orf":
                res = scan_refseq_mrna_best_orf(
                    present,
                    k_list=k_list,
                    codon_to_aa=codon_to_aa,
                    stop_codons=stop_codons,
                    max_records=int(args.max_records),
                    heartbeat_s=float(args.heartbeat_s),
                    progress_label=label,
                )
            elif mode == "cds_fasta":
                res = scan_cds_fasta(
                    present,
                    k_list=k_list,
                    codon_to_aa=codon_to_aa,
                    stop_codons=stop_codons,
                    max_records=int(args.max_records),
                    heartbeat_s=float(args.heartbeat_s),
                    progress_label=label,
                )
            else:
                raise SystemExit(f"Unsupported mode: {mode} (dataset={dataset_key})")

        # Null decomposition for U and Z (using observed codon/aa counts).
        codon_counts = {str(k): int(v) for k, v in (res.get("codon_counts", {}) or {}).items()}
        aa_counts = {str(k): int(v) for k, v in (res.get("aa_counts", {}) or {}).items()}
        codons_by_aa = codons_by_aa_from_map(codon_to_aa)

        codon_u = {c: float(FOLD_INFO[c]["delta"]) for c in GENETIC_CODE}
        codon_z = {c: float(FOLD_INFO[c]["v"]) for c in GENETIC_CODE}
        decomp_u = aa_preserving_null_decomposition(
            aa_counts=aa_counts,
            codon_counts=codon_counts,
            codons_by_aa=codons_by_aa,
            genetic_code=codon_to_aa,
            codon_value=codon_u,
            exclude_aas={"Stop"},
        )
        decomp_z = aa_preserving_null_decomposition(
            aa_counts=aa_counts,
            codon_counts=codon_counts,
            codons_by_aa=codons_by_aa,
            genetic_code=codon_to_aa,
            codon_value=codon_z,
            exclude_aas={"Stop"},
        )

        out_items.append(
            {
                "dataset": dataset_key,
                "label": label,
                "domain": domain,
                "mode": mode,
                "code_id": code_id,
                "files": [str(fp) for fp in present],
                "present": True,
                "summary": res,
                "codon_usage_null": {
                    "U": {
                        "obs_mean": decomp_u.obs_mean,
                        "null_mean": decomp_u.null_mean,
                        "null_sd": decomp_u.null_sd,
                        "z": decomp_u.z_score,
                        "p": decomp_u.p_value,
                    },
                    "Z": {
                        "obs_mean": decomp_z.obs_mean,
                        "null_mean": decomp_z.null_mean,
                        "null_sd": decomp_z.null_sd,
                        "z": decomp_z.z_score,
                        "p": decomp_z.p_value,
                    },
                },
            }
        )

        # Persist per-item cache (post-scan).
        try:
            write_json_atomic(
                item_json,
                {
                    "summary": res,
                    "codon_usage_null": out_items[-1].get("codon_usage_null"),
                },
            )
            write_json_atomic(cache_meta_path(item_json), item_meta)
        except Exception:
            # Cache is best-effort; never fail the main run.
            pass

    out = {
        "schema_version": 2,
        "analysis_version": int(ANALYSIS_VERSION),
        "panel": str(args.panel),
        "k_list": [int(x) for x in k_list],
        "mu_star": MU_STAR,
        "items": out_items,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_json, out)
    write_json_atomic(cache_meta_path(out_json), cache_meta)
    print("Wrote:", out_json)

    if args.no_latex:
        return

    _emit_latex_from_summary(out)
    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


