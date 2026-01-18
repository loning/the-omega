# -*- coding: utf-8 -*-
"""
QG interface suite (deterministic, audit-facing).

This script does NOT claim to solve quantum gravity as a full nonperturbative theory.
It provides a reproducible end-to-end *interface* demo that composes three already
closed bridge modules in the paper:

  (1) overhead proxy field chi(x) -> weak-field curvature proxy:
        G00_hat(x) := -2 * gamma * Δ_h chi(x)
      (Appendix: weak-field curvature from chi)

  (2) budget-triggered protocol horizon: select a cloud region R_* whose capacity
      exceeds an observer budget:
        I_chi = m * |R_*| >= c * I_obs
      (Appendix: protocol horizon / tick-trap viewpoint)

  (3) scattering phase/delay as an operational time dictionary:
        tau(omega) = d delta / d omega  (Breit–Wigner one-channel benchmark)
      and lapse proxy mapping via chi_ws = log(kappa/kappa0), N = exp(-gamma * chi_ws)
      (Appendix: time and mass as delay)

Outputs (LaTeX fragments):
  - sections/generated/qg_interface_suite_rows.tex
  - sections/generated/qg_interface_suite_summary.tex

Optional figure (requires matplotlib):
  - figures/qg_interface_suite.png

Design constraints:
  - Deterministic output (no timestamps; deterministic tie-breaks).
  - Python-only, English-only outputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from common_constants import M_E_GEV, PHI
from common_paths import figures_dir, generated_dir
from common_tex import write_lines

import exp_curvature_bridge_end_to_end as e2e


def _ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("b must be positive")
    return (a + b - 1) // b


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _fmt_sci(x: float, sig: int = 3) -> str:
    # LaTeX-friendly scientific formatting.
    if x == 0.0:
        return r"\ensuremath{0}"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = x / (10**exp)
    digits = max(int(sig) - 1, 0)
    mant_s = f"{mant:.{digits}f}"
    if exp == 0:
        return r"\ensuremath{" + mant_s + "}"
    return r"\ensuremath{" + mant_s + r"\times 10^{" + str(exp) + "}" + "}"


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


def _max_abs_on_region(grid: List[List[float]], region: set[int]) -> float:
    side = len(grid)
    m = 0.0
    for idx in region:
        y = idx // side
        x = idx % side
        v = grid[y][x]
        av = abs(v)
        if av > m:
            m = av
    return m


def _region_perimeter_edges(*, side: int, region: set[int]) -> int:
    # Count directed boundary edges (site in region, neighbor out of region) on 4-neighborhood.
    perim = 0
    for idx in region:
        y = idx // side
        x = idx % side
        for (nx, ny) in (
            ((x + 1) % side, y),
            ((x - 1) % side, y),
            (x, (y + 1) % side),
            (x, (y - 1) % side),
        ):
            nidx = ny * side + nx
            if nidx not in region:
                perim += 1
    return perim


def _build_chi_field(*, side: int, amp: float) -> List[List[float]]:
    # Smooth periodic toy field; deterministic.
    chi = [[0.0 for _ in range(side)] for _ in range(side)]
    for y in range(side):
        yy = y / float(side)
        sy = math.sin(2.0 * math.pi * yy)
        for x in range(side):
            xx = x / float(side)
            sx = math.sin(2.0 * math.pi * xx)
            chi[y][x] = float(amp) * sx * sy
    return chi


def _select_top_k_region(grid: List[List[float]], k: int) -> Tuple[set[int], float]:
    side = len(grid)
    total = side * side
    kk = max(0, min(int(k), int(total)))
    flat: List[Tuple[float, int]] = []
    for y in range(side):
        row = grid[y]
        for x in range(side):
            idx = y * side + x
            flat.append((float(row[x]), int(idx)))
    # Deterministic tie-break: sort by value desc, then idx asc.
    flat.sort(key=lambda t: (-t[0], t[1]))
    chosen = flat[:kk]
    region = {idx for (_v, idx) in chosen}
    chi_star = chosen[-1][0] if chosen else float("inf")
    return region, float(chi_star)


def _breit_wigner_delay(*, omega: float, omega0: float, gamma: float) -> float:
    # One-channel unitary benchmark: tau(omega) = d delta / d omega.
    return float(gamma) / ((omega - omega0) ** 2 + (float(gamma) / 2.0) ** 2)


def _mu_threshold_gev(*, m: int, r_step: float = 2.0 * math.pi) -> float:
    # Calibration in V_40: r_th(m)=(m-6)*r_step, mu_th=m_e * phi^{r_th}.
    r_th = (int(m) - 6) * float(r_step)
    return float(M_E_GEV) * (float(PHI) ** float(r_th))


@dataclass(frozen=True)
class SuiteRow:
    m: int
    n: int
    sites: int
    i_obs: int
    c: int
    required_sites: int
    required_sites_capped: int
    feasible: str
    frac: float
    chi_star: float
    perim_edges: int
    g00_max_all: float
    g00_max_region: float
    mu_th_gev: float
    tau_peak: float
    lapse_peak: float
    lapse_far: float


def _build_rows() -> List[SuiteRow]:
    # Deterministic family: even steps aligned with 2D balanced coupling.
    mn: Sequence[Tuple[int, int]] = [(6, 3), (8, 4), (10, 5)]
    # Small, auditable budget/margin family (some feasible, some infeasible).
    budgets: Sequence[int] = [64, 1024, 1_000_000]
    margins: Sequence[int] = [1, 4, 16]
    amp = 1.0
    h = 1.0
    gamma = 1.0
    sigma_delta = 0.25
    seed = 0

    # Scattering benchmark parameters.
    omega0 = 0.0
    gamma_bw = 1.0
    omega_far = 6.0

    tau_peak = _breit_wigner_delay(omega=omega0, omega0=omega0, gamma=gamma_bw)
    tau_far = _breit_wigner_delay(omega=omega_far, omega0=omega0, gamma=gamma_bw)
    tau0 = tau_far
    kappa0 = 1.0

    # Delay->chi_ws->lapse map (gamma from the gravity dictionary).
    def lapse_from_tau(tau: float) -> float:
        kappa = float(tau) / float(tau0)
        chi_ws = math.log(kappa / float(kappa0))
        return math.exp(-float(gamma) * float(chi_ws))

    lapse_peak = lapse_from_tau(tau_peak)
    lapse_far = lapse_from_tau(tau_far)

    rows: List[SuiteRow] = []
    for (m, n) in mn:
        side = 1 << int(n)
        sites = side * side

        # Build a chi field via the paper's curvature-bridge E2E reconstruction pipeline:
        # chi_true -> noisy delta -> bits -> chi_hat (index-axis) -> chi_hat grid.
        chi_true = e2e._build_chi_true(side=side, amp=float(amp))
        bits = e2e._build_bits_from_delta(
            n_bits=int(n),
            chi_true=chi_true,
            sigma_delta=float(sigma_delta),
            seed=int(seed + 17 * int(m) + 31 * int(n)),
        )
        chi_idx = e2e._reconstruct_chi_from_bits(bits=bits, m=int(m))
        chi = e2e._chi_index_to_grid(n_bits=int(n), chi_idx=chi_idx)

        lap = _periodic_laplacian(chi, h=h)
        g00 = [[-2.0 * float(gamma) * v for v in row] for row in lap]
        g00_max_all = _max_abs_grid(g00)

        for i_obs in budgets:
            for c in margins:
                required = _ceil_div(int(c) * int(i_obs), int(m))
                required_capped = min(required, sites)
                feasible = "yes" if required <= sites else "no"
                frac = float(required_capped) / float(sites)

                region, chi_star = _select_top_k_region(chi, required_capped)
                perim = _region_perimeter_edges(side=side, region=region)
                g00_max_region = _max_abs_on_region(g00, region) if region else 0.0

                rows.append(
                    SuiteRow(
                        m=int(m),
                        n=int(n),
                        sites=int(sites),
                        i_obs=int(i_obs),
                        c=int(c),
                        required_sites=int(required),
                        required_sites_capped=int(required_capped),
                        feasible=str(feasible),
                        frac=float(frac),
                        chi_star=float(chi_star),
                        perim_edges=int(perim),
                        g00_max_all=float(g00_max_all),
                        g00_max_region=float(g00_max_region),
                        mu_th_gev=float(_mu_threshold_gev(m=int(m))),
                        tau_peak=float(tau_peak),
                        lapse_peak=float(lapse_peak),
                        lapse_far=float(lapse_far),
                    )
                )
    return rows


def _write_rows(rows: Sequence[SuiteRow]) -> None:
    lines: List[str] = []
    for r in rows:
        lines.append(
            " & ".join(
                [
                    str(r.m),
                    str(r.n),
                    str(r.sites),
                    str(r.i_obs),
                    str(r.c),
                    str(r.required_sites),
                    str(r.required_sites_capped),
                    str(r.feasible),
                    _fmt(r.frac, 6),
                    _fmt(r.chi_star, 6),
                    str(r.perim_edges),
                    _fmt_sci(r.g00_max_all, 3),
                    _fmt_sci(r.g00_max_region, 3),
                    _fmt_sci(r.mu_th_gev, 3),
                    _fmt(r.tau_peak, 6),
                    _fmt(r.lapse_peak, 6),
                    _fmt(r.lapse_far, 6),
                ]
            )
            + r" \\"
        )
    write_lines(
        generated_dir() / "qg_interface_suite_rows.tex",
        lines if lines else ["% (no rows)"],
    )


def _write_summary(rows: Sequence[SuiteRow]) -> None:
    ms = ", ".join(str(x) for x in sorted({r.m for r in rows}))
    ns = ", ".join(str(x) for x in sorted({r.n for r in rows}))
    lines = [
        r"\paragraph{Audit summary (QG interface suite).} \AuditTag "
        r"This suite composes three interface bridges in a deterministic toy setting: "
        r"(i) a protocol overhead proxy field $\chi(x)$ reconstructed by the paper's "
        r"end-to-end curvature-bridge pipeline (noisy $\delta$ readout $\to$ bits $\to$ folding fibers $\to \hat\chi$), "
        r"(ii) a budget-triggered cloud selection rule $m|\mathcal R_\star|\ge c\,I_{\mathrm{obs}}$ "
        r"(capacity-only horizon trigger) and the induced boundary-perimeter diagnostic on the grid, "
        r"and (iii) a one-channel Breit--Wigner scattering delay benchmark used to define a lapse proxy "
        r"via $\chi_{\mathrm{WS}}=\log(\kappa/\kappa_0)$ and $N=\exp(-\gamma\chi_{\mathrm{WS}})$. "
        r"The curvature proxy is the weak-field bridge $G_{00}\approx -2\gamma\,\Delta\chi$ "
        r"evaluated with a periodic central-difference Laplacian at grid spacing $h=1$. "
        rf"Rows cover the balanced even-step family $(m,n)\in\{{({ms})\}}\times\{{({ns})\}}$ "
        r"and a bounded family of budgets/margins $(I_{\mathrm{obs}},c)\in\{64,1024,10^6\}\times\{1,4,16\}$ "
        r"with fixed $\gamma=1$ and a deterministic top-$k$ selection tie-break on $\hat\chi$.",
    ]
    write_lines(generated_dir() / "qg_interface_suite_summary.tex", lines)


def _plot_optional(rows: Sequence[SuiteRow]) -> None:
    # One illustrative figure for the first row.
    if not rows:
        return
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    # Pick a feasible small case to visualize if possible.
    r0 = None
    for r in rows:
        if r.feasible == "yes" and r.required_sites_capped < r.sites:
            r0 = r
            break
    if r0 is None:
        r0 = rows[0]

    side = 1 << int(r0.n)
    # Recompute chi via the same reconstruction pipeline (deterministic).
    chi_true = e2e._build_chi_true(side=side, amp=1.0)
    bits = e2e._build_bits_from_delta(
        n_bits=int(r0.n),
        chi_true=chi_true,
        sigma_delta=0.25,
        seed=int(0 + 17 * int(r0.m) + 31 * int(r0.n)),
    )
    chi_idx = e2e._reconstruct_chi_from_bits(bits=bits, m=int(r0.m))
    chi = e2e._chi_index_to_grid(n_bits=int(r0.n), chi_idx=chi_idx)
    k = min(int(r0.required_sites), int(side * side))
    region, _chi_star = _select_top_k_region(chi, k)

    # Build a mask image.
    mask = [[0.0 for _ in range(side)] for _ in range(side)]
    for idx in region:
        y = idx // side
        x = idx % side
        mask[y][x] = 1.0

    # Scattering benchmark curves.
    omega0 = 0.0
    gamma_bw = 1.0
    omega = [(-6.0 + 12.0 * i / 800.0) for i in range(801)]
    tau = [_breit_wigner_delay(omega=w, omega0=omega0, gamma=gamma_bw) for w in omega]
    tau0 = _breit_wigner_delay(omega=6.0, omega0=omega0, gamma=gamma_bw)
    kappa0 = 1.0
    gamma = 1.0
    lapse = [math.exp(-gamma * math.log((t / tau0) / kappa0)) for t in tau]

    fig = plt.figure(figsize=(10.5, 4.2))
    ax1 = fig.add_subplot(1, 2, 1)
    im = ax1.imshow(chi, cmap="viridis", origin="lower")
    ax1.imshow(mask, cmap="Reds", alpha=0.35, origin="lower")
    ax1.set_title(rf"Toy $\chi(x)$ and budget cloud ($m={r0.m},n={r0.n}$)")
    ax1.set_xticks([])
    ax1.set_yticks([])
    fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)

    ax2 = fig.add_subplot(1, 2, 2)
    ax2.plot(omega, tau, label=r"$\tau(\omega)$ (Breit--Wigner)")
    ax2.set_xlabel(r"$\omega$")
    ax2.set_ylabel(r"$\tau$")
    ax2_t = ax2.twinx()
    ax2_t.plot(omega, lapse, color="tab:orange", label=r"$N(\omega)$")
    ax2_t.set_ylabel(r"$N$")
    ax2.set_title(r"Delay and lapse proxy")
    ax2.grid(True, alpha=0.2)

    # Joint legend (two axes).
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_t.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)

    figures_dir().mkdir(parents=True, exist_ok=True)
    out_png = figures_dir() / "qg_interface_suite.png"
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def main() -> None:
    rows = _build_rows()
    _write_rows(rows)
    _write_summary(rows)
    _plot_optional(rows)


if __name__ == "__main__":
    main()

