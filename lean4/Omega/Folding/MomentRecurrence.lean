import Omega.Folding.CollisionDecomp

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- S_2 recurrence consequences
-- ══════════════════════════════════════════════════════════════

/-- S_2(m+3) = 2·S_2(m+2) + 2·S_2(m+1) - 2·S_2(m). Subtraction form. -/
theorem momentSum_two_recurrence_sub (m : Nat) :
    momentSum 2 (m + 3) = 2 * momentSum 2 (m + 2) + 2 * momentSum 2 (m + 1) - 2 * momentSum 2 m := by
  have h := momentSum_two_recurrence m; omega

-- ══════════════════════════════════════════════════════════════
-- Positivity
-- ══════════════════════════════════════════════════════════════

/-- S_2(m) > 0 for all m. -/
theorem momentSum_two_pos' (m : Nat) : 0 < momentSum 2 m := by
  calc 0 < 2 ^ m := Nat.pos_of_ne_zero (by positivity)
    _ ≤ momentSum 2 m := momentSum_two_ge_pow m

-- ══════════════════════════════════════════════════════════════
-- Monotonicity
-- ══════════════════════════════════════════════════════════════

/-- S_2 is monotone: S_2(m) ≤ S_2(m+1). -/
theorem momentSum_two_mono' (m : Nat) : momentSum 2 m ≤ momentSum 2 (m + 1) := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => rw [momentSum_two_zero, momentSum_two_one]; omega
    | 1 => rw [momentSum_two_one, momentSum_two_two]; omega
    | 2 =>
      rw [momentSum_two_two]
      rw [show (2 + 1 : Nat) = 3 from rfl, momentSum_two_three]; omega
    | m + 3 =>
      -- S_2(m+4) = 2·S_2(m+3) + 2·S_2(m+2) - 2·S_2(m+1)
      -- S_2(m+3) = 2·S_2(m+2) + 2·S_2(m+1) - 2·S_2(m)
      -- S_2(m+4) - S_2(m+3) = 2·(S_2(m+3)-S_2(m+2)) + 2·(S_2(m+2)-S_2(m+1)) - 2·(S_2(m+1)-S_2(m))
      -- Wait, let me use the recurrence directly.
      -- From recurrence: S(m+6) + 2S(m+3) = 2S(m+5) + 2S(m+4)
      -- So S(m+6) = 2S(m+5) + 2S(m+4) - 2S(m+3)
      -- Need S(m+3) ≤ S(m+4).
      -- From recurrence at m: S(m+3) + 2S(m) = 2S(m+2) + 2S(m+1)
      -- S(m+3) = 2S(m+2) + 2S(m+1) - 2S(m)
      -- From recurrence at m+1: S(m+4) = 2S(m+3) + 2S(m+2) - 2S(m+1)
      -- S(m+4) - S(m+3) = 2S(m+3) + 2S(m+2) - 2S(m+1) - S(m+3)
      --                  = S(m+3) + 2S(m+2) - 2S(m+1)
      --                  = (2S(m+2)+2S(m+1)-2S(m)) + 2S(m+2) - 2S(m+1)
      --                  = 4S(m+2) - 2S(m)
      -- Since S(m+2) ≥ 2^(m+2) = 4·2^m ≥ 4 and S(m) ≥ 1, we need 4S(m+2) ≥ 2S(m).
      -- S(m+2) ≥ 2^(m+2) and S(m) ≤ S(m+2) (by IH twice). So 4S(m+2) ≥ 4S(m) ≥ 2S(m). ✓
      have hrec1 := momentSum_two_recurrence (m + 1)
      have ihm1 := ih (m + 1) (by omega)
      have ihm2 := ih (m + 2) (by omega)
      -- S(m+4) + 2S(m+1) = 2S(m+3) + 2S(m+2)
      -- Need: S(m+3) ≤ S(m+4)
      -- i.e., S(m+3) ≤ 2S(m+3) + 2S(m+2) - 2S(m+1)
      -- i.e., 2S(m+1) ≤ S(m+3) + 2S(m+2)
      -- S(m+3) ≥ S(m+2) ≥ S(m+1) (by IH), so S(m+3)+2S(m+2) ≥ 3S(m+1) ≥ 2S(m+1). ✓
      linarith

/-- S_2 is strictly monotone for m ≥ 1. -/
theorem momentSum_two_strict_mono' (m : Nat) (hm : 1 ≤ m) :
    momentSum 2 m < momentSum 2 (m + 1) := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => omega
    | 1 => rw [momentSum_two_one, momentSum_two_two]; omega
    | 2 =>
      rw [momentSum_two_two, show (2 + 1 : Nat) = 3 from rfl, momentSum_two_three]; omega
    | m + 3 =>
      -- S(m+4) - S(m+3) = S(m+3) + 2S(m+2) - 2S(m+1) [from recurrence]
      -- = (S(m+3) - S(m+2)) + (S(m+2) - S(m+1)) + 2(S(m+2) - S(m+1))
      -- > 0 by IH at m+2 and m+1
      have hrec := momentSum_two_recurrence (m + 1)
      have ihm2 : momentSum 2 (m + 2) < momentSum 2 (m + 3) := ih (m + 2) (by omega) (by omega)
      have ihm1 : momentSum 2 (m + 1) < momentSum 2 (m + 2) := ih (m + 1) (by omega) (by omega)
      -- S(m+4) + 2S(m+1) = 2S(m+3) + 2S(m+2)
      -- S(m+4) = 2S(m+3) + 2S(m+2) - 2S(m+1) > 2S(m+3) + 2S(m+1) - 2S(m+1) = 2S(m+3)
      -- Wait: S(m+4) = 2S(m+3) + 2(S(m+2)-S(m+1)) > 2S(m+3) > S(m+3). ✓
      linarith

-- ══════════════════════════════════════════════════════════════
-- General S_q = Σ wcc^q
-- ══════════════════════════════════════════════════════════════

/-- General q-moment = Σ wcc^q. Generalizes momentSum_two_eq_congr_sq_sum to all q. -/
theorem momentSum_eq_congr_pow_sum (q m : Nat) :
    momentSum q m =
    ∑ r ∈ Finset.range (Nat.fib (m + 2)), weightCongruenceCount m r ^ q := by
  unfold momentSum
  simp_rw [fiberMultiplicity_eq_wcc]
  have hbij := X.stableValueFin_bijective m
  have step : ∑ x : X m, weightCongruenceCount m (stableValue x) ^ q =
      ∑ r : Fin (Nat.fib (m + 2)), weightCongruenceCount m r.val ^ q := by
    rw [show (fun x : X m => weightCongruenceCount m (stableValue x) ^ q) =
      (fun r : Fin (Nat.fib (m + 2)) => weightCongruenceCount m r.val ^ q) ∘
      X.stableValueFin from by ext x; simp [X.stableValueFin]]
    exact hbij.sum_comp (fun r : Fin (Nat.fib (m + 2)) => weightCongruenceCount m r.val ^ q)
  rw [step, ← Fin.sum_univ_eq_sum_range]

-- ══════════════════════════════════════════════════════════════
-- exactWeightTriple definition
-- ══════════════════════════════════════════════════════════════

/-- Sum of cubed exact weight counts. -/
def exactWeightTriple (m : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)), exactWeightCount m n ^ 3

-- ══════════════════════════════════════════════════════════════
-- S_q positivity
-- ══════════════════════════════════════════════════════════════

/-- S_q(m) > 0 for all q, m. -/
theorem momentSum_pos' (q m : Nat) : 0 < momentSum q m := by
  unfold momentSum
  apply Finset.sum_pos
  · intro x _
    exact Nat.pos_of_ne_zero (pow_ne_zero q (Nat.pos_iff_ne_zero.mp (X.fiberMultiplicity_pos x)))
  · exact ⟨⟨fun _ => false, no11_allFalse⟩, Finset.mem_univ _⟩

end Omega
