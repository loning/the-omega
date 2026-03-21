import Omega.Core.Fib
import Omega.Core.No11

namespace Omega

/-- The stable syntax space of length `m`. -/
def X (m : Nat) := { w : Word m // No11 w }

namespace X

/-- Forget the last bit of a stable word. -/
def restrict (x : X (m + 1)) : X m :=
  ⟨Omega.truncate x.1, no11_truncate x.2⟩

/-- Append `0` to the right of a stable word. -/
def appendFalse (x : X m) : X (m + 1) :=
  ⟨Omega.snoc x.1 false, no11_snoc_false x.2⟩

/-- Append `1` to the right of a stable word when the current last bit is `0`. -/
def appendTrue (x : X m) (hLast : get x.1 (m - 1) = false) : X (m + 1) :=
  ⟨Omega.snoc x.1 true, no11_snoc_true x.2 hLast⟩

@[simp] theorem restrict_val (x : X (m + 1)) :
    (restrict x).1 = Omega.truncate x.1 := rfl

@[simp] theorem restrict_apply (x : X (m + 1)) (i : Fin m) :
    (restrict x).1 i = x.1 ⟨i.1, Nat.lt_trans i.2 (Nat.lt_succ_self m)⟩ := rfl

@[simp] theorem appendFalse_val (x : X m) :
    (appendFalse x).1 = Omega.snoc x.1 false := rfl

@[simp] theorem restrict_appendFalse (x : X m) : restrict (appendFalse x) = x := by
  apply Subtype.ext
  simp [appendFalse, restrict]

@[simp] theorem appendTrue_val (x : X m) (hLast : get x.1 (m - 1) = false) :
    (appendTrue x hLast).1 = Omega.snoc x.1 true := rfl

@[simp] theorem restrict_appendTrue (x : X m) (hLast : get x.1 (m - 1) = false) :
    restrict (appendTrue x hLast) = x := by
  apply Subtype.ext
  simp [appendTrue, restrict]

theorem appendFalse_reconstruct (x : X (m + 1)) (hLast : Omega.last x.1 = false) :
    appendFalse (restrict x) = x := by
  apply Subtype.ext
  funext i
  by_cases hlt : i.1 < m
  · simp [appendFalse, restrict, Omega.truncate, Omega.snoc, hlt]
  · have hEq : i.1 = m := Nat.eq_of_lt_succ_of_not_lt i.isLt hlt
    have hFin : i = ⟨m, Nat.lt_succ_self m⟩ := Fin.ext hEq
    cases hFin
    simpa [appendFalse, restrict, Omega.last] using hLast

theorem appendTrue_reconstruct (x : X (m + 1))
    (hLast : Omega.last x.1 = true)
    (hRestrict : get (restrict x).1 (m - 1) = false) :
    appendTrue (restrict x) hRestrict = x := by
  apply Subtype.ext
  funext i
  by_cases hlt : i.1 < m
  · simp [appendTrue, restrict, Omega.truncate, Omega.snoc, hlt]
  · have hEq : i.1 = m := Nat.eq_of_lt_succ_of_not_lt i.isLt hlt
    have hFin : i = ⟨m, Nat.lt_succ_self m⟩ := Fin.ext hEq
    cases hFin
    simpa [appendTrue, restrict, Omega.last] using hLast

/-- The empty word is stable. -/
def empty : X 0 := by
  let w : Word 0 := fun i => False.elim (Nat.not_lt_zero _ i.isLt)
  refine ⟨w, ?_⟩
  intro i hi _
  exact Nat.not_lt_zero i (lt_of_get_eq_true hi)

end X

end Omega
