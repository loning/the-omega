import Mathlib.LinearAlgebra.Matrix.Notation
import Mathlib.LinearAlgebra.Matrix.Trace
import Mathlib.LinearAlgebra.Matrix.Determinant.Basic
import Omega.Folding.MomentSum

namespace Omega

/-- The 3x3 companion matrix for the S_2 recurrence:
    S_2(m+3) = 2·S_2(m+2) + 2·S_2(m+1) - 2·S_2(m).
    Characteristic polynomial: λ³ - 2λ² - 2λ + 2 = 0. -/
def collisionKernel2 : Matrix (Fin 3) (Fin 3) ℤ :=
  !![0, 1, 0; 0, 0, 1; -2, 2, 2]

theorem collisionKernel2_trace : collisionKernel2.trace = 2 := by native_decide
theorem collisionKernel2_det : collisionKernel2.det = -2 := by native_decide

/-- Cayley-Hamilton for the collision kernel: M³ = 2M² + 2M - 2I. -/
theorem collisionKernel2_cayley_hamilton :
    collisionKernel2 ^ 3 = 2 • collisionKernel2 ^ 2 + 2 • collisionKernel2 - 2 • 1 := by
  native_decide

/-- Verification that S_2 satisfies the linear recurrence S_2(m+3) + 2·S_2(m) = 2·S_2(m+2) + 2·S_2(m+1)
    for the base values m = 0..3. Written in additive form to avoid Nat subtraction. -/
theorem momentSum_two_recurrence_verified :
    (momentSum 2 3 + 2 * momentSum 2 0 = 2 * momentSum 2 2 + 2 * momentSum 2 1) ∧
    (momentSum 2 4 + 2 * momentSum 2 1 = 2 * momentSum 2 3 + 2 * momentSum 2 2) ∧
    (momentSum 2 5 + 2 * momentSum 2 2 = 2 * momentSum 2 4 + 2 * momentSum 2 3) ∧
    (momentSum 2 6 + 2 * momentSum 2 3 = 2 * momentSum 2 5 + 2 * momentSum 2 4) := by
  simp only [momentSum_two_zero, momentSum_two_one, momentSum_two_two,
    momentSum_two_three, momentSum_two_four, momentSum_two_five, momentSum_two_six]
  exact ⟨trivial, trivial, trivial, trivial⟩

end Omega
