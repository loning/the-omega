# -*- coding: utf-8 -*-
"""
ISA-B2: Stop instruction family stratification ("OpCode + microcode" lens).

We operationalize the "stop instruction family" idea in two layers:

1) Codon-level control features at m=6 under μ*:
   stop codon c ∈ {UAA,UAG,UGA} -> (N, w6, V6, Δ6, sector/boundary).

2) Local refinement at m=10 for stop+2nt (stop + +4/+5 bases):
   motif5 = stop + b_{+4} + b_{+5}  (5 nt => 10 bits)
   compute w10 = Fold_10(N10) and project to the m=6 anchor by prefix:
     u6 = π_{10->6}(w10) = w10[:6]
   mark whether u6 is in the m=6 boundary sector (three boundary words).

We then stratify the existing RefSeq terminal-stop candidate windows (used for
reporter-library design) by:
  - stop codon identity
  - candidate label (high_after vs low_after)
  - whether stop+2nt maps to a boundary anchor u6, and which u6

Outputs:
  - sections/generated/stop_instruction_family_stratification.tex
  - sections/generated/stop_instruction_family_stratification.tex.meta.json

Standard library only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import STOP_CODONS, fold_codon, fold_m, is_boundary_word, zeckendorf_value_word


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def _file_fingerprint(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"name": str(path), "missing": True}
    st = path.stat()
    return {
        "name": path.name,
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _fingerprints(paths: Iterable[Path]) -> list[dict[str, object]]:
    out = [_file_fingerprint(p) for p in paths]
    out.sort(key=lambda x: str(x.get("name") or ""))
    return out


def _normalize_rna(seq: str) -> str:
    return str(seq).strip().upper().replace("T", "U")


def _kmer_bits(seq: str) -> str:
    return "".join(MU_STAR[b] for b in seq)


@dataclass(frozen=True)
class MotifAnchor:
    motif5: str
    n10: int
    w10: str
    v10: int
    d10: int
    u6: str
    u6_is_boundary: bool


def _motif_anchor(motif5_rna: str) -> MotifAnchor:
    motif5 = _normalize_rna(motif5_rna)
    if len(motif5) != 5 or any(b not in MU_STAR for b in motif5):
        raise ValueError(f"Invalid motif5: {motif5!r}")
    n10 = int(_kmer_bits(motif5), 2)
    w10 = fold_m(n10, 10)
    u6 = w10[:6]
    v10 = int(zeckendorf_value_word(w10))
    return MotifAnchor(
        motif5=str(motif5),
        n10=int(n10),
        w10=str(w10),
        v10=int(v10),
        d10=int(n10 - v10),
        u6=str(u6),
        u6_is_boundary=bool(is_boundary_word(u6)),
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _fmt_int(x: int) -> str:
    return f"{int(x)}"


def _fmt_frac(n: int, d: int) -> str:
    if d <= 0:
        return "--"
    return f"{(float(n) / float(d)):.4f}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ISA-B2: stop instruction family stratification (μ*, m=10->6 anchors).")
    p.add_argument(
        "--refseq-candidates",
        default=str(data_root() / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="RefSeq terminal-stop candidate windows JSONL (reporter-coding set).",
    )
    p.add_argument(
        "--recoding-sites",
        default=str(data_root() / "recoding_genbank" / "recoding_sites.jsonl"),
        help="Recoding sites JSONL (Sec/Pyl; GenBank-derived).",
    )
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "stop_instruction_family_stratification.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_tex = Path(args.out_tex)
    refseq_candidates = Path(args.refseq_candidates)
    recoding_sites = Path(args.recoding_sites)

    cache_key: dict[str, Any] = {
        "analysis": "stop_instruction_family_stratification",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "inputs": {
            "refseq_candidates": _file_fingerprint(refseq_candidates),
            "recoding_sites": _file_fingerprint(recoding_sites),
        },
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    # ---- 1) Deterministic stop opcode table (μ*, m=6) ----
    stop_rows = []
    for s in STOP_CODONS:
        f = fold_codon(s, MU_STAR)
        stop_rows.append(
            {
                "stop": str(s),
                "N": int(f.n),
                "w6": str(f.w),
                "V6": int(f.v),
                "Delta6": int(f.delta),
                "sector": ("boundary" if bool(f.is_boundary) else "cyclic"),
            }
        )

    # ---- 2) RefSeq candidate-window stratification by stop+2nt anchor ----
    recs = _load_jsonl(refseq_candidates)
    # Keyed by (group_label, stop_codon).
    totals: Counter[tuple[str, str]] = Counter()
    boundary_totals: Counter[tuple[str, str]] = Counter()
    u6_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)  # only boundary anchors

    for r in recs:
        stop = _normalize_rna(r.get("stop_codon") or "")
        if stop not in STOP_CODONS:
            continue
        group = str(r.get("group_label") or "").strip()
        if group == "":
            group = "NA"

        after_nt6 = _normalize_rna(r.get("after_nt6") or "")
        plus4 = _normalize_rna(r.get("plus4_nt") or (after_nt6[:1] if after_nt6 else ""))
        plus5 = after_nt6[1] if len(after_nt6) >= 2 else ""
        if plus4 not in MU_STAR or plus5 not in MU_STAR:
            continue
        motif5 = f"{stop}{plus4}{plus5}"
        a = _motif_anchor(motif5)

        key = (group, stop)
        totals[key] += 1
        if a.u6_is_boundary:
            boundary_totals[key] += 1
            u6_counts[key][a.u6] += 1

    # ---- 3) Recoding sites: boundary-anchor rates for stop+2nt motifs ----
    recoding = _load_jsonl(recoding_sites)
    rec_totals: Counter[tuple[str, str]] = Counter()  # (aa, codon)
    rec_boundary_totals: Counter[tuple[str, str]] = Counter()
    rec_u6_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for r in recoding:
        aa = str(r.get("aa") or "").strip()
        codon = _normalize_rna(r.get("codon_rna") or "")
        if aa == "" or codon not in STOP_CODONS:
            continue
        plus4 = _normalize_rna(r.get("plus4_nt") or "")
        after_nt6 = _normalize_rna(r.get("after_nt6") or "")
        plus5 = after_nt6[1] if len(after_nt6) >= 2 else ""
        if plus4 not in MU_STAR or plus5 not in MU_STAR:
            continue
        motif5 = f"{codon}{plus4}{plus5}"
        a = _motif_anchor(motif5)
        key = (aa, codon)
        rec_totals[key] += 1
        if a.u6_is_boundary:
            rec_boundary_totals[key] += 1
            rec_u6_counts[key][a.u6] += 1

    # ---- Emit LaTeX ----
    lines: list[str] = []
    lines.append("\\paragraph{ISA-B2: Stop instruction family stratification (control features + refinement anchors).}")
    lines.append(
        "We treat the stop codon as an executable interface with a codon-level control stream (m=6) and a local "
        "refinement microstate (stop+2nt, m=10) projected to the m=6 anchor boundary sector."
    )
    lines.append("")

    # Stop opcode table.
    lines.append("\\noindent Stop codon control features under $\\mu^\\ast$ (m=6):")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{l r l r r l}")
    lines.append("\\toprule")
    lines.append("stop & $N$ & $w_6$ & $V_6$ & $\\Delta_6$ & sector \\\\")
    lines.append("\\midrule")
    for row in stop_rows:
        lines.append(
            f"{row['stop']} & {_fmt_int(int(row['N']))} & \\texttt{{{row['w6']}}} & {_fmt_int(int(row['V6']))} & {_fmt_int(int(row['Delta6']))} & {row['sector']} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    # Candidate windows: boundary-anchor rates.
    boundary_words = ["100001", "100101", "101001"]
    lines.append("\\noindent RefSeq terminal-stop candidate windows: stop+2nt boundary-anchor rates (m=10\\,$\\to$\\,6):")
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\begin{tabular}{l l r r r r r}")
    lines.append("\\toprule")
    lines.append("label & stop & $n$ & boundary & rate & " + " & ".join(f"$n(\\texttt{{{w}}})$" for w in boundary_words) + " \\\\")
    lines.append("\\midrule")
    for (group, stop), n in sorted(totals.items(), key=lambda x: (x[0][0], x[0][1])):
        nb = int(boundary_totals.get((group, stop), 0))
        parts = [str(int(u6_counts[(group, stop)].get(w, 0))) for w in boundary_words]
        lines.append(
            f"{group} & {stop} & {_fmt_int(int(n))} & {_fmt_int(int(nb))} & {_fmt_frac(int(nb), int(n))} & "
            + " & ".join(parts)
            + " \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    # Recoding sites: boundary-anchor rates.
    if rec_totals:
        lines.append("\\noindent Recoding sites (GenBank-derived): stop+2nt boundary-anchor rates (m=10\\,$\\to$\\,6):")
        lines.append("\\begin{center}")
        lines.append("\\scriptsize")
        lines.append("\\setlength{\\tabcolsep}{6pt}")
        lines.append("\\renewcommand{\\arraystretch}{1.10}")
        lines.append("\\begin{tabular}{l l r r r r r r}")
        lines.append("\\toprule")
        lines.append("aa & codon & $n$ & boundary & rate & " + " & ".join(f"$n(\\texttt{{{w}}})$" for w in boundary_words) + " \\\\")
        lines.append("\\midrule")
        for (aa, codon), n in sorted(rec_totals.items(), key=lambda x: (x[0][0], x[0][1])):
            nb = int(rec_boundary_totals.get((aa, codon), 0))
            parts = [str(int(rec_u6_counts[(aa, codon)].get(w, 0))) for w in boundary_words]
            lines.append(
                f"{aa} & {codon} & {_fmt_int(int(n))} & {_fmt_int(int(nb))} & {_fmt_frac(int(nb), int(n))} & "
                + " & ".join(parts)
                + " \\\\"
            )
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        lines.append("\\end{center}")
        lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"[write] {out_tex}", flush=True)


if __name__ == "__main__":
    main()

