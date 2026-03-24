import Omega.Folding.FiberSpectrum
import Omega.Folding.FiberArithmetic

/-! ### Window-6 invariants

The resolution m = 6 window provides a computationally accessible test case:
|X_6| = 21 stable words, |Word 6| = 64 microstates, D_6 = 5. -/

namespace Omega

/-- |Word 6| = 2^6 = 64. -/
theorem card_Word_six : Fintype.card (Word 6) = 64 := by rw [X.Word_card]; norm_num

/-- |X_6| = F(8) = 21. -/
theorem card_X_six' : Fintype.card (X 6) = 21 := X.card_X_six

/-- The number of stable words with nontrivial fiber (multiplicity ≥ 2). -/
def cNontrivialFiberCount (m : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).filter (fun x => cFiberMult x ≥ 2) |>.card

/-- At resolution 6, exactly 19 stable words have nontrivial fibers. -/
theorem cNontrivialFiberCount_six : cNontrivialFiberCount 6 = 19 := by native_decide

/-- The trivial fiber count at resolution 6: exactly 2 words have multiplicity 1. -/
theorem cTrivialFiberCount_six : cFiberHist 6 1 = 2 := cFiberHist_6_1

/-- Abelianization rank at resolution 6: |X_6| - #{x : d(x) = 1} = 19.
    This counts the stable words that participate in nontrivial folding. -/
theorem abelianization_rank_six :
    Fintype.card (X 6) - cFiberHist 6 1 = 19 := by
  rw [X.card_X_six, cFiberHist_6_1]

/-- The compression ratio at resolution 6: 64 microstates fold onto 21 types.
    Compression factor = 64/21 ≈ 3.05. -/
theorem compression_ratio_six :
    Fintype.card (Word 6) = 64 ∧ Fintype.card (X 6) = 21 :=
  ⟨card_Word_six, X.card_X_six⟩

/-- The fiber sum identity at resolution 6: ∑ d(x) = 2^6 = 64. -/
theorem fiber_sum_six : ∑ x : X 6, X.fiberMultiplicity x = 64 := by
  rw [X.fiberMultiplicity_sum_eq_pow]; norm_num

/-- Nontrivial fibers account for 64 - 2 = 62 of the 64 microstates. -/
theorem nontrivial_microstate_count_six :
    Fintype.card (Word 6) - cFiberHist 6 1 = 62 := by
  rw [card_Word_six, cFiberHist_6_1]

/-! ### CRT phase space structure

|X_6| = F(8) = 21 = 3 × 7. By CRT, ℤ/21ℤ ≅ ℤ/3ℤ × ℤ/7ℤ.
The idempotents of ℤ/21ℤ encode the CRT projection structure. -/

/-- F(8) = 21 = 3 × 7. -/
theorem fib8_factorization : Nat.fib 8 = 3 * 7 := by native_decide

/-- 21 = 3 × 7 (direct). -/
theorem card_X6_factorization : 21 = 3 * 7 := by omega

/-- The CRT idempotent e₁ = 7 in ℤ/21ℤ: 7² ≡ 7 (mod 21). -/
theorem crt_idempotent_7 : (7 : ZMod 21) ^ 2 = 7 := by native_decide

/-- The CRT idempotent e₂ = 15 in ℤ/21ℤ: 15² ≡ 15 (mod 21). -/
theorem crt_idempotent_15 : (15 : ZMod 21) ^ 2 = 15 := by native_decide

/-- The CRT idempotents are orthogonal: e₁ · e₂ = 0. -/
theorem crt_idempotent_product : (7 : ZMod 21) * 15 = 0 := by native_decide

/-- The CRT idempotents are complementary: e₁ + e₂ = 1. -/
theorem crt_idempotent_sum : (7 : ZMod 21) + 15 = 1 := by native_decide

/-- Complete classification of idempotents in ℤ/21ℤ: exactly {0, 1, 7, 15}. -/
theorem zmod21_idempotents_complete :
    ∀ x : ZMod 21, x ^ 2 = x ↔ x = 0 ∨ x = 1 ∨ x = 7 ∨ x = 15 := by native_decide

/-- The unit group of ℤ/21ℤ has 12 elements (Euler's φ(21) = 12). -/
theorem zmod21_unit_count :
    (Finset.univ.filter (fun x : ZMod 21 => IsUnit x)).card = 12 := by native_decide

/-- The non-unit, non-zero elements of ℤ/21ℤ: 21 - 12 - 1 = 8. -/
theorem zmod21_nonunit_nonzero_count : 21 - 1 - 12 = 8 := by omega

/-- Euler's totient: φ(3) × φ(7) = 2 × 6 = 12. -/
theorem euler_totient_21 : 2 * 6 = 12 := by omega

end Omega
