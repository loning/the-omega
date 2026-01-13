# -*- coding: utf-8 -*-
"""
Audit: matching-layer dictionary coverage for scattering phase registry -> toy omega.

This script reports which scattering phase datasets (and resonance metadata entries) are eligible
for cross-unit aggregation under a declared matching dictionary.

Design goals:
  - Deterministic output.
  - Standard-library only.

Outputs:
  - sections/generated/scattering_energy_match_dictionary_rows.tex
  - sections/generated/scattering_energy_match_dictionary_summary.tex
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


@dataclass(frozen=True)
class Row:
    dataset_id: str
    abscissa_symbol: str
    abscissa_unit: str
    n_res: int
    gamma_units: List[str]
    dict_status: str
    mapping_model: str


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _uniq(xs: List[str]) -> List[str]:
    out: List[str] = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def main() -> None:
    root = paper_root()
    reg = _read_json(root / "data" / "k4_matching" / "scattering_phase_registry.json")
    md = _read_json(root / "data" / "k4_matching" / "energy_unit_dictionary.json")

    mappings: Dict[str, Any] = dict(md.get("mappings", {}) or {})
    rows: List[str] = []

    parsed: List[Row] = []
    for d in list(reg.get("datasets", [])):
        did = str(d.get("id", "dataset")).strip()
        ab = dict(d.get("abscissa", {}) or {})
        ab_sym = str(ab.get("symbol", "E"))
        ab_unit = str(ab.get("unit", ""))
        res = list(d.get("resonances", []) or [])
        gamma_units = []
        for r in res:
            u = str(r.get("gamma_unit", "")).strip()
            if u:
                gamma_units.append(u)
        gamma_units = _uniq(gamma_units)

        m = dict(mappings.get(did, {}) or {})
        status = str(m.get("status", "missing"))
        model = str(m.get("mapping_model", "missing"))
        parsed.append(
            Row(
                dataset_id=did,
                abscissa_symbol=ab_sym,
                abscissa_unit=ab_unit,
                n_res=int(len(res)),
                gamma_units=gamma_units,
                dict_status=status,
                mapping_model=model,
            )
        )

    # Deterministic ordering by dataset_id.
    parsed.sort(key=lambda r: r.dataset_id)
    for r in parsed:
        rows.append(
            " & ".join(
                [
                    r.dataset_id.replace("_", r"\_"),
                    r.abscissa_symbol.replace("_", r"\_"),
                    r.abscissa_unit.replace("_", r"\_"),
                    str(int(r.n_res)),
                    (",".join(r.gamma_units) if r.gamma_units else "-").replace("_", r"\_"),
                    r.dict_status.replace("_", r"\_"),
                    r.mapping_model.replace("_", r"\_"),
                ]
            )
            + r" \\"
        )
    rows.append(r"\bottomrule")

    out = generated_dir()
    write_lines(out / "scattering_energy_match_dictionary_rows.tex", rows)

    n_total = len(parsed)
    n_complete = sum(1 for r in parsed if r.dict_status == "complete")
    n_incomplete = sum(1 for r in parsed if r.dict_status == "incomplete")
    n_missing = sum(1 for r in parsed if r.dict_status == "missing")
    eligible = [r.dataset_id for r in parsed if r.dict_status == "complete"]
    excluded = [r.dataset_id for r in parsed if r.dict_status != "complete" and r.n_res > 0]

    summary = [
        r"\paragraph{Matching dictionary coverage (scattering registry $\to$ toy $\omega$).} \AuditTag "
        + r"This fragment reports whether each scattering-phase dataset has a declared matching-layer entry "
        + r"that maps its abscissa (energy coordinate) to the toy frequency variable $\omega$ used by the scattering toy carrier. "
        + rf"Counts: total datasets={n_total}, complete={n_complete}, incomplete={n_incomplete}, missing={n_missing}. "
        + r"Eligibility rule (M1 default): only \texttt{status=complete} datasets may be used for cross-unit CAP selection; "
        + r"all other datasets remain audit-only within their declared coordinate.",
        r"\paragraph{Eligible datasets.} \AuditTag "
        + (", ".join([x.replace("_", r"\_") for x in eligible]) if eligible else "none."),
        r"\paragraph{Excluded (resonance-tagged) datasets.} \AuditTag "
        + (", ".join([x.replace("_", r"\_") for x in excluded]) if excluded else "none."),
    ]
    write_lines(out / "scattering_energy_match_dictionary_summary.tex", summary)


if __name__ == "__main__":
    main()

