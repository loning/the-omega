# -*- coding: utf-8 -*-
"""
Bounded counterfactual sweep: alternative deterministic maps {0..63} -> X6.

This script is an audit aid for Appendix "Folding-map counterfactuals at m=6".
It compares a small explicit family of low-complexity folding/repair rules and
records which finite invariants (image size, surjectivity, fiber degeneracy)
depend on the chosen map.

Outputs:
  - sections/generated/fold_family_sensitivity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable

from common_paths import generated_dir
from common_tex import write_lines

import exp_fold6_stats as fold


def bin6(n: int) -> str:
    return format(n, "06b")


def repair_right(word: str) -> str:
    """
    Deterministic admissibility repair on a binary word:
    scan left-to-right and whenever a substring '11' is found, flip the right bit to 0.
    """
    w = list(word)
    for i in range(len(w) - 1):
        if w[i] == "1" and w[i + 1] == "1":
            w[i + 1] = "0"
    out = "".join(w)
    if not fold.is_admissible_word(out):
        raise AssertionError("repair_right produced a non-admissible word.")
    return out


def fold_z_shift_1(n: int) -> str:
    """
    Zeckendorf-digit window shift: take digits c2..c7 (length 6), padding with zeros.
    """
    digits = fold.zeckendorf_digits(n)
    # Ensure we have at least 7 digits to read c2..c7.
    digits = digits + [0] * max(0, 7 - len(digits))
    d = digits[1:7]
    s = "".join("1" if b else "0" for b in d)
    if not fold.is_admissible_word(s):
        raise AssertionError("fold_z_shift_1 violated admissibility.")
    return s


def fold_z_rev(n: int) -> str:
    return fold.fold6(n)[::-1]


@dataclass(frozen=True)
class Candidate:
    name: str
    fn: Callable[[int], str]


def _hist_str(hist: Counter[int]) -> str:
    # Compact stable representation: "2:8,3:4,4:9"
    return ",".join(f"{k}:{hist[k]}" for k in sorted(hist))


def main() -> None:
    X6 = set(fold.all_x6())

    candidates = [
        Candidate("FoldZ", fold.fold6),
        Candidate("FoldZ-shift", fold_z_shift_1),
        Candidate("FoldZ-rev", fold_z_rev),
        Candidate("Bin-repair", lambda n: repair_right(bin6(n))),
    ]

    rows: list[str] = []
    for cand in candidates:
        pre = defaultdict(list)
        outs = []
        for n in range(64):
            w = cand.fn(n)
            if w not in X6:
                raise AssertionError(f"{cand.name}: produced non-X6 word {w} at n={n}")
            outs.append(w)
            pre[w].append(n)

        img = set(outs)
        surj = img == X6
        sizes = [len(pre[w]) for w in img]
        hist = Counter(sizes)
        gmin = min(sizes) if sizes else 0
        gmax = max(sizes) if sizes else 0
        missing = len(X6 - img)
        status = "OK" if surj else f"missing {missing}"

        rows.append(
            "\\texttt{"
            + cand.name
            + "} & "
            + str(len(img))
            + " & "
            + ("yes" if surj else "no")
            + " & "
            + str(gmin)
            + " & "
            + str(gmax)
            + " & "
            + "\\texttt{"
            + _hist_str(hist)
            + "} & "
            + status
            + " \\\\"
        )

    rows.append(r"\bottomrule")

    out_path = generated_dir() / "fold_family_sensitivity_rows.tex"
    write_lines(out_path, rows)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()


