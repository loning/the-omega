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

/-- The all-false infinite sequence (the unique fixed point of shift). -/
def allFalse : XInfinity := ⟨fun _ => false, fun _ h => by exact absurd h.1 Bool.false_ne_true⟩

@[simp] theorem shift_allFalse : shift allFalse = allFalse :=
  Subtype.ext (funext fun _ => rfl)

/-- shift(a) = a iff a is the all-false sequence. -/
theorem shift_fixed_iff (a : XInfinity) : shift a = a ↔ a = allFalse := by
  constructor
  · intro h
    apply Subtype.ext; funext i
    have hEq : ∀ j, a.1 (j + 1) = a.1 j := fun j => congr_fun (congr_arg Subtype.val h) j
    have hConst : ∀ i, a.1 i = a.1 0 := by
      intro i; induction i with
      | zero => rfl
      | succ n ih => exact (hEq n).trans ih
    cases h0 : a.1 0 with
    | false => exact (hConst i).trans h0
    | true => exact absurd ⟨(hConst 0).symm ▸ h0, (hConst 1).symm ▸ h0⟩ (a.2 0)
  · intro h; rw [h, shift_allFalse]

/-- The shift is not injective (both allFalse and (true,false,false,...) map to allFalse). -/
theorem shift_not_injective : ¬ Function.Injective shift := by
  intro hInj
  have hNo11 : No11Inf (fun i => if i = 0 then true else false) := by
    intro i ⟨hi, hi1⟩
    by_cases h0 : i = 0
    · subst h0; simp at hi1
    · simp [h0] at hi
  let a : XInfinity := ⟨_, hNo11⟩
  have hShift : shift a = shift allFalse := by
    apply Subtype.ext; funext i
    show (if i + 1 = 0 then true else false) = false
    simp
  have hab := congr_fun (congr_arg Subtype.val (hInj hShift)) 0
  -- hab : a.1 0 = allFalse.1 0, need to show this is true = false
  change (if (0 : Nat) = 0 then true else false) = false at hab
  simp at hab

/-- The period-3 sequence: true at positions 0, 3, 6, ... -/
def period3Seq : XInfinity :=
  ⟨fun i => decide (i % 3 = 0), fun i ⟨hi, hi1⟩ => by simp at hi hi1; omega⟩

/-- The period-3 sequence has period 3 under shift. -/
theorem shiftN_three_period3 : shiftN 3 period3Seq = period3Seq := by
  apply Subtype.ext; funext i; simp [shiftN, shift, period3Seq]; omega

/-- The period-3 sequence is NOT a fixed point of shift. -/
theorem shift_period3_ne : shift period3Seq ≠ period3Seq := by
  intro h; have := congr_fun (congr_arg Subtype.val h) 0
  simp [shift, period3Seq] at this

/-- The period-2 sequence: true at positions 0, 2, 4, ... -/
def period2Seq : XInfinity :=
  ⟨fun i => decide (i % 2 = 0), fun i ⟨hi, hi1⟩ => by simp at hi hi1; omega⟩

/-- The period-2 sequence has period 2 under shift. -/
theorem shiftN_two_period2 : shiftN 2 period2Seq = period2Seq := by
  apply Subtype.ext; funext i; simp [shiftN, shift, period2Seq]; omega

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

/-! ### Lucas numbers -/

/-- The Lucas sequence: L_0 = 2, L_1 = 1, L_{n+2} = L_{n+1} + L_n. -/
def lucasNum : Nat → Nat
  | 0 => 2
  | 1 => 1
  | n + 2 => lucasNum (n + 1) + lucasNum n

@[simp] theorem lucasNum_zero : lucasNum 0 = 2 := rfl
@[simp] theorem lucasNum_one : lucasNum 1 = 1 := rfl
theorem lucasNum_two : lucasNum 2 = 3 := rfl
theorem lucasNum_three : lucasNum 3 = 4 := rfl
@[simp] theorem lucasNum_succ_succ (n : Nat) :
    lucasNum (n + 2) = lucasNum (n + 1) + lucasNum n := rfl

/-- L_n = F_{n+1} + F_{n-1} for n ≥ 1. -/
private theorem lucasNum_eq_fib_aux :
    ∀ m : Nat, lucasNum (m + 1) = Nat.fib (m + 2) + Nat.fib m
  | 0 => by native_decide
  | 1 => by native_decide
  | m + 2 => by
    rw [lucasNum_succ_succ, lucasNum_eq_fib_aux (m + 1), lucasNum_eq_fib_aux m]
    -- Use native_decide for m=0,1 then the recurrence handles the rest uniformly
    -- Actually the omega issue is Nat.fib normalization. Just native_decide small + fallback.
    simp only [lucasNum_succ_succ, lucasNum_eq_fib_aux, fib_succ_succ']
    omega

/-- L_n = F_{n+1} + F_{n-1} for n ≥ 1. -/
theorem lucasNum_eq_fib (n : Nat) (hn : 1 ≤ n) :
    lucasNum n = Nat.fib (n + 1) + Nat.fib (n - 1) := by
  obtain ⟨m, rfl⟩ : ∃ m, n = m + 1 := ⟨n - 1, by omega⟩
  simp only [show m + 1 - 1 = m from by omega]
  exact lucasNum_eq_fib_aux m

/-- trace(A^n) = F_{n+1} + F_{n-1} for n ≥ 1 (= Lucas number). -/
theorem goldenMeanAdjacency_pow_trace (n : Nat) (hn : 1 ≤ n) :
    (Graph.goldenMeanAdjacency ^ n).trace =
      (Nat.fib (n + 1) : ℤ) + Nat.fib (n - 1) := by
  obtain ⟨m, rfl⟩ : ∃ m, n = m + 1 := ⟨n - 1, by omega⟩
  simp only [Matrix.trace, Matrix.diag, show m + 1 - 1 = m from by omega]
  rw [Fin.sum_univ_two]
  rw [Graph.goldenMeanAdjacency_pow_00, Graph.goldenMeanAdjacency_pow_11]

end Omega
