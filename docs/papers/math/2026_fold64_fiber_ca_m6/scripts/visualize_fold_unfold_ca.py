#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

repo_dir = Path(__file__).resolve().parent.parent
out_dir = repo_dir / "artifacts"
out_dir.mkdir(parents=True, exist_ok=True)

F = [0, 1, 1]
for _ in range(3, 13):
    F.append(F[-1] + F[-2])

def zeckendorf_digits(n: int, K: int = 12):
    d = [0] * (K + 1)
    k = K
    while n > 0 and k >= 2:
        while k >= 2 and F[k] > n:
            k -= 1
        d[k] = 1
        n -= F[k]
        k -= 2
    return d

X6 = []
for n in range(64):
    d = zeckendorf_digits(n, 12)
    w = (d[7], d[6], d[5], d[4], d[3], d[2])
    if w not in X6:
        X6.append(w)
X6 = sorted(X6)
w_to_idx = {w: i for i, w in enumerate(X6)}

u_vals = [0, 21, 34, 55]
u_to_idx = {u: i for i, u in enumerate(u_vals)}

def fold6_w_u_idx(n: int):
    d = zeckendorf_digits(n, 12)
    w = (d[7], d[6], d[5], d[4], d[3], d[2])
    u = d[8]*F[8] + d[9]*F[9] + d[10]*F[10]
    return w_to_idx[w], u_to_idx[u]

def step(x_arr):
    left = np.roll(x_arr, 1)
    right = np.roll(x_arr, -1)
    return (left + right) % 64

def save_spacetime(matrix, title, filename, cbar_label):
    plt.figure(figsize=(10, 6), dpi=160)
    im = plt.imshow(matrix, aspect="auto", interpolation="nearest")
    plt.xlabel("Position")
    plt.ylabel("Time")
    plt.title(title)
    cbar = plt.colorbar(im)
    cbar.set_label(cbar_label)
    plt.tight_layout()
    plt.savefig(out_dir / filename)
    plt.close()

def main(L=256, T=256, seed="impulse"):
    if seed == "impulse":
        x = np.zeros(L, dtype=np.int16)
        x[L // 2] = 1
    elif seed == "random":
        rng = np.random.default_rng(0)
        x = rng.integers(0, 64, size=L, dtype=np.int16)
    else:
        raise ValueError("seed must be 'impulse' or 'random'")

    states = np.zeros((T, L), dtype=np.int16)
    states[0] = x
    for t in range(1, T):
        states[t] = step(states[t-1])

    w_lookup = np.zeros(64, dtype=np.int16)
    u_lookup = np.zeros(64, dtype=np.int16)
    for n in range(64):
        wi, ui = fold6_w_u_idx(n)
        w_lookup[n] = wi
        u_lookup[n] = ui

    w_states = w_lookup[states]
    u_states = u_lookup[states]

    save_spacetime(states, "CA spacetime (microstate 0–63)", "ca_microstate.png", "Microstate value")
    save_spacetime(w_states, "CA spacetime (space state index 0–20)", "ca_space_state.png", "Space state index")
    save_spacetime(u_states, "CA spacetime (fiber index 0–3)", "ca_fiber.png", "Fiber index (0:0,1:21,2:34,3:55)")

if __name__ == "__main__":
    main()
