# -*- coding: utf-8 -*-
"""
Compute the folding map Fold_6: {0..63} -> X6 via Zeckendorf digits (Fibonacci base).

Reproduces:
  - surjectivity onto X6 (size 21)
  - preimage-size (degeneracy) histogram

It optionally writes small LaTeX table-row fragments into sections/generated/.
Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import product
from pathlib import Path


def is_admissible_word(s: str) -> bool:
    return "11" not in s


def all_x6() -> list[str]:
    out = []
    for bits in product("01", repeat=6):
        s = "".join(bits)
        if is_admissible_word(s):
            out.append(s)
    return sorted(out)


def fib_base_up_to(n: int) -> list[int]:
    """
    Zeckendorf weights for Fibonacci coding (standard Fibonacci numbers):
      weights are F2, F3, F4, ... where F1=F2=1 and F_{n+2}=F_{n+1}+F_n.

    Returns [F2, F3, ..., F_{K}] (as integers) with F_{K} <= n < F_{K+1} (for n>0).
    For n=0 returns [F2, F3] = [1, 2].
    """
    if n < 0:
        raise ValueError("n must be nonnegative.")
    F = [1, 2]
    while F[-1] <= n:
        F.append(F[-1] + F[-2])
    # last element is > n (unless n=0)
    if n > 0:
        F.pop()
    return F


def zeckendorf_digits(n: int) -> list[int]:
    """
    Greedy Zeckendorf digits for n in Fibonacci weights (F2=1,F3=2,F4=3,...).
    Returns digits aligned with [F2..FK], i.e. len(digits)=K-1.
    """
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
            k -= 2  # enforce no adjacent ones
        else:
            k -= 1
    return digits


def fold6(n: int) -> str:
    """
    Fold_6(n) = first 6 Zeckendorf digits (c1..c6), padding with zeros.
    """
    digits = zeckendorf_digits(n)  # aligned with F1..FK (K may be <6)
    digits = digits + [0] * (6 - len(digits))
    digits6 = digits[:6]
    s = "".join("1" if b else "0" for b in digits6)
    if not is_admissible_word(s):
        raise AssertionError("Fold_6 output violated admissibility.")
    return s


def write_tex_hist(deg_hist: Counter[int]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Degeneracy histogram rows: size & count \\
    rows = []
    for k in sorted(deg_hist):
        rows.append(f"{k} & {deg_hist[k]} \\\\")
    (out_dir / "fold6_degeneracy_rows.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")


def zeckendorf_value_of_word(w: str) -> int:
    """
    V(w) = sum_{k=1}^6 w_k F_{k+1}, with Fibonacci numbers F1=F2=1.
    This corresponds to weights [F2..F7] = [1,2,3,5,8,13].
    """
    weights = [1, 2, 3, 5, 8, 13]
    return sum(int(bit) * weights[i] for i, bit in enumerate(w))


def write_fold6_full_table(preimage: dict[str, list[int]]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for w in sorted(preimage.keys()):
        v = zeckendorf_value_of_word(w)
        ns = preimage[w]
        s_set = "\\{ " + ", ".join(str(x) for x in ns) + " \\}"
        rows.append(f"\\texttt{{{w}}} & {v} & ${s_set}$ \\\\")

    # Avoid trailing blank lines: a blank line inside tabular can break \bottomrule (\noalign).
    (out_dir / "fold6_full_table_rows.tex").write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    X6 = all_x6()
    outputs = []
    preimage = defaultdict(list)
    for n in range(64):
        y = fold6(n)
        outputs.append(y)
        preimage[y].append(n)

    out_set = sorted(set(outputs))
    print("|X6|:", len(X6))
    print("|Im(Fold_6)|:", len(out_set))
    if set(out_set) != set(X6):
        missing = sorted(set(X6) - set(out_set))
        extra = sorted(set(out_set) - set(X6))
        raise AssertionError(f"Image mismatch. missing={missing}, extra={extra}")

    sizes = [len(preimage[y]) for y in out_set]
    deg_hist = Counter(sizes)
    print("degeneracy histogram (preimage size -> number of outputs):", dict(sorted(deg_hist.items())))

    # Print a compact mapping summary
    print("\nFold_6 preimages (sorted by output word):")
    for y in out_set:
        ns = preimage[y]
        print(y, ":", ns)

    write_tex_hist(deg_hist)
    write_fold6_full_table(preimage)
    print("Wrote sections/generated/fold6_degeneracy_rows.tex and fold6_full_table_rows.tex")


if __name__ == "__main__":
    main()


