# -*- coding: utf-8 -*-
"""
Generate and audit a fixed scattering-carrier registry entry (CAP-selected; M2).

This script materializes the CAP-selected carrier as a stable JSON artifact under data/k4_matching/,
and emits LaTeX fragments for inclusion in Appendix 78.

Outputs:
  - data/k4_matching/scattering_carrier_registry.json
  - sections/generated/scattering_carrier_registry_summary.tex
  - sections/generated/scattering_carrier_registry_rows.tex
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from common_paths import generated_dir, paper_root
from common_tex import write_lines

from exp_scattering_carrier_cap_select_multi_dataset import (  # type: ignore
    cap_select_scattering_carrier_m2,
)


def _write_json(p: Path, obj: Any) -> None:
    # Preserve insertion order (schema readability); do not sort keys.
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    root = paper_root()
    out = generated_dir()

    model, note = cap_select_scattering_carrier_m2()
    if model is None:
        # Still write fragments (deterministic) but do not overwrite registry.
        write_lines(
            out / "scattering_carrier_registry_summary.tex",
            [
                r"\paragraph{Scattering carrier registry (audit).} \AuditTag "
                + r"No M2 carrier could be selected under the current matching dictionary; registry not updated. "
                + note.replace("_", r"\_"),
            ],
        )
        write_lines(out / "scattering_carrier_registry_rows.tex", ["% (no carrier)"])
        return

    reg_path = root / "data" / "k4_matching" / "scattering_carrier_registry.json"
    obj: Dict[str, Any] = {
        "carrier": {
            "id": "cap_selected_m2_v1",
            "eligible_targets_min": 2,
            "objective": {
                "note": str(note),
                "type": "mean_abs_log_mismatch",
            },
            "omega_center": float(model.r1.omega0),
            "provenance": {
                "phase_registry": "data/k4_matching/scattering_phase_registry.json",
                "energy_dictionary": "data/k4_matching/energy_unit_dictionary.json",
                "selection_script": "scripts/exp_scattering_carrier_cap_select_multi_dataset.py",
            },
            "selected_params": {
                "mix_theta": float(model.mix_theta),
                "r1": {"gamma": float(model.r1.gamma), "omega0": float(model.r1.omega0)},
                "r2": {"gamma": float(model.r2.gamma), "omega0": float(model.r2.omega0)},
            },
            "selection_source": "M2",
        },
        "scope_notes": [
            "Registry of CAP-selected toy scattering carriers S(omega) used by the K4 delay-to-scattering toy pipeline.",
            "This is an audit/matching-layer artifact: it fixes the carrier parameters as a reproducible input to downstream toy simulations.",
            "If this file is missing, scripts may fall back to online CAP selection (M2) or benchmark-only anchoring (M1), but must report the fallback in their generated summaries.",
        ],
        "version": 1,
    }
    _write_json(reg_path, obj)

    # Emit a minimal LaTeX summary + a single-row table.
    rows = [
        " & ".join(
            [
                obj["carrier"]["id"].replace("_", r"\_"),
                f"{obj['carrier']['omega_center']:.3f}",
                f"{obj['carrier']['selected_params']['mix_theta']:.3f}",
                f"{obj['carrier']['selected_params']['r1']['gamma']:.6f}",
                f"{obj['carrier']['selected_params']['r2']['omega0']:.3f}",
                f"{obj['carrier']['selected_params']['r2']['gamma']:.6f}",
            ]
        )
        + r" \\",
        r"\bottomrule",
    ]
    write_lines(out / "scattering_carrier_registry_rows.tex", rows)
    write_lines(
        out / "scattering_carrier_registry_summary.tex",
        [
            r"\paragraph{Scattering carrier registry (audit).} \AuditTag "
            + r"This fragment records a fixed CAP-selected toy scattering carrier as a reproducible registry artifact "
            + r"and is intended to be used by downstream toy simulations (M2-first; M1 fallback if missing). "
            + note.replace("_", r"\_")
            + r".",
        ],
    )


if __name__ == "__main__":
    main()

