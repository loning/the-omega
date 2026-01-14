# -*- coding: utf-8 -*-
"""
QG pack: QG interface suite + full-fusion + wormhole sweeps + QG9-M1 pack.

This is a convenience merged entry point to reduce the number of QG-facing
scripts and run_all steps a reader has to track.

It calls existing deterministic generators (no logic duplication) and relies on
their own output contracts:
  - exp_qg_interface_suite.py
  - exp_full_fusion_bh_wormhole_measurement.py
  - exp_full_fusion_wormhole_sweep.py
  - exp_full_fusion_wormhole_adaptive_search.py
  - exp_qg9_windowed_comparability_pack.py

Design goals:
  - Deterministic (no timestamps).
  - Standard-library only in this orchestrator.
"""

from __future__ import annotations


def main() -> int:
    # Local imports keep startup fast and make dependencies explicit.
    import exp_qg_interface_suite as qg_suite
    import exp_full_fusion_bh_wormhole_measurement as full_fusion
    import exp_full_fusion_wormhole_sweep as wh_sweep
    import exp_full_fusion_wormhole_adaptive_search as wh_adapt
    import exp_qg9_windowed_comparability_pack as qg9

    qg_suite.main()
    full_fusion.main()
    wh_sweep.main()
    wh_adapt.main()
    qg9.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

