import Omega.Folding.Fold

namespace Omega

namespace X

noncomputable section

/-- The finite preimage of a stable word under `Fold`. -/
def fiber (x : X m) : Finset (Word m) := by
  classical
  exact Finset.univ.filter fun w => Fold w = x

@[simp] theorem mem_fiber {x : X m} {w : Word m} :
    w ∈ fiber x ↔ Fold w = x := by
  classical
  simp [fiber]

@[simp] theorem self_mem_fiber (x : X m) : x.1 ∈ fiber x := by
  classical
  simp [fiber]

theorem fiber_nonempty (x : X m) : (fiber x).Nonempty :=
  ⟨x.1, self_mem_fiber x⟩

theorem fiber_card_pos (x : X m) : 0 < (fiber x).card := by
  classical
  exact Finset.card_pos.mpr (fiber_nonempty x)

/-- A canonical preimage of a stable word, obtained by viewing it as a raw word. -/
def choosePreimage (x : X m) : Word m :=
  x.1

@[simp] theorem Fold_choosePreimage (x : X m) : Fold (choosePreimage x) = x :=
  Fold_stable x

@[simp] theorem choosePreimage_mem_fiber (x : X m) : choosePreimage x ∈ fiber x := by
  classical
  simp [choosePreimage]

@[simp] theorem mem_fiber_Fold (w : Word m) : w ∈ fiber (Fold w) := by
  classical
  simp [fiber]

/-- Witness-carrying elements of the finite fiber over `x`. -/
abbrev FiberElem (x : X m) := {w : Word m // w ∈ fiber x}

/-- A proof-oriented version of the fiber using the equation `Fold w = x`. -/
abbrev FiberPoint (x : X m) := {w : Word m // Fold w = x}

noncomputable def fiberElemEquivSubtype (x : X m) : FiberElem x ≃ ↥(fiber x) where
  toFun w := ⟨w.1, w.2⟩
  invFun w := ⟨w.1, w.2⟩
  left_inv w := by
    cases w
    rfl
  right_inv w := by
    cases w
    rfl

noncomputable def fiberElemEquivFiberPoint (x : X m) : FiberElem x ≃ FiberPoint x where
  toFun w := ⟨w.1, (mem_fiber).1 w.2⟩
  invFun w := ⟨w.1, (mem_fiber).2 w.2⟩
  left_inv w := by
    cases w
    rfl
  right_inv w := by
    cases w
    rfl

/-- Noncomputable ranking of a fiber element by its position in `Fin card`. -/
noncomputable def rank (x : X m) : FiberElem x ≃ Fin (fiber x).card :=
  (fiberElemEquivSubtype x).trans <|
    Fintype.equivFinOfCardEq (by rw [Fintype.card_coe])

/-- Noncomputable unranking map for a fiber. -/
noncomputable def unrank (x : X m) : Fin (fiber x).card → FiberElem x :=
  (rank x).symm

@[simp] theorem rank_unrank (x : X m) (i : Fin (fiber x).card) :
    rank x (unrank x i) = i := by
  simp [rank, unrank]

@[simp] theorem unrank_rank (x : X m) (w : FiberElem x) :
    unrank x (rank x w) = w := by
  simp [rank, unrank]

/-- The raw word returned by unranking a fiber index. -/
noncomputable def unrankWord (x : X m) (i : Fin (fiber x).card) : Word m :=
  (unrank x i).1

@[simp] theorem unrankWord_mem_fiber (x : X m) (i : Fin (fiber x).card) :
    unrankWord x i ∈ fiber x :=
  (unrank x i).2

@[simp] theorem Fold_unrankWord (x : X m) (i : Fin (fiber x).card) :
    Fold (unrankWord x i) = x := by
  exact (mem_fiber).1 (unrankWord_mem_fiber x i)

/-- Rank a raw word once a proof is given that it lies in the fiber. -/
noncomputable def rankOfFoldEq (x : X m) (w : Word m) (h : Fold w = x) :
    Fin (fiber x).card :=
  rank x ⟨w, (mem_fiber).2 h⟩

@[simp] theorem unrankWord_rankOfFoldEq (x : X m) (w : Word m) (h : Fold w = x) :
    unrankWord x (rankOfFoldEq x w h) = w := by
  change (unrank x (rankOfFoldEq x w h)).1 = w
  have hEq : unrank x (rankOfFoldEq x w h) = ⟨w, (mem_fiber).2 h⟩ := by
    simp [rankOfFoldEq]
  exact congrArg Subtype.val hEq

@[simp] theorem rankOfFoldEq_choosePreimage (x : X m) :
    unrankWord x (rankOfFoldEq x (choosePreimage x) (Fold_choosePreimage x)) = choosePreimage x := by
  exact unrankWord_rankOfFoldEq x (choosePreimage x) (Fold_choosePreimage x)

end

end X

end Omega
