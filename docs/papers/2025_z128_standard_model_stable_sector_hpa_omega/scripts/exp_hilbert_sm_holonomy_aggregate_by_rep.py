# -*- coding: utf-8 -*-
"""
Aggregate holonomy diagnostics by SM representation class.

Inputs:
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry/holonomy_report.json
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry/wiring_geometry.json

Output:
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry/holonomy_aggregate_report.json

The main goal is to convert per-label holonomy into per-representation invariants:
  - angle histogram fractions at {0, 90, 120, 180} degrees (proxy classes)
  - aggregated by:
      * label_base (merge generations)
      * rep_tex (literal)
      * rep_tuple (parsed (su3_dim, su2_dim, Y_num, Y_den))
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common_paths import figures_dir


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_out_dir() -> Path:
    return figures_dir() / "adaptive" / "sm_hilbert_isomorphism" / "wiring_fold_geometry"


def _label_base(label_tex: str) -> str:
    # Remove generation superscript ^{(g)} if present.
    s = str(label_tex)
    s = re.sub(r"\^\{\(\d+\)\}", "", s)
    return s


@dataclass(frozen=True)
class RepTuple:
    su3_dim: int
    su2_dim: int
    y_num: int
    y_den: int

    def key(self) -> str:
        if self.y_den == 1:
            y = f"{self.y_num}"
        else:
            y = f"{self.y_num}/{self.y_den}"
        return f"({self.su3_dim},{self.su2_dim})_{y}"


def _gcd(a: int, b: int) -> int:
    a = abs(int(a))
    b = abs(int(b))
    while b:
        a, b = b, a % b
    return int(a)


def _parse_frac(s: str) -> Tuple[int, int]:
    s = s.strip()
    if "/" not in s:
        return (int(s), 1)
    a, b = s.split("/", 1)
    num = int(a.strip())
    den = int(b.strip())
    if den == 0:
        raise ValueError("Invalid fraction with zero denominator.")
    g = _gcd(num, den)
    num //= g
    den //= g
    if den < 0:
        den = -den
        num = -num
    return (num, den)


def _parse_rep_tex(rep_tex: str) -> RepTuple | None:
    # Expected forms like "$(3,2)_{1/6}$" or "$(1,1)_{0}$" or "$-$" (gauge classes).
    s = str(rep_tex).strip()
    if s in ("$-$", "-"):
        return None
    m = re.search(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*_\{\s*([^\}]+)\s*\}", s)
    if not m:
        return None
    su3 = int(m.group(1))
    su2 = int(m.group(2))
    y_raw = m.group(3).strip()
    y_num, y_den = _parse_frac(y_raw)
    return RepTuple(su3_dim=su3, su2_dim=su2, y_num=y_num, y_den=y_den)


def _cycle_hist_to_angle_hist(ct_hist: Dict[str, Any]) -> Dict[str, int]:
    # Map S4 cycle types to SO(3) rotation angles per su3rep convention:
    #  1 -> 0°, 4 -> 90°, 3 -> 120°, 2/2x2 -> 180°.
    h = {str(k): int(v) for k, v in ct_hist.items()}
    out = {"0": int(h.get("1", 0)), "90": int(h.get("4", 0)), "120": int(h.get("3", 0)), "180": int(h.get("2", 0)) + int(h.get("2x2", 0))}
    return out


def _normalize_hist(h: Dict[str, int]) -> Dict[str, float]:
    tot = float(sum(int(v) for v in h.values()))
    if tot <= 0:
        return {k: float("nan") for k in h}
    return {k: float(v) / tot for k, v in h.items()}


def _weighted_add(dst: Dict[str, float], src: Dict[str, float], w: float) -> None:
    for k, v in src.items():
        if v != v:  # nan
            continue
        dst[k] = float(dst.get(k, 0.0)) + float(w) * float(v)


def _aggregate_per_label(per_label: Dict[str, Any], label_to_rep: Dict[str, str]) -> Dict[str, Any]:
    # Build per-label angle fractions + group aggregates.
    by_label: Dict[str, Any] = {}
    by_label_base: Dict[str, Dict[str, Any]] = {}
    by_rep_tex: Dict[str, Dict[str, Any]] = {}
    by_rep_tuple: Dict[str, Dict[str, Any]] = {}

    for lab, entry in per_label.items():
        ct_hist = entry.get("cycle_type_hist", {})
        n_inc = int(entry.get("n_incident_plaquettes", 0))
        ang_hist = _cycle_hist_to_angle_hist(ct_hist)
        ang_frac = _normalize_hist(ang_hist)

        rep_tex = str(label_to_rep.get(lab, entry.get("rep", "$-$")))
        rep_tuple = _parse_rep_tex(rep_tex)
        rep_key = rep_tuple.key() if rep_tuple is not None else "gauge_or_unknown"

        by_label[lab] = {
            "n_incident_plaquettes": n_inc,
            "cycle_type_hist": {str(k): int(v) for k, v in ct_hist.items()},
            "angle_hist": ang_hist,
            "angle_frac": ang_frac,
            "label_base": _label_base(lab),
            "rep_tex": rep_tex,
            "rep_key": rep_key,
        }

        # Aggregate helpers
        def acc(dst: Dict[str, Dict[str, Any]], key: str) -> None:
            obj = dst.get(key)
            if obj is None:
                obj = {"n": 0, "angle_hist": {"0": 0, "90": 0, "120": 0, "180": 0}}
                dst[key] = obj
            obj["n"] = int(obj["n"]) + n_inc
            for kk, vv in ang_hist.items():
                obj["angle_hist"][kk] = int(obj["angle_hist"][kk]) + int(vv)

        acc(by_label_base, _label_base(lab))
        acc(by_rep_tex, rep_tex)
        acc(by_rep_tuple, rep_key)

    def finalize(dst: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, obj in dst.items():
            out[k] = {"n_incident_plaquettes": int(obj["n"]), "angle_hist": dict(obj["angle_hist"]), "angle_frac": _normalize_hist(obj["angle_hist"])}
        return out

    return {
        "by_label": by_label,
        "by_label_base": finalize(by_label_base),
        "by_rep_tex": finalize(by_rep_tex),
        "by_rep_key": finalize(by_rep_tuple),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--wiring-dir",
        type=str,
        default=str(_default_out_dir()),
        help="Directory containing holonomy_report.json and wiring_geometry.json (and where outputs will be written).",
    )
    args = ap.parse_args()

    d = Path(str(args.wiring_dir))
    d.mkdir(parents=True, exist_ok=True)
    hol = _read_json(d / "holonomy_report.json")
    geo = _read_json(d / "wiring_geometry.json")

    # Build label->rep mapping from geometry (authoritative).
    label_to_rep: Dict[str, str] = {}
    for n in geo.get("graph2d", {}).get("nodes", []):
        label_to_rep[str(n.get("label"))] = str(n.get("rep", "$-$"))

    out: Dict[str, Any] = {"constraints": hol.get("constraints", {}), "m_schedule_by_k": hol.get("m_schedule_by_k", {})}
    for dim_key in ("2d", "3d"):
        per_label = hol.get("summary", {}).get(dim_key, {}).get("per_label", {})
        out[dim_key] = _aggregate_per_label(per_label, label_to_rep=label_to_rep)

    out_path = d / "holonomy_aggregate_report.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

