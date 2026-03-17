import Mathlib

/-!
  ## Problem 6 (partial): RDI counterexample arithmetic

  For the epsilon-light sets conjecture (Q6), the Resistance-Degree
  spectral Inequality (RDI) was a candidate proof route asserting
  λ_max(M(S)) ≤ C · max_u w_S(u) for a universal constant C.

  This file formalizes the arithmetic core of the counterexample
  (Proposition q6-rdi-false in the paper): for the graph family G_k,
  the ratio (k+4)/5 is unbounded, so no universal C exists.

  The full Q6 analysis (unconditional √(εn/2) bound, Spectral Radius
  Conjecture, seven special graph families) is proved on paper only.
-/

namespace Problem6

open scoped BigOperators

/-- The numerator of the ratio in the RDI counterexample family G_k. -/
def ratioNumerator (k : Nat) : Nat := k + 4

/-- For any proposed constant C, there exists k such that (k+4) > 5C,
    showing the ratio (k+4)/5 exceeds C. -/
theorem ratio_unbounded_nat (C : Nat) :
    Exists (fun k : Nat => ratioNumerator k > 5 * C) := by
  refine Exists.intro (5 * C + 1) ?_
  have h1 : 5 * C < 5 * C + 1 := Nat.lt_succ_self (5 * C)
  have h2 : 5 * C + 1 <= 5 * C + 1 + 4 := Nat.le_add_right (5 * C + 1) 4
  exact
    Nat.lt_of_lt_of_le h1
      (by
        simpa [ratioNumerator, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm] using h2)

/-- No universal constant C can bound ratioNumerator(k) ≤ 5C for all k.
    This is the formal arithmetic kernel of Proposition q6-rdi-false. -/
theorem no_uniform_bound_nat :
    Not (Exists (fun C : Nat => forall k : Nat, ratioNumerator k <= 5 * C)) := by
  intro h
  cases h with
  | intro C hC =>
      cases ratio_unbounded_nat C with
      | intro k hk =>
          exact Nat.not_le_of_lt hk (hC k)

/-!
  ## Additional formally verified bridge lemmas (paper Part VII / Part IX)

  The lemmas below formalize deterministic algebraic parts of the Q6
  bridge chain used in the manuscript:
  - one-step minimal bridge (ratio averaging)
  - stuck-size algebra inequality
  - Beatty/Floor unit-debt arithmetic
  - golden explicit discrepancy post-processing
-/

/-- One-step averaging lemma: if the sum of ratios is at most `k`,
then at least one ratio is at most `1`. -/
theorem exists_feasible_bin_of_sum_ratios_le
    {k : Nat}
    (hk : 0 < k)
    (w g : Fin k → Real)
    (hg : ∀ i, 0 < g i)
    (hsum : (∑ i, w i / g i) ≤ k) :
    ∃ i, w i ≤ g i := by
  by_contra hnone
  have hgt : ∀ i, 1 < w i / g i := by
    intro i
    have hwi : g i < w i := by
      exact lt_of_not_ge (fun hle => hnone ⟨i, hle⟩)
    exact (one_lt_div (hg i)).2 hwi
  have hsumStrict :
      (∑ i : Fin k, (1 : Real)) < (∑ i : Fin k, w i / g i) := by
    refine Finset.sum_lt_sum ?_ ?_
    · intro i hi
      exact le_of_lt (hgt i)
    · refine ⟨⟨0, hk⟩, by simp, hgt ⟨0, hk⟩⟩
  have hkAsReal : (∑ i : Fin k, (1 : Real)) = k := by
    simp
  have hklt : (k : Real) < (∑ i : Fin k, w i / g i) := by
    simpa [hkAsReal] using hsumStrict
  linarith

/-- Formal one-step non-stuck consequence used by the minimal bridge:
if `sum_i w_i/(eps-lam_i) <= k` and all gaps are positive, then
some bin satisfies `lam_i + w_i <= eps`. -/
theorem minimal_bridge_step
    {k : Nat}
    (hk : 0 < k)
    (eps : Real)
    (lam w : Fin k → Real)
    (hgap : ∀ i, lam i < eps)
    (hsum : (∑ i, w i / (eps - lam i)) ≤ k) :
    ∃ i, lam i + w i ≤ eps := by
  have hpos : ∀ i, 0 < eps - lam i := by
    intro i
    linarith [hgap i]
  rcases exists_feasible_bin_of_sum_ratios_le hk w (fun i => eps - lam i) hpos hsum with
    ⟨i, hi⟩
  refine ⟨i, ?_⟩
  linarith

/-- Algebraic stuck-size inequality:
from `(s0 - s) * c < s * tau` with `tau >= 0`, `c > 0`,
deduce `s > (c/(tau+c)) * s0`. -/
theorem stuck_size_lower_bound
    {s0 s tau c : Real}
    (htau : 0 ≤ tau)
    (hc : 0 < c)
    (hineq : (s0 - s) * c < s * tau) :
    s > (c / (tau + c)) * s0 := by
  have hden : 0 < tau + c := by linarith
  have hmain : s0 * c < s * (tau + c) := by
    nlinarith [hineq]
  have hdiv : s0 * c / (tau + c) < s := by
    have hden' : tau + c ≠ 0 := by linarith
    field_simp [hden']
    nlinarith [hmain]
  have hrew : s0 * c / (tau + c) = (c / (tau + c)) * s0 := by
    ring
  simpa [hrew] using hdiv

/-- Beatty/Floor unit-debt arithmetic kernel:
for `0 <= theta < 1`, floor-shift error is at most `1` in absolute value. -/
theorem beatty_floor_unit_error
    (x theta : Real)
    (htheta0 : 0 ≤ theta)
    (htheta1 : theta < 1) :
    abs ((Int.floor (x + theta) : Real) - x) ≤ 1 := by
  have hlow : (Int.floor (x + theta) : Real) ≤ x + theta := Int.floor_le (x + theta)
  have hhigh : x + theta < (Int.floor (x + theta) : Real) + 1 := Int.lt_floor_add_one (x + theta)
  have hupper : (Int.floor (x + theta) : Real) - x ≤ 1 := by
    linarith
  have hlower : -1 ≤ (Int.floor (x + theta) : Real) - x := by
    linarith
  exact abs_le.mpr ⟨hlower, hupper⟩

/-- Endpoint identity used in the Beatty unit-debt construction:
`floor(m + theta) = m` for natural `m` and `0 <= theta < 1`. -/
theorem beatty_floor_nat_endpoint
    (m : Nat)
    (theta : Real)
    (htheta0 : 0 ≤ theta)
    (htheta1 : theta < 1) :
    Int.floor ((m : Real) + theta) = (m : Int) := by
  refine Int.floor_eq_iff.mpr ?_
  have hm : ((m : Int) : Real) = (m : Real) := by
    norm_num
  constructor
  · simpa [hm] using htheta0
  · have h' : (m : Real) + theta < (m : Real) + 1 := by
      linarith
    simpa [hm] using h'

/-- Golden explicit discrepancy post-processing:
from a standard bound `D <= (n+2)/M` and index estimate `n <= 1+t`,
derive `D <= (3 + ceil t)/M` for `M > 0`. -/
theorem golden_explicit_from_standard
    (D M n t : Real)
    (hM : 0 < M)
    (hstd : D ≤ (n + 2) / M)
    (hn : n ≤ 1 + t) :
    D ≤ (3 + (Int.ceil t : Real)) / M := by
  have hceil : t ≤ (Int.ceil t : Real) := Int.le_ceil t
  have hn2 : n + 2 ≤ 3 + (Int.ceil t : Real) := by
    linarith
  have hfrac : (n + 2) / M ≤ (3 + (Int.ceil t : Real)) / M := by
    have hM' : M ≠ 0 := by linarith
    field_simp [hM']
    nlinarith [hn2]
  exact le_trans hstd hfrac

end Problem6
