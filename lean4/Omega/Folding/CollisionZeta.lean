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

end Omega
