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
from stats_tools import aa_preserving_null_decomposition


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


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
    ks_s = ",".join(str(int(x)) for x in ks)
    summary_lines = [f"Corpus panel {tex_path(panel)} generated $n={len(items)}$ item summaries with $k\\in\\{{{ks_s}\\}}$."]
    write_text(generated_dir() / "corpus_panel_summary.tex", "\n".join(summary_lines) + "\n")


def main() -> None:
    args = parse_args()
    m = read_manifest()
    panels = m.get("panels") or {}
    if not isinstance(panels, dict):
        raise SystemExit("manifest.panels must be an object")
    pdef = panels.get(str(args.panel))
    if not isinstance(pdef, dict):
        raise SystemExit(f"Missing panel: {args.panel}")

    k_list = [int(x) for x in (pdef.get("default_stop_window_list") or []) if int(x) >= 1]
    if not k_list:
        k_list = [10]
    k_list = sorted({int(x) for x in k_list})

    items = pdef.get("items") or []
    if not isinstance(items, list) or not items:
        raise SystemExit(f"Panel has no items: {args.panel}")

    out_json = Path(args.out_json)

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

    out = {
        "schema_version": 1,
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


