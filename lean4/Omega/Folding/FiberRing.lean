import Omega.Folding.FiberArithmetic

/-! ### CommRing instance for X m

The stable syntax space X_m carries a commutative ring structure isomorphic to
ℤ/F_{m+2}ℤ, where F_{m+2} = Nat.fib (m + 2). -/

namespace Omega.X

noncomputable section

/-- stableOne is the left multiplicative identity, unconditionally. -/
theorem stableMul_one_left_univ (x : X m) : stableMul stableOne x = x := by
  cases m with
  | zero =>
    have : Subsingleton (X 0) := by
      rw [← Fintype.card_le_one_iff_subsingleton]; simp [X.card_eq_fib]
    exact Subsingleton.elim _ _
  | succ n => exact stableMul_one_left (fib_gt_one_of_ge_two (by omega)) x

/-- stableOne is the right multiplicative identity, unconditionally. -/
theorem stableMul_one_right_univ (x : X m) : stableMul x stableOne = x := by
  rw [stableMul_comm]; exact stableMul_one_left_univ x

-- Build instances bottom-up through the typeclass hierarchy.

noncomputable instance instAdd : Add (X m) := ⟨stableAdd⟩
noncomputable instance instZero : Zero (X m) := ⟨stableZero⟩
noncomputable instance instNeg : Neg (X m) := ⟨stableNeg⟩
noncomputable instance instMul : Mul (X m) := ⟨stableMul⟩
noncomputable instance instOne : One (X m) := ⟨stableOne⟩

/-- The commutative ring structure on X_m ≅ ℤ/F_{m+2}ℤ. -/
noncomputable instance instCommRing : CommRing (X m) where
  nsmul := nsmulRec
  zsmul := zsmulRec
  add_assoc := stableAdd_assoc
  zero_add := stableAdd_zero_left
  add_zero := stableAdd_zero_right
  neg_add_cancel := stableNeg_stableAdd
  add_comm := stableAdd_comm
  mul_assoc := stableMul_assoc
  one_mul := stableMul_one_left_univ
  mul_one := stableMul_one_right_univ
  zero_mul := stableMul_zero_left
  mul_zero := stableMul_zero_right
  left_distrib := stableMul_stableAdd_left
  right_distrib := fun a b c => stableMul_stableAdd_right c a b
  mul_comm := stableMul_comm

/-- The ring addition on X_m agrees with stableAdd. -/
theorem ring_add_eq (x y : X m) : x + y = stableAdd x y := rfl

/-- The ring multiplication on X_m agrees with stableMul. -/
theorem ring_mul_eq (x y : X m) : x * y = stableMul x y := rfl

/-- The ring zero on X_m is stableZero. -/
theorem ring_zero_eq : (0 : X m) = stableZero := rfl

/-- The ring one on X_m is stableOne. -/
theorem ring_one_eq : (1 : X m) = stableOne := rfl

/-- The ring negation on X_m is stableNeg. -/
theorem ring_neg_eq (x : X m) : -x = stableNeg x := rfl

/-! ### Ring isomorphism X m ≃+* ZMod (Nat.fib (m + 2)) -/

/-- NeZero instance for Nat.fib (m + 2), needed for ZMod. -/
instance instNeZeroFib : NeZero (Nat.fib (m + 2)) :=
  ⟨by exact Nat.pos_iff_ne_zero.mp (Nat.fib_pos.mpr (by omega))⟩

/-- The stable value map as a function to ZMod: x ↦ ↑(stableValue x). -/
noncomputable def toZMod (x : X m) : ZMod (Nat.fib (m + 2)) :=
  (stableValue x : ZMod (Nat.fib (m + 2)))

/-- toZMod preserves addition. -/
theorem toZMod_add (x y : X m) : toZMod (x + y) = toZMod x + toZMod y := by
  simp only [toZMod, ring_add_eq, stableValue_stableAdd, Nat.cast_add, ZMod.natCast_mod]

/-- toZMod preserves multiplication. -/
theorem toZMod_mul (x y : X m) : toZMod (x * y) = toZMod x * toZMod y := by
  simp only [toZMod, ring_mul_eq, stableValue_stableMul, Nat.cast_mul, ZMod.natCast_mod]

/-- toZMod sends 0 to 0. -/
theorem toZMod_zero : toZMod (0 : X m) = 0 := by
  simp only [toZMod, ring_zero_eq, stableValue_stableZero, Nat.cast_zero]

/-- toZMod sends 1 to 1. -/
theorem toZMod_one : toZMod (1 : X m) = 1 := by
  -- Use: 1 * 1 = 1, and toZMod preserves multiplication
  have h : toZMod (1 * 1 : X m) = toZMod 1 * toZMod 1 := toZMod_mul 1 1
  rw [mul_one] at h
  -- h : toZMod 1 = toZMod 1 * toZMod 1
  -- Also toZMod 1 = toZMod (1 + 0) = toZMod 1 + 0 = toZMod 1 (trivially)
  -- Use: 0 = toZMod 0, and 1 = toZMod 1 requires what we're proving.
  -- Different approach: use that toZMod is a RingHom once constructed,
  -- or prove directly.
  unfold toZMod
  rw [ring_one_eq]
  cases m with
  | zero =>
    -- stableValue stableOne = 0 in X 0 (since X 0 is trivial, stableOne = stableZero)
    have : Subsingleton (X 0) := by
      rw [← Fintype.card_le_one_iff_subsingleton]; simp [X.card_eq_fib]
    rw [show (stableOne : X 0) = stableZero from Subsingleton.elim _ _, stableValue_stableZero]
    -- Goal: (0 : ZMod (Nat.fib 2)) = 1. Nat.fib 2 = 1, so ZMod 1 is trivial.
    -- ZMod (Nat.fib 2) = ZMod 1, in which 0 = 1
    change (0 : ZMod (Nat.fib 2)) = 1
    native_decide
  | succ n =>
    rw [stableValue_stableOne (fib_gt_one_of_ge_two (by omega))]
    simp

/-- The stable value map as a ring homomorphism to ZMod. -/
noncomputable def stableValueRingHom (m : Nat) : X m →+* ZMod (Nat.fib (m + 2)) where
  toFun := toZMod
  map_zero' := toZMod_zero
  map_one' := toZMod_one
  map_add' := toZMod_add
  map_mul' := toZMod_mul

/-- toZMod is injective. -/
theorem toZMod_injective : Function.Injective (toZMod (m := m)) := by
  intro x y h
  simp only [toZMod] at h
  have hx := stableValue_lt_fib x
  have hy := stableValue_lt_fib y
  have hval : (stableValue x : ZMod (Nat.fib (m + 2))).val =
    (stableValue y : ZMod (Nat.fib (m + 2))).val := congr_arg ZMod.val h
  rw [ZMod.val_natCast_of_lt hx, ZMod.val_natCast_of_lt hy] at hval
  exact stableValueFin_injective m (Fin.ext hval)

/-- toZMod is surjective (injective + matching cardinality). -/
theorem toZMod_surjective : Function.Surjective (toZMod (m := m)) :=
  (Finite.injective_iff_surjective_of_equiv
    (Fintype.equivOfCardEq (by rw [X.card_eq_fib, ZMod.card]))).mp toZMod_injective

/-- The ring isomorphism X_m ≃+* ZMod(F_{m+2}). -/
noncomputable def stableValueRingEquiv (m : Nat) : X m ≃+* ZMod (Nat.fib (m + 2)) :=
  RingEquiv.ofBijective (stableValueRingHom m) ⟨toZMod_injective, toZMod_surjective⟩

/-! ### Field instance when F_{m+2} is prime -/

/-- When Nat.fib (m + 2) is prime, X m is a field (transferred from ZMod via the ring iso). -/
noncomputable def instFieldOfPrime (hp : Nat.Prime (Nat.fib (m + 2))) : Field (X m) := by
  letI : Fact (Nat.Prime (Nat.fib (m + 2))) := ⟨hp⟩
  have hIsField := (stableValueRingEquiv m).symm.toMulEquiv.symm.isField (Field.toIsField _)
  exact hIsField.toField

-- Concrete field instances

/-- X_1 ≅ GF(2) is a field (F_3 = 2 is prime). -/
noncomputable instance instField_X1 : Field (X 1) :=
  instFieldOfPrime (by native_decide)

/-- X_2 ≅ GF(3) is a field (F_4 = 3 is prime). -/
noncomputable instance instField_X2 : Field (X 2) :=
  instFieldOfPrime (by native_decide)

/-- X_3 ≅ GF(5) is a field (F_5 = 5 is prime). -/
noncomputable instance instField_X3 : Field (X 3) :=
  instFieldOfPrime (by native_decide)

/-- X_5 ≅ GF(13) is a field (F_7 = 13 is prime). -/
noncomputable instance instField_X5 : Field (X 5) :=
  instFieldOfPrime (by native_decide)

/-- X_9 ≅ GF(89) is a field (F_11 = 89 is prime). -/
noncomputable instance instField_X9 : Field (X 9) :=
  instFieldOfPrime (by native_decide)

/-- X_11 ≅ GF(233) is a field (F_13 = 233 is prime). -/
noncomputable instance instField_X11 : Field (X 11) :=
  instFieldOfPrime (by native_decide)

end
end Omega.X
