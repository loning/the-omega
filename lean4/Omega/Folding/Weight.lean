import Omega.Folding.StableSyntax

namespace Omega

/-- The Fibonacci-weighted value used by the paper's folding map. -/
def weight : {m : Nat} → Word m → Nat
  | 0, _ => 0
  | m + 1, w =>
      weight (truncate w) + if w ⟨m, Nat.lt_succ_self m⟩ then Nat.fib (m + 2) else 0

@[simp] theorem weight_empty : weight (m := 0) (fun i => False.elim (Nat.not_lt_zero _ i.isLt)) = 0 :=
  rfl

@[simp] theorem weight_snoc (w : Word m) (b : Bool) :
    weight (snoc w b) = weight w + if b then Nat.fib (m + 2) else 0 := by
  simp [weight, truncate_snoc, snoc_last]

@[simp] theorem weight_appendFalse (x : X m) :
    weight (X.appendFalse x).1 = weight x.1 := by
  simp [X.appendFalse, weight_snoc]

@[simp] theorem weight_appendTrue (x : X m) (hLast : get x.1 (m - 1) = false) :
    weight (X.appendTrue x hLast).1 = weight x.1 + Nat.fib (m + 2) := by
  simp [X.appendTrue, weight_snoc]


/-- Weight of a stable word ending in false equals weight of its restriction. -/
theorem weight_of_lastFalse {w : Word (m + 1)} (h : w ⟨m, Nat.lt_succ_self m⟩ = false) :
    weight w = weight (truncate w) := by
  simp [weight, h]

/-- Weight of a stable word ending in true equals weight of restriction + F(m+2). -/
theorem weight_of_lastTrue {w : Word (m + 1)} (h : w ⟨m, Nat.lt_succ_self m⟩ = true) :
    weight w = weight (truncate w) + Nat.fib (m + 2) := by
  simp [weight, h]

/-- Weight is monotone: adding a true bit increases weight. -/
theorem weight_pos_of_bit_true {w : Word (m + 1)} (h : w ⟨m, Nat.lt_succ_self m⟩ = true) :
    0 < weight w := by
  rw [weight_of_lastTrue h]
  exact Nat.lt_of_lt_of_le (fib_succ_pos (m + 1)) (Nat.le_add_left _ _)

/-- Weight of a length-1 word is 0 or F(2) = 1. -/
theorem weight_word_one (w : Word 1) :
    weight w = if w ⟨0, Nat.zero_lt_one⟩ then 1 else 0 := by
  simp [weight]


end Omega
