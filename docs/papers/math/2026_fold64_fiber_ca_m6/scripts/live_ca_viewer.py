#!/usr/bin/env python3
"""
live_ca_viewer.py

Live visualization of the outer 1D ring CA:

    x_i(t+1) = x_{i-1}(t) ⊕ x_{i+1}(t)  with ⊕ interpreted as (a+b) mod 64.

This viewer updates a rolling spacetime window in real time, and can display:
  - microstate values (0..63)
  - space-state index (0..20) induced by the m=6 low-bit projection
  - fiber index (0..3) induced by u in {0,21,34,55}

All UI strings are in English.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

import numpy as np
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class Lookups:
    w_lookup: np.ndarray  # shape (64,), values 0..20
    u_lookup: np.ndarray  # shape (64,), values 0..3


def fibonacci_upto_12() -> list[int]:
    F = [0, 1, 1]
    for _ in range(3, 13):
        F.append(F[-1] + F[-2])
    return F


def zeckendorf_digits(n: int, F: list[int], K: int = 12) -> list[int]:
    d = [0] * (K + 1)
    k = K
    while n > 0 and k >= 2:
        while k >= 2 and F[k] > n:
            k -= 1
        d[k] = 1
        n -= F[k]
        k -= 2
    d[1] = 0
    return d


def build_lookups() -> Lookups:
    F = fibonacci_upto_12()

    # Build X6 and consistent indices 0..20
    X6 = []
    for n in range(64):
        d = zeckendorf_digits(n, F, 12)
        w = (d[7], d[6], d[5], d[4], d[3], d[2])
        if w not in X6:
            X6.append(w)
    X6 = sorted(X6)
    w_to_idx = {w: i for i, w in enumerate(X6)}

    u_vals = [0, 21, 34, 55]
    u_to_idx = {u: i for i, u in enumerate(u_vals)}

    w_lookup = np.zeros(64, dtype=np.int16)
    u_lookup = np.zeros(64, dtype=np.int16)
    for n in range(64):
        d = zeckendorf_digits(n, F, 12)
        w = (d[7], d[6], d[5], d[4], d[3], d[2])
        u = d[8] * F[8] + d[9] * F[9] + d[10] * F[10]
        w_lookup[n] = w_to_idx[w]
        u_lookup[n] = u_to_idx[u]

    return Lookups(w_lookup=w_lookup, u_lookup=u_lookup)


def step_micro(x: np.ndarray) -> np.ndarray:
    left = np.roll(x, 1)
    right = np.roll(x, -1)
    return (left + right) % 64


def init_state(L: int, seed: str) -> np.ndarray:
    if seed == "impulse":
        x = np.zeros(L, dtype=np.int16)
        x[L // 2] = 1
        return x
    if seed == "random":
        rng = np.random.default_rng(0)
        return rng.integers(0, 64, size=L, dtype=np.int16)
    raise ValueError("seed must be 'impulse' or 'random'")


def to_layer(x: np.ndarray, layer: str, lookups: Lookups) -> np.ndarray:
    if layer == "micro":
        return x
    if layer == "w":
        return lookups.w_lookup[x]
    if layer == "u":
        return lookups.u_lookup[x]
    raise ValueError("layer must be one of: micro, w, u")


def layer_range(layer: str) -> tuple[int, int]:
    if layer == "micro":
        return 0, 63
    if layer == "w":
        return 0, 20
    if layer == "u":
        return 0, 3
    raise ValueError("layer must be one of: micro, w, u")


def run_live(
    L: int,
    history: int,
    fps: float,
    seed: str,
    panels: list[str],
    every: int,
) -> None:
    lookups = build_lookups()
    x = init_state(L, seed)

    # rolling buffers for each panel
    buffers: dict[str, np.ndarray] = {}
    for layer in panels:
        lo, hi = layer_range(layer)
        buf = np.full((history, L), lo, dtype=np.int16)
        buffers[layer] = buf

    plt.ion()
    fig, axes = plt.subplots(len(panels), 1, figsize=(10, 2.8 * len(panels)), dpi=120, squeeze=False)
    axes = axes[:, 0]

    ims = []
    for ax, layer in zip(axes, panels):
        lo, hi = layer_range(layer)
        im = ax.imshow(
            buffers[layer],
            aspect="auto",
            interpolation="nearest",
            vmin=lo,
            vmax=hi,
        )
        ax.set_title(f"Live CA spacetime ({layer})")
        ax.set_xlabel("Position")
        ax.set_ylabel("Time (rolling window)")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label(layer)
        ims.append(im)

    fig.tight_layout()

    t0 = time.time()
    last_print = t0
    t = 0
    frame_dt = 1.0 / max(fps, 1e-6)

    while plt.fignum_exists(fig.number):
        # update state
        x = step_micro(x)
        t += 1

        if t % max(every, 1) != 0:
            continue

        # shift and append row for each layer
        for layer, im in zip(panels, ims):
            buf = buffers[layer]
            buf[:-1] = buf[1:]
            buf[-1] = to_layer(x, layer, lookups)
            im.set_data(buf)

        fig.canvas.draw_idle()
        plt.pause(0.001)

        now = time.time()
        if now - last_print >= 20.0:
            elapsed = now - t0
            print(f"[progress] t={t} elapsed={elapsed:.1f}s", flush=True)
            last_print = now

        # basic pacing (best-effort)
        dt = time.time() - now
        if dt < frame_dt:
            time.sleep(frame_dt - dt)


def main() -> None:
    ap = argparse.ArgumentParser(description="Live viewer for the m=6 outer ring CA.")
    ap.add_argument("--L", type=int, default=256, help="Ring size (number of cells).")
    ap.add_argument("--history", type=int, default=256, help="Rolling time window height.")
    ap.add_argument("--fps", type=float, default=30.0, help="Target refresh rate (frames per second).")
    ap.add_argument("--seed", type=str, default="impulse", choices=["impulse", "random"], help="Initial condition.")
    ap.add_argument(
        "--panels",
        type=str,
        default="micro,w,u",
        help="Comma-separated panels: micro,w,u (any subset).",
    )
    ap.add_argument("--every", type=int, default=1, help="Update visualization every N steps.")
    args = ap.parse_args()

    panels = [p.strip() for p in args.panels.split(",") if p.strip()]
    if not panels:
        raise ValueError("panels must contain at least one of: micro,w,u")

    run_live(L=args.L, history=args.history, fps=args.fps, seed=args.seed, panels=panels, every=args.every)


if __name__ == "__main__":
    main()

