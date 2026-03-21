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

end Omega.SPG
