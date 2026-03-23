import Omega.Folding.InverseLimitTopology
import Omega.Graph.TransferMatrix

namespace Omega.X

/-- The left shift on XInfinity: σ(a)(i) = a(i+1). -/
def shift (a : XInfinity) : XInfinity :=
  ⟨fun i => a.1 (i + 1), fun i h => a.2 (i + 1) h⟩

/-- The shift map is continuous (composition of continuous projections). -/
theorem continuous_shift : Continuous shift := by
  apply Continuous.subtype_mk
  exact continuous_pi fun i => (continuous_apply (i + 1)).comp continuous_subtype_val

/-- The shift map is surjective: prepend false to any sequence. -/
theorem shift_surjective : Function.Surjective shift := by
  intro b
  refine ⟨⟨fun i => if i = 0 then false else b.1 (i - 1), fun i ⟨hi, hi1⟩ => ?_⟩, ?_⟩
  · -- No11Inf proof for prepended sequence
    cases i with
    | zero => simp at hi
    | succ i =>
      simp only [Nat.succ_ne_zero, ↓reduceIte] at hi hi1
      exact b.2 i ⟨hi, by rwa [show i + 1 + 1 - 1 = i + 1 from by omega] at hi1⟩
  · -- shift of constructed sequence = b
    ext i; simp [shift]

/-- Coordinate formula for the left shift: the i-th entry of σ(a) equals a(i+1). -/
theorem shift_val (a : XInfinity) (i : Nat) : (shift a).1 i = a.1 (i + 1) := rfl

/-- The n-fold iterate of the left shift. -/
def shiftN : Nat → XInfinity → XInfinity
  | 0, a => a
  | n + 1, a => shift (shiftN n a)

/-- Coordinate formula for the n-fold shift: σⁿ(a)(i) = a(i+n). -/
theorem shiftN_val : ∀ (n : Nat) (a : XInfinity) (i : Nat),
    (shiftN n a).1 i = a.1 (i + n)
  | 0, a, i => by simp [shiftN]
  | n + 1, a, i => by simp [shiftN, shift_val, shiftN_val n a (i + 1)]; ring_nf

/-- The n-fold shift is continuous. -/
theorem continuous_shiftN : ∀ (n : Nat), Continuous (shiftN n)
  | 0 => continuous_id
  | n + 1 => continuous_shift.comp (continuous_shiftN n)

end Omega.X

namespace Omega

/-! ### Discrete entropy skeleton (cor:folding-stable-syntax-entropy-logqdim, Stage 1)

The finite stable syntax spaces X_m satisfy:
- Fibonacci recurrence: |X_{m+2}| = |X_{m+1}| + |X_m|
- Growth bounds: |X_m| ≤ |X_{m+1}| ≤ 2 · |X_m|
- Transfer matrix representation: |X_m| = (A^m)_{00} + (A^m)_{01}
-/

/-- |X_{m+2}| = |X_{m+1}| + |X_m| (Fibonacci recurrence for stable word counts). -/
theorem card_X_recurrence (m : Nat) :
    Fintype.card (X (m + 2)) = Fintype.card (X (m + 1)) + Fintype.card (X m) := by
  simp only [X.card_eq_fib]
  exact fib_succ_succ' (m + 2)

/-- |X_m| ≤ |X_{m+1}| ≤ 2 · |X_m| (Fibonacci ratio bounds). -/
theorem card_X_ratio_bounds (m : Nat) :
    Fintype.card (X m) ≤ Fintype.card (X (m + 1)) ∧
    Fintype.card (X (m + 1)) ≤ 2 * Fintype.card (X m) := by
  simp only [X.card_eq_fib]
  constructor
  · exact Nat.fib_mono (by omega)
  · -- Nat.fib (m+3) ≤ 2 * Nat.fib (m+2)
    calc Nat.fib (m + 3)
        = Nat.fib (m + 2) + Nat.fib (m + 1) := fib_succ_succ' (m + 1)
      _ ≤ Nat.fib (m + 2) + Nat.fib (m + 2) :=
          Nat.add_le_add_left (Nat.fib_mono (by omega)) _
      _ = 2 * Nat.fib (m + 2) := by omega

/-- |X_m| = (A^m)_{00} + (A^m)_{01} where A is the golden-mean adjacency matrix. -/
theorem card_X_eq_matrix_sum (m : Nat) :
    (Fintype.card (X m) : ℤ) =
      (Graph.goldenMeanAdjacency ^ m) 0 0 + (Graph.goldenMeanAdjacency ^ m) 0 1 := by
  rw [X.card_eq_fib]
  exact (Graph.goldenMeanAdjacency_row_sum m).symm

end Omega
