# -*- coding: utf-8 -*-
"""
Closed labeling solver for the Z128 stable-sector Standard Model interface.

This script generates a deterministic field-level labeling map:
  L_SM: X6 -> F_SM ∪ G_SM

where:
  - X6 is the length-6 golden-mean admissible set (no consecutive ones),
  - F_SM is the set of 18 chiral fermion multiplets (3 generations × 6 multiplets),
  - G_SM is the set of three gauge-factor connection classes {U(1), SU(2), SU(3)}.

It writes a LaTeX table-row fragment to:
  sections/generated/sm_labeling_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Iterable, List, Tuple


FIB_WEIGHTS_6 = [1, 2, 3, 5, 8, 13]  # [F2..F7] with F1=F2=1


def is_admissible_word(w: str) -> bool:
    return "11" not in w


def all_x6() -> List[str]:
    out: List[str] = []
    for bits in product("01", repeat=6):
        w = "".join(bits)
        if is_admissible_word(w):
            out.append(w)
    return sorted(out)


def is_boundary_word(w: str) -> bool:
    # wrap-around defect: w1=wm=1
    return w[0] == "1" and w[-1] == "1"


def zeckendorf_value(w: str) -> int:
    return sum(int(bit) * FIB_WEIGHTS_6[i] for i, bit in enumerate(w))


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


def fold6(n: int) -> str:
    digits = zeckendorf_digits(n)
    digits = digits + [0] * (6 - len(digits))
    w = "".join("1" if b else "0" for b in digits[:6])
    if not is_admissible_word(w):
        raise AssertionError("Fold_6 output violated admissibility.")
    return w


def degeneracy_g(w: str) -> int:
    # g(w) = |Fold_6^{-1}(w)| over N=0..63.
    pre: List[int] = []
    for n in range(64):
        if fold6(n) == w:
            pre.append(n)
    return len(pre)


@dataclass(frozen=True)
class SMField:
    generation: int
    name: str  # e.g. "Q_L", "u_R", ...
    su3_dim: int
    su2_dim: int
    Y_num: int  # hypercharge numerator in units of 1/6

    def label_tex(self) -> str:
        return f"${self.name}^{{({self.generation})}}$"

    def rep_tex(self) -> str:
        # Representations are displayed as (SU3,SU2)_Y with Y in PDG convention Q=T3+Y.
        # Y is stored as an integer multiple of 1/6.
        if self.Y_num == 0:
            y = "0"
        else:
            # reduce sign and fraction with denominator 6
            num = self.Y_num
            den = 6
            # reduce fraction
            g = _gcd(abs(num), den)
            num //= g
            den //= g
            if den == 1:
                y = f"{num}"
            else:
                y = f"{num}/{den}"
        return f"$({self.su3_dim},{self.su2_dim})_{{{y}}}$"

    def complexity_key(self) -> Tuple[int, int, int, int, str]:
        # Deterministic ordering key for assigning stable types to field targets.
        # Heuristic: colored fields are more complex than colorless; doublets more than singlets;
        # larger hypercharge magnitude increases complexity.
        y_sq_scaled = self.Y_num * self.Y_num  # scaled by 1/36; sufficient for ordering
        return (self.generation, self.su3_dim, y_sq_scaled, self.su2_dim, self.name)


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def fermion_targets() -> List[SMField]:
    # Hypercharges in PDG convention Q = T3 + Y; store as numerator of 1/6.
    # One generation:
    #   Q_L: (3,2)_{+1/6} -> +1
    #   u_R: (3,1)_{+2/3} -> +4
    #   d_R: (3,1)_{-1/3} -> -2
    #   L_L: (1,2)_{-1/2} -> -3
    #   e_R: (1,1)_{-1}   -> -6
    #   nu_R:(1,1)_{0}    -> 0
    out: List[SMField] = []
    for g in (1, 2, 3):
        out.extend(
            [
                SMField(generation=g, name="Q_L", su3_dim=3, su2_dim=2, Y_num=+1),
                SMField(generation=g, name="u_R", su3_dim=3, su2_dim=1, Y_num=+4),
                SMField(generation=g, name="d_R", su3_dim=3, su2_dim=1, Y_num=-2),
                SMField(generation=g, name="L_L", su3_dim=1, su2_dim=2, Y_num=-3),
                SMField(generation=g, name="e_R", su3_dim=1, su2_dim=1, Y_num=-6),
                SMField(generation=g, name="\\nu_R", su3_dim=1, su2_dim=1, Y_num=0),
            ]
        )
    return out


def boundary_gauge_labels() -> List[Tuple[str, str]]:
    # (label_tex, rep_tex) for the three gauge-factor connection classes.
    # Representation column is left blank (connection class).
    return [
        ("$U(1)$", "$-$"),
        ("$SU(2)$", "$-$"),
        ("$SU(3)$", "$-$"),
    ]


def stable_type_sort_key(w: str, n_hilbert: int = 3) -> Tuple[int, int, str]:
    V = zeckendorf_value(w)
    g = degeneracy_g(w)
    r_star = V + n_hilbert * (g - 2)
    return (r_star, V, w)


def generate_rows() -> List[str]:
    X6 = all_x6()
    if len(X6) != 21:
        raise AssertionError("Expected |X6|=21.")

    boundary = [w for w in X6 if is_boundary_word(w)]
    cyclic = [w for w in X6 if not is_boundary_word(w)]
    if len(boundary) != 3 or len(cyclic) != 18:
        raise AssertionError("Expected split |cyc|=18, |bdry|=3.")

    # Assign boundary types to gauge-factor connection classes by increasing V(w),
    # aligned with increasing gauge-sector dimension (abelian -> SU(2) -> SU(3)).
    boundary_sorted = sorted(boundary, key=lambda w: (zeckendorf_value(w), w))
    gauge = boundary_gauge_labels()
    if len(gauge) != 3:
        raise AssertionError("Gauge label list must have length 3.")

    # Assign cyclic types to fermion multiplets by increasing protocol depth r_*(w),
    # against a fixed, generation-respecting complexity order on fields.
    cyclic_sorted = sorted(cyclic, key=lambda w: stable_type_sort_key(w))
    fields = sorted(fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyclic_sorted) != len(fields):
        raise AssertionError("Cyclic set and fermion target list must match in size.")

    assignment: List[Tuple[str, str, str]] = []  # (w, label_tex, rep_tex)
    for w, f in zip(cyclic_sorted, fields):
        assignment.append((w, f.label_tex(), f.rep_tex()))

    # Merge cyclic + boundary into a full row set and sort by V(w) for presentation.
    mapping = {w: (lab, rep) for (w, lab, rep) in assignment}
    for w, (lab, rep) in zip(boundary_sorted, gauge):
        mapping[w] = (lab, rep)

    # Protocol-level covariance checks (auditable finite proxy):
    # We use word reversal as a minimal proxy for a protocol swap that reverses
    # the window order (a discrete avatar of reflection/traversal reversal).
    def rev(word: str) -> str:
        return word[::-1]

    for w in X6:
        w2 = rev(w)
        if w2 not in mapping:
            raise AssertionError("Reversal did not preserve X6.")
        if is_boundary_word(w2) != is_boundary_word(w):
            raise AssertionError("Reversal did not preserve cyclic/boundary split.")

    # Under reversal, gauge-sector labels should permute among themselves.
    gauge_labels = {lab for (lab, _) in gauge}
    for w in boundary:
        lab, _ = mapping[w]
        lab2, _ = mapping[rev(w)]
        if lab not in gauge_labels or lab2 not in gauge_labels:
            raise AssertionError("Gauge label set is not closed under reversal.")

    rows: List[str] = []
    for w in sorted(X6, key=lambda s: (zeckendorf_value(s), s)):
        V = zeckendorf_value(w)
        g = degeneracy_g(w)
        d_pi = 1 if is_boundary_word(w) else 0
        lab, rep = mapping[w]
        rows.append(f"\\texttt{{{w}}} & {V} & {g} & {d_pi} & {lab} & {rep} \\\\")

    # Basic consistency checks (audit-level):
    # - boundary words map to gauge labels
    # - cyclic words map to fermion labels
    for w in boundary:
        lab, _ = mapping[w]
        if "U(1)" not in lab and "SU(2)" not in lab and "SU(3)" not in lab:
            raise AssertionError("Boundary word did not map to a gauge-sector label.")
    for w in cyclic:
        lab, _ = mapping[w]
        if "Q_L" in lab or "u_R" in lab or "d_R" in lab or "L_L" in lab or "e_R" in lab or "\\nu_R" in lab:
            continue
        raise AssertionError("Cyclic word did not map to a fermion multiplet label.")

    return rows


def write_tex(rows: Iterable[str]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sm_labeling_rows.tex"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    rows = generate_rows()
    write_tex(rows)
    print("Wrote sections/generated/sm_labeling_rows.tex")


if __name__ == "__main__":
    main()


