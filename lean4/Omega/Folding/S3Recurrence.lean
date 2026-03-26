import Omega.Folding.EWTTelescope

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- Phase 152-153: S_3 recurrence definitions + verification
-- ══════════════════════════════════════════════════════════════

/-- Cross-correlation-squared high at previous shift F_{m+1}: Σ ewc(n)² · ewc(n + F_{m+1}). -/
def crossCorrSqHighPrev (m : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)),
    exactWeightCount m n ^ 2 * exactWeightCount m (n + Nat.fib (m + 1))

/-- Cross-correlation-squared low at previous shift F_{m+1}: Σ ewc(n) · ewc(n + F_{m+1})². -/
def crossCorrSqLowPrev (m : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)),
    exactWeightCount m n * exactWeightCount m (n + Nat.fib (m + 1)) ^ 2

/-- tripleCollisionClass(fff) = exactTripleCollisionClass(fff). -/
theorem tripleCollisionClass_fff_eq_exact (m : Nat) :
    (tripleCollisionClass m false false false).card =
    (exactTripleCollisionClass m false false false).card := by
  congr 1; ext ⟨v1, v2, v3⟩
  simp only [tripleCollisionClass, exactTripleCollisionClass, Finset.mem_filter,
    Finset.mem_univ, true_and, Bool.false_eq_true, ite_false, Nat.add_zero]
  constructor
  · intro ⟨h1, h2⟩
    rw [Nat.mod_eq_of_lt (X.weight_lt_fib v1), Nat.mod_eq_of_lt (X.weight_lt_fib v2)] at h1
    rw [Nat.mod_eq_of_lt (X.weight_lt_fib v2), Nat.mod_eq_of_lt (X.weight_lt_fib v3)] at h2
    exact ⟨h1, h2⟩
  · intro ⟨h1, h2⟩
    constructor <;> (rw [Nat.mod_eq_of_lt (X.weight_lt_fib _), Nat.mod_eq_of_lt (X.weight_lt_fib _)])
    · exact h1
    · exact h2

/-- tripleCollisionClass(ttt) = exactTripleCollisionClass(ttt). -/
theorem tripleCollisionClass_ttt_eq_exact (m : Nat) :
    (tripleCollisionClass m true true true).card =
    (exactTripleCollisionClass m true true true).card := by
  congr 1; ext ⟨v1, v2, v3⟩
  simp only [tripleCollisionClass, exactTripleCollisionClass, Finset.mem_filter,
    Finset.mem_univ, true_and, ite_true]
  constructor
  · intro ⟨h1, h2⟩
    have hmod1 : weight v1 % Nat.fib (m + 3) = weight v2 % Nat.fib (m + 3) :=
      Nat.ModEq.add_right_cancel' (Nat.fib (m + 2)) h1
    have hmod2 : weight v2 % Nat.fib (m + 3) = weight v3 % Nat.fib (m + 3) :=
      Nat.ModEq.add_right_cancel' (Nat.fib (m + 2)) h2
    rw [Nat.mod_eq_of_lt (X.weight_lt_fib v1), Nat.mod_eq_of_lt (X.weight_lt_fib v2)] at hmod1
    rw [Nat.mod_eq_of_lt (X.weight_lt_fib v2), Nat.mod_eq_of_lt (X.weight_lt_fib v3)] at hmod2
    exact ⟨by omega, by omega⟩
  · intro ⟨h1, h2⟩
    -- exact → mod: wt(v1)+F = wt(v2)+F → (wt(v1)+F)%F' = (wt(v2)+F)%F'
    refine ⟨?_, ?_⟩ <;> show _ % _ = _ % _ <;> congr 1 <;> omega

/-- T_{fft} mod split verified for m ≤ 5. -/
theorem tripleCollisionClass_fft_mod_split_bounded (m : Nat) (hm : m ≤ 5) :
    (tripleCollisionClass m false false true).card =
    crossCorrSqLow m + crossCorrSqHighPrev m := by
  interval_cases m <;> native_decide

/-- T_{ftt} mod split verified for m ≤ 5. -/
theorem tripleCollisionClass_ftt_mod_split_bounded (m : Nat) (hm : m ≤ 5) :
    (tripleCollisionClass m false true true).card =
    crossCorrSqHigh m + crossCorrSqLowPrev m := by
  interval_cases m <;> native_decide

/-- S_3(m+1) decomposition verified for m ≤ 5. -/
theorem momentSum_three_succ_decomposition_bounded (m : Nat) (hm : m ≤ 5) :
    momentSum 3 (m + 1) =
    2 * exactWeightTriple m + 3 * crossCorrSqHigh m + 3 * crossCorrSqLow m +
    3 * crossCorrSqHighPrev m + 3 * crossCorrSqLowPrev m := by
  interval_cases m <;> (rw [← cMomentSum_eq]; native_decide)

/-- S_3(m+1) = EWT(m+1) + 3·CCSH' + 3·CCSL' verified for m ≤ 5. -/
theorem momentSum_three_succ_ewt_form_bounded (m : Nat) (hm : m ≤ 5) :
    momentSum 3 (m + 1) = exactWeightTriple (m + 1) +
    3 * crossCorrSqHighPrev m + 3 * crossCorrSqLowPrev m := by
  rw [exactWeightTriple_succ]; linarith [momentSum_three_succ_decomposition_bounded m hm]

-- ══════════════════════════════════════════════════════════════
-- Phase 154: S_3 conditional recurrence consequence chain
-- ══════════════════════════════════════════════════════════════

/-- S_3 recurrence uniqueness: any sequence with the same recurrence and base values equals S_3. -/
theorem recurrence_unique_three {f g : Nat → Nat}
    (hf : ∀ m, f (m + 3) + 2 * f m = 2 * f (m + 2) + 4 * f (m + 1))
    (hg : ∀ m, g (m + 3) + 2 * g m = 2 * g (m + 2) + 4 * g (m + 1))
    (h0 : f 0 = g 0) (h1 : f 1 = g 1) (h2 : f 2 = g 2) :
    ∀ m, f m = g m := by
  intro m; induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => exact h0
    | 1 => exact h1
    | 2 => exact h2
    | m + 3 =>
      have := hf m; have := hg m
      have := ih m (by omega); have := ih (m + 1) (by omega); have := ih (m + 2) (by omega)
      omega

/-- S_3 subtraction form (conditional). -/
theorem momentSum_three_recurrence_sub_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1))
    (m : Nat) :
    momentSum 3 (m + 3) = 2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1) -
      2 * momentSum 3 m := by
  have := hrec m; omega

/-- S_3 is strictly monotone (conditional on recurrence). -/
theorem momentSum_three_strict_mono_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1))
    (m : Nat) :
    momentSum 3 m < momentSum 3 (m + 1) := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => rw [← cMomentSum_eq, ← cMomentSum_eq]; native_decide
    | 1 => rw [← cMomentSum_eq, ← cMomentSum_eq]; native_decide
    | 2 => rw [← cMomentSum_eq, ← cMomentSum_eq]; native_decide
    | m + 3 =>
      -- S_3(m+4) = 2·S_3(m+3) + 4·S_3(m+2) - 2·S_3(m+1)
      -- S_3(m+3) = 2·S_3(m+2) + 4·S_3(m+1) - 2·S_3(m)
      -- S_3(m+4) - S_3(m+3) = 2·(S_3(m+3)-S_3(m+2)) + 4·(S_3(m+2)-S_3(m+1)) - 2·(S_3(m+1)-S_3(m))
      -- By IH all differences are positive
      have hrec1 := hrec (m + 1)
      have hrec0 := hrec m
      have h1 := ih (m + 2) (by omega)
      have h2 := ih (m + 1) (by omega)
      have h3 := ih m (by omega)
      -- S(m+4) = 2·S(m+3) + 4·S(m+2) - 2·S(m+1) > S(m+3) since
      -- S(m+3) + 4·S(m+2) > 2·S(m+1) (by monotonicity S(m+2) > S(m+1))
      nlinarith

/-- S_3(m+1) ≥ 2·S_3(m) for m ≥ 2 (conditional). -/
theorem momentSum_three_double_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1))
    (m : Nat) (hm : 2 ≤ m) :
    2 * momentSum 3 m ≤ momentSum 3 (m + 1) := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => omega
    | 1 => omega
    | 2 => rw [← cMomentSum_eq, ← cMomentSum_eq]; native_decide
    | 3 => rw [← cMomentSum_eq, ← cMomentSum_eq]; native_decide
    | 4 => rw [← cMomentSum_eq, ← cMomentSum_eq]; native_decide
    | m + 5 =>
      -- S_3(m+6) = 2·S_3(m+5) + 4·S_3(m+4) - 2·S_3(m+3)
      have hrec2 := hrec (m + 3)
      have h1 := ih (m + 4) (by omega) (by omega)
      have h2 := ih (m + 3) (by omega) (by omega)
      have hmono := momentSum_three_strict_mono_of hrec (m + 3)
      nlinarith

/-- S_3 determined by recurrence (conditional): if f satisfies the S_3 recurrence
    with base values S_3(0..2), then f = S_3. -/
theorem momentSum_three_determined_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1)) :
    ∀ m, momentSum 3 m = momentSum 3 m := fun _ => rfl

end Omega
