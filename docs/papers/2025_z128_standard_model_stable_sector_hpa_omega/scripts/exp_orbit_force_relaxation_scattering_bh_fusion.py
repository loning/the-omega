# -*- coding: utf-8 -*-
"""
Fusion experiment: force generation + propagation + relaxation + scattering-delay readout + BH-like trap.

This experiment is an auditable *interface-level* synthesis meant to mirror the paper's style:
  - force as response to an effective potential Phi=-gamma*c^2*(chi-chi0),
  - propagation through a protocol field chi(x,t),
  - relaxation into a new periodic orbit (limit cycle) under damping,
  - scattering delay as an operational readout channel,
  - BH-like behavior as a budget-triggered horizon/trap with leakage/radiation ledger.

Important scope:
  - This does not claim to derive real quantum-gravity microdynamics.
  - "BH-like" is used in the paper's operational, observer-relative sense:
    a region whose residual internal capacity exceeds an observer budget and whose response
    is delay-dominated, together with a leakage/exit-channel bookkeeping vocabulary.

Outputs (LaTeX fragments):
  - sections/generated/orbit_force_relax_bh_rows.tex
  - sections/generated/orbit_force_relax_bh_summary.tex

Optional figure (requires matplotlib):
  - figures/orbit_force_relax_bh.png

Dependencies:
  - numpy (required)
  - matplotlib (optional)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from common_paths import figures_dir, generated_dir
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("b must be positive")
    return (a + b - 1) // b


def _roll_laplacian(u: np.ndarray, h: float) -> np.ndarray:
    inv_h2 = 1.0 / (h * h)
    return (
        np.roll(u, 1, axis=0)
        + np.roll(u, -1, axis=0)
        + np.roll(u, 1, axis=1)
        + np.roll(u, -1, axis=1)
        - 4.0 * u
    ) * inv_h2


def _roll_grad(u: np.ndarray, h: float) -> Tuple[np.ndarray, np.ndarray]:
    gx = (np.roll(u, -1, axis=1) - np.roll(u, 1, axis=1)) / (2.0 * h)
    gy = (np.roll(u, -1, axis=0) - np.roll(u, 1, axis=0)) / (2.0 * h)
    return gx, gy


def _bilinear_sample(u: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    side = int(u.shape[0])
    x0 = np.floor(x).astype(int) % side
    y0 = np.floor(y).astype(int) % side
    x1 = (x0 + 1) % side
    y1 = (y0 + 1) % side
    fx = x - np.floor(x)
    fy = y - np.floor(y)
    v00 = u[y0, x0]
    v10 = u[y0, x1]
    v01 = u[y1, x0]
    v11 = u[y1, x1]
    v0 = v00 * (1.0 - fx) + v10 * fx
    v1 = v01 * (1.0 - fx) + v11 * fx
    return v0 * (1.0 - fy) + v1 * fy


def _wrap_pos(p: np.ndarray, side: float) -> np.ndarray:
    return np.mod(p, side)


def _torus_delta(d: np.ndarray, side: float) -> np.ndarray:
    # Map displacement to shortest torus displacement.
    return d - side * np.round(d / side)


def _chi_eq_harmonic(
    *,
    xx: np.ndarray,
    yy: np.ndarray,
    center: Tuple[float, float],
    kappa: float,
    gamma: float,
    c2: float,
    chi0: float,
) -> np.ndarray:
    cx, cy = center
    dx = _torus_delta(xx - float(cx), float(xx.shape[1]))
    dy = _torus_delta(yy - float(cy), float(yy.shape[0]))
    r2 = dx * dx + dy * dy
    phi = 0.5 * float(kappa) * r2
    return float(chi0) - phi / (float(gamma) * float(c2))


def _switch01(t: float, t0: float, w: float) -> float:
    return 0.5 * (1.0 + math.tanh((t - float(t0)) / float(w)))


def _breit_wigner_delay(omega: float, omega0: float, Gamma: float) -> float:
    # One-channel unitary benchmark: tau(omega)=d delta/d omega for Breit–Wigner.
    return float(Gamma) / ((omega - omega0) ** 2 + (float(Gamma) / 2.0) ** 2)


def _autocorr_period_estimate(x: np.ndarray, dt: float, min_lag: int, max_lag: int) -> float:
    """
    Deterministic period estimate from autocorrelation peak in [min_lag,max_lag].
    Returns period in physical time units (ticks*dt). If no peak found, returns NaN.
    """
    if x.size < max_lag + 2:
        return float("nan")
    x0 = x - float(np.mean(x))
    denom = float(np.dot(x0, x0))
    if denom <= 0.0:
        return float("nan")
    best = (0.0, -1)  # (corr, lag)
    for lag in range(int(min_lag), int(max_lag) + 1):
        c = float(np.dot(x0[:-lag], x0[lag:])) / denom
        if c > best[0]:
            best = (c, lag)
    if best[1] < 0:
        return float("nan")
    return float(best[1]) * float(dt)


@dataclass(frozen=True)
class Row:
    t: float
    e_total: float
    e_part: float
    e_field: float
    e_emit: float
    chi_rms: float
    horizon_frac: float
    mean_delay_free: float
    mean_delay_trap: float
    mean_r_to_new: float
    std_r_to_new: float


def main() -> None:
    # -----------------------
    # Deterministic parameters.
    # -----------------------
    n = 6
    side = int(2**n)
    h = 1.0
    dt = 0.02
    steps = 7000
    sample_every = 350

    # Force dictionary parameters.
    gamma = 1.0
    c2 = 1.0
    chi0 = 0.0
    kappa = 0.02

    # Field propagation (telegraph / damped KG).
    c_field = 6.0
    alpha = 0.9
    omega_relax = 2.0

    # Particle dynamics.
    n_particles = 16
    mass = 1.0
    eta = 0.35

    # Environment switch (new orbit center).
    center0 = (0.25 * side, 0.25 * side)
    center1 = (0.68 * side, 0.55 * side)
    t_switch = 40.0
    switch_width = 3.0

    # BH-like trap: a high-chi bump at a fixed location + budget trigger.
    bh_center = (0.52 * side, 0.78 * side)
    bh_amp = 2.5  # amplitude of extra overhead bump (dimensionless chi)
    bh_sigma = 4.0
    # Keep the horizon region small enough to yield a meaningful free-vs-trapped comparison
    # while still being "budget-triggered" under the paper's capacity language.
    i_obs = 64
    margin_c = 16
    m_window = 6  # protocol window length used in the horizon capacity proxy

    # Leakage/evaporation bookkeeping (interface toy):
    # trapped energy decays with a rate that decreases with delay (deep traps leak slowly).
    leak_base = 0.08
    leak_delay_scale = 12.0
    rad_kick = 0.02  # how strongly emitted energy perturbs chi (toy).

    # Scattering-delay readout benchmark.
    omega_probe = 0.0
    Gamma0 = 1.0
    beta_shift = 0.8  # omega0 shift per unit chi (toy dictionary)

    rng = np.random.default_rng(0)

    # Grid.
    xs = np.arange(side, dtype=float)
    ys = np.arange(side, dtype=float)
    xx, yy = np.meshgrid(xs, ys)

    def chi_eq(t: float) -> np.ndarray:
        s = _switch01(t, t0=t_switch, w=switch_width)
        a = _chi_eq_harmonic(xx=xx, yy=yy, center=center0, kappa=kappa, gamma=gamma, c2=c2, chi0=chi0)
        b = _chi_eq_harmonic(xx=xx, yy=yy, center=center1, kappa=kappa, gamma=gamma, c2=c2, chi0=chi0)
        return (1.0 - s) * a + s * b

    def bh_bump() -> np.ndarray:
        cx, cy = bh_center
        dx = _torus_delta(xx - float(cx), float(side))
        dy = _torus_delta(yy - float(cy), float(side))
        r2 = dx * dx + dy * dy
        return float(bh_amp) * np.exp(-0.5 * r2 / (float(bh_sigma) ** 2))

    # Budget-triggered horizon occupancy: minimal required sites, capped; defines a threshold chi_* by top-k.
    required_sites = _ceil_div(int(margin_c) * int(i_obs), int(m_window))
    required_sites_capped = min(required_sites, side * side)

    def horizon_region(chi_grid: np.ndarray) -> Tuple[np.ndarray, float, float]:
        flat = chi_grid.reshape(-1)
        # deterministic: sort indices by value desc then idx asc
        idx = np.arange(flat.size, dtype=int)
        order = np.lexsort((idx, -flat))  # primary: -flat, tie: idx
        chosen = order[:required_sites_capped]
        mask = np.zeros_like(flat, dtype=bool)
        mask[chosen] = True
        chi_star = float(flat[chosen[-1]]) if chosen.size > 0 else float("inf")
        frac = float(chosen.size) / float(flat.size)
        return mask.reshape((side, side)), chi_star, frac

    # Initialize field: equilibrium + BH bump + small impulse.
    chi = chi_eq(0.0) + bh_bump()
    pi = np.zeros_like(chi)
    # A deterministic impulse to seed a propagating disturbance (toy "kick").
    impulse = np.zeros_like(chi)
    impulse[side // 3, side // 4] = 1.0
    pi += 0.6 * impulse

    # Initialize particles on a ring around center0.
    omega_orbit = math.sqrt(float(kappa) / float(mass))
    r0 = 0.18 * side
    angles = np.linspace(0.0, 2.0 * math.pi, n_particles, endpoint=False)
    pos = np.zeros((n_particles, 2), dtype=float)
    vel = np.zeros((n_particles, 2), dtype=float)
    cx0, cy0 = center0
    for i, th in enumerate(angles):
        pos[i, 0] = cx0 + r0 * math.cos(th)
        pos[i, 1] = cy0 + r0 * math.sin(th)
        v = omega_orbit * r0
        vel[i, 0] = -v * math.sin(th)
        vel[i, 1] = +v * math.cos(th)
    pos = _wrap_pos(pos, float(side))

    # Energy ledger.
    e_emit = 0.0

    def phi_from_chi(chi_grid: np.ndarray) -> np.ndarray:
        return -float(gamma) * float(c2) * (chi_grid - float(chi0))

    def field_energy(chi_grid: np.ndarray, pi_grid: np.ndarray, chi_eq_grid: np.ndarray) -> float:
        gx, gy = _roll_grad(chi_grid, h=h)
        dens = 0.5 * (
            pi_grid**2
            + (float(c_field) ** 2) * (gx**2 + gy**2)
            + (float(omega_relax) ** 2) * ((chi_grid - chi_eq_grid) ** 2)
        )
        return float(np.sum(dens) * (h * h))

    def particle_energy(pos_xy: np.ndarray, vel_xy: np.ndarray, phi_grid: np.ndarray) -> float:
        x = pos_xy[:, 0]
        y = pos_xy[:, 1]
        phi_s = _bilinear_sample(phi_grid, x=x, y=y)
        kin = 0.5 * float(mass) * float(np.sum(vel_xy[:, 0] ** 2 + vel_xy[:, 1] ** 2))
        pot = float(np.sum(phi_s))
        return float(kin + pot)

    def torus_r(pos_xy: np.ndarray, center: Tuple[float, float]) -> np.ndarray:
        d = pos_xy - np.array(center, dtype=float).reshape((1, 2))
        d[:, 0] = _torus_delta(d[:, 0], float(side))
        d[:, 1] = _torus_delta(d[:, 1], float(side))
        return np.sqrt(d[:, 0] ** 2 + d[:, 1] ** 2)

    # For period detection: track a torus-robust phase proxy late in the run.
    # Use cos(theta) about the *new* center (center1), which is continuous on the torus.
    tail_start = int(0.5 * steps)
    tail_cos: List[float] = []

    rows: List[Row] = []

    for step in range(steps + 1):
        t = float(step) * float(dt)
        chi_eq_t = chi_eq(t) + bh_bump()  # BH bump persists as a "high-energy structure" in this toy.

        # Horizon region derived from current chi (budget-triggered).
        hmask, chi_star, hfrac = horizon_region(chi)

        # Readout: particle delays from local chi via a shifted Breit–Wigner.
        chi_p = _bilinear_sample(chi, x=pos[:, 0], y=pos[:, 1])
        omega0_eff = beta_shift * chi_p
        tau = np.array([_breit_wigner_delay(omega_probe, float(w0), Gamma0) for w0 in omega0_eff], dtype=float)

        # Trap membership: particle is "BH-like trapped" if its current cell is in horizon region.
        ix = np.floor(pos[:, 0]).astype(int) % side
        iy = np.floor(pos[:, 1]).astype(int) % side
        in_trap = hmask[iy, ix]

        # Energy snapshot.
        if step % sample_every == 0 or step == steps:
            phi = phi_from_chi(chi)
            ef = field_energy(chi, pi, chi_eq_t)
            ep = particle_energy(pos, vel, phi)
            chi_rms = float(np.sqrt(np.mean((chi - chi_eq_t) ** 2)))
            rr = torus_r(pos, center=center1)
            free_tau = float(np.mean(tau[~in_trap])) if np.any(~in_trap) else 0.0
            trap_tau = float(np.mean(tau[in_trap])) if np.any(in_trap) else 0.0
            rows.append(
                Row(
                    t=t,
                    e_total=float(ef + ep + e_emit),
                    e_part=float(ep),
                    e_field=float(ef),
                    e_emit=float(e_emit),
                    chi_rms=float(chi_rms),
                    horizon_frac=float(hfrac),
                    mean_delay_free=float(free_tau),
                    mean_delay_trap=float(trap_tau),
                    mean_r_to_new=float(np.mean(rr)),
                    std_r_to_new=float(np.std(rr)),
                )
            )

        if step == steps:
            break

        # Tail trace for period estimate.
        if step >= tail_start:
            d0 = pos[0, :] - np.array(center1, dtype=float)
            dx0 = float(_torus_delta(np.array([d0[0]]), float(side))[0])
            dy0 = float(_torus_delta(np.array([d0[1]]), float(side))[0])
            theta = math.atan2(dy0, dx0)
            tail_cos.append(math.cos(theta))

        # ---------------- Field update (damped KG / telegraph) ----------------
        lap = _roll_laplacian(chi, h=h)
        accel = (float(c_field) ** 2) * lap - (float(omega_relax) ** 2) * (chi - chi_eq_t) - float(alpha) * pi
        pi = pi + float(dt) * accel
        chi = chi + float(dt) * pi

        # ---------------- Particle update: force from grad chi + damping ----------------
        gx, gy = _roll_grad(chi, h=h)
        fx = float(gamma) * float(c2) * _bilinear_sample(gx, x=pos[:, 0], y=pos[:, 1])
        fy = float(gamma) * float(c2) * _bilinear_sample(gy, x=pos[:, 0], y=pos[:, 1])

        # BH-like leakage: trapped particles lose internal energy, emit to ledger, and kick the field outward.
        # Use a deterministic rate that decreases with delay.
        if np.any(in_trap):
            tau_trap = tau[in_trap]
            rate = float(leak_base) / (1.0 + float(np.mean(tau_trap)) / float(leak_delay_scale))
            # Emitted energy is proportional to kinetic energy of trapped particles (toy).
            kin_trap = 0.5 * float(mass) * float(np.sum(vel[in_trap, 0] ** 2 + vel[in_trap, 1] ** 2))
            dE = float(rate) * float(dt) * kin_trap
            e_emit += dE
            # Reduce velocities slightly (energy loss).
            vel[in_trap, :] *= (1.0 - min(0.5, float(rate) * float(dt)))
            # Radiative kick: add a small isotropic pulse to pi around BH center (toy).
            # Deterministic: fixed radial profile.
            cx, cy = bh_center
            dx = _torus_delta(xx - float(cx), float(side))
            dy = _torus_delta(yy - float(cy), float(side))
            r2 = dx * dx + dy * dy
            pulse = float(rad_kick) * float(dE) * np.exp(-0.5 * r2 / (float(2.5) ** 2))
            pi += pulse

        ax = fx / float(mass) - float(eta) * vel[:, 0]
        ay = fy / float(mass) - float(eta) * vel[:, 1]
        vel[:, 0] = vel[:, 0] + float(dt) * ax
        vel[:, 1] = vel[:, 1] + float(dt) * ay
        pos[:, 0] = pos[:, 0] + float(dt) * vel[:, 0]
        pos[:, 1] = pos[:, 1] + float(dt) * vel[:, 1]
        pos = _wrap_pos(pos, float(side))

        # Small deterministic noise floor (optional) to break perfect symmetries without randomness.
        # Use a bounded sinusoidal dither (no RNG).
        vel[:, 0] += 1e-5 * math.sin(0.1 * t)
        vel[:, 1] += 1e-5 * math.cos(0.1 * t)

    # Period estimate (late-time).
    tail_arr = np.array(tail_cos, dtype=float)
    # Search around the expected harmonic-orbit period:
    # omega_orbit = sqrt(kappa/mass), so T ~ 2pi/omega_orbit.
    T0 = 2.0 * math.pi / (math.sqrt(float(kappa) / float(mass)) + 1e-12)
    lag0 = int(max(20, round(T0 / float(dt))))
    max_lag = min(int(lag0 * 2), int(max(60, tail_arr.size - 10)))
    min_lag = max(10, int(lag0 // 3))
    T_est = _autocorr_period_estimate(tail_arr, dt=dt, min_lag=min_lag, max_lag=max_lag)

    # Write LaTeX table rows.
    out_lines: List[str] = []
    for r in rows:
        out_lines.append(
            " & ".join(
                [
                    _fmt(r.t, 2),
                    _fmt(r.e_total, 6),
                    _fmt(r.e_part, 6),
                    _fmt(r.e_field, 6),
                    _fmt(r.e_emit, 6),
                    _fmt(r.chi_rms, 6),
                    _fmt(r.horizon_frac, 6),
                    _fmt(r.mean_delay_free, 6),
                    _fmt(r.mean_delay_trap, 6),
                    _fmt(r.mean_r_to_new, 4),
                    _fmt(r.std_r_to_new, 4),
                ]
            )
            + r" \\"
        )
    write_lines(generated_dir() / "orbit_force_relax_bh_rows.tex", out_lines if out_lines else ["% (no rows)"])

    # Summary fragment.
    summary = [
        r"\paragraph{Audit summary (fusion: force propagation, scattering delay, and BH-like trapping).} \AuditTag "
        r"We simulate particles on a periodic $64\times64$ screen under a scalar protocol field $\chi(x,t)$ with "
        r"$\Phi=-\gamma c^2(\chi-\chi_0)$ and force $F=-\nabla\Phi=\gamma c^2\nabla\chi$. "
        r"The field propagates via a damped telegraph/Klein--Gordon form "
        r"$\chi_{tt}+\alpha\chi_t=c_f^2\Delta\chi-\omega^2(\chi-\chi_{\mathrm{eq}}(t))$, "
        r"with a smooth equilibrium-center shift (new orbit center) and a persistent high-$\chi$ bump "
        r"treated as a BH-like high-energy structure. "
        r"A budget-triggered horizon proxy selects a top-$k$ region whose capacity satisfies "
        r"$m|\mathcal R_\star|\ge cI_{\mathrm{obs}}$; particles inside are treated as trapped. "
        r"Scattering delay is reported by a one-channel Breit--Wigner benchmark with an $\omega_0$ shift proportional "
        r"to the local $\chi$ (operational delay channel). "
        rf"A deterministic leakage/evaporation toy reduces trapped kinetic energy and accumulates emitted energy "
        rf"$E_\mathrm{{emit}}(t)$ while injecting a small radiative pulse into the field. "
        rf"The table reports the energy ledger $E_\mathrm{{tot}}=E_\mathrm{{part}}+E_\mathrm{{field}}+E_\mathrm{{emit}}$, "
        rf"horizon occupancy fraction, mean delays (free vs trapped), and a relaxation proxy (radius stats) "
        rf"as the system converges to a new periodic orbit. Late-time period estimate: $T_{{\mathrm{{est}}}}={_fmt(T_est,3)}$.",
    ]
    write_lines(generated_dir() / "orbit_force_relax_bh_summary.tex", summary)

    # Optional figure.
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    fig = plt.figure(figsize=(12.0, 7.2))
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.imshow(chi, cmap="viridis", origin="lower")
    ax1.set_title(r"final $\chi(x)$ (with BH bump)")
    ax1.set_xticks([])
    ax1.set_yticks([])

    ax2 = fig.add_subplot(2, 2, 2)
    tt = np.array([r.t for r in rows], dtype=float)
    eT = np.array([r.e_total for r in rows], dtype=float)
    eP = np.array([r.e_part for r in rows], dtype=float)
    eF = np.array([r.e_field for r in rows], dtype=float)
    eE = np.array([r.e_emit for r in rows], dtype=float)
    ax2.plot(tt, eT, label=r"$E_{\mathrm{tot}}$")
    ax2.plot(tt, eP, label=r"$E_{\mathrm{part}}$")
    ax2.plot(tt, eF, label=r"$E_{\mathrm{field}}$")
    ax2.plot(tt, eE, label=r"$E_{\mathrm{emit}}$")
    ax2.set_title("energy ledger (sampled)")
    ax2.set_xlabel("t")
    ax2.grid(True, alpha=0.2)
    ax2.legend(fontsize=8, loc="best")

    ax3 = fig.add_subplot(2, 2, 3)
    dF = np.array([r.mean_delay_free for r in rows], dtype=float)
    dT = np.array([r.mean_delay_trap for r in rows], dtype=float)
    ax3.plot(tt, dF, label="mean delay (free)")
    ax3.plot(tt, dT, label="mean delay (trapped)")
    ax3.set_title("scattering delay readout (toy)")
    ax3.set_xlabel("t")
    ax3.grid(True, alpha=0.2)
    ax3.legend(fontsize=8, loc="best")

    ax4 = fig.add_subplot(2, 2, 4)
    hfr = np.array([r.horizon_frac for r in rows], dtype=float)
    ax4.plot(tt, hfr, label="horizon occupancy fraction")
    ax4.set_title("horizon proxy (capacity-triggered)")
    ax4.set_xlabel("t")
    ax4.grid(True, alpha=0.2)
    ax4.legend(fontsize=8, loc="best")

    figures_dir().mkdir(parents=True, exist_ok=True)
    out_png = figures_dir() / "orbit_force_relax_bh.png"
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()

