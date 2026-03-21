import Omega.Folding.StableSyntax

namespace Omega

/-- The Fibonacci-weighted value used by the paper's folding map. -/
def weight : {m : Nat} → Word m → Nat
  | 0, _ => 0
  | m + 1, w =>
      weight (truncate w) + if w ⟨m, Nat.lt_succ_self m⟩ then paperFib (m + 1) else 0

@[simp] theorem weight_empty : weight (m := 0) (fun i => False.elim (Nat.not_lt_zero _ i.isLt)) = 0 :=
  rfl

@[simp] theorem weight_snoc (w : Word m) (b : Bool) :
    weight (snoc w b) = weight w + if b then paperFib (m + 1) else 0 := by
  simp [weight, truncate_snoc, snoc_last]

@[simp] theorem weight_appendFalse (x : X m) :
    weight (X.appendFalse x).1 = weight x.1 := by
  simp [X.appendFalse, weight_snoc]

end Omega
