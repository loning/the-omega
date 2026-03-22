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

end Omega
