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
        # Deterministic ordering key for the closed ordering \prec_F in Definition~\ref{def:order_fsm}.
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


def hypercharge_square_sum_one_generation() -> int:
    """
    Return Σ (6Y)^2 over one generation of chiral fermion multiplets, with multiplicities
    (#colors * #SU2 components) for Q_L and L_L, and #colors for u_R/d_R.

    Under PDG normalization Q = T3 + Y, one obtains:
      Σ Y^2 (one generation, with multiplicities) = 10/3
    Hence Σ (6Y)^2 = 36 * 10/3 = 120.
    """
    g = 1
    fields = [f for f in fermion_targets() if f.generation == g]
    total = 0
    for f in fields:
        mult = f.su3_dim * f.su2_dim
        total += mult * (f.Y_num * f.Y_num)
    return total


def anomaly_checks_one_generation() -> Tuple[int, int, int, int]:
    """
    Basic U(1)_Y anomaly checks for one generation, expressed with integer arithmetic
    using Y_num = 6Y.

    We compute the left-chiral anomaly sums for:
      - SU(3)^2 U(1): proportional to Σ Y * T(R3) with SU(2) multiplicity,
      - SU(2)^2 U(1): proportional to Σ Y * T(R2) with color multiplicity,
      - U(1)^3: proportional to Σ Y^3 with color/SU2 multiplicities,
      - grav^2 U(1): proportional to Σ Y with multiplicities.

    This is a consistency audit; anomaly cancellation is standard SM lore
    (a neutral singlet ν_R with Y=0 does not affect it).
    """
    # Use left-chiral convention: treat right-handed fields as left-chiral conjugates
    # with hypercharge flipped in sign.
    # Store as (name, su3_dim, su2_dim, Y_num_left)
    # Q_L: (3,2) +1
    # u_R^c: (3,1) -4
    # d_R^c: (3,1) +2
    # L_L: (1,2) -3
    # e_R^c: (1,1) +6
    # nu_R^c: (1,1) 0
    content = [
        ("Q_L", 3, 2, +1),
        ("u_Rc", 3, 1, -4),
        ("d_Rc", 3, 1, +2),
        ("L_L", 1, 2, -3),
        ("e_Rc", 1, 1, +6),
        ("nu_Rc", 1, 1, 0),
    ]

    # Dynkin indices (in a common normalization): T(fundamental)=1.
    # This differs by a factor 2 from the common T=1/2 convention, but cancels in checks.
    T3 = {1: 0, 3: 1}
    T2 = {1: 0, 2: 1}

    a_su3_su3_u1 = 0
    a_su2_su2_u1 = 0
    a_u1_u1_u1 = 0
    a_grav_grav_u1 = 0
    for _, d3, d2, Y in content:
        # multiplicities for U(1) sums count components:
        mult = d3 * d2
        a_u1_u1_u1 += mult * (Y**3)
        a_grav_grav_u1 += mult * Y

        # mixed anomalies: include Dynkin indices and multiplicities.
        a_su3_su3_u1 += d2 * Y * T3[d3]
        a_su2_su2_u1 += d3 * Y * T2[d2]

    return a_su3_su3_u1, a_su2_su2_u1, a_u1_u1_u1, a_grav_grav_u1


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
        wt = w.count("1")
        r_star = V + 3 * (g - 2)
        d_pi = 1 if is_boundary_word(w) else 0
        lab, rep = mapping[w]
        rows.append(f"\\texttt{{{w}}} & {V} & {g} & {wt} & {r_star} & {d_pi} & {lab} & {rep} \\\\")

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
    # Important: do not add a trailing blank line; this fragment is included inside a tabular environment.
    out_path.write_text("\n".join(rows), encoding="utf-8")


def write_invariants_table(mapping_rows: Iterable[str]) -> None:
    # Reuse the already-computed rows for the main table, but also emit a compact invariants table.
    # This keeps the main table readable while providing an audit view.
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sm_labeling_invariants_rows.tex"

    # Each mapping row begins with: w & V & g & wt & r_* & D_pi & ...
    # Extract only the first 6 columns.
    out_lines: List[str] = []
    for line in mapping_rows:
        cols = [c.strip() for c in line.split("&")]
        if len(cols) < 6:
            continue
        out_lines.append(" & ".join(cols[:6]).rstrip() + "\\\\")
    # Important: do not add a trailing blank line; this fragment is included inside a tabular environment.
    out_path.write_text("\n".join(out_lines), encoding="utf-8")


def main() -> None:
    # Audit checks on the fermion content used by the closed labeling:
    # (i) hypercharge-square sum, (ii) anomaly cancellation (integer arithmetic).
    if hypercharge_square_sum_one_generation() != 120:
        raise AssertionError("Expected Σ(6Y)^2 = 120 per generation.")
    a1, a2, a3, ag = anomaly_checks_one_generation()
    if (a1, a2, a3, ag) != (0, 0, 0, 0):
        raise AssertionError(f"Anomaly check failed: {(a1, a2, a3, ag)}")

    rows = generate_rows()
    write_tex(rows)
    write_invariants_table(rows)
    print("Wrote sections/generated/sm_labeling_rows.tex")


if __name__ == "__main__":
    main()


