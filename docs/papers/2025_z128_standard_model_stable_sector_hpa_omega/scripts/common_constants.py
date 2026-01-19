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

# Quark reference masses (GeV). These are scheme-dependent PDG-style inputs used
# for deterministic, auditable threshold/scale diagnostics (e.g. simple 1-loop running
# approximations). Keep as explicit literals (no network dependency).
M_U_GEV: float = 2.16e-3
M_D_GEV: float = 4.67e-3
M_S_GEV: float = 9.30e-2
M_C_GEV: float = 1.27
M_B_GEV: float = 4.18
M_T_GEV: float = 172.76

# PDG/CODATA numeric targets used elsewhere in the paper (dimensionless).
ALPHA_INV_CODATA_2022: float = 137.035999084
ALPHAZ_INV_PDG: float = 127.955
SIN2_THETAW_PDG: float = 0.23122
JARLSKOG_PDG_CENTRAL: float = 3.00e-5

# Representative 1σ uncertainty scales used by audit scripts (explicit, deterministic stress tests).
# When a standard uncertainty is quoted by PDG/CODATA (or representative global fits), we use it
# directly; otherwise the audit scripts document the chosen stress-test scale.
ALPHA_INV_CODATA_2022_SIGMA: float = 2.1e-8
ALPHAZ_INV_PDG_SIGMA: float = 1.0e-2
SIN2_THETAW_PDG_SIGMA: float = 3.0e-5
JARLSKOG_PDG_SIGMA: float = 0.15e-5

# Representative PMNS reference values (dimensionless).
# These are used as *targets* for deterministic closure scripts and correspond to
# representative global-fit central values under PDG conventions.
PMNS_SIN2_T12_REF: float = 0.307
PMNS_SIN2_T23_REF: float = 0.545
PMNS_SIN2_T13_REF: float = 0.0218
# Representative inverted-ordering (IO) reference values (dimensionless), used only for
# robustness/ordering-sensitivity diagnostics (not as mathematical premises).
PMNS_SIN2_T12_REF_IO: float = 0.307
PMNS_SIN2_T23_REF_IO: float = 0.551
PMNS_SIN2_T13_REF_IO: float = 0.0220
# A representative Dirac phase (degrees), used only for the reference reconstruction
# and to set the magnitude target |J_l,ref| in the discrete delta-closure; see the paper
# for the audit separation.
PMNS_DELTA_REF_DEG: float = 195.0

# Representative uncertainty model parameters used by audit scripts (explicit, deterministic stress tests).
PMNS_SIN2_T12_SIGMA: float = 0.013
PMNS_SIN2_T23_SIGMA: float = 0.021
PMNS_SIN2_T13_SIGMA: float = 0.0007
PMNS_DELTA_SIGMA_DEG: float = 30.0

# Representative CKM magnitudes and uncertainty scales used by audit scripts (dimensionless).
CKM_VUS_REF: float = 0.2243
CKM_VUS_SIGMA: float = 5.0e-4
CKM_VCB_REF: float = 0.0422
CKM_VCB_SIGMA: float = 8.0e-4
CKM_VUB_REF: float = 0.00394
CKM_VUB_SIGMA: float = 3.6e-4

# Electroweak reference scale (GeV), used for calibration-sweep diagnostics.
# PDG 2024: Z pole mass.
M_W_GEV: float = 80.377
M_Z_GEV: float = 91.1876
M_H_GEV: float = 125.25


