# -*- coding: utf-8 -*-
"""
Audit: CAP-select a scattering toy carrier S(omega) from a bounded family using multiple registry datasets.

This script implements the M2 "if Match dictionary is complete" path:
  - Read the scattering phase registry (vendored).
  - Read the matching-layer energy dictionary.
  - For each dataset with status=complete and a usable resonance width, construct a normalized omega coordinate:
      omega := omega_center + (E - E0)/gamma_scale
      gamma_omega := 1 (by construction)
    so the linewidth proxy target becomes tau_gamma = 4.
  - CAP-select a toy carrier from a bounded family by matching tau_WS(omega_center) to the per-dataset tau_gamma target.

Design constraints:
  - Deterministic output.
  - Standard-library only.

Outputs:
  - sections/generated/scattering_carrier_cap_select_rows.tex
  - sections/generated/scattering_carrier_cap_select_summary.tex
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines

# Reuse the toy model math from the scattering queue script (same paper, deterministic).
from exp_scattering_process_delay_queue_sim import (  # type: ignore
    Resonance,
    ScatteringModel,
    _tau_ws_trace,
)


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _gamma_from_resonance_meta(r0: Dict[str, Any], gamma_field: str) -> Optional[float]:
    if gamma_field == "gamma":
        g = float(r0.get("gamma", float("nan")))
        return float(g) if math.isfinite(g) and g > 0.0 else None
    if gamma_field == "gamma_mid":
        gl = float(r0.get("gamma_low", float("nan")))
        gh = float(r0.get("gamma_high", float("nan")))
        if math.isfinite(gl) and math.isfinite(gh) and gl > 0.0 and gh > 0.0:
            return float(0.5 * (gl + gh))
        return None
    return None


@dataclass(frozen=True)
class Target:
    dataset_id: str
    ab_unit: str
    E0: float
    gamma_scale: float
    omega_center: float
    tau_target: float


def _collect_targets(reg: Dict[str, Any], md: Dict[str, Any]) -> List[Target]:
    mappings: Dict[str, Any] = dict(md.get("mappings", {}) or {})
    out: List[Target] = []

    for d in list(reg.get("datasets", [])):
        did = str(d.get("id", "")).strip()
        if not did:
            continue
        m = dict(mappings.get(did, {}) or {})
        if str(m.get("status", "")).strip() != "complete":
            continue
        model = str(m.get("mapping_model", "")).strip()
        if model != "center_scale_by_gamma" and model != "identity":
            continue

        ab = dict(d.get("abscissa", {}) or {})
        ab_unit = str(ab.get("unit", "")).strip()

        res = list(d.get("resonances", []) or [])
        if not res:
            continue
        ridx = int(dict(m.get("params", {}) or {}).get("resonance_index", 0))
        if ridx < 0 or ridx >= len(res):
            continue
        r0 = dict(res[ridx])
        E0 = float(r0.get("E0", float("nan")))
        if not (math.isfinite(E0)):
            continue

        params = dict(m.get("params", {}) or {})
        omega_center = float(params.get("omega_center", 1.35))

        if model == "identity":
            g = float(r0.get("gamma", float("nan")))
            if not (math.isfinite(g) and g > 0.0):
                continue
            gamma_scale = float(g)
            tau_target = float(4.0 / gamma_scale)
        else:
            gf = str(params.get("gamma_field", "gamma")).strip()
            g = _gamma_from_resonance_meta(r0, gamma_field=gf)
            if g is None:
                continue
            gamma_scale = float(g)
            # In this normalization, gamma_omega := 1, hence tau_gamma := 4.
            tau_target = 4.0

        out.append(
            Target(
                dataset_id=did,
                ab_unit=ab_unit,
                E0=float(E0),
                gamma_scale=float(gamma_scale),
                omega_center=float(omega_center),
                tau_target=float(tau_target),
            )
        )

    out.sort(key=lambda t: t.dataset_id)
    return out


def _cap_select_carrier(targets: List[Target]) -> Tuple[ScatteringModel, float, float]:
    # Explicit bounded family: keep it small and deterministic.
    mix_family = [0.0, 0.37, 0.79]
    # Candidate g1 values (dimensionless in omega units). Since our normalization sets tau_target ~ 4,
    # we can search around g1 ~ 0.5 with a small family.
    g1_family = [0.5, 0.25, 0.125, 0.08]
    r2_family = [
        Resonance(omega0=11.35, gamma=10.0),
        Resonance(omega0=3.35, gamma=5.0),
    ]

    eps = 1e-12
    scored: List[Tuple[Tuple[float, float, float, float], ScatteringModel, float]] = []
    for th in mix_family:
        for g1 in g1_family:
            for r2 in r2_family:
                # Evaluate at the shared omega_center (targets may carry different omega_center; we require consistency).
                oc = float(targets[0].omega_center) if targets else 1.35
                m = ScatteringModel(
                    mix_theta=float(th),
                    r1=Resonance(omega0=float(oc), gamma=float(g1)),
                    r2=r2,
                    loss_amp=0.0,
                    loss_center=float(oc),
                    loss_width=0.22,
                )
                diffs: List[float] = []
                for t in targets:
                    if abs(float(t.omega_center) - float(oc)) > 1e-12:
                        # Mixed omega centers are a Match inconsistency; penalize heavily (still deterministic).
                        diffs.append(10.0)
                        continue
                    tau = float(_tau_ws_trace(float(oc), m))
                    abslog = abs(math.log((abs(tau) + eps) / (abs(float(t.tau_target)) + eps)))
                    diffs.append(float(abslog))
                e = float(sum(diffs) / float(len(diffs))) if diffs else float("nan")
                key = (e, float(th), float(g1), float(r2.gamma))
                scored.append((key, m, e))

    scored.sort(key=lambda x: x[0])
    best_key, best_model, best_e = scored[0]
    second_e = float(scored[1][2]) if len(scored) > 1 else float("nan")
    gap = float(second_e - float(best_e)) if math.isfinite(second_e) else float("nan")
    return best_model, float(best_e), float(gap)


def cap_select_scattering_carrier_m2() -> Tuple[Optional[ScatteringModel], str]:
    """
    Library entrypoint for other scripts.
    Returns (model_or_none, note_string).
    """
    root = paper_root()
    reg = _read_json(root / "data" / "k4_matching" / "scattering_phase_registry.json")
    md = _read_json(root / "data" / "k4_matching" / "energy_unit_dictionary.json")
    targets = _collect_targets(reg, md)
    if len(targets) < 2:
        return None, f"M2 disabled: eligible_targets={len(targets)} (<2)"
    model, e, gap = _cap_select_carrier(targets)
    return (
        model,
        f"M2 enabled: eligible_targets={len(targets)}, objective(mean abs-log)={_fmt(e,6)}, gap={_fmt(gap,6)}",
    )


def main() -> None:
    root = paper_root()
    reg = _read_json(root / "data" / "k4_matching" / "scattering_phase_registry.json")
    md = _read_json(root / "data" / "k4_matching" / "energy_unit_dictionary.json")

    out_dir = generated_dir()
    rows_path = out_dir / "scattering_carrier_cap_select_rows.tex"
    sum_path = out_dir / "scattering_carrier_cap_select_summary.tex"

    targets = _collect_targets(reg, md)
    if not targets:
        write_lines(rows_path, ["% (no eligible targets)"])
        write_lines(
            sum_path,
            [
                r"\paragraph{CAP-selected scattering carrier (multi-dataset; M2).} \AuditTag "
                + r"No eligible datasets (status=complete with usable resonance width) were found in the matching dictionary. "
                + r"Fallback to the M1 benchmark-only anchoring is required.",
            ],
        )
        return

    # Emit target rows.
    rows: List[str] = []
    for t in targets:
        rows.append(
            " & ".join(
                [
                    t.dataset_id.replace("_", r"\_"),
                    t.ab_unit.replace("_", r"\_"),
                    _fmt(t.E0, 6),
                    _fmt(t.gamma_scale, 6),
                    _fmt(t.omega_center, 3),
                    _fmt(t.tau_target, 6),
                ]
            )
            + r" \\"
        )
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows)

    model, e, gap = _cap_select_carrier(targets)
    write_lines(
        sum_path,
        [
            r"\paragraph{CAP-selected scattering carrier (multi-dataset; M2).} \AuditTag "
            + r"We CAP-select a toy carrier $S(\omega)$ from an explicit bounded family by matching the "
            + r"linewidth-proxy target $\tau_\gamma$ on all eligible datasets (those with \texttt{status=complete} in the matching dictionary). "
            + r"The matching convention used here is a local, resonance-centered normalization (when enabled): "
            + r"$\omega:=\omega_c+(E-E_0)/\gamma$ so that $\gamma_\omega=1$ and $\tau_\gamma=4$. "
            + rf"Selected parameters: mix\_theta={_fmt(model.mix_theta,3)}, r1=(omega0={_fmt(model.r1.omega0,3)}, gamma={_fmt(model.r1.gamma,6)}); "
            + rf"objective(mean abs-log)={_fmt(e,6)}, gap={_fmt(gap,6)}.",
        ],
    )


if __name__ == "__main__":
    main()

