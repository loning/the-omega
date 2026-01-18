# -*- coding: utf-8 -*-
"""
CAP-style bounded-family closure for the Higgs uplift interface quantum numbers.

Goal (paper-facing)
  Within an explicit bounded candidate family of scalar representations
    (SU(3), SU(2))_Y
  select a deterministic minimizer that admits the standard renormalizable Yukawa
  couplings to the already-closed chiral multiplet content (Table tab:sm_labeling_table).

Design constraints
  - Deterministic (no external parameters).
  - Only Python standard library.
  - No new external inputs beyond the paper's existing fermion quantum numbers
    (taken from exp_sm_labeling_solver, which already encodes the PDG-normalized
    hypercharge assignments used throughout the manuscript).

Outputs (LaTeX fragments)
  - sections/generated/higgs_quantum_numbers_closure_rows.tex
  - sections/generated/higgs_quantum_numbers_closure_summary.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines

import exp_sm_labeling_solver as sm


@dataclass(frozen=True)
class HiggsCand:
    su3_dim: int
    su2_dim: int
    Y_num: int  # numerator in units of 1/6 (i.e. Y = Y_num / 6)

    def y_tex(self) -> str:
        # Reduce Y_num/6 to a display fraction.
        if self.Y_num == 0:
            return "0"
        num = int(self.Y_num)
        den = 6
        g = _gcd(abs(num), den)
        num //= g
        den //= g
        if den == 1:
            return f"{num}"
        return f"{num}/{den}"

    def rep_tex(self) -> str:
        return f"$({self.su3_dim},{self.su2_dim})_{{{self.y_tex()}}}$"


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _j_from_su2_dim(d: int) -> float | None:
    # SU(2) irreps have dim = 2j+1, j in {0, 1/2, 1, ...}.
    if d <= 0:
        return None
    if (d - 1) % 1 != 0:
        return None
    return 0.5 * float(d - 1)


def _su2_contains_singlet(d_left: int, d_h: int, d_right: int) -> bool:
    """
    Check whether (left ⊗ Higgs ⊗ right) contains a singlet in SU(2),
    assuming each is an irreducible SU(2) representation specified by its dimension.

    For Yukawa terms with right a singlet (d_right=1), this reduces to
    left ⊗ Higgs contains singlet, i.e. j_left == j_h.
    """
    jl = _j_from_su2_dim(d_left)
    jh = _j_from_su2_dim(d_h)
    jr = _j_from_su2_dim(d_right)
    if jl is None or jh is None or jr is None:
        return False

    # Determine if j=0 can appear in jl ⊗ jh ⊗ jr.
    # This is equivalent to: there exists j12 in [|jl-jh|..jl+jh] such that j12 == jr.
    # Then j12 ⊗ jr contains 0 iff j12 == jr.
    # So we need jr to be achievable as an intermediate.
    jmin = abs(jl - jh)
    jmax = jl + jh
    # step is 1 since spins differ by integer steps.
    # Use integer arithmetic on doubled spins to avoid float issues.
    jl2 = int(round(2 * jl))
    jh2 = int(round(2 * jh))
    jr2 = int(round(2 * jr))
    jmin2 = abs(jl2 - jh2)
    jmax2 = jl2 + jh2
    if jr2 < jmin2 or jr2 > jmax2:
        return False
    # Parity constraint: jl2+jh2+jr2 must be even for a singlet to exist.
    return ((jl2 + jh2 + jr2) % 2) == 0


def _u1_ok(Y_left: int, Y_right: int, Y_h: int, use_conjugate: bool) -> bool:
    """
    Hypercharge invariance for Yukawa term \bar{left} * (H or H~) * right.

    Hypercharges are in units of 1/6, using PDG convention Q=T3+Y.
      Y(\bar left) = -Y_left.
      Y(H~) = -Y(H).
    Condition: -Y_left + Y_right + Y_H_eff = 0.
    """
    Y_eff = -int(Y_h) if use_conjugate else int(Y_h)
    return (-int(Y_left) + int(Y_right) + Y_eff) == 0


def _su3_ok(su3_left: int, su3_right: int, su3_h: int) -> bool:
    """
    Minimal SU(3) feasibility check for renormalizable Yukawa terms:
      - leptons are SU(3) singlets, so any scalar that couples to leptons must be SU(3) singlet.
      - quarks are SU(3) triplets; scalar singlet suffices.

    We intentionally keep this as a minimal feasibility gate aligned with the paper's
    existing SM identification interface.
    """
    if su3_left == 1 and su3_right == 1:
        return su3_h == 1
    # For quarks, allow only singlet Higgs in this minimal closure.
    if su3_left == 3 and su3_right == 3:
        return su3_h == 1
    return False


def _fermion_quantum_numbers_one_generation() -> Dict[str, Tuple[int, int, int]]:
    """
    Return dict name -> (su3_dim, su2_dim, Y_num) for generation 1,
    using the same encoding as the closed labeling solver.
    """
    out: Dict[str, Tuple[int, int, int]] = {}
    for f in sm.fermion_targets():
        if f.generation != 1:
            continue
        # Map TeX-like names to simple keys used below.
        key = f.name.replace("\\", "")
        out[key] = (int(f.su3_dim), int(f.su2_dim), int(f.Y_num))
    return out


@dataclass(frozen=True)
class YukawaReq:
    left: str
    right: str
    use_conjugate: bool  # True means H~ (hypercharge flips)
    name: str


def _requirements() -> List[YukawaReq]:
    # Minimal renormalizable Yukawa interface requirements for one generation:
    #  - up-type: Q_L H~ u_R
    #  - down-type: Q_L H d_R
    #  - charged lepton: L_L H e_R
    #  - neutrino (Dirac, since ν_R is part of the closed 18 multiplets): L_L H~ ν_R
    return [
        YukawaReq(left="Q_L", right="u_R", use_conjugate=True, name="up"),
        YukawaReq(left="Q_L", right="d_R", use_conjugate=False, name="down"),
        YukawaReq(left="L_L", right="e_R", use_conjugate=False, name="e"),
        YukawaReq(left="L_L", right="nu_R", use_conjugate=True, name="nu"),
    ]


def _cand_family() -> Iterable[HiggsCand]:
    # Bounded candidate family.
    # SU(3) dim: {1,3,8} (but feasibility gates will reject non-singlets for leptons)
    # SU(2) dim: {1,2,3}
    # Hypercharge: Y_num in [-6..+6] (units of 1/6).
    for su3_dim in (1, 3, 8):
        for su2_dim in (1, 2, 3):
            for Y_num in range(-6, 7):
                yield HiggsCand(su3_dim=su3_dim, su2_dim=su2_dim, Y_num=Y_num)


def _score(c: HiggsCand, qn: Dict[str, Tuple[int, int, int]]) -> tuple:
    """
    Deterministic CAP key:
      (missing_count, missing_mask, su3_dim, su2_dim, denom(Y), abs(num), num_sign)
    """
    reqs = _requirements()
    missing: List[int] = []
    for i, r in enumerate(reqs):
        su3_l, su2_l, y_l = qn[r.left]
        su3_r, su2_r, y_r = qn[r.right]
        ok = (
            _su3_ok(su3_l, su3_r, c.su3_dim)
            and _su2_contains_singlet(su2_l, c.su2_dim, su2_r)
            and _u1_ok(y_l, y_r, c.Y_num, use_conjugate=r.use_conjugate)
        )
        if not ok:
            missing.append(i)
    miss_count = len(missing)
    # Bitmask for deterministic tie-break.
    mask = 0
    for i in missing:
        mask |= 1 << i
    den = 6 // _gcd(abs(c.Y_num), 6) if c.Y_num != 0 else 1
    sign = -1 if c.Y_num < 0 else (1 if c.Y_num > 0 else 0)
    return (miss_count, mask, c.su3_dim, c.su2_dim, den, abs(c.Y_num), sign)


def main() -> None:
    qn = _fermion_quantum_numbers_one_generation()
    reqs = _requirements()

    # Evaluate candidates.
    rows: List[Tuple[HiggsCand, tuple]] = []
    for c in _cand_family():
        rows.append((c, _score(c, qn)))
    rows.sort(key=lambda t: t[1])

    best_c, best_key = rows[0]

    # LaTeX rows for a compact audit table (bounded family; deterministic tie-break).
    lines: List[str] = []
    # Keep the table small: include all perfect candidates (miss=0) plus a small prefix of near-misses.
    keep: List[Tuple[HiggsCand, tuple]] = []
    for c, k in rows:
        if k[0] == 0:
            keep.append((c, k))
    keep.extend(rows[:20])

    # Deduplicate while preserving order.
    seen: set[Tuple[int, int, int]] = set()
    keep2: List[Tuple[HiggsCand, tuple]] = []
    for c, k in keep:
        key = (c.su3_dim, c.su2_dim, c.Y_num)
        if key in seen:
            continue
        seen.add(key)
        keep2.append((c, k))

    for c, k in keep2:
        miss_count, mask, su3_dim, su2_dim, den, anum, sign = k
        ok = "yes" if miss_count == 0 else "no"
        terms_ok = []
        for r in reqs:
            su3_l, su2_l, y_l = qn[r.left]
            su3_r, su2_r, y_r = qn[r.right]
            terms_ok.append(
                int(
                    _su3_ok(su3_l, su3_r, c.su3_dim)
                    and _su2_contains_singlet(su2_l, c.su2_dim, su2_r)
                    and _u1_ok(y_l, y_r, c.Y_num, use_conjugate=r.use_conjugate)
                )
            )
        term_bits = "".join(str(b) for b in terms_ok)
        star = "\\textbf{min}" if c == best_c else ""
        lines.append(
            f"{c.rep_tex()} & {term_bits} & {ok} & {miss_count} & {mask} & "
            f"({su3_dim},{su2_dim},{den},{anum},{sign}) & {star} \\\\"
        )

    out_rows = generated_dir() / "higgs_quantum_numbers_closure_rows.tex"
    write_lines(out_rows, lines if lines else ["% (no rows)"])

    summary = [
        "\\noindent "
        "Bounded-family CAP closure for the scalar uplift interface quantum numbers: "
        f"the unique minimizer of the deterministic key is {best_c.rep_tex()}, "
        "i.e. a color singlet, weak doublet with hypercharge $Y=1/2$ under $Q=T_3+Y$, "
        "as it is the lowest-complexity candidate that admits the standard renormalizable "
        "Yukawa couplings (up, down, charged-lepton, and Dirac neutrino) for one generation."
    ]
    out_sum = generated_dir() / "higgs_quantum_numbers_closure_summary.tex"
    write_lines(out_sum, summary)

    print("Wrote sections/generated/higgs_quantum_numbers_closure_rows.tex")
    print("Wrote sections/generated/higgs_quantum_numbers_closure_summary.tex")


if __name__ == "__main__":
    main()

