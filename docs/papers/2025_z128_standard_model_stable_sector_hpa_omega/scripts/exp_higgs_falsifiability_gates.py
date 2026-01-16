# -*- coding: utf-8 -*-
"""
Generate protocol-facing falsifiability gates for the Higgs uplift module.

These are *internal* falsifiability statements in the manuscript's sense:
given the declared protocol primitives and scripts, rerunning must reproduce the
same deterministic certificates (pairing, correlations, robustness envelopes).

Outputs
  - sections/generated/higgs_falsifiability_gates_rows.tex
  - sections/generated/higgs_falsifiability_gates_summary.tex
  - figures/adaptive/higgs_geometry/data/higgs_falsifiability_gates.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common_paths import figures_dir, generated_dir
from common_tex import write_lines


def _load_json(p: Path) -> Dict[str, Any]:
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise TypeError(f"Expected dict JSON at {p}")
    return obj


def _pairing_from_doublet_json(obj: Dict[str, Any]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    dbl = obj.get("doublet", {})
    if not isinstance(dbl, dict):
        raise TypeError("doublet must be dict")
    H1 = dbl.get("H1", {})
    H2 = dbl.get("H2", {})
    if not (isinstance(H1, dict) and isinstance(H2, dict)):
        raise TypeError("H1/H2 must be dict")
    p1 = (int(H1["re"]), int(H1["im"]))
    p2 = (int(H2["re"]), int(H2["im"]))
    return p1, p2


def _canon_pairing(p: Tuple[Tuple[int, int], Tuple[int, int]]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    (a, b), (c, d) = p
    q1 = tuple(sorted((int(a), int(b))))
    q2 = tuple(sorted((int(c), int(d))))
    return tuple(sorted((q1, q2)))  # type: ignore[return-value]


def main() -> None:
    root_fig = figures_dir() / "adaptive" / "higgs_geometry"
    j2d = root_fig / "data" / "higgs_doublet_structure_m10.json"
    j3d = root_fig / "data" / "higgs_doublet_structure_m10_3d.json"
    jrob = root_fig / "data" / "higgs_doublet_robustness_sweep.json"

    o2d = _load_json(j2d)
    o3d = _load_json(j3d)
    orob = _load_json(jrob)

    p2d = _canon_pairing(_pairing_from_doublet_json(o2d))
    p3d = _canon_pairing(_pairing_from_doublet_json(o3d))
    pcanon = ((0, 3), (1, 2))
    pcanon_c = _canon_pairing(pcanon)

    # Extract a few stable numeric summaries for audit-facing gates.
    def chan_summary(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        ch = obj.get("channels", [])
        if not isinstance(ch, list):
            return []
        out: List[Dict[str, Any]] = []
        for x in ch:
            if not isinstance(x, dict):
                continue
            out.append(
                {
                    "name": str(x.get("name", "")),
                    "mu": float(x.get("mu", 0.0)),
                    "var": float(x.get("var", 0.0)),
                    "corr_with_turn": float(x.get("corr_with_turn", 0.0)),
                }
            )
        return out

    ch2d = chan_summary(o2d)
    obj2d = float(o2d.get("doublet", {}).get("objective", 0.0)) if isinstance(o2d.get("doublet", {}), dict) else 0.0

    # Robustness match rate (already computed in the sweep summary; recompute here deterministically)
    rows = orob.get("rows", [])
    match_rate = 0.0
    if isinstance(rows, list) and rows:
        ok = 0
        for r in rows:
            if isinstance(r, dict) and bool(r.get("match_canon", False)):
                ok += 1
        match_rate = ok / float(len(rows))

    # Emit LaTeX table rows: (gate id, expected value, evidence pointer, fail cue)
    gate_rows: List[str] = []
    gate_rows.append(
        r"HIG-G1 & $m{=}10,n{=}5$ (2D) pairing $=\{\{0,3\},\{1,2\}\}$ & "
        r"Figure~\ref{fig:higgs_doublet_structure_m10_2d}, JSON certificate & "
        r"Different pairing under the same declared script/state \\"
    )
    gate_rows.append(
        r"HIG-G2 & $m{=}10,n_3{=}4$ (3D) pairing matches 2D & "
        r"Figure~\ref{fig:higgs_doublet_structure_m10_3d}, JSON certificate & "
        r"2D/3D disagreement under occupied-only coarse graining \\"
    )
    gate_rows.append(
        rf"HIG-G3 & robustness match rate $\approx {match_rate:.3f}$ (bounded family) & "
        r"Table~\ref{tab:higgs_doublet_robustness_sweep}, Figure~\ref{fig:higgs_doublet_robustness_sweep} & "
        r"Unexpected flip under declared variants (addressing/block/sparse) \\"
    )
    gate_rows.append(
        r"HIG-G4 & quantum-number CAP minimizer $(1,2)_{1/2}$ & "
        r"Table~\ref{tab:higgs_quantum_numbers_cap_closure} & "
        r"Minimizer changes under the same bounded family/tie-break \\"
    )
    gate_rows.append(
        r"HIG-G5 & renormalizable Yukawa family exists (up,down,$e$,$\nu$) & "
        r"Table~\ref{tab:higgs_yukawa_feasibility} & "
        r"Any required operator fails gauge invariance under $Q=T_3+Y$ \\"
    )
    gate_rows.append(
        r"HIG-G6 & CAP-minimal EWSB potential is Mexican hat & "
        r"Table~\ref{tab:higgs_ewsb_potential_closure} & "
        r"Alternative low-degree template satisfies all gates and beats the minimizer \\"
    )

    write_lines(generated_dir() / "higgs_falsifiability_gates_rows.tex", gate_rows)

    summary = [
        "\\noindent "
        "Higgs uplift falsifiability gates (protocol-language): the Higgs module is audited by machine-checkable certificates "
        "for (i) the uplift-derived doublet pairing at $m=10$ on 2D/3D Hilbert screens, "
        "(ii) the bounded-family robustness envelope across addressing/coarse-graining counterfactuals, "
        "and (iii) the bounded-family CAP closures for quantum numbers, Yukawa feasibility, and the minimal EWSB potential form. "
        "Reproducing these certificates is the required internal falsifiability check for the Higgs uplift interface."
    ]
    write_lines(generated_dir() / "higgs_falsifiability_gates_summary.tex", summary)

    out_json = root_fig / "data" / "higgs_falsifiability_gates.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(
            {
                "pairing_canonical": pcanon_c,
                "pairing_2d": p2d,
                "pairing_3d": p3d,
                "objective_2d": obj2d,
                "channels_2d": ch2d,
                "robustness_match_rate": match_rate,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("Wrote sections/generated/higgs_falsifiability_gates_rows.tex")
    print("Wrote sections/generated/higgs_falsifiability_gates_summary.tex")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

