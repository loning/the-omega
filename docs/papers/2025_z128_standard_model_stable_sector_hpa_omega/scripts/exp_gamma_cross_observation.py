# -*- coding: utf-8 -*-
"""
Gamma cross-observation consistency (audit generator).

This script implements a reproducible, auditable "multi-channel" estimate of the
single parameter gamma appearing in the overhead-to-lapse dictionary

  N = exp(-gamma * chi)

and in the weak-field proxy

  Phi = -gamma c^2 (chi - chi0).

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Writes LaTeX fragments into sections/generated/ and an optional figure into figures/.
  - Uses only the small vendored data subsets under data/gamma_crossobs/.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from scipy import stats

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import exp_foldm_stats as foldm
from common_paths import figures_dir, generated_dir, paper_root
from common_progress import ProgressEvery
from common_tex import write_lines


# Physical constant used only as a unit bridge for the rotation-curve proxy.
C_KM_S: float = 299_792.458

# Reference cosmology summary used only to form a compact time-delay proxy.
# Planck 2018 (TT,TE,EE+lowE+lensing) in flat LCDM: H0 = 67.4 ± 0.5 km/s/Mpc.
PLANCK18_H0_KM_S_MPC: float = 67.4
PLANCK18_H0_SIGMA_KM_S_MPC: float = 0.5

# Late-time distance-ladder reference used only as a bounded sensitivity diagnostic
# for the same time-delay proxy map (kept separate from the baseline joint estimate).
# SH0ES (Riess et al. 2019): H0 = 74.03 ± 1.42 km/s/Mpc.
SH0ES19_H0_KM_S_MPC: float = 74.03
SH0ES19_H0_SIGMA_KM_S_MPC: float = 1.42


@dataclass(frozen=True)
class GammaEstimate:
    channel: str
    dataset: str
    gamma_hat: float
    sigma: float
    note: str
    source: str

    def weight(self) -> float:
        if self.sigma <= 0:
            return 0.0
        return 1.0 / (self.sigma * self.sigma)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_data_lines(path: Path) -> Iterable[str]:
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        yield s


def _parse_sparc_rotmod(path: Path) -> dict[str, np.ndarray]:
    """
    Parse a SPARC *_rotmod.dat file.

    Expected columns (whitespace-separated):
      Rad  Vobs  errV  Vgas  Vdisk  Vbul  SBdisk  SBbul
    """
    cols: List[List[float]] = [[] for _ in range(8)]
    for s in _iter_data_lines(path):
        parts = s.split()
        if len(parts) < 8:
            continue
        for i in range(8):
            cols[i].append(float(parts[i]))
    arr = [np.asarray(c, dtype=float) for c in cols]
    return {
        "r_kpc": arr[0],
        "vobs_kms": arr[1],
        "verr_kms": arr[2],
        "vgas_kms": arr[3],
        "vdisk_kms": arr[4],
        "vbul_kms": arr[5],
        "sbdisk_l_pc2": arr[6],
        "sbbul_l_pc2": arr[7],
    }


def _binary_word_int(bits: Sequence[int]) -> int:
    # Standard MSB-first binary-to-integer map: int('b0...b_{m-1}', 2).
    n = 0
    for b in bits:
        n = (n << 1) | int(bool(b))
    return int(n)


def _threshold(values: np.ndarray, rule: str) -> float:
    if rule == "median":
        return float(np.median(values))
    if rule.startswith("quantile:"):
        q = float(rule.split(":", 1)[1])
        return float(np.quantile(values, q))
    if rule == "zero":
        return 0.0
    raise ValueError(f"Unknown threshold rule: {rule}")


def _baseline(values: np.ndarray, rule: str) -> float:
    if rule == "mean":
        return float(np.mean(values))
    if rule == "median":
        return float(np.median(values))
    raise ValueError(f"Unknown baseline rule: {rule}")


def _moving_average(x: np.ndarray, k: int) -> np.ndarray:
    if k <= 1:
        return x.copy()
    if k % 2 == 0:
        raise ValueError("moving-average window k must be odd.")
    pad = k // 2
    xp = np.pad(x, (pad, pad), mode="edge")
    w = np.ones(k, dtype=float) / float(k)
    return np.convolve(xp, w, mode="valid")


@dataclass(frozen=True)
class ChiReconstruction:
    r_kpc: np.ndarray
    chi: np.ndarray
    # Map chi indices back to original radial indices (for joining with vobs).
    center_idx: np.ndarray
    # Audit objects
    m: int
    threshold_rule: str
    baseline_rule: str
    g0: float


def reconstruct_chi_from_1d_scalar(
    *,
    r_kpc: np.ndarray,
    scalar: np.ndarray,
    m: int,
    threshold_rule: str,
    baseline_rule: str,
) -> ChiReconstruction:
    """
    Minimal 1D specialization of Appendix 29 (chi reconstruction protocol).

    - We treat the ordered radial samples as an index axis (no 2D Hilbert map).
    - Words are formed by thresholding the scalar statistic on length-m windows.
    - For each word index N we compute g_m(N) := |Fold_m^{-1}(Fold_m(N))|.
    - We then form a window-local mean degeneracy proxy and take chi = log(bar_g/g0).
    """
    if r_kpc.shape != scalar.shape:
        raise ValueError("r_kpc and scalar must have the same shape.")
    if m < 2:
        raise ValueError("m must be >= 2.")
    n = int(len(r_kpc))
    if n < (2 * m - 1):
        raise ValueError(f"Need at least 2m-1 samples (n={n}, m={m}).")

    tau = _threshold(scalar, threshold_rule)
    bits = (scalar >= tau).astype(int)

    # Precompute g_m(N) via Fold_m and the cached degeneracy map gm[w]=|preimage|.
    gm_map = foldm.cached_degeneracy_map(m)

    def g_of_int(N: int) -> int:
        w_stable = foldm.foldm(int(N), m)
        return int(gm_map[w_stable])

    # Words start positions: 0..n-m
    N_s = np.zeros(n - m + 1, dtype=int)
    for s in range(n - m + 1):
        N_s[s] = _binary_word_int(bits[s : s + m])

    g_s = np.asarray([g_of_int(int(x)) for x in N_s], dtype=float)

    # Window-local mean degeneracy proxy uses g_s[s:s+m] => s in 0..len(g_s)-m
    gbar = np.convolve(g_s, np.ones(m, dtype=float) / float(m), mode="valid")
    g0 = _baseline(gbar, baseline_rule)
    if not (g0 > 0.0):
        raise AssertionError("Baseline g0 must be positive.")

    chi = np.log(gbar / g0)
    center_idx = np.arange(m - 1, m - 1 + len(chi), dtype=int)
    r_mid = r_kpc[center_idx]

    return ChiReconstruction(
        r_kpc=r_mid,
        chi=chi,
        center_idx=center_idx,
        m=m,
        threshold_rule=threshold_rule,
        baseline_rule=baseline_rule,
        g0=g0,
    )


@dataclass(frozen=True)
class RotationCurveFit:
    galaxy: str
    gamma_hat: float
    sigma: float
    chi2_red: float
    n_used: int
    n_total: int
    frac_used: float
    recon: ChiReconstruction
    smooth_k: int
    note: str


def fit_gamma_from_rotation_curve(
    *,
    galaxy: str,
    r_kpc_full: np.ndarray,
    vobs_kms_full: np.ndarray,
    verr_kms_full: np.ndarray,
    chi_recon: ChiReconstruction,
    smooth_k: int,
) -> RotationCurveFit:
    """
    Appendix 28 WLS estimator:
      y_i := v_i^2, x_i := -c^2 r_i chi'(r_i),
      gamma_hat = sum(w_i x_i y_i) / sum(w_i x_i^2),
      w_i = 1/sigma_{y,i}^2, sigma_{y,i} ≈ 2 v_i sigma_i.
    """
    if smooth_k % 2 == 0:
        raise ValueError("smooth_k must be odd.")

    r = chi_recon.r_kpc
    chi = _moving_average(chi_recon.chi, smooth_k)
    dchi_dr = np.gradient(chi, r)

    idx = chi_recon.center_idx
    v = vobs_kms_full[idx]
    sv = verr_kms_full[idx]

    y = v * v
    sy = np.maximum(1e-12, 2.0 * np.abs(v) * np.maximum(1e-12, sv))
    w = 1.0 / (sy * sy)

    x = -(C_KM_S * C_KM_S) * r * dchi_dr

    # Enforce the sign convention: in the weak-field dictionary, physical fits use x>0.
    mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0.0) & (x > 0.0)
    n_total = int(len(x))
    n_used = int(np.sum(mask))
    frac = float(n_used) / float(n_total) if n_total else 0.0

    if n_used < 3:
        return RotationCurveFit(
            galaxy=galaxy,
            gamma_hat=float("nan"),
            sigma=float("nan"),
            chi2_red=float("nan"),
            n_used=n_used,
            n_total=n_total,
            frac_used=frac,
            recon=chi_recon,
            smooth_k=smooth_k,
            note="insufficient positive-design points (x>0) after filtering",
        )

    x_m = x[mask]
    y_m = y[mask]
    w_m = w[mask]

    denom = float(np.sum(w_m * x_m * x_m))
    if denom <= 0.0:
        return RotationCurveFit(
            galaxy=galaxy,
            gamma_hat=float("nan"),
            sigma=float("nan"),
            chi2_red=float("nan"),
            n_used=n_used,
            n_total=n_total,
            frac_used=frac,
            recon=chi_recon,
            smooth_k=smooth_k,
            note="non-positive WLS denom",
        )

    num = float(np.sum(w_m * x_m * y_m))
    gamma_hat = num / denom

    # Base (ideal-design) variance proxy (Appendix 33), then inflate by reduced chi^2
    # to reflect model mismatch / x-noise (errors-in-variables).
    sigma_ideal = math.sqrt(1.0 / denom)
    resid = y_m - gamma_hat * x_m
    chi2 = float(np.sum((resid / sy[mask]) ** 2))
    dof = max(1, n_used - 1)
    chi2_red = chi2 / float(dof)
    sigma = float(math.sqrt(max(0.0, chi2_red)) * sigma_ideal)

    return RotationCurveFit(
        galaxy=galaxy,
        gamma_hat=float(gamma_hat),
        sigma=float(sigma),
        chi2_red=float(chi2_red),
        n_used=n_used,
        n_total=n_total,
        frac_used=frac,
        recon=chi_recon,
        smooth_k=smooth_k,
        note="WLS on v^2 = gamma * (-c^2 r chi') using x>0 points only",
    )


def _combine_inverse_variance(estimates: Sequence[GammaEstimate]) -> Optional[GammaEstimate]:
    xs = [e for e in estimates if np.isfinite(e.gamma_hat) and np.isfinite(e.sigma) and e.sigma > 0]
    if not xs:
        return None
    w = np.asarray([e.weight() for e in xs], dtype=float)
    g = np.asarray([e.gamma_hat for e in xs], dtype=float)
    wsum = float(np.sum(w))
    if wsum <= 0.0:
        return None
    mu = float(np.sum(w * g) / wsum)
    sig = math.sqrt(1.0 / wsum)
    return GammaEstimate(
        channel=xs[0].channel,
        dataset="combined",
        gamma_hat=mu,
        sigma=sig,
        note=f"inverse-variance combine of {len(xs)} sub-estimates",
        source="; ".join(sorted({e.source for e in xs})),
    )


def _chi2_consistency(estimates: Sequence[GammaEstimate], gamma_ref: float) -> Tuple[float, int, float]:
    xs = [e for e in estimates if np.isfinite(e.gamma_hat) and np.isfinite(e.sigma) and e.sigma > 0]
    if len(xs) < 2:
        return float("nan"), 0, float("nan")
    chi2 = 0.0
    for e in xs:
        chi2 += ((e.gamma_hat - gamma_ref) / e.sigma) ** 2
    dof = len(xs) - 1
    p = float(stats.chi2.sf(chi2, dof)) if dof > 0 else float("nan")
    return float(chi2), int(dof), float(p)


def _pairwise_max_z(estimates: Sequence[GammaEstimate]) -> Tuple[float, str]:
    xs = [e for e in estimates if np.isfinite(e.gamma_hat) and np.isfinite(e.sigma) and e.sigma > 0]
    best = -1.0
    best_pair = ""
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            denom = math.sqrt(xs[i].sigma * xs[i].sigma + xs[j].sigma * xs[j].sigma)
            if denom <= 0:
                continue
            z = abs(xs[i].gamma_hat - xs[j].gamma_hat) / denom
            if z > best:
                best = z
                best_pair = f"{xs[i].channel}/{xs[i].dataset} vs {xs[j].channel}/{xs[j].dataset}"
    return float(best), best_pair


def _tex_escape(s: str) -> str:
    # Minimal escaping for table cells.
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
    )


def _format_sci_tex(x: float, digits: int = 6) -> str:
    if not np.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    s = f"{x:.{max(1, digits)}e}"
    mant, exp = s.split("e")
    e = int(exp)
    if e == 0:
        return mant
    return f"{mant}\\times 10^{{{e}}}"


def _format_pm(x: float, s: float) -> str:
    # Keep the representation stable for very small/large values.
    return f"${_format_sci_tex(x, digits=6)} \\pm {_format_sci_tex(s, digits=6)}$"


def _format_cell_sci(x: float) -> str:
    return f"${_format_sci_tex(x, digits=6)}$"


def main() -> None:
    root = paper_root()
    data_root = root / "data" / "gamma_crossobs"
    out_gen = generated_dir()
    out_fig = figures_dir()
    out_gen.mkdir(parents=True, exist_ok=True)
    out_fig.mkdir(parents=True, exist_ok=True)

    # ----------------------------
    # 1) Solar-system constraints
    # ----------------------------
    solar = _read_json(data_root / "solar_system" / "constraints.json")["constraints"]
    solar_est: List[GammaEstimate] = []
    for c in solar:
        obs = str(c["observable"])
        val = float(c["value"])
        sig = float(c["sigma"])
        src = str(c.get("source", ""))
        ds = str(c["id"])
        if obs == "ppn_gamma":
            # PPN: Shapiro delay / light deflection scale with (1 + gamma_PPN).
            gamma_hat = 0.5 * (1.0 + val)
            sigma = 0.5 * sig
            note = "map: gamma_dict := (1+gamma_PPN)/2"
        elif obs == "redshift_alpha":
            # Redshift test: (1+alpha) is a fractional amplitude deviation.
            gamma_hat = 1.0 + val
            sigma = sig
            note = "map: gamma_dict := 1+alpha"
        else:
            raise ValueError(f"Unknown solar observable: {obs}")
        solar_est.append(
            GammaEstimate(
                channel=str(c["channel"]),
                dataset=ds,
                gamma_hat=float(gamma_hat),
                sigma=float(sigma),
                note=note,
                source=src,
            )
        )

    # ----------------------------
    # 2) Weak lensing map proxy (CMB lensing amplitude A_L)
    # ----------------------------
    wl = _read_json(data_root / "weak_lensing" / "cmb_lensing_amplitude.json")["measurements"]
    wl_est: List[GammaEstimate] = []
    wl_est_alt: List[GammaEstimate] = []
    for m in wl:
        A = float(m["value"])
        sA = float(m["sigma"])
        if A <= 0:
            continue
        gamma_hat = math.sqrt(A)
        sigma = sA / (2.0 * math.sqrt(A))
        wl_est.append(
            GammaEstimate(
                channel=str(m["channel"]),
                dataset=str(m["id"]),
                gamma_hat=float(gamma_hat),
                sigma=float(sigma),
                note="map: gamma_dict := sqrt(A_L) (amplitude proxy)",
                source=str(m.get("source", "")),
            )
        )
        # Bounded counterfactual mapping (sensitivity diagnostic): gamma_dict := A_L.
        wl_est_alt.append(
            GammaEstimate(
                channel=str(m["channel"]),
                dataset=str(m["id"]),
                gamma_hat=float(A),
                sigma=float(sA),
                note="map: gamma_dict := A_L (counterfactual sensitivity)",
                source=str(m.get("source", "")),
            )
        )

    # ----------------------------
    # 3) Strong-lensing time-delay proxy (H0 inference)
    # ----------------------------
    td = _read_json(data_root / "strong_lensing" / "h0_time_delay.json")["measurements"]
    td_est: List[GammaEstimate] = []
    td_est_alt: List[GammaEstimate] = []
    for m in td:
        H0 = float(m["value"])
        sp = float(m.get("sigma_plus", 0.0))
        sm = float(m.get("sigma_minus", 0.0))
        sH = 0.5 * (sp + sm) if (sp > 0 and sm > 0) else max(sp, sm)
        if H0 <= 0 or sH <= 0:
            continue
        gamma_hat = H0 / PLANCK18_H0_KM_S_MPC
        # delta-method propagation assuming independence
        rel2 = (sH / H0) ** 2 + (PLANCK18_H0_SIGMA_KM_S_MPC / PLANCK18_H0_KM_S_MPC) ** 2
        sigma = abs(gamma_hat) * math.sqrt(rel2)
        td_est.append(
            GammaEstimate(
                channel=str(m["channel"]),
                dataset=str(m["id"]),
                gamma_hat=float(gamma_hat),
                sigma=float(sigma),
                note="map: gamma_dict := H0_TD / H0_ref (ref=Planck18)",
                source=str(m.get("source", "")),
            )
        )
        # Bounded counterfactual reference (sensitivity diagnostic): SH0ES19.
        gamma_hat_alt = H0 / SH0ES19_H0_KM_S_MPC
        rel2_alt = (sH / H0) ** 2 + (SH0ES19_H0_SIGMA_KM_S_MPC / SH0ES19_H0_KM_S_MPC) ** 2
        sigma_alt = abs(gamma_hat_alt) * math.sqrt(rel2_alt)
        td_est_alt.append(
            GammaEstimate(
                channel=str(m["channel"]),
                dataset=str(m["id"]),
                gamma_hat=float(gamma_hat_alt),
                sigma=float(sigma_alt),
                note="map: gamma_dict := H0_TD / H0_ref (ref=SH0ES19)",
                source=str(m.get("source", "")),
            )
        )

    # ----------------------------
    # 4) Rotation curves (SPARC) via chi reconstruction + WLS gamma fit
    # ----------------------------
    sparc_dir = data_root / "sparc"
    sparc_files = ["NGC2403_rotmod.dat", "NGC3198_rotmod.dat"]
    rc_fits: List[RotationCurveFit] = []

    # Default reconstruction knobs (audit will sweep later).
    m_word = 6
    thr_rule = "median"
    base_rule = "mean"
    smooth_k = 5  # odd

    prog = ProgressEvery("rotation-curve fits", total=len(sparc_files), interval_s=60.0)
    prog.start()

    for i, fn in enumerate(sparc_files):
        p = sparc_dir / fn
        gname = fn.replace("_rotmod.dat", "")
        dat = _parse_sparc_rotmod(p)

        # Use disk surface brightness as the scalar statistic (independent of Vobs).
        scalar = np.asarray(dat["sbdisk_l_pc2"], dtype=float)
        r_kpc = np.asarray(dat["r_kpc"], dtype=float)

        recon = reconstruct_chi_from_1d_scalar(
            r_kpc=r_kpc,
            scalar=scalar,
            m=m_word,
            threshold_rule=thr_rule,
            baseline_rule=base_rule,
        )
        fit = fit_gamma_from_rotation_curve(
            galaxy=gname,
            r_kpc_full=r_kpc,
            vobs_kms_full=np.asarray(dat["vobs_kms"], dtype=float),
            verr_kms_full=np.asarray(dat["verr_kms"], dtype=float),
            chi_recon=recon,
            smooth_k=smooth_k,
        )
        rc_fits.append(fit)
        prog.maybe(i + 1, extra=f"galaxy={gname} n_used={fit.n_used}/{fit.n_total}")

    prog.done()

    rc_est: List[GammaEstimate] = []
    for fit in rc_fits:
        src = "SPARC rotmod subset (see data/gamma_crossobs/sparc/manifest.json)"
        rc_est.append(
            GammaEstimate(
                channel="rotation_curves_sparc",
                dataset=fit.galaxy,
                gamma_hat=float(fit.gamma_hat),
                sigma=float(fit.sigma),
                note=f"chi from SBdisk, m={fit.recon.m}, thr={fit.recon.threshold_rule}, g0={fit.recon.baseline_rule}, smooth_k={fit.smooth_k}, used={fit.n_used}/{fit.n_total}",
                source=src,
            )
        )

    # Channel-level combine (rotation curves across galaxies).
    rc_comb = _combine_inverse_variance(rc_est)
    if rc_comb is not None:
        rc_comb = GammaEstimate(
            channel="rotation_curves_sparc",
            dataset="combined",
            gamma_hat=rc_comb.gamma_hat,
            sigma=rc_comb.sigma,
            note="inverse-variance combine across galaxies",
            source=rc_comb.source,
        )

    # ----------------------------
    # 5) Joint estimate + diagnostics
    # ----------------------------
    all_est: List[GammaEstimate] = []
    all_est.extend(solar_est)
    all_est.extend(wl_est)
    all_est.extend(td_est)
    if rc_comb is not None:
        all_est.append(rc_comb)

    joint = _combine_inverse_variance(all_est)
    if joint is None:
        raise RuntimeError("No valid gamma estimates were produced.")

    gamma_joint = joint.gamma_hat
    chi2, dof, pval = _chi2_consistency(all_est, gamma_joint)
    zmax, zpair = _pairwise_max_z(all_est)

    # Mapping sensitivity diagnostics (not part of the baseline joint estimate).
    wl_map_delta: List[Tuple[str, float, float]] = []
    for base, alt in zip(wl_est, wl_est_alt):
        wl_map_delta.append((base.dataset, float(base.gamma_hat), float(alt.gamma_hat)))
    td_ref_delta: List[Tuple[str, float, float]] = []
    for base, alt in zip(td_est, td_est_alt):
        td_ref_delta.append((base.dataset, float(base.gamma_hat), float(alt.gamma_hat)))

    # Leave-one-channel-out joint estimates (by channel).
    loo: Dict[str, GammaEstimate] = {}
    for ch in sorted({e.channel for e in all_est}):
        subset = [e for e in all_est if e.channel != ch]
        j = _combine_inverse_variance(subset)
        if j is None:
            continue
        loo[ch] = GammaEstimate(
            channel="joint_leave_one_out",
            dataset=ch,
            gamma_hat=j.gamma_hat,
            sigma=j.sigma,
            note="leave-one-channel-out joint",
            source="",
        )

    # ----------------------------
    # 6) Write LaTeX fragments
    # ----------------------------
    rows: List[str] = []
    # Summary header row is provided by the LaTeX wrapper; this file contains only rows.
    ordered = [
        *sorted(solar_est, key=lambda e: (e.channel, e.dataset)),
        *sorted(wl_est, key=lambda e: (e.channel, e.dataset)),
        *sorted(td_est, key=lambda e: (e.channel, e.dataset)),
    ]
    if rc_comb is not None:
        ordered.append(rc_comb)

    # Compute pulls w.r.t. joint.
    for e in ordered:
        pull = (e.gamma_hat - gamma_joint) / e.sigma if (e.sigma > 0) else float("nan")
        rows.append(
            " & ".join(
                [
                    _tex_escape(e.channel),
                    f"\\texttt{{{_tex_escape(e.dataset)}}}",
                    _format_pm(e.gamma_hat, e.sigma),
                    f"{pull:+.2f}",
                    _tex_escape(e.note),
                ]
            )
            + " \\\\"
        )

    # Add a joint row.
    rows.append(
        " & ".join(
            [
                "\\textbf{joint}",
                "\\texttt{all}",
                _format_pm(gamma_joint, joint.sigma),
                f"{0.00:+.2f}",
                _tex_escape(f"chi2={chi2:.2f} dof={dof} p={pval:.3g} |z|max={zmax:.2f} ({zpair})"),
            ]
        )
        + " \\\\"
    )
    rows.append(r"\bottomrule")

    write_lines(out_gen / "gamma_crossobs_rows.tex", rows)

    # Write a compact diagnostics fragment for the LaTeX appendix (single paragraph).
    diag_pair = _tex_escape(zpair) if zpair else "n/a"
    diag_line = (
        "Baseline-map joint estimate: "
        f"$\\widehat\\gamma_{{\\mathrm{{dict}}}}={_format_sci_tex(gamma_joint, digits=6)}"
        f" \\pm {_format_sci_tex(joint.sigma, digits=6)}$."
        f" Consistency: $\\chi^2={chi2:.2f}$, $\\mathrm{{dof}}={dof}$, $p={pval:.3g}$."
        f" Max pairwise tension: $|z|_{{\\max}}={zmax:.2f}$ (\\texttt{{{diag_pair}}})."
    )
    write_lines(out_gen / "gamma_crossobs_diagnostics.tex", [diag_line])

    stab_rows: List[str] = []
    if rc_comb is not None:
        # Counterfactual sweeps for the rotation-curve pipeline (Appendix 29 audit knobs).
        sweep_m = [6, 8]
        sweep_thr = ["median", "quantile:0.65"]
        sweep_g0 = ["mean", "median"]
        sweep_smooth = [1, 5, 9]

        sweep_vals: List[float] = []
        sweep_notes: List[str] = []
        for mm in sweep_m:
            for tr in sweep_thr:
                for br in sweep_g0:
                    for sk in sweep_smooth:
                        per_gal: List[GammaEstimate] = []
                        for fn in sparc_files:
                            p = sparc_dir / fn
                            gname = fn.replace("_rotmod.dat", "")
                            dat = _parse_sparc_rotmod(p)
                            scalar = np.asarray(dat["sbdisk_l_pc2"], dtype=float)
                            r_kpc = np.asarray(dat["r_kpc"], dtype=float)
                            recon = reconstruct_chi_from_1d_scalar(
                                r_kpc=r_kpc,
                                scalar=scalar,
                                m=mm,
                                threshold_rule=tr,
                                baseline_rule=br,
                            )
                            fit = fit_gamma_from_rotation_curve(
                                galaxy=gname,
                                r_kpc_full=r_kpc,
                                vobs_kms_full=np.asarray(dat["vobs_kms"], dtype=float),
                                verr_kms_full=np.asarray(dat["verr_kms"], dtype=float),
                                chi_recon=recon,
                                smooth_k=sk,
                            )
                            per_gal.append(
                                GammaEstimate(
                                    channel="rotation_curves_sparc",
                                    dataset=gname,
                                    gamma_hat=float(fit.gamma_hat),
                                    sigma=float(fit.sigma),
                                    note="",
                                    source="",
                                )
                            )
                        comb = _combine_inverse_variance(per_gal)
                        if comb is None:
                            continue
                        sweep_vals.append(float(comb.gamma_hat))
                        sweep_notes.append(f"m={mm},thr={tr},g0={br},smooth_k={sk}")

        if sweep_vals:
            g0 = float(rc_comb.gamma_hat)
            gmin = float(np.min(sweep_vals))
            gmax = float(np.max(sweep_vals))
            dmax = float(np.max(np.abs(np.asarray(sweep_vals) - g0)))
            stab_rows.append(
                " & ".join(
                    [
                        f"\\textbf{{{_tex_escape('rotation_curves_sparc')}}}",
                        "\\texttt{combined}",
                        _format_pm(g0, float(rc_comb.sigma)),
                        _format_cell_sci(gmin),
                        _format_cell_sci(gmax),
                        _format_cell_sci(dmax),
                        _tex_escape(
                            "sweep over m in {6,8}, thr in {median,q=0.65}, g0 in {mean,median}, smooth_k in {1,5,9}"
                        ),
                    ]
                )
                + " \\\\"
            )

    # Weak-lensing proxy-map sensitivity row: sqrt(A_L) vs A_L.
    if wl_est and wl_est_alt:
        base = wl_est[0]
        alt = wl_est_alt[0]
        g0 = float(base.gamma_hat)
        gmin = float(min(base.gamma_hat, alt.gamma_hat))
        gmax = float(max(base.gamma_hat, alt.gamma_hat))
        dmax = float(abs(alt.gamma_hat - base.gamma_hat))
        stab_rows.append(
            " & ".join(
                [
                    f"\\textbf{{{_tex_escape(base.channel)}}}",
                    f"\\texttt{{{_tex_escape(base.dataset)}}}",
                    _format_pm(g0, float(base.sigma)),
                    _format_cell_sci(gmin),
                    _format_cell_sci(gmax),
                    _format_cell_sci(dmax),
                    _tex_escape("bounded proxy-map family: gamma_dict := sqrt(A_L) (baseline) vs gamma_dict := A_L (counterfactual)"),
                ]
            )
            + " \\\\"
        )

    # Strong-lensing proxy-map sensitivity row: Planck18 vs SH0ES19 reference H0.
    if td_est and td_est_alt:
        base = td_est[0]
        alt = td_est_alt[0]
        g0 = float(base.gamma_hat)
        gmin = float(min(base.gamma_hat, alt.gamma_hat))
        gmax = float(max(base.gamma_hat, alt.gamma_hat))
        dmax = float(abs(alt.gamma_hat - base.gamma_hat))
        stab_rows.append(
            " & ".join(
                [
                    f"\\textbf{{{_tex_escape(base.channel)}}}",
                    f"\\texttt{{{_tex_escape(base.dataset)}}}",
                    _format_pm(g0, float(base.sigma)),
                    _format_cell_sci(gmin),
                    _format_cell_sci(gmax),
                    _format_cell_sci(dmax),
                    _tex_escape("bounded reference family: H0_ref = Planck18 (baseline) vs SH0ES19 (counterfactual)"),
                ]
            )
            + " \\\\"
        )

    # Leave-one-out rows
    for ch in sorted(loo.keys()):
        j = loo[ch]
        stab_rows.append(
            " & ".join(
                [
                    f"\\textbf{{{_tex_escape('joint_LOO')}}}",
                    f"\\texttt{{{_tex_escape(ch)}}}",
                    _format_pm(j.gamma_hat, j.sigma),
                    "",
                    "",
                    "",
                    _tex_escape("leave-one-channel-out joint estimate"),
                ]
            )
            + " \\\\"
        )

    if not stab_rows:
        stab_rows.append("% (no stability rows generated)")
    stab_rows.append(r"\bottomrule")
    write_lines(out_gen / "gamma_crossobs_stability_rows.tex", stab_rows)

    # ----------------------------
    # 7) Figure: channel estimates with joint band
    # ----------------------------
    fig_items = ordered + [joint]
    labels = [f"{e.channel}\n{e.dataset}" for e in fig_items]
    gvals = [e.gamma_hat for e in fig_items]
    svals = [e.sigma for e in fig_items]

    y = np.arange(len(fig_items))[::-1]
    plt.figure(figsize=(9.0, 0.6 + 0.5 * len(fig_items)))
    plt.errorbar(gvals, y, xerr=svals, fmt="o", color="black", ecolor="black", capsize=3)
    plt.axvline(gamma_joint, color="tab:blue", linewidth=2, label="joint")
    plt.fill_betweenx(
        [y.min() - 1, y.max() + 1],
        gamma_joint - joint.sigma,
        gamma_joint + joint.sigma,
        color="tab:blue",
        alpha=0.15,
        linewidth=0,
    )
    plt.yticks(y, labels)
    plt.xlabel("gamma estimate")
    plt.ylim(y.min() - 1, y.max() + 1)
    plt.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_fig / "gamma_crossobs_consistency.png", dpi=200)
    plt.close()

    print("[gamma_crossobs] wrote sections/generated/gamma_crossobs_rows.tex")
    print("[gamma_crossobs] wrote sections/generated/gamma_crossobs_stability_rows.tex")
    print("[gamma_crossobs] wrote figures/gamma_crossobs_consistency.png")


if __name__ == "__main__":
    main()

