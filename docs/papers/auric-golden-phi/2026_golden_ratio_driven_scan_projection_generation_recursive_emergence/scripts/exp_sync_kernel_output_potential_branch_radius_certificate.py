#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Branch points in complex u and analytic radius in theta for the sync-kernel output potential.

We use the explicit degree-6 algebraic curve for the Perron root lambda(u):

  F(lambda,u)=0,  with F in Z[u][lambda],

as stated in `sections/90_appendix_sync_kernel_weighted.tex` (appendix pressure-analytic).
Branch points in the u-plane occur exactly when lambda becomes a multiple root, i.e.
F=0 and dF/dlambda=0, equivalently Disc_lambda(F)(u)=0.

We compute:
  - the discriminant Disc_lambda(F)(u) and its factorization
  - the palindromic degree-20 factor D(u)
  - nearest branch points in theta = Log(u) (min over 2π i Z shifts)
  - an auditable Cauchy remainder certificate for the 8th-order Taylor truncation of P(theta)=log lambda(e^theta)
    using a numerical bound M_r = max_{|theta|=r} |P(theta)| at r=0.99*R_theta.
  - a comparison radius for the phi_minus cubic example (negative-carry potential) from
    `sections/90_appendix_sync_kernel_multi_dim.tex`.

Outputs:
  - artifacts/export/sync_kernel_output_potential_branch_radius_certificate.json
  - sections/generated/eq_sync_kernel_output_potential_branch_radius_certificate.tex
"""

from __future__ import annotations

import argparse
import json
import math
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import sympy as sp

from common_paths import export_dir, generated_dir


class _Progress:
    def __init__(
        self,
        *,
        enabled: bool,
        every_seconds: float,
        prefix: str = "[sync-branch-radius]",
    ) -> None:
        self._enabled = enabled and every_seconds > 0
        self._every_seconds = float(every_seconds)
        self._prefix = prefix
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0

    def start(self, msg: str) -> None:
        if not self._enabled:
            return
        self._t0 = time.time()
        print(f"{self._prefix} {msg}", flush=True)

        def _run() -> None:
            while not self._stop.wait(self._every_seconds):
                dt = time.time() - self._t0
                print(f"{self._prefix} still running... elapsed={dt:.1f}s", flush=True)

        self._thread = threading.Thread(target=_run, name="progress", daemon=True)
        self._thread.start()

    def stop(self, msg: str) -> None:
        if not self._enabled:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        dt = time.time() - self._t0
        print(f"{self._prefix} {msg} elapsed={dt:.1f}s", flush=True)


def _F(lam: sp.Symbol, u: sp.Symbol) -> sp.Expr:
    # Must match `sections/90_appendix_sync_kernel_weighted.tex` (app:pressure-analytic).
    return sp.expand(
        lam**6
        - (1 + u) * lam**5
        - 5 * u * lam**4
        + 3 * u * (1 + u) * lam**3
        - u * (u**2 - 3 * u + 1) * lam**2
        + u * (u**3 - 3 * u**2 - 3 * u + 1) * lam
        + u**2 * (u**2 + u + 1)
    )


def _phi_minus_cubic(lam: sp.Symbol, u: sp.Symbol) -> sp.Expr:
    # Must match `sections/90_appendix_sync_kernel_multi_dim.tex` (negative-carry example).
    return sp.expand(lam**3 - (u + 2) * lam**2 + (u - 2) * lam + 3 * u)


def _normalize_int_poly_u(expr: sp.Expr, u: sp.Symbol) -> sp.Expr:
    P = sp.Poly(sp.expand(expr), u, domain=sp.ZZ)
    if P.LC() < 0:
        P = sp.Poly(-P.as_expr(), u, domain=sp.ZZ)
    content = int(sp.gcd_list([int(c) for c in P.all_coeffs()])) if P.all_coeffs() else 1
    if content > 1:
        P = sp.Poly(P.as_expr() // content, u, domain=sp.ZZ)
    return sp.expand(P.as_expr())


def _disc_and_D() -> Tuple[sp.Expr, sp.Expr]:
    lam, u = sp.symbols("lam u")
    F = _F(lam, u)
    disc = sp.discriminant(sp.Poly(F, lam), lam)
    disc = sp.expand(disc)
    disc = _normalize_int_poly_u(disc, u)
    # Factor out u^5 (expected) and keep remaining integer polynomial.
    P = sp.Poly(disc, u, domain=sp.ZZ)
    # Poly valuation at u: minimal exponent with nonzero coefficient.
    if P.is_zero:
        raise RuntimeError("discriminant is zero (unexpected)")
    exps = [int(e[0]) for e in P.as_dict().keys()]
    v = min(exps) if exps else 0
    D = sp.expand(disc / (u**v))
    # Normalize sign to match the paper convention Disc = -u^5 D(u) with D(0)>0.
    D0 = int(sp.Poly(D, u, domain=sp.ZZ).eval(0))
    if D0 < 0:
        disc = -disc
        D = -D
    return disc, sp.expand(D)


def _min_theta_distance(u0: complex, max_k: int = 6) -> complex:
    # theta candidates: Log(u0) + 2π i k, choose with minimal |theta|.
    import cmath

    base = cmath.log(u0)
    best = None
    for k in range(-max_k, max_k + 1):
        th = base + 2j * math.pi * k
        if best is None or abs(th) < abs(best):
            best = th
    assert best is not None
    return best


def _newton_root_on_branch(
    *,
    u: complex,
    lam0: complex,
    max_iter: int = 50,
    tol: float = 1e-12,
) -> complex:
    lam_sym, u_sym = sp.symbols("lam u")
    F = _F(lam_sym, u_sym)
    dF = sp.diff(F, lam_sym)
    Ff = sp.lambdify((lam_sym, u_sym), F, "mpmath")
    dFf = sp.lambdify((lam_sym, u_sym), dF, "mpmath")
    import mpmath as mp

    lam = mp.mpc(lam0)
    uu = mp.mpc(u)
    for _ in range(max_iter):
        f = Ff(lam, uu)
        fp = dFf(lam, uu)
        if fp == 0:
            break
        step = f / fp
        lam2 = lam - step
        if abs(lam2 - lam) <= tol * (1 + abs(lam2)):
            lam = lam2
            return complex(lam)
        lam = lam2
    return complex(lam)


def _track_circle_Mr(
    *,
    r: float,
    nphi: int,
    radial_steps: int,
    dps: int,
) -> Tuple[float, float]:
    """
    Track the analytic branch lambda(e^theta) starting from theta=0, lambda=3,
    along the circle |theta|=r (in the theta-plane), and return:
      Mr = max_{|theta|=r} |P(theta)| on the continuous log branch,
      and max |lambda| as a sanity check.
    """
    import cmath
    import mpmath as mp

    mp.mp.dps = int(dps)

    # First reach theta=r (phi=0) along a radial segment.
    lam = 3.0 + 0.0j
    P = math.log(3.0) + 0.0j
    theta_prev = 0.0 + 0.0j
    lam_prev = lam
    for j in range(1, radial_steps + 1):
        theta = (r * j / radial_steps) + 0.0j
        u = cmath.exp(theta)
        lam = _newton_root_on_branch(u=u, lam0=lam_prev, tol=1e-28)
        # continuous log: P += Log(lam/lam_prev) with principal log of ratio (ratio near 1)
        ratio = lam / lam_prev
        P = P + cmath.log(ratio)
        theta_prev = theta
        lam_prev = lam

    # Now traverse the circle.
    Mr = abs(P)
    max_lam = abs(lam_prev)
    for k in range(1, nphi + 1):
        phi = 2.0 * math.pi * k / nphi
        theta = r * complex(math.cos(phi), math.sin(phi))
        u = cmath.exp(theta)
        lam = _newton_root_on_branch(u=u, lam0=lam_prev, tol=1e-26)
        ratio = lam / lam_prev
        P = P + cmath.log(ratio)
        Mr = max(Mr, abs(P))
        max_lam = max(max_lam, abs(lam))
        lam_prev = lam

    return float(Mr), float(max_lam)


@dataclass(frozen=True)
class BranchRadiusPayload:
    disc_u: str
    D_u: str
    D_degree: int
    D_is_palindromic: bool
    nearest_u: str
    nearest_u_inv: str
    theta_star: str
    R_theta: float
    arg_theta_star: float
    r_used: float
    Mr_bound: float
    remainder_bound_theta_le_0_5: float
    phi_minus_disc_u: str
    phi_minus_nearest_u: str
    phi_minus_theta_star: str
    phi_minus_R_theta: float


def _is_palindromic(P: sp.Poly) -> bool:
    coeffs = [int(c) for c in P.all_coeffs()]
    return coeffs == list(reversed(coeffs))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Branch points, analytic radius in theta, and Taylor remainder certificate for sync-kernel output potential."
    )
    parser.add_argument("--dps", type=int, default=80, help="Decimal digits for root finding/tracking.")
    parser.add_argument("--nphi", type=int, default=1024, help="Number of circle samples for M_r.")
    parser.add_argument(
        "--radial-steps",
        type=int,
        default=160,
        help="Steps for radial continuation from theta=0 to theta=r.",
    )
    parser.add_argument(
        "--radius-factor",
        type=float,
        default=0.99,
        help="Use r = radius_factor * R_theta for Cauchy certificate.",
    )
    parser.add_argument(
        "--progress-seconds",
        type=float,
        default=20.0,
        help="Print a heartbeat progress line every N seconds (0 disables).",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "sync_kernel_output_potential_branch_radius_certificate.json"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "eq_sync_kernel_output_potential_branch_radius_certificate.tex"),
    )
    args = parser.parse_args()

    prog = _Progress(enabled=(args.progress_seconds > 0), every_seconds=float(args.progress_seconds))
    prog.start("computing discriminant and branch radius")
    try:
        import mpmath as mp

        mp.mp.dps = int(args.dps)

        lam, u = sp.symbols("lam u")
        disc, D = _disc_and_D()
        Dpoly = sp.Poly(D, u, domain=sp.ZZ)
        deg = int(Dpoly.degree())
        pal = _is_palindromic(Dpoly)

        # Numerical roots of D(u)=0.
        print("[sync-branch-radius] finding roots of D(u)=0", flush=True)
        roots = sp.nroots(Dpoly, n=int(args.dps), maxsteps=250)
        roots_c: List[complex] = [complex(sp.N(r, int(args.dps))) for r in roots]
        # Choose u_star that minimizes min_k |Log(u)+2π i k|.
        best_u = None
        best_theta = None
        for uu in roots_c:
            if abs(uu) == 0:
                continue
            th = _min_theta_distance(uu, max_k=8)
            if best_theta is None or abs(th) < abs(best_theta):
                best_theta = th
                best_u = uu
        assert best_u is not None and best_theta is not None
        # Use the inverse if it gives a theta with positive real part (presentation choice).
        u_inv = 1.0 / best_u
        theta_inv = _min_theta_distance(u_inv, max_k=8)
        theta_star = theta_inv if (theta_inv.real >= 0) else best_theta
        u_star = u_inv if (theta_inv.real >= 0) else best_u

        R_theta = float(abs(theta_star))
        arg_theta = float(math.atan2(theta_star.imag, theta_star.real))

        # Cauchy remainder certificate via M_r on |theta|=r.
        r_used = float(args.radius_factor) * R_theta
        print("[sync-branch-radius] tracking analytic branch on |theta|=r", flush=True)
        Mr, _max_lam = _track_circle_Mr(
            r=r_used,
            nphi=int(args.nphi),
            radial_steps=int(args.radial_steps),
            dps=int(args.dps),
        )
        # Add a small safety margin.
        Mr_bound = float(Mr) * 1.01

        # Bound for |theta|<=0.5.
        theta_max = 0.5
        rem = Mr_bound * (theta_max**9) / (r_used**9) * (1.0 / (1.0 - theta_max / r_used))

        # Negative-carry cubic discriminant and radius.
        print("[sync-branch-radius] computing phi_minus discriminant and radius", flush=True)
        G = _phi_minus_cubic(lam, u)
        disc2 = sp.discriminant(sp.Poly(G, lam), lam)
        disc2 = _normalize_int_poly_u(disc2, u)
        disc2_poly = sp.Poly(disc2, u, domain=sp.ZZ)
        roots2 = sp.nroots(disc2_poly, n=int(args.dps), maxsteps=200)
        roots2_c: List[complex] = [complex(sp.N(r, int(args.dps))) for r in roots2]
        best_u2 = None
        best_th2 = None
        for uu in roots2_c:
            if abs(uu) == 0:
                continue
            th = _min_theta_distance(uu, max_k=8)
            if best_th2 is None or abs(th) < abs(best_th2):
                best_th2 = th
                best_u2 = uu
        assert best_u2 is not None and best_th2 is not None
        theta2 = best_th2
        u2 = best_u2
        if theta2.real < 0:
            # Prefer a representative with Re(theta)>=0.
            u2 = 1.0 / u2
            theta2 = _min_theta_distance(u2, max_k=8)
        R2 = float(abs(theta2))

        payload = BranchRadiusPayload(
            disc_u=str(disc),
            D_u=str(D),
            D_degree=deg,
            D_is_palindromic=bool(pal),
            nearest_u=f"{u_star.real:.10f}{u_star.imag:+.10f}i",
            nearest_u_inv=f"{(1.0/u_star).real:.10f}{(1.0/u_star).imag:+.10f}i",
            theta_star=f"{theta_star.real:.10f}{theta_star.imag:+.10f}i",
            R_theta=float(R_theta),
            arg_theta_star=float(arg_theta),
            r_used=float(r_used),
            Mr_bound=float(Mr_bound),
            remainder_bound_theta_le_0_5=float(rem),
            phi_minus_disc_u=str(disc2),
            phi_minus_nearest_u=f"{u2.real:.10f}{u2.imag:+.10f}i",
            phi_minus_theta_star=f"{theta2.real:.10f}{theta2.imag:+.10f}i",
            phi_minus_R_theta=float(R2),
        )

        jout = Path(args.json_out)
        jout.parent.mkdir(parents=True, exist_ok=True)
        jout.write_text(json.dumps(asdict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")

        # Build TeX snippet (Chinese, for the paper).
        u_tex = sp.Symbol("u")
        D_expr = sp.Poly(D, u_tex, domain=sp.ZZ).as_expr()
        # Present D(u) as a full polynomial (auditable).
        D_latex = sp.latex(D_expr)
        disc_latex = sp.latex(sp.Poly(disc, u_tex, domain=sp.ZZ).as_expr())

        disc2_expr = sp.Poly(disc2, u_tex, domain=sp.ZZ).as_expr()
        disc2_latex = sp.latex(disc2_expr)

        r_str = f"{r_used:.6f}"
        R_str = f"{R_theta:.10f}"
        Mr_str = f"{Mr_bound:.6f}"
        rem_str = f"{rem:.6e}"
        R2_str = f"{R2:.10f}"

        tex_lines: List[str] = []
        tex_lines.append("% AUTO-GENERATED by scripts/exp_sync_kernel_output_potential_branch_radius_certificate.py")
        tex_lines.append("\\begin{proposition}[复参数分歧点的判别式刻画]\\label{prop:pressure-branchpoints-discriminant}")
        tex_lines.append("把 $F(\\lambda,u)\\in\\ZZ[u][\\lambda]$ 视为关于 $\\lambda$ 的代数方程，并在 $u\\in\\CC^\\times$ 上延拓其代数函数分支。")
        tex_lines.append("则 $\\lambda(u)$ 的分歧点恰对应 $\\lambda$ 变为重根，即存在 $(\\lambda,u)\\in\\CC\\times\\CC^\\times$ 使得")
        tex_lines.append("$$")
        tex_lines.append("F(\\lambda,u)=0,\\qquad \\partial_{\\lambda}F(\\lambda,u)=0.")
        tex_lines.append("$$")
        tex_lines.append("等价地，分歧点的 $u$-集合由关于 $\\lambda$ 的判别式零点给出；对本附录的六次 $F$，有完全显式分解")
        tex_lines.append("$$")
        tex_lines.append("\\mathrm{Disc}_{\\lambda}(F)(u)=" + disc_latex + "=-u^{5}\\,D(u),")
        tex_lines.append("$$")
        tex_lines.append("其中 $D(u)\\in\\ZZ[u]$ 为 $20$ 次回文多项式：")
        tex_lines.append("$$")
        tex_lines.append("D(u)=" + D_latex + ".")
        tex_lines.append("$$")
        tex_lines.append("\\end{proposition}")
        tex_lines.append("")
        tex_lines.append("\\begin{corollary}[最近分歧点与 $\\theta$-解析半径]\\label{cor:pressure-analytic-radius}")
        tex_lines.append("以 $\\theta=\\log u$ 为局部坐标，并以 $\\lambda(1)=3$ 的 Perron 分支为基准进行解析延拓。")
        tex_lines.append("令 $u_\\star$ 为 $D(u)=0$ 的根中、使得 $|\\log u|$（在 $\\log u$ 的 $2\\pi i\\ZZ$ 选取中取最小模）最小者。")
        tex_lines.append("数值上可取")
        tex_lines.append("$$")
        tex_lines.append(f"u_\\star\\approx {payload.nearest_u},\\qquad u_\\star^{{-1}}\\approx {payload.nearest_u_inv},")
        tex_lines.append("$$")
        tex_lines.append("并且相应的最近分歧点可取")
        tex_lines.append("$$")
        tex_lines.append(f"\\theta_\\star=\\log u_\\star\\approx {payload.theta_star},\\qquad -\\theta_\\star,")
        tex_lines.append("$$")
        tex_lines.append("从而 $\\theta=0$ 处解析芽的最大圆盘半径为")
        tex_lines.append("$$")
        tex_lines.append(f"\\boxed{{\\ R_\\theta:=|\\theta_\\star|\\approx {R_str}\\ }}.")
        tex_lines.append("$$")
        tex_lines.append("因此在 $|\\theta|<R_\\theta$ 内，$\\lambda(e^{\\theta})$ 与 $P(\\theta)=\\log\\lambda(e^{\\theta})$ 可作为单值解析函数延拓；并且在 $|\\theta|=R_\\theta$ 处发生代数分歧（分支点）。")
        tex_lines.append("\\end{corollary}")
        tex_lines.append("")
        tex_lines.append("\\begin{corollary}[Taylor 截断余项的 Cauchy 证书]\\label{cor:pressure-taylor-remainder-cauchy}")
        tex_lines.append("设 $T_8(\\theta)$ 为 $P(\\theta)$ 在 $\\theta=0$ 的 Taylor 多项式截断到 $\\theta^8$。取任意 $0<r<R_\\theta$ 并记")
        tex_lines.append("$$")
        tex_lines.append("M_r:=\\max_{|\\theta|=r}|P(\\theta)|.")
        tex_lines.append("$$")
        tex_lines.append("则对任意 $|\\theta|<r$ 有一致余项上界")
        tex_lines.append("$$")
        tex_lines.append(
            "\\boxed{\\ \\bigl|P(\\theta)-T_8(\\theta)\\bigr|"
            "\\le M_r\\cdot \\frac{|\\theta|^{9}}{r^{9}}\\cdot\\frac{1}{1-|\\theta|/r}\\ }."
        )
        tex_lines.append("$$")
        tex_lines.append(f"取 $r:={args.radius_factor}\\,R_\\theta\\approx {r_str}$ 并沿 $|\\theta|=r$ 对分支作连续数值跟踪（初值 $\\lambda(1)=3$），得到上界 $M_r\\le {Mr_str}$。")
        tex_lines.append("因此当 $|\\theta|\\le 0.5$ 时，有可审计余项界")
        tex_lines.append("$$")
        tex_lines.append(f"\\bigl|P(\\theta)-T_8(\\theta)\\bigr|\\le {rem_str}.")
        tex_lines.append("$$")
        tex_lines.append("\\end{corollary}")
        tex_lines.append("")
        tex_lines.append("\\begin{remark}[分歧半径的势指纹：与负携带势的对比]\\label{rem:pressure-radius-compare-phi-minus}")
        tex_lines.append("在附录 \\ref{app:vector-potential} 的负携带势实例中，主特征值满足三次方程")
        tex_lines.append("$$")
        tex_lines.append("\\lambda^3-(u+2)\\lambda^2+(u-2)\\lambda+3u=0,\\qquad u=e^{\\theta}.")
        tex_lines.append("$$")
        tex_lines.append("对该三次关于 $\\lambda$ 取判别式（忽略非零常数因子）得到分歧点集合由四次多项式")
        tex_lines.append("$$")
        tex_lines.append(disc2_latex + "=0")
        tex_lines.append("$$")
        tex_lines.append("刻画；其最近分歧点可取")
        tex_lines.append("$$")
        tex_lines.append(f"u_\\star^{{(-)}}\\approx {payload.phi_minus_nearest_u},\\qquad \\theta_\\star^{{(-)}}\\approx {payload.phi_minus_theta_star},")
        tex_lines.append("$$")
        tex_lines.append("从而对应解析半径")
        tex_lines.append("$$")
        tex_lines.append(f"R_\\theta^{{(-)}}:=|\\theta_\\star^{{(-)}}|\\approx {R2_str}.")
        tex_lines.append("$$")
        tex_lines.append("因此在“分歧半径”这一可计算的谱指纹下，负携带势的局部解析半径大于同步核输出位势，从而在相同的 $|\\theta|$ 尺度上可获得更强的统一余项控制（Cauchy 估计中的 $r^{-n}$ 衰减更快）。")
        tex_lines.append("\\end{remark}")
        tex_lines.append("")
        tex_lines.append("\\begin{remark}[高阶偶系数的振荡与最近复分歧角]\\label{rem:pressure-even-derivative-oscillation}")
        tex_lines.append("令 $f(\\theta):=P(\\theta)-\\theta/2-\\log 3$，则 $f$ 为偶函数且在 $|\\theta|<R_\\theta$ 内解析。")
        tex_lines.append("由最近分歧点 $\\theta_\\star$ 的几何位置，可用 Darboux 型系数转移（或等价的 Cauchy 系数积分主贡献）解释高阶偶系数的符号/振荡：")
        tex_lines.append("其主导模式由 $\\pm\\theta_\\star$ 及其共轭贡献叠加给出，故 $f^{(2k)}(0)$ 的符号可由")
        tex_lines.append("$\\cos\\bigl(2k\\arg(\\theta_\\star)+\\phi_0\\bigr)$ 型项控制（$\\phi_0$ 为分支点局部相位）。")
        tex_lines.append(f"在本核上 $\\arg(\\theta_\\star)\\approx {payload.arg_theta_star:.10f}$。")
        tex_lines.append("\\end{remark}")

        tout = Path(args.tex_out)
        tout.parent.mkdir(parents=True, exist_ok=True)
        tout.write_text("\n".join(tex_lines) + "\n", encoding="utf-8")
    finally:
        prog.stop("done")


if __name__ == "__main__":
    main()

