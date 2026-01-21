# -*- coding: utf-8 -*-
"""
End-to-end curvature bridge demo (deterministic).

Pipeline (protocolized, self-contained):
  protocolized spatial input (synthetic scalar field on a 2D grid)
    -> thresholded window words on Hilbert index axis
    -> Fold_m degeneracy proxy g_m(N)
    -> chi reconstruction chi_hat(x) = log(gbar/g0)
    -> weak-field curvature proxy via Laplacian:
         G00_hat := -2 * gamma_hat * Δ_h chi_hat
    -> auditable error budget:
         |Δ_h chi_hat - Δ chi_true| <= C h^2 + (4d/h^2) * eps_chi

Design constraints:
  - Deterministic output (fixed RNG seeds; no timestamps).
  - Standard-library only.
  - Lightweight runtime for run_all.py.

Outputs (LaTeX fragments):
  - sections/generated/curvature_e2e_rows.tex
  - sections/generated/curvature_e2e_summary.tex
  - sections/generated/curvature_e2e_gamma_rows.tex
  - sections/generated/curvature_e2e_gamma_summary.tex
  - sections/generated/curvature_e2e_gamma_stability_rows.tex
  - sections/generated/curvature_e2e_gamma_stability_summary.tex
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import exp_hilbert_chirality_index as hil
import protocol_kernel as foldm
from common_paths import generated_dir
from common_tex import write_lines


def _ensuremath_sci(x: float, sig: int = 3) -> str:
    if x == 0.0:
        return r"\ensuremath{0}"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = x / (10**exp)
    fmt = f"{{:.{max(sig - 1, 0)}f}}"
    mant_s = fmt.format(mant)
    if exp == 0:
        return r"\ensuremath{" + mant_s + "}"
    return r"\ensuremath{" + mant_s + r"\times 10^{" + str(exp) + "}" + "}"


def _binary_word_int(bits: List[int]) -> int:
    out = 0
    for b in bits:
        out = (out << 1) | (1 if b else 0)
    return out


def _mean(xs: List[float]) -> float:
    if not xs:
        raise ValueError("mean requires non-empty list")
    return sum(xs) / float(len(xs))


def _median(xs: List[float]) -> float:
    if not xs:
        raise ValueError("median requires non-empty list")
    ys = sorted(xs)
    n = len(ys)
    if n % 2 == 1:
        return float(ys[n // 2])
    return 0.5 * float(ys[n // 2 - 1] + ys[n // 2])


def _periodic_laplacian(grid: List[List[float]], h: float) -> List[List[float]]:
    side = len(grid)
    out = [[0.0 for _ in range(side)] for _ in range(side)]
    inv_h2 = 1.0 / (h * h)
    for y in range(side):
        ym = (y - 1) % side
        yp = (y + 1) % side
        row = grid[y]
        row_ym = grid[ym]
        row_yp = grid[yp]
        for x in range(side):
            xm = (x - 1) % side
            xp = (x + 1) % side
            out[y][x] = (
                row[xp] + row[xm] + row_yp[x] + row_ym[x] - 4.0 * row[x]
            ) * inv_h2
    return out


def _max_abs_grid(grid: List[List[float]]) -> float:
    m = 0.0
    for row in grid:
        for v in row:
            av = abs(v)
            if av > m:
                m = av
    return m


def _max_abs_diff(a: List[List[float]], b: List[List[float]]) -> float:
    side = len(a)
    m = 0.0
    for y in range(side):
        for x in range(side):
            d = abs(a[y][x] - b[y][x])
            if d > m:
                m = d
    return m


@dataclass(frozen=True)
class E2ERow:
    n: int
    side: int
    h: float
    m: int
    amp: float
    sigma_delta: float
    eps_chi: float
    lap_err: float
    trunc_bound: float
    noise_bound: float
    total_bound: float
    ratio: float


@dataclass(frozen=True)
class GammaFitRow:
    n: int
    m: int
    amp0: float
    slope: float
    sigma_delta: float
    gamma_true: float
    sigma_v: float
    gamma_hat: float
    sigma_gamma: float
    chi2_red: float
    n_used: int
    rel_err: float


@dataclass(frozen=True)
class GammaStabilityRow:
    n: int
    side: int
    m: int
    family_size: int
    gamma_min: float
    gamma_max: float
    gamma_mean: float
    gamma_std: float
    max_z: float


def _build_chi_true(*, side: int, amp: float) -> List[List[float]]:
    chi = [[0.0 for _ in range(side)] for _ in range(side)]
    for y in range(side):
        yy = y / float(side)
        sy = math.sin(2.0 * math.pi * yy)
        for x in range(side):
            xx = x / float(side)
            sx = math.sin(2.0 * math.pi * xx)
            chi[y][x] = amp * sx * sy
    return chi


def _build_bits_from_delta(
    *,
    n_bits: int,
    chi_true: List[List[float]],
    sigma_delta: float,
    seed: int,
) -> List[int]:
    path = hil.hilbert_curve(n_bits)
    side = 1 << n_bits
    if len(path) != side * side:
        raise AssertionError("Unexpected Hilbert path length.")
    rng = random.Random(seed)
    bits: List[int] = []
    for (x, y) in path:
        # Protocolized scalar statistic per cell (delta) with bounded-noise intention.
        delta = chi_true[y][x] + rng.gauss(0.0, sigma_delta)
        bits.append(1 if delta >= 0.0 else 0)
    return bits


def _threshold(values: List[float], rule: str) -> float:
    if rule == "zero":
        return 0.0
    if rule == "mean":
        return _mean(values)
    if rule == "median":
        return _median(values)
    raise ValueError(f"Unknown threshold_rule: {rule}")


def _baseline(values: List[float], rule: str) -> float:
    if rule == "mean":
        return _mean(values)
    if rule == "median":
        return _median(values)
    raise ValueError(f"Unknown baseline_rule: {rule}")


def _reconstruct_chi_from_bits(*, bits: List[int], m: int) -> List[float]:
    # g_m(N) via Fold_m and cached degeneracy map gm[w]=|preimage|.
    gm_map = foldm.cached_degeneracy_map(m)

    def g_of_int(N: int) -> int:
        w = foldm.fold_m(int(N), m)
        return int(gm_map[w])

    N = len(bits)
    # Word indices for each start s (circular on the index axis).
    g_s: List[float] = []
    for s in range(N):
        word = [bits[(s + j) % N] for j in range(m)]
        Ns = _binary_word_int(word)
        g_s.append(float(g_of_int(Ns)))

    # Window-local mean degeneracy proxy: average g_s over length-m arcs (circular).
    gbar: List[float] = []
    for s in range(N):
        acc = 0.0
        for j in range(m):
            acc += g_s[(s + j) % N]
        gbar.append(acc / float(m))

    g0 = _mean(gbar)
    if not (g0 > 0.0):
        raise AssertionError("Baseline g0 must be positive.")

    return [math.log(x / g0) for x in gbar]


def _chi_index_to_grid(*, n_bits: int, chi_idx: List[float]) -> List[List[float]]:
    side = 1 << n_bits
    path = hil.hilbert_curve(n_bits)
    if len(chi_idx) != len(path):
        raise ValueError("chi_idx length must equal number of Hilbert sites.")
    grid = [[0.0 for _ in range(side)] for _ in range(side)]
    for k, (x, y) in enumerate(path):
        grid[y][x] = float(chi_idx[k])
    return grid


def _wls_gamma_fit(
    *,
    x: List[float],
    y: List[float],
    sy: List[float],
) -> tuple[float, float, float, int]:
    # gamma_hat = sum(w x y)/sum(w x^2), w=1/sy^2
    if not (len(x) == len(y) == len(sy)):
        raise ValueError("x, y, sy must have same length.")
    num = 0.0
    denom = 0.0
    used: List[int] = []
    for i in range(len(x)):
        if not (math.isfinite(x[i]) and math.isfinite(y[i]) and math.isfinite(sy[i])):
            continue
        if sy[i] <= 0.0:
            continue
        if x[i] <= 0.0:
            continue
        w = 1.0 / (sy[i] * sy[i])
        num += w * x[i] * y[i]
        denom += w * x[i] * x[i]
        used.append(i)
    n_used = len(used)
    if denom <= 0.0 or n_used < 3:
        return float("nan"), float("nan"), float("nan"), n_used
    gamma_hat = num / denom
    sigma_ideal = math.sqrt(1.0 / denom)
    # reduced chi^2
    chi2 = 0.0
    for i in used:
        r = y[i] - gamma_hat * x[i]
        chi2 += (r / sy[i]) ** 2
    dof = max(1, n_used - 1)
    chi2_red = chi2 / float(dof)
    sigma = math.sqrt(max(0.0, chi2_red)) * sigma_ideal
    return float(gamma_hat), float(sigma), float(chi2_red), n_used


def _run_gamma_fit_row(*, n_bits: int, m: int) -> GammaFitRow:
    # Synthetic 1D "rotation curve" channel with protocolized chi reconstruction.
    # We use the Hilbert index axis k=0..4^n-1 as the ordered sample axis (protocol order),
    # and define a monotone chi_model(k) used to generate both:
    #   - a noisy scalar delta(k) -> bits -> chi_hat(k) reconstruction, and
    #   - a reference v(k) via v^2 = gamma_true * x_true, x_true := -c^2 r dchi_model/dr.
    side = 1 << n_bits
    N = side * side

    amp0 = 0.30
    slope = 0.004
    sigma_delta = 0.05

    gamma_true = 1e-6
    c_km_s = 299792.458
    sigma_v = 5.0

    rng = random.Random(2000 + n_bits)

    r: List[float] = [float(i + 1) for i in range(N)]
    chi_model: List[float] = [amp0 - slope * rr for rr in r]

    bits: List[int] = []
    for i in range(N):
        delta = chi_model[i] + rng.gauss(0.0, sigma_delta)
        bits.append(1 if delta >= 0.0 else 0)

    chi_hat = _reconstruct_chi_from_bits(bits=bits, m=m)

    # dchi_model/dr is constant = -slope; hence x_true is strictly positive.
    x_true: List[float] = [(c_km_s * c_km_s) * slope * rr for rr in r]
    y_true: List[float] = [gamma_true * xx for xx in x_true]

    v: List[float] = []
    sv: List[float] = []
    for i in range(N):
        vi = math.sqrt(max(0.0, y_true[i])) + rng.gauss(0.0, sigma_v)
        v.append(vi)
        sv.append(sigma_v)

    y: List[float] = [vi * vi for vi in v]
    sy: List[float] = []
    for i in range(N):
        sy.append(max(1e-12, 2.0 * abs(v[i]) * max(1e-12, sv[i])))

    # Use reconstructed chi_hat for the design x_hat = -c^2 r dchi_hat/dr (central difference).
    dchi_hat: List[float] = [0.0 for _ in range(N)]
    for i in range(1, N - 1):
        dchi_hat[i] = (chi_hat[i + 1] - chi_hat[i - 1]) / (r[i + 1] - r[i - 1])
    dchi_hat[0] = dchi_hat[1]
    dchi_hat[N - 1] = dchi_hat[N - 2]

    x_hat: List[float] = [-(c_km_s * c_km_s) * r[i] * dchi_hat[i] for i in range(N)]

    gamma_hat, sigma_gamma, chi2_red, n_used = _wls_gamma_fit(x=x_hat, y=y, sy=sy)
    rel_err = abs(gamma_hat - gamma_true) / gamma_true if gamma_true > 0.0 and math.isfinite(gamma_hat) else float("nan")

    return GammaFitRow(
        n=n_bits,
        m=m,
        amp0=amp0,
        slope=slope,
        sigma_delta=sigma_delta,
        gamma_true=gamma_true,
        sigma_v=sigma_v,
        gamma_hat=gamma_hat,
        sigma_gamma=sigma_gamma,
        chi2_red=chi2_red,
        n_used=n_used,
        rel_err=rel_err,
    )


def _moving_average(x: List[float], k: int) -> List[float]:
    if k <= 0 or k % 2 == 0:
        raise ValueError("k must be positive odd")
    if k == 1:
        return list(x)
    n = len(x)
    r = k // 2
    out = [0.0 for _ in range(n)]
    for i in range(n):
        acc = 0.0
        cnt = 0
        for j in range(i - r, i + r + 1):
            jj = 0 if j < 0 else (n - 1 if j >= n else j)
            acc += x[jj]
            cnt += 1
        out[i] = acc / float(cnt)
    return out


def _run_gamma_stability_row(*, n_bits: int, m: int) -> GammaStabilityRow:
    side = 1 << n_bits
    N = side * side

    amp0 = 0.30
    slope = 0.004
    sigma_delta = 0.05

    gamma_true = 1e-6
    c_km_s = 299792.458
    sigma_v = 5.0

    rng = random.Random(3000 + n_bits)

    r: List[float] = [float(i + 1) for i in range(N)]
    chi_model: List[float] = [amp0 - slope * rr for rr in r]
    delta: List[float] = [chi_model[i] + rng.gauss(0.0, sigma_delta) for i in range(N)]

    # Synthetic velocities from the *reference* model.
    x_true: List[float] = [(c_km_s * c_km_s) * slope * rr for rr in r]
    y_true: List[float] = [gamma_true * xx for xx in x_true]
    v: List[float] = [math.sqrt(max(0.0, y_true[i])) + rng.gauss(0.0, sigma_v) for i in range(N)]
    sv: List[float] = [sigma_v for _ in range(N)]

    y: List[float] = [vi * vi for vi in v]
    sy: List[float] = [max(1e-12, 2.0 * abs(v[i]) * max(1e-12, sv[i])) for i in range(N)]

    threshold_rules = ["zero", "mean", "median"]
    baseline_rules = ["mean", "median"]
    smooth_ks = [1, 5, 11]

    gammas: List[float] = []
    for thr in threshold_rules:
        tau = _threshold(delta, thr)
        bits = [1 if d >= tau else 0 for d in delta]
        for base in baseline_rules:
            # Reconstruct chi with a configurable baseline on gbar.
            chi_hat = _reconstruct_chi_from_bits(bits=bits, m=m)
            # Override baseline by re-centering chi_hat with a new g0 proxy.
            # (This stays in the same audit family but keeps the implementation simple.)
            if base != "mean":
                # Translate: chi = log(gbar/g0). Changing g0 adds a constant shift.
                # We emulate a baseline change by shifting chi so that median(chi)=0.
                if base == "median":
                    shift = _median(chi_hat)
                    chi_hat = [c - shift for c in chi_hat]
                else:
                    raise ValueError("unexpected baseline rule")
            for k in smooth_ks:
                chi_s = _moving_average(chi_hat, k)
                dchi: List[float] = [0.0 for _ in range(N)]
                for i in range(1, N - 1):
                    dchi[i] = (chi_s[i + 1] - chi_s[i - 1]) / (r[i + 1] - r[i - 1])
                dchi[0] = dchi[1]
                dchi[N - 1] = dchi[N - 2]
                x_hat = [-(c_km_s * c_km_s) * r[i] * dchi[i] for i in range(N)]
                ghat, _, _, n_used = _wls_gamma_fit(x=x_hat, y=y, sy=sy)
                if math.isfinite(ghat) and n_used >= 3:
                    gammas.append(float(ghat))

    if not gammas:
        return GammaStabilityRow(
            n=n_bits,
            side=side,
            m=m,
            family_size=0,
            gamma_min=float("nan"),
            gamma_max=float("nan"),
            gamma_mean=float("nan"),
            gamma_std=float("nan"),
            max_z=float("nan"),
        )

    gmin = min(gammas)
    gmax = max(gammas)
    gmu = _mean(gammas)
    var = _mean([(g - gmu) ** 2 for g in gammas])
    gstd = math.sqrt(max(0.0, var))

    max_z = 0.0
    if gstd > 0.0:
        max_z = (gmax - gmin) / gstd

    return GammaStabilityRow(
        n=n_bits,
        side=side,
        m=m,
        family_size=len(gammas),
        gamma_min=gmin,
        gamma_max=gmax,
        gamma_mean=gmu,
        gamma_std=gstd,
        max_z=float(max_z),
    )


def _run_e2e_rows() -> List[E2ERow]:
    rows: List[E2ERow] = []
    m = 6
    gamma_hat = 1.0  # audit-only normalization (G00 scaling cancels in ratio).
    _ = gamma_hat
    d = 2

    # Smooth synthetic overhead proxy (true field) amplitude.
    amp = 0.25
    sigma_delta = 0.10

    for n_bits in [3, 4, 5, 6, 7]:
        side = 1 << n_bits
        h = 1.0 / float(side)

        chi_true = _build_chi_true(side=side, amp=amp)

        bits = _build_bits_from_delta(
            n_bits=n_bits, chi_true=chi_true, sigma_delta=sigma_delta, seed=1000 + n_bits
        )
        chi_idx = _reconstruct_chi_from_bits(bits=bits, m=m)
        chi_hat = _chi_index_to_grid(n_bits=n_bits, chi_idx=chi_idx)

        # Analytic continuum Laplacian of chi_true: Δchi = -8π^2 chi
        lap_true = [[-8.0 * (math.pi**2) * chi_true[y][x] for x in range(side)] for y in range(side)]
        lap_hat = _periodic_laplacian(chi_hat, h=h)

        # Realized pointwise chi deviation as an auditable eps_chi.
        eps_chi = _max_abs_diff(chi_hat, chi_true)

        # Laplacian error and the audit bound (Appendix 33 style).
        lap_err = _max_abs_diff(lap_hat, lap_true)

        # Truncation constant for chi_true:
        # C = (1/12) * sum_k sup |∂_k^4 chi| = amp * (2π)^4 / 6 for sin(2πx)sin(2πy).
        c_trunc = amp * (2.0 * math.pi) ** 4 / 6.0
        trunc_bound = c_trunc * (h * h)
        noise_bound = (4.0 * d / (h * h)) * eps_chi
        total = trunc_bound + noise_bound
        ratio = (lap_err / total) if total > 0.0 else 0.0

        rows.append(
            E2ERow(
                n=n_bits,
                side=side,
                h=h,
                m=m,
                amp=amp,
                sigma_delta=sigma_delta,
                eps_chi=eps_chi,
                lap_err=lap_err,
                trunc_bound=trunc_bound,
                noise_bound=noise_bound,
                total_bound=total,
                ratio=ratio,
            )
        )

    return rows


def _write_outputs(
    rows: Iterable[E2ERow],
    gamma_rows: Iterable[GammaFitRow],
    gamma_stability_rows: Iterable[GammaStabilityRow],
) -> None:
    out_rows = generated_dir() / "curvature_e2e_rows.tex"
    out_summary = generated_dir() / "curvature_e2e_summary.tex"
    out_g_rows = generated_dir() / "curvature_e2e_gamma_rows.tex"
    out_g_summary = generated_dir() / "curvature_e2e_gamma_summary.tex"
    out_gs_rows = generated_dir() / "curvature_e2e_gamma_stability_rows.tex"
    out_gs_summary = generated_dir() / "curvature_e2e_gamma_stability_summary.tex"

    lines: List[str] = []
    for r in rows:
        lines.append(
            " & ".join(
                [
                    str(r.n),
                    str(r.side),
                    _ensuremath_sci(r.h),
                    str(r.m),
                    _ensuremath_sci(r.amp),
                    _ensuremath_sci(r.sigma_delta),
                    _ensuremath_sci(r.eps_chi),
                    _ensuremath_sci(r.lap_err),
                    _ensuremath_sci(r.trunc_bound),
                    _ensuremath_sci(r.noise_bound),
                    _ensuremath_sci(r.total_bound),
                    _ensuremath_sci(r.ratio),
                ]
            )
            + r" \\"
        )
    write_lines(out_rows, lines)

    summary_lines = [
        r"\noindent\AuditTag End-to-end curvature bridge demo: synthetic protocolized scalar input on a $2^n\times 2^n$ grid is ordered by Hilbert addressing, thresholded to window words at $m=6$, mapped to $g_6(N)$ via Fold$_6$, and reconstructed into $\widehat\chi(x)=\log(\bar g/g_0)$. "
        r"We then form the weak-field curvature proxy $\widehat G_{00,h}:=-2\widehat\gamma\,\Delta_h\widehat\chi_h$ (Appendix~\ref{app:weak_field_curvature_from_chi}) and audit the Laplacian-stage error budget in the Appendix~\ref{app:protocol_to_continuum_error_control} form: truncation $C h^2$ plus noise amplification $(4d/h^2)\epsilon_\chi$ (with $d=2$). "
        r"\texttt{protocol\_state}: this demo uses the balanced Hilbert screen ($n$), window length $m=6$, and the implicit readout kernel induced by the deterministic reconstruction rule (uniform averaging in the window-level aggregator).",
    ]
    write_lines(out_summary, summary_lines)

    g_lines: List[str] = []
    for gr in gamma_rows:
        g_lines.append(
            " & ".join(
                [
                    str(gr.n),
                    str(1 << gr.n),
                    str(gr.m),
                    _ensuremath_sci(gr.amp0),
                    _ensuremath_sci(gr.slope),
                    _ensuremath_sci(gr.sigma_delta),
                    _ensuremath_sci(gr.gamma_true),
                    _ensuremath_sci(gr.sigma_v),
                    _ensuremath_sci(gr.gamma_hat),
                    _ensuremath_sci(gr.sigma_gamma),
                    _ensuremath_sci(gr.chi2_red),
                    str(gr.n_used),
                    _ensuremath_sci(gr.rel_err),
                ]
            )
            + r" \\"
        )
    write_lines(out_g_rows, g_lines)

    g_summary_lines = [
        r"\noindent\AuditTag End-to-end $\widehat\gamma$ fit demo: from the same protocolized reconstruction pipeline we build the design $x_i=-c^2 r_i \widehat\chi'(r_i)$ and fit $\widehat\gamma$ by WLS on $v_i^2=\gamma x_i$ (Appendix~\ref{app:protocol_to_continuum_error_control} variance proxy, with $\chi^2_{\rm red}$ inflation). "
        r"The synthetic $v_i$ are generated from a monotone reference $\chi_{\rm model}(r)$ so that $x_i>0$ points exist; the fit uses the reconstructed $\widehat\chi$ (not $\chi_{\rm model}$), hence the reported $\chi^2_{\rm red}$ captures model-mismatch and reconstruction noise in an auditable way.",
    ]
    write_lines(out_g_summary, g_summary_lines)

    gs_lines: List[str] = []
    for r in gamma_stability_rows:
        gs_lines.append(
            " & ".join(
                [
                    str(r.n),
                    str(r.side),
                    str(r.m),
                    str(r.family_size),
                    _ensuremath_sci(r.gamma_min),
                    _ensuremath_sci(r.gamma_max),
                    _ensuremath_sci(r.gamma_mean),
                    _ensuremath_sci(r.gamma_std),
                    _ensuremath_sci(r.max_z),
                ]
            )
            + r" \\"
        )
    write_lines(out_gs_rows, gs_lines)

    gs_summary_lines = [
        r"\noindent\AuditTag $\widehat\gamma$ stability sweep (bounded counterfactual family): we vary the threshold rule for the protocolized scalar statistic (zero/mean/median), the baseline convention (mean vs median recentering), and a small set of odd smoothing windows for $\widehat\chi$. "
        r"For each configuration we refit $\widehat\gamma$ by WLS and summarize the resulting family by min/max/mean/std and a simple spread score $(\max-\min)/\mathrm{std}$.",
    ]
    write_lines(out_gs_summary, gs_summary_lines)


def main() -> None:
    rows = _run_e2e_rows()
    gamma_rows = [_run_gamma_fit_row(n_bits=n, m=6) for n in [3, 4, 5]]
    gamma_stab = [_run_gamma_stability_row(n_bits=n, m=6) for n in [3, 4, 5]]
    _write_outputs(rows, gamma_rows, gamma_stab)


if __name__ == "__main__":
    main()

