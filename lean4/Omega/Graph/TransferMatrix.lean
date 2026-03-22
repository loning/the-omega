import Mathlib.Data.Matrix.Basic
import Mathlib.LinearAlgebra.Matrix.Notation
import Mathlib.LinearAlgebra.Matrix.Trace
import Mathlib.LinearAlgebra.Matrix.Determinant.Basic

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

end Omega.Graph
