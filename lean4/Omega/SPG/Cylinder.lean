import Mathlib.Topology.MetricSpace.PiNat
import Omega.Core.Word

namespace Omega.SPG

/-- The ambient one-sided binary sequence space used by the SPG layer. -/
abbrev OmegaInfinity := ℕ → Bool

/-- Read the first `m` bits of an infinite binary sequence as a fixed-length word. -/
def prefixWord (x : OmegaInfinity) (m : Nat) : Word m :=
  fun i => x i.1

/-- Extend a finite word to an infinite sequence by padding with `false`. -/
def extendWord (w : Word m) : OmegaInfinity :=
  fun i => get w i

@[simp] theorem prefixWord_extendWord (w : Word m) :
    prefixWord (extendWord w) m = w := by
  funext i
  simp [prefixWord, extendWord, get, i.isLt]

@[simp] theorem extendWord_prefixWord (x : OmegaInfinity) (m : Nat) :
    prefixWord (extendWord (prefixWord x m)) m = prefixWord x m := by
  simp

/-- The cylinder determined by a finite word. -/
def cylinderWord (w : Word m) : Set OmegaInfinity :=
  { x | prefixWord x m = w }

@[simp] theorem mem_cylinderWord_iff (x : OmegaInfinity) (w : Word m) :
    x ∈ cylinderWord w ↔ prefixWord x m = w := by
  rfl

theorem cylinderWord_eq_piCylinder (w : Word m) :
    cylinderWord w = PiNat.cylinder (extendWord w) m := by
  ext x
  constructor
  · intro hx i hi
    have hEq : prefixWord x m = w := hx
    have := congrFun hEq ⟨i, hi⟩
    simpa [prefixWord, extendWord, get, hi] using this
  · intro hx
    funext i
    simpa [prefixWord, extendWord, get, i.isLt] using hx i.1 i.2

theorem mem_piCylinder_iff_prefixWord_eq (x : OmegaInfinity) (m : Nat) :
    x ∈ PiNat.cylinder x m := PiNat.self_mem_cylinder x m

/-- Prefix events of resolution `m`: they only depend on the first `m` bits. -/
def fromWordSet (A : Set (Word m)) : Set OmegaInfinity :=
  { x | prefixWord x m ∈ A }

@[simp] theorem mem_fromWordSet_iff (A : Set (Word m)) (x : OmegaInfinity) :
    x ∈ fromWordSet A ↔ prefixWord x m ∈ A := by
  rfl

theorem fromWordSet_eq_iUnion (A : Set (Word m)) :
    fromWordSet A = ⋃ w : Word m, ⋃ (_ : w ∈ A), cylinderWord w := by
  ext x
  simp [fromWordSet, cylinderWord]

theorem fromWordSet_compl (A : Set (Word m)) :
    (fromWordSet A)ᶜ = fromWordSet Aᶜ := by
  ext x
  simp [fromWordSet]

/-- A set is prefix-determined at depth `m` if membership only depends on the first `m` bits. -/
def PrefixDetermined (s : Set OmegaInfinity) (m : Nat) : Prop :=
  ∀ ⦃x y : OmegaInfinity⦄, prefixWord x m = prefixWord y m → (x ∈ s ↔ y ∈ s)

theorem prefixDetermined_fromWordSet (A : Set (Word m)) :
    PrefixDetermined (fromWordSet A) m := by
  intro x y hxy
  simp [fromWordSet, hxy]

theorem prefixDetermined_iff_exists_fromWordSet (s : Set OmegaInfinity) (m : Nat) :
    PrefixDetermined s m ↔ ∃ A : Set (Word m), s = fromWordSet A := by
  constructor
  · intro hs
    refine ⟨{w | extendWord w ∈ s}, ?_⟩
    ext x
    constructor
    · intro hx
      have hxy : prefixWord (extendWord (prefixWord x m)) m = prefixWord x m := by
        simp
      exact (hs hxy.symm).1 hx
    · intro hx
      have hxy : prefixWord x m = prefixWord (extendWord (prefixWord x m)) m := by
        simp
      exact (hs hxy).2 hx
  · rintro ⟨A, rfl⟩
    exact prefixDetermined_fromWordSet A

end Omega.SPG
