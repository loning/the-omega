# -*- coding: utf-8 -*-
"""
Generate a deterministic protocol-net axiom checklist as a LaTeX fragment.

Only the Python standard library is used.
"""

from __future__ import annotations

from common_paths import generated_dir
from common_tex import write_lines


def main() -> None:
    rows = [
        r"isotony & PT & Proposition~\ref{prop:prot_net_isotony} (Appendix~\ref{app:construct_local_net_from_protocol}) \\",
        r"microcausality & PT (subclass) & Corollary~\ref{cor:microcausality_tensor_subclass} (Appendix~\ref{app:protocol_subclass_tensor_net}) \\",
        r"covariance & PT (carrier) & Corollary~\ref{cor:induced_action_on_quasilocal} (Appendix~\ref{app:covariance_from_window_action}) \\",
        r"spectrum condition & CP & Assumption~\ref{ass:spectrum_condition_template} (Appendix~\ref{app:covariance_spectrum_from_protocol_dynamics}); see surrogate contract Appendix~\ref{app:spectrum_surrogate_contract} \\",
        r"domain control (net level) & PT & Proposition~\ref{prop:bounded_generator_net_no_domain} (Appendix~\ref{app:domain_control_for_generators}) \\",
        r"reconstruction & CP & Assumption~\ref{ass:reconstruction_bundle_template} (Appendix~\ref{app:field_reconstruction_theorems}) \\",
        r"scattering & CP & Assumption~\ref{ass:gapped_one_particle_sector_template} (Appendix~\ref{app:scattering_haag_ruelle_theorems}) \\",
    ]
    out = generated_dir() / "protocol_net_axiom_checks_rows.tex"
    write_lines(out, rows)


if __name__ == "__main__":
    main()

