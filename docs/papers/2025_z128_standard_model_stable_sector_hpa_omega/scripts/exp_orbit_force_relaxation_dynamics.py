# -*- coding: utf-8 -*-
"""
Force propagation and relaxation to a new periodic orbit (deterministic interface experiment).

Goal (interface, auditable):
  Construct a single mathematical mechanism that
    - generates a force acting on particle orbits,
    - propagates that force influence through a field,
    - relaxes the system into a new stable periodic orbit,
    - reports an explicit energy ledger over time.

Mechanism used (aligned with the paper's dictionaries):
  - A scalar overhead-like field chi(x,t) on a periodic 2D screen (torus).
  - An effective potential Phi := -gamma * c^2 * (chi - chi0).
  - Particle force: F = -∇Phi = gamma * c^2 * ∇chi (sampled at particle positions).
  - Field propagation: damped Klein–Gordon / telegraph form
        chi_tt + alpha * chi_t = c_field^2 * Δ chi - omega_relax^2 * (chi - chi_eq(t))
      where chi_eq(t) is a slowly switched equilibrium profile (center shift).
  - Particle relaxation: viscous damping term -eta * v, so trajectories converge to a
    stable limit cycle (periodic orbit) set by the final equilibrium field.

This is a protocol-level *toy* implementation: it is not claimed as a derivation of
microscopic QFT/quantum-gravity dynamics. It is intended as a reproducible, auditable
demonstration of the narrative step "force as response, propagation, and relaxation"
within a finite deterministic pipeline.

Outputs (LaTeX fragments):
  - sections/generated/orbit_force_relax_rows.tex
  - sections/generated/orbit_force_relax_summary.tex

Optional figure (requires matplotlib):
  - figures/orbit_force_relax.png

Dependencies:
  - numpy (required)
  - matplotlib (optional for plots)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from common_paths import figures_dir, generated_dir
from common_tex import write_lines


def _roll_laplacian(u: np.ndarray, h: float) -> np.ndarray:
    # Periodic 2D Laplacian with central differences.
    inv_h2 = 1.0 / (h * h)
    return (
        np.roll(u, 1, axis=0)
        + np.roll(u, -1, axis=0)
        + np.roll(u, 1, axis=1)
        + np.roll(u, -1, axis=1)
        - 4.0 * u
    ) * inv_h2


def _roll_grad(u: np.ndarray, h: float) -> Tuple[np.ndarray, np.ndarray]:
    # Periodic gradient, central differences.
    gx = (np.roll(u, -1, axis=1) - np.roll(u, 1, axis=1)) / (2.0 * h)
    gy = (np.roll(u, -1, axis=0) - np.roll(u, 1, axis=0)) / (2.0 * h)
    return gx, gy


def _bilinear_sample(u: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    Sample a periodic 2D grid u[y,x] at continuous positions (x,y) in [0,side).
    """
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


def _chi_equilibrium(
    *,
    xx: np.ndarray,
    yy: np.ndarray,
    center: Tuple[float, float],
    kappa: float,
    gamma: float,
    c2: float,
    chi0: float,
) -> np.ndarray:
    """
    Equilibrium chi profile that corresponds (via Phi=-gamma*c^2*(chi-chi0))
    to a harmonic potential Phi=(kappa/2) r^2 centered at 'center'.
    """
    cx, cy = center
    # Periodic shortest displacement on the torus.
    dx0 = np.abs(xx - cx)
    dxp = np.abs(xx - cx + xx.shape[1])
    dxm = np.abs(xx - cx - xx.shape[1])
    dx = np.minimum.reduce([dx0, dxp, dxm])

    dy0 = np.abs(yy - cy)
    dyp = np.abs(yy - cy + yy.shape[0])
    dym = np.abs(yy - cy - yy.shape[0])
    dy = np.minimum.reduce([dy0, dyp, dym])
    r2 = dx * dx + dy * dy
    phi = 0.5 * float(kappa) * r2
    # chi = chi0 - phi/(gamma*c^2)
    return float(chi0) - phi / (float(gamma) * float(c2))


@dataclass(frozen=True)
class Snapshot:
    t: float
    e_field: float
    e_part: float
    e_total: float
    chi_rms: float
    mean_r: float
    std_r: float


def main() -> None:
    # -----------------------
    # Fixed, auditable parameters (small deterministic family reduced to one case).
    # -----------------------
    n = 6  # grid side = 2^n (64)
    side = int(2**n)
    h = 1.0
    dt = 0.02
    steps = 6000
    sample_every = 400

    # Field parameters.
    c_field = 6.0
    alpha = 0.8  # field damping
    omega_relax = 2.0  # relax to chi_eq

    # Force dictionary parameters.
    gamma = 1.0
    c2 = 1.0
    chi0 = 0.0
    kappa = 0.02  # strength of harmonic trap potential in Phi

    # Particle parameters.
    n_particles = 12
    mass = 1.0
    eta = 0.35  # particle damping (relaxation)

    # Equilibrium shift ("energy landscape" change).
    center0 = (0.25 * side, 0.25 * side)
    center1 = (0.68 * side, 0.55 * side)
    t_switch = 40.0
    switch_width = 3.0

    # Initial orbit radius and tangential speed (set by harmonic oscillator frequency).
    # For Phi=(kappa/2) r^2, omega_orbit = sqrt(kappa/mass) and stable circular v=omega*r.
    r0 = 0.18 * side
    omega_orbit = math.sqrt(float(kappa) / float(mass))

    # Grid coordinates.
    xs = np.arange(side, dtype=float)
    ys = np.arange(side, dtype=float)
    xx, yy = np.meshgrid(xs, ys)

    # Smooth switch function s(t) in [0,1].
    def s_of_t(t: float) -> float:
        return 0.5 * (1.0 + math.tanh((t - float(t_switch)) / float(switch_width)))

    def chi_eq(t: float) -> np.ndarray:
        s = s_of_t(t)
        chi_a = _chi_equilibrium(
            xx=xx, yy=yy, center=center0, kappa=kappa, gamma=gamma, c2=c2, chi0=chi0
        )
        chi_b = _chi_equilibrium(
            xx=xx, yy=yy, center=center1, kappa=kappa, gamma=gamma, c2=c2, chi0=chi0
        )
        return (1.0 - s) * chi_a + s * chi_b

    # Initialize field at equilibrium (t=0), zero velocity.
    chi = chi_eq(0.0).copy()
    pi = np.zeros_like(chi)

    # Initialize particles on a ring around center0 with tangential velocity.
    angles = np.linspace(0.0, 2.0 * math.pi, n_particles, endpoint=False)
    pos = np.zeros((n_particles, 2), dtype=float)
    vel = np.zeros((n_particles, 2), dtype=float)
    cx0, cy0 = center0
    for i, th in enumerate(angles):
        x = cx0 + r0 * math.cos(th)
        y = cy0 + r0 * math.sin(th)
        pos[i, 0] = x
        pos[i, 1] = y
        # tangential direction (-sin, cos)
        v = omega_orbit * r0
        vel[i, 0] = -v * math.sin(th)
        vel[i, 1] = +v * math.cos(th)

    pos = _wrap_pos(pos, float(side))

    # Storage for an illustrative trajectory (first particle).
    traj = np.zeros((steps + 1, 2), dtype=float)
    traj[0] = pos[0].copy()

    # Energy helpers.
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
        kin = 0.5 * float(mass) * np.sum(vel_xy[:, 0] ** 2 + vel_xy[:, 1] ** 2)
        pot = float(np.sum(phi_s))
        return float(kin + pot)

    # Periodic distance to center1 for reporting (final equilibrium center).
    def torus_r(pos_xy: np.ndarray, center: Tuple[float, float]) -> np.ndarray:
        cx, cy = center
        dx = pos_xy[:, 0] - float(cx)
        dy = pos_xy[:, 1] - float(cy)
        dx = dx - float(side) * np.round(dx / float(side))
        dy = dy - float(side) * np.round(dy / float(side))
        return np.sqrt(dx * dx + dy * dy)

    snaps: List[Snapshot] = []

    # Main loop: leapfrog for field; semi-implicit damping for particles.
    for step in range(steps + 1):
        t = float(step) * float(dt)
        chi_eq_t = chi_eq(t)

        # Sample/record snapshot.
        if step % sample_every == 0 or step == steps:
            phi = phi_from_chi(chi)
            ef = field_energy(chi, pi, chi_eq_t)
            ep = particle_energy(pos, vel, phi)
            et = ef + ep
            chi_rms = float(np.sqrt(np.mean((chi - chi_eq_t) ** 2)))
            rr = torus_r(pos, center=center1)
            snaps.append(
                Snapshot(
                    t=t,
                    e_field=ef,
                    e_part=ep,
                    e_total=et,
                    chi_rms=chi_rms,
                    mean_r=float(np.mean(rr)),
                    std_r=float(np.std(rr)),
                )
            )

        if step == steps:
            break

        # -------- Field update (leapfrog) --------
        # pi_{n+1/2} = pi_{n-1/2} + dt * (c^2 Δchi - omega^2(chi-chi_eq) - alpha*pi)
        lap = _roll_laplacian(chi, h=h)
        accel = (float(c_field) ** 2) * lap - (float(omega_relax) ** 2) * (chi - chi_eq_t) - float(alpha) * pi
        pi = pi + float(dt) * accel
        chi = chi + float(dt) * pi

        # -------- Particle update --------
        gx, gy = _roll_grad(chi, h=h)
        fx = float(gamma) * float(c2) * _bilinear_sample(gx, x=pos[:, 0], y=pos[:, 1])
        fy = float(gamma) * float(c2) * _bilinear_sample(gy, x=pos[:, 0], y=pos[:, 1])
        # a = F/m - eta v (viscous damping)
        ax = fx / float(mass) - float(eta) * vel[:, 0]
        ay = fy / float(mass) - float(eta) * vel[:, 1]

        vel[:, 0] = vel[:, 0] + float(dt) * ax
        vel[:, 1] = vel[:, 1] + float(dt) * ay
        pos[:, 0] = pos[:, 0] + float(dt) * vel[:, 0]
        pos[:, 1] = pos[:, 1] + float(dt) * vel[:, 1]
        pos = _wrap_pos(pos, float(side))

        traj[step + 1] = pos[0].copy()

    # Write LaTeX rows.
    row_lines: List[str] = []
    for s in snaps:
        row_lines.append(
            " & ".join(
                [
                    _fmt(s.t, 2),
                    _fmt(s.e_total, 6),
                    _fmt(s.e_part, 6),
                    _fmt(s.e_field, 6),
                    _fmt(s.chi_rms, 6),
                    _fmt(s.mean_r, 4),
                    _fmt(s.std_r, 4),
                ]
            )
            + r" \\"
        )
    write_lines(generated_dir() / "orbit_force_relax_rows.tex", row_lines if row_lines else ["% (no rows)"])

    # Summary text (single paragraph fragment).
    summary = [
        r"\paragraph{Audit summary (force propagation and relaxation toy).} \AuditTag "
        r"We simulate $N_p=12$ particles on a $64\times64$ periodic screen with a scalar field $\chi(x,t)$ "
        r"that generates an effective potential $\Phi=-\gamma c^2(\chi-\chi_0)$ and force $F=-\nabla\Phi=\gamma c^2\nabla\chi$. "
        r"The field follows a damped Klein--Gordon/telegraph form "
        r"$\chi_{tt}+\alpha\chi_t=c_f^2\Delta\chi-\omega^2(\chi-\chi_{\mathrm{eq}}(t))$ "
        r"with a smooth equilibrium-center shift at $t_\mathrm{switch}=40$ (torus). "
        r"Particles include viscous damping $-\eta v$ so the orbit family relaxes into a new stable limit cycle "
        r"around the post-switch equilibrium center. "
        r"The table reports an explicit energy ledger $E_\mathrm{tot}=E_\mathrm{part}+E_\mathrm{field}$ "
        r"and a stability proxy (RMS field deviation and particle-radius statistics) at fixed sampling times.",
    ]
    write_lines(generated_dir() / "orbit_force_relax_summary.tex", summary)

    # Optional plot.
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    # Recompute a few field frames for visualization (deterministic, lightweight).
    # We only need chi at t=0, near switch, and final, so reuse equilibrium profiles.
    chi0_grid = chi_eq(0.0)
    chi1_grid = chi_eq(t_switch)
    chiF_grid = chi_eq(float(steps) * float(dt))

    fig = plt.figure(figsize=(11.5, 4.2))
    ax1 = fig.add_subplot(1, 3, 1)
    ax1.imshow(chi0_grid, cmap="viridis", origin="lower")
    ax1.set_title(r"$\chi_{\mathrm{eq}}$ (pre-switch)")
    ax1.set_xticks([])
    ax1.set_yticks([])

    ax2 = fig.add_subplot(1, 3, 2)
    ax2.imshow(chi1_grid, cmap="viridis", origin="lower")
    ax2.set_title(r"$\chi_{\mathrm{eq}}$ (near switch)")
    ax2.set_xticks([])
    ax2.set_yticks([])

    ax3 = fig.add_subplot(1, 3, 3)
    ax3.imshow(chiF_grid, cmap="viridis", origin="lower")
    ax3.plot(traj[:, 0], traj[:, 1], color="w", lw=1.0, alpha=0.9)
    ax3.set_title(r"$\chi_{\mathrm{eq}}$ (post-switch) + sample orbit")
    ax3.set_xticks([])
    ax3.set_yticks([])

    figures_dir().mkdir(parents=True, exist_ok=True)
    out_png = figures_dir() / "orbit_force_relax.png"
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


if __name__ == "__main__":
    main()

