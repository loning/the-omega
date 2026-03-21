namespace Omega

/-- The standard Fibonacci sequence with `fib 0 = 0` and `fib 1 = 1`. -/
def fib : Nat → Nat
  | 0 => 0
  | 1 => 1
  | n + 2 => fib (n + 1) + fib n

@[simp] theorem fib_zero : fib 0 = 0 := rfl
@[simp] theorem fib_one : fib 1 = 1 := rfl
@[simp] theorem fib_two : fib 2 = 1 := rfl
@[simp] theorem fib_succ_succ (n : Nat) : fib (n + 2) = fib (n + 1) + fib n := rfl

/-- The paper's indexing convention, where `F₁ = F₂ = 1`, as a derived view. -/
def paperFib (k : Nat) : Nat := fib (k + 1)

@[simp] theorem paperFib_zero : paperFib 0 = 1 := rfl
@[simp] theorem paperFib_one : paperFib 1 = 1 := rfl
@[simp] theorem paperFib_two : paperFib 2 = 2 := rfl

theorem paperFib_recurrence (k : Nat) :
    paperFib (k + 2) = paperFib (k + 1) + paperFib k := by
  simpa [paperFib, Nat.add_assoc] using fib_succ_succ (k + 1)

end Omega
