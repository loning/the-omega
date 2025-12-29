"""
Experiment B: a toy demonstration of the predictive-information-rate threshold.

This is NOT a biological model. It is a unit test for the inequality chain:
  Fdot_pred <= k_B*T_c * Idot_pred
  survival needs Fdot_pred > Wdot_diss
  => Idot_pred > Wdot_diss/(k_B*T_c)

We simulate a binary environment with tunable predictability and a simple predictor
with tunable memory, then estimate a mutual-information-rate proxy from accuracy.
"""

from __future__ import annotations

import math
import random


def simulate_environment(T: int, p_flip: float, seed: int) -> list[int]:
    """
    Binary Markov environment:
      s_{t+1} = s_t XOR Bernoulli(p_flip).
    Smaller p_flip -> more predictable.
    """
    rng = random.Random(seed)
    s = 0
    out: list[int] = []
    for _ in range(T):
        out.append(s)
        if rng.random() < p_flip:
            s ^= 1
    return out


def predictor_majority_memory(seq: list[int], m: int, seed: int) -> float:
    """
    Toy predictor with memory length m:
    predict next bit as majority of last m bits; if insufficient history, guess random.

    Returns empirical one-step-ahead accuracy.
    """
    rng = random.Random(seed)
    T = len(seq)
    if T < 2:
        return 0.0
    correct = 0
    for t in range(T - 1):
        if m <= 0 or t < m:
            pred = rng.randint(0, 1)
        else:
            window = seq[t - m + 1 : t + 1]
            ones = sum(window)
            pred = 1 if ones > (m / 2.0) else 0
        correct += int(pred == seq[t + 1])
    return correct / float(T - 1)


def mutual_information_rate_proxy_from_accuracy(acc: float) -> float:
    """
    Proxy: treat prediction as a binary symmetric channel with crossover e=1-acc.
    Then I = 1 - H2(e) bits/step (clipped at 0).
    """
    e = max(1e-12, min(1.0 - 1e-12, 1.0 - float(acc)))
    H2 = -(e * math.log2(e) + (1.0 - e) * math.log2(1.0 - e))
    return max(0.0, 1.0 - H2)


def main() -> None:
    # Units: set k_B*T_c = 1 so the threshold is simply Idot_pred > Wdot_diss.
    kBTc = 1.0
    Wdot_diss = 0.15

    T = 50_000
    memory_list = [0, 1, 2, 4, 8, 16, 32]
    for p_flip in [0.01, 0.05, 0.10, 0.20]:
        seq = simulate_environment(T=T, p_flip=p_flip, seed=0)
        print(f"\nEnvironment p_flip={p_flip:.2f} (smaller -> more predictable)")
        for m in memory_list:
            acc = predictor_majority_memory(seq, m=m, seed=1)
            Idot = mutual_information_rate_proxy_from_accuracy(acc)
            Fdot_upper = kBTc * Idot
            survives = Fdot_upper > Wdot_diss
            print(
                f"  m={m:2d}  acc={acc:.3f}  Idot~={Idot:.3f}  "
                f"Fdot_upper~={Fdot_upper:.3f}  survive? {survives}"
            )


if __name__ == "__main__":
    main()


