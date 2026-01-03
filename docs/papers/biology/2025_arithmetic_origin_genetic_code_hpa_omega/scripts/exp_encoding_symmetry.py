# -*- coding: utf-8 -*-
"""
Encoding-level symmetry statistics over the 24 bijective two-bit nucleotide encodings.

This script quantifies a few encoding properties that are *not* used as premises in the
control-boundary identification theorem, but can be reported as emergent structure under
the selected encoding mu*.

Outputs:
  - sections/generated/encoding_symmetry_summary.tex
  - sections/generated/encoding_symmetry_table.tex
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import all_encodings


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Encoding symmetry statistics over all 24 encodings.")
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "encoding_symmetry_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "encoding_symmetry_table.tex"),
        help="Output LaTeX table fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def _bit_not(bits: str) -> str:
    if len(bits) != 2 or any(ch not in "01" for ch in bits):
        raise ValueError(f"Invalid 2-bit string: {bits!r}")
    return ("1" if bits[0] == "0" else "0") + ("1" if bits[1] == "0" else "0")


def _fns(bits: str) -> dict[str, int]:
    b1 = 1 if bits[0] == "1" else 0
    b0 = 1 if bits[1] == "1" else 0
    return {"b1": b1, "b0": b0, "xor": (b1 ^ b0)}


def _separates(mu: dict[str, str], a: set[str], b: set[str], fn: str) -> bool:
    va = {_fns(mu[x])[fn] for x in a}
    vb = {_fns(mu[x])[fn] for x in b}
    if len(va) != 1 or len(vb) != 1:
        return False
    return next(iter(va)) != next(iter(vb))


def _complement_is_bitwise_not(mu: dict[str, str]) -> bool:
    # Watson–Crick complement: A<->U, C<->G.
    return (mu["U"] == _bit_not(mu["A"])) and (mu["G"] == _bit_not(mu["C"]))


def _triple_linear_alignment(mu: dict[str, str]) -> tuple[bool, dict[str, str] | None]:
    # Classical nucleotide dichotomies:
    # - amino/keto:  A,C vs G,U
    # - purine/pyrimidine: A,G vs C,U
    # - weak/strong H-bond: A,U vs C,G
    dich = {
        "amino_keto": ({"A", "C"}, {"G", "U"}),
        "purine_pyrimidine": ({"A", "G"}, {"C", "U"}),
        "weak_strong": ({"A", "U"}, {"C", "G"}),
    }
    fns = ["b1", "b0", "xor"]
    ok: dict[str, list[str]] = {k: [] for k in dich}
    for k, (s1, s2) in dich.items():
        for fn in fns:
            if _separates(mu, s1, s2, fn):
                ok[k].append(fn)
    # Need a one-to-one assignment of distinct fn to the three dichotomies.
    for perm in itertools.permutations(fns, 3):
        mapping = {"amino_keto": perm[0], "purine_pyrimidine": perm[1], "weak_strong": perm[2]}
        if all(mapping[k] in ok[k] for k in dich):
            return True, mapping
    return False, None


def _mu_to_row(mu: dict[str, str]) -> str:
    return f"{mu['A']} & {mu['C']} & {mu['G']} & {mu['U']} \\\\"


def _unique_mapping(mu: dict[str, str]) -> dict[str, str]:
    dich = {
        "amino/keto": ({"A", "C"}, {"G", "U"}),
        "purine/pyrimidine": ({"A", "G"}, {"C", "U"}),
        "weak/strong": ({"A", "U"}, {"C", "G"}),
    }
    fns = ["b1", "b0", "xor"]
    out: dict[str, str] = {}
    for name, (s1, s2) in dich.items():
        hits = [fn for fn in fns if _separates(mu, s1, s2, fn)]
        if len(hits) != 1:
            raise ValueError(f"Expected unique linear function for {name}, got {hits}")
        out[name] = hits[0]
    return out


def _invert_mapping(m: dict[str, str]) -> dict[str, str]:
    inv: dict[str, str] = {}
    for k, v in m.items():
        inv[v] = k
    return inv


def main() -> None:
    args = parse_args()
    out_summary = Path(args.out_summary)
    out_table = Path(args.out_table)

    cache_key = {
        "analysis": "encoding_symmetry",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "out_summary": str(out_summary),
        "out_table": str(out_table),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_summary, expected_meta=cache_meta, require_meta=True) and cache_hit(
        out_table, expected_meta=cache_meta, require_meta=True
    ):
        print(f"[cache] hit: {out_summary}", flush=True)
        return

    encs = list(all_encodings())
    if len(encs) != 24:
        raise SystemExit(f"Expected 24 encodings, got {len(encs)}")

    n_comp = 0
    comp_rows: list[dict[str, object]] = []
    mapping_counts: dict[str, int] = {}
    mapping_counts_comp: dict[str, int] = {}

    mu_star_map_named: dict[str, str] | None = None
    mu_star_map_inv: dict[str, str] | None = None
    for mu in encs:
        comp = _complement_is_bitwise_not(mu)
        if comp:
            n_comp += 1

        m_named = _unique_mapping(mu)
        m_inv = _invert_mapping(m_named)
        key = f"b1={m_inv['b1']}; b0={m_inv['b0']}; xor={m_inv['xor']}"
        mapping_counts[key] = int(mapping_counts.get(key, 0)) + 1
        if comp:
            mapping_counts_comp[key] = int(mapping_counts_comp.get(key, 0)) + 1
            comp_rows.append({"mu": mu, "map_inv": m_inv})

        if mu == MU_STAR:
            mu_star_map_named = m_named
            mu_star_map_inv = m_inv

    if mu_star_map_named is None or mu_star_map_inv is None:
        raise SystemExit("mu* mapping unexpectedly not found")

    # Summary fragment (used in main text).
    # Keep this short and robust against line-breaking.
    mapping_str = f"b1={mu_star_map_inv['b1']}, b0={mu_star_map_inv['b0']}, xor={mu_star_map_inv['xor']}"
    mu_star_key = f"b1={mu_star_map_inv['b1']}; b0={mu_star_map_inv['b0']}; xor={mu_star_map_inv['xor']}"
    same_key = int(mapping_counts.get(mu_star_key, 0))
    same_key_comp = int(mapping_counts_comp.get(mu_star_key, 0))
    summary_lines: list[str] = []
    summary_lines.append(
        "Among the $24$ bijective two-bit encodings, "
        f"{n_comp} satisfy Watson--Crick complement as bitwise negation "
        "($A\\leftrightarrow U$ and $C\\leftrightarrow G$ correspond to $\\texttt{00}\\leftrightarrow\\texttt{11}$ and "
        "$\\texttt{01}\\leftrightarrow\\texttt{10}$). "
        "For every encoding, the three classical nucleotide dichotomies "
        "(amino/keto, purine/pyrimidine, weak/strong) correspond to the three nontrivial linear observables on $\\{0,1\\}^2$ "
        "(the two bits and their XOR), but the assignment to $(b1,b0,\\mathrm{xor})$ depends on the encoding. "
        f"Under $\\mu^\\ast$, the assignment is {mapping_str}; this exact assignment occurs for {same_key}/24 encodings, "
        f"and for {same_key_comp}/{n_comp} among the complement-as-bitwise-negation encodings."
    )
    summary_lines.append("")
    write_text_atomic(out_summary, "\n".join(summary_lines) + "\n")

    # Table fragment: list the encodings that satisfy complement-as-bitwise-negation, together with
    # the induced (b1,b0,xor) assignment (useful for appendix).
    comp_rows.sort(key=lambda r: (str(r["mu"]["A"]), str(r["mu"]["C"]), str(r["mu"]["G"]), str(r["mu"]["U"])))
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{center}")
    lines.append("\\begin{tabular}{lllllll}")
    lines.append("\\toprule")
    lines.append("A & C & G & U & $b1$ & $b0$ & xor \\\\")
    lines.append("\\midrule")
    for r in comp_rows:
        mu = r["mu"]  # type: ignore[assignment]
        m_inv = r["map_inv"]  # type: ignore[assignment]
        lines.append(
            f"{mu['A']} & {mu['C']} & {mu['G']} & {mu['U']} & {m_inv['b1']} & {m_inv['b0']} & {m_inv['xor']} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("\\endgroup")
    lines.append("")
    write_text_atomic(out_table, "\n".join(lines) + "\n")

    write_json_atomic(cache_meta_path(out_summary), cache_meta)
    write_json_atomic(cache_meta_path(out_table), cache_meta)
    print("Wrote:", out_summary)
    print("Wrote:", out_table)


if __name__ == "__main__":
    main()


