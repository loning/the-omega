# -*- coding: utf-8 -*-
"""
Optional figure generator: chi-horizon occupancy phase diagram (capacity-only).

This script visualizes the capacity-only horizon occupancy fraction:
    f_hor(m,n; I_obs, c) = min( ceil(c*I_obs/m), 4^n ) / 4^n

It is intentionally independent of any chi(x) distribution and uses only the
budget-trigger rule in the manuscript (Appendix: protocol horizon / tick-trap).

Outputs (optional, requires matplotlib):
  - figures/chi_horizon_occupancy_phase.png

Design:
  - deterministic (no randomness, no timestamps)
  - English-only
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from common_paths import figures_dir


def _ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("b must be positive")
    return (a + b - 1) // b


@dataclass(frozen=True)
class Params:
    i_obs_bits: int
    c: int
    m_min: int
    m_max: int
    n_min: int
    n_max: int


def _occupancy_frac(*, m: int, n: int, i_obs_bits: int, c: int) -> float:
    total = 4 ** int(n)
    required = _ceil_div(int(c) * int(i_obs_bits), int(m))
    capped = min(required, total)
    return float(capped) / float(total)


def _grid(p: Params) -> Tuple[List[int], List[int], List[List[float]]]:
    ms = list(range(int(p.m_min), int(p.m_max) + 1))
    ns = list(range(int(p.n_min), int(p.n_max) + 1))
    z: List[List[float]] = []
    for n in ns:
        row: List[float] = []
        for m in ms:
            row.append(_occupancy_frac(m=m, n=n, i_obs_bits=p.i_obs_bits, c=p.c))
        z.append(row)
    return ms, ns, z


def main() -> None:
    # Match the capacity-only audit family defaults (but visualize a wider grid).
    p = Params(
        i_obs_bits=1024,
        c=16,
        m_min=4,
        m_max=16,
        n_min=2,
        n_max=8,
    )

    ms, ns, z = _grid(p)

    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "matplotlib is required for this optional figure. "
            "Install requirements.txt or run other scripts without plotting."
        ) from e

    fig, ax = plt.subplots(figsize=(8.6, 4.3), dpi=160)
    x0 = float(min(ms) - 0.5)
    x1 = float(max(ms) + 0.5)
    y0 = float(min(ns) - 0.5)
    y1 = float(max(ns) + 0.5)
    im = ax.imshow(
        z,
        origin="lower",
        aspect="auto",
        vmin=0.0,
        vmax=1.0,
        extent=[x0, x1, y0, y1],
        cmap="viridis",
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(r"occupancy fraction $f_{\mathrm{hor}}=|\mathcal{R}_\star|/4^n$")

    ax.set_xlabel(r"window length $m$")
    ax.set_ylabel(r"Hilbert order $n$ (screen size $4^n$)")
    ax.set_title(
        r"Capacity-only chi-horizon occupancy phase diagram  "
        + rf"($I_{{\mathrm{{obs}}}}={p.i_obs_bits}$ bits, $c={p.c}$)"
    )

    # Overlay the saturation boundary where required_sites > 4^n (i.e., frac==1 after capping).
    # This is the discrete curve m = ceil(c*I_obs / 4^n).
    boundary_ms: List[int] = []
    boundary_ns: List[int] = []
    for n in ns:
        total = 4 ** int(n)
        m_sat = _ceil_div(int(p.c) * int(p.i_obs_bits), int(total))
        # Only plot boundary points that lie within the shown m-range; otherwise
        # matplotlib will auto-expand xlim and make the heatmap unreadable.
        if int(p.m_min) <= int(m_sat) <= int(p.m_max):
            boundary_ms.append(int(m_sat))
            boundary_ns.append(int(n))
    if boundary_ms:
        ax.plot(boundary_ms, boundary_ns, color="white", linewidth=2.0, label="saturation boundary")

    # Keep axes pinned to the heatmap range (avoid expansion due to out-of-range overlays).
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.legend(loc="upper right", frameon=True, fontsize=8)

    out = figures_dir() / "chi_horizon_occupancy_phase.png"
    fig.tight_layout()
    fig.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

