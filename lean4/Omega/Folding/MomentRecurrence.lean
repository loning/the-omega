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

-- ══════════════════════════════════════════════════════════════
-- S_3 = triple collision count
-- ══════════════════════════════════════════════════════════════

/-- S_3(m) = #{(w1,w2,w3) : Fold w1 = Fold w2 = Fold w3}. -/
theorem momentSum_three_eq_triple_collision (m : Nat) :
    momentSum 3 m = (Finset.univ.filter
      (fun p : Word m × Word m × Word m =>
        Fold p.1 = Fold p.2.1 ∧ Fold p.2.1 = Fold p.2.2)).card := by
  classical
  simp only [momentSum]
  -- d(x)³ = |fiber x ×ˢ (fiber x ×ˢ fiber x)|
  simp_rw [show ∀ (x : X m), X.fiberMultiplicity x ^ 3 =
    (X.fiber x ×ˢ (X.fiber x ×ˢ X.fiber x)).card from fun x => by
      simp [X.fiberMultiplicity, Finset.card_product]; ring]
  rw [← Finset.card_biUnion]
  · congr 1; ext ⟨w1, w2, w3⟩
    simp only [Finset.mem_biUnion, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and, X.mem_fiber]
    exact ⟨fun ⟨x, hw1, hw2, hw3⟩ => ⟨hw1.trans hw2.symm, hw2.trans hw3.symm⟩,
      fun ⟨h12, h23⟩ => ⟨Fold w1, rfl, h12.symm, (h12.trans h23).symm⟩⟩
  · intro x _ y _ hne
    simp only [Function.onFun, Finset.disjoint_left, Finset.mem_product, X.mem_fiber]
    intro ⟨w1, w2, w3⟩ ⟨hw1, _, _⟩ ⟨hw1', _, _⟩
    exact hne (hw1.symm.trans hw1')

/-- Triple collision ↔ weight triple congruence. -/
theorem triple_collision_iff_weight_mod (m : Nat) :
    (Finset.univ.filter (fun p : Word m × Word m × Word m =>
      Fold p.1 = Fold p.2.1 ∧ Fold p.2.1 = Fold p.2.2)).card =
    (Finset.univ.filter (fun p : Word m × Word m × Word m =>
      weight p.1 % Nat.fib (m + 2) = weight p.2.1 % Nat.fib (m + 2) ∧
      weight p.2.1 % Nat.fib (m + 2) = weight p.2.2 % Nat.fib (m + 2))).card := by
  congr 1; ext ⟨w1, w2, w3⟩; simp only [Finset.mem_filter, Finset.mem_univ, true_and]
  exact ⟨fun ⟨h1, h2⟩ => ⟨(Fold_eq_iff_weight_mod w1 w2).mp h1,
      (Fold_eq_iff_weight_mod w2 w3).mp h2⟩,
    fun ⟨h1, h2⟩ => ⟨(Fold_eq_iff_weight_mod w1 w2).mpr h1,
      (Fold_eq_iff_weight_mod w2 w3).mpr h2⟩⟩

-- ══════════════════════════════════════════════════════════════
-- S_q universal inequalities
-- ══════════════════════════════════════════════════════════════

/-- S_q(m) ≥ 2^m for q ≥ 1. -/
theorem momentSum_ge_pow' (q m : Nat) (hq : 1 ≤ q) : 2 ^ m ≤ momentSum q m := by
  calc 2 ^ m = ∑ x : X m, X.fiberMultiplicity x := (X.fiberMultiplicity_sum_eq_pow m).symm
    _ ≤ ∑ x : X m, X.fiberMultiplicity x ^ q := by
        apply Finset.sum_le_sum; intro x _
        exact le_self_pow (X.fiberMultiplicity_pos x) (by omega)
    _ = momentSum q m := rfl

/-- S_q(m) ≤ S_{q+1}(m). -/
theorem momentSum_le_succ' (q m : Nat) : momentSum q m ≤ momentSum (q + 1) m := by
  simp only [momentSum]
  apply Finset.sum_le_sum; intro x _
  exact pow_le_pow_right' (X.fiberMultiplicity_pos x) (Nat.le_succ q)

/-- Cauchy-Schwarz: S_2(m) · F_{m+2} ≥ 4^m. -/
theorem momentSum_two_mul_card_ge (m : Nat) :
    momentSum 2 m * Nat.fib (m + 2) ≥ 4 ^ m := by
  have hcs := momentSum_cauchy_schwarz m
  rw [show (2 ^ m) ^ 2 = 4 ^ m from by rw [← pow_mul, show 4 = 2 ^ 2 from by norm_num, ← pow_mul]; ring_nf] at hcs
  linarith [Nat.mul_comm (momentSum 2 m) (Nat.fib (m + 2))]

/-- S_q(m) ≥ F_{m+2} for all q. -/
theorem momentSum_ge_card' (q m : Nat) : Nat.fib (m + 2) ≤ momentSum q m := by
  calc Nat.fib (m + 2) = Fintype.card (X m) := (X.card_eq_fib m).symm
    _ = ∑ _ : X m, 1 := by simp
    _ ≤ ∑ x : X m, X.fiberMultiplicity x ^ q := by
        apply Finset.sum_le_sum; intro x _
        exact Nat.one_le_pow q _ (X.fiberMultiplicity_pos x)
    _ = momentSum q m := rfl

/-- S_q(m) ≤ D_m^{q-1} · 2^m (wrapper of momentSum_le_max_pow). -/
theorem momentSum_upper_bound' (q m : Nat) (hq : 1 ≤ q) :
    momentSum q m ≤ X.maxFiberMultiplicity m ^ (q - 1) * 2 ^ m :=
  momentSum_le_max_pow q m hq

-- ══════════════════════════════════════════════════════════════
-- S_2 number-theoretic properties
-- ══════════════════════════════════════════════════════════════

/-- S_2(m) is even for m ≥ 1. -/
theorem momentSum_two_even (m : Nat) (hm : 1 ≤ m) : 2 ∣ momentSum 2 m := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => omega
    | 1 => exact ⟨1, by rw [momentSum_two_one]⟩
    | 2 => exact ⟨3, by rw [momentSum_two_two]⟩
    | m + 3 =>
      have hrec := momentSum_two_recurrence m
      have h1 := ih (m + 1) (by omega) (by omega)
      have h2 := ih (m + 2) (by omega) (by omega)
      -- S(m+3) + 2S(m) = 2S(m+2) + 2S(m+1), so S(m+3) = 2(S(m+2)+S(m+1)-S(m))
      -- S(m+2) + S(m+1) ≥ S(m) by monotonicity
      obtain ⟨a, ha⟩ := h1; obtain ⟨b, hb⟩ := h2
      have hmono := momentSum_two_mono' m
      have hmono2 := momentSum_two_mono' (m + 1)
      exact ⟨2 * b + 2 * a - momentSum 2 m, by omega⟩

/-- S_2(m+1) / 2 = E00(m) + E01(m) (collision pair halving). -/
theorem momentSum_two_succ_half (m : Nat) :
    momentSum 2 (m + 1) / 2 =
    (Finset.univ.filter (fun p : Word m × Word m =>
      weight p.1 % Nat.fib (m + 3) = weight p.2 % Nat.fib (m + 3))).card +
    (Finset.univ.filter (fun p : Word m × Word m =>
      weight p.1 % Nat.fib (m + 3) =
      (weight p.2 + Nat.fib (m + 2)) % Nat.fib (m + 3))).card := by
  have h := momentSum_two_succ_two_term m; omega

/-- S_2(m+1) ≥ 2·S_2(m) for m ≥ 2. -/
theorem momentSum_two_succ_ge_double (m : Nat) (hm : 2 ≤ m) :
    2 * momentSum 2 m ≤ momentSum 2 (m + 1) := by
  obtain ⟨k, rfl⟩ : ∃ k, m = k + 2 := ⟨m - 2, by omega⟩
  have hrec := momentSum_two_recurrence k
  have hmono := momentSum_two_mono' k
  linarith

/-- S_2(m+1) ≤ 4·S_2(m). -/
theorem momentSum_two_succ_le_quadruple (m : Nat) :
    momentSum 2 (m + 1) ≤ 4 * momentSum 2 m := by
  match m with
  | 0 => rw [momentSum_two_zero, momentSum_two_one]; omega
  | 1 => rw [momentSum_two_one, momentSum_two_two]; omega
  | m + 2 =>
    have hrec := momentSum_two_recurrence m
    have hmono := momentSum_two_mono' (m + 1)
    linarith

/-- Additive form: S_2(m+1) + 2·S_2(m-2) = 2·S_2(m) + 2·S_2(m-1) for m ≥ 2. -/
theorem momentSum_two_succ_excess (m : Nat) (hm : 2 ≤ m) :
    momentSum 2 (m + 1) + 2 * momentSum 2 (m - 2) =
    2 * momentSum 2 m + 2 * momentSum 2 (m - 1) := by
  obtain ⟨k, rfl⟩ : ∃ k, m = k + 2 := ⟨m - 2, by omega⟩
  simp only [show k + 2 - 2 = k from by omega, show k + 2 - 1 = k + 1 from by omega]
  exact momentSum_two_recurrence k

-- ══════════════════════════════════════════════════════════════
-- S_2 divisibility
-- ══════════════════════════════════════════════════════════════

/-- S_2(m) is odd iff m = 0. -/
theorem momentSum_two_odd_iff (m : Nat) :
    ¬ (2 ∣ momentSum 2 m) ↔ m = 0 := by
  constructor
  · intro h; by_contra hne; exact h (momentSum_two_even m (Nat.pos_of_ne_zero hne))
  · intro h; rw [h, momentSum_two_zero]; omega

/-- 4 ∣ S_2(m) for m ≥ 4. -/
theorem momentSum_two_mod_four (m : Nat) (hm : 4 ≤ m) : 4 ∣ momentSum 2 m := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 | 1 | 2 | 3 => omega
    | 4 => exact ⟨9, by rw [momentSum_two_four]⟩
    | 5 => exact ⟨22, by rw [momentSum_two_five]⟩
    | 6 => exact ⟨55, by rw [momentSum_two_six]⟩
    | m + 7 =>
      have hrec := momentSum_two_recurrence (m + 4)
      have h4 := ih (m + 4) (by omega) (by omega)
      have h5 := ih (m + 5) (by omega) (by omega)
      have h6 := ih (m + 6) (by omega) (by omega)
      -- S(m+7) + 2S(m+4) = 2S(m+6) + 2S(m+5)
      -- 4|S(m+4), 4|S(m+5), 4|S(m+6)
      -- So 4 | (2S(m+6) + 2S(m+5) - 2S(m+4)) = S(m+7)
      obtain ⟨a, ha⟩ := h4; obtain ⟨b, hb⟩ := h5; obtain ⟨c, hc⟩ := h6
      -- S(m+7) + 8a = 8c + 8b, so S(m+7) = 8(c+b) - 8a = 4·(2(c+b) - 2a)
      -- Need: 4 | S(m+7), i.e., ∃ k, S(m+7) = 4k
      -- S(m+7) + 8a = 8c + 8b → S(m+7) = 8c + 8b - 8a
      -- Since a ≤ b (from monotonicity S(m+4) ≤ S(m+5)), 8a ≤ 8b ≤ 8b + 8c
      suffices h : momentSum 2 (m + 7) + 4 * (2 * a) = 4 * (2 * c + 2 * b) by
        exact ⟨2 * c + 2 * b - 2 * a, by omega⟩
      linarith

-- ══════════════════════════════════════════════════════════════
-- S_2 vs E00 comparison
-- ══════════════════════════════════════════════════════════════

/-- E00(m) ≤ S_2(m) for m ≥ 1. -/
theorem momentSum_two_ge_exactWeightCollision (m : Nat) (hm : 1 ≤ m) :
    exactWeightCollision m ≤ momentSum 2 m := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => omega
    | 1 =>
      rw [exactWeightCollision_eq_sum, momentSum_two_one]
      simp [Finset.sum_range_succ, Finset.range_zero, Finset.sum_empty, momentSum_two_zero]
    | 2 =>
      have he := exactWeightCollision_eq_sum 2
      simp [Finset.sum_range_succ, Finset.range_zero, Finset.sum_empty,
        momentSum_two_zero, momentSum_two_one] at he
      rw [momentSum_two_two]; omega
    | m + 3 =>
      have hes := exactWeightCollision_succ (m + 2)
      have hge := momentSum_two_succ_ge_double (m + 2) (by omega)
      have him := ih (m + 2) (by omega) (by omega)
      linarith

/-- E00(m+1) ≥ 2·E00(m) for m ≥ 1. -/
theorem exactWeightCollision_double (m : Nat) (hm : 1 ≤ m) :
    2 * exactWeightCollision m ≤ exactWeightCollision (m + 1) := by
  rw [exactWeightCollision_succ]
  have := momentSum_two_ge_exactWeightCollision m hm
  omega

/-- E00(m) ≥ m for all m. -/
theorem exactWeightCollision_ge_linear (m : Nat) : m ≤ exactWeightCollision m := by
  induction m with
  | zero => omega
  | succ m ih =>
    rw [exactWeightCollision_succ]
    have := momentSum_pos' 2 m
    omega

-- ══════════════════════════════════════════════════════════════
-- Recurrence uniqueness
-- ══════════════════════════════════════════════════════════════

/-- A 3rd-order recurrence is uniquely determined by its initial values. -/
theorem recurrence_unique {f g : Nat → Nat}
    (hf : ∀ m, f (m + 3) + 2 * f m = 2 * f (m + 2) + 2 * f (m + 1))
    (hg : ∀ m, g (m + 3) + 2 * g m = 2 * g (m + 2) + 2 * g (m + 1))
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

/-- S_2 is the unique sequence satisfying the recurrence with initial values 1, 2, 6. -/
theorem momentSum_two_determined {f : Nat → Nat}
    (hrec : ∀ m, f (m + 3) + 2 * f m = 2 * f (m + 2) + 2 * f (m + 1))
    (h0 : f 0 = 1) (h1 : f 1 = 2) (h2 : f 2 = 6) :
    ∀ m, f m = momentSum 2 m :=
  recurrence_unique hrec momentSum_two_recurrence
    (by rw [h0, momentSum_two_zero])
    (by rw [h1, momentSum_two_one])
    (by rw [h2, momentSum_two_two])

-- ══════════════════════════════════════════════════════════════
-- S_2 high-order values by pure recurrence (no native_decide)
-- ══════════════════════════════════════════════════════════════

theorem momentSum_two_seven_rec : momentSum 2 7 = 544 := by
  have h := momentSum_two_recurrence 4
  simp only [show (4 : Nat) + 3 = 7 from rfl, show (4 : Nat) + 2 = 6 from rfl,
    show (4 : Nat) + 1 = 5 from rfl, momentSum_two_four, momentSum_two_five, momentSum_two_six] at h
  omega

theorem momentSum_two_eight_rec : momentSum 2 8 = 1352 := by
  have h := momentSum_two_recurrence 5
  simp only [show (5 : Nat) + 3 = 8 from rfl, show (5 : Nat) + 2 = 7 from rfl,
    show (5 : Nat) + 1 = 6 from rfl, momentSum_two_five, momentSum_two_six,
    momentSum_two_seven_rec] at h
  omega

theorem momentSum_two_nine_rec : momentSum 2 9 = 3352 := by
  have h := momentSum_two_recurrence 6
  simp only [show (6 : Nat) + 3 = 9 from rfl, show (6 : Nat) + 2 = 8 from rfl,
    show (6 : Nat) + 1 = 7 from rfl, momentSum_two_six, momentSum_two_seven_rec,
    momentSum_two_eight_rec] at h
  omega

-- ══════════════════════════════════════════════════════════════
-- Fiber structure bounds
-- ══════════════════════════════════════════════════════════════

/-- D(m) · F_{m+2} ≥ 2^m (average fiber bound). -/
theorem maxFiberMultiplicity_ge_avg (m : Nat) :
    X.maxFiberMultiplicity m * Nat.fib (m + 2) ≥ 2 ^ m := by
  calc 2 ^ m = ∑ x : X m, X.fiberMultiplicity x := (X.fiberMultiplicity_sum_eq_pow m).symm
    _ ≤ ∑ _ : X m, X.maxFiberMultiplicity m :=
        Finset.sum_le_sum (fun x _ => X.fiberMultiplicity_le_max x)
    _ = X.maxFiberMultiplicity m * Fintype.card (X m) := by
        simp [Finset.sum_const, Finset.card_univ, Nat.mul_comm]
    _ = X.maxFiberMultiplicity m * Nat.fib (m + 2) := by rw [X.card_eq_fib]

/-- D(m) ≤ 2^m. -/
theorem maxFiberMultiplicity_le_pow (m : Nat) :
    X.maxFiberMultiplicity m ≤ 2 ^ m := by
  obtain ⟨x, hx⟩ := X.maxFiberMultiplicity_achieved m
  rw [← hx]
  calc X.fiberMultiplicity x = (X.fiber x).card := rfl
    _ ≤ Finset.univ.card := Finset.card_le_card (Finset.subset_univ _)
    _ = 2 ^ m := by simp [Fintype.card_fin, Fintype.card_bool]

/-- d(x) ≤ 2^m for all x. -/
theorem fiberMultiplicity_le_pow (x : X m) :
    X.fiberMultiplicity x ≤ 2 ^ m :=
  (X.fiberMultiplicity_le_max x).trans (maxFiberMultiplicity_le_pow m)

/-- D(m) ≥ 1. -/
theorem maxFiberMultiplicity_ge_one (m : Nat) :
    1 ≤ X.maxFiberMultiplicity m := X.maxFiberMultiplicity_pos m

/-- At least one element achieves the max fiber multiplicity. -/
theorem maxFiberMultiplicity_achievers_pos (m : Nat) :
    0 < ((Finset.univ : Finset (X m)).filter
      (fun x => X.fiberMultiplicity x = X.maxFiberMultiplicity m)).card := by
  rw [Finset.card_pos]
  obtain ⟨x, hx⟩ := X.maxFiberMultiplicity_achieved m
  exact ⟨x, Finset.mem_filter.mpr ⟨Finset.mem_univ _, hx⟩⟩

end Omega
