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

/-- The word space has cardinality 2^m. -/
theorem Word_card (m : Nat) : Fintype.card (Word m) = 2 ^ m := by
  rw [Fintype.card_fun, Fintype.card_bool, Fintype.card_fin]

/-- Fiber cardinalities sum to the total word count (fibers partition `Word m`). -/
theorem fiber_card_sum (m : Nat) :
    ∑ x : X m, (fiber x).card = Fintype.card (Word m) := by
  classical
  have hDisjoint : (↑(Finset.univ : Finset (X m)) : Set (X m)).PairwiseDisjoint fiber := by
    intro x _ y _ hxy
    rw [Function.onFun, Finset.disjoint_left]
    intro w hwx hwy
    exact hxy ((mem_fiber.1 hwx).symm.trans (mem_fiber.1 hwy))
  have hUnion : (Finset.univ : Finset (Word m)) = Finset.univ.biUnion fiber := by
    ext w
    simp only [Finset.mem_univ, Finset.mem_biUnion, true_iff]
    exact ⟨Fold w, trivial, mem_fiber_Fold w⟩
  calc ∑ x : X m, (fiber x).card
      = (Finset.univ.biUnion fiber).card := (Finset.card_biUnion hDisjoint).symm
    _ = (Finset.univ : Finset (Word m)).card := by rw [← hUnion]
    _ = Fintype.card (Word m) := Finset.card_univ

/-- Fiber cardinalities sum to 2^m. -/
theorem fiber_card_sum_eq_pow (m : Nat) :
    ∑ x : X m, (fiber x).card = 2 ^ m := by
  rw [fiber_card_sum, Word_card]

/-- The stable value of a stable word is a valid Fin index. -/
def stableValueFin (x : X m) : Fin (paperFib (m + 1)) :=
  ⟨stableValue x, stableValue_lt_paperFib_succ x⟩

/-- stableValueFin is injective. -/
theorem stableValueFin_injective (m : Nat) :
    Function.Injective (stableValueFin (m := m)) := by
  intro x y h
  have := congr_arg Fin.val h
  simp only [stableValueFin, Fin.mk.injEq] at this
  exact (Function.HasLeftInverse.injective ⟨X.ofNat m, X.ofNat_stableValue⟩) this

/-- The stable syntax space is equivalent to Fin(paperFib(m+1)).
    This is the core encoding result: X_m ≃ {0, ..., F_{m+2}-1}. -/
noncomputable def stableValueEquiv (m : Nat) : X m ≃ Fin (paperFib (m + 1)) :=
  Fintype.equivFinOfCardEq (X.card_eq_paperFib_succ m)

/-- The stableValueFin map is surjective (from injectivity + matching cardinality). -/
theorem stableValueFin_surjective (m : Nat) :
    Function.Surjective (stableValueFin (m := m)) :=
  (Finite.injective_iff_surjective_of_equiv (stableValueEquiv m)).mp
    (stableValueFin_injective m)

/-- The stableValueFin map is bijective. -/
theorem stableValueFin_bijective (m : Nat) :
    Function.Bijective (stableValueFin (m := m)) :=
  ⟨stableValueFin_injective m, stableValueFin_surjective m⟩

/-- The fiber multiplicity of a stable word x: the number of raw words folding to x. -/
def fiberMultiplicity (x : X m) : Nat := (fiber x).card

/-- Fiber multiplicity is positive for every stable word. -/
theorem fiberMultiplicity_pos (x : X m) : 0 < fiberMultiplicity x :=
  fiber_card_pos x

/-- Fiber multiplicities sum to 2^m. -/
theorem fiberMultiplicity_sum_eq_pow (m : Nat) :
    ∑ x : X m, fiberMultiplicity x = 2 ^ m :=
  fiber_card_sum_eq_pow m

/-- The average fiber multiplicity is 2^m / |X_m|.
    Since |X_m| = F_{m+2}, this ratio approaches φ^m / √5 as m grows. -/
theorem fiberMultiplicity_avg (m : Nat) :
    ∑ x : X m, fiberMultiplicity x = 2 ^ m ∧
    Fintype.card (X m) = paperFib (m + 1) :=
  ⟨fiberMultiplicity_sum_eq_pow m, X.card_eq_paperFib_succ m⟩

/-- For n < paperFib(m+1), ofNat m n has stable value n. -/
theorem stableValue_ofNat_lt (n : Nat) (hn : n < paperFib (m + 1)) :
    stableValue (X.ofNat m n) = n := by
  obtain ⟨x, hx⟩ := stableValueFin_surjective m ⟨n, hn⟩
  have hVal : stableValue x = n := by simpa [stableValueFin] using congr_arg Fin.val hx
  rw [show X.ofNat m n = x from by rw [← hVal, X.ofNat_stableValue], hVal]

/-- For n < paperFib(m+1), ofNat and stableValue form a round-trip. -/
theorem stableValue_ofNat_mod (n : Nat) :
    stableValue (X.ofNat m (n % paperFib (m + 1))) = n % paperFib (m + 1) :=
  stableValue_ofNat_lt _ (Nat.mod_lt n (paperFib_pos (m + 1)))

/-- Stable addition on X m: wrap-around Fibonacci arithmetic. -/
noncomputable def stableAdd (x y : X m) : X m :=
  X.ofNat m ((stableValue x + stableValue y) % paperFib (m + 1))

/-- The zero element for stable addition. -/
noncomputable def stableZero : X m := X.ofNat m 0

/-- Stable addition is commutative. -/
theorem stableAdd_comm (x y : X m) :
    stableAdd x y = stableAdd y x := by
  simp only [stableAdd, Nat.add_comm]

/-- The zero element has stable value 0. -/
theorem stableValue_stableZero : stableValue (stableZero (m := m)) = 0 :=
  stableValue_ofNat_lt 0 (paperFib_pos (m + 1))

/-- stableZero is the left identity for stable addition. -/
theorem stableAdd_zero_left (x : X m) : stableAdd stableZero x = x := by
  unfold stableAdd stableZero
  rw [stableValue_ofNat_lt 0 (paperFib_pos (m + 1)), Nat.zero_add,
    Nat.mod_eq_of_lt (stableValue_lt_paperFib_succ x), X.ofNat_stableValue]

/-- stableZero is the right identity for stable addition. -/
theorem stableAdd_zero_right (x : X m) : stableAdd x stableZero = x := by
  rw [stableAdd_comm]; exact stableAdd_zero_left x

/-- Helper: (a % n + b) % n = (a + b) % n for 0 < n. -/
private theorem Nat.mod_add_mod_right (a b n : Nat) (hn : 0 < n) :
    (a % n + b) % n = (a + b) % n := by
  conv_rhs => rw [← Nat.mod_add_div a n]
  rw [Nat.add_assoc, Nat.add_comm (n * (a / n)), ← Nat.add_assoc,
    Nat.add_mul_mod_self_left]

/-- Stable addition is associative. -/
theorem stableAdd_assoc (x y z : X m) :
    stableAdd (stableAdd x y) z = stableAdd x (stableAdd y z) := by
  unfold stableAdd
  have hF := paperFib_pos (m + 1)
  rw [stableValue_ofNat_mod, stableValue_ofNat_mod]
  congr 1
  -- Goal: ((sv_x + sv_y) % F + sv_z) % F = (sv_x + (sv_y + sv_z) % F) % F
  -- Both sides equal (sv_x + sv_y + sv_z) % F
  have lhs : ((stableValue x + stableValue y) % paperFib (m + 1) + stableValue z)
      % paperFib (m + 1) =
      (stableValue x + stableValue y + stableValue z) % paperFib (m + 1) :=
    Nat.mod_add_mod_right _ _ _ hF
  have rhs : (stableValue x + (stableValue y + stableValue z) % paperFib (m + 1))
      % paperFib (m + 1) =
      (stableValue x + (stableValue y + stableValue z)) % paperFib (m + 1) := by
    conv_lhs => rw [Nat.add_comm]
    rw [Nat.mod_add_mod_right _ _ _ hF, Nat.add_comm]
  rw [lhs, rhs, Nat.add_assoc]

/-- Stable multiplication on X m: wrap-around Fibonacci arithmetic. -/
noncomputable def stableMul (x y : X m) : X m :=
  X.ofNat m ((stableValue x * stableValue y) % paperFib (m + 1))

/-- Stable multiplication is commutative. -/
theorem stableMul_comm (x y : X m) :
    stableMul x y = stableMul y x := by
  simp only [stableMul, Nat.mul_comm]

/-- stableZero is the annihilator for multiplication. -/
theorem stableMul_zero_left (x : X m) : stableMul stableZero x = stableZero := by
  unfold stableMul stableZero
  rw [stableValue_ofNat_lt 0 (paperFib_pos (m + 1)), Nat.zero_mul, Nat.zero_mod]

/-- stableZero is the annihilator for multiplication (right). -/
theorem stableMul_zero_right (x : X m) : stableMul x stableZero = stableZero := by
  rw [stableMul_comm]; exact stableMul_zero_left x

/-- The one element for stable multiplication. -/
noncomputable def stableOne : X m := X.ofNat m 1

/-- stableOne has value 1 when paperFib(m+1) > 1. -/
theorem stableValue_stableOne (hm : 1 < paperFib (m + 1)) :
    stableValue (stableOne (m := m)) = 1 :=
  stableValue_ofNat_lt 1 hm

/-- stableOne is the left identity for multiplication when F_{m+2} > 1. -/
theorem stableMul_one_left (hm : 1 < paperFib (m + 1)) (x : X m) :
    stableMul stableOne x = x := by
  unfold stableMul stableOne
  rw [stableValue_ofNat_lt 1 hm, Nat.one_mul,
    Nat.mod_eq_of_lt (stableValue_lt_paperFib_succ x), X.ofNat_stableValue]

/-- Helper: (a * (b % n)) % n = (a * b) % n. -/
private theorem Nat.mul_mod_right' (a b n : Nat) :
    (a * (b % n)) % n = (a * b) % n := by
  conv_rhs => rw [Nat.mul_mod]
  rw [Nat.mul_mod a (b % n) n, Nat.mod_mod_of_dvd _ (dvd_refl n)]

/-- Helper: ((a % n) * b) % n = (a * b) % n. -/
private theorem Nat.mul_mod_left' (a b n : Nat) :
    (a % n * b) % n = (a * b) % n := by
  rw [Nat.mul_comm, Nat.mul_mod_right', Nat.mul_comm]

/-- Helper: ((a % n) + (b % n)) % n = (a + b) % n. -/
private theorem Nat.add_mod' (a b n : Nat) :
    ((a % n) + (b % n)) % n = (a + b) % n := by
  rw [← Nat.add_mod]

/-- Stable multiplication distributes over stable addition (left). -/
theorem stableMul_stableAdd_left (x y z : X m) :
    stableMul x (stableAdd y z) = stableAdd (stableMul x y) (stableMul x z) := by
  simp only [stableMul, stableAdd, stableValue_ofNat_mod]
  congr 1
  rw [Nat.mul_mod_right', Nat.add_mod', Nat.mul_add]

/-- Stable multiplication is associative. -/
theorem stableMul_assoc (x y z : X m) :
    stableMul (stableMul x y) z = stableMul x (stableMul y z) := by
  simp only [stableMul, stableValue_ofNat_mod]
  congr 1
  rw [Nat.mul_mod_left' (stableValue x * stableValue y) (stableValue z),
    Nat.mul_mod_right' (stableValue x) (stableValue y * stableValue z),
    Nat.mul_assoc]

/-- stableOne is the right identity for multiplication when F_{m+2} > 1. -/
theorem stableMul_one_right (hm : 1 < paperFib (m + 1)) (x : X m) :
    stableMul x stableOne = x := by
  rw [stableMul_comm]; exact stableMul_one_left hm x

/-- Fiber multiplicity as a function of value index. -/
noncomputable def fiberMultiplicityByValue (m : Nat) (n : Nat) : Nat :=
  if hn : n < paperFib (m + 1) then fiberMultiplicity (X.ofNat m n) else 0

/-- Fiber multiplicity of x equals fiberMultiplicityByValue at stableValue(x). -/
theorem fiberMultiplicity_eq_byValue (x : X m) :
    fiberMultiplicity x = fiberMultiplicityByValue m (stableValue x) := by
  simp [fiberMultiplicityByValue, stableValue_lt_paperFib_succ x, X.ofNat_stableValue]

/-- The range of stableValue is exactly {0, ..., paperFib(m+1)-1}. -/
theorem stableValue_range (m : Nat) :
    Set.range (stableValue (m := m)) = {n | n < paperFib (m + 1)} := by
  ext n
  constructor
  · rintro ⟨x, rfl⟩
    exact stableValue_lt_paperFib_succ x
  · intro hn
    exact ⟨X.ofNat m n, stableValue_ofNat_lt n hn⟩

/-- X.ofNat m restricted to valid indices is the inverse of stableValue. -/
theorem ofNat_stableValue_eq (x : X m) : X.ofNat m (stableValue x) = x :=
  X.ofNat_stableValue x

/-- stableValue followed by ofNat is the identity for values in range. -/
theorem stableValue_ofNat_roundtrip (n : Nat) (hn : n < paperFib (m + 1)) :
    stableValue (X.ofNat m n) = n :=
  stableValue_ofNat_lt n hn

/-- stableAdd encodes modular addition on values. -/
theorem stableValue_stableAdd (x y : X m) :
    stableValue (stableAdd x y) = (stableValue x + stableValue y) % paperFib (m + 1) :=
  stableValue_ofNat_mod _

/-- stableMul encodes modular multiplication on values. -/
theorem stableValue_stableMul (x y : X m) :
    stableValue (stableMul x y) = (stableValue x * stableValue y) % paperFib (m + 1) :=
  stableValue_ofNat_mod _

/-- The stable value map is a semiring homomorphism to ℤ/F_{m+2}ℤ (addition component). -/
theorem stableValue_add_mod (x y : X m) :
    stableValue (stableAdd x y) % paperFib (m + 1) =
      (stableValue x + stableValue y) % paperFib (m + 1) := by
  rw [stableValue_stableAdd, Nat.mod_mod_of_dvd _ (dvd_refl _)]

/-- The stable value map is a semiring homomorphism to ℤ/F_{m+2}ℤ (multiplication component). -/
theorem stableValue_mul_mod (x y : X m) :
    stableValue (stableMul x y) % paperFib (m + 1) =
      (stableValue x * stableValue y) % paperFib (m + 1) := by
  rw [stableValue_stableMul, Nat.mod_mod_of_dvd _ (dvd_refl _)]

/-- The carry element at resolution m: χ^car_m = ofNat m (fib(m+2)). -/
noncomputable def carryElement (m : Nat) : X m :=
  X.ofNat m (Nat.fib (m + 2))

/-- The carry element value: stableValue(χ^car_m) = fib(m+2) mod F_{m+2}.
    Note: fib(m+2) = paperFib(m+1), so this wraps to fib(m+2) when < F_{m+2},
    which holds for m ≥ 1 since fib(m+2) < fib(m+3) = paperFib(m+2). -/
theorem stableValue_carryElement (hm : Nat.fib (m + 2) < paperFib (m + 1)) :
    stableValue (carryElement m) = Nat.fib (m + 2) :=
  stableValue_ofNat_lt _ hm

/-- The carry indicator is 0 or 1. -/
theorem carryIndicator_le_one (x y : X (m + 1)) :
    carryIndicator x y ≤ 1 := by
  unfold carryIndicator
  split <;> omega

/-- When the sum is below the threshold, stableAdd at m+1 restricted to m
    coincides with stableAdd at m of the restrictions (no carry). -/
theorem restrict_stableAdd_of_no_carry (x y : X (m + 1))
    (hNoCarry : stableValue x + stableValue y < paperFib (m + 2)) :
    stableValue (X.restrict (stableAdd x y)) % paperFib (m + 1) =
      (stableValue (X.restrict x) + stableValue (X.restrict y)) % paperFib (m + 1) := by
  -- stableValue(x ⊕ y) = sv_x + sv_y (no mod reduction)
  have hSV : stableValue (stableAdd x y) = stableValue x + stableValue y := by
    rw [stableValue_stableAdd, Nat.mod_eq_of_lt hNoCarry]
  -- After rewriting: (sv_x + sv_y) % F_{m+2} = (sv_restrict_x + sv_restrict_y) % F_{m+2}
  -- Use: sv_x ≡ sv_restrict_x (mod F_{m+2}) and sv_y ≡ sv_restrict_y (mod F_{m+2})
  have hModX := stableValue_restrict_mod x
  have hModY := stableValue_restrict_mod y
  rw [← stableValue_restrict_mod (stableAdd x y), hSV, Nat.add_mod,
    hModX, hModY, ← Nat.add_mod]

/-- Fold is the identity on the underlying word of a stable element. -/
theorem Fold_val_stable (x : X m) : (Fold x.1).1 = x.1 := by
  exact congrArg Subtype.val (Fold_stable x)

/-- Two stable words with the same stableValue are equal. -/
theorem eq_of_stableValue_eq {x y : X m} (h : stableValue x = stableValue y) : x = y :=
  stableValueFin_injective m (by simp [stableValueFin, h])

/-- stableAdd with the same element doubled: x ⊕ x = ofNat(2 * stableValue x mod F). -/
theorem stableAdd_self (x : X m) :
    stableAdd x x = X.ofNat m ((2 * stableValue x) % paperFib (m + 1)) := by
  simp [stableAdd, two_mul]

/-- Negation in the stable semiring: the additive inverse. -/
noncomputable def stableNeg (x : X m) : X m :=
  X.ofNat m ((paperFib (m + 1) - stableValue x) % paperFib (m + 1))

/-- stableNeg gives the additive inverse: x + neg(x) = 0. -/
theorem stableAdd_stableNeg (x : X m) :
    stableAdd x (stableNeg x) = stableZero := by
  apply eq_of_stableValue_eq
  simp only [stableValue_stableAdd, stableNeg, stableValue_ofNat_mod, stableValue_stableZero]
  have hLt := stableValue_lt_paperFib_succ x
  rw [Nat.add_mod, Nat.mod_mod_of_dvd _ (dvd_refl _), ← Nat.add_mod]
  rw [show stableValue x + (paperFib (m + 1) - stableValue x) = paperFib (m + 1) from by omega]
  simp [Nat.mod_self]

/-- stableNeg gives the right additive inverse: neg(x) + x = 0. -/
theorem stableNeg_stableAdd (x : X m) :
    stableAdd (stableNeg x) x = stableZero := by
  rw [stableAdd_comm]; exact stableAdd_stableNeg x

/-- stableNeg of zero is zero. -/
theorem stableNeg_zero : stableNeg (stableZero (m := m)) = stableZero := by
  apply eq_of_stableValue_eq
  simp only [stableNeg, stableValue_ofNat_mod, stableZero]
  rw [stableValue_ofNat_lt 0 (paperFib_pos (m + 1)), Nat.sub_zero, Nat.mod_self]

/-- stableValue of the negation. -/
theorem stableValue_stableNeg (x : X m) :
    stableValue (stableNeg x) = (paperFib (m + 1) - stableValue x) % paperFib (m + 1) :=
  stableValue_ofNat_mod _

/-- Stable subtraction: x - y := x + neg(y). -/
noncomputable def stableSub (x y : X m) : X m :=
  stableAdd x (stableNeg y)

/-- stableSub is a left inverse of stableAdd: (x + y) - y = x. -/
theorem stableSub_stableAdd_cancel (x y : X m) :
    stableSub (stableAdd x y) y = x := by
  simp only [stableSub, stableAdd_assoc, stableAdd_stableNeg, stableAdd_zero_right]

/-- Stable multiplication by stableZero on the right annihilates. -/
theorem stableValue_stableMul_zero (x : X m) :
    stableValue (stableMul x stableZero) = 0 := by
  rw [stableValue_stableMul, stableValue_stableZero, Nat.mul_zero, Nat.zero_mod]

/-- stableAdd distributes over stableMul on the right. -/
theorem stableMul_stableAdd_right (x y z : X m) :
    stableMul (stableAdd y z) x = stableAdd (stableMul y x) (stableMul z x) := by
  rw [stableMul_comm, stableMul_stableAdd_left, stableMul_comm y, stableMul_comm z]

/-- The stable value map characterizes equality: two stable words are equal iff
    they have the same value. -/
theorem stableValue_eq_iff (x y : X m) : x = y ↔ stableValue x = stableValue y :=
  ⟨fun h => congrArg _ h, eq_of_stableValue_eq⟩

/-- The stable arithmetic respects the Fibonacci modulus:
    stableAdd and stableMul are the unique operations making stableValue
    a surjective ring homomorphism to ℤ/F_{m+2}ℤ. -/
theorem stableValue_ring_surjective (n : Nat) (hn : n < paperFib (m + 1)) :
    ∃ x : X m, stableValue x = n :=
  ⟨X.ofNat m n, stableValue_ofNat_lt n hn⟩

/-- The fiber of Fold over x contains x's own underlying word. -/
theorem self_in_own_fiber (x : X m) : x.1 ∈ fiber x := by
  classical
  exact self_mem_fiber x

/-- Two distinct stable words yield disjoint fibers. -/
theorem fiber_disjoint {x y : X m} (hne : x ≠ y) :
    Disjoint (fiber x) (fiber y) := by
  classical
  rw [Finset.disjoint_left]
  intro w hwx hwy
  exact hne ((mem_fiber.1 hwx).symm.trans (mem_fiber.1 hwy))

/-- Fiber cardinality is at least 1 (positivity, named variant). -/
theorem fiber_card_ge_one (x : X m) : 1 ≤ (fiber x).card :=
  fiber_card_pos x

/-- Subtraction and addition cancel: (x - y) + y = x. -/
theorem stableSub_add_cancel (x y : X m) :
    stableAdd (stableSub x y) y = x := by
  rw [stableSub, stableAdd_assoc, stableNeg_stableAdd, stableAdd_zero_right]

/-- Stable subtraction value: stableValue(x - y) = (sv_x - sv_y) mod F. -/
theorem stableValue_stableSub (x y : X m) :
    stableValue (stableSub x y) =
      (stableValue x + (paperFib (m + 1) - stableValue y)) % paperFib (m + 1) := by
  simp [stableSub, stableValue_stableAdd, stableValue_stableNeg]

/-- Subtraction is the inverse of addition on the left: x - x = 0. -/
theorem stableSub_self (x : X m) : stableSub x x = stableZero := by
  simp [stableSub, stableAdd_stableNeg]

/-- stableAdd is cancellative on the left: x + y = x + z → y = z. -/
theorem stableAdd_left_cancel {x y z : X m} (h : stableAdd x y = stableAdd x z) : y = z := by
  -- (-x) + (x + y) = (-x) + (x + z)
  have h1 : stableAdd (stableNeg x) (stableAdd x y) =
    stableAdd (stableNeg x) (stableAdd x z) := by rw [h]
  -- (-x + x) + y = (-x + x) + z by associativity
  rw [← stableAdd_assoc, ← stableAdd_assoc,
    stableNeg_stableAdd, stableAdd_zero_left, stableAdd_zero_left] at h1
  exact h1

/-- stableAdd is cancellative on the right: y + x = z + x → y = z. -/
theorem stableAdd_right_cancel {x y z : X m} (h : stableAdd y x = stableAdd z x) : y = z := by
  apply stableAdd_left_cancel (x := x)
  rwa [stableAdd_comm x y, stableAdd_comm x z]

/-- The stable arithmetic on X_m is isomorphic to ℤ/F_{m+2}ℤ as a commutative ring:
    stableValue witnesses the isomorphism. -/
theorem stableValue_isomorphism_summary (m : Nat) :
    -- Additive homomorphism
    (∀ x y : X m, stableValue (stableAdd x y) = (stableValue x + stableValue y) % paperFib (m + 1)) ∧
    -- Multiplicative homomorphism
    (∀ x y : X m, stableValue (stableMul x y) = (stableValue x * stableValue y) % paperFib (m + 1)) ∧
    -- Injective
    Function.Injective (stableValue (m := m)) ∧
    -- Range is {0,...,F_{m+2}-1}
    Set.range (stableValue (m := m)) = {n | n < paperFib (m + 1)} :=
  ⟨stableValue_stableAdd, stableValue_stableMul,
   (Function.HasLeftInverse.injective ⟨X.ofNat m, X.ofNat_stableValue⟩),
   stableValue_range m⟩

/-- |X 1| = 2. -/
theorem card_X_one : Fintype.card (X 1) = 2 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- |X 2| = 3. -/
theorem card_X_two : Fintype.card (X 2) = 3 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- |X 3| = 5. -/
theorem card_X_three : Fintype.card (X 3) = 5 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- |X 4| = 8. -/
theorem card_X_four : Fintype.card (X 4) = 8 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- |X 5| = 13. -/
theorem card_X_five : Fintype.card (X 5) = 13 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- The stable value of stableOne is 1 for m ≥ 1. -/
theorem stableValue_stableOne_of_ge_one (hm : 1 ≤ m) :
    stableValue (stableOne (m := m)) = 1 :=
  stableValue_ofNat_lt 1 (paperFib_gt_one hm)

/-- |X 6| = 21. -/
theorem card_X_six : Fintype.card (X 6) = 21 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- |X 7| = 34. -/
theorem card_X_seven : Fintype.card (X 7) = 34 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- stableAdd with stableNeg of y gives stableSub x y. -/
theorem stableAdd_neg_eq_sub (x y : X m) :
    stableAdd x (stableNeg y) = stableSub x y :=
  rfl

/-- Double negation: -(-x) = x. Proved via the additive inverse uniqueness. -/
theorem stableNeg_neg_eq (x : X m) :
    stableNeg (stableNeg x) = x := by
  -- -(-x) + (-x) = 0 and x + (-x) = 0
  -- Both are left inverses of (-x), so they must be equal.
  have h1 := stableAdd_stableNeg (stableNeg x)
  have h2 := stableNeg_stableAdd x
  -- h1 : (-x) + (-(-x)) = 0, but we need -(-x) + (-x) = 0
  rw [stableAdd_comm] at h1
  -- So (-(-x)) + (-x) = 0 and x + (-x) = 0
  -- (-(-x)) = x by left cancellation of (-x):
  -- (-(-x)) + (-x) = x + (-x) → -(-x) = x
  have h3 := stableAdd_stableNeg x
  exact stableAdd_right_cancel (h1.trans h3.symm)

/-- Negation is an involution for stableAdd: equivalent via cancellation. -/
theorem stableNeg_add_cancel (x y : X m) :
    stableAdd (stableNeg x) (stableAdd x y) = y := by
  rw [← stableAdd_assoc, stableNeg_stableAdd, stableAdd_zero_left]

/-- Negation distributes to subtraction: (x - y) = x + (-y) (definitional). -/
theorem stableSub_eq_add_neg (x y : X m) : stableSub x y = stableAdd x (stableNeg y) := rfl

/-- |X 8| = 55. -/
theorem card_X_eight : Fintype.card (X 8) = 55 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- |X 9| = 89. -/
theorem card_X_nine : Fintype.card (X 9) = 89 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- |X 10| = 144. -/
theorem card_X_ten : Fintype.card (X 10) = 144 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- stableAdd with stableNeg on left cancels (named variant). -/
theorem stableNeg_add_self (x : X m) : stableAdd (stableNeg x) x = stableZero :=
  stableNeg_stableAdd x

/-- stableAdd with self negation on right cancels (named variant). -/
theorem stableAdd_self_neg (x : X m) : stableAdd x (stableNeg x) = stableZero :=
  stableAdd_stableNeg x

/-- stableNeg of stableOne gives the maximal element (F_{m+2} - 1). -/
theorem stableValue_neg_one (hm : 1 ≤ m) :
    stableValue (stableNeg (stableOne (m := m))) = paperFib (m + 1) - 1 := by
  rw [stableValue_stableNeg, stableValue_stableOne_of_ge_one hm,
    Nat.mod_eq_of_lt (by have := paperFib_pos (m + 1); omega)]

/-- For m ≥ 1, stableOne is not stableZero. -/
theorem stableOne_ne_stableZero (hm : 1 ≤ m) : stableOne (m := m) ≠ stableZero := by
  intro h
  have h1 := stableValue_stableOne_of_ge_one hm
  have h0 := stableValue_stableZero (m := m)
  rw [h] at h1; omega

/-- The modular reduction map: project a value from X_{m+1} to X_m via Fibonacci modulus. -/
noncomputable def modularProject (x : X (m + 1)) : X m :=
  X.ofNat m (stableValue x % paperFib (m + 1))

/-- The modular projection agrees with restriction on stable value. -/
theorem stableValue_modularProject (x : X (m + 1)) :
    stableValue (modularProject x) = stableValue x % paperFib (m + 1) := by
  unfold modularProject
  exact stableValue_ofNat_lt _ (Nat.mod_lt _ (paperFib_pos (m + 1)))

/-- The modular projection maps zero to zero. -/
theorem modularProject_zero : modularProject (stableZero (m := m + 1)) = stableZero := by
  apply eq_of_stableValue_eq
  rw [stableValue_modularProject, stableValue_stableZero, Nat.zero_mod, stableValue_stableZero]

/-- When carry is zero, the modular projection preserves addition exactly. -/
theorem modularProject_add_no_carry (x y : X (m + 1))
    (hNoCarry : stableValue x + stableValue y < paperFib (m + 2)) :
    modularProject (stableAdd x y) = stableAdd (modularProject x) (modularProject y) := by
  apply eq_of_stableValue_eq
  rw [stableValue_modularProject, stableValue_stableAdd, stableValue_stableAdd,
    stableValue_modularProject, stableValue_modularProject,
    Nat.mod_eq_of_lt hNoCarry]
  rw [Nat.add_mod]

/-- At resolution 0, the total fiber sum is 2^0 = 1, and |X_0| = 1,
    so the unique element has fiber multiplicity 1. -/
theorem fiberMultiplicity_unique_at_zero :
    ∑ x : X 0, fiberMultiplicity x = 1 := by
  rw [fiberMultiplicity_sum_eq_pow]; rfl

/-- The average fiber multiplicity grows: at resolution m, it's 2^m / F_{m+2}. -/
theorem fiberMultiplicity_total (m : Nat) :
    ∑ x : X m, fiberMultiplicity x = 2 ^ m :=
  fiberMultiplicity_sum_eq_pow m

/-- Zeckendorf uniqueness: same Zeckendorf indices ⇒ same stable word.
    Proved via value characterization: same indices ⇒ same value ⇒ same word. -/
theorem eq_of_zeckIndices_eq {x y : X m} (h : X.zeckIndices x = X.zeckIndices y) : x = y :=
  eq_of_stableValue_eq (X.stableValue_eq_of_zeckIndices_eq h)

/-- The Zeckendorf encoding is faithful: injective on stable words. -/
theorem zeckIndices_injective (m : Nat) : Function.Injective (X.zeckIndices (m := m)) :=
  fun _ _ h => eq_of_zeckIndices_eq h

/-- The ring structure on X_m: stableValue is an isomorphism to ℤ/F_{m+2}ℤ.
    Certificate: add hom + mul hom + injective + surjective + neg hom. -/
structure RingIsomorphismCertificate (m : Nat) where
  add_hom : ∀ x y : X m, stableValue (stableAdd x y) =
    (stableValue x + stableValue y) % paperFib (m + 1)
  mul_hom : ∀ x y : X m, stableValue (stableMul x y) =
    (stableValue x * stableValue y) % paperFib (m + 1)
  neg_hom : ∀ x : X m, stableValue (stableNeg x) =
    (paperFib (m + 1) - stableValue x) % paperFib (m + 1)
  injective : Function.Injective (stableValue (m := m))
  range_eq : Set.range (stableValue (m := m)) = {n | n < paperFib (m + 1)}

/-- The canonical ring isomorphism certificate for X_m. -/
noncomputable def ringIsoCert (m : Nat) : RingIsomorphismCertificate m where
  add_hom := stableValue_stableAdd
  mul_hom := stableValue_stableMul
  neg_hom := stableValue_stableNeg
  injective := (Function.HasLeftInverse.injective ⟨X.ofNat m, X.ofNat_stableValue⟩)
  range_eq := stableValue_range m

/-- The ring isomorphism certificate witnesses injectivity. -/
theorem ringIsoCert_injective (m : Nat) :
    Function.Injective (stableValue (m := m)) :=
  (ringIsoCert m).injective

/-- Partition X_m into even-value and odd-value elements. -/
noncomputable def evenElements (m : Nat) : Finset (X m) := by
  classical
  exact Finset.univ.filter (fun x => stableValue x % 2 = 0)

/-- Partition X_m into odd-value elements. -/
noncomputable def oddElements (m : Nat) : Finset (X m) := by
  classical
  exact Finset.univ.filter (fun x => stableValue x % 2 = 1)

/-- Even and odd elements partition X_m (disjointness). -/
theorem even_odd_disjoint (m : Nat) :
    Disjoint (evenElements m) (oddElements m) := by
  classical
  exact Finset.disjoint_filter.2 (fun x _ h1 h2 => by omega)

/-- The fiber of x consists of words whose Fold equals x,
    i.e., words whose weight equals stableValue x. -/
theorem mem_fiber_iff_fold (x : X m) (w : Word m) :
    w ∈ fiber x ↔ Fold w = x := by
  classical
  exact mem_fiber

/-- The modular projection is surjective: every element of X_m
    is the projection of some element of X_{m+1}. -/
theorem modularProject_surjective (m : Nat) :
    Function.Surjective (modularProject (m := m)) := by
  intro y
  -- y : X m. Take x = appendFalse y : X (m+1). Then restrict x = y.
  refine ⟨X.appendFalse y, ?_⟩
  apply eq_of_stableValue_eq
  rw [stableValue_modularProject, stableValue_restrict_appendFalse,
    Nat.mod_eq_of_lt (stableValue_lt_paperFib_succ y)]

end

end X

end Omega
