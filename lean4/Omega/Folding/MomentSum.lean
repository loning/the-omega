import Omega.Folding.MaxFiber
import Mathlib.Algebra.Order.Chebyshev

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

-- S_3 base values
theorem momentSum_three_zero : momentSum 3 0 = 1 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_three_one : momentSum 3 1 = 2 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_three_two : momentSum 3 2 = 10 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_three_three : momentSum 3 3 = 26 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_three_four : momentSum 3 4 = 88 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_three_five : momentSum 3 5 = 260 := by rw [← cMomentSum_eq]; native_decide
theorem momentSum_three_six : momentSum 3 6 = 820 := by rw [← cMomentSum_eq]; native_decide

/-- S_q is monotone in q: S_q(m) ≤ S_{q+1}(m) since d(x) ≥ 1. -/
theorem momentSum_mono_q (q m : Nat) (hq : 1 ≤ q) :
    momentSum q m ≤ momentSum (q + 1) m := by
  simp only [momentSum]
  apply Finset.sum_le_sum; intro x _
  -- d(x)^q ≤ d(x)^(q+1) since d(x) ≥ 1
  calc (X.fiberMultiplicity x) ^ q
      = (X.fiberMultiplicity x) ^ q * 1 := (Nat.mul_one _).symm
    _ ≤ (X.fiberMultiplicity x) ^ q * X.fiberMultiplicity x :=
        Nat.mul_le_mul_left _ (X.fiberMultiplicity_pos x)
    _ = (X.fiberMultiplicity x) ^ (q + 1) := (pow_succ _ _).symm

/-- S_2(m) ≥ 2^m. -/
theorem momentSum_two_ge_pow (m : Nat) : 2 ^ m ≤ momentSum 2 m := by
  rw [← momentSum_one m]; exact momentSum_mono_q 1 m (by omega)

/-- S_q(m) ≥ |X_m| = paperFib(m+1) for all q. -/
theorem momentSum_ge_card (q m : Nat) : paperFib (m + 1) ≤ momentSum q m := by
  simp only [momentSum]; rw [← X.card_eq_paperFib_succ, ← Finset.card_univ]
  rw [Finset.card_eq_sum_ones]
  apply Finset.sum_le_sum; intro x _
  exact Nat.one_le_pow q _ (X.fiberMultiplicity_pos x)

/-- Cauchy-Schwarz for fiber multiplicities: (2^m)² ≤ |X_m| · S_2(m). -/
theorem momentSum_cauchy_schwarz (m : Nat) :
    (2 ^ m) ^ 2 ≤ paperFib (m + 1) * momentSum 2 m := by
  rw [← momentSum_one, ← momentSum_zero]
  simp only [momentSum, pow_zero, pow_one, Finset.sum_const, Finset.card_univ, smul_eq_mul, mul_one]
  rw [← Finset.card_univ (α := X m)]
  exact sq_sum_le_card_mul_sum_sq

end Omega
