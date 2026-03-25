import Omega.Folding.MomentRecurrence

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- S_3(m+1) last-bit split into 8 collision classes
-- ══════════════════════════════════════════════════════════════

/-- Helper: triple collision class for given bit offsets. -/
def tripleCollisionClass (m : Nat) (b1 b2 b3 : Bool) : Finset (Word m × Word m × Word m) :=
  Finset.univ.filter (fun p : Word m × Word m × Word m =>
    (weight p.1 + if b1 then Nat.fib (m + 2) else 0) % Nat.fib (m + 3) =
    (weight p.2.1 + if b2 then Nat.fib (m + 2) else 0) % Nat.fib (m + 3) ∧
    (weight p.2.1 + if b2 then Nat.fib (m + 2) else 0) % Nat.fib (m + 3) =
    (weight p.2.2 + if b3 then Nat.fib (m + 2) else 0) % Nat.fib (m + 3))

set_option maxHeartbeats 400000 in
/-- Each last-bit slice at level m+1 bijects to a tripleCollisionClass at level m. -/
private theorem tripleClass_card_eq (m : Nat) (b1 b2 b3 : Bool) :
    (Finset.univ.filter (fun p : Word (m + 1) × Word (m + 1) × Word (m + 1) =>
      weight p.1 % Nat.fib (m + 3) = weight p.2.1 % Nat.fib (m + 3) ∧
      weight p.2.1 % Nat.fib (m + 3) = weight p.2.2 % Nat.fib (m + 3) ∧
      p.1 ⟨m, by omega⟩ = b1 ∧ p.2.1 ⟨m, by omega⟩ = b2 ∧ p.2.2 ⟨m, by omega⟩ = b3)).card =
    (tripleCollisionClass m b1 b2 b3).card := by
  unfold tripleCollisionClass
  apply Finset.card_bij
    (fun (p : Word (m + 1) × Word (m + 1) × Word (m + 1)) _ =>
      (truncate p.1, truncate p.2.1, truncate p.2.2))
  · intro ⟨w1, w2, w3⟩ hp
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hp ⊢
    rw [weight, hp.2.2.1, weight, hp.2.2.2.1, weight, hp.2.2.2.2] at hp
    exact ⟨hp.1, hp.2.1⟩
  · intro ⟨w1a, w2a, w3a⟩ ha ⟨w1b, w2b, w3b⟩ hb heq
    simp only [Finset.mem_filter, Finset.mem_univ, true_and, Prod.mk.injEq] at ha hb heq ⊢
    exact ⟨by rw [← X.snoc_truncate_last w1a, ← X.snoc_truncate_last w1b,
                   heq.1, ha.2.2.1, hb.2.2.1],
           by rw [← X.snoc_truncate_last w2a, ← X.snoc_truncate_last w2b,
                   heq.2.1, ha.2.2.2.1, hb.2.2.2.1],
           by rw [← X.snoc_truncate_last w3a, ← X.snoc_truncate_last w3b,
                   heq.2.2, ha.2.2.2.2, hb.2.2.2.2]⟩
  · intro ⟨v1, v2, v3⟩ hv
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
    refine ⟨(snoc v1 b1, snoc v2 b2, snoc v3 b3), ?_, by simp⟩
    refine ⟨?_, ?_, by simp, by simp, by simp⟩
    · rw [weight_snoc, weight_snoc]; exact hv.1
    · rw [weight_snoc, weight_snoc]; exact hv.2

/-- S_3(m+1) = Σ_{b1,b2,b3} |tripleCollisionClass m b1 b2 b3|. -/
theorem momentSum_three_lastBit_split (m : Nat) :
    momentSum 3 (m + 1) =
    (tripleCollisionClass m false false false).card +
    (tripleCollisionClass m false false true).card +
    (tripleCollisionClass m false true false).card +
    (tripleCollisionClass m false true true).card +
    (tripleCollisionClass m true false false).card +
    (tripleCollisionClass m true false true).card +
    (tripleCollisionClass m true true false).card +
    (tripleCollisionClass m true true true).card := by
  classical
  rw [momentSum_three_eq_triple_collision, triple_collision_iff_weight_mod]
  rw [show Nat.fib ((m + 1) + 2) = Nat.fib (m + 3) from by ring_nf]
  -- Rewrite the full collision set as a disjoint union of 8 slices by last bits
  -- then apply tripleClass_card_eq to each slice.
  -- Total = Σ over all 8 bit-triples of (slice card) = Σ (tripleCollisionClass card)
  -- Strategy: each element belongs to exactly one slice determined by its last bits.
  -- Use: card S = Σ_{b} card(S ∩ {last bits = b})
  -- The key bijection
  have h := tripleClass_card_eq m
  -- Partition the collision set into 8 disjoint parts by last bits
  set T := Finset.univ.filter (fun p : Word (m + 1) × Word (m + 1) × Word (m + 1) =>
    weight p.1 % Nat.fib (m + 3) = weight p.2.1 % Nat.fib (m + 3) ∧
    weight p.2.1 % Nat.fib (m + 3) = weight p.2.2 % Nat.fib (m + 3))
  let lastBits : Word (m + 1) × Word (m + 1) × Word (m + 1) → Bool × Bool × Bool :=
    fun p => (p.1 ⟨m, by omega⟩, p.2.1 ⟨m, by omega⟩, p.2.2 ⟨m, by omega⟩)
  have hpartition : T.card =
      ∑ b : Bool × Bool × Bool,
        (T.filter (fun p => lastBits p = b)).card := by
    rw [← Finset.card_biUnion]
    · congr 1; ext p
      simp only [Finset.mem_biUnion, Finset.mem_filter, Finset.mem_univ, true_and]
      exact ⟨fun hp => ⟨lastBits p, hp, rfl⟩, fun ⟨_, hp, _⟩ => hp⟩
    · intro b _ b' _ hne
      apply Finset.disjoint_filter.mpr
      intro p _ h1 h2; exact hne (h1.symm.trans h2)
  rw [hpartition]
  -- Expand the sum over Bool × Bool × Bool into 8 explicit terms
  simp only [Fintype.sum_prod_type, Fintype.univ_bool, Finset.sum_insert (by decide : true ∉ ({false} : Finset Bool)),
    Finset.sum_singleton]
  -- Each filter term equals the restricted collision set
  have hf : ∀ b1 b2 b3 : Bool,
      (T.filter (fun p => lastBits p = (b1, b2, b3))).card =
      (Finset.univ.filter (fun p : Word (m + 1) × Word (m + 1) × Word (m + 1) =>
        weight p.1 % Nat.fib (m + 3) = weight p.2.1 % Nat.fib (m + 3) ∧
        weight p.2.1 % Nat.fib (m + 3) = weight p.2.2 % Nat.fib (m + 3) ∧
        p.1 ⟨m, by omega⟩ = b1 ∧ p.2.1 ⟨m, by omega⟩ = b2 ∧
        p.2.2 ⟨m, by omega⟩ = b3)).card := by
    intro b1 b2 b3; congr 1; ext ⟨w1, w2, w3⟩
    simp only [T, lastBits, Finset.mem_filter, Finset.mem_univ, true_and, Prod.mk.injEq]
    tauto
  simp only [hf, h]; omega

-- ══════════════════════════════════════════════════════════════
-- Bit-flip cancellation (Finset equality)
-- ══════════════════════════════════════════════════════════════

/-- T(1,1,1) = T(0,0,0): adding F_{m+2} to all three offsets cancels. -/
theorem tripleCollisionClass_cancel_111 (m : Nat) :
    tripleCollisionClass m true true true = tripleCollisionClass m false false false := by
  unfold tripleCollisionClass; ext ⟨v1, v2, v3⟩
  simp only [Finset.mem_filter, Finset.mem_univ, true_and, ↓reduceIte, Nat.add_zero]
  exact ⟨fun ⟨h1, h2⟩ => ⟨Nat.ModEq.add_right_cancel' _ h1, Nat.ModEq.add_right_cancel' _ h2⟩,
         fun ⟨h1, h2⟩ => ⟨Nat.ModEq.add_right _ h1, Nat.ModEq.add_right _ h2⟩⟩

-- ══════════════════════════════════════════════════════════════
-- Permutation symmetries (card equalities via bijection)
-- ══════════════════════════════════════════════════════════════

/-- Swapping (v1,v2,v3) → (v2,v1,v3) sends T(b1,b2,b3).card = T(b2,b1,b3).card. -/
theorem tripleCollisionClass_swap12 (m : Nat) (b1 b2 b3 : Bool) :
    (tripleCollisionClass m b1 b2 b3).card =
    (tripleCollisionClass m b2 b1 b3).card := by
  unfold tripleCollisionClass
  apply Finset.card_bij (fun (p : Word m × Word m × Word m) _ => (p.2.1, p.1, p.2.2))
  · intro ⟨v1, v2, v3⟩ hv
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
    exact ⟨hv.1.symm, hv.1.trans hv.2⟩
  · intro ⟨a1, a2, a3⟩ _ ⟨b1', b2', b3'⟩ _ h
    simp only [Prod.mk.injEq] at h; exact Prod.ext h.2.1 (Prod.ext h.1 h.2.2)
  · intro ⟨v1, v2, v3⟩ hv
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
    exact ⟨(v2, v1, v3), ⟨hv.1.symm, hv.1.trans hv.2⟩, rfl⟩

/-- Swapping (v1,v2,v3) → (v1,v3,v2) sends T(b1,b2,b3).card = T(b1,b3,b2).card. -/
theorem tripleCollisionClass_swap23 (m : Nat) (b1 b2 b3 : Bool) :
    (tripleCollisionClass m b1 b2 b3).card =
    (tripleCollisionClass m b1 b3 b2).card := by
  unfold tripleCollisionClass
  apply Finset.card_bij (fun (p : Word m × Word m × Word m) _ => (p.1, p.2.2, p.2.1))
  · intro ⟨v1, v2, v3⟩ hv
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
    exact ⟨hv.1.trans hv.2, hv.2.symm⟩
  · intro ⟨a1, a2, a3⟩ _ ⟨b1', b2', b3'⟩ _ h
    simp only [Prod.mk.injEq] at h; exact Prod.ext h.1 (Prod.ext h.2.2 h.2.1)
  · intro ⟨v1, v2, v3⟩ hv
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
    exact ⟨(v1, v3, v2), ⟨hv.1.trans hv.2, hv.2.symm⟩, rfl⟩

/-- Swapping (v1,v2,v3) → (v3,v2,v1) sends T(b1,b2,b3).card = T(b3,b2,b1).card. -/
theorem tripleCollisionClass_swap13 (m : Nat) (b1 b2 b3 : Bool) :
    (tripleCollisionClass m b1 b2 b3).card =
    (tripleCollisionClass m b3 b2 b1).card := by
  unfold tripleCollisionClass
  apply Finset.card_bij (fun (p : Word m × Word m × Word m) _ => (p.2.2, p.2.1, p.1))
  · intro ⟨v1, v2, v3⟩ hv
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
    exact ⟨hv.2.symm, hv.1.symm⟩
  · intro ⟨a1, a2, a3⟩ _ ⟨b1', b2', b3'⟩ _ h
    simp only [Prod.mk.injEq] at h; exact Prod.ext h.2.2 (Prod.ext h.2.1 h.1)
  · intro ⟨v1, v2, v3⟩ hv
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
    exact ⟨(v3, v2, v1), ⟨hv.2.symm, hv.1.symm⟩, rfl⟩

-- ══════════════════════════════════════════════════════════════
-- S_3(m+1) = 2·T(0,0,0) + 3·T(0,0,1) + 3·T(0,1,1)
-- ══════════════════════════════════════════════════════════════

/-- S_3(m+1) reduces to 3 distinct collision classes via symmetry. -/
theorem momentSum_three_succ_three_term (m : Nat) :
    momentSum 3 (m + 1) =
    2 * (tripleCollisionClass m false false false).card +
    3 * (tripleCollisionClass m false false true).card +
    3 * (tripleCollisionClass m false true true).card := by
  rw [momentSum_three_lastBit_split]
  -- T111 = T000 by Finset equality
  rw [congrArg Finset.card (tripleCollisionClass_cancel_111 m)]
  -- Orbit {T001, T010, T100}: T001 = T010 (swap23), T010 = T100 (swap12)
  have h1 := tripleCollisionClass_swap23 m false false true   -- T001 = T010
  have h2 := tripleCollisionClass_swap12 m false true false   -- T010 = T100
  -- Orbit {T011, T101, T110}: T011 = T101 (swap12), T101 = T110 (swap23)
  have h3 := tripleCollisionClass_swap12 m false true true    -- T011 = T101
  have h4 := tripleCollisionClass_swap23 m true false true    -- T101 = T110
  omega

-- ══════════════════════════════════════════════════════════════
-- E000 = exactWeightTriple (Σ ewc³)
-- ══════════════════════════════════════════════════════════════

/-- T(0,0,0) = Σ_n ewc(m,n)³: all three words share the same weight. -/
theorem tripleCollisionClass_000_eq_ewcCube (m : Nat) :
    (tripleCollisionClass m false false false).card = exactWeightTriple m := by
  classical
  unfold tripleCollisionClass
  simp only [Bool.false_eq_true, ↓reduceIte, Nat.add_zero]
  -- Since weight < F_{m+3}, mod is identity
  have hmod : ∀ v : Word m, weight v % Nat.fib (m + 3) = weight v :=
    fun v => Nat.mod_eq_of_lt (X.weight_lt_fib v)
  simp_rw [hmod]
  unfold exactWeightTriple exactWeightCount
  -- Now: |{(v1,v2,v3) : wt v1 = wt v2 ∧ wt v2 = wt v3}| = Σ_n ewc(n)³
  -- ewc(n)³ = |{v1:wt=n}| · |{v2:wt=n}| · |{v3:wt=n}| = |{v1:wt=n} ×ˢ {v2:wt=n} ×ˢ {v3:wt=n}|
  have hprod : ∀ n, (Finset.univ.filter (fun w : Word m => weight w = n)).card ^ 3 =
      ((Finset.univ.filter (fun w : Word m => weight w = n)) ×ˢ
       ((Finset.univ.filter (fun w : Word m => weight w = n)) ×ˢ
        (Finset.univ.filter (fun w : Word m => weight w = n)))).card := by
    intro n; rw [Finset.card_product, Finset.card_product]; ring
  simp_rw [hprod]; symm
  rw [← Finset.card_biUnion]
  · congr 1; ext ⟨v1, v2, v3⟩
    simp only [Finset.mem_biUnion, Finset.mem_range, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    constructor
    · rintro ⟨n, _, h1, h2, h3⟩; exact ⟨h1 ▸ h2 ▸ rfl, h2 ▸ h3 ▸ rfl⟩
    · intro ⟨h12, h23⟩
      exact ⟨weight v1, X.weight_lt_fib v1, rfl, h12.symm, (h12.trans h23).symm⟩
  · intro n _ n' _ hne
    simp only [Function.onFun, Finset.disjoint_left, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    intro ⟨v1, _, _⟩ ⟨h1, _⟩ ⟨h2, _⟩; exact hne (h1.symm.trans h2)

-- ══════════════════════════════════════════════════════════════
-- E001 and E011 in ewc terms (definitions)
-- ══════════════════════════════════════════════════════════════

/-- Triple cross-correlation: Σ ewc(n)^a · ewc(n+d)^b. -/
def tripleCorr (m d : Nat) (a b : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)),
    exactWeightCount m n ^ a * exactWeightCount m (n + d) ^ b

/-- S_3(m+1) = 2·exactWeightTriple(m) + 3·T001(m) + 3·T011(m). -/
theorem momentSum_three_succ_ewt_form (m : Nat) :
    momentSum 3 (m + 1) =
    2 * exactWeightTriple m +
    3 * (tripleCollisionClass m false false true).card +
    3 * (tripleCollisionClass m false true true).card := by
  rw [momentSum_three_succ_three_term, tripleCollisionClass_000_eq_ewcCube]

-- ══════════════════════════════════════════════════════════════
-- Cross-correlation-squared definitions (CCSH, CCSL)
-- ══════════════════════════════════════════════════════════════

/-- Cross-correlation-squared high: Σ ewc(n)² · ewc(n + F_{m+2}). -/
def crossCorrSqHigh (m : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)),
    exactWeightCount m n ^ 2 * exactWeightCount m (n + Nat.fib (m + 2))

/-- Cross-correlation-squared low: Σ ewc(n) · ewc(n + F_{m+2})². -/
def crossCorrSqLow (m : Nat) : Nat :=
  ∑ n ∈ Finset.range (Nat.fib (m + 3)),
    exactWeightCount m n * exactWeightCount m (n + Nat.fib (m + 2)) ^ 2

/-- CCSH = tripleCorr specialized to (2,1) at shift F_{m+2}. -/
theorem crossCorrSqHigh_eq_tripleCorr (m : Nat) :
    crossCorrSqHigh m = tripleCorr m (Nat.fib (m + 2)) 2 1 := by
  unfold crossCorrSqHigh tripleCorr; congr 1; ext n; ring

/-- CCSL = tripleCorr specialized to (1,2) at shift F_{m+2}. -/
theorem crossCorrSqLow_eq_tripleCorr (m : Nat) :
    crossCorrSqLow m = tripleCorr m (Nat.fib (m + 2)) 1 2 := by
  unfold crossCorrSqLow tripleCorr; congr 1; ext n; ring

end Omega

-- Below: unfinished exactWeightTriple_succ infrastructure, excluded from build.
-- Will be completed in a future phase with codex-consultant assistance.
#exit

private def ewtClass (m : Nat) (b1 b2 b3 : Bool) : Finset (Word m × Word m × Word m) :=
  Finset.univ.filter (fun p =>
    weight p.1 + (if b1 then Nat.fib (m + 2) else 0) =
    weight p.2.1 + (if b2 then Nat.fib (m + 2) else 0) ∧
    weight p.2.1 + (if b2 then Nat.fib (m + 2) else 0) =
    weight p.2.2 + (if b3 then Nat.fib (m + 2) else 0))

private theorem ewtClass_000 (m : Nat) : (ewtClass m false false false).card = exactWeightTriple m := by
  have : ewtClass m false false false = tripleCollisionClass m false false false := by
    unfold ewtClass tripleCollisionClass; congr 1; ext ⟨v1, v2, v3⟩
    simp only [Finset.mem_filter, Finset.mem_univ, true_and, Bool.false_eq_true, ↓reduceIte, Nat.add_zero]
    have hm1 := Nat.mod_eq_of_lt (X.weight_lt_fib v1)
    have hm2 := Nat.mod_eq_of_lt (X.weight_lt_fib v2)
    have hm3 := Nat.mod_eq_of_lt (X.weight_lt_fib v3)
    constructor <;> intro ⟨h1, h2⟩ <;> exact ⟨by omega, by omega⟩
  rw [this]; exact tripleCollisionClass_000_eq_ewcCube m

private theorem ewtClass_111 (m : Nat) : (ewtClass m true true true).card = exactWeightTriple m := by
  rw [show (ewtClass m true true true).card = (ewtClass m false false false).card from by
    unfold ewtClass; congr 1; ext ⟨v1, v2, v3⟩
    simp only [Finset.mem_filter, Finset.mem_univ, true_and, ↓reduceIte]; omega]
  exact ewtClass_000 m

private theorem ewtClass_ccsl (m : Nat) (b1 b2 b3 : Bool)
    (h : (b1 = false ∧ b2 = false ∧ b3 = true) ∨
         (b1 = false ∧ b2 = true ∧ b3 = false) ∨
         (b1 = true ∧ b2 = false ∧ b3 = false)) :
    (ewtClass m b1 b2 b3).card = crossCorrSqLow m := by
  -- All three cases count triples where two words share weight n+F'
  -- and the third has weight n, giving Σ ewc(n)·ewc(n+F')²
  -- We show (0,0,1) case, then reduce others to it via permutation bijections.
  suffices h001 : (ewtClass m false false true).card = crossCorrSqLow m by
    rcases h with ⟨rfl, rfl, rfl⟩ | ⟨rfl, rfl, rfl⟩ | ⟨rfl, rfl, rfl⟩
    · exact h001
    · -- (0,1,0): v1=v3=n, v2=n-F'. bij (v1,v2,v3) ↦ (v1,v3,v2) maps to (0,0,1)
      rw [← h001]; unfold ewtClass; simp only [↓reduceIte, Nat.add_zero]
      apply Finset.card_bij (fun (p : Word m × Word m × Word m) _ => (p.1, p.2.2, p.2.1))
      · intro ⟨v1, v2, v3⟩ hv; simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢; omega
      · intro ⟨a1, a2, a3⟩ _ ⟨b1, b2, b3⟩ _ h
        simp only [Prod.mk.injEq] at h; exact Prod.ext h.1 (Prod.ext h.2.2 h.2.1)
      · intro ⟨v1, v2, v3⟩ hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and]
        exact ⟨(v1, v3, v2), ⟨by linarith [hv.1, hv.2], by linarith [hv.1, hv.2]⟩, rfl⟩
    · -- (1,0,0): v2=v3=n, v1=n-F'. bij (v1,v2,v3) ↦ (v2,v3,v1) maps to (0,0,1)
      rw [← h001]; unfold ewtClass; simp only [↓reduceIte, Nat.add_zero]
      apply Finset.card_bij (fun (p : Word m × Word m × Word m) _ => (p.2.1, p.2.2, p.1))
      · intro ⟨v1, v2, v3⟩ hv; simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢; omega
      · intro ⟨a1, a2, a3⟩ _ ⟨b1, b2, b3⟩ _ h
        simp only [Prod.mk.injEq] at h; exact Prod.ext h.2.2 (Prod.ext h.1 h.2.1)
      · intro ⟨v1, v2, v3⟩ hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and]
        exact ⟨(v3, v1, v2), ⟨by linarith [hv.1, hv.2], by linarith [hv.1, hv.2]⟩, rfl⟩
  -- Now prove the (0,0,1) case: wt v1 = wt v2, wt v2 = wt v3 + F'
  -- Count = Σ_{n < F_{m+1}} ewc(n+F')² · ewc(n) = CCSL = Σ ewc(n)·ewc(n+F')²
  -- (0,0,1): wt v1 = wt v2, wt v2 = wt v3 + F'
  -- Group by v3's weight k: v1,v2 have weight k+F', v3 has weight k
  -- Count = Σ_{k < F_{m+1}} ewc(k+F')² · ewc(k) = CCSL
  classical
  unfold ewtClass crossCorrSqLow
  simp only [↓reduceIte, Nat.add_zero]
  symm; rw [← Finset.card_biUnion]
  · congr 1; ext ⟨v1, v2, v3⟩
    simp only [Finset.mem_biUnion, Finset.mem_range, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    constructor
    · rintro ⟨k, _, ⟨h1, h2⟩, ⟨h3, h4⟩, h5⟩; exact ⟨by omega, by omega⟩
    · intro ⟨h12, h23⟩
      refine ⟨weight v2.2, ?_, ⟨⟨by omega, rfl⟩, ⟨by omega, rfl⟩, by omega⟩⟩
      have := X.weight_lt_fib v2.2; have := Nat.fib_add_two (n := m + 1); omega
  · intro k _ k' _ hne
    simp only [Function.onFun, Finset.disjoint_left, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    intro ⟨_, _, v3⟩ ⟨_, ⟨_, h2⟩, _⟩ ⟨_, ⟨_, h2'⟩, _⟩; exact hne (by omega)

private theorem ewtClass_ccsh (m : Nat) (b1 b2 b3 : Bool)
    (h : (b1 = false ∧ b2 = true ∧ b3 = true) ∨
         (b1 = true ∧ b2 = false ∧ b3 = true) ∨
         (b1 = true ∧ b2 = true ∧ b3 = false)) :
    (ewtClass m b1 b2 b3).card = crossCorrSqHigh m := by
  suffices h011 : (ewtClass m false true true).card = crossCorrSqHigh m by
    rcases h with ⟨rfl, rfl, rfl⟩ | ⟨rfl, rfl, rfl⟩ | ⟨rfl, rfl, rfl⟩
    · exact h011
    · -- (1,0,1) → (0,1,1) via (v1,v2,v3) ↦ (v2,v1,v3)
      rw [← h011]; unfold ewtClass; simp only [↓reduceIte, Nat.add_zero]
      apply Finset.card_bij (fun (p : Word m × Word m × Word m) _ => (p.2.1, p.1, p.2.2))
      · intro ⟨v1, v2, v3⟩ hv; simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢; omega
      · intro ⟨a1, a2, a3⟩ _ ⟨b1, b2, b3⟩ _ h
        simp only [Prod.mk.injEq] at h; exact Prod.ext h.2.1 (Prod.ext h.1 h.2.2)
      · intro ⟨v1, v2, v3⟩ hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢
        simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and]
        exact ⟨(v2, v1, v3), ⟨by linarith [hv.1, hv.2], by linarith [hv.1, hv.2]⟩, rfl⟩
    · -- (1,1,0) → (0,1,1) via (v1,v2,v3) ↦ (v3,v2,v1)
      rw [← h011]; unfold ewtClass; simp only [↓reduceIte, Nat.add_zero]
      apply Finset.card_bij (fun (p : Word m × Word m × Word m) _ => (p.2.2, p.2.1, p.1))
      · intro ⟨v1, v2, v3⟩ hv; simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv ⊢; omega
      · intro ⟨a1, a2, a3⟩ _ ⟨b1, b2, b3⟩ _ h
        simp only [Prod.mk.injEq] at h; exact Prod.ext h.2.2 (Prod.ext h.2.1 h.1)
      · intro ⟨v1, v2, v3⟩ hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hv
        simp only [Finset.mem_filter, Finset.mem_univ, true_and]
        exact ⟨(v3, v2, v1), ⟨by linarith [hv.1, hv.2], by linarith [hv.1, hv.2]⟩, rfl⟩
  -- (0,1,1): wt v1 = wt v2 + F', wt v2 + F' = wt v3 + F' ⟹ wt v2 = wt v3, wt v1 = wt v2 + F'
  -- Count = Σ_n ewc(n+F') · ewc(n)² = CCSH
  classical
  unfold ewtClass crossCorrSqHigh
  simp only [↓reduceIte, Nat.add_zero]
  have hsimp : ∀ p : Word m × Word m × Word m,
      (weight p.1 = weight p.2.1 + Nat.fib (m + 2) ∧
       weight p.2.1 + Nat.fib (m + 2) = weight p.2.2 + Nat.fib (m + 2)) ↔
      (weight p.1 = weight p.2.1 + Nat.fib (m + 2) ∧ weight p.2.1 = weight p.2.2) := by
    intro ⟨v1, v2, v3⟩; simp; omega
  simp_rw [hsimp]
  symm; rw [← Finset.card_biUnion]
  · congr 1; ext ⟨v1, v2, v3⟩
    simp only [Finset.mem_biUnion, Finset.mem_range, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    constructor
    · rintro ⟨k, hk, ⟨h1, h2⟩, ⟨h3, h4⟩, h5⟩; constructor <;> omega
    · intro ⟨h12, h23⟩
      refine ⟨weight v2.1, ?_, ?_⟩
      · have := X.weight_lt_fib v2.1
        have := Nat.fib_add_two (n := m + 1); omega
      · exact ⟨⟨by omega, rfl⟩, ⟨by omega, rfl⟩, by omega⟩
  · intro k _ k' _ hne
    simp only [Function.onFun, Finset.disjoint_left, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    intro ⟨_, v2, _⟩ ⟨_, ⟨_, h2⟩, _⟩ ⟨_, ⟨_, h2'⟩, _⟩; exact hne (by omega)

set_option maxHeartbeats 800000 in
/-- EWT(m+1) = 2·EWT(m) + 3·CCSH(m) + 3·CCSL(m). -/
theorem exactWeightTriple_succ (m : Nat) :
    exactWeightTriple (m + 1) =
    2 * exactWeightTriple m + 3 * crossCorrSqHigh m + 3 * crossCorrSqLow m := by
  classical
  -- Step 1: EWT(m+1) = T000(m+1).card
  rw [← tripleCollisionClass_000_eq_ewcCube (m + 1)]
  -- Step 2: T000 at level m+1 uses mod F_{m+4}, but weights < F_{m+4} so mod = identity
  unfold tripleCollisionClass
  simp only [Bool.false_eq_true, ↓reduceIte, Nat.add_zero]
  have hmod : ∀ v : Word (m + 1), weight v % Nat.fib (m + 4) = weight v :=
    fun v => Nat.mod_eq_of_lt (X.weight_lt_fib v)
  simp_rw [hmod]
  -- Step 3: Partition by last bits
  set S := Finset.univ.filter (fun p : Word (m + 1) × Word (m + 1) × Word (m + 1) =>
    weight p.1 = weight p.2.1 ∧ weight p.2.1 = weight p.2.2)
  let lb : Word (m + 1) × Word (m + 1) × Word (m + 1) → Bool × Bool × Bool :=
    fun p => (p.1 ⟨m, by omega⟩, p.2.1 ⟨m, by omega⟩, p.2.2 ⟨m, by omega⟩)
  have hpart : S.card = ∑ b : Bool × Bool × Bool, (S.filter (fun p => lb p = b)).card := by
    rw [← Finset.card_biUnion]
    · congr 1; ext p; simp only [Finset.mem_biUnion, Finset.mem_filter, Finset.mem_univ, true_and]
      exact ⟨fun hp => ⟨lb p, hp, rfl⟩, fun ⟨_, hp, _⟩ => hp⟩
    · intro b _ b' _ hne; apply Finset.disjoint_filter.mpr; intro p _ h1 h2; exact hne (h1.symm.trans h2)
  rw [hpart]
  simp only [Fintype.sum_prod_type, Fintype.univ_bool,
    Finset.sum_insert (by decide : true ∉ ({false} : Finset Bool)), Finset.sum_singleton]
  -- Step 4: Each slice bijects to ewtClass at level m
  have hbij : ∀ b1 b2 b3 : Bool,
      (S.filter (fun p => lb p = (b1, b2, b3))).card = (ewtClass m b1 b2 b3).card := by
    intro b1 b2 b3; unfold ewtClass
    apply Finset.card_bij (fun p _ => (truncate p.1, truncate p.2.1, truncate p.2.2))
    · intro ⟨w1, w2, w3⟩ hp
      simp only [S, lb, Finset.mem_filter, Finset.mem_univ, true_and, Prod.mk.injEq] at hp ⊢
      rw [weight, hp.2.1, weight, hp.2.2.1, weight, hp.2.2.2] at hp
      exact ⟨by omega, by omega⟩
    · intro ⟨w1a, w2a, w3a⟩ ha ⟨w1b, w2b, w3b⟩ hb heq
      simp only [S, lb, Finset.mem_filter, Finset.mem_univ, true_and, Prod.mk.injEq] at ha hb heq
      exact ⟨by rw [← X.snoc_truncate_last w1a, ← X.snoc_truncate_last w1b, heq.1, ha.2.1, hb.2.1],
             by rw [← X.snoc_truncate_last w2a, ← X.snoc_truncate_last w2b, heq.2.1, ha.2.2.1, hb.2.2.1],
             by rw [← X.snoc_truncate_last w3a, ← X.snoc_truncate_last w3b, heq.2.2, ha.2.2.2, hb.2.2.2]⟩
    · intro ⟨v1, v2, v3⟩ hv
      simp only [ewtClass, Finset.mem_filter, Finset.mem_univ, true_and] at hv
      simp only [S, lb, Finset.mem_filter, Finset.mem_univ, true_and, Prod.mk.injEq]
      exact ⟨(snoc v1 b1, snoc v2 b2, snoc v3 b3),
        ⟨⟨by rw [weight_snoc, weight_snoc]; omega, by rw [weight_snoc, weight_snoc]; omega⟩,
         by simp, by simp, by simp⟩, by simp⟩
  simp only [hbij]
  -- Step 5: Classify each ewtClass
  rw [ewtClass_000 m, ewtClass_111 m]
  rw [ewtClass_ccsl m false false true (Or.inl ⟨rfl, rfl, rfl⟩)]
  rw [ewtClass_ccsl m false true false (Or.inr (Or.inl ⟨rfl, rfl, rfl⟩))]
  rw [ewtClass_ccsl m true false false (Or.inr (Or.inr ⟨rfl, rfl, rfl⟩))]
  rw [ewtClass_ccsh m false true true (Or.inl ⟨rfl, rfl, rfl⟩)]
  rw [ewtClass_ccsh m true false true (Or.inr (Or.inl ⟨rfl, rfl, rfl⟩))]
  rw [ewtClass_ccsh m true true false (Or.inr (Or.inr ⟨rfl, rfl, rfl⟩))]
  omega

end Omega
