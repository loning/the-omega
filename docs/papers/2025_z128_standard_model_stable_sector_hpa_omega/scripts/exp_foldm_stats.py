# -*- coding: utf-8 -*-
"""
Compute Fold_m statistics for a small m-sweep.

We generalize Fold_6: {0..63} -> X6 to Fold_m: {0..2^m-1} -> X_m by
Zeckendorf digits and truncation to the first m digits (padding with zeros).

For each m in a small sweep, we record:
  - |X_m| and |Im(Fold_m)|
  - degeneracy histogram over outputs (preimage size -> number of stable types)
  - min/max degeneracy values

Output (LaTeX fragment):
  - sections/generated/foldm_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple


def is_admissible_word(s: str) -> bool:
    return "11" not in s


def all_xm(m: int) -> List[str]:
    out: List[str] = []
    for bits in product("01", repeat=m):
        s = "".join(bits)
        if is_admissible_word(s):
            out.append(s)
    return sorted(out)


def fib_base_up_to(n: int) -> List[int]:
    # Zeckendorf weights [F2, F3, ...] up to the largest <= n.
    if n < 0:
        raise ValueError("n must be nonnegative.")
    F = [1, 2]
    while F[-1] <= n:
        F.append(F[-1] + F[-2])
    if n > 0:
        F.pop()
    return F


def zeckendorf_digits(n: int) -> List[int]:
    # Greedy Zeckendorf digits aligned to fib_base_up_to(n).
    if n < 0:
        raise ValueError("n must be nonnegative.")
    if n == 0:
        return []
    F = fib_base_up_to(n)
    digits = [0] * len(F)
    k = len(F) - 1
    while n > 0 and k >= 0:
        if F[k] <= n:
            digits[k] = 1
            n -= F[k]
            k -= 2
        else:
            k -= 1
    return digits


def foldm(n: int, m: int) -> str:
    digits = zeckendorf_digits(n)
    if len(digits) < m:
        digits = digits + [0] * (m - len(digits))
    w = "".join("1" if b else "0" for b in digits[:m])
    if not is_admissible_word(w):
        raise AssertionError("Fold_m output violated admissibility.")
    return w


def hist_to_tex(hist: Counter[int]) -> str:
    # Compact string "k1:v1, k2:v2, ..."
    parts = [f"{k}:{hist[k]}" for k in sorted(hist)]
    return "\\texttt{" + ", ".join(parts) + "}"


def main() -> None:
    m_list = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    rows: List[str] = []
    for m in m_list:
        Xm = all_xm(m)
        pre: Dict[str, List[int]] = defaultdict(list)
        for n in range(1 << m):
            w = foldm(n, m)
            pre[w].append(n)
        img = sorted(pre.keys())
        if set(img) != set(Xm):
            missing = sorted(set(Xm) - set(img))
            extra = sorted(set(img) - set(Xm))
            raise AssertionError(f"Image mismatch at m={m}. missing={missing[:10]}, extra={extra[:10]}")

        degeneracies = [len(pre[w]) for w in Xm]
        hist = Counter(degeneracies)
        g_min = min(degeneracies)
        g_max = max(degeneracies)
        rows.append(f"{m} & {len(Xm)} & {len(img)} & {g_min} & {g_max} & {hist_to_tex(hist)} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "foldm_sweep_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/foldm_sweep_rows.tex")


if __name__ == "__main__":
    main()



