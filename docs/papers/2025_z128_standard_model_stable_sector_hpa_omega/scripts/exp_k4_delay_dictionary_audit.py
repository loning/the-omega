# -*- coding: utf-8 -*-
"""
K4 delay/time-dictionary audit (data-facing, deterministic).

This script reuses vendored subsets under data/gamma_crossobs/ to build
an explicit registry-driven audit of a single dimensionless delay-scale
parameter kappa across multiple channels.

Outputs (LaTeX fragments):
  - sections/generated/k4_delay_audit_rows.tex
  - sections/generated/k4_delay_audit_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _tex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
    )


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


@dataclass(frozen=True)
class KappaObs:
    channel: str
    dataset: str
    kappa: float
    sigma: float
    note: str


def _select_items(items: Sequence[dict[str, Any]], where: dict[str, Any]) -> List[dict[str, Any]]:
    out: List[dict[str, Any]] = []
    for it in items:
        ok = True
        for k, v in where.items():
            if str(it.get(k, "")) != str(v):
                ok = False
                break
        if ok:
            out.append(it)
    return out


def _kappa_from_expr(expr: str, ctx: dict[str, float]) -> float:
    """
    Very small safe evaluator for registry expressions.
    Allowed symbols: ctx keys; allowed ops: + - * / ** ( ).
    """
    allowed = set("0123456789.+-*/()eE_ ")
    for ch in expr:
        if ch.isalpha():
            continue
        if ch not in allowed:
            raise ValueError(f"Unsafe character in expr: {ch!r}")
    safe_ctx = dict(ctx)
    # Allow a minimal math whitelist for registry expressions.
    safe_ctx["sqrt"] = math.sqrt
    safe_ctx["abs"] = abs
    return float(eval(expr, {"__builtins__": {}}, safe_ctx))  # noqa: S307 (sandboxed)


def _build_observations(reg: dict[str, Any]) -> List[KappaObs]:
    root = paper_root()
    obs: List[KappaObs] = []

    for ch in reg.get("channels", []):
        src_file = Path(str(ch["source_file"]))
        src = _read_json(root / src_file)
        items = src[str(ch["json_path"])]
        selected = _select_items(items, dict(ch.get("select_where", {})))

        # Two cases: with reference family (strong lensing), or without.
        if "reference_family" in ch:
            refs = list(ch["reference_family"])
            maps = list(ch["mapping_family"])
            for it in selected:
                val = float(it["value"])
                # Symmetric sigma for H0 with +/- in the vendored file.
                sp = float(it.get("sigma_plus", 0.0))
                sm = float(it.get("sigma_minus", 0.0))
                sigma_val = 0.5 * (sp + sm) if (sp > 0 and sm > 0) else max(sp, sm)
                for r in refs:
                    H0_ref = float(r["H0_ref"])
                    sigma_ref = float(r["sigma_ref"])
                    for m in maps:
                        ctx = {
                            "value": val,
                            "sigma_value": sigma_val,
                            "H0_ref": H0_ref,
                            "sigma_ref": sigma_ref,
                        }
                        kappa = _kappa_from_expr(str(m["kappa_expr"]), ctx)
                        sigma = _kappa_from_expr(str(m["sigma_expr"]), dict(ctx, kappa=kappa))
                        obs.append(
                            KappaObs(
                                channel=str(it.get("channel", "")) + f"/ref={r['id']}",
                                dataset=str(it.get("id", "")),
                                kappa=float(kappa),
                                sigma=float(abs(sigma)),
                                note=str(m.get("description", "")),
                            )
                        )
        else:
            maps = list(ch.get("mapping_family", []))
            for it in selected:
                val = float(it["value"])
                sigma_val = float(it.get("sigma", 0.0))
                for m in maps:
                    ctx = {"value": val, "sigma": sigma_val}
                    kappa = _kappa_from_expr(str(m["kappa_expr"]), ctx)
                    sigma = _kappa_from_expr(str(m["sigma_expr"]), ctx)
                    obs.append(
                        KappaObs(
                            channel=str(it.get("channel", "")) + f"/map={m['id']}",
                            dataset=str(it.get("id", "")),
                            kappa=float(kappa),
                            sigma=float(abs(sigma)),
                            note=str(m.get("description", "")),
                        )
                    )
    return obs


def _inverse_variance_mean(xs: Sequence[KappaObs]) -> Optional[Tuple[float, float]]:
    wsum = 0.0
    msum = 0.0
    for x in xs:
        if not math.isfinite(x.kappa) or not math.isfinite(x.sigma) or x.sigma <= 0:
            continue
        w = 1.0 / (x.sigma * x.sigma)
        wsum += w
        msum += w * x.kappa
    if wsum <= 0:
        return None
    mu = msum / wsum
    sig = math.sqrt(1.0 / wsum)
    return (float(mu), float(sig))


def _chi2(xs: Sequence[KappaObs], mu: float) -> Tuple[float, int]:
    chi2 = 0.0
    n = 0
    for x in xs:
        if x.sigma <= 0:
            continue
        chi2 += ((x.kappa - mu) / x.sigma) ** 2
        n += 1
    dof = max(0, n - 1)
    return float(chi2), int(dof)


def _pairwise_max_z(xs: Sequence[KappaObs]) -> float:
    best = -1.0
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            si = xs[i].sigma
            sj = xs[j].sigma
            denom = math.sqrt(si * si + sj * sj) if (si > 0 and sj > 0) else 0.0
            if denom <= 0:
                continue
            z = abs(xs[i].kappa - xs[j].kappa) / denom
            best = max(best, z)
    return float(best)


def main() -> None:
    root = paper_root()
    reg = _read_json(root / "data" / "k4_matching" / "delay_channel_registry.json")

    # Build observations under each strong-lensing reference choice by filtering channel label.
    all_obs = _build_observations(reg)

    # Candidate family: select one strong-lensing reference and one solar PPN mapping.
    # We do this by filtering the expanded observation list.
    ref_ids = ["Planck18", "SH0ES19"]
    ppn_maps = ["ppn_halfsum", "ppn_identity"]
    candidates: List[Tuple[str, List[KappaObs]]] = []

    for ref in ref_ids:
        for ppn in ppn_maps:
            xs: List[KappaObs] = []
            for o in all_obs:
                ch = o.channel
                if "strong_lensing_time_delay" in ch:
                    if f"ref={ref}" not in ch:
                        continue
                    xs.append(o)
                elif "ppn_gamma" in ch:
                    if f"map={ppn}" not in ch:
                        continue
                    xs.append(o)
                else:
                    # redshift map family has a single option; include.
                    xs.append(o)
            candidates.append((f"ref={ref},ppn={ppn}", xs))

    # Score each candidate by (chi2_red, max_z, complexity).
    rows: List[str] = []
    best_key = None
    best_label = ""
    best_mu = float("nan")
    best_sig = float("nan")
    best_chi2 = float("nan")
    best_dof = 0
    best_maxz = float("nan")

    scored: List[Tuple[Tuple[float, float, int], str, float, float, float, int, float, int]] = []
    for label, xs in candidates:
        iv = _inverse_variance_mean(xs)
        if iv is None:
            continue
        mu, sig = iv
        chi2, dof = _chi2(xs, mu)
        chi2_red = chi2 / float(dof) if dof > 0 else float("nan")
        maxz = _pairwise_max_z(xs)
        complexity = len(label)
        key = (
            float(chi2_red) if math.isfinite(chi2_red) else 1e99,
            float(maxz) if math.isfinite(maxz) else 1e99,
            int(complexity),
        )
        scored.append((key, label, mu, sig, chi2, dof, maxz, len(xs)))

    scored.sort(key=lambda t: t[0])
    if scored:
        best_key, best_label, best_mu, best_sig, best_chi2, best_dof, best_maxz, _ = scored[0]

    for i, (key, label, mu, sig, chi2, dof, maxz, nobs) in enumerate(scored, start=1):
        rows.append(
            " & ".join(
                [
                    str(i),
                    _tex_escape(label),
                    str(int(nobs)),
                    _fmt(mu, 6),
                    _fmt(sig, 6),
                    _fmt(chi2, 3),
                    str(int(dof)),
                    _fmt(maxz, 3),
                ]
            )
            + r" \\"
        )

    out_dir = generated_dir()
    write_lines(out_dir / "k4_delay_audit_rows.tex", rows if rows else ["% (no rows)"])

    summary = [
        r"\paragraph{Audit summary (K4 delay dictionary).} \AuditTag "
        + rf"Candidate family size: {len(scored)}. "
        + r"Each candidate selects (i) a strong-lensing reference (Planck18 vs SH0ES19) "
        + r"and (ii) a solar PPN mapping (half-sum vs identity), while including the redshift-alpha mapping. "
        + r"Scoring key: $(\chi^2/\nu,\ z_{\max},\ \mathrm{len}(\mathrm{label}))$ with deterministic tie-break.",
        r"\noindent\AuditTag "
        + rf"Selected: \texttt{{{_tex_escape(best_label)}}}, "
        + rf"$\widehat\kappa={_fmt(best_mu, 6)}\pm{_fmt(best_sig, 6)}$, "
        + rf"$\chi^2={_fmt(best_chi2, 3)}$ (dof={best_dof}), "
        + rf"$z_{{\max}}={_fmt(best_maxz, 3)}$.",
    ]
    write_lines(out_dir / "k4_delay_audit_summary.tex", summary)


if __name__ == "__main__":
    main()

