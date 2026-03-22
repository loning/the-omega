import Omega.Folding.Weight

namespace Omega

/-- The Fibonacci-weighted value restricted to stable words. -/
def stableValue (x : X m) : Nat :=
  weight x.1

@[simp] theorem stableValue_restrict_appendFalse (x : X m) :
    stableValue (X.appendFalse x) = stableValue x := by
  simp [stableValue]

@[simp] theorem stableValue_appendTrue (x : X m) (hLast : get x.1 (m - 1) = false) :
    stableValue (X.appendTrue x hLast) = stableValue x + paperFib (m + 1) := by
  simp [stableValue, X.appendTrue, weight_snoc]

/-- Stable values are strictly bounded by the Fibonacci cardinality.
    This is the key bound enabling finite stable arithmetic on `X m`. -/
theorem stableValue_lt_paperFib_succ : ∀ {m : Nat}, (x : X m) → stableValue x < paperFib (m + 1)
  | 0, x => by
    have : x = X.empty := Unique.eq_default x; subst this
    exact paperFib_pos 1
  | n + 1, x => by
    by_cases hLast : Omega.last x.1 = true
    · -- x ends in true: stableValue x = stableValue(restrict x) + paperFib(n+1)
      have hRestr : get (X.restrict x).1 (n - 1) = false :=
        X.restrict_endsInZero_of_last_true x hLast
      have hRec : X.appendTrue (X.restrict x) hRestr = x :=
        X.appendTrue_reconstruct x hLast hRestr
      rw [← hRec, stableValue_appendTrue]
      -- Need: stableValue(restrict x) < paperFib n
      -- When n = 0, restrict x : X 0 = empty has stableValue 0 < paperFib 0 = 1
      -- When n ≥ 1, restrict x ends in false, so stableValue = stableValue(double restrict)
      suffices h : stableValue (X.restrict x) < paperFib n by
        calc stableValue (X.restrict x) + paperFib (n + 1)
            < paperFib n + paperFib (n + 1) := Nat.add_lt_add_right h _
          _ = paperFib (n + 1) + paperFib n := Nat.add_comm _ _
          _ = paperFib (n + 2) := (paperFib_recurrence n).symm
      cases n with
      | zero =>
        have : X.restrict x = X.empty := Unique.eq_default _
        rw [this]; exact paperFib_pos 0
      | succ k =>
        -- restrict x : X (k+1) ends in false (second-to-last bit of x is false by No11)
        have hRestrLast : Omega.last (X.restrict x).1 = false := by
          simp only [Omega.last, X.restrict_val, Omega.truncate]
          simp only [X.EndsInZero, Omega.get] at hRestr
          convert hRestr using 1
          simp [Nat.succ_sub_one]
        have hRec2 := X.appendFalse_reconstruct (X.restrict x) hRestrLast
        rw [← hRec2, stableValue_restrict_appendFalse]
        exact stableValue_lt_paperFib_succ (X.restrict (X.restrict x))
    · -- x ends in false: stableValue x = stableValue(restrict x) < paperFib(n+1) ≤ paperFib(n+2)
      have hLastFalse : Omega.last x.1 = false := by
        cases hBit : Omega.last x.1 <;> simp_all
      rw [← X.appendFalse_reconstruct x hLastFalse, stableValue_restrict_appendFalse]
      exact Nat.lt_of_lt_of_le
        (stableValue_lt_paperFib_succ (X.restrict x))
        (paperFib_le_succ (n + 1))


/-- The stable value decomposes as: restrict's value + last bit contribution. -/
theorem stableValue_eq_restrict_add_last (x : X (m + 1)) :
    stableValue x = stableValue (X.restrict x) +
      (if x.1 ⟨m, Nat.lt_succ_self m⟩ = true then paperFib (m + 1) else 0) := by
  simp [stableValue, weight, X.restrict]

/-- The stable value of restrict x is at most stableValue x. -/
theorem stableValue_restrict_le (x : X (m + 1)) :
    stableValue (X.restrict x) ≤ stableValue x := by
  rw [stableValue_eq_restrict_add_last]
  exact Nat.le_add_right _ _

/-- The stable value of restrict x equals stableValue x modulo paperFib(m+1). -/
theorem stableValue_restrict_mod (x : X (m + 1)) :
    stableValue x % paperFib (m + 1) = stableValue (X.restrict x) % paperFib (m + 1) := by
  rw [stableValue_eq_restrict_add_last x]
  by_cases hLast : x.1 ⟨m, Nat.lt_succ_self m⟩ = true
  · simp only [hLast, ite_true, Nat.add_mod, Nat.mod_self, Nat.add_zero, Nat.mod_mod]
  · have hFalse : x.1 ⟨m, Nat.lt_succ_self m⟩ = false := by
      cases h : x.1 ⟨m, _⟩ <;> simp_all
    simp only [hFalse, Bool.false_eq_true, ite_false, Nat.add_zero]

/-- The carry indicator for stable addition at resolution m+1. -/
def carryIndicator (x y : X (m + 1)) : Nat :=
  if stableValue x + stableValue y ≥ paperFib (m + 2) then 1 else 0

/-- The carry indicator is zero when the sum is below the threshold. -/
theorem carryIndicator_zero_of_lt (x y : X (m + 1))
    (h : stableValue x + stableValue y < paperFib (m + 2)) :
    carryIndicator x y = 0 := by
  simp [carryIndicator, not_le.mpr h]

/-- The carry indicator is one when the sum reaches the threshold. -/
theorem carryIndicator_one_of_ge (x y : X (m + 1))
    (h : stableValue x + stableValue y ≥ paperFib (m + 2)) :
    carryIndicator x y = 1 := by
  simp [carryIndicator, h]

/-- stableValue of the empty word is 0. -/
@[simp] theorem stableValue_empty : stableValue (X.empty : X 0) = 0 := by
  simp [stableValue, weight]

/-- stableValue is nonneg (trivially, since it's a Nat). -/
theorem stableValue_nonneg (x : X m) : 0 ≤ stableValue x :=
  Nat.zero_le _

end Omega
