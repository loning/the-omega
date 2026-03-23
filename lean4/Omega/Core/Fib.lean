import Mathlib.Data.Nat.Fib.Basic

/-! ### Convenience lemmas for `Nat.fib`

The project uses `Nat.fib` directly with the standard convention F₀ = 0, F₁ = 1.
The previous `paperFib k` indirection layer has been removed: all references now
use `Nat.fib (k + 1)` directly.

Mathlib's `Nat.fib_add_two` has the *small* term first:
  `Nat.fib (n + 2) = Nat.fib n + Nat.fib (n + 1)`.
Many project proofs need the *large* term first, so we provide `fib_succ_succ`. -/

namespace Omega

-- ══════════════════════════════════════════════════════════════════
-- New canonical lemmas (Nat.fib based, in Omega namespace)
-- ══════════════════════════════════════════════════════════════════

/-- Fibonacci recurrence with large term first: F(n+2) = F(n+1) + F(n). -/
theorem fib_succ_succ' (n : Nat) : Nat.fib (n + 2) = Nat.fib (n + 1) + Nat.fib n := by
  have := Nat.fib_add_two (n := n); omega

/-- F(n+1) > 0 for all n. -/
theorem fib_succ_pos (n : Nat) : 0 < Nat.fib (n + 1) :=
  Nat.fib_pos.mpr (by omega)

/-- F(n+1) ≥ 1 for all n. -/
theorem one_le_fib_succ (n : Nat) : 1 ≤ Nat.fib (n + 1) :=
  fib_succ_pos n

/-- Fibonacci recurrence, additive form: F(m+2) + F(m+1) = F(m+3). -/
theorem fib_add_succ (m : Nat) : Nat.fib (m + 2) + Nat.fib (m + 1) = Nat.fib (m + 3) := by
  have h := fib_succ_succ' (m + 1)
  rw [show m + 1 + 2 = m + 3 from by omega, show m + 1 + 1 = m + 2 from by omega] at h
  omega

/-- Fibonacci subtraction: F(m+3) - F(m+2) = F(m+1). -/
theorem fib_sub_succ (m : Nat) : Nat.fib (m + 3) - Nat.fib (m + 2) = Nat.fib (m + 1) := by
  have h := fib_succ_succ' (m + 1)
  rw [show m + 1 + 2 = m + 3 from by omega, show m + 1 + 1 = m + 2 from by omega] at h
  omega

/-- Carry modular identity: (F(m+2) + F(m+1)) % F(m+3) = 0. -/
theorem fib_mod_sum' (m : Nat) :
    (Nat.fib (m + 2) + Nat.fib (m + 1)) % Nat.fib (m + 3) = 0 := by
  rw [fib_add_succ, Nat.mod_self]

/-- Strict monotonicity: F(m+2) < F(m+3). -/
theorem fib_lt_fib_succ (m : Nat) : Nat.fib (m + 2) < Nat.fib (m + 3) := by
  have h := fib_succ_succ' (m + 1)
  rw [show m + 1 + 2 = m + 3 from by omega, show m + 1 + 1 = m + 2 from by omega] at h
  have := fib_succ_pos m; omega

/-- Resolution-crossing identity: F(m+4) mod F(m+3) = F(m+2). -/
theorem fib_succ_mod' (m : Nat) :
    Nat.fib (m + 4) % Nat.fib (m + 3) = Nat.fib (m + 2) := by
  have : Nat.fib (m + 4) = Nat.fib (m + 3) + Nat.fib (m + 2) := by
    rw [show m + 4 = (m + 2) + 2 from by omega]; exact fib_succ_succ' (m + 2)
  rw [this, Nat.add_comm, Nat.add_mod_right, Nat.mod_eq_of_lt (fib_lt_fib_succ m)]

/-- F(m+2) > 1 for m ≥ 1. -/
theorem fib_gt_one_of_ge_two (hm : 1 ≤ m) : 1 < Nat.fib (m + 2) := by
  calc 1 < 2 := by omega
    _ = Nat.fib 3 := by native_decide
    _ ≤ Nat.fib (m + 2) := Nat.fib_mono (by omega)

/-- Upper bound: F(m+2) ≤ 2^(m+1) for all m. -/
theorem fib_le_pow_two : ∀ m : Nat, Nat.fib (m + 2) ≤ 2 ^ (m + 1)
  | 0 => by simp
  | 1 => by native_decide
  | m + 2 => by
    calc Nat.fib (m + 2 + 2)
        = Nat.fib (m + 2 + 1) + Nat.fib (m + 2) := fib_succ_succ' (m + 2)
      _ ≤ 2 ^ (m + 1 + 1) + 2 ^ (m + 1) :=
          Nat.add_le_add (fib_le_pow_two (m + 1)) (fib_le_pow_two m)
      _ ≤ 2 ^ (m + 1 + 1) + 2 ^ (m + 1 + 1) :=
          Nat.add_le_add_left (Nat.pow_le_pow_right (by omega) (by omega)) _
      _ = 2 ^ (m + 2 + 1) := by ring

/-- gcd(F_m, F_n) = F_{gcd(m,n)} (strong divisibility). -/
theorem fib_gcd (m n : Nat) : Nat.gcd (Nat.fib m) (Nat.fib n) = Nat.fib (Nat.gcd m n) :=
  (Nat.fib_gcd m n).symm

/-- F_m and F_{m+1} are coprime. -/
theorem fib_coprime_succ (m : Nat) : Nat.Coprime (Nat.fib m) (Nat.fib (m + 1)) :=
  Nat.fib_coprime_fib_succ m

/-- F_m divides F_{k*m}. -/
theorem fib_dvd_mul (m k : Nat) : Nat.fib m ∣ Nat.fib (k * m) :=
  Nat.fib_dvd m (k * m) ⟨k, (Nat.mul_comm m k).symm⟩

/-- F_{2n} = F_n · (2·F_{n+1} - F_n). -/
theorem fib_double (n : Nat) :
    Nat.fib (2 * n) = Nat.fib n * (2 * Nat.fib (n + 1) - Nat.fib n) :=
  Nat.fib_two_mul n

/-- F_{2n+1} = F_{n+1}² + F_n². -/
theorem fib_double_plus_one (n : Nat) :
    Nat.fib (2 * n + 1) = Nat.fib (n + 1) ^ 2 + Nat.fib n ^ 2 :=
  Nat.fib_two_mul_add_one n

/-- F_n² + F_{n+1}² = F_{2n+1}. -/
theorem fib_sq_add_sq (n : Nat) :
    Nat.fib n ^ 2 + Nat.fib (n + 1) ^ 2 = Nat.fib (2 * n + 1) := by
  rw [Nat.add_comm]; exact (Nat.fib_two_mul_add_one n).symm

end Omega
