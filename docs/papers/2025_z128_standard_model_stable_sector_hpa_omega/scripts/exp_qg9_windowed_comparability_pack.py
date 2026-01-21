# -*- coding: utf-8 -*-
"""
QG9-M1 windowed comparability: single pack generator (merged entry point).

This script MERGES the previously split QG9-M1 generators into one deterministic
entry point. It produces the full family of LaTeX fragments used by
Appendix app:qg9_m1_windowed_comparability:

  - qg9_windowed_comparability_default_instance.tex
  - qg9_windowed_comparability_registry.tex
  - qg9_windowed_comparability_budget.tex
  - qg9_windowed_comparability_evidence.tex
  - qg9_windowed_comparability_acceptance_checklist.tex
  - qg9_windowed_comparability_numeric_summary.tex
  - qg9_windowed_comparability_numeric.tex

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Standard-library only, except for importing existing local demo scripts.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines

import exp_curvature_bridge_end_to_end as e2e


# ---------------------------
# Shared helpers
# ---------------------------

_SCI_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*\\times\s*10\^\{([+-]?\d+)\}\s*$")


def _strip_ensuremath(s: str) -> str:
    t = s.strip()
    if t.startswith(r"\ensuremath{") and t.endswith("}"):
        return t[len(r"\ensuremath{") : -1]
    return t


def _parse_tex_float(token: str) -> float:
    t = _strip_ensuremath(token).strip()
    if t in {"", "n/a"}:
        raise ValueError(f"Empty/non-numeric token: {token!r}")
    m = _SCI_RE.match(t)
    if m:
        mant = float(m.group(1))
        exp = int(m.group(2))
        return mant * (10.0 ** exp)
    return float(t)


def _read_rows(path: Path) -> List[List[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: List[List[str]] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.endswith(r"\\"):
            s = s[: -len(r"\\")].rstrip()
        out.append([p.strip() for p in s.split("&")])
    return out


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


# ---------------------------
# Default instance (reproducibility reference)
# ---------------------------

@dataclass(frozen=True)
class SelectedState:
    tag: str
    mu_label: str
    m: int
    n: int
    kernel_family: str
    kernel_t: str


def _load_selected_state() -> Optional[SelectedState]:
    p = paper_root() / "sections/generated/protocol_state_selected.json"
    if not p.is_file():
        return None
    try:
        obj: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    sel = obj.get("selected", {})
    if not isinstance(sel, dict):
        return None

    preferred_tags = ["gamma_direct", "mu_Z", "cosmo_z0"]
    pick: Optional[Tuple[str, Dict[str, Any]]] = None
    for t in preferred_tags:
        v = sel.get(t)
        if isinstance(v, dict):
            pick = (t, v)
            break
    if pick is None:
        keys = sorted([k for k in sel.keys() if isinstance(k, str)])
        if not keys:
            return None
        v = sel.get(keys[0])
        if not isinstance(v, dict):
            return None
        pick = (keys[0], v)

    tag, v = pick
    k = v.get("kernel", {})
    if not isinstance(k, dict):
        k = {}
    return SelectedState(
        tag=str(tag),
        mu_label=str(v.get("mu_label", "")),
        m=int(v.get("m", 0)),
        n=int(v.get("n", 0)),
        kernel_family=str(k.get("family", "none")),
        kernel_t=str(k.get("t", "n/a")),
    )


def _write_default_instance(outdir: Path) -> None:
    s = _load_selected_state()
    out_path = outdir / "qg9_windowed_comparability_default_instance.tex"
    if s is None:
        write_lines(
            out_path,
            [
                r"\noindent\AuditTag Default-instance registry unavailable: "
                r"\texttt{sections/generated/protocol\_state\_selected.json} not found.",
            ],
        )
        return

    n_order = 1
    delta_tex = r"10^{-2}"
    lines: List[str] = []
    lines.append(
        r"\noindent\AuditTag \textbf{Reference QG9-M1 instance (reproducibility).} "
        r"The following is a non-normative instance used to pin down a concrete window/state when reproducing "
        r"the QG-interface comparability tables; it does not add assumptions beyond the declared staircase dictionary."
    )
    lines.append(r"\begin{itemize}")
    lines.append(
        r"\item \textbf{Protocol state anchor:} "
        + rf"\texttt{{{s.tag}}} at $\mu=$ {s.mu_label}, "
        + rf"$(m,n)=({s.m},{s.n})$, "
        + rf"$K=$ \texttt{{{s.kernel_family}}}:{s.kernel_t} "
        + r"(from \texttt{sections/generated/protocol\_state\_selected.json})."
    )
    lines.append(
        r"\item \textbf{Reference UV window:} "
        r"use the staircase threshold coordinate $r_{\mathrm{th}}(m)=(m-6)\,r_{\mathrm{step}}$ with "
        r"$r_{\mathrm{step}}=2\pi$ (Section~\ref{subsec:p3_resolution_jumps}) and take "
        r"$W_{\mathrm{ref}}=[r_{\mathrm{th}}(6),\,r_{\mathrm{th}}(10)]=[0,\,8\pi]$ as a minimal even-step window "
        r"aligned with the QG interface suite family $(m,n)\in\{(6,3),(8,4),(10,5)\}$."
    )
    lines.append(
        r"\item \textbf{EFT order and confidence:} "
        + rf"take $N={n_order}$ and $\delta={delta_tex}$ as a compact default for the registry-wide bound in "
        + r"Appendix~\ref{app:eft_error_bounds} (union-bound over a finite registry)."
    )
    lines.append(r"\end{itemize}")
    write_lines(out_path, lines)


# ---------------------------
# Registry / budget / evidence / checklist (static audit indices)
# ---------------------------

def _write_registry(outdir: Path) -> None:
    rows = [
        (
            r"$\widehat\chi$ (reconstructed overhead proxy field)",
            r"Deterministic reconstruction pipeline (Appendix~\ref{app:overhead_to_gravity_closure}; Appendix~\ref{app:protocol_to_continuum_error_control}).",
            r"EFT-side target is the corresponding scalar proxy under the declared representative action and matching conventions (Appendix~\ref{app:cap_continuum_action_closure}).",
            r"$E_{\mathrm{stat}}$+$E_{\mathrm{disc}}$ from Appendix~\ref{app:protocol_to_continuum_error_control}; $E_{\mathrm{bias}}$ from declared kernel/smoothing sweeps.",
        ),
        (
            r"$\widehat G_{00,h}$ (weak-field curvature proxy from $\widehat\chi$)",
            r"$\widehat G_{00,h}=-2\widehat\gamma\,\Delta_h\widehat\chi_h$ (Appendix~\ref{app:weak_field_curvature_from_chi}).",
            r"Weak-field EFT prediction in the declared truncation scope (Appendix~\ref{app:variational_field_equations}; Appendix~\ref{app:overhead_to_gravity_closure}).",
            r"$E_{\mathrm{disc}}$ via Laplacian truncation/noise amplification; $E_{\mathrm{match}}$ includes $\gamma$-dictionary matching envelope when applicable.",
        ),
        (
            r"$\tau_{\mathrm{WS}}(\omega)$ / $N_{\mathrm{WS}}$ (delay-derived lapse proxy)",
            r"Wigner--Smith delay dictionary and audit gates (Appendix~\ref{app:time_mass_delay}; Section~\ref{subsec:p6_wigner_smith_delay}).",
            r"EFT-side target specified by the declared time dictionary and carrier conventions (Appendix~\ref{app:renormalization_dictionary_and_boundaries}).",
            r"$E_{\mathrm{match}}$ over a finite carrier/scheme family; endpoint/unwrap failures trigger explicit failure points (S1).",
        ),
        (
            r"$|\mathcal{R}_\star|/4^n$ (budget-triggered horizon occupancy fraction)",
            r"Capacity-only budget trigger applied to reconstructed $\widehat\chi$ (Section~\ref{subsec:p8_chi_horizon_budget}; Appendix~\ref{app:protocol_horizon_tick_trap}).",
            r"EFT-side interpretation is interface-level only; comparability uses the declared capacity/entropy dictionary (Appendix~\ref{app:thermodynamics_from_equivalence}).",
            r"$E_{\mathrm{bias}}$ includes the declared margin constant and smoothing; $E_{\mathrm{stat}}$ inherits from $\widehat\chi$ uncertainty.",
        ),
        (
            r"Full-fusion interface gates (ledger closure; $V^2+D^2\le 1$; counterfactual deltas)",
            r"Deterministic full-fusion generator and artifacts (Section~\ref{sec:qg_interface_full_fusion}).",
            r"No EFT-side target: these are protocol-interface consistency constraints (Prediction~P9; Section~\ref{subsec:p9_full_fusion_interface_gates}).",
            r"Must hold exactly up to numerical tolerance; violations falsify the interface contract (not the theorem-level core).",
        ),
    ]

    lines: List[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(r"\begin{tabular}{p{0.22\textwidth} p{0.25\textwidth} p{0.23\textwidth} p{0.24\textwidth}}")
    lines.append(r"\toprule")
    lines.append(r"observable $\mathcal{O}$ & protocol-side rule & EFT-side rule/scope & error-budget terms \\")
    lines.append(r"\midrule")
    for o, pr, er, bt in rows:
        lines.append(f"{o} & {pr} & {er} & {bt} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    write_lines(outdir / "qg9_windowed_comparability_registry.tex", lines)


def _write_budget_mapping(outdir: Path) -> None:
    rows = [
        (
            r"$\widehat\chi$",
            r"Appendix~\ref{app:protocol_to_continuum_error_control} (concentration + log propagation + derivative tradeoffs).",
            r"None unless a matching dictionary is invoked for units/anchors (Match scope).",
            r"Not applicable unless an EFT-side target is specified at finite $D_{\max}$.",
            r"Kernel-family / smoothing / estimator sweeps (explicit finite families; audit tables).",
        ),
        (
            r"$\widehat G_{00,h}$",
            r"Appendix~\ref{app:weak_field_curvature_from_chi} (discrete proxy + error budget; Laplacian truncation/noise amp).",
            r"$\gamma$ dictionary matching and scheme envelope when applicable (Appendix~\ref{app:matching_envelope_theoremization}; Appendix~\ref{app:scheme_invariance_audit_contract}).",
            r"Only if compared to an EFT-side weak-field prediction; then use Appendix~\ref{app:eft_error_bounds}.",
            r"Reconstruction/regularization sweeps (bounded counterfactuals).",
        ),
        (
            r"$\tau_{\mathrm{WS}}(\omega)$ / $N_{\mathrm{WS}}$",
            r"Numerical differentiation/unwrap stability gates (Appendix~\ref{app:time_mass_delay}; Appendix~\ref{app:force_phase_delay_audit}).",
            r"Finite carrier/scheme family envelope (Appendix~\ref{app:matching_envelope_theoremization}).",
            r"EFT-side truncation only if an EFT prediction is used; otherwise this remains an interface dictionary.",
            r"Observation-class boundary: endpoint-gated/intermittent channels (Section~\ref{subsec:p9_full_fusion_interface_gates}).",
        ),
        (
            r"$|\mathcal{R}_\star|/4^n$",
            r"Inherits from $\widehat\chi$ uncertainty; capacity-only computation is exact given $(m,n)$.",
            r"None (capacity-only); any physical reinterpretation is Match/Iface only.",
            r"Not applicable (no EFT-side target claimed).",
            r"Margin constant and smoothing rule must be fixed or swept as an explicit finite family.",
        ),
        (
            r"Full-fusion gates",
            r"Exact interface checks (ledger closure; complementarity); numerical tolerance only.",
            r"None (protocol-interface consistency only).",
            r"Not applicable.",
            r"Counterfactual baseline required (wormhole off) and observation-class limitations must be stated.",
        ),
    ]

    lines: List[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(r"\begin{tabular}{p{0.12\textwidth} p{0.26\textwidth} p{0.20\textwidth} p{0.18\textwidth} p{0.18\textwidth}}")
    lines.append(r"\toprule")
    lines.append(r"$\mathcal{O}$ & $E_{\mathrm{stat}}/E_{\mathrm{disc}}$ provenance & $E_{\mathrm{match}}$ provenance & $E_{\mathrm{trunc}}$ scope & $E_{\mathrm{bias}}$ provenance \\")
    lines.append(r"\midrule")
    for o, ed, em, et, eb in rows:
        lines.append(f"{o} & {ed} & {em} & {et} & {eb} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    write_lines(outdir / "qg9_windowed_comparability_budget.tex", lines)


def _write_evidence(outdir: Path) -> None:
    rows = [
        (
            r"$\widehat\chi$",
            r"\texttt{sections/generated/qg\_interface\_suite\_rows.tex}; \texttt{sections/generated/qg\_interface\_suite\_summary.tex}; \texttt{sections/generated/chi\_kernel\_family\_sweep\_rows.tex}.",
            r"\texttt{scripts/exp\_qg\_interface\_suite.py}; \texttt{scripts/exp\_chi\_kernel\_family\_sweep.py}.",
            r"Counterfactual sensitivity of reconstructed scalars is recorded via kernel-family sweeps.",
        ),
        (
            r"$\widehat G_{00,h}$",
            r"\texttt{sections/generated/curvature\_e2e\_rows.tex}; \texttt{sections/generated/curvature\_e2e\_summary.tex}; \texttt{sections/generated/curvature\_e2e\_gamma\_rows.tex}; \texttt{sections/generated/curvature\_e2e\_gamma\_summary.tex}; \texttt{sections/generated/curvature\_e2e\_gamma\_stability\_rows.tex}.",
            r"\texttt{scripts/exp\_curvature\_bridge\_end\_to\_end.py}.",
            r"End-to-end provenance: protocolized input $\rightarrow \widehat\chi \rightarrow$ curvature proxy, including $\gamma$ diagnostics and bounded stability rows.",
        ),
        (
            r"$\tau_{\mathrm{WS}}(\omega)$ / $N_{\mathrm{WS}}$",
            r"\texttt{sections/generated/qg\_interface\_suite\_rows.tex}; \texttt{sections/generated/qg\_interface\_suite\_summary.tex}; \texttt{sections/generated/force\_phase\_delay\_audit\_toy\_rows.tex}.",
            r"\texttt{scripts/exp\_qg\_interface\_suite.py}; \texttt{scripts/exp\_force\_phase\_delay\_audit\_toy.py}.",
            r"Numerical stability of phase$\rightarrow$delay differentiation is recorded as an auditable toy table; carriers must satisfy S1-style gates.",
        ),
        (
            r"$|\mathcal{R}_\star|/4^n$",
            r"\texttt{sections/generated/chi\_horizon\_budget\_occupancy\_rows.tex}; \texttt{sections/generated/chi\_horizon\_budget\_occupancy\_summary.tex}.",
            r"\texttt{scripts/exp\_chi\_horizon\_budget\_occupancy.py}.",
            r"Capacity-only occupancy is deterministic given $(m,n)$ and the declared budget/margin.",
        ),
        (
            r"Full-fusion gates",
            r"\texttt{sections/generated/full\_fusion\_rows.tex}; \texttt{sections/generated/full\_fusion\_nowh\_rows.tex}; \texttt{sections/generated/full\_fusion\_compare\_rows.tex}; \texttt{sections/generated/full\_fusion\_summary.tex}; \texttt{sections/generated/full\_fusion\_wormhole\_sweep\_rows.tex}; \texttt{sections/generated/full\_fusion\_wormhole\_pareto\_rows.tex}.",
            r"\texttt{scripts/exp\_full\_fusion\_bh\_wormhole\_measurement.py}; \texttt{scripts/exp\_full\_fusion\_wormhole\_sweep.py}; \texttt{scripts/exp\_full\_fusion\_wormhole\_adaptive\_search.py}.",
            r"Gate checks are ledger closure + complementarity + counterfactual isolation; sweep outputs provide bounded trade-off records.",
        ),
    ]

    lines: List[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(r"\begin{tabular}{p{0.12\textwidth} p{0.40\textwidth} p{0.22\textwidth} p{0.20\textwidth}}")
    lines.append(r"\toprule")
    lines.append(r"$\mathcal{O}$ & reproducible artifacts & generator scripts & audit note \\")
    lines.append(r"\midrule")
    for o, a, g, n in rows:
        lines.append(f"{o} & {a} & {g} & {n} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    write_lines(outdir / "qg9_windowed_comparability_evidence.tex", lines)


def _write_acceptance_checklist(outdir: Path) -> None:
    rows = [
        (
            r"E0 (default instance pinned)",
            r"A concrete reference instance (window + state + $N,\delta$) is recorded to avoid underspecification.",
            r"\texttt{sections/generated/qg9\_windowed\_comparability\_default\_instance.tex}.",
        ),
        (
            r"E1 (finite registry)",
            r"$\mathfrak{Obs}_{\le N}$ is finite and explicitly listed; each $\mathcal{O}$ has protocol/EFT rules and a metric.",
            r"Appendix~\ref{app:eft_error_bounds} (Def.~\ref{def:obs_registry_finite}); \texttt{sections/generated/qg9\_windowed\_comparability\_registry.tex}.",
        ),
        (
            r"E2 (estimator semantics)",
            r"Protocol-side estimators (smoothing, differencing, kernels) are declared or swept in explicit finite families.",
            r"\texttt{sections/generated/qg9\_windowed\_comparability\_budget.tex}; \texttt{sections/generated/qg9\_windowed\_comparability\_evidence.tex}.",
        ),
        (
            r"E3 (truncation scope)",
            r"If an EFT-side target is invoked: $N$ and $D_{\max}$ (and any remainder model/envelope) are declared; otherwise the item is interface-only.",
            r"Appendix~\ref{app:eft_error_bounds} (E3); Appendix~\ref{app:strong_eft_remainder_bounds} when a remainder envelope is used.",
        ),
        (
            r"E4 (scheme/threshold scope)",
            r"Matching conventions are fixed or bounded into an explicit finite family; envelope width is budgeted (no hidden scheme knobs).",
            r"Appendix~\ref{app:matching_envelope_theoremization}; Appendix~\ref{app:scheme_invariance_audit_contract}.",
        ),
        (
            r"R1/R2 (finite-family envelopes)",
            r"All counterfactual families (kernels, schemes, carriers) are explicit and treated as envelopes, not free parameters.",
            r"\texttt{sections/generated/qg9\_windowed\_comparability\_budget.tex}; MDL registry discipline: Appendix~\ref{app:global_model_selection_mdl}.",
        ),
        (
            r"Obs-class boundary",
            r"Observation-class identifiability limits are stated (e.g.\ endpoint-gated channels; final-snapshot deltas may miss intermittent effects).",
            r"Section~\ref{subsec:p9_full_fusion_interface_gates}; \texttt{sections/generated/full\_fusion\_compare\_rows.tex}.",
        ),
        (
            r"Provenance gate",
            r"Artifacts are content-addressed for auditable provenance (script/deps fingerprint).",
            r"\texttt{sections/generated/artifact\_hash\_registry\_summary.tex}.",
        ),
    ]

    lines: List[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(r"\begin{tabular}{p{0.16\textwidth} p{0.40\textwidth} p{0.38\textwidth}}")
    lines.append(r"\toprule")
    lines.append(r"gate & acceptance requirement & evidence pointers \\")
    lines.append(r"\midrule")
    for g, r, e in rows:
        lines.append(f"{g} & {r} & {e} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    write_lines(outdir / "qg9_windowed_comparability_acceptance_checklist.tex", lines)


# ---------------------------
# Numeric instantiation (actual computation)
# ---------------------------

@dataclass(frozen=True)
class DefaultInstance:
    m: int
    n: int
    kernel_family: str
    kernel_t: str
    n_order: int
    delta: float


def _load_default_instance() -> DefaultInstance:
    s = _load_selected_state()
    if s is None:
        raise ValueError("Missing protocol_state_selected.json for numeric instantiation.")
    return DefaultInstance(
        m=int(s.m),
        n=int(s.n),
        kernel_family=str(s.kernel_family),
        kernel_t=str(s.kernel_t),
        n_order=1,
        delta=1e-2,
    )


@dataclass(frozen=True)
class ChiCurvResult:
    eps_chi: float
    lap_err: float
    total_bound: float
    max_abs_lap_true: float


def _compute_chi_curvature_anchor(*, n_bits: int, m: int) -> ChiCurvResult:
    side = 1 << int(n_bits)
    h = 1.0 / float(side)
    amp = 0.25
    sigma_delta = 0.10
    chi_true = e2e._build_chi_true(side=side, amp=amp)
    bits = e2e._build_bits_from_delta(
        n_bits=n_bits, chi_true=chi_true, sigma_delta=sigma_delta, seed=1000 + n_bits
    )
    chi_idx = e2e._reconstruct_chi_from_bits(bits=bits, m=m)
    chi_hat = e2e._chi_index_to_grid(n_bits=n_bits, chi_idx=chi_idx)
    lap_true = [
        [-8.0 * (math.pi**2) * chi_true[y][x] for x in range(side)]
        for y in range(side)
    ]
    lap_hat = e2e._periodic_laplacian(chi_hat, h=h)
    eps_chi = e2e._max_abs_diff(chi_hat, chi_true)
    lap_err = e2e._max_abs_diff(lap_hat, lap_true)
    c_trunc = amp * (2.0 * math.pi) ** 4 / 6.0
    trunc_bound = c_trunc * (h * h)
    d = 2
    noise_bound = (4.0 * d / (h * h)) * eps_chi
    total_bound = trunc_bound + noise_bound
    max_abs_lap_true = e2e._max_abs_grid(lap_true)
    return ChiCurvResult(
        eps_chi=float(eps_chi),
        lap_err=float(lap_err),
        total_bound=float(total_bound),
        max_abs_lap_true=float(max_abs_lap_true),
    )


@dataclass(frozen=True)
class GammaFamily:
    gamma_min: float
    gamma_max: float
    gamma_mean: float


def _load_gamma_family_for_anchor(n_bits: int, m: int) -> GammaFamily:
    p = paper_root() / "sections/generated/curvature_e2e_gamma_stability_rows.tex"
    rows = _read_rows(p)
    for parts in rows:
        if len(parts) < 9:
            continue
        n0 = int(_parse_tex_float(parts[0]))
        m0 = int(_parse_tex_float(parts[2]))
        if n0 == int(n_bits) and m0 == int(m):
            return GammaFamily(
                gamma_min=_parse_tex_float(parts[4]),
                gamma_max=_parse_tex_float(parts[5]),
                gamma_mean=_parse_tex_float(parts[6]),
            )
    raise ValueError("No matching gamma stability row found for anchor (n_bits,m).")


@dataclass(frozen=True)
class FullFusionGates:
    max_ledger_residual: float
    max_complementarity_free: float
    max_complementarity_trap: float


def _compute_full_fusion_gates(rows_path: Path) -> FullFusionGates:
    rows = _read_rows(rows_path)
    max_ledger = 0.0
    max_comp_free = 0.0
    max_comp_trap = 0.0
    for parts in rows:
        if len(parts) < 18:
            continue
        e_tot = _parse_tex_float(parts[1])
        e_part = _parse_tex_float(parts[2])
        e_field = _parse_tex_float(parts[3])
        e_emit = _parse_tex_float(parts[4])
        e_wh = _parse_tex_float(parts[5])
        resid = abs(e_tot - (e_part + e_field + e_emit + e_wh))
        max_ledger = max(max_ledger, resid)
        v_free = _parse_tex_float(parts[11])
        v_trap = _parse_tex_float(parts[12])
        d_free = _parse_tex_float(parts[13])
        d_trap = _parse_tex_float(parts[14])
        max_comp_free = max(max_comp_free, max(0.0, (v_free * v_free + d_free * d_free) - 1.0))
        max_comp_trap = max(max_comp_trap, max(0.0, (v_trap * v_trap + d_trap * d_trap) - 1.0))
    return FullFusionGates(
        max_ledger_residual=float(max_ledger),
        max_complementarity_free=float(max_comp_free),
        max_complementarity_trap=float(max_comp_trap),
    )


def _pick_qg_interface_row_for_anchor(*, m: int, n: int) -> List[str]:
    p = paper_root() / "sections/generated/qg_interface_suite_rows.tex"
    rows = _read_rows(p)
    for parts in rows:
        if len(parts) < 16:
            continue
        m0 = int(_parse_tex_float(parts[0]))
        n0 = int(_parse_tex_float(parts[1]))
        feasible = parts[7].strip().lower()
        if m0 == int(m) and n0 == int(n) and feasible in {"yes", "true"}:
            return parts
    for parts in rows:
        if len(parts) < 16:
            continue
        m0 = int(_parse_tex_float(parts[0]))
        n0 = int(_parse_tex_float(parts[1]))
        if m0 == int(m) and n0 == int(n):
            return parts
    raise ValueError("No qg_interface_suite row found for the anchor (m,n).")


def _write_numeric(outdir: Path) -> None:
    inst = _load_default_instance()
    n_bits = int(inst.n)
    chi_curv = _compute_chi_curvature_anchor(n_bits=n_bits, m=6)
    gamma_fam = _load_gamma_family_for_anchor(n_bits=n_bits, m=6)

    eps_chi = float(chi_curv.eps_chi)
    eps_lap = float(chi_curv.total_bound)
    gamma_radius = max(
        abs(gamma_fam.gamma_max - gamma_fam.gamma_mean),
        abs(gamma_fam.gamma_mean - gamma_fam.gamma_min),
    )
    eps_g00 = 2.0 * abs(gamma_fam.gamma_mean) * eps_lap + 2.0 * float(gamma_radius) * float(chi_curv.max_abs_lap_true)

    qg_row = _pick_qg_interface_row_for_anchor(m=inst.m, n=inst.n)
    occ_frac = float(_parse_tex_float(qg_row[8]))
    tau_peak = float(_parse_tex_float(qg_row[14]))
    lapse_peak = float(_parse_tex_float(qg_row[15]))
    lapse_far = float(_parse_tex_float(qg_row[16]))

    ff_on = _compute_full_fusion_gates(paper_root() / "sections/generated/full_fusion_rows.tex")
    ff_off = _compute_full_fusion_gates(paper_root() / "sections/generated/full_fusion_nowh_rows.tex")

    write_lines(
        outdir / "qg9_windowed_comparability_numeric_summary.tex",
        [
            r"\noindent\AuditTag QG9-M1 numerical instantiation (default instance): "
            + rf"anchor $(m,n)=({inst.m},{inst.n})$, $K=$ \texttt{{{inst.kernel_family}}}:{inst.kernel_t}, "
            + rf"$N={inst.n_order}$, $\delta={_fmt(inst.delta, nd=4)}$. "
            + r"All quantities below are computed deterministically from the paper's generated artifacts/scripts."
        ],
    )

    lines: List[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(r"\begin{tabular}{p{0.22\textwidth} p{0.20\textwidth} p{0.20\textwidth} p{0.32\textwidth}}")
    lines.append(r"\toprule")
    lines.append(r"$\mathcal{O}$ & numeric proxy/value & $\epsilon$ (numeric) & audit note \\")
    lines.append(r"\midrule")
    lines.append(
        r"$\widehat\chi$ (sup error) & "
        + _fmt(eps_chi, 6)
        + r" & "
        + _fmt(eps_chi, 6)
        + r" & "
        + r"Computed as $\|\widehat\chi-\chi_{\rm true}\|_\infty$ in the end-to-end reconstruction carrier at $n=3,m=6$."
        + r" \\"
    )
    lines.append(
        r"$\Delta_h\widehat\chi$ (Laplacian-stage bound) & "
        + _fmt(chi_curv.lap_err, 6)
        + r" & "
        + _fmt(eps_lap, 6)
        + r" & "
        + r"Computed bound $C h^2+(4d/h^2)\epsilon_\chi$ and realized error $\|\Delta_h\widehat\chi-\Delta\chi_{\rm true}\|_\infty$."
        + r" \\"
    )
    lines.append(
        r"$\widehat G_{00,h}$ (proxy) & "
        + _fmt(eps_g00, 6)
        + r" & "
        + _fmt(eps_g00, 6)
        + r" & "
        + r"Bound uses $\gamma$ family envelope (min/max/mean) and $\max|\Delta\chi_{\rm true}|$ under the same carrier."
        + r" \\"
    )
    lines.append(
        r"$\tau_{\mathrm{WS}}$ (peak) & "
        + _fmt(tau_peak, 6)
        + r" & 0.0 & "
        + r"Breit--Wigner one-channel benchmark in the QG interface suite (analytic carrier)."
        + r" \\"
    )
    lines.append(
        r"$N_{\mathrm{WS}}$ (peak/far) & "
        + _fmt(lapse_peak, 6)
        + r"/"
        + _fmt(lapse_far, 6)
        + r" & 0.0 & "
        + r"Delay-to-lapse mapping in the same analytic carrier; numerical error is zero in this benchmark."
        + r" \\"
    )
    lines.append(
        r"$|\mathcal{R}_\star|/4^n$ (occupancy) & "
        + _fmt(occ_frac, 6)
        + r" & 0.0 & "
        + r"Capacity-only occupancy fraction for the first feasible row at the anchor $(m,n)$ in \texttt{qg\_interface\_suite\_rows.tex}."
        + r" \\"
    )
    lines.append(
        r"Full-fusion ledger gate (max resid; on/off) & "
        + _fmt(ff_on.max_ledger_residual, 6)
        + r"/"
        + _fmt(ff_off.max_ledger_residual, 6)
        + r" & "
        + _fmt(max(ff_on.max_ledger_residual, ff_off.max_ledger_residual), 6)
        + r" & "
        + r"Computed as $\max_t |E_{\rm tot}-(E_{\rm part}+E_{\rm field}+E_{\rm emit}+E_{\rm wh})|$ from generated time-series rows."
        + r" \\"
    )
    lines.append(
        r"Full-fusion complementarity (max violation; free/trap) & "
        + _fmt(ff_on.max_complementarity_free, 6)
        + r"/"
        + _fmt(ff_on.max_complementarity_trap, 6)
        + r" & "
        + _fmt(max(ff_on.max_complementarity_free, ff_on.max_complementarity_trap), 6)
        + r" & "
        + r"Computed as $\max_t \max(0,V^2+D^2-1)$ (wormhole on); off-baseline computed analogously."
        + r" \\"
    )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    write_lines(outdir / "qg9_windowed_comparability_numeric.tex", lines)


def main() -> int:
    out = generated_dir()
    out.mkdir(parents=True, exist_ok=True)

    _write_default_instance(out)
    _write_registry(out)
    _write_budget_mapping(out)
    _write_evidence(out)
    _write_acceptance_checklist(out)
    _write_numeric(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

