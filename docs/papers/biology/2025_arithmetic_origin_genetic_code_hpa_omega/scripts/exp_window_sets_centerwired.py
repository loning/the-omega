# -*- coding: utf-8 -*-
"""
ISA-WV1: Decoder-driven candidate selection for reporter windows (centerwired control-flow).

We start from RefSeq-derived, composition-matched terminal-stop context pairs
(`matched_after_high` vs `matched_after_low`) and compute simple Z128/ISA
control-flow features by running the centerwired gate state machine on the
local codon stream (k_before, stop, k_after).

Goal
----
Provide an actionable candidate library for W1/W2-style reporter assays:
  - composition is matched (GC + dinucleotide, per the upstream pairing);
  - control-flow signatures (gate/refinement schedule) differ maximally.

Outputs:
  - data/_cache/window_sets_centerwired.json
  - sections/generated/window_sets_centerwired.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import BOUNDARY_WORDS, fold_codon


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _parse_int_set(s: str) -> set[int]:
    out: set[int] = set()
    for p in (s or "").split(","):
        p = p.strip()
        if not p:
            continue
        out.add(int(p))
    if not out:
        raise SystemExit("--delta-m10 produced an empty set")
    return {int(x) for x in out}


def _sanitize_codon_dna(b3: str) -> str:
    b3 = str(b3).upper().replace("U", "T")
    if len(b3) != 3:
        return "AAA"
    return "".join(ch if ch in "ACGT" else "A" for ch in b3)


@dataclass(frozen=True)
class CenterwiredFeatures:
    k_before: int
    k_after: int
    refined_after_count: int
    m10_after_count: int
    refined_after_frac: float
    m10_after_frac: float
    gate_counts_after: dict[str, int]


def _centerwired_features_from_context(
    *,
    before_seq_dna: str,
    stop_codon_dna: str,
    after_seq_dna: str,
    delta_to_m10: set[int],
) -> CenterwiredFeatures:
    before = str(before_seq_dna or "").upper()
    after = str(after_seq_dna or "").upper()
    stop = str(stop_codon_dna or "").upper()
    seq = before + stop + after
    L = (len(seq) // 3) * 3
    seq = seq[:L]
    codons = [_sanitize_codon_dna(seq[i : i + 3]) for i in range(0, len(seq), 3)]

    k_before = len(before) // 3
    k_after = len(after) // 3
    stop_index = int(k_before)

    refined = False
    m_eff: list[int] = []
    gate_counts_after = {w: 0 for w in sorted(BOUNDARY_WORDS)}

    for i, codon_dna in enumerate(codons):
        f = fold_codon(codon_dna.replace("T", "U"), MU_STAR)
        w = str(f.w)
        delta = int(f.delta)

        if i > stop_index and w in gate_counts_after:
            gate_counts_after[w] += 1

        if w == "101001":
            refined = True
            m_eff.append(6)
            continue
        if w in ("100101", "100001"):
            refined = False
            m_eff.append(6)
            continue
        if refined:
            m_eff.append(10 if delta in delta_to_m10 else 8)
        else:
            m_eff.append(6)

    after_idx = [i for i in range(stop_index + 1, min(stop_index + 1 + int(k_after), len(m_eff)))]
    refined_after_count = int(sum(1 for i in after_idx if m_eff[i] in (8, 10)))
    m10_after_count = int(sum(1 for i in after_idx if m_eff[i] == 10))

    refined_after_frac = float(refined_after_count / k_after) if k_after > 0 else float("nan")
    m10_after_frac = float(m10_after_count / k_after) if k_after > 0 else float("nan")

    return CenterwiredFeatures(
        k_before=int(k_before),
        k_after=int(k_after),
        refined_after_count=int(refined_after_count),
        m10_after_count=int(m10_after_count),
        refined_after_frac=float(refined_after_frac),
        m10_after_frac=float(m10_after_frac),
        gate_counts_after=gate_counts_after,
    )


def _fmt_float(x: float | None, *, nd: int = 3) -> str:
    if x is None:
        return "NA"
    if not math.isfinite(float(x)):
        return "NA"
    return f"{float(x):.{int(nd)}f}"


def _tex_escape(s: str) -> str:
    """
    Minimal LaTeX escaping for text fragments (especially inside \\texttt{}).
    """
    s = str(s)
    s = s.replace("\\", "\\textbackslash{}")
    s = s.replace("{", "\\{").replace("}", "\\}")
    s = s.replace("&", "\\&").replace("%", "\\%").replace("$", "\\$")
    s = s.replace("#", "\\#").replace("_", "\\_")
    s = s.replace("~", "\\textasciitilde{}").replace("^", "\\textasciicircum{}")
    return s


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ISA-WV1: centerwired decoder-driven window-set selection (matched pairs).")
    ap.add_argument(
        "--in-jsonl",
        default=str(root_dir() / "data" / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="Input stop-context candidates JSONL (must contain matched_after_* rows).",
    )
    ap.add_argument("--candidate-set", default="reporter_coding_v1", help="Candidate-set label to filter.")
    ap.add_argument("--k", type=int, default=10, help="Window size (codons) to filter.")
    ap.add_argument("--delta-m10", default="55", help="Comma-separated Δ values that trigger m=10 in refined mode.")
    ap.add_argument("--max-pairs-per-stop", type=int, default=10, help="Max selected pairs per stop codon.")
    ap.add_argument(
        "--out-json",
        default=str(cache_dir() / "window_sets_centerwired.json"),
        help="Output JSON cache path (selected pairs + features).",
    )
    ap.add_argument(
        "--out-tex",
        default=str(generated_dir() / "window_sets_centerwired.tex"),
        help="Output LaTeX fragment path (summary table).",
    )
    ap.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    in_jsonl = Path(args.in_jsonl)
    out_json = Path(args.out_json)
    out_tex = Path(args.out_tex)

    if not in_jsonl.exists():
        raise SystemExit(f"Missing input JSONL: {in_jsonl}")

    delta_to_m10 = _parse_int_set(str(args.delta_m10))

    cache_key: dict[str, Any] = {
        "analysis": "window_sets_centerwired",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "delta_to_m10": sorted(int(x) for x in delta_to_m10),
        "candidate_set": str(args.candidate_set),
        "k": int(args.k),
        "max_pairs_per_stop": int(args.max_pairs_per_stop),
        "in_jsonl": str(in_jsonl),
        "out_json": str(out_json),
        "out_tex": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True) and out_json.exists():
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    cand_set = str(args.candidate_set)
    k = int(args.k)
    max_pairs_per_stop = int(args.max_pairs_per_stop)
    if k <= 0:
        raise SystemExit("--k must be positive")
    if max_pairs_per_stop <= 0:
        raise SystemExit("--max-pairs-per-stop must be positive")

    # Collect matched pairs keyed by (stop, rank).
    pairs: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    match_meta: dict[tuple[str, int], dict[str, Any]] = {}
    for obj in _iter_jsonl(in_jsonl):
        if str(obj.get("candidate_set") or "") != cand_set:
            continue
        if int(obj.get("k", 0) or 0) != int(k):
            continue
        gl = str(obj.get("group_label") or "")
        if gl not in ("matched_after_high", "matched_after_low"):
            continue
        stop = str(obj.get("stop_codon") or "")
        rk = int(obj.get("rank", 0) or 0)
        if not stop or rk <= 0:
            continue
        key = (stop, rk)
        pairs.setdefault(key, {})[gl] = obj
        m = ((obj.get("payload") or {}).get("match") or {}) if isinstance(obj.get("payload"), dict) else {}
        if isinstance(m, dict) and m:
            match_meta.setdefault(key, {"eps_used": m.get("eps_used"), "l1": m.get("l1")})

    # Build complete pair objects with centerwired features.
    selected_by_stop: dict[str, list[dict[str, Any]]] = {}
    all_pairs: list[dict[str, Any]] = []
    for (stop, rk), d in sorted(pairs.items(), key=lambda t: (t[0][0], t[0][1])):
        high = d.get("matched_after_high")
        low = d.get("matched_after_low")
        if not isinstance(high, dict) or not isinstance(low, dict):
            continue
        f_high = _centerwired_features_from_context(
            before_seq_dna=str(high.get("before_seq_dna") or ""),
            stop_codon_dna=str(high.get("stop_codon_dna") or ""),
            after_seq_dna=str(high.get("after_seq_dna") or ""),
            delta_to_m10=delta_to_m10,
        )
        f_low = _centerwired_features_from_context(
            before_seq_dna=str(low.get("before_seq_dna") or ""),
            stop_codon_dna=str(low.get("stop_codon_dna") or ""),
            after_seq_dna=str(low.get("after_seq_dna") or ""),
            delta_to_m10=delta_to_m10,
        )
        refined_diff = int(f_high.refined_after_count - f_low.refined_after_count)
        m10_diff = int(f_high.m10_after_count - f_low.m10_after_count)
        gate_diff = int(
            sum(abs(int(f_high.gate_counts_after[w]) - int(f_low.gate_counts_after[w])) for w in sorted(BOUNDARY_WORDS))
        )
        after_delta_diff = float((high.get("after_mean_delta") or 0.0) - (low.get("after_mean_delta") or 0.0))
        score = (abs(refined_diff), abs(m10_diff), abs(gate_diff), abs(after_delta_diff))

        row = {
            "stop_codon": stop,
            "pair_rank": int(rk),
            "candidate_set": cand_set,
            "k": int(k),
            "match": match_meta.get((stop, rk), {}),
            "features_high": asdict(f_high),
            "features_low": asdict(f_low),
            "diffs": {
                "refined_after_count": refined_diff,
                "m10_after_count": m10_diff,
                "gate_counts_after_l1": gate_diff,
                "after_mean_delta": after_delta_diff,
            },
            "score": {"abs_refined": score[0], "abs_m10": score[1], "abs_gate_l1": score[2], "abs_after_mean_delta": score[3]},
            # Minimal provenance for locating the exact windows:
            "high": {
                "record_id": high.get("record_id"),
                "frame": high.get("frame"),
                "stop_base": high.get("stop_base"),
                "before_seq_dna": high.get("before_seq_dna"),
                "stop_codon_dna": high.get("stop_codon_dna"),
                "after_seq_dna": high.get("after_seq_dna"),
                "before_mean_delta": high.get("before_mean_delta"),
                "after_mean_delta": high.get("after_mean_delta"),
                "after_gc": high.get("after_gc"),
                "after_dinuc": high.get("after_dinuc"),
            },
            "low": {
                "record_id": low.get("record_id"),
                "frame": low.get("frame"),
                "stop_base": low.get("stop_base"),
                "before_seq_dna": low.get("before_seq_dna"),
                "stop_codon_dna": low.get("stop_codon_dna"),
                "after_seq_dna": low.get("after_seq_dna"),
                "before_mean_delta": low.get("before_mean_delta"),
                "after_mean_delta": low.get("after_mean_delta"),
                "after_gc": low.get("after_gc"),
                "after_dinuc": low.get("after_dinuc"),
            },
        }
        all_pairs.append(row)
        selected_by_stop.setdefault(stop, []).append(row)

    # Rank within stop codon and select.
    selected: list[dict[str, Any]] = []
    for stop in sorted(selected_by_stop.keys()):
        rows = selected_by_stop[stop]
        rows.sort(
            key=lambda r: (
                -int((r.get("score") or {}).get("abs_refined") or 0),
                -int((r.get("score") or {}).get("abs_m10") or 0),
                -int((r.get("score") or {}).get("abs_gate_l1") or 0),
                -float((r.get("score") or {}).get("abs_after_mean_delta") or 0.0),
                int(r.get("pair_rank") or 0),
            )
        )
        selected.extend(rows[: max_pairs_per_stop])

    out_obj = {
        "analysis": "window_sets_centerwired",
        "script_version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "delta_to_m10": sorted(int(x) for x in delta_to_m10),
        "input": {"jsonl": str(in_jsonl), "candidate_set": cand_set, "k": int(k)},
        "selection": {"max_pairs_per_stop": int(max_pairs_per_stop), "selected_pairs": int(len(selected))},
        "pairs": selected,
    }
    write_json_atomic(out_json, out_obj)

    # Emit LaTeX fragment.
    cand_set_tex = _tex_escape(cand_set)
    out_json_rel = str(out_json.relative_to(root_dir()))
    out_json_tex = _tex_escape(out_json_rel)

    lines: list[str] = []
    lines.append("\\paragraph{ISA-WV1: Decoder-driven candidate selection for reporter windows (centerwired control-flow).}")
    lines.append(
        "From the RefSeq composition-matched stop-context pairs (high vs low $u_{\\mathrm{after}}$, "
        f"$k={int(k)}$; candidate-set \\texttt{{{cand_set_tex}}}), we compute centerwired gate/refinement features "
        "(refined-after count, $m=10$ hits, and downstream boundary-word hits) and select pairs with the "
        "largest divergence in the inferred control-flow signature. "
        f"Full sequences and features are exported to \\texttt{{{out_json_tex}}}."
    )
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{5pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\begin{tabular}{l r r r r r l l}")
    lines.append("\\toprule")
    lines.append(
        "stop & pair rank & $\\Delta\\overline{U}_{\\mathrm{after}}$ & $\\Delta$refined & $\\Delta m{=}10$ & match $L_1$ & high id & low id \\\\"
    )
    lines.append("\\midrule")
    for r in selected:
        m = r.get("match") or {}
        l1 = m.get("l1")
        dif = r.get("diffs") or {}
        high = r.get("high") or {}
        low = r.get("low") or {}
        high_id = _tex_escape(f"{high.get('record_id') or ''}:{int(high.get('stop_base') or 0)}")
        low_id = _tex_escape(f"{low.get('record_id') or ''}:{int(low.get('stop_base') or 0)}")
        lines.append(
            f"$\\mathrm{{{r.get('stop_codon')}}}$ & {int(r.get('pair_rank') or 0)} & {float(dif.get('after_mean_delta') or 0.0):.1f} & "
            f"{int(dif.get('refined_after_count') or 0)} & {int(dif.get('m10_after_count') or 0)} & {_fmt_float(float(l1) if l1 is not None else None, nd=3)} & "
            f"\\texttt{{{high_id}}} & \\texttt{{{low_id}}} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"[write] {out_json}", flush=True)
    print(f"[write] {out_tex}", flush=True)


if __name__ == "__main__":
    main()
