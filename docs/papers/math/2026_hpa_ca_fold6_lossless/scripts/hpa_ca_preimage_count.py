#!/usr/bin/env python3
"""Preimage counting for the symbolic pair-rule induced by HPA-CA Fold6 overlap.

We work on the *symbolic* lattice of 6-bit admissible words X6 (|X6|=21):
  - Given two adjacent symbols (w_i, w_{i+1}), form micro6 = suffix3(w_i)+prefix3(w_{i+1}),
    then apply Fold6 to get the next symbol at position i (plus an uplift label).

Visible-only evolution on the symbol lattice is deterministic:
    y_i = f(x_i, x_{i+1})
but the inverse problem is non-deterministic.

This script provides exact counting of k-step preimages for small k via a lifted-state
transfer DP on a ring of length n=L/6.

Complexity:
  - k=1: O(n * |A| * deg)
  - k=2: O(n * |A|^2 * deg)
  - In general scales like |A|^k, so keep k small (<=2 or 3).
"""

from __future__ import annotations

import argparse
from functools import lru_cache
from typing import Dict, List, Sequence, Tuple

import numpy as np

from hpa_ca_lossless import fold6_kernel


def is_admissible_no11(word: str) -> bool:
    return "11" not in word


def stable_words_x6() -> List[str]:
    words = [format(i, "06b") for i in range(64) if is_admissible_no11(format(i, "06b"))]
    words = sorted(words)
    if len(words) != 21:
        raise RuntimeError(f"Expected 21 admissible words, got {len(words)}")
    return words


def str_to_bits(s: str) -> np.ndarray:
    return np.array([0 if ch == "0" else 1 for ch in s.strip()], dtype=np.uint8)


def bits_to_str(bits: np.ndarray) -> str:
    return "".join(str(int(b)) for b in bits.tolist())


def f_pair(words: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    """Return f[a,b]=out and uplift_code[a,b] on alphabet indices."""
    A = len(words)
    idx = {w: i for i, w in enumerate(words)}
    out = np.zeros((A, A), dtype=np.int16)
    uplift_code = np.zeros((A, A), dtype=np.int8)

    uplift_to_code = {0: 0, 21: 1, 34: 2, 55: 3}

    for wl in words:
        a = idx[wl]
        suf = wl[3:6]
        for wr in words:
            b = idx[wr]
            pre = wr[0:3]
            micro = suf + pre
            out_bits, uplift = fold6_kernel(str_to_bits(micro))
            out_word = bits_to_str(out_bits)
            out[a, b] = idx[out_word]
            uplift_code[a, b] = uplift_to_code[int(uplift)]

    return out, uplift_code


def words_from_state_bits(state: np.ndarray, offset: int) -> List[str]:
    """Split a length-L bit state into n=L/6 6-bit words at given offset."""
    L = int(state.shape[0])
    if L % 6 != 0:
        raise ValueError("L must be a multiple of 6")
    if offset not in (0, 3):
        raise ValueError("offset must be 0 or 3")

    n = L // 6
    out: List[str] = []
    for b in range(n):
        start = (offset + 6 * b) % L
        idxs = [(start + i) % L for i in range(6)]
        word = "".join(str(int(state[i])) for i in idxs)
        out.append(word)
    return out


def detect_stable_offset(state: np.ndarray) -> int:
    """Heuristic: return offset in {0,3} such that all blocks are in X6 (no '11')."""
    for off in (0, 3):
        words = words_from_state_bits(state, off)
        if all(is_admissible_no11(w) for w in words):
            return off
    raise ValueError("State is not block-admissible for offset 0 or 3")


def build_succ_table(out_f: np.ndarray) -> List[List[List[int]]]:
    """succ[y][a] -> list of b such that f(a,b)=y."""
    A = int(out_f.shape[0])
    succ: List[List[List[int]]] = [[[] for _ in range(A)] for _ in range(A)]
    for a in range(A):
        for b in range(A):
            y = int(out_f[a, b])
            succ[y][a].append(b)
    return succ


def count_preimages_k1_ring(out_seq: Sequence[int], succ: List[List[List[int]]]) -> int:
    """Exact 1-step preimage count on a ring for y_i = f(x_i, x_{i+1})."""
    n = len(out_seq)
    A = len(succ)
    total = 0
    y_last = int(out_seq[-1])

    for x0 in range(A):
        counts = {x0: 1}
        for i in range(n - 1):
            y = int(out_seq[i])
            new_counts: Dict[int, int] = {}
            for xi, c in counts.items():
                for xip1 in succ[y][xi]:
                    new_counts[xip1] = new_counts.get(xip1, 0) + c
            counts = new_counts
            if not counts:
                break
        if not counts:
            continue

        for x_last, c in counts.items():
            # closure: y_{n-1} = f(x_{n-1}, x0)
            if x0 in succ[y_last][x_last]:
                total += c
    return int(total)


def tuple_to_index(tup: Tuple[int, ...], base: int) -> int:
    idx = 0
    mul = 1
    for x in tup:
        idx += int(x) * mul
        mul *= base
    return idx


def index_to_tuple(idx: int, k: int, base: int) -> Tuple[int, ...]:
    out = []
    x = int(idx)
    for _ in range(k):
        out.append(x % base)
        x //= base
    return tuple(out)


def count_preimages_k_ring(out_seq: Sequence[int], succ: List[List[List[int]]], k: int) -> int:
    """Exact k-step preimage count (small k) via lifted-state DP on a ring.

    Constraints:
      For t=0..k-2:  x^{t+1}_i = f(x^{t}_i, x^{t}_{i+1})
      For t=k-1:     out_i     = f(x^{k-1}_i, x^{k-1}_{i+1})

    We lift the per-site state to a tuple:
      A_i = (x^0_i, x^1_i, ..., x^{k-1}_i) in A^k
    and enforce local constraints between A_i and A_{i+1}.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    if k == 1:
        return count_preimages_k1_ring(out_seq, succ)

    A = len(succ)
    S = A ** k
    n = len(out_seq)

    @lru_cache(maxsize=None)
    def next_states(a_idx: int, y_out: int) -> Tuple[int, ...]:
        a_tup = index_to_tuple(a_idx, k=k, base=A)  # (x^0_i,...,x^{k-1}_i)

        options: List[List[int]] = []
        for t in range(k - 1):
            # a_tup[t+1] = f(a_tup[t], b_tup[t])  =>  b_tup[t] in succ[a_tup[t+1]][a_tup[t]]
            options.append(succ[int(a_tup[t + 1])][int(a_tup[t])])
        # output constraint for top layer:
        options.append(succ[int(y_out)][int(a_tup[k - 1])])

        if any(len(opt) == 0 for opt in options):
            return tuple()

        # Cartesian product over options to build b_tup
        states: List[int] = []
        if k == 2:
            for b0 in options[0]:
                for b1 in options[1]:
                    states.append(tuple_to_index((b0, b1), base=A))
        elif k == 3:
            for b0 in options[0]:
                for b1 in options[1]:
                    for b2 in options[2]:
                        states.append(tuple_to_index((b0, b1, b2), base=A))
        else:
            # Generic recursion (may be slow for k>3)
            def rec_build(t: int, acc: List[int]) -> None:
                if t == k:
                    states.append(tuple_to_index(tuple(acc), base=A))
                    return
                for b in options[t]:
                    acc.append(int(b))
                    rec_build(t + 1, acc)
                    acc.pop()

            rec_build(0, [])

        return tuple(states)

    total = 0
    y_last = int(out_seq[-1])

    for a0 in range(S):
        counts = {a0: 1}
        for i in range(n - 1):
            y = int(out_seq[i])
            new_counts: Dict[int, int] = {}
            for ai, c in counts.items():
                for bi in next_states(ai, y):
                    new_counts[bi] = new_counts.get(bi, 0) + c
            counts = new_counts
            if not counts:
                break
        if not counts:
            continue

        for a_last, c in counts.items():
            # closure at site n-1 uses y_last
            if a0 in next_states(a_last, y_last):
                total += c

    return int(total)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=str, default="", help="optional .npz produced by hpa_ca_lossless.py")
    ap.add_argument("--t", type=int, default=-1, help="time index in data (default: last)")
    ap.add_argument("--offset", type=int, default=-1, help="0 or 3; default: auto-detect")
    ap.add_argument("--k", type=int, default=1, help="number of steps to invert (symbolic count)")
    ap.add_argument("--max_k_warn", type=int, default=3, help="warn if k exceeds this")
    ap.add_argument(
        "--assume_alternating_offsets",
        action="store_true",
        help="if set and --offset not given, choose offset by t parity (HPA-CA convention)",
    )
    args = ap.parse_args()

    words = stable_words_x6()
    idx = {w: i for i, w in enumerate(words)}
    out_f, _upl = f_pair(words)
    succ = build_succ_table(out_f)

    if args.data:
        data = np.load(args.data)
        states = data["states"]
        t = int(args.t) if args.t >= 0 else (states.shape[0] - 1)
        state = states[t].astype(np.uint8)
        if args.offset in (0, 3):
            offset = int(args.offset)
        elif args.assume_alternating_offsets:
            # In our HPA-CA convention, step 0 uses offset=0, step 1 uses offset=3, ...
            # The output state at time t is block-admissible in the offset used at step t-1.
            if t <= 0:
                raise SystemExit("t must be >= 1 when using --assume_alternating_offsets")
            offset = 0 if ((t - 1) % 2 == 0) else 3
        else:
            offset = detect_stable_offset(state)

        out_words = words_from_state_bits(state, offset=offset)
        if not all(w in idx for w in out_words):
            raise SystemExit("Output slice contains non-admissible 6-bit words; choose correct offset or time.")
        out_seq = [idx[w] for w in out_words]
        print(f"Loaded state at t={t}, detected offset={offset}, n={len(out_seq)}")
    else:
        raise SystemExit("Please provide --data path/to/data.npz for now.")

    if args.k > args.max_k_warn:
        print(f"Warning: k={args.k} may be expensive (alphabet size grows as 21^k).")

    count = count_preimages_k_ring(out_seq, succ, k=int(args.k))
    print(f"k-step symbolic preimage count (k={args.k}): {count}")


if __name__ == "__main__":
    main()

