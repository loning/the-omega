# -*- coding: utf-8 -*-
"""
Objective-function robustness stress test for μ* identification (Reinforcement 2).

Reviewer-facing question:
  Is the unique optimizer μ* an artifact of one very specific choice of
  control set K and one very specific objective?

Design:
  Pre-register a small family of reasonable control sets and objective variants,
  then exhaustively evaluate all 24 two-bit nucleotide encodings for each setting.

Outputs:
  - sections/generated/control_objective_robustness.tex
  - data/_cache/control_objective_robustness_v1.json (+ meta)

Standard library only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic
from genetic_code_tools import all_encodings, encoding_to_str, fold_codon, fold_m, is_boundary_word

# Reuse gc.prt parsing to construct nonstandard-table K sets (start/stop).
from exp_nonstandard_codes import codons_for_table, parse_gc_prt


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 1


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


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


@dataclass(frozen=True)
class KSpec:
    key: str
    label: str
    starts: tuple[str, ...]
    stops: tuple[str, ...]

    def all_codons(self) -> tuple[str, ...]:
        return tuple(self.starts) + tuple(self.stops)


def _is_mu_star(mu: dict[str, str]) -> bool:
    return all(mu.get(b) == MU_STAR[b] for b in ("A", "C", "G", "U"))


def _boundary_hit(*, codon: str, mu: dict[str, str], m: int) -> bool:
    f = fold_codon(codon, mu)
    w = fold_m(int(f.n), int(m)) if int(m) != 6 else str(f.w)
    return bool(is_boundary_word(str(w)))


def _score_boundary_hits(mu: dict[str, str], K: KSpec, *, m: int = 6) -> int:
    s = 0
    for c in K.all_codons():
        if _boundary_hit(codon=c, mu=mu, m=m):
            s += 1
    return int(s)


def _score_homology(mu: dict[str, str], K: KSpec, *, m: int = 6) -> int:
    """
    Start–stop boundary homology: number of start codons whose boundary word
    matches the boundary word of at least one stop codon (in the same m).
    """
    stop_ws = set()
    for c in K.stops:
        if _boundary_hit(codon=c, mu=mu, m=m):
            f = fold_codon(c, mu)
            w = fold_m(int(f.n), int(m)) if int(m) != 6 else str(f.w)
            stop_ws.add(str(w))
    if not stop_ws:
        return 0
    h = 0
    for c in K.starts:
        if _boundary_hit(codon=c, mu=mu, m=m):
            f = fold_codon(c, mu)
            w = fold_m(int(f.n), int(m)) if int(m) != 6 else str(f.w)
            if str(w) in stop_ws:
                h += 1
    return int(h)


@dataclass(frozen=True)
class ObjSpec:
    key: str
    label: str
    fn: Callable[[dict[str, str], KSpec], tuple[int, ...]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    out_json = cache_dir() / "control_objective_robustness_v1.json"
    out_tex = generated_dir() / "control_objective_robustness.tex"

    cache_key = {"analysis": "control_objective_robustness", "analysis_version": ANALYSIS_VERSION}
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        write_text(out_tex, str(obj["latex"]) + "\n")
        return

    # --------------------------
    # Pre-registered K family
    # --------------------------
    K_list: list[KSpec] = [
        KSpec(
            key="K0_standard",
            label=r"$\{ \mathrm{AUG} \} \cup \{ \mathrm{UAA,UAG,UGA} \}$",
            starts=("AUG",),
            stops=("UAA", "UAG", "UGA"),
        ),
        KSpec(
            key="K1_altstart",
            label=r"$\{ \mathrm{AUG,CUG,GUG,UUG} \} \cup \{ \mathrm{UAA,UAG,UGA} \}$",
            starts=("AUG", "CUG", "GUG", "UUG"),
            stops=("UAA", "UAG", "UGA"),
        ),
        KSpec(
            key="K2_stop_only",
            label=r"$\{ \mathrm{UAA,UAG,UGA} \}$",
            starts=(),
            stops=("UAA", "UAG", "UGA"),
        ),
    ]

    # --------------------------
    # Pre-registered objective family
    # --------------------------
    def obj_A(mu: dict[str, str], K: KSpec) -> tuple[int, ...]:
        # Original objective: maximize boundary hits at m=6.
        return (_score_boundary_hits(mu, K, m=6),)

    def obj_B(mu: dict[str, str], K: KSpec) -> tuple[int, ...]:
        # Lexicographic tie-break: maximize boundary hits, then start–stop boundary homology (m=6).
        return (_score_boundary_hits(mu, K, m=6), _score_homology(mu, K, m=6))

    def obj_C(mu: dict[str, str], K: KSpec) -> tuple[int, ...]:
        # Multi-resolution robustness: maximize total boundary hits across m=6 and m=7.
        return (_score_boundary_hits(mu, K, m=6) + _score_boundary_hits(mu, K, m=7),)

    Obj_list: list[ObjSpec] = [
        ObjSpec(key="A_m6_hits", label=r"max $\sum_{c\in\mathcal{K}}\mathbf{1}\{w_\mu(c)\in X^{\mathrm{bdry}}_6\}$", fn=obj_A),
        ObjSpec(key="B_m6_hits_hom", label=r"lex(max hits, start--stop homology)", fn=obj_B),
        ObjSpec(key="C_m6m7_hits", label=r"max hits at $m=6$+$m=7$", fn=obj_C),
    ]

    encs = all_encodings()

    def solve(K: KSpec, O: ObjSpec) -> dict[str, object]:
        scores = []
        for mu in encs:
            scores.append((O.fn(mu, K), mu))
        best_score = max(s for s, _ in scores)
        argmax = [mu for s, mu in scores if s == best_score]
        M = len(argmax)
        mu_star_in = any(_is_mu_star(mu) for mu in argmax)
        return {
            "best_score": list(best_score),
            "M": int(M),
            "mu_star_in": bool(mu_star_in),
            "mu_star_unique": bool(mu_star_in and M == 1),
            "argmax": [encoding_to_str(mu) for mu in argmax],
            "best": encoding_to_str(argmax[0]) if argmax else None,
        }

    grid = {}
    for K in K_list:
        grid[K.key] = {}
        for O in Obj_list:
            grid[K.key][O.key] = solve(K, O)

    # Additional robustness scan: use K = (starts ∪ stops) for each nonstandard translation table.
    gc_path = root_dir() / "data" / "gc.prt"
    tables = parse_gc_prt(gc_path.read_text(encoding="utf-8"))
    table_scan = {}
    for O in Obj_list:
        n_total = 0
        n_mu_star_unique = 0
        n_mu_star_in = 0
        for t in tables:
            codons = codons_for_table(t)
            starts = tuple(codons[i] for i, aa in enumerate(t.sncbieaa) if aa.upper() == "M")
            stops = tuple(codons[i] for i, aa in enumerate(t.ncbieaa) if aa == "*")
            if not stops:
                continue
            Kt = KSpec(key=f"table_{t.code_id}", label=t.primary_name(), starts=starts, stops=stops)
            r = solve(Kt, O)
            n_total += 1
            if r["mu_star_in"]:
                n_mu_star_in += 1
            if r["mu_star_unique"]:
                n_mu_star_unique += 1
        table_scan[O.key] = {
            "n_tables": int(n_total),
            "mu_star_in": int(n_mu_star_in),
            "mu_star_unique": int(n_mu_star_unique),
        }

    # --------------------------
    # LaTeX fragment
    # --------------------------
    def cell(r: dict[str, object]) -> str:
        M = int(r.get("M", 0) or 0)
        if bool(r.get("mu_star_unique")):
            return r"$\mu^\ast$ (unique)"
        if bool(r.get("mu_star_in")):
            return rf"$\mu^\ast$ (tie; $M={M}$)"
        if M == 1 and r.get("best"):
            return r"\texttt{" + str(r["best"]) + r"} (unique)"
        return rf"not $\mu^\ast$ (tie; $M={M}$)"

    rows = []
    for K in K_list:
        cs = [cell(grid[K.key][O.key]) for O in Obj_list]
        rows.append(K.label + " & " + " & ".join(cs) + r" \\")

    # Summary line for nonstandard tables.
    tbl_lines = []
    for O in Obj_list:
        ts = table_scan.get(O.key, {})
        tbl_lines.append(
            f"{O.key}: mu* in argmax {ts.get('mu_star_in',0)}/{ts.get('n_tables',0)}, unique {ts.get('mu_star_unique',0)}/{ts.get('n_tables',0)}"
        )
    table_summary = "; ".join(tbl_lines)

    tex = []
    tex.append(
        "Protocol robustness check (pre-registered $\\mathcal{K}$ family and objective family; exhaustive scan over 24 encodings)."
    )
    tex.append(r"\begin{center}")
    tex.append(r"\small")
    tex.append(r"\setlength{\tabcolsep}{6pt}")
    tex.append(r"\renewcommand{\arraystretch}{1.20}")
    tex.append(r"\begin{tabular}{l" + "c" * len(Obj_list) + r"}")
    tex.append(r"\toprule")
    tex.append(r"$\mathcal{K}$ variant & " + " & ".join([O.key for O in Obj_list]) + r" \\")
    tex.append(r"\midrule")
    tex.extend(rows)
    tex.append(r"\bottomrule")
    tex.append(r"\end{tabular}")
    tex.append(r"\end{center}")
    tex.append(
        r"\noindent Nonstandard translation tables (NCBI \texttt{gc.prt}) summary: " + table_summary + "."
    )
    latex = "\n".join(tex)

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "K": [{"key": K.key, "label": K.label, "starts": list(K.starts), "stops": list(K.stops)} for K in K_list],
        "Obj": [{"key": O.key, "label": O.label} for O in Obj_list],
        "grid": grid,
        "table_scan": table_scan,
        "latex": latex,
    }
    write_json_atomic(out_json, obj)
    write_json_atomic(cache_meta_path(out_json), expected_meta)
    write_text(out_tex, latex + "\n")
    print(f"Wrote: {out_tex}")
    print(f"Wrote: {out_json}")


if __name__ == "__main__":
    main()

