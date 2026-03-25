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

end Omega
