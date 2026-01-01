# -*- coding: utf-8 -*-
"""
Shared numeric constants and reference values.

We keep PDG/CODATA reference numbers as explicit literals to avoid any network
dependency. These are used for reproducible closure and audit scripts.
"""

from __future__ import annotations

import math

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
LOG_PHI: float = math.log(PHI)

# Reference masses (GeV). Values are consistent with the paper's existing scripts.
M_E_GEV: float = 5.1099895e-4
M_MU_GEV: float = 1.0565838e-1
M_TAU_GEV: float = 1.77686

# PDG/CODATA numeric targets used elsewhere in the paper (dimensionless).
ALPHA_INV_CODATA_2022: float = 137.035999084
ALPHAZ_INV_PDG: float = 127.955
SIN2_THETAW_PDG: float = 0.23122
JARLSKOG_PDG_CENTRAL: float = 3.00e-5

# Electroweak reference scale (GeV), used for calibration-sweep diagnostics.
# PDG 2024: Z pole mass.
M_Z_GEV: float = 91.1876


