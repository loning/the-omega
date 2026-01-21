# -*- coding: utf-8 -*-
"""
Equivalence-ladder certificate registry (audit generator).

This script generates a deterministic registry table for the BH/WH <-> scattering/decay
equivalence ladder. It is audit-only: it records declared triggers/observables/gates/fallbacks
and points to where concrete artifacts live in the manuscript.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/equivalence_ladder_registry_rows.tex
  - sections/generated/equivalence_ladder_registry_summary.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


def _tex_escape(s: str) -> str:
    return s.replace("_", r"\_")


@dataclass(frozen=True)
class Entry:
    cert_id: str
    step: str
    carrier: str
    observables: str
    gates: str
    pointers: str


def _entries() -> List[Entry]:
    # The list is intentionally short and canonical: it matches the ladder narrative and
    # points to the auditable artifacts and failure points already normalized elsewhere.
    return [
        Entry(
            cert_id="C1",
            step=r"BH-like saturation $\leftrightarrow$ delay-driven backlog",
            carrier=r"interface/audit (queue record)",
            observables=r"frac\_q$>q_\star$, max\_q; $\overline{\tau}_{\mathrm{WS}}$",
            gates=r"(S1) unitarity window; declared band/grid",
            pointers=r"App.~\ref{app:scattering_bh_toy_equivalence_audits}, Tab.~\ref{tab:scattering_bh_queue_equivalence_toy}",
        ),
        Entry(
            cert_id="C2",
            step=r"leak/evaporation $\leftrightarrow$ decay exit (width/lifetime proxy)",
            carrier=r"interface/audit (finite families)",
            observables=r"$P_f(t)$, $\Gamma_f$, $\tau_f$; exit-channel tokens",
            gates=r"finite-family discipline; CAP tie-break",
            pointers=r"App.~\ref{app:leakage_kernel}, Def.~\ref{def:survival_kernel_family}",
        ),
        Entry(
            cert_id="C3",
            step=r"scattering delay $\leftrightarrow$ phase/logdet bookkeeping",
            carrier=r"interface (dictionary)",
            observables=r"$\tau_{\mathrm{WS}}(\omega)=-\iu\,\dd(\log\det S)/\dd\omega$",
            gates=r"(S1) (approx.) unitarity + differentiability on band",
            pointers=r"App.~\ref{app:scattering_haag_ruelle_lsz_interface}, Lem.~\ref{lem:wigner_smith_trace_logdet}",
        ),
        Entry(
            cert_id="C4",
            step=r"wormhole-like shortcut $\leftrightarrow$ finite-rank update (operator dictionary)",
            carrier=r"operator dictionary (resolvent/det)",
            observables=r"logdet increment; resolvent-trace delay proxy",
            gates=r"(B5)/(IC13) HTF-lite optional; otherwise operator-only baseline",
            pointers=r"App.~\ref{app:operator_mother_space} (Lem.~\ref{lem:rank_one_det_sherman_morrison}--\ref{lem:finite_rank_det_woodbury}); "
            r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:wormhole_finite_rank_delay_logdet_audit}",
        ),
        Entry(
            cert_id="C6",
            step=r"added edge $\leftrightarrow$ rank-2 update $\leftrightarrow$ det packaging",
            carrier=r"top/operator (graph det)",
            observables=r"$D(z)=\det(I-zA)$ ratio; $\Delta\log|D|$",
            gates=r"finite graph toy; resolvent domain (invertibility)",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:added_edge_det_update_audit}",
        ),
        Entry(
            cert_id="C7",
            step=r"det phase $\leftrightarrow$ scalar unitary $S(\omega)$ $\leftrightarrow$ delay proxy",
            carrier=r"frequency-domain packaging (audit)",
            observables=r"$\phi(\omega)=\arg D(r\e^{\iu\omega})$; $\tau=\dd\phi/\dd\omega$",
            gates=r"declared (r, omega-grid); phase unwrapping; finite-difference stability",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:det_phase_delay_proxy_audit}",
        ),
        Entry(
            cert_id="C8",
            step=r"delay proxy trace identity: $\tau=\Im(-\iu z\,\Tr(A(I-zA)^{-1}))$",
            carrier=r"operator/determinant (audit identity)",
            observables=r"$\tau_{\mathrm{fd}}$ vs $\tau_{\mathrm{tr}}$; err bounds",
            gates=r"resolvent domain (invertibility); numerical stability",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:det_phase_delay_trace_identity_audit}",
        ),
        Entry(
            cert_id="C9",
            step=r"unitary $S(\omega)$ proxy: $\tfrac12\Tr Q \leftrightarrow \tau$ (WS dictionary closure)",
            carrier=r"scattering dictionary (audit toy)",
            observables=r"$Q=-\iu S^\dagger S'$; $\tfrac12\Tr Q$ vs $\tau_{\mathrm{tr}}$",
            gates=r"(S1) is trivial in toy (exact unitary); gate away from det zeros",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:det_to_smatrix_ws_delay_audit}",
        ),
        Entry(
            cert_id="C10",
            step=r"resonance peak $\leftrightarrow$ linewidth $\Gamma$ $\leftrightarrow$ lifetime proxy",
            carrier=r"delay/linewidth dictionary (audit toy)",
            observables=r"$\tau_{\max}$; $\Gamma_{\mathrm{FWHM}}$; $\Gamma_\tau=4/\tau_{\max}$",
            gates=r"finite window + grid; peak selection; FWHM existence",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:det_delay_linewidth_audit}",
        ),
        Entry(
            cert_id="C11",
            step=r"linewidth $\Gamma \Rightarrow$ survival kernel $P(t)=\exp(-\Gamma t)$ (leakage dictionary closure)",
            carrier=r"decay/evaporation dictionary (audit toy)",
            observables=r"$\tau=1/\Gamma$; $P(t)$ at declared times",
            gates=r"rate proxy must be nonnegative; declared time grid",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:linewidth_survival_kernel_audit}",
        ),
        Entry(
            cert_id="C12",
            step=r"finite-family survival kernels: CAP selection and rate proxy $\Gamma_f$",
            carrier=r"finite-family discipline (audit)",
            observables=r"$\Gamma_f$; $\tau_f$; $P_f(t)$; CAP-selected row",
            gates=r"explicit finite family + deterministic tie-break",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:survival_finite_family_audit}",
        ),
        Entry(
            cert_id="C13",
            step=r"Ihara/Hashimoto/Bass determinant packaging $\leftrightarrow$ added-edge update ratio",
            carrier=r"graph zeta / det packaging (audit toy)",
            observables=r"$\det(I-uB)$; Bass determinant; edge/base ratio",
            gates=r"degree>=2 (toy uses cycle); declared u-grid",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:ihara_hashimoto_added_edge_audit}",
        ),
        Entry(
            cert_id="C14",
            step=r"dimension-changing update: $\det(I-uB_{\mathrm{new}})/\det(I-uB_{\mathrm{old}})=\det(S(u))$ (Schur factor)",
            carrier=r"graph zeta / block determinant (audit identity)",
            observables=r"ratio (direct) vs ratio (Schur); err",
            gates=r"det(I-uB_old) nonzero on grid; explicit block split",
            pointers=r"App.~\ref{app:equivalence_ladder_certificates}, Tab.~\ref{tab:hashimoto_added_edge_schur_audit}",
        ),
        Entry(
            cert_id="C15",
            step=r"local interface factorization contract: small det factor (Woodbury/Schur)",
            carrier=r"operator mother space (audit unification)",
            observables=r"det ratio = det(small factor) in both regimes",
            gates=r"declared baseline + explicit interface split; no hidden degrees of freedom",
            pointers=r"App.~\ref{app:operator_mother_space}, Rem.~\ref{rem:local_interface_factorization_contract}; "
            r"App.~\ref{app:equivalence_ladder_certificates}, Tabs.~\ref{tab:wormhole_finite_rank_delay_logdet_audit},\ref{tab:hashimoto_added_edge_schur_audit}",
        ),
        Entry(
            cert_id="C5",
            step=r"four-way unification as a contract form",
            carrier=r"audit thesis (contract)",
            observables=r"ledger form + gate checklist",
            gates=r"hard gates in full-fusion interface; explicit fallbacks",
            pointers=r"Prop.~\ref{prop:four_way_unification_contract_form}, Rem.~\ref{rem:four_way_unification_contract_fallback}",
        ),
    ]


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "equivalence_ladder_registry_rows.tex"
    sum_path = out_dir / "equivalence_ladder_registry_summary.tex"

    rows: List[str] = []
    for e in _entries():
        rows.append(
            " & ".join(
                [
                    _tex_escape(e.cert_id),
                    e.step,
                    _tex_escape(e.carrier),
                    _tex_escape(e.observables),
                    _tex_escape(e.gates),
                    e.pointers,
                ]
            )
            + r" \\"
        )
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Certificate registry (equivalence ladder).} \AuditTag "
            + r"The table records a minimal set of canonical certificates for the BH/WH $\leftrightarrow$ scattering/decay equivalence ladder. "
            + r"Each row is a declared contract: it names the trigger and readout observable, the required gate/failure point instance, "
            + r"and where the corresponding reproducible artifact or dictionary lives in the manuscript.",
            r"\paragraph{Discipline.} \AuditTag "
            + r"Rows are not claims of ontological identity. They are audit entries: if the named gate fails, the step must revert to its declared fallback "
            + r"(typically a weaker interface comparison or a pure bookkeeping statement).",
        ],
    )


if __name__ == "__main__":
    main()

