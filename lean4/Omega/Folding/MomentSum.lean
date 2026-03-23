import Omega.Folding.MaxFiber

namespace Omega

/-- S_q(m) = Σ_{x : X m} d_m(x)^q, the q-th moment of the fiber multiplicity distribution. -/
noncomputable def momentSum (q m : Nat) : Nat :=
  ∑ x : X m, (X.fiberMultiplicity x) ^ q

/-- S_0(m) = |X_m| = paperFib(m+1). -/
theorem momentSum_zero (m : Nat) : momentSum 0 m = paperFib (m + 1) := by
  simp only [momentSum, pow_zero, Finset.sum_const, Finset.card_univ, smul_eq_mul, mul_one,
    X.card_eq_paperFib_succ]

/-- S_1(m) = 2^m (fiber multiplicities sum to the word count). -/
theorem momentSum_one (m : Nat) : momentSum 1 m = 2 ^ m := by
  simp only [momentSum, pow_one, X.fiberMultiplicity_sum_eq_pow]

/-- S_q(m) ≤ D_m^(q-1) * 2^m: the q-th moment is bounded by the max multiplicity. -/
theorem momentSum_le_max_pow (q m : Nat) (hq : 1 ≤ q) :
    momentSum q m ≤ (X.maxFiberMultiplicity m) ^ (q - 1) * 2 ^ m := by
  simp only [momentSum]
  calc ∑ x : X m, (X.fiberMultiplicity x) ^ q
      = ∑ x : X m, (X.fiberMultiplicity x) ^ (q - 1) * (X.fiberMultiplicity x) ^ 1 := by
        congr 1; ext x; rw [← pow_add]; congr 1; omega
    _ = ∑ x : X m, (X.fiberMultiplicity x) ^ (q - 1) * X.fiberMultiplicity x := by
        simp only [pow_one]
    _ ≤ ∑ x : X m, (X.maxFiberMultiplicity m) ^ (q - 1) * X.fiberMultiplicity x := by
        apply Finset.sum_le_sum; intro x _
        apply Nat.mul_le_mul_right
        exact Nat.pow_le_pow_left (X.fiberMultiplicity_le_max x) (q - 1)
    _ = (X.maxFiberMultiplicity m) ^ (q - 1) * ∑ x : X m, X.fiberMultiplicity x := by
        rw [Finset.mul_sum]
    _ = (X.maxFiberMultiplicity m) ^ (q - 1) * 2 ^ m := by
        rw [X.fiberMultiplicity_sum_eq_pow]

end Omega
