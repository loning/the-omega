import Omega.Folding.EWTTelescope

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- Phase 152: S_3 recurrence definitions + bounded verification
-- ══════════════════════════════════════════════════════════════

/-- Cross-correlation-squared high at previous shift F_{m+1}: Σ ewc(n)² · ewc(n + F_{m+1}). -/
def crossCorrSqHighPrev (m : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)),
    exactWeightCount m n ^ 2 * exactWeightCount m (n + Nat.fib (m + 1))

/-- Cross-correlation-squared low at previous shift F_{m+1}: Σ ewc(n) · ewc(n + F_{m+1})². -/
def crossCorrSqLowPrev (m : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)),
    exactWeightCount m n * exactWeightCount m (n + Nat.fib (m + 1)) ^ 2

/-- tripleCollisionClass(fff) = exactTripleCollisionClass(fff) since weights < F_{m+3}
    means mod is identity. -/
theorem tripleCollisionClass_fff_eq_exact (m : Nat) :
    (tripleCollisionClass m false false false).card =
    (exactTripleCollisionClass m false false false).card := by
  congr 1; ext ⟨v1, v2, v3⟩
  simp only [tripleCollisionClass, exactTripleCollisionClass, Finset.mem_filter,
    Finset.mem_univ, true_and, Bool.false_eq_true, ite_false, Nat.add_zero]
  have h1 : weight v1 < Nat.fib (m + 3) := X.weight_lt_fib v1
  have h2 : weight v2 < Nat.fib (m + 3) := X.weight_lt_fib v2
  have h3 : weight v3 < Nat.fib (m + 3) := X.weight_lt_fib v3
  constructor
  · intro ⟨hmod1, hmod2⟩
    rw [Nat.mod_eq_of_lt h1, Nat.mod_eq_of_lt h2] at hmod1
    rw [Nat.mod_eq_of_lt h2, Nat.mod_eq_of_lt h3] at hmod2
    exact ⟨hmod1, hmod2⟩
  · intro ⟨h12, h23⟩
    rw [Nat.mod_eq_of_lt h1, Nat.mod_eq_of_lt h2, Nat.mod_eq_of_lt h3]
    exact ⟨h12, h23⟩

/-- tripleCollisionClass(ttt) = exactTripleCollisionClass(ttt) since +F cancels in mod. -/
theorem tripleCollisionClass_ttt_eq_exact (m : Nat) :
    (tripleCollisionClass m true true true).card =
    (exactTripleCollisionClass m true true true).card := by
  congr 1; ext ⟨v1, v2, v3⟩
  simp only [tripleCollisionClass, exactTripleCollisionClass, Finset.mem_filter,
    Finset.mem_univ, true_and, ite_true]
  -- Both conditions reduce to: wt(vi) + F mod F' = wt(vj) + F mod F'
  -- ↔ (wt(vi) + F) mod F' = (wt(vj) + F) mod F'
  -- ↔ wt(vi) + F = wt(vj) + F (when both < 2·F')
  have hlt : ∀ w : Word m, weight w + Nat.fib (m + 2) < 2 * Nat.fib (m + 3) := by
    intro w; have := X.weight_lt_fib w
    have := Nat.fib_mono (show m + 2 ≤ m + 3 by omega)
    omega
  constructor
  · -- (→) mod → exact: cancel F_{m+2} from mod equality
    intro ⟨h1, h2⟩
    have hmod1 : weight v1 % Nat.fib (m + 3) = weight v2 % Nat.fib (m + 3) :=
      Nat.ModEq.add_right_cancel' (Nat.fib (m + 2)) h1
    have hmod2 : weight v2 % Nat.fib (m + 3) = weight v3 % Nat.fib (m + 3) :=
      Nat.ModEq.add_right_cancel' (Nat.fib (m + 2)) h2
    rw [Nat.mod_eq_of_lt (X.weight_lt_fib v1), Nat.mod_eq_of_lt (X.weight_lt_fib v2)] at hmod1
    rw [Nat.mod_eq_of_lt (X.weight_lt_fib v2), Nat.mod_eq_of_lt (X.weight_lt_fib v3)] at hmod2
    exact ⟨by omega, by omega⟩
  · -- (←) exact → mod: direct congruence
    intro ⟨h1, h2⟩
    exact ⟨congr_arg (· % Nat.fib (m + 3)) h1,
           congr_arg (· % Nat.fib (m + 3)) h2⟩

/-- S_3(m+1) decomposition verified for m ≤ 5. -/
theorem momentSum_three_succ_decomposition_bounded (m : Nat) (hm : m ≤ 5) :
    momentSum 3 (m + 1) =
    2 * exactWeightTriple m + 3 * crossCorrSqHigh m + 3 * crossCorrSqLow m +
    3 * crossCorrSqHighPrev m + 3 * crossCorrSqLowPrev m := by
  interval_cases m <;> (rw [← cMomentSum_eq]; native_decide)

/-- S_3(m+1) in terms of EWT(m+1) and prev cross-correlations, verified for m ≤ 5. -/
theorem momentSum_three_succ_ewt_form_bounded (m : Nat) (hm : m ≤ 5) :
    momentSum 3 (m + 1) = exactWeightTriple (m + 1) +
    3 * crossCorrSqHighPrev m + 3 * crossCorrSqLowPrev m := by
  rw [exactWeightTriple_succ]; linarith [momentSum_three_succ_decomposition_bounded m hm]

end Omega
