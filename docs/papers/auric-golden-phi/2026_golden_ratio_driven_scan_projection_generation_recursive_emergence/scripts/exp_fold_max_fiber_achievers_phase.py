#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Max-fiber achievers (phase structure) for Fold_m via modular DP.

Recall (proved in the paper) the congruence characterization:
  Fold_m(omega)=Fold_m(omega')  <->  N(omega) ≡ N(omega') (mod F_{m+2}),
and define residue counts:
  c_m(r) = #{ omega in {0,1}^m : N(omega) ≡ r (mod F_{m+2}) }.
Then for the unique stable type x with V_m(x)=r we have d_m(x)=c_m(r), hence
  D_m := max_x d_m(x) = max_r c_m(r),
and the number of maximizers equals #{r: c_m(r)=D_m}.

This script computes, for m<=M:
  - D_m (closed form, for consistency check),
  - D_m (DP),
  - kappa_m := #{ maximizers },
  - representative maximizer stable words (Zeckendorf/greedy map r -> x in X_m).

Outputs:
  - artifacts/export/fold_max_fiber_achievers_phase.json
  - sections/generated/tab_fold_max_fiber_achievers_phase.tex

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import numpy as np

from common_paths import export_dir, generated_dir
from common_phi_fold import Progress


def fib_upto(n: int) -> List[int]:
    if n < 0:
        raise ValueError("n must be >= 0")
    F = [0, 1]
    for _ in range(2, n + 1):
        F.append(F[-1] + F[-2])
    return F[: n + 1]


def D_closed(m: int) -> int:
    if m < 2:
        raise ValueError("m must be >= 2")
    F = fib_upto((m // 2) + 2)
    if m % 2 == 0:
        k = m // 2
        return int(F[k + 2])
    # odd: D_{2k+1} = 2F_{k+1}
    k = (m - 1) // 2
    return int(2 * F[k + 1])


def counts_mod_fib(m: int, prog: Progress | None = None) -> np.ndarray:
    """Compute residue counts c_m(r) for modulus F_{m+2}."""
    if m < 0:
        raise ValueError("m must be >= 0")
    F = fib_upto(m + 2)
    mod = F[m + 2]
    c = np.zeros(mod, dtype=np.uint64)
    c[0] = 1
    for i in range(1, m + 1):
        w = F[i + 1]
        c = c + np.roll(c, w)
        if prog is not None:
            prog.tick(f"maxfiber m={m} step={i}/{m} mod={mod}")
    return c


def zeckendorf_word(m: int, r: int) -> str:
    """
    Return the unique x in X_m (no adjacent 11) with value V_m(x)=r,
    where V_m(x)=sum_{k=1}^m x_k F_{k+1} and 0<=r<F_{m+2}.
    """
    if m < 1:
        raise ValueError("m must be >= 1")
    F = fib_upto(m + 2)
    if r < 0 or r >= F[m + 2]:
        raise ValueError("r out of range for modulus F_{m+2}")

    rem = int(r)
    x = [0] * m
    prev_one = False  # track adjacency on descending greedy (higher index is next)
    for k in range(m, 0, -1):
        w = F[k + 1]
        if (not prev_one) and rem >= w:
            x[k - 1] = 1
            rem -= w
            prev_one = True
        else:
            x[k - 1] = 0
            prev_one = False
    if rem != 0:
        raise ValueError("Greedy Zeckendorf failed to exhaust remainder")
    # sanity: no adjacent 11
    for i in range(m - 1):
        if x[i] == 1 and x[i + 1] == 1:
            raise ValueError("Adjacent 11 produced (should not happen)")
    return "".join(str(b) for b in x)


@dataclass(frozen=True)
class Row:
    m: int
    D_closed: int
    D_dp: int
    kappa: int
    residues: List[int]
    words: List[str]


def write_table_tex(path: Path, rows: List[Row]) -> None:
    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Max-fiber achiever multiplicity for Fold$_m$ via modular DP. "
        "$\\kappa_m$ counts the number of stable types $x\\in X_m$ attaining $d_m(x)=D_m$. "
        "Equivalently, $\\kappa_m=\\#\\{r\\in\\mathbb{Z}/F_{m+2}\\mathbb{Z}: c_m(r)=D_m\\}$ for residue counts $c_m$. "
        "Representative maximizers are shown only for the largest $m$ in the window.}"
    )
    lines.append("\\label{tab:fold_max_fiber_achievers_phase}")
    lines.append("\\begin{tabular}{r r r r l}")
    lines.append("\\toprule")
    lines.append("$m$ & $D_m$ (closed) & $D_m$ (DP) & $\\kappa_m$ & representative maximizers\\\\")
    lines.append("\\midrule")
    m_max = max(r.m for r in rows) if rows else 0
    show_ms = {m_max, m_max - 1} if m_max >= 3 else {m_max}
    for r in rows:
        if r.m in show_ms:
            ex = ",\\;".join([f"\\texttt{{{w}}}" for w in r.words])
        else:
            ex = "--"
        lines.append(f"{r.m} & {r.D_closed} & {r.D_dp} & {r.kappa} & {ex}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Max-fiber achievers and phase representatives (m<=M).")
    parser.add_argument("--m-min", type=int, default=2)
    parser.add_argument("--m-max", type=int, default=30)
    parser.add_argument("--show-words", type=int, default=4, help="How many maximizer words to record per m.")
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "fold_max_fiber_achievers_phase.json"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_fold_max_fiber_achievers_phase.tex"),
    )
    args = parser.parse_args()

    if args.m_min < 2 or args.m_max < args.m_min:
        raise SystemExit("Require m_max >= m_min >= 2")
    if args.show_words < 1:
        raise SystemExit("Require --show-words >= 1")

    prog = Progress("fold-max-fiber-achievers", every_seconds=20.0)

    rows: List[Row] = []
    for m in range(args.m_min, args.m_max + 1):
        c = counts_mod_fib(m, prog=prog)
        Ddp = int(np.max(c))
        residues = np.flatnonzero(c == Ddp).astype(int).tolist()
        kappa = int(len(residues))

        Dc = D_closed(m)
        if Ddp != Dc:
            raise ValueError(f"D mismatch at m={m}: DP={Ddp}, closed={Dc}")

        # Representative words (by smallest residues)
        residues_sorted = sorted(residues)[: args.show_words]
        words = [zeckendorf_word(m, r) for r in residues_sorted]

        rows.append(
            Row(
                m=m,
                D_closed=Dc,
                D_dp=Ddp,
                kappa=kappa,
                residues=residues_sorted,
                words=words,
            )
        )
        print(f"[fold-max-fiber] m={m} mod={len(c)} D={Ddp} kappa={kappa}", flush=True)

    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    payload = {"m_min": int(args.m_min), "m_max": int(args.m_max), "rows": [asdict(r) for r in rows]}
    jout.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[fold-max-fiber] wrote {jout}", flush=True)

    tout = Path(args.tex_out)
    write_table_tex(tout, rows)
    print(f"[fold-max-fiber] wrote {tout}", flush=True)


if __name__ == "__main__":
    main()

