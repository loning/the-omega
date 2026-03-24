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


/-- Helper: entry (i,j) of A^(m+2) = entry of A^(m+1) + entry of A^m. -/
private theorem pow_entry_add_two (m : Nat) (i j : Fin 2) :
    (goldenMeanAdjacency ^ (m + 2)) i j =
      (goldenMeanAdjacency ^ (m + 1)) i j + (goldenMeanAdjacency ^ m) i j := by
  have := goldenMeanAdjacency_pow_add_two m
  exact congr_fun (congr_fun (congr_arg Matrix.of this) i) j

/-- (A^m)_{00} = F_{m+1}. -/
theorem goldenMeanAdjacency_pow_00 :
    ∀ m : Nat, (goldenMeanAdjacency ^ m) 0 0 = (Nat.fib (m + 1) : ℤ)
  | 0 => by native_decide
  | 1 => by native_decide
  | m + 2 => by
    rw [pow_entry_add_two, goldenMeanAdjacency_pow_00 (m + 1),
        goldenMeanAdjacency_pow_00 m, ← Nat.cast_add]
    congr 1; exact (Omega.fib_succ_succ' (m + 1)).symm

/-- (A^m)_{01} = F_m. -/
theorem goldenMeanAdjacency_pow_01 :
    ∀ m : Nat, (goldenMeanAdjacency ^ m) 0 1 = (Nat.fib m : ℤ)
  | 0 => by native_decide
  | 1 => by native_decide
  | m + 2 => by
    rw [pow_entry_add_two, goldenMeanAdjacency_pow_01 (m + 1),
        goldenMeanAdjacency_pow_01 m, ← Nat.cast_add]
    congr 1; exact (Omega.fib_succ_succ' m).symm

/-- (A^m)_{10} = F_m. -/
theorem goldenMeanAdjacency_pow_10 :
    ∀ m : Nat, (goldenMeanAdjacency ^ m) 1 0 = (Nat.fib m : ℤ)
  | 0 => by native_decide
  | 1 => by native_decide
  | m + 2 => by
    rw [pow_entry_add_two, goldenMeanAdjacency_pow_10 (m + 1),
        goldenMeanAdjacency_pow_10 m, ← Nat.cast_add]
    congr 1; exact (Omega.fib_succ_succ' m).symm

/-- (A^m)_{11} = F_{m-1} for m ≥ 1. -/
theorem goldenMeanAdjacency_pow_11 :
    ∀ m : Nat, (goldenMeanAdjacency ^ (m + 1)) 1 1 = (Nat.fib m : ℤ)
  | 0 => by native_decide
  | 1 => by native_decide
  | m + 2 => by
    rw [show m + 2 + 1 = (m + 1 + 1) + 1 from by omega,
        show (m + 1 + 1) + 1 = (m + 1) + 2 from by omega,
        pow_entry_add_two,
        goldenMeanAdjacency_pow_11 (m + 1), goldenMeanAdjacency_pow_11 m, ← Nat.cast_add]
    congr 1; exact (Omega.fib_succ_succ' m).symm

/-- det(A^m) = (-1)^m. -/
theorem goldenMeanAdjacency_pow_det (m : Nat) :
    (goldenMeanAdjacency ^ m).det = (-1 : ℤ) ^ m := by
  rw [Matrix.det_pow]; simp [goldenMeanAdjacency_det]

/-- Cassini's identity: F_{n+1}·F_{n-1} - F_n² = (-1)^n for n ≥ 1. -/
theorem fib_cassini (n : Nat) (hn : 1 ≤ n) :
    (Nat.fib (n + 1) : ℤ) * Nat.fib (n - 1) - (Nat.fib n : ℤ) ^ 2 = (-1 : ℤ) ^ n := by
  obtain ⟨m, rfl⟩ : ∃ m, n = m + 1 := ⟨n - 1, by omega⟩
  -- det(A^{m+1}) = (A^{m+1})_{00}·(A^{m+1})_{11} - (A^{m+1})_{01}·(A^{m+1})_{10}
  have hDet := goldenMeanAdjacency_pow_det (m + 1)
  simp only [Matrix.det_fin_two, goldenMeanAdjacency_pow_00,
    goldenMeanAdjacency_pow_01, goldenMeanAdjacency_pow_10,
    goldenMeanAdjacency_pow_11] at hDet
  -- hDet : F_{m+2}·F_m - F_{m+1}·F_{m+1} = (-1)^{m+1}
  simp only [show m + 1 - 1 = m from by omega] at *
  -- hDet : ↑(F_{m+2}) * ↑(F_m) - ↑(F_{m+1}) * ↑(F_{m+1}) = (-1)^(m+1)
  -- Goal: ↑(F_{m+2}) * ↑(F_m) - ↑(F_{m+1})^2 = (-1)^(m+1)
  rw [sq]; exact hDet

/-- Row 1 sum of A^m: paths starting from state 1. -/
theorem goldenMean_path_count_from_true (m : Nat) :
    (goldenMeanAdjacency ^ m) 1 0 + (goldenMeanAdjacency ^ m) 1 1 =
      (Nat.fib (m + 1) : ℤ) := by
  cases m with
  | zero => native_decide
  | succ m =>
    rw [goldenMeanAdjacency_pow_10, goldenMeanAdjacency_pow_11, ← Nat.cast_add]
    congr 1; exact (Omega.fib_succ_succ' m).symm

/-- Total paths of length m in the golden-mean shift. -/
theorem goldenMean_total_paths (m : Nat) :
    (goldenMeanAdjacency ^ m) 0 0 + (goldenMeanAdjacency ^ m) 0 1 +
    ((goldenMeanAdjacency ^ m) 1 0 + (goldenMeanAdjacency ^ m) 1 1) =
      (Nat.fib (m + 2) + Nat.fib (m + 1) : ℤ) := by
  rw [goldenMeanAdjacency_row_sum, goldenMean_path_count_from_true, ← Nat.cast_add]

/-- Specific power entries: (A^5)_{00} = F(6) = 8. -/
theorem goldenMeanAdjacency_pow_five_00 :
    (goldenMeanAdjacency ^ 5) 0 0 = (Nat.fib 6 : ℤ) :=
  goldenMeanAdjacency_pow_00 5

/-- Specific power entries: (A^6)_{00} = F(7) = 13. -/
theorem goldenMeanAdjacency_pow_six_00 :
    (goldenMeanAdjacency ^ 6) 0 0 = (Nat.fib 7 : ℤ) :=
  goldenMeanAdjacency_pow_00 6

/-- Specific power entries: (A^10)_{00} = F(11) = 89. -/
theorem goldenMeanAdjacency_pow_ten_00 :
    (goldenMeanAdjacency ^ 10) 0 0 = (Nat.fib 11 : ℤ) :=
  goldenMeanAdjacency_pow_00 10

/-! ### Golden-mean zeta function -/

/-- Zeta denominator evaluation at z=1: 1 - tr(A) + det(A) = 1 - 1 + (-1) = -1. -/
theorem goldenMean_zeta_denom_at_one :
    (1 : ℤ) - goldenMeanAdjacency.trace + goldenMeanAdjacency.det = -1 := by
  rw [goldenMeanAdjacency_trace, goldenMeanAdjacency_det]; norm_num

/-- Golden-mean trace recurrence verified for n = 0..4. -/
theorem goldenMean_trace_recurrence_verified :
    (goldenMeanAdjacency ^ 2).trace = (goldenMeanAdjacency ^ 1).trace + (goldenMeanAdjacency ^ 0).trace ∧
    (goldenMeanAdjacency ^ 3).trace = (goldenMeanAdjacency ^ 2).trace + (goldenMeanAdjacency ^ 1).trace ∧
    (goldenMeanAdjacency ^ 4).trace = (goldenMeanAdjacency ^ 3).trace + (goldenMeanAdjacency ^ 2).trace ∧
    (goldenMeanAdjacency ^ 5).trace = (goldenMeanAdjacency ^ 4).trace + (goldenMeanAdjacency ^ 3).trace ∧
    (goldenMeanAdjacency ^ 6).trace = (goldenMeanAdjacency ^ 5).trace + (goldenMeanAdjacency ^ 4).trace := by
  refine ⟨?_, ?_, ?_, ?_, ?_⟩ <;> native_decide

end Omega.Graph
