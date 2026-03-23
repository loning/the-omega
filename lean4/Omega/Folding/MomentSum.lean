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

section Computable

/-- Computable version of momentSum using the decidable infrastructure from MaxFiber. -/
def cMomentSum (q m : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).sum (fun x => (cFiberMult x) ^ q)

theorem cMomentSum_eq (q m : Nat) : cMomentSum q m = momentSum q m := by
  simp only [cMomentSum, momentSum]
  apply Finset.sum_equiv (Equiv.refl _) (by simp) (fun x _ => by simp [cFiberMult_eq])

end Computable

-- S_2 base values via native_decide
theorem momentSum_two_zero : momentSum 2 0 = 1 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_two_one : momentSum 2 1 = 2 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_two_two : momentSum 2 2 = 6 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_two_three : momentSum 2 3 = 14 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_two_four : momentSum 2 4 = 36 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_two_five : momentSum 2 5 = 88 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_two_six : momentSum 2 6 = 220 := by rw [← cMomentSum_eq]; native_decide

end Omega
