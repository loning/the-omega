import Omega.SPG.PrefixMetric

namespace Omega.SPG

open Set

theorem isOpen_cylinderWord (w : Word m) : IsOpen (cylinderWord w) := by
  rw [cylinderWord_eq_piCylinder]
  exact PiNat.isOpen_cylinder (fun _ : ℕ => Bool) (extendWord w) m

theorem isOpen_fromWordSet (A : Set (Word m)) : IsOpen (fromWordSet A) := by
  rw [fromWordSet_eq_iUnion]
  refine isOpen_iUnion ?_
  intro w
  refine isOpen_iUnion ?_
  intro _hw
  exact isOpen_cylinderWord w

theorem isClopen_fromWordSet (A : Set (Word m)) : IsClopen (fromWordSet A) := by
  refine ⟨?_, isOpen_fromWordSet A⟩
  refine ⟨?_⟩
  simpa [fromWordSet_compl] using isOpen_fromWordSet (A := Aᶜ)

/-- Finite-prefix events are clopen in the product topology. -/
theorem prefixDetermined_isClopen {s : Set OmegaInfinity} (m : Nat)
    (hs : PrefixDetermined s m) : IsClopen s := by
  rcases (prefixDetermined_iff_exists_fromWordSet s m).1 hs with ⟨A, rfl⟩
  exact isClopen_fromWordSet A

/-- The SPG-facing clopen theorem: any event cut out by finitely many prefixes is clopen. -/
theorem spg_decidableClopen (A : Set (Word m)) : IsClopen (fromWordSet A) :=
  isClopen_fromWordSet A

/-- Cylinder sets are clopen. -/
theorem isClopen_cylinderWord (w : Word m) : IsClopen (cylinderWord w) := by
  have := isClopen_fromWordSet {w}
  rwa [show fromWordSet ({w} : Set (Word m)) = cylinderWord w from by ext x; simp [fromWordSet]] at this

/-- The intersection of two clopen fromWordSets is a clopen fromWordSet. -/
theorem isClopen_fromWordSet_inter (A B : Set (Word m)) :
    IsClopen (fromWordSet A ∩ fromWordSet B) := by
  rw [← fromWordSet_inter]; exact isClopen_fromWordSet (A ∩ B)

/-- The union of two clopen fromWordSets is a clopen fromWordSet. -/
theorem isClopen_fromWordSet_union (A B : Set (Word m)) :
    IsClopen (fromWordSet A ∪ fromWordSet B) := by
  rw [← fromWordSet_union]; exact isClopen_fromWordSet (A ∪ B)

end Omega.SPG
