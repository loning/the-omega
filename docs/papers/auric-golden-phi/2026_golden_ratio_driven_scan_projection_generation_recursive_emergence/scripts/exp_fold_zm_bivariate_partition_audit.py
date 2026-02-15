#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit the Fold fiber-weight bivariate partition function Z_m(y).

This script is English-only by repository convention.

We verify, by exact small-m enumeration and symbolic algebra:
  - The order-4 recurrence and rational t-generating function for Z_m(y)
  - The characteristic quartic Pi(lambda,y)
  - Discriminant factorization and the real Lee–Yang boundary root
  - LLN/CLT constants (mean and variance rate) via implicit differentiation at (lambda,y)=(2,1)
  - The local (m,k) 2D recurrence for coefficients a_{m,k}

Outputs (default):
  - artifacts/export/fold_zm_bivariate_partition_audit.json
  - sections/generated/eq_fold_zm_bivariate_partition_audit.tex
"""

from __future__ import annotations

import argparse
import json
import math
import time
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple

import sympy as sp

from common_paths import export_dir, generated_dir
from common_phi_fold import Progress, fold_m


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def enumerate_a_mk(m: int) -> List[int]:
    # a_{m,k} = sum_{x in X_m, |x|_1=k} d_m(x) = # {a in Omega_m : |Fold_m(a)|_1 = k}
    counts = [0] * (m + 1)
    for bits in product([0, 1], repeat=m):
        x = fold_m(bits)
        k = sum(x)
        counts[k] += 1
    return counts


def build_Z_polys(m_max: int, prog: Progress) -> Tuple[sp.Symbol, List[sp.Expr], List[List[int]]]:
    y = sp.Symbol("y")
    Z_exprs: List[sp.Expr] = []
    a: List[List[int]] = []
    for m in range(m_max + 1):
        counts = enumerate_a_mk(m)
        a.append(counts)
        expr = sp.Integer(0)
        for k, c in enumerate(counts):
            if c:
                expr += sp.Integer(c) * (y**k)
        Z_exprs.append(sp.expand(expr))
        prog.tick(f"enumerate m={m} total_micro={1<<m}")
    return y, Z_exprs, a


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Z_m(y) recurrence, discriminant, and LLN/CLT constants")
    parser.add_argument("--m-max", type=int, default=12, help="Max m for exact enumeration checks (default: 12)")
    parser.add_argument("--no-output", action="store_true", help="Skip writing outputs")
    args = parser.parse_args()

    t0 = time.time()
    prog = Progress(label="fold-zm-audit", every_seconds=10.0)
    print("[fold-zm-audit] start", flush=True)

    # --- Exact enumeration for Z_m(y) as polynomials in y ---
    y, Zm, a_mk = build_Z_polys(args.m_max, prog)

    # --- Recurrence and generating function checks ---
    t = sp.Symbol("t")
    N = 1 + y * t - y * t**2 - y**2 * t**3
    D = 1 - t - (2 * y + 1) * t**2 + t**3 + y * (y + 1) * t**4

    rec_ok = True
    rec_fail: List[Dict[str, object]] = []
    for m in range(4, args.m_max + 1):
        lhs = Zm[m]
        rhs = sp.expand(Zm[m - 1] + (2 * y + 1) * Zm[m - 2] - Zm[m - 3] - y * (y + 1) * Zm[m - 4])
        diff = sp.expand(lhs - rhs)
        if diff != 0:
            rec_ok = False
            rec_fail.append({"m": m, "diff": str(diff)})

    # series expansion of N/D and compare coefficients to enumerated Z_m(y)
    gen_ok = True
    gen_fail: List[Dict[str, object]] = []
    series = sp.series(N / D, t, 0, args.m_max + 1).removeO()
    series = sp.expand(series)
    for m in range(0, args.m_max + 1):
        coeff = sp.expand(sp.series(N / D, t, 0, m + 1).removeO().coeff(t, m))
        if sp.expand(coeff - Zm[m]) != 0:
            gen_ok = False
            gen_fail.append({"m": m, "coeff_minus_Zm": str(sp.expand(coeff - Zm[m]))})

    # --- 2D (m,k) recurrence check for a_{m,k} ---
    rec2_ok = True
    rec2_fail: List[Dict[str, object]] = []
    for m in range(4, args.m_max + 1):
        k_max = (m + 1) // 2  # ceil(m/2)
        for k in range(0, k_max + 1):
            get = lambda mm, kk: (a_mk[mm][kk] if (0 <= kk < len(a_mk[mm])) else 0)
            lhs = get(m, k)
            rhs = (
                get(m - 1, k)
                + get(m - 2, k)
                + 2 * get(m - 2, k - 1)
                - get(m - 3, k)
                - get(m - 4, k - 1)
                - get(m - 4, k - 2)
            )
            if lhs != rhs:
                rec2_ok = False
                rec2_fail.append({"m": m, "k": k, "lhs": lhs, "rhs": rhs})
                break
        if not rec2_ok:
            break

    # --- Symbolic algebra for Pi(lambda,y) and discriminant ---
    lam = sp.Symbol("lam")
    Pi = lam**4 - lam**3 - (2 * y + 1) * lam**2 + lam + y * (y + 1)
    disc = sp.factor(sp.discriminant(Pi, lam))
    disc_expected = -y * (y - 1) * (256 * y**3 + 411 * y**2 + 165 * y + 32)
    disc_ok = sp.factor(disc - disc_expected) == 0

    # Lee–Yang real root
    cubic = 256 * y**3 + 411 * y**2 + 165 * y + 32
    roots = [complex(r) for r in sp.nroots(cubic)]
    y_ly = None
    for r in roots:
        if abs(r.imag) < 1e-10:
            y_ly = float(r.real)
            break

    # --- Implicit differentiation at (lam,y)=(2,1) for mean/variance ---
    Pi_l = sp.diff(Pi, lam)
    Pi_y = sp.diff(Pi, y)
    Pi_ll = sp.diff(Pi, lam, 2)
    Pi_ly = sp.diff(Pi, lam, 1, y, 1)
    Pi_yy = sp.diff(Pi, y, 2)

    lam0 = sp.Integer(2)
    y0 = sp.Integer(1)
    A = sp.simplify(Pi_l.subs({lam: lam0, y: y0}))
    By = sp.simplify(Pi_y.subs({lam: lam0, y: y0}))
    lam1 = sp.simplify(-By / A)  # d lam / d y at y=1

    ll0 = sp.simplify(Pi_ll.subs({lam: lam0, y: y0}))
    ly0 = sp.simplify(Pi_ly.subs({lam: lam0, y: y0}))
    yy0 = sp.simplify(Pi_yy.subs({lam: lam0, y: y0}))
    lam2 = sp.simplify(-(yy0 + 2 * ly0 * lam1 + ll0 * lam1**2) / A)  # d^2 lam / d y^2 at y=1

    mean = sp.simplify((y0 * lam1) / lam0)  # psi'(0)
    var = sp.simplify(lam1 / lam0 + lam2 / lam0 - (lam1 / lam0) ** 2)  # psi''(0)

    mean_ok = sp.simplify(mean - sp.Rational(5, 18)) == 0
    var_ok = sp.simplify(var - sp.Rational(67, 972)) == 0

    # Self-inversive spot check at primitive cube root y = exp(2pi i/3)
    omega = complex(-0.5, math.sqrt(3) / 2.0)
    coeffs = [
        complex(sp.N(sp.Integer(1))),  # lam^4
        complex(sp.N(sp.Integer(-1))),  # lam^3
        complex(sp.N(-(2 * omega + 1))),  # lam^2
        complex(sp.N(sp.Integer(1))),  # lam^1
        complex(sp.N(omega * (omega + 1))),  # lam^0
    ]
    # Find c from a3 = c * conj(a1).
    c = coeffs[1] / coeffs[3].conjugate()
    self_inv_ok = abs(abs(c) - 1.0) < 1e-12
    for k in range(5):
        if abs(coeffs[k] - c * coeffs[4 - k].conjugate()) > 1e-10:
            self_inv_ok = False
            break

    payload: Dict[str, object] = {
        "meta": {
            "script": Path(__file__).name,
            "generated_at_unix_s": float(time.time()),
            "seconds": float(time.time() - t0),
        },
        "params": {"m_max": int(args.m_max)},
        "checks": {
            "recurrence_order4_polynomial_ok": rec_ok,
            "recurrence_order4_fail_head": rec_fail[:5],
            "generating_function_series_ok": gen_ok,
            "generating_function_fail_head": gen_fail[:5],
            "recurrence_2d_amk_ok": rec2_ok,
            "recurrence_2d_fail_head": rec2_fail[:5],
            "discriminant_factorization_ok": bool(disc_ok),
            "mean_ok_5_over_18": bool(mean_ok),
            "var_ok_67_over_972": bool(var_ok),
            "self_inversive_check_at_omega_ok": bool(self_inv_ok),
        },
        "polynomials": {
            "Pi_lambda_y": str(Pi),
            "Disc_lambda_factor": str(disc),
            "Disc_lambda_expected": str(disc_expected),
            "cubic_branch_factor": str(cubic),
        },
        "numeric": {
            "y_LY_real_root": None if y_ly is None else float(y_ly),
            "mean": {"exact": str(mean), "float": float(sp.N(mean))},
            "var": {"exact": str(var), "float": float(sp.N(var))},
        },
        "Z_m_coeffs_a_mk_head": [
            {"m": m, "a_mk": a_mk[m][: (m + 1)]} for m in range(min(args.m_max, 8) + 1)
        ],
    }

    if not args.no_output:
        out_json = export_dir() / "fold_zm_bivariate_partition_audit.json"
        _write_json(out_json, payload)

        # Minimal TeX snippet (optional in the paper).
        tex = "\n".join(
            [
                "% Auto-generated by scripts/exp_fold_zm_bivariate_partition_audit.py",
                "\\[",
                "\\Pi(\\lambda,y)=\\lambda^{4}-\\lambda^{3}-(2y+1)\\lambda^{2}+\\lambda+y(y+1).",
                "\\]",
                "\\[",
                "\\mathrm{Disc}_{\\lambda}(\\Pi)=-y\\,(y-1)\\,(256y^{3}+411y^{2}+165y+32).",
                "\\]",
                f"\\[y_{{\\mathrm{{LY}}}}\\approx {y_ly:.10f}.\\]" if y_ly is not None else "% y_LY not found",
                "\\[",
                "\\psi'(0)=\\frac{5}{18},\\qquad \\psi''(0)=\\frac{67}{972}.",
                "\\]",
                "",
            ]
        )
        out_tex = generated_dir() / "eq_fold_zm_bivariate_partition_audit.tex"
        _write_text(out_tex, tex)

        print(f"[fold-zm-audit] wrote {out_json}", flush=True)
        print(f"[fold-zm-audit] wrote {out_tex}", flush=True)

    print(
        f"[fold-zm-audit] checks: rec={rec_ok} gen={gen_ok} disc={disc_ok} mean_ok={mean_ok} var_ok={var_ok} y_LY={y_ly}",
        flush=True,
    )
    print("[fold-zm-audit] done", flush=True)


if __name__ == "__main__":
    main()

