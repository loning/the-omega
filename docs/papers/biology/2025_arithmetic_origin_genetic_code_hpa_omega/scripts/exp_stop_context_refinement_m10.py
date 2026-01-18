# -*- coding: utf-8 -*-
"""
H2-8: Stop-context refinement at m=10 (stop codon + two downstream bases).

Motivation:
  In the Z128 refinement picture, an m=10 microstate projects to the m=6 anchor
  by prefix truncation of the Fold_m stable type. Biologically, stop recognition
  is known to depend on downstream bases (+4, +5, ...). Here we treat the
  stop+2nt 5-mer as an m=10 microstate, compute Fold_10, and record the induced
  m=6 anchor word u = pi_{10->6}(Fold_10(N)).

This script reports:
  1) The deterministic catalog of stop+2nt 5-mers whose induced m=6 anchor word
     lands in the boundary sector X_6^bdry (one of three 6-bit boundary words).
  2) Frequencies of those boundary-anchor contexts among human RefSeq mRNA
     terminal stops (best ORF per transcript).
  3) Frequencies among curated recoding sites (Sec/Pyl; GenBank-derived).

Outputs:
  - sections/generated/stop_context_refinement_m10.tex
  - sections/generated/stop_context_refinement_m10.tex.meta.json

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
from genetic_code_tools import STOP_CODONS, fold_m, is_boundary_word, iter_fasta, zeckendorf_value_word


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
BASES = ("A", "C", "G", "U")


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


def _kmer_bits(seq: str) -> str:
    return "".join(MU_STAR[b] for b in seq)


@dataclass(frozen=True)
class BoundaryMotif:
    stop: str
    motif5: str
    n10: int
    w10: str
    v10: int
    d10: int
    u6: str  # anchor prefix


def boundary_motif_catalog() -> list[BoundaryMotif]:
    out: list[BoundaryMotif] = []
    for stop in STOP_CODONS:
        for b1 in BASES:
            for b2 in BASES:
                motif5 = f"{stop}{b1}{b2}"
                n10 = int(_kmer_bits(motif5), 2)
                w10 = fold_m(n10, 10)
                u6 = w10[:6]
                if not is_boundary_word(u6):
                    continue
                v10 = int(zeckendorf_value_word(w10))
                out.append(
                    BoundaryMotif(
                        stop=str(stop),
                        motif5=motif5,
                        n10=int(n10),
                        w10=str(w10),
                        v10=int(v10),
                        d10=int(n10 - v10),
                        u6=str(u6),
                    )
                )
    out.sort(key=lambda r: (r.stop, r.u6, r.motif5))
    return out


@dataclass(frozen=True)
class BestOrf:
    frame: int
    start_base: int
    stop_base: int
    length_codons_including_stop: int


def best_orf_across_frames(seq: str, *, min_codons: int) -> BestOrf | None:
    """
    Longest ORF across frames using AUG starts and standard stops.
    Tie-breakers:
      - longer ORF wins
      - earlier start wins
      - lower frame wins
    """
    best: BestOrf | None = None
    for frame in (0, 1, 2):
        in_orf = False
        start_pos: int | None = None
        best_frame: BestOrf | None = None
        for pos in range(frame, len(seq) - 2, 3):
            codon = seq[pos : pos + 3]
            if codon not in STOP_CODONS and codon != "AUG":
                # Allow coding bases only.
                if len(codon) != 3 or any(b not in "ACGU" for b in codon):
                    in_orf = False
                    start_pos = None
                continue
            if not in_orf:
                if codon == "AUG":
                    in_orf = True
                    start_pos = pos
            else:
                if codon in STOP_CODONS:
                    if start_pos is not None:
                        length_codons = (pos - start_pos) // 3 + 1
                        if length_codons >= int(min_codons):
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
        else:
            key = (best_frame.length_codons_including_stop, -best_frame.start_base, -best_frame.frame)
            key_best = (best.length_codons_including_stop, -best.start_base, -best.frame)
            if key > key_best:
                best = best_frame
    return best


def _refseq_human_files() -> list[Path]:
    d = data_root() / "refseq_hsapiens_mrna"
    return sorted(d.glob("human.*.rna.fna.gz"))


def _normalize_rna(seq: str) -> str:
    return seq.upper().replace("T", "U")


def _count_terminal_stop_motifs(
    fasta_files: list[Path],
    *,
    min_orf_codons: int,
) -> tuple[Counter[str], Counter[tuple[str, str]]]:
    """
    Returns:
      - stop totals: Counter(stop)
      - motif counts: Counter((stop, motif5))
    """
    totals: Counter[str] = Counter()
    motif_counts: Counter[tuple[str, str]] = Counter()

    for fp in fasta_files:
        for _rid, seq0 in iter_fasta(str(fp)):
            seq = _normalize_rna(seq0)
            orf = best_orf_across_frames(seq, min_codons=int(min_orf_codons))
            if orf is None:
                continue
            stop_base = int(orf.stop_base)
            if stop_base + 5 > len(seq):
                continue
            stop = seq[stop_base : stop_base + 3]
            if stop not in STOP_CODONS:
                continue
            plus4 = seq[stop_base + 3]
            plus5 = seq[stop_base + 4]
            if plus4 not in BASES or plus5 not in BASES:
                continue
            motif5 = f"{stop}{plus4}{plus5}"
            totals[str(stop)] += 1
            motif_counts[(str(stop), motif5)] += 1

    return totals, motif_counts


def _count_recoding_motifs(
    jsonl_path: Path,
) -> tuple[Counter[tuple[str, str]], Counter[tuple[str, str, str]]]:
    """
    Returns:
      - totals: Counter((aa, codon))
      - motif counts: Counter((aa, codon, motif5))
    """
    totals: Counter[tuple[str, str]] = Counter()
    motif_counts: Counter[tuple[str, str, str]] = Counter()
    if not jsonl_path.exists():
        return totals, motif_counts

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            aa = str(r.get("aa") or "").strip()
            codon = str(r.get("codon_rna") or "").strip().upper().replace("T", "U")
            if aa == "" or codon not in STOP_CODONS:
                continue
            plus4 = str(r.get("plus4_nt") or "").strip().upper().replace("T", "U")
            after_nt6 = str(r.get("after_nt6") or "").strip().upper().replace("T", "U")
            plus5 = after_nt6[1] if len(after_nt6) >= 2 else ""
            if plus4 not in BASES or plus5 not in BASES:
                continue
            motif5 = f"{codon}{plus4}{plus5}"
            totals[(aa, codon)] += 1
            motif_counts[(aa, codon, motif5)] += 1
    return totals, motif_counts


def _fmt_int(x: int) -> str:
    return f"{int(x)}"


def _fmt_frac(n: int, d: int) -> str:
    if d <= 0:
        return "--"
    return f"{(float(n) / float(d)):.4f}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="H2-8 stop-context refinement at m=10 (stop+2nt).")
    p.add_argument("--min-orf-codons", type=int, default=20, help="Minimum ORF length (codons incl. stop).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "stop_context_refinement_m10.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_tex = Path(args.out_tex)

    human_files = _refseq_human_files()
    recoding_jsonl = data_root() / "recoding_genbank" / "recoding_sites.jsonl"

    cache_key: dict[str, Any] = {
        "analysis": "stop_context_refinement_m10",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "min_orf_codons": int(args.min_orf_codons),
        "inputs": {
            "refseq_hsapiens_mrna": _fingerprints(human_files),
            "recoding_sites_jsonl": _file_fingerprint(recoding_jsonl),
        },
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    motifs = boundary_motif_catalog()
    motif_to_u6 = {m.motif5: m.u6 for m in motifs}

    stop_totals, stop_motif_counts = _count_terminal_stop_motifs(
        human_files,
        min_orf_codons=int(args.min_orf_codons),
    )
    stop_u6_counts: dict[str, Counter[str]] = {}
    for stop in STOP_CODONS:
        stop_u6_counts[str(stop)] = Counter()
    for (stop, motif5), c in stop_motif_counts.items():
        u6 = motif_to_u6.get(motif5)
        if u6 is None:
            continue
        stop_u6_counts[stop][u6] += int(c)

    rec_totals, rec_motif_counts = _count_recoding_motifs(recoding_jsonl)
    rec_u6_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for (aa, codon, motif5), c in rec_motif_counts.items():
        u6 = motif_to_u6.get(motif5)
        if u6 is None:
            continue
        rec_u6_counts[(aa, codon)][u6] += int(c)

    # LaTeX
    lines: list[str] = []
    lines.append(
        "Stop-context refinement via $m=10$ microstates (stop codon + two downstream bases; $\\mu^\\ast$), "
        "projected to the $m=6$ anchor boundary sector."
    )
    lines.append("")

    # Deterministic motif catalog.
    lines.append("\\paragraph{Deterministic boundary-anchor motifs (stop+2nt).}")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{l l l l r r}")
    lines.append("\\toprule")
    lines.append("stop & motif (5-nt) & $u=\\pi_{10\\to 6}(\\mathrm{Fold}_{10})$ & $w_{10}$ & $N_{10}$ & $\\Delta_{10}$ \\\\")
    lines.append("\\midrule")
    for m in motifs:
        lines.append(
            f"{m.stop} & \\texttt{{{m.motif5}}} & \\texttt{{{m.u6}}} & \\texttt{{{m.w10}}} & {_fmt_int(m.n10)} & {_fmt_int(m.d10)} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    # Human RefSeq counts.
    lines.append(
        f"\\paragraph{{Human RefSeq terminal stops (best ORF; min ORF={int(args.min_orf_codons)} codons).}}"
    )
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{l r r r r r}")
    lines.append("\\toprule")
    lines.append(
        "stop & $n$ & $n(u=100001)$ & $n(u=100101)$ & $n(u=101001)$ & frac(boundary) \\\\"
    )
    lines.append("\\midrule")
    for stop in ("UAA", "UAG", "UGA"):
        n = int(stop_totals.get(stop, 0))
        c_100001 = int(stop_u6_counts[stop].get("100001", 0))
        c_100101 = int(stop_u6_counts[stop].get("100101", 0))
        c_101001 = int(stop_u6_counts[stop].get("101001", 0))
        cb = c_100001 + c_100101 + c_101001
        lines.append(
            f"{stop} & {_fmt_int(n)} & {_fmt_int(c_100001)} & {_fmt_int(c_100101)} & {_fmt_int(c_101001)} & {_fmt_frac(cb, n)} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    # Recoding counts.
    lines.append("\\paragraph{Recoding sites (GenBank-derived; stop+2nt available).}")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{l l r r r r r}")
    lines.append("\\toprule")
    lines.append("AA & codon & $n$ & $n(u=100001)$ & $n(u=100101)$ & $n(u=101001)$ & frac(boundary) \\\\")
    lines.append("\\midrule")
    for (aa, codon), n in sorted(rec_totals.items(), key=lambda x: (x[0][0], x[0][1])):
        c_100001 = int(rec_u6_counts[(aa, codon)].get("100001", 0))
        c_100101 = int(rec_u6_counts[(aa, codon)].get("100101", 0))
        c_101001 = int(rec_u6_counts[(aa, codon)].get("101001", 0))
        cb = c_100001 + c_100101 + c_101001
        lines.append(
            f"{aa} & {codon} & {_fmt_int(int(n))} & {_fmt_int(c_100001)} & {_fmt_int(c_100101)} & {_fmt_int(c_101001)} & {_fmt_frac(cb, int(n))} \\\\"
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

