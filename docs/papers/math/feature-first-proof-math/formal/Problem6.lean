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

end Problem6
