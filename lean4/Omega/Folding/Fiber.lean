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

end

end X

end Omega
