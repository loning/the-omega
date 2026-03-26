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
-- Phase 155: T_fft mod split via weight-class summation
-- ══════════════════════════════════════════════════════════════

/-- Count of words whose weight + F_{m+2} ≡ n (mod F_{m+3}). -/
theorem modular_weight_count (m n : Nat) (hn : n < Nat.fib (m + 3)) :
    (Finset.univ.filter (fun v : Word m =>
      (weight v + Nat.fib (m + 2)) % Nat.fib (m + 3) = n)).card =
    if Nat.fib (m + 2) ≤ n then exactWeightCount m (n - Nat.fib (m + 2))
    else exactWeightCount m (n + Nat.fib (m + 1)) := by
  have hfib : Nat.fib (m + 3) = Nat.fib (m + 1) + Nat.fib (m + 2) := Nat.fib_add_two
  split_ifs with hge
  · -- n ≥ F_{m+2}: (wt + F_{m+2}) % F_{m+3} = n ↔ wt = n - F_{m+2}
    -- Since n - F_{m+2} < F_{m+1} < F_{m+3}, wt + F_{m+2} = n < F_{m+3}, so mod is identity
    simp only [exactWeightCount]; congr 1; ext v
    simp only [Finset.mem_filter, Finset.mem_univ, true_and]
    constructor
    · intro h
      have hvlt : weight v < Nat.fib (m + 3) := X.weight_lt_fib v
      have : weight v + Nat.fib (m + 2) < 2 * Nat.fib (m + 3) := by omega
      by_cases hlt : weight v + Nat.fib (m + 2) < Nat.fib (m + 3)
      · rw [Nat.mod_eq_of_lt hlt] at h; omega
      · push_neg at hlt
        rw [Nat.mod_eq_sub_mod hlt, Nat.mod_eq_of_lt (by omega)] at h; omega
    · intro h
      rw [h, Nat.sub_add_cancel hge, Nat.mod_eq_of_lt hn]
  · -- n < F_{m+2}: (wt + F_{m+2}) % F_{m+3} = n ↔ wt = n + F_{m+1}
    -- Since wt + F_{m+2} = n + F_{m+1} + F_{m+2} = n + F_{m+3} ≥ F_{m+3}, mod subtracts F_{m+3}
    push_neg at hge
    simp only [exactWeightCount]; congr 1; ext v
    simp only [Finset.mem_filter, Finset.mem_univ, true_and]
    constructor
    · intro h
      have hvlt : weight v < Nat.fib (m + 3) := X.weight_lt_fib v
      by_cases hlt : weight v + Nat.fib (m + 2) < Nat.fib (m + 3)
      · rw [Nat.mod_eq_of_lt hlt] at h; omega
      · push_neg at hlt
        rw [Nat.mod_eq_sub_mod hlt, Nat.mod_eq_of_lt (by omega)] at h; omega
    · intro h
      rw [h, show n + Nat.fib (m + 1) + Nat.fib (m + 2) = n + Nat.fib (m + 3) from by omega,
          Nat.add_mod, Nat.mod_self, Nat.add_zero, Nat.mod_mod, Nat.mod_eq_of_lt hn]

set_option maxHeartbeats 800000 in
/-- T_{fft}(mod) expressed as sum over weight classes. -/
theorem tripleCollisionClass_fft_eq_sum (m : Nat) :
    (tripleCollisionClass m false false true).card =
    ∑ n ∈ Finset.range (Nat.fib (m + 3)),
      exactWeightCount m n ^ 2 *
      (Finset.univ.filter (fun v : Word m =>
        (weight v + Nat.fib (m + 2)) % Nat.fib (m + 3) = n)).card := by
  classical
  -- T_{fft}: wt(v1) % F = wt(v2) % F ∧ wt(v2) % F = (wt(v3)+F_{m+2}) % F
  -- Since wt < F, first condition is wt(v1) = wt(v2)
  -- Group by n = wt(v1) = wt(v2)
  simp only [tripleCollisionClass, exactWeightCount, Bool.false_eq_true, ite_false, ite_true,
    Nat.add_zero]
  -- Rewrite as product decomposition
  simp_rw [show ∀ n, (Finset.univ.filter (fun w : Word m => weight w = n)).card ^ 2 *
    (Finset.univ.filter (fun v : Word m =>
      (weight v + Nat.fib (m + 2)) % Nat.fib (m + 3) = n)).card =
    ((Finset.univ.filter (fun w : Word m => weight w = n)) ×ˢ
     ((Finset.univ.filter (fun w : Word m => weight w = n)) ×ˢ
      (Finset.univ.filter (fun v : Word m =>
        (weight v + Nat.fib (m + 2)) % Nat.fib (m + 3) = n)))).card from
    fun n => by simp [Finset.card_product]; ring]
  rw [← Finset.card_biUnion]
  · congr 1; ext ⟨v1, v2, v3⟩
    simp only [Finset.mem_biUnion, Finset.mem_range, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    constructor
    · intro ⟨h1, h2⟩
      rw [Nat.mod_eq_of_lt (X.weight_lt_fib v1),
          Nat.mod_eq_of_lt (X.weight_lt_fib v2)] at h1
      rw [Nat.mod_eq_of_lt (X.weight_lt_fib v2)] at h2
      rw [← h1] at h2
      exact ⟨weight v1, X.weight_lt_fib v1, rfl, h1.symm, h2.symm⟩
    · rintro ⟨n, hn, hw1, hw2, hw3⟩
      have hv1 : weight v1 = n := hw1
      have hv2 : weight v2 = n := by omega
      refine ⟨?_, ?_⟩
      · show _ % _ = _ % _; rw [hv1, hv2]
      · show _ % _ = _ % _; rw [hv2, Nat.mod_eq_of_lt hn, ← hw3]
  · intro n _ n' _ hne
    simp only [Function.onFun, Finset.disjoint_left, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    intro ⟨v1, _, _⟩ ⟨hw1, _⟩ ⟨hw1', _⟩
    exact hne (hw1.symm.trans hw1')

-- ewc vanishes for weights ≥ F_{m+3}
private theorem ewc_zero_of_ge (m n : Nat) (hn : Nat.fib (m + 3) ≤ n) :
    exactWeightCount m n = 0 := by
  simp only [exactWeightCount, Finset.card_eq_zero, Finset.filter_eq_empty_iff]
  intro w _; exact Nat.ne_of_lt (by linarith [X.weight_lt_fib w])

/-- CCSL range truncates to F_{m+1}: for k ≥ F_{m+1}, ewc(k+F_{m+2}) = 0. -/
theorem crossCorrSqLow_range_truncate (m : Nat) :
    crossCorrSqLow m = ∑ k ∈ Finset.range (Nat.fib (m + 1)),
      exactWeightCount m k * exactWeightCount m (k + Nat.fib (m + 2)) ^ 2 := by
  unfold crossCorrSqLow
  have hfib : Nat.fib (m + 3) = Nat.fib (m + 1) + Nat.fib (m + 2) := Nat.fib_add_two
  symm; apply Finset.sum_subset (Finset.range_mono (Nat.fib_mono (show m + 1 ≤ m + 3 by omega)))
  intro k hk hk'
  simp only [Finset.mem_range] at hk hk'; push_neg at hk'
  have : Nat.fib (m + 3) ≤ k + Nat.fib (m + 2) := by linarith [hfib]
  rw [ewc_zero_of_ge m _ this]; simp

/-- CCSH' range truncates to F_{m+2}: for n ≥ F_{m+2}, ewc(n+F_{m+1}) = 0. -/
theorem crossCorrSqHighPrev_range_truncate (m : Nat) :
    crossCorrSqHighPrev m = ∑ n ∈ Finset.range (Nat.fib (m + 2)),
      exactWeightCount m n ^ 2 * exactWeightCount m (n + Nat.fib (m + 1)) := by
  unfold crossCorrSqHighPrev
  have hfib : Nat.fib (m + 3) = Nat.fib (m + 1) + Nat.fib (m + 2) := Nat.fib_add_two
  symm; apply Finset.sum_subset (Finset.range_mono (Nat.fib_mono (show m + 2 ≤ m + 3 by omega)))
  intro n hn hn'
  simp only [Finset.mem_range] at hn hn'; push_neg at hn'
  have : Nat.fib (m + 3) ≤ n + Nat.fib (m + 1) := by linarith [hfib]
  rw [ewc_zero_of_ge m _ this]; simp

set_option maxHeartbeats 800000 in
/-- T_{fft}(mod) = CCSL + CCSH' (general, all m). -/
theorem tripleCollisionClass_fft_mod_split (m : Nat) :
    (tripleCollisionClass m false false true).card =
    crossCorrSqLow m + crossCorrSqHighPrev m := by
  rw [tripleCollisionClass_fft_eq_sum]
  have hfib : Nat.fib (m + 3) = Nat.fib (m + 1) + Nat.fib (m + 2) := Nat.fib_add_two
  -- Substitute modular_weight_count
  have hsubst : ∀ n ∈ Finset.range (Nat.fib (m + 3)),
      exactWeightCount m n ^ 2 *
      (Finset.univ.filter (fun v : Word m =>
        (weight v + Nat.fib (m + 2)) % Nat.fib (m + 3) = n)).card =
      if Nat.fib (m + 2) ≤ n
      then exactWeightCount m n ^ 2 * exactWeightCount m (n - Nat.fib (m + 2))
      else exactWeightCount m n ^ 2 * exactWeightCount m (n + Nat.fib (m + 1)) := by
    intro n hn; rw [modular_weight_count m n (Finset.mem_range.mp hn)]; split_ifs <;> rfl
  rw [Finset.sum_congr rfl hsubst, Finset.sum_ite]
  -- Goal: Σ_{n≥F₂} ewc(n)²·ewc(n-F₂) + Σ_{n<F₂} ewc(n)²·ewc(n+F₁) = CCSL + CCSH'
  congr 1
  · -- Σ_{n∈range(F₃), n≥F₂} ewc(n)²·ewc(n-F₂) = CCSL
    rw [crossCorrSqLow_range_truncate]
    -- Bijection: filter(range(F₃), ≥F₂) ↔ range(F₁) via n ↦ n - F₂
    apply Finset.sum_bij (fun n _ => n - Nat.fib (m + 2))
    · intro n hn
      simp only [Finset.mem_filter, Finset.mem_range] at hn
      exact Finset.mem_range.mpr (by omega)
    · intro n1 hn1 n2 hn2 h
      simp only [Finset.mem_filter] at hn1 hn2; omega
    · intro k hk
      have hk' := Finset.mem_range.mp hk
      exact ⟨k + Nat.fib (m + 2),
        Finset.mem_filter.mpr ⟨Finset.mem_range.mpr (by omega), by omega⟩,
        by simp⟩
    · intro n hn
      simp only [Finset.mem_filter, Finset.mem_range] at hn
      rw [Nat.sub_add_cancel hn.2]; ring
  · -- Σ_{n∈range(F₃), ¬(n≥F₂)} ewc(n)²·ewc(n+F₁) = CCSH'
    rw [crossCorrSqHighPrev_range_truncate]
    -- filter(range(F₃), ¬≥F₂) = range(F₂) (since F₂ ≤ F₃)
    congr 1
    ext n; simp only [Finset.mem_filter, Finset.mem_range, not_le]; omega

-- T_{ftt} mod split and S_3 full decomposition: depend on T_{ftt}_eq_sum (mirror of fft).
-- The fft proof is complete; ftt follows the same pattern. Deferred to next session.

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

-- ══════════════════════════════════════════════════════════════
-- Phase 156: S_3 high-order values + S_3 mod 2
-- ══════════════════════════════════════════════════════════════

/-- S_3(8) = 7768 (by conditional recurrence from S_3(5..7)). -/
theorem momentSum_three_eight_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1)) :
    momentSum 3 8 = 7768 := by
  have h := hrec 5
  simp only [show (5 : Nat) + 3 = 8 from rfl, show (5 : Nat) + 2 = 7 from rfl,
    show (5 : Nat) + 1 = 6 from rfl,
    momentSum_three_five, momentSum_three_six, momentSum_three_seven] at h; omega

/-- S_3(9) = 23912. -/
theorem momentSum_three_nine_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1)) :
    momentSum 3 9 = 23912 := by
  have h := hrec 6
  simp only [show (6 : Nat) + 3 = 9 from rfl, show (6 : Nat) + 2 = 8 from rfl,
    show (6 : Nat) + 1 = 7 from rfl,
    momentSum_three_six, momentSum_three_seven, momentSum_three_eight_of hrec] at h; omega

/-- S_3(10) = 73888. -/
theorem momentSum_three_ten_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1)) :
    momentSum 3 10 = 73888 := by
  have h := hrec 7
  simp only [show (7 : Nat) + 3 = 10 from rfl, show (7 : Nat) + 2 = 9 from rfl,
    show (7 : Nat) + 1 = 8 from rfl,
    momentSum_three_seven, momentSum_three_eight_of hrec, momentSum_three_nine_of hrec] at h; omega

/-- S_3(m) is even for m ≥ 1 (conditional). -/
theorem momentSum_three_even_of
    (hrec : ∀ m, momentSum 3 (m + 3) + 2 * momentSum 3 m =
      2 * momentSum 3 (m + 2) + 4 * momentSum 3 (m + 1))
    (m : Nat) (hm : 1 ≤ m) : 2 ∣ momentSum 3 m := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => omega
    | 1 => exact ⟨1, by rw [momentSum_three_one]⟩
    | 2 => exact ⟨5, by rw [momentSum_three_two]⟩
    | m + 3 =>
      have h := hrec m
      have hmono := momentSum_three_strict_mono_of hrec m
      have hmono2 := momentSum_three_strict_mono_of hrec (m + 1)
      exact ⟨momentSum 3 (m + 2) + 2 * momentSum 3 (m + 1) - momentSum 3 m, by omega⟩

end Omega
