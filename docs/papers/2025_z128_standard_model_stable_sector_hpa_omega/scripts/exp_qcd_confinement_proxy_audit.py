# -*- coding: utf-8 -*-
"""
Audit-only confinement proxy from finite Wilson-loop style diagnostics.

We use the already-generated loop-scale Wilson diagnostics on the n=3 (8×8) grid:
  sections/generated/holonomy_wilson_loop_rows.tex

For each k×k square loop (k=1..7), the source table reports the mean value
  W_k := Re(tr(Q))/3
over the nontrivial 3/4-cycle subset.

As an audit-facing proxy for an area-law falloff, we fit the two-parameter form
  |W_k| ≈ exp( - sigma * k^2 - mu * k )
over a bounded rational candidate family for (sigma, mu) and select the CAP-minimal
best-fit by deterministic tie-break rules.

Outputs (LaTeX fragments):
  - sections/generated/qcd_confinement_proxy_rows.tex
  - sections/generated/qcd_confinement_proxy_summary.tex
  - sections/generated/qcd_confinement_proxy_robustness_rows.tex
  - sections/generated/qcd_confinement_proxy_sigma_rows.tex
  - sections/generated/qcd_confinement_proxy_sigma_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from common_tex import write_lines


@dataclass(frozen=True)
class ObsRow:
    k: int
    count: int
    mean_w: float


def _parse_float(s: str) -> float:
    s = s.strip().strip("$")
    if s in {"-", "$-$"}:
        return float("nan")
    return float(s)


def _read_wilson_rows(path: Path) -> List[ObsRow]:
    rows: List[ObsRow] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("\\") or "bottomrule" in line:
            continue
        if "&" not in line:
            continue
        # expected: k & cnt & meanW & minW & maxW & meanA \\
        parts = [p.strip() for p in line.split("&")]
        if len(parts) < 3:
            continue
        try:
            k = int(parts[0])
            cnt = int(parts[1])
            mean_w = _parse_float(parts[2])
        except Exception:
            continue
        rows.append(ObsRow(k=k, count=cnt, mean_w=float(mean_w)))
    return rows


def _bounded_rationals(max_q: int, max_p: int) -> Iterable[Tuple[int, int]]:
    for q in range(1, max_q + 1):
        for p in range(0, max_p + 1):
            yield (p, q)


def _model_abs_w(k: int, sigma: float, mu: float) -> float:
    # |W_k| ≈ exp(-sigma*k^2 - mu*k)
    x = -sigma * float(k * k) - mu * float(k)
    # guard for underflow
    if x < -800:
        return 0.0
    return math.exp(x)


def _abs_log_mismatch(pred: float, obs: float) -> float:
    if pred <= 0.0 or obs <= 0.0 or math.isnan(pred) or math.isnan(obs):
        return float("inf")
    return abs(math.log(pred / obs))


def _fit_proxy(
    obs: List[Tuple[int, float]],
    Q: int,
    P: int,
) -> tuple[float, float, float, float]:
    """
    Return (sigma_hat, mu_hat, E_best, gap_to_second) under bounded rational family:
      sigma=p/q, mu=r/s with 1<=q,s<=Q and 0<=p,r<=P.
    Objective: mean absolute log mismatch over obs.
    Tie-break: (E, denom_sum, q,p,s,r).
    """
    best_key = None
    best_sigma = 0.0
    best_mu = 0.0
    best_E = float("inf")

    second_key = None
    second_E = float("inf")

    for sp, sq in _bounded_rationals(Q, P):
        sigma = float(sp) / float(sq)
        for mp, mq in _bounded_rationals(Q, P):
            mu = float(mp) / float(mq)

            errs: List[float] = []
            for k, w_abs in obs:
                pred = _model_abs_w(k, sigma=sigma, mu=mu)
                errs.append(_abs_log_mismatch(pred, w_abs))
            E = sum(errs) / float(len(errs)) if errs else float("inf")

            key = (E, sq + mq, sq, sp, mq, mp)
            if best_key is None or key < best_key:
                # demote current best to second
                if best_key is not None:
                    second_key = best_key
                    second_E = best_E
                best_key = key
                best_sigma = sigma
                best_mu = mu
                best_E = E
            elif best_key is not None and (second_key is None or key < second_key):
                # track best runner-up
                second_key = key
                second_E = E

    gap = float("nan")
    if math.isfinite(best_E) and math.isfinite(second_E):
        gap = max(0.0, float(second_E - best_E))
    return best_sigma, best_mu, best_E, gap


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"
    src = gen / "holonomy_wilson_loop_rows.tex"
    if not src.is_file():
        raise FileNotFoundError("Missing sections/generated/holonomy_wilson_loop_rows.tex; run exp_holonomy_wilson_loop_sweep.py first.")

    data = _read_wilson_rows(src)

    # Use k=1..6 where the diagnostic is most stable; ignore missing/zero rows.
    obs: List[Tuple[int, float]] = []
    for r in data:
        if r.count <= 0:
            continue
        if r.k < 1 or r.k > 6:
            continue
        w_abs = abs(float(r.mean_w))
        if w_abs <= 0.0 or math.isnan(w_abs):
            continue
        obs.append((r.k, w_abs))
    if len(obs) < 3:
        raise AssertionError("Insufficient Wilson-loop rows for confinement proxy fit.")

    # Primary bounded rational candidate family (reduced form not required; domain is explicit).
    Q0 = 20
    P0 = 40
    best_sigma, best_mu, best_E, best_gap = _fit_proxy(obs, Q=Q0, P=P0)

    # Emit per-k diagnostics.
    out_rows: List[str] = []
    for k, w_abs in sorted(obs, key=lambda t: t[0]):
        pred = _model_abs_w(k, sigma=best_sigma, mu=best_mu)
        e = _abs_log_mismatch(pred, w_abs)
        out_rows.append(
            f"{k} & {k*k} & {w_abs:.6g} & {pred:.6g} & {e:.6g} \\\\"
        )
    out_rows.append("\\bottomrule")

    summary = [
        rf"\paragraph{{Audit summary (QCD confinement proxy).}} \AuditTag "
        rf"Fit model $|W_k|\approx \exp(-\sigma k^2-\mu k)$ on $k\in\{{1,\dots,6\}}$ using the loop-scale Wilson diagnostics "
        rf"(Table~\ref{{tab:holonomy_wilson_loop}}). "
        rf"Bounded candidate family: $\sigma=p/q$, $\mu=r/s$ with $1\le q,s\le {Q0}$ and $0\le p,r\le {P0}$. "
        rf"Deterministic selection minimizes mean absolute log mismatch, tie-break by smaller denominators. "
        rf"Selected: $\widehat\sigma={best_sigma:.6g}$, $\widehat\mu={best_mu:.6g}$ (mean log mismatch {best_E:.6g}; runner-up gap {best_gap:.6g})."
    ]

    # Derived string-tension style sequence (audit-only):
    # sigma_eff(k) := (-log|W_k| - mu*k)/k^2
    sig_rows: List[str] = []
    sig_vals: List[float] = []
    for k, w_abs in sorted(obs, key=lambda t: t[0]):
        if k <= 0:
            continue
        if w_abs <= 0.0:
            continue
        sig_raw = (-math.log(w_abs)) / float(k * k)
        sig_eff = (-math.log(w_abs) - best_mu * float(k)) / float(k * k)
        sig_rows.append(f"{k} & {w_abs:.6g} & {sig_raw:.6g} & {sig_eff:.6g} \\\\")
        if 2 <= k <= 6 and math.isfinite(sig_eff):
            sig_vals.append(float(sig_eff))
    sig_rows.append("\\bottomrule")

    sig_summary: List[str] = []
    if sig_vals:
        sig_vals_sorted = sorted(sig_vals)
        lo = sig_vals_sorted[0]
        hi = sig_vals_sorted[-1]
        mean_sig = sum(sig_vals_sorted) / float(len(sig_vals_sorted))
        var = sum((x - mean_sig) ** 2 for x in sig_vals_sorted) / float(len(sig_vals_sorted))
        std = math.sqrt(max(0.0, var))
        sig_summary.append(
            rf"\paragraph{{Audit summary (string-tension style sequence).}} \AuditTag "
            rf"Define $\sigma_{{\mathrm{{eff}}}}(k):=(-\log|W_k|-\widehat\mu k)/k^2$ using the selected $\widehat\mu$ from the proxy fit. "
            rf"On $k\in\{{2,\dots,6\}}$ this yields mean {mean_sig:.6g} with std {std:.6g} and range [{lo:.6g},{hi:.6g}] (plaquette units)."
        )
    else:
        sig_summary.append(r"\paragraph{Audit summary (string-tension style sequence).} \AuditTag \textit{pending} (insufficient valid $k$ rows).")

    # Robustness: vary bounds and leave-one-out in k.
    rob_rows: List[str] = []
    for Q in (10, 15, 20):
        P = 2 * Q
        s, m, E, gap = _fit_proxy(obs, Q=Q, P=P)
        rob_rows.append(f"bound & {Q} & {P} & {s:.6g} & {m:.6g} & {E:.6g} & {gap:.6g} \\\\")
    # Leave-one-out: exclude one k at a time.
    ks = sorted([k for k, _ in obs])
    for k_ex in ks:
        obs2 = [(k, w) for (k, w) in obs if k != k_ex]
        if len(obs2) < 3:
            continue
        s, m, E, gap = _fit_proxy(obs2, Q=Q0, P=P0)
        rob_rows.append(f"loo($k={k_ex}$) & {Q0} & {P0} & {s:.6g} & {m:.6g} & {E:.6g} & {gap:.6g} \\\\")
    rob_rows.append("\\bottomrule")

    write_lines(gen / "qcd_confinement_proxy_rows.tex", out_rows)
    write_lines(gen / "qcd_confinement_proxy_summary.tex", summary)
    write_lines(gen / "qcd_confinement_proxy_robustness_rows.tex", rob_rows)
    write_lines(gen / "qcd_confinement_proxy_sigma_rows.tex", sig_rows)
    write_lines(gen / "qcd_confinement_proxy_sigma_summary.tex", sig_summary)
    print("Wrote sections/generated/qcd_confinement_proxy_rows.tex")
    print("Wrote sections/generated/qcd_confinement_proxy_summary.tex")
    print("Wrote sections/generated/qcd_confinement_proxy_robustness_rows.tex")
    print("Wrote sections/generated/qcd_confinement_proxy_sigma_rows.tex")
    print("Wrote sections/generated/qcd_confinement_proxy_sigma_summary.tex")


if __name__ == "__main__":
    main()

