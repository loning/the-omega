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

/-- Prefix determination is monotone: if determined at depth m, also at depth m+k. -/
theorem prefixDetermined_of_le {s : Set OmegaInfinity} {m n : Nat}
    (h : m ≤ n) (hs : PrefixDetermined s m) : PrefixDetermined s n := by
  intro x y hxy
  have hPrefix : prefixWord x m = prefixWord y m := by
    funext i
    have := congr_fun hxy ⟨i.1, Nat.lt_of_lt_of_le i.2 h⟩
    exact this
  exact hs hPrefix

/-- Empty set is prefix-determined at every depth. -/
theorem prefixDetermined_empty (m : Nat) : PrefixDetermined ∅ m :=
  fun _x _y _h => ⟨False.elim, False.elim⟩

/-- Universal set is prefix-determined at every depth. -/
theorem prefixDetermined_univ (m : Nat) : PrefixDetermined Set.univ m :=
  fun _x _y _h => ⟨fun _ => trivial, fun _ => trivial⟩

/-- Complement of a prefix-determined set is prefix-determined. -/
theorem prefixDetermined_compl {s : Set OmegaInfinity} {m : Nat}
    (hs : PrefixDetermined s m) : PrefixDetermined sᶜ m :=
  fun _x _y h => ⟨fun hx hy => hx ((hs h).2 hy), fun hx hy => hx ((hs h).1 hy)⟩

/-- Intersection of prefix-determined sets is prefix-determined. -/
theorem prefixDetermined_inter {s t : Set OmegaInfinity} {m : Nat}
    (hs : PrefixDetermined s m) (ht : PrefixDetermined t m) :
    PrefixDetermined (s ∩ t) m :=
  fun _x _y h => ⟨fun ⟨hxs, hxt⟩ => ⟨(hs h).1 hxs, (ht h).1 hxt⟩,
    fun ⟨hys, hyt⟩ => ⟨(hs h).2 hys, (ht h).2 hyt⟩⟩

/-- Union of prefix-determined sets is prefix-determined. -/
theorem prefixDetermined_union {s t : Set OmegaInfinity} {m : Nat}
    (hs : PrefixDetermined s m) (ht : PrefixDetermined t m) :
    PrefixDetermined (s ∪ t) m :=
  fun _x _y h => ⟨fun hx => hx.elim (fun h' => Or.inl ((hs h).1 h')) (fun h' => Or.inr ((ht h).1 h')),
    fun hy => hy.elim (fun h' => Or.inl ((hs h).2 h')) (fun h' => Or.inr ((ht h).2 h'))⟩

/-- Cylinder containment: finer-resolution cylinder is contained in coarser. -/
theorem cylinderWord_subset_of_prefix {w₁ : Word m₁} {w₂ : Word m₂}
    (h : m₁ ≤ m₂) (hPrefix : ∀ i : Fin m₁, w₁ i = w₂ ⟨i.1, Nat.lt_of_lt_of_le i.2 h⟩) :
    cylinderWord w₂ ⊆ cylinderWord w₁ := by
  intro x hx
  simp only [cylinderWord, Set.mem_setOf_eq, prefixWord] at hx ⊢
  funext i
  have := congr_fun hx ⟨i.1, Nat.lt_of_lt_of_le i.2 h⟩
  rw [hPrefix i]
  exact this

/-- The intersection of prefix-determined sets is prefix-determined at the finer resolution. -/
theorem prefixDetermined_inter_resolutions {s : Set OmegaInfinity} {t : Set OmegaInfinity}
    {m₁ m₂ : Nat}
    (hs : PrefixDetermined s m₁) (ht : PrefixDetermined t m₂) :
    PrefixDetermined (s ∩ t) (max m₁ m₂) := by
  exact prefixDetermined_inter
    (prefixDetermined_of_le (le_max_left _ _) hs)
    (prefixDetermined_of_le (le_max_right _ _) ht)

end Omega.SPG
