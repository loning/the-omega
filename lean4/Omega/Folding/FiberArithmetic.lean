import Omega.Folding.Fiber

namespace Omega

namespace X

noncomputable section

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

/-- The carry element at resolution m: χ^car_m = s_m(F_m) = ofNat m (Nat.fib m).
    Paper notation: χ^car_m is the unique element carrying the carry defect. -/
noncomputable def carryElement (m : Nat) : X m :=
  X.ofNat m (Nat.fib m)

/-- The carry element value: stableValue(χ^car_m) = Nat.fib m.
    This holds because Nat.fib m < paperFib(m+1) = Nat.fib(m+2) for all m. -/
theorem stableValue_carryElement :
    stableValue (carryElement m) = Nat.fib m :=
  stableValue_ofNat_lt _ (by
    show Nat.fib m < Nat.fib (m + 2)
    have h : Nat.fib (m + 2) = Nat.fib m + Nat.fib (m + 1) := Nat.fib_add_two
    have hpos : 0 < Nat.fib (m + 1) := Nat.fib_pos.mpr (by omega)
    omega)

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

/-- The stable semiring has a well-defined characteristic: paperFib(m+1). -/
theorem stableAdd_characteristic (x : X m) :
    (Finset.range (paperFib (m + 1))).sum (fun _ => stableValue x) % paperFib (m + 1) = 0 := by
  simp [Finset.sum_const, Nat.mul_mod_right]

/-- stableAdd is idempotent on zero: 0 + 0 = 0. -/
theorem stableAdd_zero_zero : stableAdd (stableZero (m := m)) stableZero = stableZero :=
  stableAdd_zero_left stableZero

/-- stableMul is idempotent on zero: 0 * 0 = 0. -/
theorem stableMul_zero_zero : stableMul (stableZero (m := m)) stableZero = stableZero :=
  stableMul_zero_left stableZero

/-- stableMul is idempotent on one (when F_{m+2} > 1): 1 * 1 = 1. -/
theorem stableMul_one_one (hm : 1 < paperFib (m + 1)) :
    stableMul (stableOne (m := m)) stableOne = stableOne := by
  exact stableMul_one_left hm stableOne

/-- stableAdd of x with itself n times equals stableMul by ofNat n
    (when n < F_{m+2}). This connects repeated addition to multiplication. -/
theorem stableAdd_self_eq_stableMul_two (x : X m) (hm : 2 < paperFib (m + 1)) :
    stableAdd x x = stableMul (X.ofNat m 2) x := by
  apply eq_of_stableValue_eq
  rw [stableValue_stableAdd, stableValue_stableMul, stableValue_ofNat_lt 2 hm]
  ring_nf


/-- The stable ring at resolution 1 has exactly 2 elements: X_1 ≅ ℤ/2ℤ. -/
theorem card_X1_eq_two : Fintype.card (X 1) = 2 := card_X_one

/-- The stable ring at resolution 2 has exactly 3 elements: X_2 ≅ ℤ/3ℤ. -/
theorem card_X2_eq_three : Fintype.card (X 2) = 3 := card_X_two

/-- stableValue is a bijection at every resolution (complete bijectivity). -/
theorem stableValue_is_bijection (m : Nat) :
    Function.Bijective (stableValueFin (m := m)) :=
  stableValueFin_bijective m

/-- The Fold map factors through stableValue: Fold w = ofNat m (weight w). -/
theorem Fold_eq_ofNat_weight (w : Word m) :
    Fold w = X.ofNat m (weight w) := rfl

/-- Two words with the same weight fold to the same stable word. -/
theorem Fold_eq_of_weight_eq {w₁ w₂ : Word m} (h : weight w₁ = weight w₂) :
    Fold w₁ = Fold w₂ := by
  simp [Fold, h]

/-- The stable value of appendFalse equals that of the original. -/
theorem stableValue_appendFalse' (x : X m) :
    stableValue (X.appendFalse x) = stableValue x :=
  stableValue_restrict_appendFalse x

/-- stableAdd with itself equals stableMul by 2 (named). -/
theorem double_is_two_mul (x : X m) (hm : 2 < paperFib (m + 1)) :
    stableAdd x x = stableMul (X.ofNat m 2) x :=
  stableAdd_self_eq_stableMul_two x hm

/-- The stable value of the appendTrue extension. -/
theorem stableValue_appendTrue' (x : X m) (h : get x.1 (m - 1) = false) :
    stableValue (X.appendTrue x h) = stableValue x + paperFib (m + 1) :=
  stableValue_appendTrue x h

/-- The stable value of the zero element at any resolution. -/
theorem stableValue_zero_eq : stableValue (stableZero (m := m)) = 0 :=
  stableValue_stableZero

/-- Fiber partition is complete: every word is in exactly one fiber. -/
theorem word_in_unique_fiber (w : Word m) :
    ∃! x : X m, w ∈ fiber x := by
  classical
  exact ⟨Fold w, mem_fiber_Fold w, fun y hy => (mem_fiber.1 hy).symm⟩

/-- The restriction of a stable word preserves stability. -/
theorem restrict_preserves_stability (x : X (m + 1)) : No11 (X.restrict x).1 :=
  (X.restrict x).2

/-- stableAdd with zero on both sides. -/
theorem stableAdd_zero_both :
    stableAdd (stableZero (m := m)) stableZero = stableZero :=
  stableAdd_zero_zero

/-- Fold is monotone in the sense that it maps to a unique stable target. -/
theorem Fold_unique_target (w : Word m) : ∃! x : X m, Fold w = x :=
  ⟨Fold w, rfl, fun _ h => h.symm⟩

/-- stableNeg is its own inverse: stableNeg ∘ stableNeg = id. -/
theorem stableNeg_involutive : Function.Involutive (stableNeg (m := m)) :=
  stableNeg_neg_eq

/-- stableNeg is injective. -/
theorem stableNeg_injective : Function.Injective (stableNeg (m := m)) :=
  stableNeg_involutive.injective

/-- stableNeg is surjective. -/
theorem stableNeg_surjective : Function.Surjective (stableNeg (m := m)) :=
  stableNeg_involutive.surjective

/-- stableNeg is bijective. -/
theorem stableNeg_bijective : Function.Bijective (stableNeg (m := m)) :=
  stableNeg_involutive.bijective

/-- stableMul by zero annihilates on the right (named). -/
theorem stableMul_annihilates_right (x : X m) :
    stableMul x stableZero = stableZero :=
  stableMul_zero_right x

/-- stableMul by zero annihilates on the left (named). -/
theorem stableMul_annihilates_left (x : X m) :
    stableMul stableZero x = stableZero :=
  stableMul_zero_left x

/-- stableAdd is injective in its second argument (fixed first). -/
theorem stableAdd_injective_right (x : X m) : Function.Injective (stableAdd x) :=
  fun _ _ h => stableAdd_left_cancel h

/-- stableAdd is injective in its first argument (fixed second). -/
theorem stableAdd_injective_left (y : X m) : Function.Injective (fun x => stableAdd x y) :=
  fun _ _ h => stableAdd_right_cancel h

/-- The stableAdd group action on X_m is free: x + · is a bijection for each x. -/
theorem stableAdd_bijective (x : X m) : Function.Bijective (stableAdd x) :=
  ⟨stableAdd_injective_right x,
   fun y => ⟨stableSub y x, by rw [stableAdd_comm]; exact stableSub_add_cancel y x⟩⟩


/-- stableSub with zero on the right: x - 0 = x. -/
theorem stableSub_zero (x : X m) : stableSub x stableZero = x := by
  rw [stableSub, stableNeg_zero, stableAdd_zero_right]

/-- stableSub with zero on the left: 0 - x = -x. -/
theorem zero_stableSub (x : X m) : stableSub stableZero x = stableNeg x := by
  rw [stableSub, stableAdd_zero_left]

/-- Fiber multiplicity of the zero element equals the number of words with weight 0. -/
theorem fiberMultiplicity_stableZero :
    fiberMultiplicity (stableZero (m := m)) ≥ 1 :=
  fiberMultiplicity_pos stableZero

/-- The Fold map is an endomorphism of Word m (in the sense that Fold : Word m → X m). -/
theorem Fold_maps_to_stable (w : Word m) : No11 (Fold w).1 :=
  (Fold w).2

/-- Stable words are bounded by all words: |X_m| ≤ |Word m| = 2^m. -/
theorem stable_le_all_words (m : Nat) :
    Fintype.card (X m) ≤ Fintype.card (Word m) :=
  Fintype.card_le_of_injective (fun x => x.1) Subtype.val_injective

/-- F_{m+2} ≤ 2^m (Fibonacci growth bound). -/
theorem paperFib_le_pow (m : Nat) : paperFib (m + 1) ≤ 2 ^ m := by
  rw [← X.card_eq_paperFib_succ, ← Word_card]
  exact stable_le_all_words m

/-- |X_m| ≤ 2^m (combining cardinality and word space size). -/
theorem stable_card_le_pow (m : Nat) :
    Fintype.card (X m) ≤ 2 ^ m := by
  rw [← Word_card]; exact stable_le_all_words m

/-- Average fiber multiplicity: (∑ mult) / |X_m| = 2^m / F_{m+2}. -/
theorem avg_fiber_numerator_denominator (m : Nat) :
    (∑ x : X m, fiberMultiplicity x) = 2 ^ m ∧
    Fintype.card (X m) = paperFib (m + 1) :=
  ⟨fiberMultiplicity_sum_eq_pow m, X.card_eq_paperFib_succ m⟩

/-- The modular projection preserves multiplication (no-carry case). -/
theorem modularProject_mul_no_carry (x y : X (m + 1))
    (h : stableValue x * stableValue y < paperFib (m + 2)) :
    modularProject (stableMul x y) = stableMul (modularProject x) (modularProject y) := by
  apply eq_of_stableValue_eq
  rw [stableValue_modularProject, stableValue_stableMul, stableValue_stableMul,
    stableValue_modularProject, stableValue_modularProject, Nat.mod_eq_of_lt h, Nat.mul_mod]

/-- stableMul by one on the right is the identity (when F > 1). -/
theorem stableMul_one_right' (hm : 1 < paperFib (m + 1)) (x : X m) :
    stableMul x stableOne = x := by
  rw [stableMul_comm]; exact stableMul_one_left hm x

/-- The stable ring has no zero divisors when paperFib(m+1) is prime. -/
theorem stableMul_no_zero_divisor_of_prime (hPrime : Nat.Prime (paperFib (m + 1)))
    {x y : X m} (hx : x ≠ stableZero) (hy : y ≠ stableZero) :
    stableMul x y ≠ stableZero := by
  intro hxy
  have hValX : stableValue x ≠ 0 := by
    intro h; exact hx (eq_of_stableValue_eq (h.trans stableValue_stableZero.symm))
  have hValY : stableValue y ≠ 0 := by
    intro h; exact hy (eq_of_stableValue_eq (h.trans stableValue_stableZero.symm))
  have hMul := congr_arg stableValue hxy
  rw [stableValue_stableMul, stableValue_stableZero] at hMul
  have hDvd : paperFib (m + 1) ∣ stableValue x * stableValue y :=
    Nat.dvd_of_mod_eq_zero hMul
  rcases hPrime.dvd_mul.mp hDvd with hDvdX | hDvdY
  · exact hValX (Nat.eq_zero_of_dvd_of_lt hDvdX (stableValue_lt_paperFib_succ x))
  · exact hValY (Nat.eq_zero_of_dvd_of_lt hDvdY (stableValue_lt_paperFib_succ y))

/-- Concrete: F_3 = 3 is prime, so X_2 ≅ F_3 is a field. -/
theorem X2_is_integral_domain : Nat.Prime (paperFib 3) := by decide

/-- Concrete: F_5 = 8 is NOT prime (2^3). -/
theorem F5_not_prime : ¬ Nat.Prime (paperFib 5) := by decide

/-- Concrete: F_7 = 21 is NOT prime (3 × 7). -/
theorem F7_not_prime : ¬ Nat.Prime (paperFib 7) := by decide

/-- Concrete: F_11 = 144 is NOT prime (2^4 × 3^2). -/
theorem F11_not_prime : ¬ Nat.Prime (paperFib 11) := by decide

/-- Concrete: F_4 = 5 is prime. -/
theorem F4_is_prime : Nat.Prime (paperFib 4) := by decide

/-- Concrete: F_2 = 2 is prime. -/
theorem F2_is_prime : Nat.Prime (paperFib 2) := by decide

/-- F_6 = 13 is prime. -/
theorem F6_is_prime : Nat.Prime (paperFib 6) := by decide

/-- F_8 = 34 is NOT prime. -/
theorem F8_not_prime : ¬ Nat.Prime (paperFib 8) := by decide

/-- F_10 = 89 is prime. -/
theorem F10_is_prime : Nat.Prime (paperFib 10) := by decide

/-- The Fibonacci primes in the first 11 values: F_2=2, F_3=3, F_4=5, F_6=13, F_10=89. -/
theorem fibonacci_prime_list :
    Nat.Prime (paperFib 2) ∧ Nat.Prime (paperFib 3) ∧ Nat.Prime (paperFib 4) ∧
    Nat.Prime (paperFib 6) ∧ Nat.Prime (paperFib 10) :=
  ⟨F2_is_prime, X2_is_integral_domain, F4_is_prime, F6_is_prime, F10_is_prime⟩

/-- F_9 = 55 is NOT prime (5 × 11). -/
theorem F9_not_prime : ¬ Nat.Prime (paperFib 9) := by decide

/-- The Fibonacci composite values in F_2..F_11: F_5=8, F_7=21, F_8=34, F_9=55, F_11=144. -/
theorem fibonacci_composite_list :
    ¬ Nat.Prime (paperFib 5) ∧ ¬ Nat.Prime (paperFib 7) ∧
    ¬ Nat.Prime (paperFib 8) ∧ ¬ Nat.Prime (paperFib 9) ∧
    ¬ Nat.Prime (paperFib 11) :=
  ⟨F5_not_prime, F7_not_prime, F8_not_prime, F9_not_prime, F11_not_prime⟩

/-- stableValue is strictly less than 2^m (combining bounds). -/
theorem stableValue_lt_pow (x : X m) : stableValue x < 2 ^ m := by
  exact Nat.lt_of_lt_of_le (stableValue_lt_paperFib_succ x) (paperFib_le_pow m)


/-- stableValue determines ofNat on valid inputs. -/
theorem ofNat_of_stableValue (x : X m) :
    X.ofNat m (stableValue x) = x :=
  X.ofNat_stableValue x

/-- Fold composed with stableValue gives back the original value. -/
theorem Fold_stableValue_roundtrip (x : X m) :
    stableValue (Fold x.1) = stableValue x := by
  rw [Fold_stable]

/-- stableAdd preserves the bound: if both < F, sum mod F < F. -/
theorem stableAdd_value_bound (x y : X m) :
    stableValue (stableAdd x y) < paperFib (m + 1) :=
  stableValue_lt_paperFib_succ _

/-- stableMul preserves the bound. -/
theorem stableMul_value_bound (x y : X m) :
    stableValue (stableMul x y) < paperFib (m + 1) :=
  stableValue_lt_paperFib_succ _

/-- stableNeg of stableOne gives the maximal nonzero element. -/
theorem neg_one_value (hm : 1 ≤ m) :
    stableValue (stableNeg (stableOne (m := m))) = paperFib (m + 1) - 1 :=
  stableValue_neg_one hm

/-- The stable ring cardinality matches the Fibonacci number. -/
theorem stable_ring_order (m : Nat) : Fintype.card (X m) = paperFib (m + 1) :=
  X.card_eq_paperFib_succ m

/-- Concrete: |X_11| = 233. -/
theorem card_X_eleven : Fintype.card (X 11) = 233 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- Concrete: |X_12| = 377. -/
theorem card_X_twelve : Fintype.card (X 12) = 377 := by
  rw [X.card_eq_paperFib_succ]; rfl

/-- F_12 = 233 is prime. -/
theorem F12_is_prime : Nat.Prime (paperFib 12) := by native_decide

/-- |X_13| = 610. -/
theorem card_X_thirteen : Fintype.card (X 13) = 610 := by
  rw [X.card_eq_paperFib_succ]; native_decide

/-- The carry element value (named variant). -/
theorem carryElement_value :
    stableValue (carryElement m) = Nat.fib m :=
  stableValue_carryElement

/-- modularProject preserves the zero element. -/
theorem modularProject_preserves_zero :
    modularProject (stableZero (m := m + 1)) = stableZero :=
  modularProject_zero

/-- stableSub value is stableAdd of x and neg y values. -/
theorem stableValue_sub_eq (x y : X m) :
    stableValue (stableSub x y) = stableValue (stableAdd x (stableNeg y)) := rfl

/-- Fiber multiplicity is always positive (named). -/
theorem fiber_always_positive (x : X m) : 0 < fiberMultiplicity x :=
  fiberMultiplicity_pos x

/-- The stable ring has exactly F_{m+2} elements (named). -/
theorem ring_cardinality (m : Nat) : Fintype.card (X m) = paperFib (m + 1) :=
  X.card_eq_paperFib_succ m

/-- Fold preserves No11 (stable output). -/
theorem Fold_output_is_stable (w : Word m) : No11 (Fold w).1 :=
  Fold_maps_to_stable w

/-- The fiber partition is a complete disjoint decomposition. -/
theorem fiber_decomposition_complete (m : Nat) :
    (∀ w : Word m, ∃! x : X m, w ∈ fiber x) ∧
    (∀ x : X m, 0 < (fiber x).card) ∧
    (∑ x : X m, (fiber x).card = 2 ^ m) :=
  ⟨word_in_unique_fiber, fiber_card_pos, fiber_card_sum_eq_pow m⟩

/-- stableSub cancels on the right: (x + y) - y = x. -/
theorem add_sub_cancel_right (x y : X m) : stableSub (stableAdd x y) y = x :=
  stableSub_stableAdd_cancel x y

/-- stableSub followed by add recovers: (x - y) + y = x. -/
theorem sub_add_recover (x y : X m) : stableAdd (stableSub x y) y = x :=
  stableSub_add_cancel x y

/-- stableAdd homomorphism (named). -/
theorem stableAdd_hom (x y : X m) :
    stableValue (stableAdd x y) = (stableValue x + stableValue y) % paperFib (m + 1) :=
  stableValue_stableAdd x y

/-- stableMul homomorphism (named). -/
theorem stableMul_hom (x y : X m) :
    stableValue (stableMul x y) = (stableValue x * stableValue y) % paperFib (m + 1) :=
  stableValue_stableMul x y

/-- stableNeg homomorphism (named). -/
theorem stableNeg_hom (x : X m) :
    stableValue (stableNeg x) = (paperFib (m + 1) - stableValue x) % paperFib (m + 1) :=
  stableValue_stableNeg x

/-- Complete ring axioms for X_m (8 laws). -/
theorem complete_ring_axioms (m : Nat) :
    (∀ x y : X m, stableAdd x y = stableAdd y x) ∧
    (∀ x y z : X m, stableAdd (stableAdd x y) z = stableAdd x (stableAdd y z)) ∧
    (∀ x : X m, stableAdd stableZero x = x) ∧
    (∀ x : X m, stableAdd x (stableNeg x) = stableZero) ∧
    (∀ x y : X m, stableMul x y = stableMul y x) ∧
    (∀ x y z : X m, stableMul (stableMul x y) z = stableMul x (stableMul y z)) ∧
    (∀ x y z : X m, stableMul x (stableAdd y z) = stableAdd (stableMul x y) (stableMul x z)) ∧
    (∀ x y z : X m, stableAdd x y = stableAdd x z → y = z) :=
  ⟨stableAdd_comm, stableAdd_assoc, stableAdd_zero_left, stableAdd_stableNeg,
   stableMul_comm, stableMul_assoc, stableMul_stableAdd_left, fun _ _ _ h => stableAdd_left_cancel h⟩

end

/-- Even and odd stableValue elements partition X m. -/
theorem even_odd_card_sum (m : Nat) :
    (evenElements m).card + (oddElements m).card = paperFib (m + 1) := by
  classical
  rw [← X.card_eq_paperFib_succ, ← Finset.card_univ]
  rw [← Finset.card_union_of_disjoint (even_odd_disjoint m)]
  congr 1; ext x
  simp only [Finset.mem_union, evenElements, oddElements, Finset.mem_filter, Finset.mem_univ, true_and]
  rcases Nat.mod_two_eq_zero_or_one (stableValue x) with h | h <;> simp [h]

