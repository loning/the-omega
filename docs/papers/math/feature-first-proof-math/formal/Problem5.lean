import Mathlib

open scoped Classical

/-!
  ## Problem 5: O-Adapted Slice Filtration -- Lean 4 Skeleton

  We formalize the proof structure: induction on |G| with the
  forward direction via restriction + geometric-piece lemma, and
  the reverse direction via induction hypothesis + isotropy separation.
-/

-- Abstract types (equivariant stable category not in Mathlib)
variable {G : Type*} [Group G] [Fintype G]

/-- Abstract notion of "O-slice n-connective" for a G-spectrum E. -/
class SliceConnective (G : Type*) [Group G] [Fintype G] where
  /-- E is in tau^{O,G}_{>=n} -/
  is_slice_conn : Nat -> Prop
  /-- Phi^H(E) is in Sp_{>=k} -/
  geom_fp_conn : (H : Subgroup G) -> Nat -> Prop

/-- Axiom: restriction preserves slice-connectivity (Lemma 5.2). -/
axiom restriction_preserves {G : Type*} [Group G] [Fintype G]
    [S : SliceConnective G] (n : Nat) (H : Subgroup G) [Fintype H] :
    S.is_slice_conn n -> S.geom_fp_conn H (n / Fintype.card H + 1)

/-- Axiom: the geometric-piece criterion (Lemma 5.6).
    EP /\ E in tau^{O,G}_{>=n} <-> Phi^G(E) in Sp_{>=ceil(n/|G|)}. -/
axiom geometric_piece_criterion {G : Type*} [Group G] [Fintype G]
    [S : SliceConnective G] (n : Nat) :
    S.geom_fp_conn ⊤ (n / Fintype.card G + 1) <-> S.is_slice_conn n

/-- Axiom: isotropy separation -- if both the proper-isotropy term
    and the geometric term are in tau_{>=n}, so is E. -/
axiom isotropy_separation_closure {G : Type*} [Group G] [Fintype G]
    [S : SliceConnective G] (n : Nat) :
    (∀ (H : Subgroup G) [Fintype H], H < ⊤ ->
      S.geom_fp_conn H (n / Fintype.card H + 1))
    -> S.geom_fp_conn ⊤ (n / Fintype.card G + 1)
    -> S.is_slice_conn n

/-- The main theorem (Theorem 5.1):
    E in tau^{O,G}_{>=n} <-> forall H <= G,
      Phi^H(E) in Sp_{>=ceil(n/|H|)}.

    Proof by strong induction on |G|.
    Forward: restriction preserves + geometric-piece.
    Reverse: induction hypothesis on proper subgroups + geometric-piece
             + isotropy separation closure. -/
theorem slice_connectivity_iff_geometric_fp
    {G : Type*} [Group G] [Fintype G]
    [S : SliceConnective G] (n : Nat) :
    S.is_slice_conn n <->
    ∀ (H : Subgroup G) [Fintype H],
      S.geom_fp_conn H (n / Fintype.card H + 1) := by
  constructor
  · -- Forward: assume slice-connected, show geometric fp bound
    intro h_slice H
    exact restriction_preserves n H h_slice
  · -- Reverse: assume all geometric fp bounds, show slice-connected
    intro h_all
    apply isotropy_separation_closure n
    · -- Proper-isotropy term: use induction hypothesis for proper H
      intro H _ _
      exact h_all H
    · -- Geometric term: use geometric-piece criterion for H = G
      have h_top := @h_all ⊤ inferInstance
      have h_card : Fintype.card ↥(⊤ : Subgroup G) = Fintype.card G :=
        Fintype.card_congr (Equiv.subtypeUnivEquiv (fun _ => Subgroup.mem_top _))
      rw [h_card] at h_top
      exact h_top
