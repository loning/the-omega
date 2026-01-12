# -*- coding: utf-8 -*-
"""
Kernel-family sweep for the direct gamma_dict calibration (audit generator).

This script complements `exp_gamma_cross_observation.py` by auditing how the
direct rotation-curve estimate of gamma_dict changes under a finite family of
readout kernels used inside the chi reconstruction aggregator.

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Writes LaTeX fragments into sections/generated/.
  - Uses only the small vendored data subsets under data/gamma_crossobs/.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np

import exp_foldm_stats as foldm
import exp_gamma_cross_observation as gx
import protocol_state_selection as psel
from common_paths import generated_dir, paper_root
from common_progress import ProgressEvery
from common_tex import write_lines


@dataclass(frozen=True)
class KernelSweepRow:
    t: Fraction
    n_gal: int
    gamma_joint: float
    sigma_joint: float
    gamma_min_gal: float
    gamma_max_gal: float
    d_joint: float
    note: str


def _format_cell_sci(x: float, digits: int = 6) -> str:
    if not np.isfinite(x):
        return r"\texttt{nan}"
    return f"{x:.{digits}g}"


def _format_pm(mu: float, sig: float, digits: int = 6) -> str:
    return f"${_format_cell_sci(mu, digits=digits)}\\pm{_format_cell_sci(sig, digits=digits)}$"


def _inverse_variance_combine(estimates: Sequence[gx.GammaEstimate]) -> Tuple[float, float]:
    xs = [e for e in estimates if np.isfinite(e.gamma_hat) and np.isfinite(e.sigma) and e.sigma > 0]
    if not xs:
        return float("nan"), float("nan")
    w = np.asarray([1.0 / (e.sigma * e.sigma) for e in xs], dtype=float)
    g = np.asarray([e.gamma_hat for e in xs], dtype=float)
    wsum = float(np.sum(w))
    if wsum <= 0:
        return float("nan"), float("nan")
    mu = float(np.sum(w * g) / wsum)
    sig = float(math.sqrt(1.0 / wsum))
    return mu, sig


def _weighted_mean(x: np.ndarray, w: np.ndarray) -> float:
    ww = np.asarray(w, dtype=float)
    xx = np.asarray(x, dtype=float)
    s = float(np.sum(ww))
    if not (s > 0.0):
        return float(np.mean(xx))
    return float(np.sum(ww * xx) / s)


def reconstruct_chi_from_1d_scalar_kernel(
    *,
    r_kpc: np.ndarray,
    scalar: np.ndarray,
    m: int,
    threshold_rule: str,
    baseline_rule: str,
    t: Fraction,
) -> gx.ChiReconstruction:
    """
    Variant of `gx.reconstruct_chi_from_1d_scalar` where the window-local
    degeneracy proxy uses a kernel-weighted mean:

      gbar_t(s) := sum_j g_j * w_j / sum_j w_j,   w_j := g_j^t

    with t taken from a finite rational grid.
    """
    if r_kpc.shape != scalar.shape:
        raise ValueError("r_kpc and scalar must have the same shape.")
    if m < 2:
        raise ValueError("m must be >= 2.")

    n = int(len(r_kpc))
    if n < (2 * m - 1):
        raise ValueError(f"Need at least 2m-1 samples (n={n}, m={m}).")

    tau = gx._threshold(scalar, threshold_rule)
    bits = (scalar >= tau).astype(int)

    gm_map = foldm.cached_degeneracy_map(m)

    def g_of_int(N: int) -> int:
        w_stable = foldm.foldm(int(N), m)
        return int(gm_map[w_stable])

    N_s = np.zeros(n - m + 1, dtype=int)
    for s in range(n - m + 1):
        N_s[s] = gx._binary_word_int(bits[s : s + m])

    g_s = np.asarray([g_of_int(int(x)) for x in N_s], dtype=float)

    # Window-local aggregator (kernel-dependent).
    tt = float(t.numerator) / float(t.denominator)
    gbar: List[float] = []
    for s in range(len(g_s) - m + 1):
        w = np.power(g_s[s : s + m], tt, dtype=float)
        gbar.append(_weighted_mean(g_s[s : s + m], w))
    gbar_arr = np.asarray(gbar, dtype=float)

    g0 = gx._baseline(gbar_arr, baseline_rule)
    if not (g0 > 0.0):
        raise AssertionError("Baseline g0 must be positive.")

    chi = np.log(gbar_arr / g0)
    center_idx = np.arange(m - 1, m - 1 + len(chi), dtype=int)
    r_mid = r_kpc[center_idx]

    return gx.ChiReconstruction(
        r_kpc=r_mid,
        chi=chi,
        center_idx=center_idx,
        m=m,
        threshold_rule=threshold_rule,
        baseline_rule=baseline_rule,
        g0=g0,
    )


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

    # Match the baseline knobs used in exp_gamma_cross_observation.py, but align m to the
    # joint protocol-state selection when available.
    try:
        sel = psel.load_selected_state("gamma_direct")
        m_word = int(sel.m)
    except Exception:
        m_word = 6
    thr_rule = "median"
    base_rule = "mean"
    smooth_k = 5  # odd

    # Finite kernel family (tempered degeneracy weights).
    t_grid: List[Fraction] = [
        Fraction(0, 1),
        Fraction(1, 4),
        Fraction(1, 2),
        Fraction(3, 4),
        Fraction(1, 1),
    ]

    sparc_dir = paper_root() / "data" / "gamma_crossobs" / "sparc"
    sparc_files = _iter_sparc_files()

    rows: List[KernelSweepRow] = []
    baseline_gamma: float | None = None

    prog = ProgressEvery("gamma kernel-family sweep", total=len(t_grid) * len(sparc_files), interval_s=60.0)
    prog.start()

    for ti, t in enumerate(t_grid):
        rc_est: List[gx.GammaEstimate] = []
        for fi, fn in enumerate(sparc_files):
            p = sparc_dir / fn
            gname = fn.replace("_rotmod.dat", "")
            dat = gx._parse_sparc_rotmod(p)

            scalar = np.asarray(dat["sbdisk_l_pc2"], dtype=float)
            r_kpc = np.asarray(dat["r_kpc"], dtype=float)
            if len(r_kpc) < (2 * m_word - 1):
                prog.maybe(ti * len(sparc_files) + fi + 1, extra=f"t={t} galaxy={gname} SKIP")
                continue

            recon = reconstruct_chi_from_1d_scalar_kernel(
                r_kpc=r_kpc,
                scalar=scalar,
                m=m_word,
                threshold_rule=thr_rule,
                baseline_rule=base_rule,
                t=t,
            )
            fit = gx.fit_gamma_from_rotation_curve(
                galaxy=gname,
                r_kpc_full=r_kpc,
                vobs_kms_full=np.asarray(dat["vobs_kms"], dtype=float),
                verr_kms_full=np.asarray(dat["verr_kms"], dtype=float),
                chi_recon=recon,
                smooth_k=smooth_k,
            )
            if np.isfinite(fit.gamma_hat) and np.isfinite(fit.sigma) and float(fit.sigma) > 0.0:
                rc_est.append(
                    gx.GammaEstimate(
                        channel="rotation_curves_sparc",
                        dataset=fit.galaxy,
                        gamma_hat=float(fit.gamma_hat),
                        sigma=float(fit.sigma),
                        note=(
                            f"kernel-weighted chi: t={t.numerator}/{t.denominator}, "
                            f"m={fit.recon.m}, thr={fit.recon.threshold_rule}, g0={fit.recon.baseline_rule}, "
                            f"smooth_k={fit.smooth_k}, used={fit.n_used}/{fit.n_total}"
                        ),
                        source="SPARC rotmod subset (see data/gamma_crossobs/sparc/manifest.json)",
                    )
                )
            prog.maybe(ti * len(sparc_files) + fi + 1, extra=f"t={t} galaxy={gname}")

        prog.maybe((ti + 1) * len(sparc_files), extra=f"t={t} n_gal={len(rc_est)}")

        gamma_joint, sigma_joint = _inverse_variance_combine(rc_est)
        gvals = [e.gamma_hat for e in rc_est if np.isfinite(e.gamma_hat)]
        gmin = float(min(gvals)) if gvals else float("nan")
        gmax = float(max(gvals)) if gvals else float("nan")

        if baseline_gamma is None and t == Fraction(0, 1):
            baseline_gamma = float(gamma_joint)
        d_joint = float(abs(gamma_joint - baseline_gamma)) if (baseline_gamma is not None) else float("nan")

        rows.append(
            KernelSweepRow(
                t=t,
                n_gal=len(rc_est),
                gamma_joint=float(gamma_joint),
                sigma_joint=float(sigma_joint),
                gamma_min_gal=gmin,
                gamma_max_gal=gmax,
                d_joint=d_joint,
                note="tempered degeneracy kernel in chi aggregator; proxy channels unchanged",
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
                    _format_pm(r.gamma_joint, r.sigma_joint),
                    _format_cell_sci(r.d_joint),
                    _format_cell_sci(r.gamma_min_gal),
                    _format_cell_sci(r.gamma_max_gal),
                    gx._tex_escape(r.note),
                ]
            )
            + r" \\"
        )
    tex_rows.append(r"\bottomrule")

    write_lines(out_gen / "gamma_crossobs_direct_kernel_family_rows.tex", tex_rows)
    print(
        "[protocol_state] Gamma kernel-family sweep (direct): "
        "scan a finite tempered degeneracy-kernel family K_t inside the chi-aggregator "
        "(t in a fixed rational grid), holding the dataset and proxy channels fixed; "
        "report the resulting sensitivity envelope for the direct gamma_dict estimate."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

