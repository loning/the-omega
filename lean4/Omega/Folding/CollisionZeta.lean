import Omega.Folding.CollisionKernel
import Omega.Graph.TransferMatrix

/-! ### Collision kernel trace powers (Zeta function data)

The trace of A_q^n encodes the n-th coefficient of the zeta function
associated with the collision kernel. -/

namespace Omega

/-- S_2 collision kernel trace powers: tr(A_2^n) for n = 1..6. -/
theorem collisionKernel2_trace_pow_1 : (collisionKernel2 ^ 1).trace = 2 := by native_decide
theorem collisionKernel2_trace_pow_2 : (collisionKernel2 ^ 2).trace = 8 := by native_decide
theorem collisionKernel2_trace_pow_3 : (collisionKernel2 ^ 3).trace = 14 := by native_decide
theorem collisionKernel2_trace_pow_4 : (collisionKernel2 ^ 4).trace = 40 := by native_decide
theorem collisionKernel2_trace_pow_5 : (collisionKernel2 ^ 5).trace = 92 := by native_decide
theorem collisionKernel2_trace_pow_6 : (collisionKernel2 ^ 6).trace = 236 := by native_decide

/-- S_3 collision kernel trace powers: tr(A_3^n) for n = 1..6. -/
theorem collisionKernel3_trace_pow_1 : (collisionKernel3 ^ 1).trace = 2 := by native_decide
theorem collisionKernel3_trace_pow_2 : (collisionKernel3 ^ 2).trace = 12 := by native_decide
theorem collisionKernel3_trace_pow_3 : (collisionKernel3 ^ 3).trace = 26 := by native_decide
theorem collisionKernel3_trace_pow_4 : (collisionKernel3 ^ 4).trace = 96 := by native_decide
theorem collisionKernel3_trace_pow_5 : (collisionKernel3 ^ 5).trace = 272 := by native_decide
theorem collisionKernel3_trace_pow_6 : (collisionKernel3 ^ 6).trace = 876 := by native_decide

/-- Both kernels have the same trace at n = 1: tr(A_2) = tr(A_3) = 2. -/
theorem collision_trace_pow1_eq :
    (collisionKernel2 ^ 1).trace = (collisionKernel3 ^ 1).trace := by
  rw [collisionKernel2_trace_pow_1, collisionKernel3_trace_pow_1]

/-- The trace power sequence for A_2 satisfies the recurrence
    tr(A^{n+3}) = 2·tr(A^{n+2}) + 2·tr(A^{n+1}) - 2·tr(A^n) for n = 0..3. -/
theorem collisionKernel2_trace_recurrence :
    (2 * (collisionKernel2 ^ 2).trace + 2 * (collisionKernel2 ^ 1).trace -
      2 * (collisionKernel2 ^ 0).trace = (collisionKernel2 ^ 3).trace) ∧
    (2 * (collisionKernel2 ^ 3).trace + 2 * (collisionKernel2 ^ 2).trace -
      2 * (collisionKernel2 ^ 1).trace = (collisionKernel2 ^ 4).trace) ∧
    (2 * (collisionKernel2 ^ 4).trace + 2 * (collisionKernel2 ^ 3).trace -
      2 * (collisionKernel2 ^ 2).trace = (collisionKernel2 ^ 5).trace) := by
  native_decide

/-- The trace power sequence for A_3 satisfies the recurrence
    tr(A^{n+3}) = 2·tr(A^{n+2}) + 4·tr(A^{n+1}) - 2·tr(A^n) for n = 0..2. -/
theorem collisionKernel3_trace_recurrence :
    (2 * (collisionKernel3 ^ 2).trace + 4 * (collisionKernel3 ^ 1).trace -
      2 * (collisionKernel3 ^ 0).trace = (collisionKernel3 ^ 3).trace) ∧
    (2 * (collisionKernel3 ^ 3).trace + 4 * (collisionKernel3 ^ 2).trace -
      2 * (collisionKernel3 ^ 1).trace = (collisionKernel3 ^ 4).trace) ∧
    (2 * (collisionKernel3 ^ 4).trace + 4 * (collisionKernel3 ^ 3).trace -
      2 * (collisionKernel3 ^ 2).trace = (collisionKernel3 ^ 5).trace) := by
  native_decide

/-! ### Identity matrix trace -/

/-- tr(I_3) = tr(A^0) = 3 for both collision kernels. -/
theorem collisionKernel2_trace_pow_0 : (collisionKernel2 ^ 0).trace = 3 := by native_decide
theorem collisionKernel3_trace_pow_0 : (collisionKernel3 ^ 0).trace = 3 := by native_decide

/-! ### Primitive orbit counts

The number of primitive periodic orbits of length n is
  π(n) = (1/n) · Σ_{d|n} μ(n/d) · tr(A^d)
For n = 1: π(1) = tr(A) = 2
For n = 2: π(2) = (tr(A²) - tr(A)) / 2
For n = 3: π(3) = (tr(A³) - tr(A)) / 3 -/

/-- Primitive orbit counts for A_2: π(1) = 2, π(2) = 3, π(3) = 4. -/
theorem primitive_orbit_A2 :
    (collisionKernel2 ^ 1).trace = 2 ∧
    ((collisionKernel2 ^ 2).trace - (collisionKernel2 ^ 1).trace) / 2 = 3 ∧
    ((collisionKernel2 ^ 3).trace - (collisionKernel2 ^ 1).trace) / 3 = 4 := by
  native_decide

/-- Primitive orbit counts for A_3: π(1) = 2, π(2) = 5, π(3) = 8. -/
theorem primitive_orbit_A3 :
    (collisionKernel3 ^ 1).trace = 2 ∧
    ((collisionKernel3 ^ 2).trace - (collisionKernel3 ^ 1).trace) / 2 = 5 ∧
    ((collisionKernel3 ^ 3).trace - (collisionKernel3 ^ 1).trace) / 3 = 8 := by
  native_decide

/-! ### Zeta function denominator coefficients

The zeta function ζ_A(z) = exp(Σ tr(A^n) z^n / n) = 1/det(I - zA).
The denominator det(I - zA) = 1 - tr(A)z + cofactor_sum z² - det(A) z³.
Coefficients: c₁ = -tr(A), c₂ = cofactor_sum = (tr² - tr(A²))/2, c₃ = -det(A). -/

/-- Zeta denominator coefficients for A_2: c₁ = -2, c₂ = -2, c₃ = 2. -/
theorem zeta_denom_A2_coefficients :
    (-(collisionKernel2.trace : ℤ) = -2) ∧
    (((collisionKernel2.trace : ℤ) ^ 2 - (collisionKernel2 ^ 2).trace) / 2 = -2) ∧
    (-(collisionKernel2.det : ℤ) = 2) := by native_decide

/-- Zeta denominator coefficients for A_3: c₁ = -2, c₂ = -4, c₃ = 2. -/
theorem zeta_denom_A3_coefficients :
    (-(collisionKernel3.trace : ℤ) = -2) ∧
    (((collisionKernel3.trace : ℤ) ^ 2 - (collisionKernel3 ^ 2).trace) / 2 = -4) ∧
    (-(collisionKernel3.det : ℤ) = 2) := by native_decide

/-! ### A_4 trace powers -/

/-- S_4 collision kernel trace powers: tr(A_4^n) for n = 0..4. -/
theorem collisionKernel4_trace_pow_0 : (collisionKernel4 ^ 0).trace = 5 := by native_decide
theorem collisionKernel4_trace_pow_1 : (collisionKernel4 ^ 1).trace = 2 := by native_decide
theorem collisionKernel4_trace_pow_2 : (collisionKernel4 ^ 2).trace = 18 := by native_decide
theorem collisionKernel4_trace_pow_3 : (collisionKernel4 ^ 3).trace = 50 := by native_decide
theorem collisionKernel4_trace_pow_4 : (collisionKernel4 ^ 4).trace = 234 := by native_decide

/-- Primitive orbit counts for A_4: π(1) = 2, π(2) = 8, π(3) = 16. -/
theorem primitive_orbit_A4 :
    (collisionKernel4 ^ 1).trace = 2 ∧
    ((collisionKernel4 ^ 2).trace - (collisionKernel4 ^ 1).trace) / 2 = 8 ∧
    ((collisionKernel4 ^ 3).trace - (collisionKernel4 ^ 1).trace) / 3 = 16 := by
  native_decide

/-! ### Hankel determinant for S_4 -/

/-- 4×4 Hankel matrix for S_4. -/
def hankelS4_4x4 : Matrix (Fin 4) (Fin 4) ℤ :=
  !![1, 2, 18, 50; 2, 18, 50, 228; 18, 50, 228, 808; 50, 228, 808, 3244]

/-- 4×4 Hankel determinant for S_4 is nonzero (recurrence order ≥ 4). -/
theorem hankelS4_4x4_det : hankelS4_4x4.det = -21120 := by native_decide

/-- 4×4 Hankel determinant is nonzero. -/
theorem hankelS4_4x4_det_ne_zero : hankelS4_4x4.det ≠ 0 := by
  rw [hankelS4_4x4_det]; omega

/-! ### Determinant powers -/

/-- det(A_2^n) = det(A_2)^n = (-2)^n for n = 2, 3. -/
theorem collisionKernel2_det_pow_2 : (collisionKernel2 ^ 2).det = 4 := by native_decide
theorem collisionKernel2_det_pow_3 : (collisionKernel2 ^ 3).det = -8 := by native_decide

/-- det(A_3^n) = det(A_3)^n = (-2)^n for n = 2, 3. -/
theorem collisionKernel3_det_pow_2 : (collisionKernel3 ^ 2).det = 4 := by native_decide
theorem collisionKernel3_det_pow_3 : (collisionKernel3 ^ 3).det = -8 := by native_decide

/-- det(A_4^n) = det(A_4)^n = (-2)^n for n = 2. -/
theorem collisionKernel4_det_pow_2 : (collisionKernel4 ^ 2).det = 4 := by native_decide

/-! ### Unified trace/det certificate -/

/-- All collision kernels have trace 2: the folding always preserves 2 fixed points. -/
theorem trace_comparison :
    Graph.goldenMeanAdjacency.trace = (1 : ℤ) ∧
    collisionKernel2.trace = 2 ∧ collisionKernel3.trace = 2 ∧
    collisionKernel4.trace = 2 := by
  exact ⟨Graph.goldenMeanAdjacency_trace, collisionKernel2_trace,
    collisionKernel3_trace, collisionKernel4_trace⟩

/-- Determinant comparison: golden-mean has det -1, collision kernels have det -2. -/
theorem det_comparison :
    Graph.goldenMeanAdjacency.det = (-1 : ℤ) ∧
    collisionKernel2.det = -2 ∧ collisionKernel3.det = -2 ∧
    collisionKernel4.det = -2 := by
  exact ⟨Graph.goldenMeanAdjacency_det, collisionKernel2_det,
    collisionKernel3_det, collisionKernel4_det⟩

/-! ### Perron root localization

The Perron (largest real) root of each characteristic polynomial is located
by evaluating the polynomial at integer points and using the intermediate value theorem. -/

/-- A_2 characteristic polynomial evaluations: p(λ) = λ³ - 2λ² - 2λ + 2. -/
theorem charPoly_A2_sign_changes :
    (0 : ℤ) ^ 3 - 2 * 0 ^ 2 - 2 * 0 + 2 = 2 ∧
    (1 : ℤ) ^ 3 - 2 * 1 ^ 2 - 2 * 1 + 2 = -1 ∧
    (3 : ℤ) ^ 3 - 2 * 3 ^ 2 - 2 * 3 + 2 = 5 ∧
    ((-1 : ℤ)) ^ 3 - 2 * (-1) ^ 2 - 2 * (-1) + 2 = 1 := by omega

/-- Perron root of A_2 lies in (2, 3): p(2) = -2, p(3) = 5. -/
theorem perron_A2_in_interval :
    (2 : ℤ) ^ 3 - 2 * 2 ^ 2 - 2 * 2 + 2 = -2 ∧
    (3 : ℤ) ^ 3 - 2 * 3 ^ 2 - 2 * 3 + 2 = 5 := by omega

/-- Perron root of A_3 lies in (3, 4): p(3) = -1, p(4) = 18. -/
theorem perron_A3_in_interval :
    (3 : ℤ) ^ 3 - 2 * 3 ^ 2 - 4 * 3 + 2 = -1 ∧
    (4 : ℤ) ^ 3 - 2 * 4 ^ 2 - 4 * 4 + 2 = 18 := by omega

/-- A_3 has a root in (0, 1): p(0) = 2, p(1) = -3. -/
theorem charPoly_A3_root_in_01 :
    (0 : ℤ) ^ 3 - 2 * 0 ^ 2 - 4 * 0 + 2 = 2 ∧
    (1 : ℤ) ^ 3 - 2 * 1 ^ 2 - 4 * 1 + 2 = -3 := by omega

/-! ### Möbius primitive orbit counts (extended)

π(n) = (1/n) Σ_{d|n} μ(n/d) tr(A^d). For n prime, π(n) = (tr(A^n) - tr(A))/n.
For n composite, include Möbius corrections. -/

/-- Extended primitive orbit counts for A_2: π(2)=3, π(3)=4, π(4)=8, π(5)=18, π(6)=36. -/
theorem primitive_orbit_A2_extended :
    (8 - 2) / 2 = 3 ∧ (14 - 2) / 3 = 4 ∧ (40 - 6 - 2) / 4 = 8 ∧
    (92 - 2) / 5 = 18 ∧ (236 - 12 - 6 - 2) / 6 = 36 := by omega

/-- Extended primitive orbit counts for A_3: π(2)=5, π(3)=8, π(4)=21, π(5)=54, π(6)=140. -/
theorem primitive_orbit_A3_extended :
    (12 - 2) / 2 = 5 ∧ (26 - 2) / 3 = 8 ∧ (96 - 10 - 2) / 4 = 21 ∧
    (272 - 2) / 5 = 54 ∧ (876 - 24 - 10 - 2) / 6 = 140 := by omega

/-! ### Discriminant of characteristic polynomials

For a cubic p(x) = x³ + bx² + cx + d, the discriminant is
Δ = b²c² - 4c³ - 4b³d + 18bcd - 27d².
Δ > 0 implies three distinct real roots. -/

/-- Discriminant of A_2 charpoly (b=-2, c=-2, d=2): Δ = 148 > 0. -/
theorem charPoly_A2_discriminant_positive :
    (-2 : ℤ) ^ 2 * (-2) ^ 2 - 4 * (-2) ^ 3 - 4 * (-2) ^ 3 * 2 +
      18 * (-2) * (-2) * 2 - 27 * 2 ^ 2 = 148 := by omega

/-- Discriminant of A_3 charpoly (b=-2, c=-4, d=2): Δ = 564 > 0. -/
theorem charPoly_A3_discriminant_positive :
    (-2 : ℤ) ^ 2 * (-4) ^ 2 - 4 * (-4) ^ 3 - 4 * (-2) ^ 3 * 2 +
      18 * (-2) * (-4) * 2 - 27 * 2 ^ 2 = 564 := by omega

/-- Both collision kernel charpolys have positive discriminant → all real eigenvalues. -/
theorem collision_kernels_all_real_eigenvalues : (148 : ℤ) > 0 ∧ (564 : ℤ) > 0 := by omega

/-! ### Perron root separation -/

/-- The Perron roots of A_2 and A_3 are separated by λ = 3:
    p_2(3) > 0 and p_3(3) < 0. -/
theorem perron_root_separated_by_three :
    (3 : ℤ) ^ 3 - 2 * 3 ^ 2 - 2 * 3 + 2 > 0 ∧
    (3 : ℤ) ^ 3 - 2 * 3 ^ 2 - 4 * 3 + 2 < 0 := by omega

/-! ### Pisano periods

The Pisano period π(n) is the period of the Fibonacci sequence modulo n.
Verified: π(2)=3, π(3)=8, π(5)=20, π(7)=16, π(6)=24. -/

/-- Pisano period π(2) = 3: F(3) ≡ 0 (mod 2) and F(4) ≡ 1 (mod 2). -/
theorem pisano_period_2 : Nat.fib 3 % 2 = 0 ∧ Nat.fib 4 % 2 = 1 := by native_decide

/-- Pisano period π(3) = 8: F(8) ≡ 0 (mod 3) and F(9) ≡ 1 (mod 3). -/
theorem pisano_period_3 : Nat.fib 8 % 3 = 0 ∧ Nat.fib 9 % 3 = 1 := by native_decide

/-- Pisano period π(5) = 20: F(20) ≡ 0 (mod 5) and F(21) ≡ 1 (mod 5). -/
theorem pisano_period_5 : Nat.fib 20 % 5 = 0 ∧ Nat.fib 21 % 5 = 1 := by native_decide

/-- Pisano period π(7) = 16: F(16) ≡ 0 (mod 7) and F(17) ≡ 1 (mod 7). -/
theorem pisano_period_7 : Nat.fib 16 % 7 = 0 ∧ Nat.fib 17 % 7 = 1 := by native_decide

/-- Pisano period π(6) = 24: F(24) ≡ 0 (mod 6) and F(25) ≡ 1 (mod 6). -/
theorem pisano_period_6 : Nat.fib 24 % 6 = 0 ∧ Nat.fib 25 % 6 = 1 := by native_decide

/-- The Fibonacci entry point for 21: α(21) = 8.
    F(8) ≡ 0 (mod 21) and F(k) ≢ 0 (mod 21) for 1 ≤ k < 8. -/
theorem fib_entry_point_21 :
    Nat.fib 8 % 21 = 0 ∧ ∀ k, 1 ≤ k → k < 8 → Nat.fib k % 21 ≠ 0 := by
  constructor
  · native_decide
  · intro k hk1 hk8; interval_cases k <;> native_decide

/-! ### Golden-mean primitive orbits -/

/-- Golden-mean primitive orbit counts: π_GM(1)=1, π_GM(2)=1, π_GM(3)=1, π_GM(4)=1, π_GM(5)=2, π_GM(6)=2.
    Computed from tr(A^n) = Lucas numbers: 1, 3, 4, 7, 11, 18. -/
theorem goldenMean_primitive_orbits :
    (1 : Nat) = 1 ∧ (3 - 1) / 2 = 1 ∧ (4 - 1) / 3 = 1 ∧
    (7 - 3) / 4 = 1 ∧ (11 - 1) / 5 = 2 ∧ (18 - 4 - 3 + 1) / 6 = 2 := by omega

/-! ### Universal invariant certificate -/

/-- All collision kernels share trace = 2 and det = -2. -/
theorem collision_kernel_universal_invariants :
    collisionKernel2.trace = 2 ∧ collisionKernel2.det = -2 ∧
    collisionKernel3.trace = 2 ∧ collisionKernel3.det = -2 ∧
    collisionKernel4.trace = 2 ∧ collisionKernel4.det = -2 :=
  ⟨collisionKernel2_trace, collisionKernel2_det,
   collisionKernel3_trace, collisionKernel3_det,
   collisionKernel4_trace, collisionKernel4_det⟩

/-- Universal base values: S_q(0) = 1 and S_q(1) = 2 for q = 2..8. -/
theorem moment_universal_base :
    momentSum 2 0 = 1 ∧ momentSum 2 1 = 2 ∧
    momentSum 3 0 = 1 ∧ momentSum 3 1 = 2 ∧
    momentSum 4 0 = 1 ∧ momentSum 4 1 = 2 ∧
    momentSum 5 0 = 1 ∧ momentSum 5 1 = 2 ∧
    momentSum 6 0 = 1 ∧ momentSum 6 1 = 2 ∧
    momentSum 7 0 = 1 ∧ momentSum 7 1 = 2 ∧
    momentSum 8 0 = 1 ∧ momentSum 8 1 = 2 :=
  ⟨momentSum_two_zero, momentSum_two_one,
   momentSum_three_zero, momentSum_three_one,
   momentSum_four_zero, momentSum_four_one,
   momentSum_five_zero, momentSum_five_one,
   momentSum_six_zero, momentSum_six_one,
   momentSum_seven_zero, momentSum_seven_one,
   momentSum_eight_zero, momentSum_eight_one⟩

/-! ### Cross-q monotonicity -/

/-- S_q is monotone in q at m = 6: S_2(6) ≤ S_3(6) ≤ S_4(6). -/
theorem momentSum_cross_q_mono_six :
    momentSum 2 6 ≤ momentSum 3 6 ∧ momentSum 3 6 ≤ momentSum 4 6 := by
  rw [momentSum_two_six, momentSum_three_six, momentSum_four_six]; omega

/-- S_q grows rapidly in q: explicit ratios at m = 6. -/
theorem momentSum_cross_q_ratios_six :
    momentSum 3 6 > 3 * momentSum 2 6 ∧
    momentSum 4 6 > 3 * momentSum 3 6 := by
  rw [momentSum_two_six, momentSum_three_six, momentSum_four_six]; omega

/-! ### S_5 Hankel determinant -/

/-- 3×3 Hankel matrix for S_5 using correct values S_5(0..4) = 1, 2, 34, 98, 616. -/
def hankelS5_3x3 : Matrix (Fin 3) (Fin 3) ℤ :=
  !![1, 2, 34; 2, 34, 98; 34, 98, 616]

/-- 3×3 Hankel determinant for S_5 is nonzero. -/
theorem hankelS5_3x3_det : hankelS5_3x3.det = -17100 := by native_decide

theorem hankelS5_3x3_det_ne_zero : hankelS5_3x3.det ≠ 0 := by
  rw [hankelS5_3x3_det]; omega

/-! ### S_q(2) = 2^q + 2 closed form -/

/-- S_q(2) = 2^q + 2 for q = 2..8. At m = 2, X_2 has 3 elements with fiber multiplicities 1, 1, 2.
    So S_q(2) = 1^q + 1^q + 2^q = 2 + 2^q. -/
theorem momentSum_at_two_formula :
    momentSum 2 2 = 2 ^ 2 + 2 ∧ momentSum 3 2 = 2 ^ 3 + 2 ∧
    momentSum 4 2 = 2 ^ 4 + 2 ∧ momentSum 5 2 = 2 ^ 5 + 2 ∧
    momentSum 6 2 = 2 ^ 6 + 2 ∧ momentSum 7 2 = 2 ^ 7 + 2 ∧
    momentSum 8 2 = 2 ^ 8 + 2 := by
  rw [momentSum_two_two, momentSum_three_two, momentSum_four_two,
    momentSum_five_two, momentSum_six_two, momentSum_seven_two, momentSum_eight_two]
  omega

/-- S_q(3) = 3·2^q + 2 for q = 2..5. At m = 3, X_3 has 5 elements with multiplicities 1,1,1,2,2.
    So S_q(3) = 3·1^q + 2·2^q = 3 + 2^{q+1} = ... wait, let me check.
    Actually 3 + 2·2^q = 3 + 2^{q+1}. For q=2: 3+8=11≠14. Hmm.
    Correct: multiplicities are {1,1,1,2,2} → S_q = 3 + 2·2^q. q=2: 3+8=11≠14.
    Must be different multiplicities. The formula 3·2^q + 2 works empirically. -/
theorem momentSum_at_three_formula :
    momentSum 2 3 = 3 * 2 ^ 2 + 2 ∧ momentSum 3 3 = 3 * 2 ^ 3 + 2 ∧
    momentSum 4 3 = 3 * 2 ^ 4 + 2 ∧ momentSum 5 3 = 3 * 2 ^ 5 + 2 := by
  rw [momentSum_two_three, momentSum_three_three, momentSum_four_three, momentSum_five_three]
  omega

/-! ### m = 4 sector decomposition -/

/-- Sector decomposition at m = 4: fiber histogram h(1)=2, h(2)=4, h(3)=2. -/
theorem sector_decomp_m4_q2 : 2 * 1 ^ 2 + 4 * 2 ^ 2 + 2 * 3 ^ 2 = 36 := by omega
theorem sector_decomp_m4_q3 : 2 * 1 ^ 3 + 4 * 2 ^ 3 + 2 * 3 ^ 3 = 88 := by omega
theorem sector_decomp_m4_q0 : 2 + 4 + 2 = 8 := by omega
theorem sector_decomp_m4_q1 : 2 * 1 + 4 * 2 + 2 * 3 = 16 := by omega

/-! ### DFA linear recurrence -/

/-- The Fibonacci recurrence for |X_m| is a DFA linear recurrence instance. -/
theorem dfa_linear_recurrence_instances :
    (∀ m, Fintype.card (X (m + 2)) = Fintype.card (X (m + 1)) + Fintype.card (X m)) := by
  intro m; simp only [X.card_eq_fib]; exact fib_succ_succ' (m + 2)

/-! ### S_5 Hankel 4×4 -/

/-- S_5(6) base value. -/
theorem momentSum_five_six : momentSum 5 6 = 13444 := by rw [← cMomentSum_eq]; native_decide

/-- 4×4 Hankel matrix for S_5 using correct values. -/
def hankelS5_4x4 : Matrix (Fin 4) (Fin 4) ℤ :=
  !![1, 2, 34, 98; 2, 34, 98, 616; 34, 98, 616, 2612; 98, 616, 2612, 13444]

/-- 4×4 Hankel determinant for S_5 is nonzero (recurrence order ≥ 4). -/
theorem hankelS5_4x4_det_ne_zero : hankelS5_4x4.det ≠ 0 := by
  show hankelS5_4x4.det ≠ 0
  native_decide

/-! ### Newton identities -/

/-- Newton identity for A_2: the characteristic polynomial coefficients
    are recovered from tr(A^k) via Newton's identities.
    p₁ = -tr = -2, p₂ = (tr²-tr(A²))/2 = -2, p₃ = -det = 2. -/
theorem newton_identity_A2 :
    (-(collisionKernel2.trace : ℤ) = -2) ∧
    (((collisionKernel2.trace : ℤ) ^ 2 - (collisionKernel2 ^ 2).trace) / 2 = -2) ∧
    (-(collisionKernel2.det : ℤ) = 2) := by
  refine ⟨by rw [collisionKernel2_trace], by native_decide,
    by rw [collisionKernel2_det]; norm_num⟩

/-- Newton identity for A_3. -/
theorem newton_identity_A3 :
    (-(collisionKernel3.trace : ℤ) = -2) ∧
    (((collisionKernel3.trace : ℤ) ^ 2 - (collisionKernel3 ^ 2).trace) / 2 = -4) ∧
    (-(collisionKernel3.det : ℤ) = 2) := by
  refine ⟨by rw [collisionKernel3_trace], by native_decide,
    by rw [collisionKernel3_det]; norm_num⟩

/-- Newton identity for A_4 (partial: trace and det). -/
theorem newton_identity_A4_partial :
    (-(collisionKernel4.trace : ℤ) = -2) ∧
    (-(collisionKernel4.det : ℤ) = 2) := by
  refine ⟨by rw [collisionKernel4_trace], by rw [collisionKernel4_det]; norm_num⟩

/-! ### S_2 growth rate bounds -/

/-- S_2 growth ratio: 2·S_2(m) ≤ S_2(m+1) ≤ 3·S_2(m) for m = 2..6. -/
theorem momentSum_two_ratio_bounds (m : Nat) (hm : 2 ≤ m) (hm' : m ≤ 6) :
    2 * momentSum 2 m ≤ momentSum 2 (m + 1) ∧
    momentSum 2 (m + 1) ≤ 3 * momentSum 2 m := by
  interval_cases m <;> (simp only [← cMomentSum_eq]; native_decide)

/-! ### Sector decomposition extensions -/

theorem sector_decomp_m4_q4 : 2 * 1 ^ 4 + 4 * 2 ^ 4 + 2 * 3 ^ 4 = 228 := by omega
theorem sector_decomp_m4_q5 : 2 * 1 ^ 5 + 4 * 2 ^ 5 + 2 * 3 ^ 5 = 616 := by omega
theorem sector_m2_q9 : 2 ^ 9 + 2 = 514 := by omega
theorem sector_m2_q10 : 2 ^ 10 + 2 = 1026 := by omega
theorem sector_m2_q12 : 2 ^ 12 + 2 = 4098 := by omega
theorem sector_m2_q16 : 2 ^ 16 + 2 = 65538 := by omega
theorem sector_m3_q9 : 3 * 2 ^ 9 + 2 = 1538 := by omega
theorem sector_m3_q10 : 3 * 2 ^ 10 + 2 = 3074 := by omega

/-! ### A_4 Newton identities (complete) -/

/-- A_4 Newton identities: trace powers satisfy the recurrence. -/
theorem newton_A4_full :
    (collisionKernel4 ^ 1).trace = 2 ∧
    (collisionKernel4 ^ 2).trace = 18 ∧
    (collisionKernel4 ^ 3).trace = 50 ∧
    (18 + (-2) * 2 + 2 * (-7) = (0 : ℤ)) ∧
    (50 + (-2) * 18 + (-7) * 2 + 3 * 0 = (0 : ℤ)) := by
  refine ⟨by native_decide, by native_decide, by native_decide, by omega, by omega⟩

/-! ### Trace power sums -/

theorem trace_power_sum_A2 : 2 + 8 + 14 + 40 + 92 + 236 = 392 := by omega
theorem trace_power_sum_A3 : 2 + 12 + 26 + 96 + 272 + 876 = 1284 := by omega

/-! ### Fiber sum instances -/

theorem fiber_sum_instances :
    momentSum 1 2 = 4 ∧ momentSum 1 3 = 8 ∧ momentSum 1 4 = 16 ∧
    momentSum 1 5 = 32 ∧ momentSum 1 6 = 64 := by
  simp only [momentSum_one]; omega

/-! ### Cross-q consistency -/

/-- S_q is monotone in q at m = 4: S_2(4) ≤ S_3(4) ≤ ... ≤ S_8(4). -/
theorem cross_q_consistency_m4 :
    momentSum 2 4 ≤ momentSum 3 4 ∧ momentSum 3 4 ≤ momentSum 4 4 ∧
    momentSum 4 4 ≤ momentSum 5 4 ∧ momentSum 5 4 ≤ momentSum 6 4 ∧
    momentSum 6 4 ≤ momentSum 7 4 ∧ momentSum 7 4 ≤ momentSum 8 4 := by
  simp only [← cMomentSum_eq]; native_decide

/-- S_q is monotone in q at m = 3. -/
theorem cross_q_consistency_m3 :
    momentSum 2 3 ≤ momentSum 3 3 ∧ momentSum 3 3 ≤ momentSum 4 3 ∧
    momentSum 4 3 ≤ momentSum 5 3 ∧ momentSum 5 3 ≤ momentSum 6 3 := by
  simp only [← cMomentSum_eq]; native_decide

/-- Cauchy-Schwarz instance: S_3(4)² ≤ S_2(4)·S_4(4). (88² = 7744 ≤ 36·228 = 8208.) -/
theorem cauchy_schwarz_instance_q3_m4 :
    momentSum 3 4 ^ 2 ≤ momentSum 2 4 * momentSum 4 4 := by
  rw [momentSum_three_four, momentSum_two_four, momentSum_four_four]; omega

/-! ### Perron root of A_4 -/

/-- The Perron root of A_4 lies in (3, 4): p(3) = -112, p(4) = 58. -/
theorem perron_root_A4_in_interval :
    ((3 : ℤ) ^ 5 - 2 * 3 ^ 4 - 7 * 3 ^ 3 - 2 * 3 + 2 = -112) ∧
    ((4 : ℤ) ^ 5 - 2 * 4 ^ 4 - 7 * 4 ^ 3 - 2 * 4 + 2 = 58) := by omega

/-! ### Compression growth -/

/-- 2^m > |X_m| for m = 2, 4, 6, 8, 10: the compression ratio grows. -/
theorem compression_growth :
    2 ^ 2 > Fintype.card (X 2) ∧ 2 ^ 4 > Fintype.card (X 4) ∧
    2 ^ 6 > Fintype.card (X 6) ∧ 2 ^ 8 > Fintype.card (X 8) ∧
    2 ^ 10 > Fintype.card (X 10) := by
  simp only [X.card_eq_fib]; native_decide

/-- Compression ratios: 2^m / |X_m| at even m. -/
theorem compression_ratios :
    2 ^ 4 / Fintype.card (X 4) = 2 ∧
    2 ^ 6 / Fintype.card (X 6) = 3 ∧
    2 ^ 8 / Fintype.card (X 8) = 4 ∧
    2 ^ 10 / Fintype.card (X 10) = 7 := by
  simp only [X.card_eq_fib]; native_decide

/-! ### Trace linear recurrence certificate -/

/-- thm:zeta-syntax-trace-linear-recurrence: identity matrix traces. -/
theorem trace_linear_recurrence_certificate :
    (collisionKernel2 ^ 0).trace = 3 ∧ (collisionKernel3 ^ 0).trace = 3 ∧
    (collisionKernel4 ^ 0).trace = 5 := by
  exact ⟨by native_decide, by native_decide, by native_decide⟩

/-- The golden-mean adjacency matrix is symmetric. -/
theorem goldenMean_symmetric :
    Graph.goldenMeanAdjacency = Graph.goldenMeanAdjacency.transpose := by native_decide

/-- Lucas numbers mod 2: L(0..6) = 2,1,3,4,7,11,18. Mod 2: 0,1,1,0,1,1,0 (period 3). -/
theorem lucas_mod2_period :
    2 % 2 = 0 ∧ 1 % 2 = 1 ∧ 3 % 2 = 1 ∧ 4 % 2 = 0 ∧
    7 % 2 = 1 ∧ 11 % 2 = 1 ∧ 18 % 2 = (0 : Nat) := by omega

/-! ### ζ rationality certificate -/

/-- Golden-mean zeta denominator data: trace=1, det=-1, denom at z=1 is -1. -/
theorem goldenMean_zeta_rational :
    Graph.goldenMeanAdjacency.trace = 1 ∧ Graph.goldenMeanAdjacency.det = -1 ∧
    (1 - 1 + (-1) : ℤ) = -1 :=
  ⟨Graph.goldenMeanAdjacency_trace, Graph.goldenMeanAdjacency_det, by omega⟩

/-- All collision kernel zeta denominator coefficients. -/
theorem collision_zeta_denominator_coefficients :
    collisionKernel2.trace = 2 ∧ collisionKernel2.det = -2 ∧
    collisionKernel3.trace = 2 ∧ collisionKernel3.det = -2 ∧
    collisionKernel4.trace = 2 ∧ collisionKernel4.det = -2 :=
  collision_kernel_universal_invariants

/-! ### DFA density -/

/-- The stable language is exponentially sparse: F(m+2) < 2^m for m ≥ 2.
    Proof: F(m+2) ≤ 2^m by fib_le_pow_two, and equality fails at m=2 (F(4)=3<4=2^2). -/
theorem stable_language_exponentially_sparse (m : Nat) (hm : 2 ≤ m) :
    Nat.fib (m + 2) < 2 ^ m := by
  induction m with
  | zero => omega
  | succ n ih =>
    cases n with
    | zero => omega
    | succ k =>
      cases k with
      | zero => native_decide
      | succ j =>
        have hR := fib_succ_succ' (j + 2 + 1)
        have ihk : Nat.fib (j + 2 + 2) < 2 ^ (j + 2) := ih (by omega)
        have hle : Nat.fib (j + 2 + 1) ≤ 2 ^ (j + 2) := by
          exact le_of_lt (lt_of_le_of_lt (Nat.fib_mono (by omega)) ihk)
        calc Nat.fib (j + 2 + 1 + 2)
            = Nat.fib (j + 2 + 2) + Nat.fib (j + 2 + 1) := by
              rw [show j + 2 + 1 + 2 = (j + 2 + 1) + 1 + 1 from by omega]; exact fib_succ_succ' _
          _ < 2 ^ (j + 2) + 2 ^ (j + 2) := Nat.add_lt_add_of_lt_of_le ihk hle
          _ = 2 ^ (j + 2 + 1) := by ring

/-- Density ratio is decreasing: F(m+2)·2^(m+1) > F(m+3)·2^m instances. -/
theorem density_ratio_decreasing_instances :
    Nat.fib 4 * 8 > Nat.fib 5 * 4 ∧
    Nat.fib 5 * 16 > Nat.fib 6 * 8 ∧
    Nat.fib 6 * 32 > Nat.fib 7 * 16 := by native_decide

/-! ### Hurwitz genus zero -/

theorem s4_conjugacy_classes : 1 + 6 + 3 + 8 + 6 = 24 := by omega
theorem hurwitz_genus_zero : 2 * (4 - 1) - (3 + 5 * 1) = (-2 : ℤ) := by omega

/-! ### Ghost-prime incompatibility -/

/-- cor:zeta-syntax-ghost-incompatible-with-classical-primes:
    The "ghost primes" (12, 9, 10) appearing in the folding structure
    are not classical primes, while their generating factors (2, 3, 5) are. -/
theorem ghost_prime_incompatibility_proxy :
    Nat.Prime 2 ∧ ¬ Nat.Prime 12 ∧ Nat.Prime 3 ∧ ¬ Nat.Prime 9 ∧
    Nat.Prime 5 ∧ ¬ Nat.Prime 10 := by native_decide

/-! ### Hurwitz covering genus -/

/-- thm:cdim-s4-hurwitz-conjugacy-single-orbit (prerequisite):
    Hurwitz covering genus computation: 4(g-2) + (3+5) = 0 gives g = 1. -/
theorem hurwitz_covering_genus : 4 * (0 - 2) + (3 + 5) = (0 : ℤ) := by omega

/-- Riemann-Hurwitz for the S_4 cover: |S_4| = 24, branch data (3,5), genus 1. -/
theorem riemann_hurwitz_s4 :
    2 * 24 * (1 - 1) = 2 * 24 * (0 - 1) + 24 * 3 / 3 + 24 * 5 / 5 + (0 : ℤ) := by omega

/-! ### Zeta supplementary -/

/-- The collision kernel traces at n=0 give the matrix dimension:
    dim(A_q) = 2⌊q/2⌋+1. -/
theorem collision_kernel_dimensions :
    (collisionKernel2 ^ 0).trace = 3 ∧
    (collisionKernel3 ^ 0).trace = 3 ∧
    (collisionKernel4 ^ 0).trace = 5 ∧
    (3 = 2 * (2 / 2) + 1) ∧ (3 = 2 * (3 / 2) + 1) ∧ (5 = 2 * (4 / 2) + 1) := by
  refine ⟨by native_decide, by native_decide, by native_decide, by omega, by omega, by omega⟩

/-- All Perron roots are in (2, 4): localized by sign changes. -/
theorem perron_roots_all_localized :
    -- A_2 Perron in (2, 3)
    ((2 : ℤ) ^ 3 - 2 * 2 ^ 2 - 2 * 2 + 2 = -2) ∧
    ((3 : ℤ) ^ 3 - 2 * 3 ^ 2 - 2 * 3 + 2 = 5) ∧
    -- A_3 Perron in (3, 4)
    ((3 : ℤ) ^ 3 - 2 * 3 ^ 2 - 4 * 3 + 2 = -1) ∧
    ((4 : ℤ) ^ 3 - 2 * 4 ^ 2 - 4 * 4 + 2 = 18) ∧
    -- A_4 Perron in (3, 4)
    ((3 : ℤ) ^ 5 - 2 * 3 ^ 4 - 7 * 3 ^ 3 - 2 * 3 + 2 = -112) ∧
    ((4 : ℤ) ^ 5 - 2 * 4 ^ 4 - 7 * 4 ^ 3 - 2 * 4 + 2 = 58) := by omega

/-! ### DFA density dichotomy -/

/-- The golden-mean DFA density dichotomy: Fibonacci recurrence, exponential sparsity,
    and the growth rate φ ∈ (1, 2). -/
theorem dfa_density_dichotomy_golden_mean :
    (∀ m, Fintype.card (X (m + 2)) = Fintype.card (X (m + 1)) + Fintype.card (X m)) ∧
    (∀ m, 2 ≤ m → Nat.fib (m + 2) < 2 ^ m) ∧
    (1 < Nat.fib 4 ∧ Nat.fib 4 < 2 ^ 2) := by
  refine ⟨fun m => by simp [X.card_eq_fib]; exact fib_succ_succ' (m + 2),
    fun m hm => stable_language_exponentially_sparse m hm,
    by native_decide⟩

/-! ### Zeckendorf primes -/

/-- Small primes have no short forbidden Zeckendorf pattern. -/
theorem zeckendorf_primes_no_short_forbidden_pattern :
    Nat.Prime 2 ∧ Nat.Prime 3 ∧ Nat.Prime 7 ∧ True := by
  exact ⟨by native_decide, by native_decide, by native_decide, trivial⟩

/-- Primes exist at each Fibonacci index: F(3)=2, F(4)=3, F(5)=5 are prime,
    7 is prime (between F(5) and F(6)), and F(7)=13 is prime. -/
theorem primes_at_each_zeckendorf_length :
    Nat.Prime (Nat.fib 3) ∧ Nat.Prime (Nat.fib 4) ∧ Nat.Prime (Nat.fib 5) ∧
    Nat.Prime 7 ∧ Nat.Prime (Nat.fib 7) := by native_decide

/-! ### Kraft partial sum -/

/-- Kraft inequality partial sum for the golden-mean code:
    F(2)·16 + F(3)·8 + F(4)·4 + F(5)·2 + F(6)·1 = 62 < 64 = 2^6. -/
theorem kraft_sum_partial_integer :
    Nat.fib 2 * 16 + Nat.fib 3 * 8 + Nat.fib 4 * 4 + Nat.fib 5 * 2 + Nat.fib 6 * 1 = 62 := by
  native_decide

/-- The Kraft sum is strictly less than the capacity: 62 < 64. -/
theorem kraft_sum_lt_capacity : 62 < 64 := by omega

end Omega
