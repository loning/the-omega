#!/usr/bin/env python3
"""
CAP-II reproducibility script:
Numerical check of the Breit--Wigner peak Wigner--Smith time delay scaling.

We use the single-channel unitary Breit--Wigner scattering amplitude
  S(E) = (E - E0 - i*gamma/2) / (E - E0 + i*gamma/2)
and estimate dS/dE at E0 by a central difference with step dE.

We then compute
  Q(E) = -i * hbar * S(E)^* * dS/dE
and compare tau_WS(E0)=Q(E0) against 4*hbar/gamma.

This script is deterministic (no randomness).
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _default_out_path() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "sections" / "generated" / "ws_breit_wigner_rows.tex"


def S_breit_wigner(E: float, E0: float, gamma: float) -> complex:
    if gamma <= 0.0:
        raise ValueError("gamma must be positive")
    z = E - E0
    a = 0.5 * gamma
    return complex(z, -a) / complex(z, a)


def dS_dE_central(E: float, E0: float, gamma: float, dE: float) -> complex:
    if dE <= 0.0:
        raise ValueError("dE must be positive")
    Sp = S_breit_wigner(E + dE, E0, gamma)
    Sm = S_breit_wigner(E - dE, E0, gamma)
    return (Sp - Sm) / (2.0 * dE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=_default_out_path())
    parser.add_argument("--E0", type=float, default=0.0)
    parser.add_argument("--hbar", type=float, default=1.0)
    parser.add_argument("--dE", type=float, default=1.0e-6)
    parser.add_argument(
        "--gamma",
        type=float,
        nargs="+",
        default=[0.2, 0.5, 1.0, 2.0, 5.0],
        help="List of linewidths gamma to include.",
    )
    args = parser.parse_args()

    rows: list[str] = []
    for gamma in args.gamma:
        E = args.E0
        S0 = S_breit_wigner(E, args.E0, gamma)
        dS = dS_dE_central(E, args.E0, gamma, args.dE)
        Q = (-1j) * args.hbar * (S0.conjugate() * dS)
        tau_num = Q.real
        tau_pred = 4.0 * args.hbar / gamma
        rel_err = abs(tau_num - tau_pred) / abs(tau_pred)
        rows.append(
            f"{gamma:.6g} & {args.dE:.2e} & {tau_num:.6g} & {tau_pred:.6g} & {rel_err:.3e} \\\\"
        )

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


