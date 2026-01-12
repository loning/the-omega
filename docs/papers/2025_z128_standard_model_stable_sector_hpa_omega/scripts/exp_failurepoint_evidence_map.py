# -*- coding: utf-8 -*-
"""
Generate a deterministic failure-point -> evidence/trigger map as a LaTeX fragment.

Only the Python standard library is used.
"""

from __future__ import annotations

from common_paths import generated_dir
from common_tex import write_lines


def main() -> None:
    # Keep content ASCII-only (pdfLaTeX compatibility).
    rows = [
        r"W1 & Appendix~\ref{app:domain_control_for_generators} & Attempting to use unbounded generators without a stable domain; revert to bounded net generation \\",
        r"W2 & Appendix~\ref{app:field_reconstruction_theorems} & No generating fields in declared class / no energy bounds; treat field statements as interface only \\",
        r"W3 & Appendix~\ref{app:wightman_bridge_and_reconstruction} & Graded/braided locality required; naive commutativity mismatch \\",
        r"S1 & Appendix~\ref{app:scattering_haag_ruelle_lsz_interface} & S(omega) not unitary on band (loss/instability); delay becomes proxy with loss model \\",
        r"S2 & Appendix~\ref{app:gapped_sector_evidence_contract} & No gap witness / thresholds dominate; no Haag-Ruelle/LSZ particle interpretation \\",
        r"S3 & Appendix~\ref{app:scattering_haag_ruelle_theorems} & Asymptotic completeness unknown/false; S treated as effective interface object \\",
        r"Spectrum & Appendix~\ref{app:spectrum_surrogate_contract} & Spectrum condition not discharged; use windowed surrogate or downgrade scattering claims \\",
        r"R1 & Appendix~\ref{app:renormalization_dictionary_and_boundaries} & Scheme change shifts parameters; use bounded-family envelopes \\",
        r"R2 & Appendix~\ref{app:renormalization_dictionary_and_boundaries} & Threshold conventions alter running segments; re-audit candidate family \\",
        r"R3 & Appendix~\ref{app:renormalization_dictionary_and_boundaries} & Claim needs nonperturbative control; downgrade to proxy/audit \\",
        r"CL1 & Appendix~\ref{app:minimal_failure_point_templates} & Refinement maps incompatible; no theorem-level continuum limit claim \\",
        r"CL2 & Appendix~\ref{app:minimal_failure_point_templates} & Loop-scale to length map not declared/stable; small-loop ID not usable \\",
        r"CL3 & Appendix~\ref{app:minimal_failure_point_templates} & Regularity/energy bounds for small-loop expansion not discharged \\",
        r"CL4 & Appendix~\ref{app:minimal_failure_point_templates} & No variational convergence/Gamma-limit; E-L not a limit of discrete minimizers \\",
        r"WBR1 & Appendices~\ref{app:eg_causal_perturbation_framework}--\ref{app:eg_st_restoration_algorithm} & BRST broken by normalization; restore via admissible counterterms or record failure \\",
        r"WBR2 & Appendix~\ref{app:anomaly_theorem_filters} & Nonzero anomaly coefficients; ST not restorable by local counterterms \\",
        r"WBR3 & Appendix~\ref{app:strong_eft_remainder_bounds} & Truncation leaves higher-order breaking; include explicit remainder budget \\",
    ]
    out = generated_dir() / "failurepoint_evidence_map_rows.tex"
    write_lines(out, rows)


if __name__ == "__main__":
    main()

