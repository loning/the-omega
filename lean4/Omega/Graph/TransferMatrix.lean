import Mathlib.Data.Matrix.Basic
import Mathlib.LinearAlgebra.Matrix.Notation
import Mathlib.LinearAlgebra.Matrix.Trace
import Mathlib.LinearAlgebra.Matrix.Determinant.Basic
import Omega.Core.Fib

namespace Omega.Graph

/-- The 2x2 adjacency (transfer) matrix of the golden-mean shift:
    A = [[1,1],[1,0]], encoding allowed transitions in the No11 constraint. -/
def goldenMeanAdjacency : Matrix (Fin 2) (Fin 2) ℤ :=
  !![1, 1; 1, 0]

/-- Entry (0,0) = 1: transition 0 → 0 is allowed. -/
theorem goldenMeanAdjacency_entry_00 : goldenMeanAdjacency 0 0 = 1 := by native_decide

/-- Entry (0,1) = 1: transition 0 → 1 is allowed. -/
theorem goldenMeanAdjacency_entry_01 : goldenMeanAdjacency 0 1 = 1 := by native_decide

/-- Entry (1,0) = 1: transition 1 → 0 is allowed. -/
theorem goldenMeanAdjacency_entry_10 : goldenMeanAdjacency 1 0 = 1 := by native_decide

/-- Entry (1,1) = 0: transition 1 → 1 is forbidden (No11 constraint). -/
theorem goldenMeanAdjacency_entry_11 : goldenMeanAdjacency 1 1 = 0 := by native_decide

/-- Concrete Cayley-Hamilton identity: A² = A + I for the golden-mean adjacency matrix. -/
theorem goldenMeanAdjacency_sq :
    goldenMeanAdjacency ^ 2 = goldenMeanAdjacency + 1 := by native_decide

/-- Trace of the golden-mean adjacency matrix is 1. -/
theorem goldenMeanAdjacency_trace : goldenMeanAdjacency.trace = 1 := by native_decide

/-- Determinant of the golden-mean adjacency matrix is -1. -/
theorem goldenMeanAdjacency_det : goldenMeanAdjacency.det = -1 := by native_decide

/-! ### Transfer matrix and Fibonacci numbers -/

/-- A^(m+2) = A^(m+1) + A^m (matrix Fibonacci recurrence from A² = A + I). -/
theorem goldenMeanAdjacency_pow_add_two (m : Nat) :
    goldenMeanAdjacency ^ (m + 2) =
      goldenMeanAdjacency ^ (m + 1) + goldenMeanAdjacency ^ m := by
  have : goldenMeanAdjacency ^ (m + 2) = goldenMeanAdjacency ^ m * goldenMeanAdjacency ^ 2 := by
    rw [← pow_add]
  rw [this, goldenMeanAdjacency_sq, mul_add, mul_one, pow_succ]

/-- Row-sum of A^m equals Nat.fib(m+2) (cast to ℤ). -/
theorem goldenMeanAdjacency_row_sum :
    ∀ m : Nat, (goldenMeanAdjacency ^ m) 0 0 + (goldenMeanAdjacency ^ m) 0 1 =
      (Nat.fib (m + 2) : ℤ)
  | 0 => by native_decide
  | 1 => by native_decide
  | m + 2 => by
    have hRec := goldenMeanAdjacency_pow_add_two m
    have ih1 := goldenMeanAdjacency_row_sum (m + 1)
    have ih0 := goldenMeanAdjacency_row_sum m
    simp only [hRec, Matrix.add_apply]
    rw [show (goldenMeanAdjacency ^ (m + 1)) 0 0 + (goldenMeanAdjacency ^ m) 0 0 +
        ((goldenMeanAdjacency ^ (m + 1)) 0 1 + (goldenMeanAdjacency ^ m) 0 1) =
        ((goldenMeanAdjacency ^ (m + 1)) 0 0 + (goldenMeanAdjacency ^ (m + 1)) 0 1) +
        ((goldenMeanAdjacency ^ m) 0 0 + (goldenMeanAdjacency ^ m) 0 1) from by ring]
    rw [ih1, ih0, ← Nat.cast_add]
    congr 1
    exact (Omega.fib_succ_succ' (m + 2)).symm


end Omega.Graph
