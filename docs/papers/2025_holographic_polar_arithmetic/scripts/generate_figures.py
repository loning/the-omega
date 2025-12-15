import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np

TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class PhaseModel:
    name: str
    theta: np.ndarray  # shape (n_max + 1,), theta[0] unused, theta[1] for n=1


def linear_sieve_spf(n_max: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (spf, primes) where spf[n] is the smallest prime factor."""
    spf = np.zeros(n_max + 1, dtype=np.int32)
    primes: list[int] = []
    for i in range(2, n_max + 1):
        if spf[i] == 0:
            spf[i] = i
            primes.append(i)
        for p in primes:
            ip = i * p
            if ip > n_max:
                break
            spf[ip] = p
            if p == spf[i]:
                break
    spf[1] = 1
    return spf, np.asarray(primes, dtype=np.int32)


def build_phase_models(n_max: int, seed: int = 0) -> list[PhaseModel]:
    """Construct several explicit phase models theta(n) on {1..n_max}."""
    rng = np.random.default_rng(seed)
    spf, primes = linear_sieve_spf(n_max)

    n = np.arange(0, n_max + 1, dtype=np.float64)
    n[0] = 1.0  # avoid log(0) below; theta[0] unused anyway

    # Model 1: log-phase (theta(n) = beta0 * log n mod 2pi)
    beta0 = 4.0
    theta_log = (beta0 * np.log(n)) % TWO_PI

    # Model 2: omega-phase (theta(n) = beta1 * Omega(n) mod 2pi),
    # where Omega counts prime factors with multiplicity.
    beta1 = 2.0
    omega = np.zeros(n_max + 1, dtype=np.int32)
    for k in range(2, n_max + 1):
        omega[k] = omega[k // spf[k]] + 1
    theta_omega = (beta1 * omega.astype(np.float64)) % TWO_PI

    # Model 3: random prime weights beta(p) ~ Unif[0, 2pi)
    beta_prime = np.zeros(n_max + 1, dtype=np.float64)
    beta_prime[primes] = rng.uniform(0.0, TWO_PI, size=len(primes))
    theta_rnd = np.zeros(n_max + 1, dtype=np.float64)
    for k in range(2, n_max + 1):
        p = spf[k]
        theta_rnd[k] = theta_rnd[k // p] + beta_prime[p]
    theta_rnd %= TWO_PI

    return [
        PhaseModel("log_phase", theta_log),
        PhaseModel("omega_phase", theta_omega),
        PhaseModel("random_prime_phase", theta_rnd),
    ]


def build_Z(n_max: int, phase: PhaseModel, radial_power: float = 1.0) -> np.ndarray:
    """Return Z[1..n_max] as complex array of length n_max (index 0 => n=1)."""
    n = np.arange(1, n_max + 1, dtype=np.float64)
    rho = np.power(n, radial_power)
    theta = phase.theta[1 : n_max + 1]
    return rho * np.exp(1j * theta)


def nearest_point(v: complex, Z: np.ndarray) -> tuple[int, float, int]:
    """
    Exact nearest-point search for v against {Z(n)}_{n=1..len(Z)}.

    Uses a radial lower bound |v - Z(n)| >= ||v| - |Z(n)|| = ||v| - n|.
    """
    r = float(abs(v))
    if r <= 1.0:
        dists = np.abs(Z - v)
        best_idx = int(np.argmin(dists))
        best = float(dists[best_idx])
        tol = 1e-12 * max(1.0, best)
        count = int(np.sum(np.abs(dists - best) <= tol))
        return best_idx + 1, best, count

    W = max(25, int(math.ceil(math.sqrt(r))) + 2)
    while True:
        left = max(1, int(math.floor(r - W)))
        right = min(len(Z), int(math.ceil(r + W)))
        dists = np.abs(Z[left - 1 : right] - v)
        best_local = int(np.argmin(dists))
        best = float(dists[best_local])
        best_n = left + best_local

        if best <= W or (left == 1 and right == len(Z)):
            tol = 1e-12 * max(1.0, best)
            count = int(np.sum(np.abs(dists - best) <= tol))
            return best_n, best, count

        W = int(math.ceil(best))


def simulate_projection_gaps(
    Z: np.ndarray, n_pair_max: int, n_samples: int, seed: int = 0
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    a = rng.integers(1, n_pair_max + 1, size=n_samples, dtype=np.int32)
    b = rng.integers(1, n_pair_max + 1, size=n_samples, dtype=np.int32)

    v = Z[a - 1] + Z[b - 1]
    r = np.abs(v)

    n_proj = np.empty(n_samples, dtype=np.int32)
    g = np.empty(n_samples, dtype=np.float64)
    minimizer_count = np.empty(n_samples, dtype=np.int32)
    delta = np.empty(n_samples, dtype=np.complex128)

    for i in range(n_samples):
        n_i, g_i, c_i = nearest_point(v[i], Z)
        n_proj[i] = n_i
        g[i] = g_i
        minimizer_count[i] = c_i
        delta[i] = v[i] - Z[n_i - 1]

    return {
        "a": a,
        "b": b,
        "v": v,
        "r": r,
        "n_proj": n_proj,
        "g": g,
        "g_over_sqrt_r": g / np.sqrt(np.maximum(r, 1e-12)),
        "minimizer_count": minimizer_count,
        "delta": delta,
    }


def window_indicator(x: np.ndarray, start: float, length: float) -> np.ndarray:
    """Indicator of a half-open interval [start, start+length) on the circle."""
    start = float(start % 1.0)
    end = float((start + length) % 1.0)
    if length <= 0.0:
        return np.zeros_like(x, dtype=bool)
    if start <= end:
        return (x >= start) & (x < end)
    return (x >= start) | (x < end)


def zeckendorf_bits(n: int) -> list[int]:
    """Zeckendorf representation with Fibonacci base F1=1, F2=2."""
    if n <= 0:
        return [0]

    fib = [1, 2]
    while fib[-1] <= n:
        fib.append(fib[-1] + fib[-2])
    if fib[-1] > n:
        fib.pop()

    bits = [0] * len(fib)
    rem = n
    i = len(fib) - 1
    while i >= 0:
        if fib[i] <= rem:
            bits[i] = 1
            rem -= fib[i]
            i -= 2
        else:
            i -= 1
    return bits


def hamming_bits(a: list[int], b: list[int]) -> int:
    la, lb = len(a), len(b)
    L = max(la, lb)
    a2 = a + [0] * (L - la)
    b2 = b + [0] * (L - lb)
    return sum(int(x != y) for x, y in zip(a2, b2))


def ostrowski_digits_periodic(n: int, a_val: int) -> list[int]:
    """
    Ostrowski digits for alpha = [0; a_val, a_val, a_val, ...] (bounded type).

    Returns digits [b1, b2, ..., b_{m+1}] matching the convention in the paper:
      n = sum_{k=0}^m b_{k+1} q_k, with q_{-1}=0, q_0=1, q_{k+1}=a_{k+1} q_k + q_{k-1}.
    """
    if n <= 0:
        return [0]
    if a_val <= 0:
        raise ValueError("a_val must be positive")

    # Build convergent denominators q_0, q_1, ..., q_{m+1} with q_{m+1} > n.
    q_minus1 = 0
    q0 = 1
    q = [q0]
    while True:
        q1 = a_val * q0 + q_minus1
        q.append(q1)
        if q1 > n:
            break
        q_minus1, q0 = q0, q1

    m = len(q) - 2  # q[m] <= n < q[m+1]
    digits = [0] * (m + 1)  # digits[k] is b_{k+1} for k=0..m
    rem = n
    force_next_zero = False
    for k in range(m, -1, -1):
        if force_next_zero:
            digits[k] = 0
            force_next_zero = False
            continue

        qk = q[k]
        max_digit = (a_val - 1) if k == 0 else a_val
        d = min(max_digit, rem // qk)
        digits[k] = int(d)
        rem -= int(d) * qk
        if k >= 1 and d == a_val:
            force_next_zero = True

    return digits

def simulate_readout_stability(
    alpha: float,
    n_steps: int,
    etas: np.ndarray,
    n_trials: int,
    seed: int = 0,
    encode: Optional[Callable[[int], list[int]]] = None,
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    k = np.arange(n_steps, dtype=np.float64)
    x0 = rng.uniform(0.0, 1.0, size=n_trials)

    # Default window in the paper: W = [1-alpha, 1)
    start = 1.0 - alpha
    length = alpha

    flip_rate = np.empty(len(etas), dtype=np.float64)
    mean_abs_dS = np.empty(len(etas), dtype=np.float64)
    mean_zeck_hamming = np.empty(len(etas), dtype=np.float64)

    for j, eta in enumerate(etas):
        flips = []
        dS = []
        dZ = []
        for t in range(n_trials):
            x = (x0[t] + k * alpha) % 1.0
            s = window_indicator(x, start, length)
            s2 = window_indicator(x, start + eta, length)
            flips.append(np.mean(s != s2))

            S = int(np.sum(s))
            S2 = int(np.sum(s2))
            dS.append(abs(S - S2))

            if encode is None:
                z1 = zeckendorf_bits(S)
                z2 = zeckendorf_bits(S2)
                dZ.append(hamming_bits(z1, z2))
            else:
                z1 = encode(S)
                z2 = encode(S2)
                dZ.append(hamming_bits(z1, z2))

        flip_rate[j] = float(np.mean(flips))
        mean_abs_dS[j] = float(np.mean(dS))
        mean_zeck_hamming[j] = float(np.mean(dZ))

    return {
        "etas": etas,
        "flip_rate": flip_rate,
        "mean_abs_dS": mean_abs_dS,
        "mean_zeck_hamming": mean_zeck_hamming,
    }


def plot_scatter(Z: np.ndarray, title: str, out_path: Path, n_plot: int = 5000) -> None:
    n_plot = min(n_plot, len(Z))
    pts = Z[:n_plot]
    n = np.arange(1, n_plot + 1, dtype=np.float64)

    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    ax.set_aspect("equal", adjustable="box")
    sc = ax.scatter(pts.real, pts.imag, c=np.log(n), s=2, cmap="viridis", alpha=0.75, edgecolors="none")
    ax.set_title(title)
    ax.set_xlabel(r"$\Re(\mathcal{Z}(n))$")
    ax.set_ylabel(r"$\Im(\mathcal{Z}(n))$")
    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$\log n$")
    fig.tight_layout()
    fig.savefig(out_path, dpi=250)
    plt.close(fig)


def plot_gap_histograms(stats: dict[str, np.ndarray], title: str, out_path: Path) -> None:
    g = stats["g"]
    g_over_sqrt_r = stats["g_over_sqrt_r"]
    r = stats["r"]

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0))

    axes[0].hist(np.log10(g + 1e-12), bins=60, color="#2c7fb8", alpha=0.9)
    axes[0].set_title(r"$\log_{10} |\,\delta\,|$ (nearest-point)")
    axes[0].set_xlabel(r"$\log_{10}|\,\delta\,|$")
    axes[0].set_ylabel("count")

    axes[1].hist(g_over_sqrt_r, bins=60, color="#7fcdbb", alpha=0.9)
    axes[1].set_title(r"$|\,\delta\,|/\sqrt{|v|}$")
    axes[1].set_xlabel(r"$|\,\delta\,|/\sqrt{|v|}$")

    axes[2].scatter(r, g, s=2, alpha=0.25, color="#f03b20", edgecolors="none")
    axes[2].set_title(r"$|\,\delta\,|$ vs $|v|$")
    axes[2].set_xlabel(r"$|v|$")
    axes[2].set_ylabel(r"$|\,\delta\,|$")

    fig.suptitle(title)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(out_path, dpi=250)
    plt.close(fig)


def plot_readout_stability(stab: dict[str, np.ndarray], out_path: Path) -> None:
    etas = stab["etas"]
    flip_rate = stab["flip_rate"]
    mean_abs_dS = stab["mean_abs_dS"]
    mean_zeck_hamming = stab["mean_zeck_hamming"]

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(etas, flip_rate, marker="o", label="bit flip rate")
    ax.plot(etas, mean_abs_dS / np.max(mean_abs_dS), marker="s", label="|ΔS| (normalized)")
    ax.plot(etas, mean_zeck_hamming / np.max(mean_zeck_hamming), marker="^", label="Zeckendorf Hamming (normalized)")
    ax.set_xscale("log")
    ax.set_xlabel(r"window shift $\eta$")
    ax.set_ylabel("normalized magnitude")
    ax.set_title("Window perturbation stability (golden rotation)")
    ax.grid(True, which="both", linewidth=0.3, alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=250)
    plt.close(fig)


def plot_projection_kernel_example(
    Z: np.ndarray,
    v: complex,
    sigma: float,
    title: str,
    out_path: Path,
) -> None:
    r = float(abs(v))
    W = int(math.ceil(6.0 * sigma))
    left = max(1, int(math.floor(r - W)))
    right = min(len(Z), int(math.ceil(r + W)))
    n = np.arange(left, right + 1, dtype=np.int32)
    d = np.abs(Z[left - 1 : right] - v)
    d2 = d * d
    d2_min = float(np.min(d2))
    w = np.exp(-(d2 - d2_min) / (sigma * sigma))
    p = w / np.sum(w)

    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.plot(n, p, linewidth=1.1, color="#2c7fb8")
    ax.set_yscale("log")
    ax.set_xlabel(r"candidate $c$")
    ax.set_ylabel(r"$\pi_\sigma(c\mid v)$ (log scale)")
    ax.set_title(title)
    ax.grid(True, which="both", linewidth=0.3, alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=250)
    plt.close(fig)


def plot_transport_duality_diagram(out_path: Path) -> None:
    """
    Schematic concept figure:
      - Boundary S^1 with prime traps / mass impedance
      - Low-energy arc path with detours (gravitational delay)
      - High-energy chord shortcut and inward dive (kinematic advance)
    """
    fig, ax = plt.subplots(figsize=(7.8, 6.2))
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    # Unit disk (bulk)
    disk = plt.Circle((0.0, 0.0), 1.0, facecolor="#f3f3f3", edgecolor="none", zorder=0)
    ax.add_patch(disk)

    # Rough boundary ring to suggest impedance/texture.
    # Keep the ring on or outside the unit circle (no inward dents), so the
    # low-energy arc path is visually confined to the boundary regime.
    theta = np.linspace(0.0, TWO_PI, 800, dtype=np.float64)
    rough1 = 0.5 + 0.5 * np.sin(20.0 * theta)
    rough2 = 0.5 + 0.5 * np.sin(7.0 * theta + 0.7)
    r = 1.0 + 0.03 * rough1 + 0.015 * rough2
    ax.plot(r * np.cos(theta), r * np.sin(theta), color="black", linewidth=3.0, zorder=3)

    # Prime traps on the boundary
    trap_deg = np.array([20.0, 75.0, 140.0, 210.0, 280.0, 330.0], dtype=np.float64)
    trap_theta = np.deg2rad(trap_deg)
    trap_r = 1.0 + 0.03 * (0.5 + 0.5 * np.sin(20.0 * trap_theta)) + 0.015 * (0.5 + 0.5 * np.sin(7.0 * trap_theta + 0.7))
    ax.scatter(trap_r * np.cos(trap_theta), trap_r * np.sin(trap_theta), s=70, c="black", zorder=4)

    # Low-energy arc path near the boundary with local detours near traps
    t_arc = np.linspace(0.15 * math.pi, 1.85 * math.pi, 700, dtype=np.float64)
    r_arc = 0.92 + 0.015 * np.sin(6.0 * t_arc)
    for a in trap_theta:
        diff = np.angle(np.exp(1j * (t_arc - a)))
        r_arc += 0.06 * np.exp(-((diff / 0.12) ** 2))
    x_arc = r_arc * np.cos(t_arc)
    y_arc = r_arc * np.sin(t_arc)
    ax.plot(x_arc, y_arc, color="#d73027", linewidth=2.6, zorder=2)

    # High-energy chord shortcut across the disk
    p0 = (math.cos(float(t_arc[0])), math.sin(float(t_arc[0])))
    p1 = (math.cos(float(t_arc[-1])), math.sin(float(t_arc[-1])))
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color="#4575b4", linewidth=3.0, zorder=1)

    # Inward dive: logarithmic spiral (Fibonacci-type visual)
    t_sp = np.linspace(0.0, 4.0 * math.pi, 900, dtype=np.float64)
    r0, r_end = 0.98, 0.10
    k = math.log(r_end / r0) / float(t_sp[-1])  # negative
    r_sp = r0 * np.exp(k * t_sp)
    phi0 = math.radians(35.0)
    x_sp = r_sp * np.cos(t_sp + phi0)
    y_sp = r_sp * np.sin(t_sp + phi0)
    ax.plot(x_sp, y_sp, color="#1a9850", linewidth=2.4, zorder=2)

    # Arrow along the spiral (inward direction)
    i0, i1 = -110, -1
    ax.annotate(
        "",
        xy=(float(x_sp[i1]), float(y_sp[i1])),
        xytext=(float(x_sp[i0]), float(y_sp[i0])),
        arrowprops=dict(arrowstyle="->", lw=2.0, color="#1a9850"),
        zorder=5,
    )

    # Labels
    ax.text(0.0, 1.16, r"Boundary $S^1$", fontsize=11, ha="center", va="bottom")
    ax.text(0.0, 0.0, r"Bulk $D^2$", fontsize=11, ha="center", va="center", color="gray")

    ax.text(-1.45, 0.95, "Arc path\n(gravitational delay)", fontsize=10, ha="left", va="center", color="#d73027")

    mid = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
    ax.text(
        mid[0] + 0.10,
        mid[1] - 0.20,
        "Chord shortcut\n(kinematic advance)",
        fontsize=10,
        ha="center",
        va="center",
        color="#4575b4",
    )

    ax.text(-0.25, -0.55, "Inward dive\n(Fibonacci-type spiral)", fontsize=10, ha="center", va="center", color="#1a9850")

    ax.annotate(
        "Prime traps\n(mass impedance)",
        xy=(float(trap_r[1] * np.cos(trap_theta[1])), float(trap_r[1] * np.sin(trap_theta[1]))),
        xytext=(1.35, 0.85),
        arrowprops=dict(arrowstyle="->", lw=1.2, color="black"),
        fontsize=10,
        ha="left",
        va="center",
        color="black",
    )

    ax.set_xlim(-1.65, 1.65)
    ax.set_ylim(-1.35, 1.30)

    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_holographic_slice_diagram(out_path: Path) -> None:
    """
    Concept figure:
      - A unit sphere (monolith) in which the state is a unit vector.
      - An observation slice (a plane through the origin) and the orthogonal
        projection of the state onto that slice.
      - A discrete lattice readout on the slice, illustrating a nonzero gap δ.
    """
    # Matplotlib registers 3D projections via mpl_toolkits.
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(12.6, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 0.85])

    ax3 = fig.add_subplot(gs[0], projection="3d")
    ax2 = fig.add_subplot(gs[1])

    # --- Left: sphere + slice + projection ---
    ax3.set_box_aspect((1.0, 1.0, 1.0))
    ax3.set_xlim(-1.1, 1.1)
    ax3.set_ylim(-1.1, 1.1)
    ax3.set_zlim(-1.1, 1.1)
    ax3.axis("off")

    # Unit sphere
    u = np.linspace(0.0, TWO_PI, 80, dtype=np.float64)
    v = np.linspace(0.0, math.pi, 40, dtype=np.float64)
    uu, vv = np.meshgrid(u, v)
    xs = np.cos(uu) * np.sin(vv)
    ys = np.sin(uu) * np.sin(vv)
    zs = np.cos(vv)
    ax3.plot_surface(xs, ys, zs, rstride=1, cstride=1, color="#e6e6e6", alpha=0.25, edgecolor="none")

    # Observation slice plane through origin with normal n
    n = np.asarray([0.25, -0.15, 1.0], dtype=np.float64)
    n /= float(np.linalg.norm(n))
    e1 = np.asarray([n[1], -n[0], 0.0], dtype=np.float64)
    if float(np.linalg.norm(e1)) < 1e-8:
        e1 = np.asarray([1.0, 0.0, 0.0], dtype=np.float64)
    e1 /= float(np.linalg.norm(e1))
    e2 = np.cross(n, e1)
    e2 /= float(np.linalg.norm(e2))

    s = np.linspace(-1.05, 1.05, 18, dtype=np.float64)
    t = np.linspace(-1.05, 1.05, 18, dtype=np.float64)
    ss, tt = np.meshgrid(s, t)
    xp = ss * e1[0] + tt * e2[0]
    yp = ss * e1[1] + tt * e2[1]
    zp = ss * e1[2] + tt * e2[2]
    ax3.plot_surface(xp, yp, zp, color="#4575b4", alpha=0.12, edgecolor="none")

    # Orthogonal axes: maximal distinguishability channels (schematic).
    axis_len = 1.25
    ax3.plot([-axis_len, axis_len], [0.0, 0.0], [0.0, 0.0], color="black", lw=1.1, alpha=0.55)
    ax3.plot([0.0, 0.0], [-axis_len, axis_len], [0.0, 0.0], color="black", lw=1.1, alpha=0.55)
    ax3.plot([0.0, 0.0], [0.0, 0.0], [-axis_len, axis_len], color="black", lw=1.1, alpha=0.55)
    ax3.quiver(0.0, 0.0, 0.0, axis_len, 0.0, 0.0, color="black", lw=1.3, arrow_length_ratio=0.08)
    ax3.quiver(0.0, 0.0, 0.0, 0.0, axis_len, 0.0, color="black", lw=1.3, arrow_length_ratio=0.08)
    ax3.quiver(0.0, 0.0, 0.0, 0.0, 0.0, axis_len, color="black", lw=1.3, arrow_length_ratio=0.08)
    ax3.text(axis_len + 0.06, 0.0, 0.0, "X", fontsize=10, ha="left", va="center", color="black")
    ax3.text(0.0, axis_len + 0.06, 0.0, "Y", fontsize=10, ha="center", va="bottom", color="black")
    ax3.text(0.0, 0.0, axis_len + 0.06, "Z", fontsize=10, ha="center", va="bottom", color="black")

    # A measurement/readout axis (needle): a chosen direction of distinction.
    needle_start = 1.25 * n
    needle_dir = -1.25 * n
    ax3.quiver(
        float(needle_start[0]),
        float(needle_start[1]),
        float(needle_start[2]),
        float(needle_dir[0]),
        float(needle_dir[1]),
        float(needle_dir[2]),
        color="#542788",
        lw=2.0,
        arrow_length_ratio=0.10,
    )
    ax3.text(
        float(needle_start[0]) + 0.04,
        float(needle_start[1]) + 0.04,
        float(needle_start[2]) + 0.02,
        "Reading axis",
        fontsize=9,
        ha="left",
        va="center",
        color="#542788",
    )

    # Slice boundary on the sphere + a wavy residual ring (conceptual).
    theta_c = np.linspace(0.0, TWO_PI, 500, dtype=np.float64)
    circle = (np.cos(theta_c)[:, None] * e1[None, :]) + (np.sin(theta_c)[:, None] * e2[None, :])
    ax3.plot(circle[:, 0], circle[:, 1], circle[:, 2], color="black", lw=1.1, alpha=0.55, ls="--")
    wav = (1.0 + 0.05 * np.sin(12.0 * theta_c))[:, None] * circle
    ax3.plot(wav[:, 0], wav[:, 1], wav[:, 2], color="#1a9850", lw=1.2, alpha=0.55)

    # A representative unit state vector Ψ
    psi = np.asarray([0.62, 0.23, 0.75], dtype=np.float64)
    psi /= float(np.linalg.norm(psi))
    psi_proj = psi - float(np.dot(psi, n)) * n

    # Draw Ψ and its slice projection
    ax3.plot([0.0, float(psi[0])], [0.0, float(psi[1])], [0.0, float(psi[2])], color="#d73027", lw=3.0)
    ax3.scatter([float(psi[0])], [float(psi[1])], [float(psi[2])], s=28, c="#d73027")

    ax3.plot(
        [0.0, float(psi_proj[0])],
        [0.0, float(psi_proj[1])],
        [0.0, float(psi_proj[2])],
        color="#d73027",
        lw=2.2,
        ls="--",
    )
    ax3.plot(
        [float(psi[0]), float(psi_proj[0])],
        [float(psi[1]), float(psi_proj[1])],
        [float(psi[2]), float(psi_proj[2])],
        color="black",
        lw=1.2,
        ls=":",
    )
    ax3.scatter([float(psi_proj[0])], [float(psi_proj[1])], [float(psi_proj[2])], s=18, c="black")

    # A small in-slice spiral to suggest residual structure around the cut.
    t_sp = np.linspace(0.0, 3.5 * math.pi, 400, dtype=np.float64)
    r_sp = 0.02 + 0.18 * (t_sp / float(t_sp[-1]))
    spiral = psi_proj[None, :] + (r_sp * np.cos(t_sp))[:, None] * e1[None, :] + (r_sp * np.sin(t_sp))[:, None] * e2[None, :]
    ax3.plot(spiral[:, 0], spiral[:, 1], spiral[:, 2], color="#1a9850", lw=1.4, alpha=0.8)

    ax3.view_init(elev=18.0, azim=35.0)
    ax3.text(-1.15, 0.0, 1.05, r"Monolith ($\|\Psi\|=1$)", fontsize=10, ha="left", va="center")
    ax3.text(-0.20, -1.25, -0.95, "Observation slice", fontsize=10, ha="center", va="center", color="#4575b4")
    ax3.text(float(psi[0]) + 0.08, float(psi[1]) + 0.05, float(psi[2]) + 0.02, r"state $\Psi$", fontsize=10, color="#d73027")
    ax3.text(-1.15, -0.25, 0.85, "Orthogonal axes\n(maximal distinction)", fontsize=9, ha="left", va="center", color="black")

    # --- Right: slice coordinates + lattice mismatch + δ ---
    ax2.set_aspect("equal", adjustable="box")
    ax2.axis("off")

    # Coordinates of the projected point in the (e1,e2) basis
    p2 = np.asarray([float(np.dot(psi_proj, e1)), float(np.dot(psi_proj, e2))], dtype=np.float64)

    # A schematic lattice on the slice (conceptual readout grid)
    grid = np.arange(-1.2, 1.21, 0.4, dtype=np.float64)
    gx, gy = np.meshgrid(grid, grid)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    d = np.linalg.norm(pts - p2[None, :], axis=1)
    q2 = pts[int(np.argmin(d))]

    ax2.scatter(pts[:, 0], pts[:, 1], s=12, c="#555555", alpha=0.35, edgecolors="none")
    ax2.scatter([float(q2[0])], [float(q2[1])], s=55, c="black", zorder=5)
    ax2.scatter([float(p2[0])], [float(p2[1])], s=70, c="#d73027", marker="o", zorder=6)

    ax2.annotate(
        "",
        xy=(float(p2[0]), float(p2[1])),
        xytext=(float(q2[0]), float(q2[1])),
        arrowprops=dict(arrowstyle="->", lw=2.0, color="#d73027"),
        zorder=7,
    )
    ax2.text(float(p2[0]) + 0.08, float(p2[1]) + 0.04, r"projection", fontsize=10, color="#d73027")
    ax2.text(float(q2[0]) - 0.05, float(q2[1]) - 0.10, r"readout", fontsize=10, ha="right", va="top", color="black")
    mid = 0.5 * (p2 + q2)
    ax2.text(float(mid[0]) + 0.06, float(mid[1]) + 0.02, r"$\delta$", fontsize=12, color="#d73027")
    ax2.plot([-1.35, 1.35], [0.0, 0.0], color="black", lw=1.0, alpha=0.30)
    ax2.plot([0.0, 0.0], [-1.35, 1.35], color="black", lw=1.0, alpha=0.30)
    ax2.text(1.30, -0.08, "x", fontsize=10, ha="right", va="top", color="black", alpha=0.7)
    ax2.text(-0.08, 1.30, "y", fontsize=10, ha="right", va="top", color="black", alpha=0.7)
    ax2.text(0.0, 1.25, "Orthogonal readout + lattice mismatch", fontsize=10, ha="center", va="bottom")

    ax2.set_xlim(-1.35, 1.35)
    ax2.set_ylim(-1.35, 1.35)

    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_spiral_geodesic_diagram(out_path: Path) -> None:
    """
    Concept figure:
      - A cylinder representing (space-time) × (internal phase) geometry.
      - A geodesic-like path with no internal winding (m=0) and a tight helix
        with significant internal winding (m>0).
      - A schematic right-triangle decomposition (E, p, mc^2).
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(12.2, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 0.8])
    ax3 = fig.add_subplot(gs[0], projection="3d")
    ax = fig.add_subplot(gs[1])

    # --- Left: cylinder + paths ---
    ax3.set_box_aspect((1.0, 1.0, 1.3))
    ax3.axis("off")

    R = 1.0
    H = 2.6
    th = np.linspace(0.0, TWO_PI, 80, dtype=np.float64)
    zz = np.linspace(0.0, H, 40, dtype=np.float64)
    tt, zzm = np.meshgrid(th, zz)
    xc = R * np.cos(tt)
    yc = R * np.sin(tt)
    zc = zzm
    ax3.plot_surface(xc, yc, zc, color="#bdbdbd", alpha=0.10, edgecolor="none")

    # Path A: no internal winding (straight along the axis on the surface)
    theta0 = 0.55 * math.pi
    z_line = np.linspace(0.0, H, 200, dtype=np.float64)
    x_line = R * np.cos(theta0) * np.ones_like(z_line)
    y_line = R * np.sin(theta0) * np.ones_like(z_line)
    ax3.plot(x_line, y_line, z_line, color="#4575b4", lw=3.0)

    # Path B: tight internal helix (winding stores action off-axis)
    r = 0.62
    turns = 10.0
    t = np.linspace(0.0, TWO_PI * turns, 1500, dtype=np.float64)
    xh = r * np.cos(t)
    yh = r * np.sin(t)
    zh = H * (t / (TWO_PI * turns))
    ax3.plot(xh, yh, zh, color="#d73027", lw=2.6)

    # Direction arrow on helix
    i0, i1 = 950, 1050
    ax3.quiver(
        float(xh[i0]),
        float(yh[i0]),
        float(zh[i0]),
        float(xh[i1] - xh[i0]),
        float(yh[i1] - yh[i0]),
        float(zh[i1] - zh[i0]),
        color="#d73027",
        lw=1.8,
        arrow_length_ratio=0.25,
    )

    ax3.view_init(elev=18.0, azim=-55.0)
    ax3.text(0.0, 0.0, H + 0.15, "Spiral vs. geodesic (schematic)", fontsize=11, ha="center", va="bottom")
    ax3.text(float(x_line[0]) + 0.05, float(y_line[0]) + 0.05, 0.15, r"Light / geodesic ($m=0$)", fontsize=10, color="#4575b4")
    ax3.text(-0.95, 0.75, 1.45, r"Massive / helix ($m>0$)", fontsize=10, color="#d73027")

    ax3.set_xlim(-1.15, 1.15)
    ax3.set_ylim(-1.15, 1.15)
    ax3.set_zlim(0.0, H + 0.25)

    # --- Right: Pythagorean split diagram (interpretive) ---
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    p = 1.20
    m = 0.85
    A = (0.0, 0.0)
    B = (p, 0.0)
    C = (p, m)

    ax.plot([A[0], B[0]], [A[1], B[1]], color="black", lw=2.2)
    ax.plot([B[0], C[0]], [B[1], C[1]], color="black", lw=2.2)
    ax.plot([C[0], A[0]], [C[1], A[1]], color="black", lw=2.2)

    ax.text(0.5 * p, -0.12, r"$p$", fontsize=12, ha="center", va="top")
    ax.text(p + 0.08, 0.5 * m, r"$mc^2$", fontsize=12, ha="left", va="center")
    ax.text(0.52 * p, 0.48 * m + 0.10, r"$E$", fontsize=12, ha="center", va="bottom")
    ax.text(0.0, m + 0.25, "Local right-triangle split (interpretive)", fontsize=10, ha="left", va="bottom")

    ax.set_xlim(-0.2, p + 0.55)
    ax.set_ylim(-0.35, m + 0.55)

    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_fractal_onion_diagram(out_path: Path) -> None:
    """
    Concept figure:
      - A schematic 'fractal onion' / recursive decomposition view.
      - Three zoom levels that suggest nested Pythagorean splits.
    """
    from matplotlib.patches import Circle, Rectangle

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.2))
    for ax in axes:
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

    # Panel 1: Level 0 (unity)
    ax0 = axes[0]
    ax0.add_patch(Circle((0.0, 0.0), 1.0, facecolor="none", edgecolor="black", lw=2.2))
    ax0.plot([0.0], [0.0], "o", color="black", ms=3)
    ax0.text(0.0, 1.22, "Level 0: Unity", fontsize=11, ha="center", va="bottom")
    ax0.text(0.0, -1.28, r"$R^2$", fontsize=12, ha="center", va="top")
    zoom_box = Rectangle((0.58, 0.58), 0.32, 0.32, fill=False, edgecolor="#d73027", lw=1.8)
    ax0.add_patch(zoom_box)
    ax0.annotate("zoom", xy=(0.90, 0.90), xytext=(1.10, 1.10), arrowprops=dict(arrowstyle="->", lw=1.2, color="#d73027"), fontsize=10, color="#d73027")
    ax0.set_xlim(-1.35, 1.45)
    ax0.set_ylim(-1.35, 1.45)

    # Panel 2: Level 1 (first decomposition)
    ax1 = axes[1]
    ax1.text(0.0, 1.22, "Level 1: First split", fontsize=11, ha="center", va="bottom")
    ax1.text(0.0, -1.28, r"$R^2=x^2+y^2$", fontsize=12, ha="center", va="top")
    # A 'beaded' boundary segment
    n_beads = 12
    centers = np.linspace(-1.05, 1.05, n_beads, dtype=np.float64)
    for c in centers:
        ax1.add_patch(Circle((float(c), 0.0), 0.18, facecolor="none", edgecolor="black", lw=1.2, alpha=0.9))
    ax1.add_patch(Rectangle((-0.25, -0.22), 0.50, 0.44, fill=False, edgecolor="#4575b4", lw=1.8))
    ax1.annotate("zoom", xy=(0.25, 0.22), xytext=(0.95, 0.95), arrowprops=dict(arrowstyle="->", lw=1.2, color="#4575b4"), fontsize=10, color="#4575b4")
    ax1.set_xlim(-1.35, 1.45)
    ax1.set_ylim(-1.35, 1.45)

    # Panel 3: Level 2 (nested decomposition)
    ax2 = axes[2]
    ax2.text(0.0, 1.22, "Level 2: Nested split", fontsize=11, ha="center", va="bottom")
    ax2.text(0.0, -1.28, r"$y^2=z^2+w^2$", fontsize=12, ha="center", va="top")
    centers2 = np.linspace(-1.05, 1.05, 22, dtype=np.float64)
    for c in centers2:
        ax2.add_patch(Circle((float(c), 0.0), 0.09, facecolor="none", edgecolor="black", lw=1.0, alpha=0.9))
    ax2.set_xlim(-1.35, 1.45)
    ax2.set_ylim(-1.35, 1.45)

    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def main() -> None:
    here = Path(__file__).resolve()
    images_dir = (here.parent / "../images").resolve()
    images_dir.mkdir(parents=True, exist_ok=True)

    # Parameters tuned for quick, reproducible runs.
    n_scatter = 6000
    n_pair_max = 5000
    n_total = 4 * n_pair_max
    n_gap_samples = 20000

    phase_models = build_phase_models(n_total, seed=1)

    for model in phase_models:
        Z = build_Z(n_total, model, radial_power=1.0)

        plot_scatter(
            Z,
            title=f"HPA embedding scatter: {model.name}",
            out_path=images_dir / f"hpa_Z_scatter_{model.name}.png",
            n_plot=n_scatter,
        )

        stats = simulate_projection_gaps(
            Z=Z,
            n_pair_max=n_pair_max,
            n_samples=n_gap_samples,
            seed=2,
        )
        plot_gap_histograms(
            stats,
            title=f"Projection gap statistics (model: {model.name})",
            out_path=images_dir / f"hpa_gap_stats_{model.name}.png",
        )

        # One illustrative projection-kernel example per phase model.
        a0, b0 = 3000, 4000
        v0 = Z[a0 - 1] + Z[b0 - 1]
        plot_projection_kernel_example(
            Z=Z,
            v=v0,
            sigma=120.0,
            title=f"Soft projection kernel example (model: {model.name})",
            out_path=images_dir / f"hpa_kernel_example_{model.name}.png",
        )

    # Readout stability under window perturbation for the golden branch.
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    alpha = 1.0 / phi
    etas = np.logspace(-5, -1, 9, dtype=np.float64)
    stab = simulate_readout_stability(
        alpha=alpha,
        n_steps=4000,
        etas=etas,
        n_trials=200,
        seed=3,
    )
    plot_readout_stability(stab, out_path=images_dir / "hpa_readout_stability_golden.png")

    # A non-golden Ostrowski example: alpha = sqrt(2) - 1 = [0;2,2,2,...]
    alpha_silver = math.sqrt(2.0) - 1.0
    stab_silver = simulate_readout_stability(
        alpha=alpha_silver,
        n_steps=4000,
        etas=etas,
        n_trials=200,
        seed=4,
        encode=lambda S: ostrowski_digits_periodic(int(S), a_val=2),
    )
    plot_readout_stability(stab_silver, out_path=images_dir / "hpa_readout_stability_silver.png")

    plot_transport_duality_diagram(images_dir / "hpa_transport_duality.png")
    plot_holographic_slice_diagram(images_dir / "hpa_holographic_slice.png")
    plot_spiral_geodesic_diagram(images_dir / "hpa_spiral_geodesic.png")
    plot_fractal_onion_diagram(images_dir / "hpa_fractal_onion.png")

    print(f"Saved figures to: {images_dir}")


if __name__ == "__main__":
    main()

