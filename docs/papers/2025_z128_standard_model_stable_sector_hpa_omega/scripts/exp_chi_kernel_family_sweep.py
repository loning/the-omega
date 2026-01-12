# -*- coding: utf-8 -*-
"""
Kernel-family sweep for chi reconstruction (audit generator).

This script audits the sensitivity of the reconstructed chi(r) field statistics
to a finite readout-kernel family used in the window-level aggregator.

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Writes LaTeX fragments into sections/generated/.
  - Uses only the small vendored data subsets under data/gamma_crossobs/.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import List

import numpy as np

import exp_gamma_kernel_family_sweep as gks
import exp_gamma_cross_observation as gx
from common_paths import generated_dir, paper_root
from common_progress import ProgressEvery
from common_tex import write_lines


@dataclass(frozen=True)
class ChiKernelRow:
    t: Fraction
    n_gal: int
    mean_std_chi: float
    mean_abs_chi: float
    note: str


def _format_cell_sci(x: float, digits: int = 6) -> str:
    if not np.isfinite(x):
        return r"\texttt{nan}"
    return f"{x:.{digits}g}"


def _iter_sparc_files() -> List[str]:
    sparc_dir = paper_root() / "data" / "gamma_crossobs" / "sparc"
    manifest = gx._read_json(sparc_dir / "manifest.json")
    files = [str(x["path"]) for x in manifest.get("files", []) if "path" in x]
    if not files:
        raise RuntimeError("SPARC manifest contains no files.")
    return files


def main() -> int:
    out_gen = generated_dir()
    out_gen.mkdir(parents=True, exist_ok=True)

    m_word = 6
    thr_rule = "median"
    base_rule = "mean"

    t_grid: List[Fraction] = [
        Fraction(0, 1),
        Fraction(1, 4),
        Fraction(1, 2),
        Fraction(3, 4),
        Fraction(1, 1),
    ]

    sparc_dir = paper_root() / "data" / "gamma_crossobs" / "sparc"
    sparc_files = _iter_sparc_files()

    rows: List[ChiKernelRow] = []
    prog = ProgressEvery("chi kernel-family sweep", total=len(t_grid) * len(sparc_files), interval_s=60.0)
    prog.start()

    for ti, t in enumerate(t_grid):
        stds: List[float] = []
        means_abs: List[float] = []
        n_gal = 0
        for fi, fn in enumerate(sparc_files):
            p = sparc_dir / fn
            gname = fn.replace("_rotmod.dat", "")
            dat = gx._parse_sparc_rotmod(p)
            scalar = np.asarray(dat["sbdisk_l_pc2"], dtype=float)
            r_kpc = np.asarray(dat["r_kpc"], dtype=float)
            if len(r_kpc) < (2 * m_word - 1):
                prog.maybe(ti * len(sparc_files) + fi + 1, extra=f"t={t} galaxy={gname} SKIP")
                continue

            recon = gks.reconstruct_chi_from_1d_scalar_kernel(
                r_kpc=r_kpc,
                scalar=scalar,
                m=m_word,
                threshold_rule=thr_rule,
                baseline_rule=base_rule,
                t=t,
            )
            chi = np.asarray(recon.chi, dtype=float)
            if chi.size < 3:
                prog.maybe(ti * len(sparc_files) + fi + 1, extra=f"t={t} galaxy={gname} SKIP (short)")
                continue
            if not np.all(np.isfinite(chi)):
                prog.maybe(ti * len(sparc_files) + fi + 1, extra=f"t={t} galaxy={gname} SKIP (nan)")
                continue

            stds.append(float(np.std(chi)))
            means_abs.append(float(np.mean(np.abs(chi))))
            n_gal += 1
            prog.maybe(ti * len(sparc_files) + fi + 1, extra=f"t={t} galaxy={gname}")

        mean_std = float(np.mean(stds)) if stds else float("nan")
        mean_abs = float(np.mean(means_abs)) if means_abs else float("nan")
        rows.append(
            ChiKernelRow(
                t=t,
                n_gal=int(n_gal),
                mean_std_chi=mean_std,
                mean_abs_chi=mean_abs,
                note="SBdisk 1D specialization; kernel-weighted degeneracy aggregator",
            )
        )

    prog.done()

    tex_rows: List[str] = []
    for r in rows:
        t_tex = f"{r.t.numerator}/{r.t.denominator}" if r.t.denominator != 1 else f"{r.t.numerator}"
        tex_rows.append(
            " & ".join(
                [
                    f"${t_tex}$",
                    f"{int(r.n_gal)}",
                    _format_cell_sci(r.mean_std_chi),
                    _format_cell_sci(r.mean_abs_chi),
                    gx._tex_escape(r.note),
                ]
            )
            + r" \\"
        )
    tex_rows.append(r"\bottomrule")
    write_lines(out_gen / "chi_kernel_family_sweep_rows.tex", tex_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

