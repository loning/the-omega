# -*- coding: utf-8 -*-
"""
K4 leakage audit against a minimal vendored PDG-style lifetime dataset.

We treat Gamma as a leakage-rate proxy (1/s) derived from lifetimes.
We then run bounded candidate families for explanatory models and select the
CAP/MDL-minimal one under explicit tie-break rules.

Outputs (LaTeX fragments):
  - sections/generated/k4_pdg_leakage_rows.tex
  - sections/generated/k4_pdg_leakage_summary.tex

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
from typing import Any, Dict, List, Optional, Sequence, Tuple

from common_paths import generated_dir, paper_root
from common_progress import ProgressEvery
from common_tex import write_lines


SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0
HBAR_GEV_S = 6.582119569e-25  # CODATA 2018/2022-compatible value; used for GeV -> s^-1 conversion.


def _ch_id(x: Optional[str]) -> Optional[int]:
    if x is None:
        return None
    s = str(x).strip().upper()
    if s in ("U1", "U(1)"):
        return 0
    if s in ("SU2", "SU(2)"):
        return 1
    if s in ("SU3", "SU(3)"):
        return 2
    return None


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
class Entry:
    name: str
    quantity: str  # lifetime | lifetime_lower_bound | lifetime_upper_bound | width | width_lower_bound | width_upper_bound
    value: float
    sigma: Optional[float]
    unit: str
    channel: Optional[int]  # optional fixed exit-channel id for M2


def _to_seconds(value: float, unit: str) -> float:
    u = unit.strip()
    scale = {
        "s": 1.0,
        "ms": 1e-3,
        "us": 1e-6,
        "ns": 1e-9,
        "ps": 1e-12,
        "fs": 1e-15,
        "yr": SECONDS_PER_YEAR,
    }.get(u)
    if scale is None:
        raise ValueError(f"Unknown time unit: {unit!r}")
    return float(value) * float(scale)


def _to_gamma_per_s(quantity: str, value: float, unit: str) -> float:
    q = str(quantity)
    u = str(unit).strip()
    if q.startswith("lifetime"):
        tau = _to_seconds(float(value), u)
        if tau <= 0:
            raise ValueError("Non-positive lifetime")
        return float(1.0 / tau)
    if q.startswith("width"):
        if u == "s^-1":
            return float(value)
        if u == "GeV":
            if value < 0:
                raise ValueError("Negative width")
            return float(value) / float(HBAR_GEV_S)
        raise ValueError(f"Unknown width unit: {unit!r}")
    raise ValueError(f"Unknown quantity family: {quantity!r}")


def _load_entries() -> List[Entry]:
    p = paper_root() / "data" / "k4_matching" / "pdg_decay_miniset.json"
    data = _read_json(p)
    out: List[Entry] = []
    for e in data.get("entries", []):
        name = str(e["name"])
        q = str(e["quantity"])
        unit = str(e.get("unit", "s"))
        sigma = float(e["sigma"]) if "sigma" in e else None
        ch = _ch_id(e.get("channel"))
        out.append(
            Entry(
                name=name,
                quantity=q,
                value=float(e["value"]),
                sigma=float(sigma) if (sigma is not None) else None,
                unit=unit,
                channel=ch,
            )
        )
    return out


def _gamma_obs(entry: Entry) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Return (gamma_hat, sigma_gamma, gamma_upper_bound, gamma_lower_bound).
    - For lifetime/width: gamma_hat from conversion, sigma via delta method in linear space.
    - For lifetime_lower_bound: implies gamma_upper_bound.
    - For lifetime_upper_bound: implies gamma_lower_bound.
    """
    q = str(entry.quantity)
    if q in ("lifetime", "width"):
        g = _to_gamma_per_s(q, entry.value, entry.unit)
        if entry.sigma is None or entry.sigma <= 0:
            return (float(g), None, None, None)
        # Delta method: Gamma = f(x), sigma_Gamma = |f'(x)| sigma_x.
        if q == "lifetime":
            tau = _to_seconds(float(entry.value), entry.unit)
            sig_tau = _to_seconds(float(entry.sigma), entry.unit)
            sig_g = abs(sig_tau) / (tau * tau)
            return (float(g), float(sig_g), None, None)
        # width: linear conversion (either s^-1 already, or GeV/ħ)
        if entry.unit.strip() == "s^-1":
            return (float(g), float(entry.sigma), None, None)
        if entry.unit.strip() == "GeV":
            return (float(g), float(entry.sigma) / float(HBAR_GEV_S), None, None)
        raise ValueError(f"Unknown width unit: {entry.unit!r}")

    if q in ("lifetime_lower_bound", "width_upper_bound"):
        g_ub = _to_gamma_per_s("lifetime" if q.startswith("lifetime") else "width", entry.value, entry.unit)
        return (None, None, float(g_ub), None)
    if q in ("lifetime_upper_bound", "width_lower_bound"):
        g_lb = _to_gamma_per_s("lifetime" if q.startswith("lifetime") else "width", entry.value, entry.unit)
        return (None, None, None, float(g_lb))

    raise ValueError(f"Unknown entry quantity: {q}")


def _abs_log_mismatch(a: float, b: float) -> float:
    if a <= 0.0 or b <= 0.0:
        return float("inf")
    return abs(math.log(a / b))


def _score_point(g_pred: float, g_hat: float, sig: Optional[float]) -> float:
    # Prefer log mismatch as an audit norm, with optional sigma scaling.
    e = _abs_log_mismatch(g_pred, g_hat)
    if sig is None or sig <= 0.0:
        return float(e)
    # Map sigma to log space approximately.
    rel = sig / g_hat if g_hat > 0 else float("inf")
    denom = max(1e-12, rel)
    return float(e / denom)


def _score_upper_bound(g_pred: float, g_max: float) -> float:
    # One-sided penalty: zero if satisfied, else log violation.
    if not (g_pred > 0 and g_max > 0):
        return float("inf")
    if g_pred <= g_max:
        return 0.0
    return float(_abs_log_mismatch(g_pred, g_max))


def _score_lower_bound(g_pred: float, g_min: float) -> float:
    # One-sided penalty: zero if satisfied, else log violation.
    if not (g_pred > 0 and g_min > 0):
        return float("inf")
    if g_pred >= g_min:
        return 0.0
    return float(_abs_log_mismatch(g_pred, g_min))


@dataclass(frozen=True)
class BestModel:
    model: str
    b: int
    a: int
    level_max: int
    md_cost: float
    detail: str


def _median(xs: Sequence[float]) -> float:
    ys = sorted(xs)
    if not ys:
        return float("nan")
    n = len(ys)
    if n % 2 == 1:
        return float(ys[n // 2])
    return 0.5 * (ys[n // 2 - 1] + ys[n // 2])


def _evaluate_models(entries: Sequence[Entry]) -> Tuple[BestModel, List[Tuple[float, BestModel]]]:
    # Observations in log10 space for lifetime entries.
    names = [e.name for e in entries]
    obs_log10: Dict[str, float] = {}
    obs_sig_log10: Dict[str, Optional[float]] = {}
    ub_log10: Dict[str, float] = {}
    lb_log10: Dict[str, float] = {}
    ch_fixed: Dict[str, int] = {}

    for e in entries:
        if e.channel is not None:
            ch_fixed[e.name] = int(e.channel)
        g_hat, g_sig, g_ub, g_lb = _gamma_obs(e)
        if g_ub is not None:
            ub_log10[e.name] = math.log10(g_ub)
            continue
        if g_lb is not None:
            lb_log10[e.name] = math.log10(g_lb)
            continue
        assert g_hat is not None
        obs_log10[e.name] = math.log10(g_hat)
        if g_sig is None:
            obs_sig_log10[e.name] = None
        else:
            rel = g_sig / g_hat if g_hat > 0 else None
            obs_sig_log10[e.name] = float(rel / math.log(10.0)) if rel else None

    # Finite families (bounded, auditable).
    b_set = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    level_max_set = [4, 5, 6]
    a_grid = list(range(-50, 11, 2))  # even grid for determinism

    # Channel offsets for model M2 (in log10 gamma).
    ch_names = ["U1", "SU2", "SU3"]
    delta_set = [0.0, 2.0, 4.0]  # bounded, coarse

    # Keep only top-K candidates for reporting (avoid storing huge lists).
    TOPK = 20
    top: List[Tuple[float, BestModel]] = []

    def push_candidate(total_cost: float, cand: BestModel) -> None:
        top.append((float(total_cost), cand))
        top.sort(key=lambda t: (t[0], t[1].model, t[1].level_max, t[1].b, t[1].a))
        if len(top) > TOPK:
            del top[TOPK:]

    # Enumerate monotone level assignments (nondecreasing sequence) to avoid L^n blowup.
    def enum_levels_monotone(n: int, L: int) -> List[Tuple[int, ...]]:
        out: List[Tuple[int, ...]] = []

        cur = [1] * n

        def rec(i: int, lo: int) -> None:
            if i == n:
                out.append(tuple(cur))
                return
            for v in range(lo, L + 1):
                cur[i] = v
                rec(i + 1, v)

        rec(0, 1)
        return out

    # Precompute observation names that have direct values (exclude upper-bound-only).
    fit_names_unsorted = [n for n in names if n in obs_log10]
    ub_names = [n for n in names if n in ub_log10]
    lb_names = [n for n in names if n in lb_log10]

    # Sort fit names by observed gamma (descending) so that monotone levels respect
    # the heuristic: larger gamma (faster leakage) should correspond to smaller depth level.
    fit_names = sorted(fit_names_unsorted, key=lambda n: -obs_log10[n])

    for Lmax in level_max_set:
        # Assign levels only to fit_names; for upper-bound entries, fix to the deepest level.
        level_assignments_fit = enum_levels_monotone(len(fit_names), Lmax)
        for b in b_set:
            # ----------------
            # M1: log10(gamma) = a - b*(level-1)
            # ----------------
            prog_m1 = ProgressEvery(label=f"k4_pdg_leakage:M1(Lmax={Lmax},b={b})", total=len(level_assignments_fit))
            prog_m1.start()

            for idx_lv, lv_fit in enumerate(level_assignments_fit, start=1):
                # Build full level map.
                level_of: Dict[str, int] = {}
                for i, n in enumerate(fit_names):
                    level_of[n] = int(lv_fit[i])
                for n in ub_names:
                    level_of[n] = int(Lmax)

                # choose a by median of residuals
                residuals = [
                    obs_log10[n] + b * (level_of[n] - 1) for n in fit_names
                ]
                a_med = _median(residuals)
                # snap to grid
                a = min(a_grid, key=lambda x: abs(x - a_med))
                # compute cost
                cost = 0.0
                for n in fit_names:
                    pred_log10 = float(a) - float(b) * float(level_of[n] - 1)
                    g_pred = 10.0 ** pred_log10
                    g_hat = 10.0 ** obs_log10[n]
                    sig_rel_log10 = obs_sig_log10[n]
                    sig = (sig_rel_log10 * g_hat * math.log(10.0)) if (sig_rel_log10 is not None) else None
                    cost += _score_point(g_pred, g_hat, sig)
                for n in ub_names:
                    pred_log10 = float(a) - float(b) * float(level_of[n] - 1)
                    g_pred = 10.0 ** pred_log10
                    g_max = 10.0 ** ub_log10[n]
                    cost += _score_upper_bound(g_pred, g_max)
                for n in lb_names:
                    pred_log10 = float(a) - float(b) * float(level_of[n] - 1)
                    g_pred = 10.0 ** pred_log10
                    g_min = 10.0 ** lb_log10[n]
                    cost += _score_lower_bound(g_pred, g_min)
                # MDL-like penalty (tiny): prefer smaller Lmax and smaller |a|,b.
                mdl = 0.01 * (Lmax + abs(a) / 10.0 + b / 10.0)
                total = cost + mdl
                push_candidate(
                    float(total),
                    BestModel(
                        model="M1",
                        b=int(b),
                        a=int(a),
                        level_max=int(Lmax),
                        md_cost=float(total),
                        detail=f"levels_fit={lv_fit}; ub_fixed={Lmax}",
                    ),
                )
                prog_m1.maybe(idx_lv)
            prog_m1.done()

            # ----------------
            # M2: log10(gamma) = a - b*(level-1) + delta[channel]
            # ----------------
            # Finite family for delta triplets.
            delta_triplets: List[Tuple[float, float, float]] = []
            for d1 in delta_set:
                for d2 in delta_set:
                    for d3 in delta_set:
                        delta_triplets.append((float(d1), float(d2), float(d3)))

            # IMPORTANT: Enumerating channel assignments is 3^N and becomes infeasible once the
            # dataset grows. Instead we use a deterministic inner minimization:
            # for each data point, pick the best channel among {0,1,2} (or a fixed channel label)
            # under the current (Lmax,b,a,delta) candidate. This reduces 3^N -> 3N and keeps the
            # audit bounded and reproducible.
            total_inner = len(level_assignments_fit) * len(delta_triplets)
            prog_m2 = ProgressEvery(
                label=f"k4_pdg_leakage:M2(Lmax={Lmax},b={b})",
                total=total_inner,
            )
            prog_m2.start()
            inner_i = 0

            for lv_fit in level_assignments_fit:
                level_of: Dict[str, int] = {}
                for i, n in enumerate(fit_names):
                    level_of[n] = int(lv_fit[i])
                for n in ub_names:
                    level_of[n] = int(Lmax)
                for n in lb_names:
                    level_of[n] = int(Lmax)

                for dt in delta_triplets:
                    delta_of = {0: dt[0], 1: dt[1], 2: dt[2]}

                    # Estimate (a, channel choices) by a deterministic finite-step fixed-point iteration:
                    #  - initialize channels (fixed if provided; else default 0)
                    #  - compute a by median residuals under current channels (snap to grid)
                    #  - update channels by minimizing the *actual* per-point score under current a
                    #  - iterate a small bounded number of times or until stable
                    ch_choice: Dict[str, int] = {}
                    for n in fit_names:
                        ch_choice[n] = int(ch_fixed[n]) if (n in ch_fixed) else 0
                    for n in ub_names:
                        ch_choice[n] = int(ch_fixed[n]) if (n in ch_fixed) else 0
                    for n in lb_names:
                        ch_choice[n] = int(ch_fixed[n]) if (n in ch_fixed) else 0

                    a = 0
                    for _iter in range(3):
                        # Update a from median residuals under current channel choices.
                        residuals = [
                            obs_log10[n] + b * (level_of[n] - 1) - float(delta_of[int(ch_choice[n])])
                            for n in fit_names
                        ]
                        a_med = _median(residuals)
                        a_new = min(a_grid, key=lambda x: abs(x - a_med))

                        # Update channels using current a_new.
                        changed = False
                        for n in fit_names:
                            if n in ch_fixed:
                                continue
                            base_pred = float(a_new) - float(b) * float(level_of[n] - 1)
                            g_hat = 10.0 ** obs_log10[n]
                            sig_rel_log10 = obs_sig_log10[n]
                            sig = (sig_rel_log10 * g_hat * math.log(10.0)) if (sig_rel_log10 is not None) else None
                            best = None
                            for c in (0, 1, 2):
                                g_pred = 10.0 ** (base_pred + float(delta_of[c]))
                                s = _score_point(g_pred, g_hat, sig)
                                key = (s, c)
                                if best is None or key < best[0]:
                                    best = (key, c)
                            assert best is not None
                            c_best = int(best[1])
                            if int(ch_choice.get(n, 0)) != c_best:
                                ch_choice[n] = c_best
                                changed = True

                        if int(a) != int(a_new):
                            changed = True
                        a = int(a_new)
                        if not changed:
                            break

                    # Now score with per-point best channel choice given the stabilized (a, ch_choice).
                    cost = 0.0
                    used = set()
                    for n in fit_names:
                        base_pred = float(a) - float(b) * float(level_of[n] - 1)
                        g_hat = 10.0 ** obs_log10[n]
                        sig_rel_log10 = obs_sig_log10[n]
                        sig = (sig_rel_log10 * g_hat * math.log(10.0)) if (sig_rel_log10 is not None) else None

                        if n in ch_fixed:
                            c = int(ch_fixed[n])
                            used.add(c)
                            pred_log10 = base_pred + float(delta_of[c])
                            g_pred = 10.0 ** pred_log10
                            cost += _score_point(g_pred, g_hat, sig)
                        else:
                            c = int(ch_choice.get(n, 0))
                            used.add(c)
                            g_pred = 10.0 ** (base_pred + float(delta_of[c]))
                            cost += _score_point(g_pred, g_hat, sig)

                    for n in ub_names:
                        base_pred = float(a) - float(b) * float(level_of[n] - 1)
                        g_max = 10.0 ** ub_log10[n]
                        if n in ch_fixed:
                            c = int(ch_fixed[n])
                            g_pred = 10.0 ** (base_pred + float(delta_of[c]))
                            cost += _score_upper_bound(g_pred, g_max)
                        else:
                            c = int(ch_choice.get(n, 0))
                            g_pred = 10.0 ** (base_pred + float(delta_of[c]))
                            cost += _score_upper_bound(g_pred, g_max)

                    for n in lb_names:
                        base_pred = float(a) - float(b) * float(level_of[n] - 1)
                        g_min = 10.0 ** lb_log10[n]
                        if n in ch_fixed:
                            c = int(ch_fixed[n])
                            g_pred = 10.0 ** (base_pred + float(delta_of[c]))
                            cost += _score_lower_bound(g_pred, g_min)
                        else:
                            c = int(ch_choice.get(n, 0))
                            g_pred = 10.0 ** (base_pred + float(delta_of[c]))
                            cost += _score_lower_bound(g_pred, g_min)

                    mdl = 0.01 * (
                        Lmax
                        + abs(a) / 10.0
                        + b / 10.0
                        + sum(abs(x) for x in dt) / 10.0
                    )
                    total = cost + mdl
                    detail = f"levels_fit={lv_fit}; used_channels={tuple(ch_names[i] for i in sorted(used))}; delta={dt}"
                    push_candidate(
                        float(total),
                        BestModel(
                            model="M2",
                            b=int(b),
                            a=int(a),
                            level_max=int(Lmax),
                            md_cost=float(total),
                            detail=detail,
                        ),
                    )
                    inner_i += 1
                    prog_m2.maybe(inner_i)
            prog_m2.done()

    assert top, "No candidates evaluated"
    top.sort(key=lambda t: (t[0], t[1].model, t[1].level_max, t[1].b, t[1].a))
    best = top[0][1]
    return best, top


def main() -> None:
    entries = _load_entries()
    best, top = _evaluate_models(entries)

    rows: List[str] = []
    for i, (score, m) in enumerate(top, start=1):
        rows.append(
            " & ".join(
                [
                    str(i),
                    m.model,
                    str(int(m.level_max)),
                    str(int(m.b)),
                    str(int(m.a)),
                    _fmt(float(m.md_cost), 6),
                    _tex_escape(m.detail[:90] + ("..." if len(m.detail) > 90 else "")),
                ]
            )
            + r" \\"
        )

    out = generated_dir()
    write_lines(out / "k4_pdg_leakage_rows.tex", rows if rows else ["% (no rows)"])

    summary = [
        r"\paragraph{Audit summary (K4 leakage vs PDG mini-set).} \AuditTag "
        + rf"Dataset size: {len(entries)}. "
        + r"We convert lifetimes to leakage-rate proxies $\Gamma=1/\tau$ (proxy units: s$^{-1}$), "
        + r"and treat lower bounds as one-sided constraints on $\Gamma$ (upper bounds). "
        + r"Candidate families M1/M2 are evaluated on bounded discrete parameter sets; "
        + r"scoring uses an audit norm based on absolute log mismatch plus a small MDL-like penalty.",
        r"\noindent\AuditTag "
        + rf"Selected best model: {best.model} with $(L_{{\\mathrm{{max}}}},b,a)=({best.level_max},{best.b},{best.a})$ and score {_fmt(best.md_cost, 6)}.",
    ]
    write_lines(out / "k4_pdg_leakage_summary.tex", summary)


if __name__ == "__main__":
    main()

