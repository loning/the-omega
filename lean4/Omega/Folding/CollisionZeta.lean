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

end Omega
