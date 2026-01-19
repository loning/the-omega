# -*- coding: utf-8 -*-
"""
Audit: U(1) interface strengths (from a concrete wiring) -> alpha linkage.

This mirrors the style of exp_k4_alpha_link_audit.py:
  - finite family of low-complexity aggregations
  - coarse bounded scale family
  - deterministic minimax log-mismatch to two targets:
      * alpha_em^{-1} (CODATA) and alpha^{-1}(m_Z) (PDG)

Input:
  <wiring-dir>/u1_interface_strengths.json

Outputs (LaTeX fragments):
  - sections/generated/sm_hilbert_u1_alpha_link_<wiring-dir-name>_rows.tex
  - sections/generated/sm_hilbert_u1_alpha_link_<wiring-dir-name>_summary.tex

English-only output.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from common_constants import ALPHA_INV_CODATA_2022, ALPHAZ_INV_PDG
from common_paths import generated_dir
from common_tex import write_lines

import alpha_running as arun

def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _safe_log(x: float) -> float:
    return math.log(max(1e-300, float(x)))


SCALE_MODE = "extend_scale"  # or "pow10_only"
SCALE_CS_EXTENDED = [1.0, 1.25, 1.5, 2.0, 2.5, 4.0, 5.0, 8.0]
SCALE_E_MIN = -6
SCALE_E_MAX = 6


def _scale_family() -> List[float]:
    # Finite and auditable; optionally denser than pure 10^e to reduce step-like quantization.
    mode = str(SCALE_MODE)
    cs = [1.0] if mode == "pow10_only" else list(SCALE_CS_EXTENDED)
    scales = []
    for e in range(int(SCALE_E_MIN), int(SCALE_E_MAX) + 1):
        p = 10.0 ** int(e)
        for c in cs:
            scales.append(float(c) * float(p))
    return sorted(set(float(s) for s in scales))


@dataclass(frozen=True)
class Edge:
    s: float  # interface strength


def _edges_from_u1_report(rep: Dict[str, Any], mode: str) -> List[Edge]:
    # Backward/forward compatible:
    # - rep can be the analysis dict directly
    # - or a wrapper {selected, coarse, micro}; in that case default to coarse unless
    #   the caller already selected a sub-dict.
    if "coarse" in rep and isinstance(rep.get("coarse"), dict) and "edges" not in rep:
        rep = rep.get("coarse", {})
    edges = []
    for e in rep.get("edges", []):
        flow = float(e.get("flow_u1", 0.0))
        mis = float(e.get("mis_u1", 0.0))
        ham = float(e.get("hamming_cost", 0.0))
        if mode == "flow_plus_mis":
            s = flow + mis
        elif mode == "mis_only":
            s = mis
        elif mode == "hamming":
            s = ham
        else:
            raise ValueError(mode)
        edges.append(Edge(s=float(s)))
    return edges


def _aggregate(values: Sequence[float], agg_id: str, k: int) -> float:
    xs = [float(x) for x in values]
    if not xs:
        return float("nan")
    if agg_id == "mean_s":
        return float(sum(xs) / len(xs))
    if agg_id == "sum_s":
        return float(sum(xs))
    if agg_id == "sum_log1p_s":
        return float(sum(math.log1p(max(0.0, x)) for x in xs))
    if agg_id == "mean_pow_s":
        return float(sum((max(0.0, x) ** int(k)) for x in xs) / len(xs))
    if agg_id == "mean_inv1p_s_pow":
        return float(sum((1.0 / (1.0 + max(0.0, x))) ** int(k) for x in xs) / len(xs))
    if agg_id == "sum_neg_log1p_s":
        return float(sum(-_safe_log(1.0 + max(0.0, x)) for x in xs))
    raise ValueError(agg_id)


def _candidates() -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = [
        ("mean_s", 1),
        ("sum_s", 1),
        ("sum_log1p_s", 1),
        ("sum_neg_log1p_s", 1),
    ]
    for k in (1, 2, 3):
        out.append(("mean_pow_s", k))
        out.append(("mean_inv1p_s_pow", k))
    return out


def _audit_one(
    *,
    label: str,
    edges: List[Edge],
    alpha_low: float,
    alpha_z: float,
) -> Tuple[List[str], List[str]]:
    xs = [e.s for e in edges]
    n = len(xs)
    header = [rf"\textbf{{{label}}}: $n_{{\mathrm{{edges}}}}={n}$."]
    if n == 0:
        return header, ["% (no edges)"]
    if max(xs) <= 0.0:
        return header, ["% (all zero strengths; no U(1) signal on cross-m edges)"]

    scored: List[Tuple[Tuple[float, float, int], str, float, float, float]] = []
    for agg_id, k in _candidates():
        base = _aggregate(xs, agg_id=agg_id, k=int(k))
        if not math.isfinite(base) or base <= 0.0:
            continue
        best = None
        for s in _scale_family():
            pred0 = float(s) * float(base)
            predz = arun.alpha_inv_mz_from_alpha0_inv(float(pred0))
            if not (math.isfinite(pred0) and pred0 > 0.0 and math.isfinite(predz) and predz > 0.0):
                e_low = float("inf")
                e_z = float("inf")
                e_inf = float("inf")
            else:
                e_low = abs(math.log(pred0 / alpha_low))
                e_z = abs(math.log(predz / alpha_z))
                e_inf = max(e_low, e_z)
            key = (e_inf, e_low + e_z, len(agg_id) + int(k))
            if best is None or key < best[0]:
                best = (key, pred0, predz, e_low, e_z, s)
        assert best is not None
        key, pred0, predz, e_low, e_z, _s = best
        scored.append((key, f"{agg_id}(k={k})", float(pred0), float(predz), float(e_low), float(e_z)))

    scored.sort(key=lambda t: t[0])
    rows: List[str] = []
    for i, (_key, name, pred0, predz, e_low, e_z) in enumerate(scored[:12], start=1):
        rows.append(
            " & ".join(
                [
                    str(i),
                    name,
                    _fmt(pred0, 6),
                    _fmt(predz, 6),
                    _fmt(e_low, 6),
                    _fmt(e_z, 6),
                ]
            )
            + r" \\"
        )
    if not rows:
        rows = ["% (no finite candidates)"]
    return header, rows


def _best_joint_all(
    groups: Dict[str, Sequence[float]], *, alpha_low: float, alpha_z: float
) -> Optional[Dict[str, Any]]:
    """
    Choose ONE (candidate, scale) to minimize the worst-case minimax log-mismatch across:
      - targets {alpha_low, alpha_z}
      - all named groups in `groups`
    """
    clean: Dict[str, List[float]] = {}
    for name, xs in groups.items():
        ys = [float(x) for x in xs if math.isfinite(float(x))]
        if not ys:
            return None
        if max(ys) <= 0.0:
            return None
        clean[str(name)] = ys

    best = None
    for agg_id, k in _candidates():
        bases: Dict[str, float] = {}
        ok = True
        for gname, xs in clean.items():
            base = _aggregate(xs, agg_id=agg_id, k=int(k))
            if not math.isfinite(base) or base <= 0.0:
                ok = False
                break
            bases[gname] = float(base)
        if not ok:
            continue

        local_best = None
        for s in _scale_family():
            worst = 0.0
            worst_sum = 0.0
            per: Dict[str, Dict[str, float]] = {}
            for gname, base in bases.items():
                pred0 = float(s) * float(base)
                predz = arun.alpha_inv_mz_from_alpha0_inv(float(pred0))
                if not (math.isfinite(pred0) and pred0 > 0.0 and math.isfinite(predz) and predz > 0.0):
                    e_low = float("inf")
                    e_z = float("inf")
                    e_inf = float("inf")
                else:
                    e_low = abs(math.log(pred0 / float(alpha_low)))
                    e_z = abs(math.log(predz / float(alpha_z)))
                    e_inf = max(e_low, e_z)
                per[gname] = {"pred0": float(pred0), "predz": float(predz), "e_low": float(e_low), "e_z": float(e_z), "e_inf": float(e_inf)}
                worst = max(worst, float(e_inf))
                worst_sum = max(worst_sum, float(e_low + e_z))
            key = (float(worst), float(worst_sum), len(agg_id) + int(k), abs(math.log10(float(s))))
            if local_best is None or key < local_best[0]:
                local_best = (key, s, per)
        assert local_best is not None
        key, s, per = local_best
        rec = {
            "candidate": f"{agg_id}(k={k})",
            "scale": float(s),
            "e_inf": float(key[0]),
            "per_group": per,
            "delta_alpha": {
                "lep": float(arun.delta_alpha_mz().lep),
                "had5": float(arun.delta_alpha_mz().had5),
                "top": float(arun.delta_alpha_mz().top),
                "eff": float(arun.delta_alpha_mz().eff),
                "total": float(arun.delta_alpha_mz().total),
            },
            "_key2": float(key[1]),
        }
        if best is None or (float(rec["e_inf"]), float(rec["_key2"])) < (float(best["e_inf"]), float(best["_key2"])):
            best = rec

    if best is None:
        return None
    best.pop("_key2", None)
    best["groups"] = sorted(clean.keys())
    return best


def _audit_joint_all(*, tag: str, rep: Dict[str, Any], mode: str, alpha_low: float, alpha_z: float) -> Tuple[List[str], List[str]]:
    """
    Joint audit across {graph2d,graph3d} x {micro,coarse}, using ONE shared (candidate,scale).
    """
    groups: Dict[str, Sequence[float]] = {}
    counts: Dict[str, int] = {}
    for gkey in ("graph2d", "graph3d"):
        gg = rep.get(gkey, {})
        for layer in ("micro", "coarse"):
            sub = gg
            if layer == "micro" and isinstance(gg, dict) and "micro" in gg:
                sub = gg.get("micro", {})
            if layer == "coarse" and isinstance(gg, dict) and "coarse" in gg:
                sub = gg.get("coarse", {})
            edges = _edges_from_u1_report(sub, mode=mode)
            xs = [e.s for e in edges]
            name = f"{gkey}:{layer}"
            groups[name] = xs
            counts[name] = int(len(xs))

    header = [
        rf"\textbf{{{tag}:joint_all:{mode}}}: "
        + ", ".join([rf"\texttt{{{k}}}: $n_{{\mathrm{{edges}}}}={counts[k]}$" for k in sorted(counts.keys())])
        + "."
    ]

    best = _best_joint_all(groups, alpha_low=alpha_low, alpha_z=alpha_z)
    if best is None:
        return header, ["% (joint-all: no valid candidate; missing edges or all-zero strengths in at least one group)"]

    rows: List[str] = []
    rows.append(r"% joint-all best: one (candidate,scale) shared across all groups")
    rows.append(r"\midrule")
    rows.append(r"\multicolumn{6}{l}{\textbf{Joint-all best (shared candidate+scale across all groups)}} \\")
    rows.append(
        " & ".join(
            [
                r"\textbf{candidate}",
                r"\textbf{scale}",
                r"\textbf{$e_{\infty}$}",
                "",
                "",
                "",
            ]
        )
        + r" \\"
    )
    rows.append(
        " & ".join([best["candidate"], _fmt(best["scale"], 6), _fmt(best["e_inf"], 6), "", "", ""]) + r" \\"
    )
    rows.append(r"\addlinespace")
    rows.append(r"\multicolumn{6}{l}{\textbf{Per-group predictions and mismatches}} \\")
    rows.append(r"group & pred$_0$ & pred$_Z$ & $e_{\mathrm{low}}$ & $e_Z$ & $e_{\infty}$ \\")
    for gname in best.get("groups", []):
        rec = best["per_group"].get(gname, {})
        rows.append(
            " & ".join(
                [
                    rf"\texttt{{{gname}}}",
                    _fmt(float(rec.get("pred0", float("nan"))), 6),
                    _fmt(float(rec.get("predz", float("nan"))), 6),
                    _fmt(float(rec.get("e_low", float("nan"))), 6),
                    _fmt(float(rec.get("e_z", float("nan"))), 6),
                    _fmt(float(rec.get("e_inf", float("nan"))), 6),
                ]
            )
            + r" \\"
        )
    return header, rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiring-dir", type=str, required=True, help="Directory containing u1_interface_strengths.json")
    ap.add_argument("--mode", type=str, default="flow_plus_mis", choices=["flow_plus_mis", "mis_only", "hamming"])
    ap.add_argument("--layer", type=str, default="coarse", choices=["coarse", "micro"], help="Which scan-layer to audit (default: coarse).")
    ap.add_argument("--joint-all", action="store_true", help="Audit one shared (candidate,scale) across {2D,3D}×{micro,coarse}.")
    ap.add_argument("--scale-mode", type=str, default="extend_scale", choices=["pow10_only", "extend_scale"], help="Bounded scale-family mode.")
    args = ap.parse_args()

    global SCALE_MODE
    SCALE_MODE = str(args.scale_mode)

    wdir = Path(str(args.wiring_dir))
    rep = _read_json(wdir / "u1_interface_strengths.json")
    alpha_low = float(ALPHA_INV_CODATA_2022)
    alpha_z = float(ALPHAZ_INV_PDG)

    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = wdir.name
    mode = str(args.mode)
    layer = str(args.layer)
    joint_all = bool(args.joint_all)

    tex: List[str] = []
    tex.append(r"\toprule")
    tex.append(r"rank & candidate & pred$_0$ & pred$_Z$ & $e_{\mathrm{low}}$ & $e_Z$ \\")
    tex.append(r"\midrule")

    summaries: List[str] = []
    if joint_all:
        header, rows = _audit_joint_all(tag=tag, rep=rep, mode=mode, alpha_low=alpha_low, alpha_z=alpha_z)
        summaries.extend(header)
        tex.extend(rows)
        tex.append(r"\bottomrule")

        rows_path = out_dir / f"sm_hilbert_u1_alpha_link_{tag}_joint_all_rows.tex"
        write_lines(rows_path, tex)

        summary_path = out_dir / f"sm_hilbert_u1_alpha_link_{tag}_joint_all_summary.tex"
        write_lines(
            summary_path,
            [
                r"\paragraph{Audit summary (SM-Hilbert U(1) interface $\to$ $\alpha$ link; joint-all).} \AuditTag "
                r"We apply a bounded-family, deterministic aggregation audit to U(1) interface strengths measured on cross-$m$ scan edges in a concrete wiring geometry. "
                r"We enforce a \emph{single shared} candidate and scale across \{graph2d,graph3d\}$\times$\{micro,coarse\}. "
                r"Candidates predict $\alpha^{-1}(0)$ and are mapped to $\alpha^{-1}(m_Z)$ via a fixed vacuum-polarization decomposition "
                r"$\Delta\alpha(m_Z)=\Delta\alpha_\ell+\Delta\alpha^{(5)}_{\mathrm{had}}+\Delta\alpha_{\mathrm{top}}+\Delta\alpha_{\mathrm{eff}}$, "
                r"then ranked by minimax log-mismatch to $\alpha_{\mathrm{em}}^{-1}$ (CODATA) and $\alpha^{-1}(m_Z)$ (PDG). "
                + " ".join(summaries),
            ],
        )

        print(f"Wrote sections/generated/{rows_path.name}")
        print(f"Wrote sections/generated/{summary_path.name}")
        return

    for gkey in ("graph2d", "graph3d"):
        gg = rep.get(gkey, {})
        if layer == "micro" and isinstance(gg, dict) and "micro" in gg:
            gg = gg.get("micro", {})
        edges = _edges_from_u1_report(gg, mode=mode)
        header, rows = _audit_one(label=f"{tag}:{gkey}:{mode}:{layer}", edges=edges, alpha_low=alpha_low, alpha_z=alpha_z)
        summaries.extend(header)
        tex.extend(rows)
        tex.append(r"\addlinespace")
    tex.append(r"\bottomrule")

    rows_path = out_dir / f"sm_hilbert_u1_alpha_link_{tag}_{layer}_rows.tex"
    write_lines(rows_path, tex)

    summary_path = out_dir / f"sm_hilbert_u1_alpha_link_{tag}_{layer}_summary.tex"
    write_lines(
        summary_path,
        [
            r"\paragraph{Audit summary (SM-Hilbert U(1) interface $\to$ $\alpha$ link).} \AuditTag "
            r"We apply a bounded-family, deterministic aggregation audit to U(1) interface strengths measured on cross-$m$ scan edges in a concrete wiring geometry. "
            r"Candidates predict $\alpha^{-1}(0)$ and are mapped to $\alpha^{-1}(m_Z)$ via a fixed vacuum-polarization decomposition "
            r"$\Delta\alpha(m_Z)=\Delta\alpha_\ell+\Delta\alpha^{(5)}_{\mathrm{had}}+\Delta\alpha_{\mathrm{top}}+\Delta\alpha_{\mathrm{eff}}$, "
            r"then ranked by minimax log-mismatch to $\alpha_{\mathrm{em}}^{-1}$ (CODATA) and $\alpha^{-1}(m_Z)$ (PDG). "
            + " ".join(summaries),
        ],
    )

    print(f"Wrote sections/generated/{rows_path.name}")
    print(f"Wrote sections/generated/{summary_path.name}")


if __name__ == "__main__":
    main()

