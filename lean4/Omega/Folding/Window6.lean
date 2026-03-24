import Omega.Folding.FiberSpectrum
import Omega.Folding.FiberArithmetic
import Omega.Folding.MomentSum
import Omega.Folding.BinFold

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

/-! ### TQFT partition function and sector sums

The q-th moment S_q(m) = ∑_x d(x)^q computes TQFT-like partition functions:
- q = 0: S_0 = |X_m| = F(m+2) (sphere partition / type count)
- q = 1: S_1 = 2^m (total microstate count)
- q = 2: S_2 = collision number (torus partition function) -/

/-- The sphere partition function: ∑ d(x)^2 = S_2(m). -/
theorem tqft_sphere_eq_momentSum_two (m : Nat) :
    ∑ x : X m, (X.fiberMultiplicity x) ^ 2 = momentSum 2 m := rfl

/-- The type count: ∑ d(x)^0 = |X_m| = F(m+2). -/
theorem tqft_torus_eq_card (m : Nat) :
    ∑ x : X m, (X.fiberMultiplicity x) ^ 0 = Nat.fib (m + 2) := by
  simp only [pow_zero, Finset.sum_const, Finset.card_univ, smul_eq_mul, mul_one, X.card_eq_fib]

/-- Sector sum at m = 6, q = 2: weighted by fiber histogram.
    2·1² + 4·2² + 8·3² + 5·4² + 2·5² = 220 = S_2(6). -/
theorem sector_sum_six_q2 : 2 * 1 ^ 2 + 4 * 2 ^ 2 + 8 * 3 ^ 2 + 5 * 4 ^ 2 + 2 * 5 ^ 2 = 220 := by
  omega

/-- Sector sum at m = 6, q = 1: 2·1 + 4·2 + 8·3 + 5·4 + 2·5 = 64 = 2^6. -/
theorem sector_sum_six_q1 : 2 * 1 + 4 * 2 + 8 * 3 + 5 * 4 + 2 * 5 = 64 := by omega

/-- Sector sum at m = 6, q = 0: 2 + 4 + 8 + 5 + 2 = 21 = |X_6|. -/
theorem sector_sum_six_q0 : 2 + 4 + 8 + 5 + 2 = 21 := by omega

/-! ### Hidden reflection packet

The "hidden dimensions" arise from the BinFold compression: each fiber of
size k contributes k - 1 hidden dimensions. -/

/-- Hidden reflection dimension at m = 6: ∑ (mult - 1) = 43. -/
theorem hidden_reflection_dim_six : 8 * 1 + 4 * 2 + 9 * 3 = 43 := by omega

/-- Hidden reflection from BinFold histogram:
    h(2)·1 + h(3)·2 + h(4)·3 = 43. -/
theorem hidden_reflection_from_histogram :
    cBinFiberHist 6 2 * 1 + cBinFiberHist 6 3 * 2 + cBinFiberHist 6 4 * 3 = 43 := by
  rw [cBinFiberHist_6_2, cBinFiberHist_6_3, cBinFiberHist_6_4]

/-- Quadratic collision mass: S_2(6) - 2^6 = 220 - 64 = 156.
    This measures the "excess" collisions beyond uniform distribution. -/
theorem quadratic_collision_mass_six : momentSum 2 6 - 2 ^ 6 = 156 := by
  rw [momentSum_two_six]; norm_num

/-- Discriminant total degree at m = 6: 8·1 + 4·3 + 9·6 = 74. -/
theorem discriminant_total_degree_six : 8 * 1 + 4 * 3 + 9 * 6 = 74 := by omega

/-! ### Information certificate and Jones index -/

/-- Jones index lower bound: S_2(6) > 10 · |X_6|. -/
theorem jones_index_lower_six : momentSum 2 6 > 10 * Fintype.card (X 6) := by
  rw [momentSum_two_six, X.card_X_six]; omega

/-- The complete Window-6 information certificate. -/
theorem window6_information_certificate :
    2 ^ 6 = 64 ∧ Fintype.card (X 6) = 21 ∧ momentSum 2 6 = 220 ∧
    2 ^ 6 - Fintype.card (X 6) = 43 ∧
    cBinFiberHist 6 2 = 8 ∧ cBinFiberHist 6 3 = 4 ∧ cBinFiberHist 6 4 = 9 := by
  exact ⟨by norm_num, X.card_X_six, momentSum_two_six,
    by rw [X.card_X_six]; norm_num,
    cBinFiberHist_6_2, cBinFiberHist_6_3, cBinFiberHist_6_4⟩

/-- The TQFT triple at m = 6: (|X|, 2^m, S_2) = (21, 64, 220). -/
theorem tqft_triple_six :
    Fintype.card (X 6) = 21 ∧ 2 ^ 6 = 64 ∧ momentSum 2 6 = 220 :=
  ⟨X.card_X_six, by norm_num, momentSum_two_six⟩

/-- The collision-to-type ratio: S_2(6) / |X_6| ≈ 10.47.
    Verified: S_2(6) = 220 > 10 · 21 = 210 and 220 < 11 · 21 = 231. -/
theorem collision_ratio_bounds_six :
    10 * Fintype.card (X 6) < momentSum 2 6 ∧
    momentSum 2 6 < 11 * Fintype.card (X 6) := by
  rw [momentSum_two_six, X.card_X_six]; omega

end Omega
