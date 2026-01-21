# -*- coding: utf-8 -*-
"""
Hydrogen binding energy scale -> resolution coordinate r(mu) and effective window m_eff (audit helper).

Inputs:
  - data/pdg_minisets/hydrogen_atom_miniset.json

Outputs (LaTeX fragments):
  - sections/generated/hydrogen_binding_resolution_rows.tex
  - sections/generated/hydrogen_binding_resolution_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from common_constants import LOG_PHI, M_E_GEV, PHI
from common_paths import generated_dir, paper_root
from common_tex import write_lines


EV_TO_GEV: float = 1.0e-9


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _r_of_mu(mu: float, mu0: float) -> float:
    return math.log(float(mu) / float(mu0)) / float(LOG_PHI)


def _mu_th(m: int, r_step: float) -> float:
    r_th = (int(m) - 6) * float(r_step)
    return float(M_E_GEV) * float(PHI ** float(r_th))


def _m_eff_from_r(r_mu: float, r_step: float) -> int:
    return 6 + int(math.floor(float(r_mu) / float(r_step)))


def _load_E1_eV(path: Path) -> float:
    raw = _read_json(path)
    for it in raw.get("entries", []):
        if str(it.get("id", "")) == "hydrogen_ground_state_ionization_energy":
            if str(it.get("unit", "")) != "eV":
                raise RuntimeError("Expected ionization energy unit to be eV.")
            return float(it["value"])
    # fallback: quantity match
    for it in raw.get("entries", []):
        if str(it.get("quantity", "")) == "ionization_energy_n1" and str(it.get("unit", "")) == "eV":
            return float(it["value"])
    raise RuntimeError("Could not find hydrogen ground-state ionization energy entry.")


def _fmt_mu_GeV(mu: float) -> str:
    if mu == 0.0:
        return "0"
    if mu < 1.0e-6 or mu >= 1.0e3:
        exp = int(math.floor(math.log10(abs(mu))))
        mant = float(mu) / (10.0**exp)
        return f"{mant:.6g}\\times 10^{{{exp}}}"
    return f"{float(mu):.10g}"


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}g}"


@dataclass(frozen=True)
class Row:
    obj: str
    e_eV: float
    mu_GeV: float
    r_mu: float
    m_eff: int
    mu_th_lo: float
    mu_th_hi: float
    note: str


def main() -> None:
    r_step = 2.0 * math.pi
    data_path = paper_root() / "data" / "pdg_minisets" / "hydrogen_atom_miniset.json"
    e1_eV = _load_E1_eV(data_path)
    mu = float(e1_eV) * float(EV_TO_GEV)
    r_mu = _r_of_mu(mu, float(M_E_GEV))
    m_eff = _m_eff_from_r(r_mu, r_step)
    mu_lo = _mu_th(m_eff, r_step)
    mu_hi = _mu_th(m_eff + 1, r_step)

    # Important interpretation boundary: m<6 is sub-admissible for single-window localized matter.
    # Hydrogen binding energy is a composite low-energy scale; m_eff is only a scale label here.
    note = "composite binding scale"
    if m_eff < 6:
        note = "composite binding scale (below m=6 single-window admissibility)"
    elif m_eff == 6:
        note = "composite binding scale (near m=6 anchor band)"

    row = Row(
        obj="hydrogen (n=1 ionization)",
        e_eV=float(e1_eV),
        mu_GeV=float(mu),
        r_mu=float(r_mu),
        m_eff=int(m_eff),
        mu_th_lo=float(mu_lo),
        mu_th_hi=float(mu_hi),
        note=note,
    )

    lines: List[str] = []
    lines.append(
        " & ".join(
            [
                row.obj.replace("_", r"\_"),
                _fmt(row.e_eV, 8),
                _fmt_mu_GeV(row.mu_GeV),
                _fmt(row.r_mu, 6),
                str(int(row.m_eff)),
                _fmt_mu_GeV(row.mu_th_lo),
                _fmt_mu_GeV(row.mu_th_hi),
                row.note,
            ]
        )
        + r" \\"
    )
    write_lines(generated_dir() / "hydrogen_binding_resolution_rows.tex", lines)

    summary = [
        r"\paragraph{Audit summary (hydrogen binding scale $\mu\to r\to m_{\mathrm{eff}}$).} \AuditTag "
        r"We map the ground-state ionization energy (a composite binding scale) from the vendored miniset "
        r"to $\mu$ in GeV and then to the resolution coordinate $r(\mu)=\log(\mu/m_e)/\log\varphi$ "
        r"using $m_e=\texttt{M\_E\_GEV}$ and $\varphi=\texttt{PHI}$. "
        r"We report the staircase label $m_{\mathrm{eff}}(\mu)=6+\lfloor r(\mu)/r_{\mathrm{step}}\rfloor$ "
        r"with $r_{\mathrm{step}}=2\pi$ (Section~\ref{sec:falsifiability_predictions}). "
        r"Interpretation boundary: values with $m_{\mathrm{eff}}<6$ are \emph{not} treated as "
        r"single-window localized matter (Section~\ref{subsec:matter_as_types}); they are recorded only as "
        r"scale labels for composite low-energy structure.",
    ]
    write_lines(generated_dir() / "hydrogen_binding_resolution_summary.tex", summary)


if __name__ == "__main__":
    main()

