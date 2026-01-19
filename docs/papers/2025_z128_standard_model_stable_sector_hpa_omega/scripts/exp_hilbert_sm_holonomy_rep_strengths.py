# -*- coding: utf-8 -*-
"""
Derive compact SU(2)/SU(3) proxy strengths from holonomy aggregated by representation.

Input:
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry/holonomy_aggregate_report.json

Output:
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry/holonomy_rep_strengths.json

Definitions (proxy, auditable):
  - su3_order3_strength := frac(120°)  (3-cycles / 120° rotations)
  - su2_pi_strength     := frac(180°)  (pi rotations; SU(2) trace proxy ~ 0)
  - order4_strength     := frac(90°)
  - trivial_strength    := frac(0°)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from common_paths import figures_dir


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _default_out_dir() -> Path:
    return figures_dir() / "adaptive" / "sm_hilbert_isomorphism" / "wiring_fold_geometry"


def _get_frac(entry: Dict[str, Any], key: str) -> float:
    frac = entry.get("angle_frac", {})
    v = frac.get(key)
    if v is None:
        return float("nan")
    return float(v)


def _summarize_rep_map(by_rep_key: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for rep_key, obj in by_rep_key.items():
        out[rep_key] = {
            "n_incident_plaquettes": int(obj.get("n_incident_plaquettes", 0)),
            "trivial_0": _get_frac(obj, "0"),
            "order4_90": _get_frac(obj, "90"),
            "su3_order3_120": _get_frac(obj, "120"),
            "su2_pi_180": _get_frac(obj, "180"),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--wiring-dir",
        type=str,
        default=str(_default_out_dir()),
        help="Directory containing holonomy_aggregate_report.json (and where outputs will be written).",
    )
    args = ap.parse_args()

    d = Path(str(args.wiring_dir))
    d.mkdir(parents=True, exist_ok=True)
    agg = _read_json(d / "holonomy_aggregate_report.json")

    by2 = agg.get("2d", {}).get("by_rep_key", {})
    by3 = agg.get("3d", {}).get("by_rep_key", {})

    rep2 = _summarize_rep_map(by2)
    rep3 = _summarize_rep_map(by3)

    # Union keys and compute deltas (3D - 2D) for shared reps.
    all_keys = sorted(set(rep2.keys()) | set(rep3.keys()))
    delta: Dict[str, Any] = {}
    for k in all_keys:
        a = rep2.get(k, {})
        b = rep3.get(k, {})
        if not a or not b:
            continue
        delta[k] = {
            "d_su3_order3_120": float(b.get("su3_order3_120", float("nan"))) - float(a.get("su3_order3_120", float("nan"))),
            "d_su2_pi_180": float(b.get("su2_pi_180", float("nan"))) - float(a.get("su2_pi_180", float("nan"))),
            "d_order4_90": float(b.get("order4_90", float("nan"))) - float(a.get("order4_90", float("nan"))),
            "d_trivial_0": float(b.get("trivial_0", float("nan"))) - float(a.get("trivial_0", float("nan"))),
        }

    out = {
        "constraints": agg.get("constraints", {}),
        "m_schedule_by_k": agg.get("m_schedule_by_k", {}),
        "rep_strengths": {
            "2d": rep2,
            "3d": rep3,
            "delta_3d_minus_2d": delta,
        },
        "notes": {
            "su3_order3_120": "fraction of 120° plaquette holonomies (3-cycles proxy)",
            "su2_pi_180": "fraction of 180° plaquette holonomies (pi-rotation proxy; SU(2) trace ~ 0)",
        },
    }

    out_path = d / "holonomy_rep_strengths.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

