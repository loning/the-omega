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

end Omega
