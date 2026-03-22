import Omega.Folding.CarryDefect
import Omega.Folding.Defect

namespace Omega

namespace X

noncomputable section

/-! ## Modular mapping tower: modularProject–restrict equivalence and tower properties -/

/-! ### Auxiliary: re-derive stableValue(restrict z) = stableValue z % G -/

/-- stableValue(restrict z) = stableValue z % paperFib(m+1). -/
private theorem stableValue_restrict_eq_mod_tower (z : X (m + 1)) :
    stableValue (X.restrict z) = stableValue z % paperFib (m + 1) := by
  have h1 := stableValue_restrict_mod z
  have h2 := stableValue_lt_paperFib_succ (X.restrict z)
  rw [Nat.mod_eq_of_lt h2] at h1
  exact h1.symm

/-! ### Theorem 1: modularProject = restrict -/

/-- modularProject equals restrict as functions X(m+1) → X(m).
    Both produce the unique stable word with value stableValue(x) % paperFib(m+1). -/
theorem modularProject_eq_restrict (x : X (m + 1)) :
    modularProject x = X.restrict x := by
  apply eq_of_stableValue_eq
  rw [stableValue_modularProject, ← stableValue_restrict_eq_mod_tower]

/-! ### Theorem 2: modularProject carry defect for addition -/

/-- modularProject carry defect for addition (via restrict equivalence).
    Paper: thm:pom-stable-addition-carry-defect-unique-element (modularProject form) -/
theorem modularProject_stableAdd_carry (x y : X (m + 1)) :
    modularProject (stableAdd x y) =
      stableAdd (stableAdd (modularProject x) (modularProject y))
        (if carryIndicator x y = 0 then stableZero else carryElement m) := by
  rw [modularProject_eq_restrict, modularProject_eq_restrict x, modularProject_eq_restrict y]
  exact restrict_stableAdd_carry_defect x y

/-! ### Theorem 3: multiplicative projection value identity -/

/-- Value-level identity for multiplicative projection through the tower. -/
theorem stableValue_modularProject_stableMul (x y : X (m + 1)) :
    stableValue (modularProject (stableMul x y)) =
      (stableValue x * stableValue y) % paperFib (m + 2) % paperFib (m + 1) := by
  rw [stableValue_modularProject, stableValue_stableMul]

/-- Multiplicative projection via restrict. -/
theorem stableValue_restrict_stableMul (x y : X (m + 1)) :
    stableValue (X.restrict (stableMul x y)) =
      (stableValue x * stableValue y) % paperFib (m + 2) % paperFib (m + 1) := by
  rw [stableValue_restrict_eq_mod_tower, stableValue_stableMul]

/-! ### Theorem 4: restrict compose equals restrictLE -/

/-- Two applications of restrict equal the composed restrictLE. -/
theorem restrict_comp_restrict (x : X (m + 2)) :
    X.restrict (X.restrict x) =
      X.restrictLE (Nat.le_trans (Nat.le_succ m) (Nat.le_succ (m + 1))) x := by
  conv_lhs =>
    rw [show X.restrict x = X.restrictLE (Nat.le_succ (m + 1)) x from
      (X.restrictLE_succ x).symm]
    rw [show X.restrict (X.restrictLE (Nat.le_succ (m + 1)) x) =
      X.restrictLE (Nat.le_succ m) (X.restrictLE (Nat.le_succ (m + 1)) x) from
      (X.restrictLE_succ (X.restrictLE (Nat.le_succ (m + 1)) x)).symm]
  exact X.restrictLE_comp (Nat.le_succ m) (Nat.le_succ (m + 1)) x

/-! ### Theorem 5: tower compatibility -/

/-- The tower of restriction maps is compatible: restrict ∘ restrict = restrictLE. -/
theorem tower_compatible (x : X (m + 2)) :
    X.restrict (X.restrict x) = X.restrictLE (Nat.le_succ m) (X.restrict x) := by
  rw [X.restrictLE_succ]

/-! ### Theorem 6: restrict transitivity -/

/-- restrict composes correctly via restrictLE transitivity. -/
theorem restrict_tower_transitivity (h₁ : m ≤ n) (x : X (n + 1)) :
    X.restrictLE h₁ (X.restrict x) =
      X.restrictLE (Nat.le_trans h₁ (Nat.le_succ n)) x := by
  exact (X.restrictLE_trans_succ h₁ x).symm

/-! ### Theorem 7: modularProject preserves zero -/

/-- modularProject preserves the zero element. -/
theorem modularProject_stableZero :
    modularProject (stableZero (m := m + 1)) = (stableZero : X m) :=
  modularProject_zero

/-! ### Additional tower properties -/

/-- Value-level carry defect for modularProject addition. -/
theorem stableValue_modularProject_stableAdd_carry (x y : X (m + 1)) :
    stableValue (modularProject (stableAdd x y)) =
      (stableValue (modularProject x) + stableValue (modularProject y) +
        carryIndicator x y * Nat.fib m) % paperFib (m + 1) := by
  rw [modularProject_eq_restrict, modularProject_eq_restrict x, modularProject_eq_restrict y]
  exact stableValue_restrict_stableAdd_carry x y

/-- modularProject composes through two levels via double mod. -/
theorem stableValue_modularProject_compose (x : X (m + 2)) :
    stableValue (modularProject (m := m) (modularProject (m := m + 1) x)) =
      stableValue x % paperFib (m + 2) % paperFib (m + 1) := by
  rw [stableValue_modularProject, stableValue_modularProject]

/-- The carry indicator is symmetric. -/
theorem carryIndicator_comm (x y : X (m + 1)) :
    carryIndicator x y = carryIndicator y x := by
  unfold carryIndicator; rw [Nat.add_comm]

/-- The modularProject tower: surjectivity at every level. -/
theorem modularProject_tower_surjective (m : Nat) :
    Function.Surjective (modularProject (m := m)) :=
  modularProject_surjective m

end

end X

end Omega
