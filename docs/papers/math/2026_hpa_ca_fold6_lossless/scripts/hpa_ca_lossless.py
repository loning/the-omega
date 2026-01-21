#!/usr/bin/env python3
"""Lossless HPA-CA prototype (m=6, 64→21 Fold6 kernel + explicit uplift log).

Core idea
---------
Each local 6-bit *microstate* is a binary word b∈{0,1}^6, i.e. an integer N∈{0,…,63}.
We compute Fold6(N) by greedy Zeckendorf normalization and truncation to a 6-digit
(F7..F2) window. This produces an *admissible* (no adjacent ones) 6-bit word w∈X6,
|X6|=21.

The map Fold6 is many-to-one on {0,…,63}; the missing information is the *uplift*
Δ(N) = N − V(w), where V(w)=Σ_{k=1..6} w_k F_{8-k} is the Zeckendorf value inside
this window. For m=6 and N∈{0,…,63}, one has Δ∈{0,21,34,55}.

We make the dynamics lossless by recording Δ for every block update as a time-edge label.
Given (w,Δ) we can reconstruct N = V(w)+Δ and hence the original 6-bit microstate.

Global evolution
----------------
We evolve a 1D periodic bit lattice of length L using a Margolus partition:
  - even t: blocks start at offset 0
  - odd  t: blocks start at offset 3
with block width m=6.

At each step we apply the *same* local kernel to every block:
  block_bits -> N (binary) -> (w=Fold6(N), Δ) -> write w into next state
and store Δ in an uplift table (time × block-index).

This script writes:
  - spacetime.png : (T+1)×L bitmap of the visible stable slice
  - uplift.png    : T×(L/6) image of Δ-codes (0/21/34/55)
  - density.png   : density(t)
  - psd.png       : power spectral density of density(t)
  - boxcount.png  : simple box-counting curve + estimated fractal dimension
  - data.npz      : raw arrays (states, uplift, density)

No external input is used after initialization (seeded RNG only for the t=0 state).
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt


# ---------- Fibonacci / Zeckendorf utilities ----------

def fib_sequence(n_max: int) -> List[int]:
    """Return Fibonacci numbers F[0..n_max] with F1=F2=1."""
    F = [0, 1]
    while len(F) <= n_max:
        F.append(F[-1] + F[-2])
    return F


F = fib_sequence(20)
# Window m=6 uses weights F7..F2 = 13,8,5,3,2,1
F_WEIGHTS_MSB = [F[7], F[6], F[5], F[4], F[3], F[2]]  # [13, 8, 5, 3, 2, 1]


def zeckendorf_digits(N: int, max_fib_index: int = 10) -> Dict[int, int]:
    """Greedy Zeckendorf decomposition.

    Returns digits c_i for weights F_i (i>=2), encoded as a dict {i:0/1}.
    Uniqueness is classical (Zeckendorf theorem).
    """
    if N < 0:
        raise ValueError("N must be nonnegative")

    digits = {i: 0 for i in range(2, max_fib_index + 1)}

    # find largest i with F[i] <= N
    i = max_fib_index
    while i >= 2 and F[i] > N:
        i -= 1

    while N > 0 and i >= 2:
        if F[i] <= N:
            digits[i] = 1
            N -= F[i]
            i -= 2  # skip adjacent weight
        else:
            i -= 1

    return digits


def fold6_from_int(N: int) -> np.ndarray:
    """Fold6: {0..63} -> X6 (length-6 admissible word, MSB->LSB, weights 13..1)."""
    if not (0 <= N <= 63):
        raise ValueError("Fold6 expects N in [0,63]")

    d = zeckendorf_digits(N, max_fib_index=10)
    # digits for F7..F2 correspond to indices 7..2
    bits = [d[i] for i in range(7, 1, -1)]
    return np.array(bits, dtype=np.uint8)


def zeck_value(bits6_msb: np.ndarray) -> int:
    """Zeckendorf value inside the m=6 window, using weights 13..1."""
    return int(sum(int(b) * w for b, w in zip(bits6_msb.tolist(), F_WEIGHTS_MSB)))


def int_to_bits6_msb(N: int) -> np.ndarray:
    """Binary 6-bit MSB->LSB."""
    return np.array([(N >> k) & 1 for k in range(5, -1, -1)], dtype=np.uint8)


def bits6_to_int_msb(bits6: np.ndarray) -> int:
    """Binary bits6 MSB->LSB -> integer 0..63."""
    N = 0
    for b in bits6.tolist():
        N = (N << 1) | int(b)
    return int(N)


# Precompute LUTs for speed
FOLD6_LUT = np.stack([fold6_from_int(N) for N in range(64)], axis=0)  # (64,6)
ZECKVAL_LUT = np.array([zeck_value(FOLD6_LUT[N]) for N in range(64)], dtype=np.int32)
UPLIFT_LUT = np.array([N - int(ZECKVAL_LUT[N]) for N in range(64)], dtype=np.int32)

# Uplift codes: 0,21,34,55 -> 0,1,2,3 (2 bits)
UPLIFT_VALUES = [0, 21, 34, 55]
UPLIFT_TO_CODE = {v: i for i, v in enumerate(UPLIFT_VALUES)}
CODE_TO_UPLIFT = {i: v for i, v in enumerate(UPLIFT_VALUES)}


def fold6_kernel(bits6: np.ndarray) -> Tuple[np.ndarray, int]:
    """Apply the 64→21 kernel to one 6-bit binary microstate.

    Returns:
      w: Fold6(N) as 6 bits (MSB->LSB, admissible)
      uplift: Δ(N) in {0,21,34,55}
    """
    N = bits6_to_int_msb(bits6)
    w = FOLD6_LUT[N]
    uplift = int(UPLIFT_LUT[N])
    return w.copy(), uplift


# ---------- CA evolution (Margolus partition) ----------

@dataclass
class RunResult:
    states: np.ndarray  # (T+1, L) bits
    uplift: np.ndarray  # (T, nb) uplift codes 0..3
    density: np.ndarray  # (T+1,)


def evolve(L: int, T: int, seed: int, p: float) -> RunResult:
    if L % 6 != 0:
        raise ValueError("L must be a multiple of 6 for this prototype")

    rng = np.random.default_rng(seed)
    state = (rng.random(L) < p).astype(np.uint8)

    nb = L // 6

    states = np.zeros((T + 1, L), dtype=np.uint8)
    uplift_codes = np.zeros((T, nb), dtype=np.uint8)
    density = np.zeros(T + 1, dtype=np.float64)

    states[0] = state
    density[0] = state.mean()

    for t in range(T):
        offset = 0 if (t % 2 == 0) else 3
        new_state = state.copy()

        for b in range(nb):
            start = (offset + 6 * b) % L
            idx = [(start + i) % L for i in range(6)]
            block = state[idx]

            w, uplift = fold6_kernel(block)
            new_state[idx] = w
            uplift_codes[t, b] = UPLIFT_TO_CODE[uplift]

        state = new_state
        states[t + 1] = state
        density[t + 1] = state.mean()

    return RunResult(states=states, uplift=uplift_codes, density=density)


def invert_step(state_out: np.ndarray, uplift_codes_step: np.ndarray, offset: int) -> np.ndarray:
    """Invert one global CA step, given the *output* state and uplift codes recorded during the step."""
    L = len(state_out)
    nb = L // 6
    state_in = state_out.copy()

    for b in range(nb):
        start = (offset + 6 * b) % L
        idx = [(start + i) % L for i in range(6)]
        w = state_out[idx]
        Vw = zeck_value(w)
        uplift = CODE_TO_UPLIFT[int(uplift_codes_step[b])]
        N_in = Vw + uplift
        bits_in = int_to_bits6_msb(N_in)
        state_in[idx] = bits_in

    return state_in


# ---------- Diagnostics ----------

def save_spacetime_png(states: np.ndarray, path: str) -> None:
    plt.figure(figsize=(12, 6))
    plt.imshow(states, cmap="gray", aspect="auto", interpolation="nearest")
    plt.xlabel("space index")
    plt.ylabel("time")
    plt.title("HPA-CA visible slice (Fold6 outputs)")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def save_uplift_png(uplift_codes: np.ndarray, path: str) -> None:
    plt.figure(figsize=(12, 4))
    plt.imshow(uplift_codes, cmap="viridis", aspect="auto", interpolation="nearest")
    plt.xlabel("block index (size=6)")
    plt.ylabel("time step")
    plt.title("Uplift log (codes for Δ∈{0,21,34,55})")
    cbar = plt.colorbar()
    cbar.set_ticks([0, 1, 2, 3])
    cbar.set_ticklabels(["0", "21", "34", "55"])
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def save_density_png(density: np.ndarray, path: str) -> None:
    plt.figure(figsize=(10, 3))
    plt.plot(density)
    plt.xlabel("time")
    plt.ylabel("density")
    plt.title("Density over time")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def save_psd_png(density: np.ndarray, path: str) -> None:
    x = density - density.mean()
    fft = np.fft.rfft(x)
    psd = (np.abs(fft) ** 2)
    freqs = np.fft.rfftfreq(len(x), d=1.0)

    mask = freqs > 0

    plt.figure(figsize=(10, 3))
    plt.loglog(freqs[mask], psd[mask])
    plt.xlabel("frequency")
    plt.ylabel("power")
    plt.title("Power spectral density of density(t)")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def box_counting_dimension(binary_img: np.ndarray, box_sizes: List[int]) -> Tuple[np.ndarray, np.ndarray, float]:
    """Simple box-counting on a 2D binary image (1=filled)."""
    H, W = binary_img.shape
    Ns = []
    eps = []
    for s in box_sizes:
        if s <= 0:
            continue
        H2 = (H + s - 1) // s * s
        W2 = (W + s - 1) // s * s
        img = np.zeros((H2, W2), dtype=np.uint8)
        img[:H, :W] = binary_img
        img_boxes = img.reshape(H2 // s, s, W2 // s, s)
        occ = (img_boxes.max(axis=(1, 3)) > 0)
        Ns.append(int(occ.sum()))
        eps.append(s)

    eps = np.array(eps, dtype=np.float64)
    Ns = np.array(Ns, dtype=np.float64)

    x = np.log(1.0 / eps)
    y = np.log(Ns + 1e-12)
    A = np.vstack([x, np.ones_like(x)]).T
    slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
    return eps, Ns, float(slope)


def save_boxcount_png(states: np.ndarray, path: str) -> float:
    img = states.astype(np.uint8)
    max_pow = int(np.log2(min(img.shape)))
    sizes = [2 ** k for k in range(1, max_pow - 1)]
    eps, Ns, D = box_counting_dimension(img, sizes)

    plt.figure(figsize=(6, 4))
    plt.loglog(1.0 / eps, Ns, marker="o")
    plt.xlabel("1/box size")
    plt.ylabel("occupied boxes")
    plt.title(f"Box counting (estimated D≈{D:.3f})")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()
    return D


# ---------- CLI ----------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=600, help="lattice length (multiple of 6)")
    ap.add_argument("--T", type=int, default=400, help="time steps")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed for the initial state")
    ap.add_argument("--p", type=float, default=0.5, help="initial Bernoulli(p) density")
    ap.add_argument("--outdir", type=str, default="out_hpa_ca_lossless", help="output directory")
    ap.add_argument("--check_invert", action="store_true", help="verify exact invertibility from uplift log")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    res = evolve(L=args.L, T=args.T, seed=args.seed, p=args.p)

    np.savez_compressed(
        os.path.join(args.outdir, "data.npz"),
        states=res.states,
        uplift_codes=res.uplift,
        density=res.density,
        uplift_values=np.array(UPLIFT_VALUES, dtype=np.int32),
    )

    if args.check_invert:
        ok = True
        state = res.states[-1]
        for t in range(args.T - 1, -1, -1):
            offset = 0 if (t % 2 == 0) else 3
            state = invert_step(state, res.uplift[t], offset)
            if not np.array_equal(state, res.states[t]):
                ok = False
                print(f"Invertibility check FAILED at t={t}")
                break
        if ok:
            print("Invertibility check PASSED (exact reconstruction).")

    save_spacetime_png(res.states, os.path.join(args.outdir, "spacetime.png"))
    save_uplift_png(res.uplift, os.path.join(args.outdir, "uplift.png"))
    save_density_png(res.density, os.path.join(args.outdir, "density.png"))
    save_psd_png(res.density, os.path.join(args.outdir, "psd.png"))
    D = save_boxcount_png(res.states, os.path.join(args.outdir, "boxcount.png"))

    print(f"Wrote results to: {args.outdir}")
    print(f"Final density: {res.density[-1]:.4f}")
    print(f"Box-counting D (rough): {D:.3f}")


if __name__ == "__main__":
    main()

