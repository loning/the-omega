# -*- coding: utf-8 -*-
"""
BH4/BH5 auxiliary audit: capacity-calibrated queue-model parameters for known black holes.

We reuse Appendix 09's CAP calibration M -> (m*, n*) (matching layer) and then
evaluate the queue-model (at the selected m*) under the preferred BH-like absorption mode
`cyclic_only` (trap absorbs; boundary exits).

Important:
  - The queue model is 1D in m (local alphabet/window). n* is reported as a capacity/screen scale
    indicator but is not simulated explicitly (n* may be huge).

Outputs:
  - sections/generated/bh_capacity_calibrated_queue_params_rows.tex
  - sections/generated/bh_capacity_calibrated_queue_params_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines

import exp_bh_planck_capacity_calibration as calib
import exp_black_hole_queue_equivalence as bhq


def _known() -> List[Tuple[str, float]]:
    return calib._known_bh_family_m_over_msun()


def main() -> None:
    base_vacuum_mass = 64
    msg_text = "TICK-INFORMATION"

    m_set = calib._candidate_m()
    n_set_known = calib._candidate_n_known(max_n=200)
    msun_kg = calib._m_sun_kg()

    rows: List[str] = []
    for name, m_over_msun in _known():
        mass_kg = float(m_over_msun) * float(msun_kg)
        i_bh = calib._i_bh_bits_from_mass(mass_kg)
        m_star, n_star, _ip, delta = calib._best_mn_for_mass(i_bh, m_set, n_set_known)

        # Run the queue model at m_star (cyclic_only).
        r = bhq._run_case(m=int(m_star), base_vacuum_mass=base_vacuum_mass, msg_text=msg_text, mode="cyclic_only")
        ok = r["ok"]
        escape_extra = r["escape_extra"]
        ticks = r["radiation_ticks"]
        t_digits = r["t"]

        rows.append(
            " & ".join(
                [
                    name,
                    f"{m_over_msun:.6g}",
                    str(int(m_star)),
                    str(int(n_star)),
                    f"{float(delta):.6f}",
                    str(int(t_digits)),
                    str(int(escape_extra)),
                    str(int(ticks)),
                    ok,
                ]
            )
            + r" \\"
        )

    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_capacity_calibrated_queue_params_rows.tex", rows)

    summary = [
        r"\paragraph{Capacity-calibrated queue parameters for known black holes (audit).} \AuditTag "
        r"This fragment combines the matching-layer CAP calibration $M\mapsto(m^\ast(M),n^\ast(M))$ "
        r"(Appendix~\ref{app:bh_planck_capacity_calibration}) with the protocol queue model at the selected "
        r"window length $m^\ast(M)$. The addressing scale $n^\ast(M)$ is reported as a capacity/screen indicator "
        r"but is not simulated explicitly here. The queue model is evaluated under the BH-like absorption mode "
        r"\texttt{cyclic\_only}.",
    ]
    write_lines(generated_dir() / "bh_capacity_calibrated_queue_params_summary.tex", summary)

    print("Wrote sections/generated/bh_capacity_calibrated_queue_params_rows.tex")
    print("Wrote sections/generated/bh_capacity_calibrated_queue_params_summary.tex")


if __name__ == "__main__":
    main()

