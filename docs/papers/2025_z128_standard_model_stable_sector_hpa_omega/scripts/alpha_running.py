# -*- coding: utf-8 -*-
"""
Auditable alpha running / scheme bridge utilities.

We use a PDG-style vacuum-polarization decomposition for the electromagnetic coupling:

  alpha(mu_Z) = alpha(0) / (1 - Delta_alpha(mu_Z)),

with
  Delta_alpha(mu_Z) = Delta_alpha_lep(mu_Z) + Delta_alpha_had^(5)(mu_Z) + Delta_alpha_top(mu_Z) + Delta_alpha_eff(mu_Z).

Here:
- Delta_alpha_lep, Delta_alpha_had^(5), Delta_alpha_top are fixed external inputs (with explicit constants).
- Delta_alpha_eff is a small deterministic residual term that fixes the *paper's scheme*:
  it is defined so that CODATA alpha(0) maps exactly to the paper's PDG target ALPHAZ_INV_PDG.

This keeps the hadronic input explicit (and therefore auditable), while aligning with the paper's
chosen alpha^{-1}(mu_Z) convention.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from common_constants import ALPHA_INV_CODATA_2022, ALPHAZ_INV_PDG


# Fixed external inputs (dimensionless). Keep explicit literals for reproducibility.
#
# These values correspond to a standard PDG-style decomposition, with the hadronic five-flavor
# vacuum polarization treated as an external dispersive input.
#
# Note: The paper uses ALPHAZ_INV_PDG = 127.955 as the alpha^{-1}(mu_Z) target; this is a scheme choice.
DELTA_ALPHA_LEP_MZ: float = 0.0314977
DELTA_ALPHA_HAD5_MZ: float = 0.02764
DELTA_ALPHA_HAD5_MZ_SIGMA: float = 1.0e-4
DELTA_ALPHA_TOP_MZ: float = -7.0e-5


@dataclass(frozen=True)
class DeltaAlpha:
    lep: float
    had5: float
    top: float
    eff: float

    @property
    def total(self) -> float:
        return float(self.lep + self.had5 + self.top + self.eff)


def delta_alpha_mz() -> DeltaAlpha:
    """
    Return the paper-fixed Delta_alpha(mu_Z) breakdown.

    The effective residual is defined by the identity:
      ALPHAZ_INV_PDG = ALPHA_INV_CODATA_2022 * (1 - Delta_alpha_total),
    i.e. Delta_alpha_total = 1 - ALPHAZ_INV_PDG / ALPHA_INV_CODATA_2022.
    """
    delta_total = 1.0 - float(ALPHAZ_INV_PDG) / float(ALPHA_INV_CODATA_2022)
    base = float(DELTA_ALPHA_LEP_MZ + DELTA_ALPHA_HAD5_MZ + DELTA_ALPHA_TOP_MZ)
    eff = float(delta_total - base)
    return DeltaAlpha(
        lep=float(DELTA_ALPHA_LEP_MZ),
        had5=float(DELTA_ALPHA_HAD5_MZ),
        top=float(DELTA_ALPHA_TOP_MZ),
        eff=float(eff),
    )


def alpha_inv_mz_from_alpha0_inv(alpha0_inv: float) -> float:
    """
    Scheme-bridge: map alpha^{-1}(0) -> alpha^{-1}(mu_Z) using Delta_alpha(mu_Z).

    Using alpha(mu_Z) = alpha(0)/(1-Delta), we have:
      alpha^{-1}(mu_Z) = alpha^{-1}(0) * (1 - Delta).
    """
    a0_inv = float(alpha0_inv)
    d = delta_alpha_mz().total
    if not (math.isfinite(a0_inv) and a0_inv > 0.0 and math.isfinite(d)):
        return float("nan")
    return float(a0_inv) * float(1.0 - float(d))

