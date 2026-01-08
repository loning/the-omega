# -*- coding: utf-8 -*-
"""
Cosmology energy-budget fit (discrete resolution matching).

Implements Appendix 32's interface hypothesis:
  f_stab(m) = F_{m+2} / 2^m
and selects an effective integer window length m_* by discrete matching to a
target present-day visible fraction Omega_vis,0 (e.g., baryon fraction).

Outputs:
  - sections/generated/cosmology_energy_budget_fit_equation.tex
  - sections/generated/cosmology_energy_budget_fit_summary.tex
  - sections/generated/cosmology_energy_budget_fit_stability.tex
  - figures/cosmology_energy_budget_fit.png (required; requires matplotlib)

Core computation is standard-library only. Plotting is required.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from common_paths import figures_dir, generated_dir
from common_tex import write_lines


def fib(n: int) -> int:
    # Fibonacci numbers with F1=F2=1.
    if n <= 0:
        raise ValueError("n must be positive.")
    if n in (1, 2):
        return 1
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


def f_stab(m: int) -> Tuple[int, int, float]:
    """
    Return (numerator, denominator, value) for f_stab(m)=F_{m+2}/2^m.
    """
    if m < 1:
        raise ValueError("m must be >= 1.")
    num = fib(m + 2)
    den = 1 << m  # 2^m
    return num, den, num / float(den)


@dataclass(frozen=True)
class FitResult:
    m_star: int
    num: int
    den: int
    f_stab: float
    f_hid: float
    ratio_hid_to_stab: float


def best_fit_m(omega_vis0: float, m_min: int, m_max: int) -> FitResult:
    if not (0.0 < omega_vis0 < 1.0):
        raise ValueError("omega_vis0 must be in (0, 1).")
    if m_min < 1:
        raise ValueError("m_min must be >= 1.")
    if m_max < m_min:
        raise ValueError("m_max must be >= m_min.")

    best: FitResult | None = None
    best_err: float | None = None
    for m in range(int(m_min), int(m_max) + 1):
        num, den, v = f_stab(m)
        # Use scale-invariant log-mismatch in line with Appendix 32.
        err = abs(math.log(v / omega_vis0))
        if best is None or best_err is None or err < best_err or (err == best_err and m < best.m_star):
            f_hid = 1.0 - v
            ratio = f_hid / v
            best = FitResult(
                m_star=m,
                num=num,
                den=den,
                f_stab=v,
                f_hid=f_hid,
                ratio_hid_to_stab=ratio,
            )
            best_err = err

    if best is None:
        raise RuntimeError("No fit result (unexpected).")
    return best


def fmt_float(x: float, digits: int) -> str:
    if digits < 0:
        raise ValueError("digits must be >= 0.")
    return f"{x:.{digits}f}"


def fmt_sci_tex(x: float, digits: int = 6) -> str:
    """
    Format a float in a stable LaTeX-friendly scientific notation: a×10^{b}.
    """
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    s = f"{x:.{max(1, digits)}e}"
    mant, exp = s.split("e")
    e = int(exp)
    if e == 0:
        return mant
    return f"{mant}\\times 10^{{{e}}}"


def equation_line(res: FitResult, digits: int) -> str:
    # Appendix 32 displays F_{m+2}/2^m and a concrete rational instance.
    approx = fmt_float(res.f_stab, digits=digits)
    f_index = res.m_star + 2
    return (
        f"\\frac{{F_{{{f_index}}}}}{{2^{{{res.m_star}}}}}"
        f"=\\frac{{{res.num}}}{{{res.den}}}\\approx {approx},"
    )


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def stability_ms(omega_vis0: float, omega_vis0_sigma: float, m_min: int, m_max: int) -> List[int]:
    """
    Return the discrete set of m values whose Voronoi cell (by absolute-log-mismatch matching
    against f_stab(m)) intersects the uncertainty interval [omega-sigma, omega+sigma].
    """
    if omega_vis0_sigma < 0.0:
        raise ValueError("omega_vis0_sigma must be >= 0.")
    lo = _clamp01(omega_vis0 - omega_vis0_sigma)
    hi = _clamp01(omega_vis0 + omega_vis0_sigma)
    if hi < lo:
        lo, hi = hi, lo

    vals: List[Tuple[int, float]] = []
    for m in range(int(m_min), int(m_max) + 1):
        _num, _den, v = f_stab(m)
        vals.append((m, float(v)))

    # f_stab(m) is strictly decreasing in m for m>=1, so Voronoi cells are contiguous.
    allowed: List[int] = []
    for i, (m, v) in enumerate(vals):
        if i == 0:
            left = 1.0
        else:
            # Boundary between neighbors under |log(v/omega)| distance is the geometric mean.
            left = math.sqrt(vals[i - 1][1] * v)
        if i == len(vals) - 1:
            right = 0.0
        else:
            right = math.sqrt(v * vals[i + 1][1])
        # Cell is (right, left] within [0,1].
        cell_lo = max(0.0, right)
        cell_hi = min(1.0, left)
        if (hi > cell_lo) and (lo <= cell_hi):
            allowed.append(int(m))
    return allowed


def try_plot(
    points: Iterable[Tuple[int, float]],
    omega_vis0: float,
    res: FitResult,
) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "matplotlib is required to generate figures/cosmology_energy_budget_fit.png. "
            "Install the paper's requirements.txt and re-run."
        ) from e

    ms: List[int] = []
    ys: List[float] = []
    for m, v in points:
        ms.append(int(m))
        ys.append(float(v))

    fig = plt.figure(figsize=(6.5, 3.2))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(ms, ys, linewidth=2.0, label=r"$f_{\mathrm{stab}}(m)$")
    ax.axhline(omega_vis0, linestyle="--", linewidth=1.2, label=r"target $\Omega_{\mathrm{vis},0}$")
    ax.scatter([res.m_star], [res.f_stab], s=32, zorder=3)
    ax.set_xlabel("window length m")
    ax.set_ylabel(r"$f_{\mathrm{stab}}(m)=F_{m+2}/2^m$")
    ax.set_title("Discrete energy-budget fit (resolution matching)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, loc="best")

    fig_dir = figures_dir()
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_png = fig_dir / "cosmology_energy_budget_fit.png"
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser(description="Discrete cosmology energy-budget fit (Appendix 32).")
    p.add_argument(
        "--omega-vis0",
        type=float,
        default=0.0493,
        help="Target present-day visible fraction Omega_vis,0 (default: 0.0493).",
    )
    p.add_argument(
        "--omega-vis0-sigma",
        type=float,
        default=0.0005,
        help="Uncertainty (1σ) on Omega_vis,0 used only for a discrete stability diagnostic (default: 5e-4).",
    )
    p.add_argument(
        "--omega-dm-over-omega-b",
        type=float,
        default=5.36,
        help="Reference dark-to-baryon ratio Omega_DM/Omega_b used only for mismatch reporting (default: 5.36).",
    )
    p.add_argument("--m-min", type=int, default=1, help="Minimum integer window length to scan (>=1).")
    p.add_argument("--m-max", type=int, default=40, help="Maximum integer window length to scan (>=m-min).")
    p.add_argument(
        "--digits",
        type=int,
        default=4,
        help="Digits after decimal for the \\approx value in the generated equation.",
    )
    args = p.parse_args()

    res = best_fit_m(omega_vis0=float(args.omega_vis0), m_min=int(args.m_min), m_max=int(args.m_max))
    ms = stability_ms(
        omega_vis0=float(args.omega_vis0),
        omega_vis0_sigma=float(args.omega_vis0_sigma),
        m_min=int(args.m_min),
        m_max=int(args.m_max),
    )

    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cosmology_energy_budget_fit_equation.tex"
    write_lines(out_path, [equation_line(res, digits=int(args.digits))])
    print(f"Wrote sections/generated/{out_path.name}")

    # Primary reference ratio implied by the same target (if one identifies the
    # "hidden" sector with the complement of the visible fraction at z=0).
    omega_vis0 = float(args.omega_vis0)
    ratio_ref_hidden_over_vis = (1.0 - omega_vis0) / omega_vis0

    # Optional secondary reference ratio (DM-only vs baryons) used only for
    # a stricter matching-layer diagnostic if the user chooses to interpret
    # "hidden" as "dark matter" only.
    ratio_ref_dm_over_b = float(args.omega_dm_over_omega_b)
    if ratio_ref_dm_over_b <= 0.0:
        raise ValueError("omega_dm_over_omega_b must be > 0.")
    ratio_pred = float(res.ratio_hid_to_stab)
    log_mismatch_hidden_over_vis = math.log(ratio_pred / ratio_ref_hidden_over_vis)
    log_mismatch_dm_over_b = math.log(ratio_pred / ratio_ref_dm_over_b)

    summary_lines = [
        (
            f"Selected $m_\\ast={res.m_star}$, "
            f"$f_\\mathrm{{stab}}(m_\\ast)={fmt_sci_tex(res.f_stab)}$, "
            f"$f_\\mathrm{{hid}}/f_\\mathrm{{stab}}={fmt_sci_tex(ratio_pred)}$, "
            f"with $(\\Omega_\\mathrm{{hid}}/\\Omega_\\mathrm{{vis}})_\\mathrm{{ref}}=(1-\\Omega_{{\\mathrm{{vis}},0}})/\\Omega_{{\\mathrm{{vis}},0}}={fmt_sci_tex(ratio_ref_hidden_over_vis)}$, "
            f"$\\log\\!\\bigl((f_\\mathrm{{hid}}/f_\\mathrm{{stab}})/(\\Omega_\\mathrm{{hid}}/\\Omega_\\mathrm{{vis}})_\\mathrm{{ref}}\\bigr)"
            f"={fmt_sci_tex(log_mismatch_hidden_over_vis)}$."
        ),
        (
            f"Optional DM-only comparison (matching-layer): "
            f"$(\\Omega_\\mathrm{{DM}}/\\Omega_\\mathrm{{b}})_\\mathrm{{ref}}={fmt_sci_tex(ratio_ref_dm_over_b)}$, "
            f"$\\log\\!\\bigl((f_\\mathrm{{hid}}/f_\\mathrm{{stab}})/(\\Omega_\\mathrm{{DM}}/\\Omega_\\mathrm{{b}})_\\mathrm{{ref}}\\bigr)"
            f"={fmt_sci_tex(log_mismatch_dm_over_b)}$."
        ),
    ]
    write_lines(out_dir / "cosmology_energy_budget_fit_summary.tex", summary_lines)

    if ms:
        ms_tex = ", ".join(str(m) for m in ms)
        stable_flag = "stable" if (len(ms) == 1 and ms[0] == res.m_star) else "not stable"
        stab_line = (
            f"Stability diagnostic: for $\\Omega_{{\\mathrm{{vis}},0}}={fmt_float(float(args.omega_vis0), 6)}"
            f"\\pm {fmt_float(float(args.omega_vis0_sigma), 6)}$ (1$\\sigma$), "
            f"the admissible discrete set is $\\{{{ms_tex}\\}}$ ({stable_flag})."
        )
    else:
        stab_line = (
            f"Stability diagnostic: no admissible $m$ found in the scanned range "
            f"$[{int(args.m_min)},{int(args.m_max)}]$ (unexpected)."
        )
    write_lines(out_dir / "cosmology_energy_budget_fit_stability.tex", [stab_line])

    print(f"[fit] omega_vis0={args.omega_vis0}")
    print(f"[fit] m*={res.m_star}")
    print(f"[fit] f_stab(m*)={res.f_stab:.12g}")
    print(f"[fit] f_hid(m*)={res.f_hid:.12g}")
    print(f"[fit] f_hid/f_stab={res.ratio_hid_to_stab:.12g}")
    print(f"[fit] ref Omega_hid/Omega_vis=(1-omega_vis0)/omega_vis0={ratio_ref_hidden_over_vis:.12g}")
    print(f"[fit] log mismatch (pred/ref, hid/vis)={log_mismatch_hidden_over_vis:.12g}")
    print(f"[fit] ref Omega_DM/Omega_b={ratio_ref_dm_over_b:.12g}")
    print(f"[fit] log mismatch (pred/ref, dm/b)={log_mismatch_dm_over_b:.12g}")

    points: List[Tuple[int, float]] = []
    for m in range(int(args.m_min), int(args.m_max) + 1):
        _num, _den, v = f_stab(m)
        points.append((m, v))
    try_plot(points=points, omega_vis0=float(args.omega_vis0), res=res)


if __name__ == "__main__":
    main()


