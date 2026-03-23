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

/-- The 3x3 companion matrix for the S_3 recurrence:
    S_3(m+3) = 2·S_3(m+2) + 4·S_3(m+1) - 2·S_3(m).
    Characteristic polynomial: λ³ - 2λ² - 4λ + 2 = 0. -/
def collisionKernel3 : Matrix (Fin 3) (Fin 3) ℤ :=
  !![0, 1, 0; 0, 0, 1; -2, 4, 2]

theorem collisionKernel3_trace : collisionKernel3.trace = 2 := by native_decide
theorem collisionKernel3_det : collisionKernel3.det = -2 := by native_decide

/-- Cayley-Hamilton for A_3: M³ = 2M² + 4M - 2I. -/
theorem collisionKernel3_cayley_hamilton :
    collisionKernel3 ^ 3 = 2 • collisionKernel3 ^ 2 + 4 • collisionKernel3 - 2 • 1 := by
  native_decide

/-- S_3 recurrence verification: S_3(m+3) + 2·S_3(m) = 2·S_3(m+2) + 4·S_3(m+1) for m=0..3. -/
theorem momentSum_three_recurrence_verified :
    (momentSum 3 3 + 2 * momentSum 3 0 = 2 * momentSum 3 2 + 4 * momentSum 3 1) ∧
    (momentSum 3 4 + 2 * momentSum 3 1 = 2 * momentSum 3 3 + 4 * momentSum 3 2) ∧
    (momentSum 3 5 + 2 * momentSum 3 2 = 2 * momentSum 3 4 + 4 * momentSum 3 3) ∧
    (momentSum 3 6 + 2 * momentSum 3 3 = 2 * momentSum 3 5 + 4 * momentSum 3 4) := by
  simp only [momentSum_three_zero, momentSum_three_one, momentSum_three_two,
    momentSum_three_three, momentSum_three_four, momentSum_three_five, momentSum_three_six]
  exact ⟨trivial, trivial, trivial, trivial⟩

end Omega
