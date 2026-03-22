import Mathlib.Data.Finset.Lattice.Fold
import Omega.Folding.Fiber

namespace Omega

namespace X

noncomputable section

/-- X m is nonempty: the all-false word satisfies No11. -/
instance instNonempty (m : Nat) : Nonempty (X m) :=
  ⟨⟨fun _ => false, no11_allFalse⟩⟩

/-- The maximum fiber multiplicity at resolution m. -/
noncomputable def maxFiberMultiplicity (m : Nat) : Nat :=
  Finset.sup' Finset.univ Finset.univ_nonempty
    (fun x : X m => fiberMultiplicity x)

/-- maxFiberMultiplicity is achieved by some element. -/
theorem maxFiberMultiplicity_achieved (m : Nat) :
    ∃ x : X m, fiberMultiplicity x = maxFiberMultiplicity m := by
  obtain ⟨x, _, hx⟩ := Finset.exists_mem_eq_sup' Finset.univ_nonempty
    (fun x : X m => fiberMultiplicity x)
  exact ⟨x, hx.symm⟩

/-- Every fiber multiplicity is bounded by maxFiberMultiplicity. -/
theorem fiberMultiplicity_le_max (x : X m) :
    fiberMultiplicity x ≤ maxFiberMultiplicity m := by
  exact Finset.le_sup' (fun x : X m => fiberMultiplicity x) (Finset.mem_univ x)

/-- maxFiberMultiplicity is positive. -/
theorem maxFiberMultiplicity_pos (m : Nat) :
    0 < maxFiberMultiplicity m := by
  obtain ⟨x, hx⟩ := maxFiberMultiplicity_achieved m
  rw [← hx]
  exact fiberMultiplicity_pos x

end

end X

end Omega
