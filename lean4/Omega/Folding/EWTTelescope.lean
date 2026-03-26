import Omega.Folding.MomentTriple

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- Phase 150: EWT telescope via Word³ exact triple collision
-- ══════════════════════════════════════════════════════════════

/-- EWT(m) = |{(w1,w2,w3) : Word m³ | weight w1 = weight w2 = weight w3}|. -/
theorem exactWeightTriple_eq_triple_exact (m : Nat) :
    exactWeightTriple m =
    (Finset.univ.filter (fun p : Word m × Word m × Word m =>
      weight p.1 = weight p.2.1 ∧ weight p.2.1 = weight p.2.2)).card := by
  classical
  simp only [exactWeightTriple, exactWeightCount]
  simp_rw [show ∀ n, (Finset.univ.filter (fun w : Word m => weight w = n)).card ^ 3 =
    ((Finset.univ.filter (fun w : Word m => weight w = n)) ×ˢ
     ((Finset.univ.filter (fun w : Word m => weight w = n)) ×ˢ
      (Finset.univ.filter (fun w : Word m => weight w = n)))).card from
    fun n => by simp [Finset.card_product]; ring]
  rw [← Finset.card_biUnion]
  · congr 1; ext ⟨w1, w2, w3⟩
    simp only [Finset.mem_biUnion, Finset.mem_range, Finset.mem_product,
      Finset.mem_filter, Finset.mem_univ, true_and]
    constructor
    · rintro ⟨n, _, hw1, hw2, hw3⟩; exact ⟨hw1.trans hw2.symm, hw2.trans hw3.symm⟩
    · intro ⟨h12, h23⟩
      exact ⟨weight w1, X.weight_lt_fib w1, rfl, h12.symm, (h12.trans h23).symm⟩
  · intro n _ n' _ hne
    simp only [Function.onFun, Finset.disjoint_left, Finset.mem_product, Finset.mem_filter,
      Finset.mem_univ, true_and]
    intro ⟨w1, _, _⟩ ⟨hw1, _⟩ ⟨hw1', _⟩
    exact hne (hw1.symm.trans hw1')

-- ══════════════════════════════════════════════════════════════
-- Exact triple collision class
-- ══════════════════════════════════════════════════════════════

/-- Exact triple collision class for given last-bit pattern. -/
def exactTripleCollisionClass (m : Nat) (b1 b2 b3 : Bool) : Finset (Word m × Word m × Word m) :=
  Finset.univ.filter (fun p : Word m × Word m × Word m =>
    weight p.1 + (if b1 then Nat.fib (m + 2) else 0) =
    weight p.2.1 + (if b2 then Nat.fib (m + 2) else 0) ∧
    weight p.2.1 + (if b2 then Nat.fib (m + 2) else 0) =
    weight p.2.2 + (if b3 then Nat.fib (m + 2) else 0))

set_option maxHeartbeats 400000 in
/-- Each last-bit slice at level m+1 bijects to an exactTripleCollisionClass at level m. -/
private theorem exactTripleClass_card_eq (m : Nat) (b1 b2 b3 : Bool) :
    (Finset.univ.filter (fun p : Word (m + 1) × Word (m + 1) × Word (m + 1) =>
      weight p.1 = weight p.2.1 ∧ weight p.2.1 = weight p.2.2 ∧
      p.1 ⟨m, by omega⟩ = b1 ∧ p.2.1 ⟨m, by omega⟩ = b2 ∧ p.2.2 ⟨m, by omega⟩ = b3)).card =
    (exactTripleCollisionClass m b1 b2 b3).card := by
  unfold exactTripleCollisionClass
  apply Finset.card_bij
    (fun (p : Word (m + 1) × Word (m + 1) × Word (m + 1)) _ =>
      (truncate p.1, truncate p.2.1, truncate p.2.2))
  · intro ⟨w1, w2, w3⟩ hp
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hp ⊢
    constructor
    · have := hp.1; rw [weight, hp.2.2.1, weight, hp.2.2.2.1] at this; exact this
    · have := hp.2.1; rw [weight, hp.2.2.2.1, weight, hp.2.2.2.2] at this; exact this
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

/-- EWT(m+1) = sum of 8 exact triple collision classes. -/
theorem exactWeightTriple_lastBit_split (m : Nat) :
    exactWeightTriple (m + 1) =
    (exactTripleCollisionClass m false false false).card +
    (exactTripleCollisionClass m false false true).card +
    (exactTripleCollisionClass m false true false).card +
    (exactTripleCollisionClass m false true true).card +
    (exactTripleCollisionClass m true false false).card +
    (exactTripleCollisionClass m true false true).card +
    (exactTripleCollisionClass m true true false).card +
    (exactTripleCollisionClass m true true true).card := by
  classical
  rw [exactWeightTriple_eq_triple_exact]
  set T := Finset.univ.filter (fun p : Word (m + 1) × Word (m + 1) × Word (m + 1) =>
    weight p.1 = weight p.2.1 ∧ weight p.2.1 = weight p.2.2)
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
  simp only [Fintype.sum_prod_type, Fintype.univ_bool,
    Finset.sum_insert (by decide : true ∉ ({false} : Finset Bool)),
    Finset.sum_singleton]
  have hf : ∀ b1 b2 b3 : Bool,
      (T.filter (fun p => lastBits p = (b1, b2, b3))).card =
      (Finset.univ.filter (fun p : Word (m + 1) × Word (m + 1) × Word (m + 1) =>
        weight p.1 = weight p.2.1 ∧ weight p.2.1 = weight p.2.2 ∧
        p.1 ⟨m, by omega⟩ = b1 ∧ p.2.1 ⟨m, by omega⟩ = b2 ∧
        p.2.2 ⟨m, by omega⟩ = b3)).card := by
    intro b1 b2 b3; congr 1; ext ⟨w1, w2, w3⟩
    simp only [T, lastBits, Finset.mem_filter, Finset.mem_univ, true_and, Prod.mk.injEq]
    tauto
  have h := exactTripleClass_card_eq m
  simp only [hf, h]; omega

-- ══════════════════════════════════════════════════════════════
-- Orbit identification
-- ══════════════════════════════════════════════════════════════

/-- exactTripleCollisionClass(fff) = exactWeightTriple. -/
theorem exactTripleClass_fff (m : Nat) :
    (exactTripleCollisionClass m false false false).card = exactWeightTriple m := by
  rw [exactWeightTriple_eq_triple_exact]; rfl

/-- exactTripleCollisionClass(ttt) = exactWeightTriple. -/
theorem exactTripleClass_ttt (m : Nat) :
    (exactTripleCollisionClass m true true true).card = exactWeightTriple m := by
  rw [exactWeightTriple_eq_triple_exact]; congr 1; ext ⟨w1, w2, w3⟩
  simp only [exactTripleCollisionClass, Finset.mem_filter, Finset.mem_univ, true_and, ite_true]
  constructor <;> intro ⟨h1, h2⟩ <;> constructor <;> omega

end Omega
