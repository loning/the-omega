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
    epsilon: float,
    title: str,
    out_path: Path,
) -> None:
    r = float(abs(v))
    W = int(math.ceil(6.0 * epsilon))
    left = max(1, int(math.floor(r - W)))
    right = min(len(Z), int(math.ceil(r + W)))
    n = np.arange(left, right + 1, dtype=np.int32)
    d = np.abs(Z[left - 1 : right] - v)
    d2 = d * d
    d2_min = float(np.min(d2))
    w = np.exp(-(d2 - d2_min) / (epsilon * epsilon))
    p = w / np.sum(w)

    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.plot(n, p, linewidth=1.1, color="#2c7fb8")
    ax.set_yscale("log")
    ax.set_xlabel(r"candidate $c$")
    ax.set_ylabel(r"$\pi_\varepsilon(c\mid v)$ (log scale)")
    ax.set_title(title)
    ax.grid(True, which="both", linewidth=0.3, alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=250)
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
            epsilon=120.0,
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

    print(f"Saved figures to: {images_dir}")


if __name__ == "__main__":
    main()

