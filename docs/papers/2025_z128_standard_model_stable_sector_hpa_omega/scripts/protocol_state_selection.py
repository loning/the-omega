# -*- coding: utf-8 -*-
"""
Joint protocol-state selection (theory-first) for this paper.

This script implements a finite, explicit one-shot closure of the protocol state (m,n,K)
at selected target tags (mu-tags) by minimizing a joint key:

  J = MDL + lambda * Sens

where:
  - MDL is a simple description-length proxy for the protocol-state hypothesis plus
    an explicit family-size footprint term;
  - Sens is a bounded sensitivity score computed from explicit finite sweeps
    (kernel-family or counterfactual envelopes) inside the same declared audit budget.

Outputs:
  - sections/generated/protocol_state_selected.json
  - sections/generated/protocol_state_selected.tex

Notes:
  - Deterministic output (no timestamps).
  - English-only script output.
  - Uses only finite candidate families; no continuous hyperparameters are fitted.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


# Fixed convention for theory-first closure: Sens weight.
LAMBDA_SENS: float = 10.0


def _elias_gamma_length(n: int) -> int:
    if n <= 0:
        raise ValueError("Elias gamma code requires n>=1.")
    return 2 * int(math.floor(math.log2(float(n)))) + 1


def _t_complexity_key(t: Fraction) -> Tuple[int, int, int]:
    # Complexity proxy for a rational t: prefer simpler rationals (small denom/numer).
    return (int(t.denominator), abs(int(t.numerator)), int(t.numerator))

def _tex_escape_tt(s: str) -> str:
    # Minimal escape for \texttt{...} content used in generated LaTeX fragments.
    return str(s).replace("_", r"\_")


@dataclass(frozen=True)
class KernelChoice:
    family: str  # e.g., "tempered_deg"
    t: str  # rational string, e.g., "1/2" or "0"


@dataclass(frozen=True)
class SelectedState:
    tag: str
    mu_label: str
    m: int
    n: int
    kernel: KernelChoice
    family_size: int
    mdl: float
    sens: float
    J: float
    tie_break: str
    notes: str


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def load_selected_state(tag: str) -> SelectedState:
    """
    Load a selected state from the generated JSON.
    """
    p = generated_dir() / "protocol_state_selected.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    rec = obj.get("selected", {}).get(tag, None)
    if not isinstance(rec, dict):
        raise KeyError(f"Missing selected state for tag='{tag}' in {p}")
    k = rec.get("kernel", {})
    kernel = KernelChoice(family=str(k.get("family")), t=str(k.get("t")))
    return SelectedState(
        tag=str(rec.get("tag")),
        mu_label=str(rec.get("mu_label")),
        m=int(rec.get("m")),
        n=int(rec.get("n")),
        kernel=kernel,
        family_size=int(rec.get("family_size")),
        mdl=float(rec.get("mdl")),
        sens=float(rec.get("sens")),
        J=float(rec.get("J")),
        tie_break=str(rec.get("tie_break")),
        notes=str(rec.get("notes")),
    )


# -------------------------
# mu_Z (electroweak) selection
# -------------------------


def _ew_candidate_ms() -> List[int]:
    return [6, 8, 10, 12, 14, 16]


def _tempered_t_grid() -> List[Fraction]:
    return [Fraction(0, 1), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(1, 1)]


def _ew_eval_e_sum(m: int, t: Fraction, u_to_field: object) -> float:
    """
    Evaluate the electroweak joint mismatch objective e_alpha + e_sin2 for (m,t)
    using the same computation as exp_ew_resolution_weighted_match_family.py.
    """
    import exp_ew_resolution_weighted_match_family as ewfam

    c = ewfam._candidate(m=int(m), t=t, u_to_field=u_to_field)  # type: ignore[attr-defined]
    return float(c.e_alpha + c.e_sin2)


def _select_mu_Z() -> SelectedState:
    import exp_ew_resolution_weighted_match_family as ewfam

    ms = _ew_candidate_ms()
    ts = _tempered_t_grid()
    # Balanced coupling convention: m = 2n.
    mn = [(m, m // 2) for m in ms]
    family_size = len(mn) * len(ts)

    u_to_field = ewfam._build_x6_to_field_map()  # type: ignore[attr-defined]

    # Sensitivity at fixed m: spread of e_sum over the kernel family grid.
    spread_by_m: Dict[int, float] = {}
    for (m, _n) in mn:
        vals = [float(_ew_eval_e_sum(m, t, u_to_field=u_to_field)) for t in ts]
        spread_by_m[m] = float(max(vals) - min(vals))

    # Candidates: all (m,n,t)
    cands: List[Tuple[float, Tuple[int, int, Fraction], float, float]] = []
    # key -> (J, (m,n,t), mdl, sens)
    for (m, n) in mn:
        sens = float(spread_by_m[m])
        for t in ts:
            # MDL proxy: bits for m, bits for n, rational complexity for t, plus explicit family-size footprint.
            # We keep it simple and deterministic.
            mdl = float(m + 2 * n + _t_complexity_key(t)[0] + math.log2(float(family_size)))
            J = float(mdl + LAMBDA_SENS * sens)
            cands.append((J, (m, n, t), mdl, sens))

    # Deterministic tie-break: smaller J -> simpler t -> smaller n -> smaller m.
    best = min(
        cands,
        key=lambda x: (
            x[0],
            _t_complexity_key(x[1][2]),
            x[1][1],
            x[1][0],
        ),
    )
    J, (m_star, n_star, t_star), mdl_star, sens_star = best

    t_str = f"{t_star.numerator}/{t_star.denominator}" if t_star.denominator != 1 else f"{t_star.numerator}"
    return SelectedState(
        tag="mu_Z",
        mu_label=r"$\mu_Z$",
        m=int(m_star),
        n=int(n_star),
        kernel=KernelChoice(family="tempered_deg", t=t_str),
        family_size=int(family_size),
        mdl=float(mdl_star),
        sens=float(sens_star),
        J=float(J),
        tie_break="J, then t-complexity, then n, then m",
        notes="EW: Sens is kernel-family spread of (e_alpha+e_sin2) over a fixed rational t-grid at each m.",
    )


# -------------------------
# gamma_direct selection (vendored SPARC subset)
# -------------------------


def _iter_sparc_files() -> List[str]:
    import exp_gamma_cross_observation as gx

    sparc_dir = paper_root() / "data" / "gamma_crossobs" / "sparc"
    manifest = gx._read_json(sparc_dir / "manifest.json")
    files = [str(x["path"]) for x in manifest.get("files", []) if "path" in x]
    if not files:
        raise RuntimeError("SPARC manifest contains no files.")
    return files


def _gamma_joint_for_m_t(m: int, t: Fraction) -> Tuple[float, float]:
    """
    Compute the inverse-variance combined gamma_hat and sigma over a fixed sweep-eligible subset,
    using the kernelized chi aggregator (tempered degeneracy kernel g^t).
    """
    import numpy as np
    import exp_gamma_cross_observation as gx
    import exp_gamma_kernel_family_sweep as gks

    sparc_dir = paper_root() / "data" / "gamma_crossobs" / "sparc"
    sparc_files = _iter_sparc_files()

    # Keep a fixed subset across m by requiring enough samples for the largest m in the scan.
    max_m = max(6, int(m))
    sweep_files: List[str] = []
    for fn in sparc_files:
        dat0 = gx._parse_sparc_rotmod(sparc_dir / fn)
        n0 = int(len(dat0.get("r_kpc", [])))
        if n0 >= (2 * max_m - 1):
            sweep_files.append(fn)

    thr_rule = "median"
    base_rule = "mean"
    smooth_k = 5

    ests: List[gx.GammaEstimate] = []
    for fn in sweep_files:
        p = sparc_dir / fn
        gname = fn.replace("_rotmod.dat", "")
        dat = gx._parse_sparc_rotmod(p)
        scalar = np.asarray(dat["sbdisk_l_pc2"], dtype=float)
        r_kpc = np.asarray(dat["r_kpc"], dtype=float)
        vobs_kms = np.asarray(dat["vobs_kms"], dtype=float)
        verr_kms = np.asarray(dat["verr_kms"], dtype=float)

        recon = gks.reconstruct_chi_from_1d_scalar_kernel(
            r_kpc=r_kpc,
            scalar=scalar,
            m=int(m),
            threshold_rule=thr_rule,
            baseline_rule=base_rule,
            t=t,
        )
        fit = gx.fit_gamma_from_rotation_curve(
            galaxy=gname,
            r_kpc_full=r_kpc,
            vobs_kms_full=vobs_kms,
            verr_kms_full=verr_kms,
            chi_recon=recon,
            smooth_k=int(smooth_k),
        )
        ests.append(
            gx.GammaEstimate(
                channel="dict",
                dataset=gname,
                gamma_hat=float(fit.gamma_hat),
                sigma=float(fit.sigma),
                note="kernelized chi aggregator (tempered degeneracy kernel)",
                source="rotation_curves",
            )
        )

    # Inverse-variance combine (same as gks).
    import numpy as np

    xs = [e for e in ests if np.isfinite(e.gamma_hat) and np.isfinite(e.sigma) and e.sigma > 0]
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


def _select_gamma_direct() -> SelectedState:
    ms = [6, 8]
    ts = _tempered_t_grid()
    mn = [(m, m // 2) for m in ms]
    family_size = len(mn) * len(ts)

    # For each m compute a kernel-family envelope spread in gamma_hat.
    spread_by_m: Dict[int, float] = {}
    gamma_by_m_t: Dict[Tuple[int, Fraction], Tuple[float, float]] = {}
    for (m, _n) in mn:
        vals: List[float] = []
        for t in ts:
            ghat, _sig = _gamma_joint_for_m_t(m, t)
            gamma_by_m_t[(m, t)] = (ghat, _sig)
            vals.append(float(ghat))
        spread_by_m[m] = float(max(vals) - min(vals)) if vals else float("inf")

    cands: List[Tuple[float, Tuple[int, int, Fraction], float, float]] = []
    for (m, n) in mn:
        sens = float(spread_by_m[m])
        for t in ts:
            mdl = float(m + 2 * n + _t_complexity_key(t)[0] + math.log2(float(family_size)))
            J = float(mdl + LAMBDA_SENS * sens)
            cands.append((J, (m, n, t), mdl, sens))

    best = min(
        cands,
        key=lambda x: (
            x[0],
            _t_complexity_key(x[1][2]),
            x[1][1],
            x[1][0],
        ),
    )
    J, (m_star, n_star, t_star), mdl_star, sens_star = best
    t_str = f"{t_star.numerator}/{t_star.denominator}" if t_star.denominator != 1 else f"{t_star.numerator}"
    return SelectedState(
        tag="gamma_direct",
        mu_label="SPARC-direct",
        m=int(m_star),
        n=int(n_star),
        kernel=KernelChoice(family="tempered_deg", t=t_str),
        family_size=int(family_size),
        mdl=float(mdl_star),
        sens=float(sens_star),
        J=float(J),
        tie_break="J, then t-complexity, then n, then m",
        notes="Gamma-direct: Sens is kernel-family spread of the inverse-variance joint gamma_hat over a fixed rational t-grid.",
    )


# -------------------------
# cosmology z=0 (energy budget) selection
# -------------------------


def _select_cosmo_z0() -> SelectedState:
    import exp_cosmology_energy_budget_fit as cf

    omega_vis0 = 0.0493
    omega_sigma = 0.0005
    m_min, m_max = 1, 40

    ms_allowed = cf.stability_ms(omega_vis0=omega_vis0, omega_vis0_sigma=omega_sigma, m_min=m_min, m_max=m_max)
    # theory-first: prefer smaller m among the admissible set; if empty, fall back to best mismatch.
    if ms_allowed:
        m_star = min(int(x) for x in ms_allowed)
        stable = True
    else:
        m_star = int(cf.best_fit_m(omega_vis0=omega_vis0, m_min=m_min, m_max=m_max).m_star)
        stable = False

    # Kernel is irrelevant for this deterministic fraction template; keep a placeholder.
    family_size = (m_max - m_min + 1)
    mdl = float(m_star + math.log2(float(family_size)))
    sens = float(len(ms_allowed))  # smaller is better; 1 means stable.
    J = float(mdl + LAMBDA_SENS * sens)

    return SelectedState(
        tag="cosmo_z0",
        mu_label=r"$z=0$",
        m=int(m_star),
        n=int(m_star // 2) if (m_star % 2 == 0) else int((m_star - 1) // 2),
        kernel=KernelChoice(family="none", t="n/a"),
        family_size=int(family_size),
        mdl=float(mdl),
        sens=float(sens),
        J=float(J),
        tie_break="prefer smaller m inside the discrete stability set; fallback to best mismatch",
        notes=f"Cosmology z=0: Sens is |allowed_m_set| under omega_vis0±sigma (stable={stable}).",
    )


def main() -> int:
    selected: Dict[str, SelectedState] = {}

    s_ew = _select_mu_Z()
    selected[s_ew.tag] = s_ew

    s_gamma = _select_gamma_direct()
    selected[s_gamma.tag] = s_gamma

    s_cosmo = _select_cosmo_z0()
    selected[s_cosmo.tag] = s_cosmo

    # JSON for scripts.
    out_json = generated_dir() / "protocol_state_selected.json"
    obj = {
        "lambda_sens": LAMBDA_SENS,
        "selected": {k: asdict(v) for (k, v) in selected.items()},
        "kernel_families": {
            "tempered_deg": {
                "t_grid": [f"{t.numerator}/{t.denominator}" if t.denominator != 1 else f"{t.numerator}" for t in _tempered_t_grid()],
                "note": "mu(w) ∝ g_m(w)^t on X_m (degeneracy-tempered family).",
            }
        },
    }
    _write_json(out_json, obj)

    # Compact TeX fragment for the appendix.
    lines: List[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(r"\begin{tabular}{llllrrr}")
    lines.append(r"\toprule")
    lines.append(r"tag & $\mu$ & $(m^\ast,n^\ast)$ & $K^\ast$ & $|\mathcal{F}_\mu|$ & $\mathrm{MDL}$ & $\mathrm{Sens}$ \\")
    lines.append(r"\midrule")
    for tag in ["mu_Z", "gamma_direct", "cosmo_z0"]:
        s = selected[tag]
        mn_tex = rf"({s.m},{s.n})"
        k_tex = rf"\texttt{{{_tex_escape_tt(s.kernel.family)}}}:{_tex_escape_tt(s.kernel.t)}"
        lines.append(
            rf"\texttt{{{_tex_escape_tt(s.tag)}}} & {s.mu_label} & {mn_tex} & {k_tex} & {s.family_size} & {s.mdl:.3f} & {s.sens:.3f} \\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    lines.append(r"\noindent\AuditTag Joint key convention: $J_\mu=\mathrm{MDL}_\mu+\lambda\,\mathrm{Sens}_\mu$ with $\lambda=\,$" + f"{LAMBDA_SENS:.1f}" + r".")

    out_tex = generated_dir() / "protocol_state_selected.tex"
    write_lines(out_tex, lines)

    print("Wrote sections/generated/protocol_state_selected.json")
    print("Wrote sections/generated/protocol_state_selected.tex")
    print(f"[protocol_state] Selected states: {', '.join(sorted(selected.keys()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

