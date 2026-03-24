import Omega.Folding.CollisionKernel

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

end Omega
