# -*- coding: utf-8 -*-
"""
Linewidth -> survival kernel finite-family (CAP) audit (toy).

Goal:
  Upgrade the linewidth->survival closure to the finite-family discipline of Appendix (leakage kernel):
    - declare a finite candidate family of survival laws P_f(t)
    - compute leakage-rate proxy Gamma_f and lifetime proxy tau_f=1/Gamma_f
    - CAP-select a family element by a deterministic mismatch objective + tie-break

Targets:
  We treat two width proxies extracted from the det-delay carrier as audit targets:
    Gamma_tau  (Breit-Wigner proxy) and Gamma_FWHM (half-maximum width proxy).

Family:
  - exponential:           P(t)=exp(-gamma t)
  - stretched exponential: P(t)=exp(-(gamma t)^alpha) with alpha in {1.5, 2.0}
  - log-quadratic:         P(t)=exp(-gamma t - beta t^2) with beta in {0.2, 0.5} * gamma^2
  Each family member is fully specified by a small finite parameter tuple.

Rate proxy:
  We use the same upper-envelope definition as in the leakage-kernel dictionary:
    Gamma_f := inf{ g>0 : P_f(t) <= exp(-g t) for all t >= 0 }.
  For the declared finite families we compute Gamma_f in closed form:
    - exponential:           Gamma_f = gamma
    - stretched exp (alpha>1): Gamma_f = gamma (since exp(-(gamma t)^alpha) <= exp(-gamma t))
    - log-quadratic:         Gamma_f = gamma  (since extra -beta t^2 only decreases P)

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/survival_finite_family_rows.tex
  - sections/generated/survival_finite_family_summary.tex
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


@dataclass(frozen=True)
class Cand:
    family_id: str
    gamma: float
    alpha: float
    beta_scale: float
    note: str

    def P(self, t: float) -> float:
        g = float(self.gamma)
        if g < 0.0:
            return float("nan")
        tt = float(t)
        if tt < 0.0:
            return float("nan")
        if self.family_id == "exp":
            return float(math.exp(-g * tt))
        if self.family_id == "stretched":
            a = float(self.alpha)
            return float(math.exp(-math.pow(g * tt, a)))
        if self.family_id == "logquad":
            b = float(self.beta_scale) * (g * g)
            return float(math.exp(-g * tt - b * tt * tt))
        return float("nan")

    def Gamma_proxy(self) -> float:
        # Upper-envelope rate proxy for declared families: always gamma as explained above.
        return float(self.gamma)

    def Tau_proxy(self) -> float:
        G = self.Gamma_proxy()
        return float(1.0 / G) if G > 0.0 else float("nan")


def _candidate_family(gamma_targets: Tuple[float, float]) -> Sequence[Cand]:
    g1, g2 = float(gamma_targets[0]), float(gamma_targets[1])
    # Deterministic declared finite set of gamma anchors:
    anchors = sorted({max(1e-6, g1), max(1e-6, g2), 0.5 * (g1 + g2), min(g1, g2), max(g1, g2)})
    out: List[Cand] = []
    for g in anchors:
        out.append(Cand("exp", float(g), 1.0, 0.0, "exponential"))
        out.append(Cand("stretched", float(g), 1.5, 0.0, "stretched exp; alpha=1.5"))
        out.append(Cand("stretched", float(g), 2.0, 0.0, "stretched exp; alpha=2.0"))
        out.append(Cand("logquad", float(g), 1.0, 0.2, "log-quadratic; beta=0.2*gamma^2"))
        out.append(Cand("logquad", float(g), 1.0, 0.5, "log-quadratic; beta=0.5*gamma^2"))
    # Deduplicate by (family, gamma, alpha, beta_scale)
    seen = set()
    uniq: List[Cand] = []
    for c in out:
        key = (c.family_id, round(float(c.gamma), 12), round(float(c.alpha), 6), round(float(c.beta_scale), 6))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


def _objective(c: Cand, gamma_targets: Tuple[float, float], times: Sequence[float]) -> float:
    g_tau, g_fwhm = float(gamma_targets[0]), float(gamma_targets[1])
    G = c.Gamma_proxy()
    # Match both width proxies in a symmetric way.
    e1 = float(abs(G - g_tau))
    e2 = float(abs(G - g_fwhm))
    # Also encourage survival values that are not numerically degenerate on the declared times.
    # (This is a deterministic secondary proxy to avoid silly extremes when gamma targets are very small.)
    surv_pen = 0.0
    for t in times:
        p = c.P(float(t))
        if not math.isfinite(p):
            surv_pen += 1.0
        else:
            surv_pen += abs(p - 0.5)  # keep mid-range by preference (audit tie-break)
    return float(e1 + e2 + 0.05 * surv_pen)


def _cap_select(cands: Sequence[Cand], gamma_targets: Tuple[float, float], times: Sequence[float]) -> Cand:
    best = None
    for c in cands:
        obj = _objective(c, gamma_targets, times)
        # deterministic tie-break: smaller objective, then shorter note, then lexicographic id
        key = (float(obj), int(len(c.note)), c.family_id, float(c.gamma), float(c.alpha), float(c.beta_scale))
        if best is None or key < best[0]:
            best = (key, c, obj)
    assert best is not None
    return best[1]


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "survival_finite_family_rows.tex"
    sum_path = out_dir / "survival_finite_family_summary.tex"

    times = [0.25, 0.50, 1.00]

    # Auto-load targets from the det-delay linewidth audit artifact.
    # Expected row format (generated): case & rank & r & omega0 & tau_max & Gamma_tau & Gamma_FWHM & mismatch \\\\
    det_rows_path = out_dir / "det_delay_linewidth_rows.tex"
    raw = det_rows_path.read_text(encoding="utf-8").splitlines() if det_rows_path.is_file() else []
    targets: dict[str, Tuple[float, float]] = {}
    for line in raw:
        s = line.strip()
        if not s or s.startswith("%") or s.startswith(r"\bottomrule"):
            continue
        s = s.replace(r"\\", "")
        parts = [p.strip() for p in s.split("&")]
        if len(parts) < 8:
            continue
        case = parts[0]
        try:
            rank = int(parts[1])
            g_tau = float(parts[5])
            g_fwhm = float(parts[6])
        except (ValueError, TypeError):
            continue
        if rank != 1:
            continue
        if case not in targets and math.isfinite(g_tau) and math.isfinite(g_fwhm):
            targets[case] = (g_tau, g_fwhm)

    if not targets:
        raise RuntimeError("no linewidth targets found; run det-delay linewidth audit first")

    rows: List[str] = []
    chosen_cases: List[Tuple[str, Cand, Tuple[float, float]]] = []
    for case in sorted(targets.keys()):
        gamma_targets = targets[case]
        fam = list(_candidate_family(gamma_targets))
        chosen = _cap_select(fam, gamma_targets, times)
        chosen_cases.append((case, chosen, gamma_targets))
        for c in fam:
            chosen_flag = "yes" if c == chosen else ""
            G = c.Gamma_proxy()
            tau = c.Tau_proxy()
            Ps = [_fmt(c.P(t), 6) for t in times]
            rows.append(
                " & ".join(
                    [
                        case.replace("_", r"\_"),
                        c.family_id.replace("_", r"\_"),
                        _fmt(float(c.gamma), 6),
                        _fmt(float(c.alpha), 3),
                        _fmt(float(c.beta_scale), 3),
                        _fmt(G, 6),
                        _fmt(tau, 6),
                        _fmt(times[0], 2),
                        Ps[0],
                        _fmt(times[1], 2),
                        Ps[1],
                        _fmt(times[2], 2),
                        Ps[2],
                        chosen_flag,
                    ]
                )
                + r" \\"
            )
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    target_lines: List[str] = []
    for case, _c, (g_tau, g_fwhm) in chosen_cases:
        target_lines.append(f"{case}: (Gamma_tau={_fmt(g_tau,6)}, Gamma_FWHM={_fmt(g_fwhm,6)})")

    write_lines(
        sum_path,
        [
            r"\paragraph{Finite-family survival-kernel closure (CAP).} \AuditTag "
            + r"We declare a finite candidate family of survival kernels $P_f(t)$ and CAP-select an element by a deterministic objective. "
            + r"The rate proxy is $\Gamma_f:=\inf\{g>0: P_f(t)\le \exp(-g t)\ \forall t\ge 0\}$; for the declared families it equals the base $\gamma$. "
            + r"Targets are two linewidth proxies $(\Gamma_\tau,\Gamma_{\mathrm{FWHM}})$ obtained from the det-delay carrier. "
            + r"The table reports $\Gamma_f$, $\tau_f=1/\Gamma_f$, and $P_f(t)$ at declared times, and flags the CAP-selected row.",
            r"\paragraph{Determinism.} \AuditTag "
            + rf"Targets are auto-loaded from \texttt{{sections/generated/det\_delay\_linewidth\_rows.tex}} (rank=1 per case): "
            + (", ".join(target_lines)).replace("_", r"\_")
            + rf"; times={times}. "
            + r"The candidate family and tie-break are finite and explicit.",
        ],
    )


if __name__ == "__main__":
    main()

