# -*- coding: utf-8 -*-
"""
Cosmology energy-budget fit (discrete resolution matching).

Implements Appendix 32's interface hypothesis:
  f_stab(m) = F_{m+2} / 2^m
and selects an effective integer window length m_* by discrete matching to a
target present-day visible fraction Omega_vis,0 (e.g., baryon fraction).

Outputs:
  - sections/generated/cosmology_energy_budget_fit_equation.tex
  - figures/cosmology_energy_budget_fit.png (required; requires matplotlib)

Core computation is standard-library only. Plotting is required.
"""

from __future__ import annotations

import argparse
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
        err = abs(v - omega_vis0)
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


def equation_line(res: FitResult, digits: int) -> str:
    # Appendix 32 displays F_{m+2}/2^m and a concrete rational instance.
    approx = fmt_float(res.f_stab, digits=digits)
    f_index = res.m_star + 2
    return (
        f"\\frac{{F_{{{f_index}}}}}{{2^{{{res.m_star}}}}}"
        f"=\\frac{{{res.num}}}{{{res.den}}}\\approx {approx},"
    )


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

    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cosmology_energy_budget_fit_equation.tex"
    write_lines(out_path, [equation_line(res, digits=int(args.digits))])
    print(f"Wrote sections/generated/{out_path.name}")

    print(f"[fit] omega_vis0={args.omega_vis0}")
    print(f"[fit] m*={res.m_star}")
    print(f"[fit] f_stab(m*)={res.f_stab:.12g}")
    print(f"[fit] f_hid(m*)={res.f_hid:.12g}")
    print(f"[fit] f_hid/f_stab={res.ratio_hid_to_stab:.12g}")

    points: List[Tuple[int, float]] = []
    for m in range(int(args.m_min), int(args.m_max) + 1):
        _num, _den, v = f_stab(m)
        points.append((m, v))
    try_plot(points=points, omega_vis0=float(args.omega_vis0), res=res)


if __name__ == "__main__":
    main()


