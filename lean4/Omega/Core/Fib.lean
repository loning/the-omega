import Mathlib.Data.Nat.Fib.Basic

namespace Omega

/-- The project's canonical Fibonacci sequence is `Nat.fib`. -/
abbrev fib : Nat → Nat := Nat.fib

@[simp] theorem fib_zero : fib 0 = 0 := Nat.fib_zero
@[simp] theorem fib_one : fib 1 = 1 := Nat.fib_one
@[simp] theorem fib_two : fib 2 = 1 := Nat.fib_two

@[simp] theorem fib_succ_succ (n : Nat) : fib (n + 2) = fib (n + 1) + fib n := by
  simpa [add_comm] using (Nat.fib_add_two (n := n))

/-- The paper's indexing convention, where `F₁ = F₂ = 1`, as a derived view. -/
def paperFib (k : Nat) : Nat := fib (k + 1)

@[simp] theorem paperFib_zero : paperFib 0 = 1 := rfl
@[simp] theorem paperFib_one : paperFib 1 = 1 := rfl
@[simp] theorem paperFib_two : paperFib 2 = 2 := rfl

set_option linter.unnecessarySimpa false in
theorem paperFib_recurrence (k : Nat) :
    paperFib (k + 2) = paperFib (k + 1) + paperFib k := by
  unfold paperFib
  have hIndex : (k + 2) + 1 = (k + 1) + 2 := by
    simpa [Nat.add_assoc] using (Nat.add_right_comm k 2 1)
  rw [hIndex]
  exact fib_succ_succ (k + 1)

theorem paperFib_pos (n : Nat) : 0 < paperFib n := by
  simp [paperFib, Nat.fib_pos]

theorem paperFib_mono {m n : Nat} (h : m ≤ n) : paperFib m ≤ paperFib n :=
  Nat.fib_mono (Nat.succ_le_succ h)

theorem paperFib_le_succ (k : Nat) : paperFib k ≤ paperFib (k + 1) :=
  paperFib_mono (Nat.le_succ k)

theorem paperFib_le_add_right (k l : Nat) : paperFib k ≤ paperFib (k + l) :=
  paperFib_mono (Nat.le_add_right k l)

/-- paperFib(m+1) + paperFib(m) = paperFib(m+2) (Fibonacci recurrence, symmetric form). -/
theorem paperFib_add (m : Nat) : paperFib (m + 1) + paperFib m = paperFib (m + 2) := by
  have := paperFib_recurrence m; omega

/-- paperFib(m+2) - paperFib(m+1) = paperFib(m) (Fibonacci subtraction). -/
theorem paperFib_sub (m : Nat) : paperFib (m + 2) - paperFib (m + 1) = paperFib m := by
  have := paperFib_recurrence m; omega

/-- F_{m+1} + F_m ≡ 0 (mod F_{m+2}) (carry modular identity). -/
theorem paperFib_mod_sum (m : Nat) :
    (paperFib (m + 1) + paperFib m) % paperFib (m + 2) = 0 := by
  rw [paperFib_add, Nat.mod_self]

/-- F_{m+1} < F_{m+2} for all m. -/
theorem paperFib_lt_succ (m : Nat) : paperFib (m + 1) < paperFib (m + 2) := by
  have := paperFib_recurrence m; have := paperFib_pos m; omega

/-- F_{m+3} mod F_{m+2} = F_{m+1} (resolution-crossing identity). -/
theorem paperFib_succ_mod (m : Nat) :
    paperFib (m + 3) % paperFib (m + 2) = paperFib (m + 1) := by
  have : paperFib (m + 3) = paperFib (m + 2) + paperFib (m + 1) := by
    rw [show m + 3 = (m + 1) + 2 from by omega]; exact paperFib_recurrence (m + 1)
  rw [this, Nat.add_comm, Nat.add_mod_right, Nat.mod_eq_of_lt (paperFib_lt_succ m)]

end Omega
