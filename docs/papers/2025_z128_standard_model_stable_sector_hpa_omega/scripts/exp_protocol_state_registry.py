# -*- coding: utf-8 -*-
"""
Protocol-state registry (audit generator).

This script generates a single LaTeX fragment that records, for the main
quantitative outputs of this paper, the declared protocol state components
(m,n,K) and the associated finite-family closure stance (CAP key / tie-break).

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Writes LaTeX fragments into sections/generated/.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class RegistryRow:
    output: str
    protocol_state: str
    kernel_family: str
    closure_note: str


def main() -> int:
    out = generated_dir()
    out.mkdir(parents=True, exist_ok=True)

    # Keep this registry compact and reader-facing: it is an audit index, not a new proof layer.
    rows: List[RegistryRow] = [
        RegistryRow(
            output=r"Joint protocol-state selection (theory-first; $J_\mu$)",
            protocol_state=r"selected $(m^\ast,n^\ast,K^\ast)$ (generated)",
            kernel_family=r"finite $\mathcal{F}_\mu\subset\mathcal{M}\times\mathcal{N}\times\mathcal{K}$",
            closure_note=r"One-shot CAP closure by minimizing $J_\mu=\mathrm{MDL}_\mu+\lambda\,\mathrm{Sens}_\mu$; see Appendix~\ref{subsec:tick_cap_joint_key_contract} and \texttt{sections/generated/protocol\_state\_selected.tex}.",
        ),
        RegistryRow(
            output=r"Electroweak normalization ($\alpha^{-1}(\mu_Z)$, $\sin^2\theta_W(\mu_Z)$)",
            protocol_state=r"$(m,n,K^\ast)$ at $\mu_Z$",
            kernel_family=r"finite $\mathcal{K}$ (Appendix~\ref{app:kernel_family_cap_closure})",
            closure_note=r"Kernel-closed weighted-volume dictionary; CAP tie-break inside $\mathcal{K}$; see Definition~\ref{def:ew_volumes}.",
        ),
        RegistryRow(
            output=r"Mass spectrum template (depth map and matching-layer $\Delta r$)",
            protocol_state=r"anchor $(m,n)=(6,3)$; $K$ optional",
            kernel_family=r"kernel-irrelevant for the deterministic depth ansatz",
            closure_note=r"CAP over a bounded integer ansatz class; optional probabilistic readings must declare $K$ (Section~\ref{sec:mass_spectrum_closure}).",
        ),
        RegistryRow(
            output=r"PMNS closure (mixing angles; bounded family)",
            protocol_state=r"anchor $(m,n)=(6,3)$; $K$ optional",
            kernel_family=r"kernel-irrelevant for the minimal bounded phase/perm families",
            closure_note=r"CAP over bounded discrete candidates; kernel dependence only enters when forming weighted readouts from refined fibers (Section~\ref{sec:pmns_neutrino_closure}).",
        ),
        RegistryRow(
            output=r"$\widehat\chi$ reconstruction and $\gamma$ cross-observation audits (SPARC/proxy)",
            protocol_state=r"$(m,n,K)$ with 1D specialization (Appendix~\ref{app:gamma_crossobs_consistency})",
            kernel_family=r"finite tempered family in the aggregator (tables in Appendix~\ref{app:generated_tables})",
            closure_note=r"Direct/proxy separation; bounded counterfactual sweeps include kernel-family sensitivity of the direct pipeline.",
        ),
        RegistryRow(
            output=r"Cosmology energy-budget interface (occupancy mapping; audit)",
            protocol_state=r"$(m,n,K)$ (Appendix~\ref{app:cosmology_resolution_flow})",
            kernel_family=r"baseline uses microstate-pushforward $\mu_m$ when stated",
            closure_note=r"Occupancy-to-energy mapping is an explicit interface assumption; any probabilistic statements are conditional on declared $K$.",
        ),
        RegistryRow(
            output=r"Protocol RG operator readouts (kernel view; operator audits)",
            protocol_state=r"balanced chain $(m,n)=(2n,n)$; $K$ for readout aggregation",
            kernel_family=r"readout kernels are explicit when scalar summaries are reported",
            closure_note=r"Operator kernels (transport/uplift) are structural; readout kernels $K$ are weighting rules for scalar summaries (Appendix~\ref{app:protocol_rg_operator_closure}).",
        ),
        RegistryRow(
            output=r"Global model selection across families (MDL registry; OP4)",
            protocol_state=r"not a physical state; a declared hypothesis-space registry",
            kernel_family=r"kernel-family scans counted as explicit footprint when applicable",
            closure_note=r"Cross-family look-elsewhere closure inside an explicit registry; finite kernel-family scans treated as explicit search-space enlargement (Appendix~\ref{app:global_model_selection_mdl}).",
        ),
    ]

    lines: List[str] = []
    lines.append(r"\begin{center}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(r"\begin{tabular}{p{0.24\textwidth} p{0.18\textwidth} p{0.22\textwidth} p{0.30\textwidth}}")
    lines.append(r"\toprule")
    lines.append(r"output & protocol state & kernel family & closure note \\")
    lines.append(r"\midrule")
    for r in rows:
        lines.append(f"{r.output} & {r.protocol_state} & {r.kernel_family} & {r.closure_note} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")

    write_lines(out / "protocol_state_registry.tex", lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

