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

-- ══════════════════════════════════════════════════════════════
-- Fibonacci parity / Pisano period mod 2
-- ══════════════════════════════════════════════════════════════

/-- 3|n → 2|F_n. -/
theorem fib_even_of_three_dvd (n : Nat) (h : 3 ∣ n) : 2 ∣ Nat.fib n := by
  exact dvd_trans (show (2 : Nat) ∣ Nat.fib 3 from by decide) (Nat.fib_dvd 3 n h)

/-- 2|F_n → 3|n. -/
theorem three_dvd_of_fib_even (n : Nat) (h : 2 ∣ Nat.fib n) : 3 ∣ n := by
  induction n using Nat.strongRecOn with
  | _ n ih =>
    match n with
    | 0 => exact dvd_zero 3
    | 1 => exfalso; simp [Nat.fib] at h
    | 2 => exfalso; simp [Nat.fib] at h
    | n + 3 =>
      -- F(n+3) = F(n+2) + F(n+1). If F(n+3) even, then F(n+2) and F(n+1) have same parity.
      have hfib : Nat.fib (n + 3) = Nat.fib (n + 1) + Nat.fib (n + 2) := Nat.fib_add_two
      -- If both even: 3|(n+1) and 3|(n+2), impossible (consecutive)
      -- If both odd: F(n) = F(n+2) - F(n+1) is even → 3|n by IH → 3|(n+3)
      by_cases h1 : 2 ∣ Nat.fib (n + 1)
      · -- F(n+1) even → 3|(n+1). Also F(n+2) even (same parity) → 3|(n+2). Contradiction.
        have h2 : 2 ∣ Nat.fib (n + 2) := by rwa [hfib, Nat.dvd_add_right h1] at h
        have := ih (n + 1) (by omega) h1
        have := ih (n + 2) (by omega) h2
        omega
      · -- F(n+1) odd → F(n+2) odd (same parity) → F(n) = F(n+2)-F(n+1) even
        have h2 : ¬ (2 ∣ Nat.fib (n + 2)) := by
          intro h2; exact h1 (by rwa [hfib, Nat.dvd_add_left h2] at h)
        -- F(n) = F(n+2) - F(n+1)
        have hfn : Nat.fib n = Nat.fib (n + 2) - Nat.fib (n + 1) := by
          have := Nat.fib_add_two (n := n); omega
        -- F(n+1) odd and F(n+2) odd → F(n+1) % 2 = 1, F(n+2) % 2 = 1
        -- F(n) = F(n+2) - F(n+1), both odd → difference even
        have heven : 2 ∣ Nat.fib n := by
          rw [hfn]
          -- Both F(n+1) and F(n+2) are odd, so their difference is even
          have hr1 : Nat.fib (n + 1) % 2 = 1 := by omega
          have hr2 : Nat.fib (n + 2) % 2 = 1 := by omega
          omega
        have := ih n (by omega) heven
        omega

/-- F_n is even iff 3|n. -/
theorem fib_even_iff_three_dvd (n : Nat) : 2 ∣ Nat.fib n ↔ 3 ∣ n :=
  ⟨three_dvd_of_fib_even n, fib_even_of_three_dvd n⟩

/-- F_n % 2 = F_{n%3} % 2. -/
theorem fib_mod_two_period (n : Nat) :
    Nat.fib n % 2 = Nat.fib (n % 3) % 2 := by
  by_cases h : 3 ∣ n
  · -- 3|n → F_n even → F_n % 2 = 0. Also n%3=0 → F_0=0 → F_0 % 2 = 0
    have heven := (fib_even_iff_three_dvd n).mpr h
    have hmod : n % 3 = 0 := Nat.mod_eq_zero_of_dvd h
    rw [hmod]; simp only [Nat.fib_zero, Nat.zero_mod]; omega
  · -- 3∤n → F_n odd → F_n % 2 = 1. n%3 ∈ {1,2} → F_{n%3} ∈ {F_1, F_2} = {1,1} → % 2 = 1
    have hodd := mt (three_dvd_of_fib_even n) h
    have hmod : n % 3 = 1 ∨ n % 3 = 2 := by omega
    have : Nat.fib n % 2 = 1 := by omega
    rcases hmod with hm | hm <;> rw [hm] <;> simp only [Nat.fib_one, Nat.fib_two] <;> omega

/-- F_n is odd iff 3∤n. -/
theorem fib_odd_iff_not_three_dvd (n : Nat) : ¬ (2 ∣ Nat.fib n) ↔ ¬ (3 ∣ n) := by
  rw [fib_even_iff_three_dvd]

-- ══════════════════════════════════════════════════════════════
-- Fibonacci summation identities
-- ══════════════════════════════════════════════════════════════

/-- Σ_{k<n} F_{k+1} = F_{n+2} - 1. -/
theorem fib_partial_sum (n : Nat) :
    ∑ k ∈ Finset.range n, Nat.fib (k + 1) = Nat.fib (n + 2) - 1 := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [Finset.sum_range_succ, ih]
    have h1 : Nat.fib (n + 1 + 1) = Nat.fib (n + 2) := rfl
    have h2 : Nat.fib (n + 1 + 2) = Nat.fib (n + 3) := rfl
    rw [h1, h2]
    have := Nat.fib_add_two (n := n + 1)
    rw [show n + 1 + 2 = n + 3 from rfl, show n + 1 + 1 = n + 2 from rfl] at this
    have := fib_succ_pos n; have := fib_succ_pos (n + 1)
    omega

/-- Σ_{k<n} F_{k+2} = F_{n+3} - 2. -/
theorem fib_partial_sum_from_two (n : Nat) :
    ∑ k ∈ Finset.range n, Nat.fib (k + 2) = Nat.fib (n + 3) - 2 := by
  induction n with
  | zero => simp [Nat.fib]
  | succ n ih =>
    rw [Finset.sum_range_succ, ih]
    have h1 : Nat.fib (n + 1 + 2) = Nat.fib (n + 3) := rfl
    have h2 : Nat.fib (n + 1 + 3) = Nat.fib (n + 4) := rfl
    rw [h1, h2]
    have := Nat.fib_add_two (n := n + 2)
    rw [show n + 2 + 2 = n + 4 from rfl, show n + 2 + 1 = n + 3 from rfl] at this
    have : 0 < Nat.fib (n + 2) := fib_succ_pos (n + 1)
    have : 0 < Nat.fib (n + 3) := fib_succ_pos (n + 2)
    have hfib3 := Nat.fib_add_two (n := n + 1)
    rw [show n + 1 + 2 = n + 3 from rfl, show n + 1 + 1 = n + 2 from rfl] at hfib3
    have : 0 < Nat.fib (n + 1) := fib_succ_pos n
    have : 2 ≤ Nat.fib (n + 4) := by omega
    omega

/-- Σ_{k<n} F_{k+1}² = F_n · F_{n+1}. -/
theorem fib_sq_sum (n : Nat) :
    ∑ k ∈ Finset.range n, Nat.fib (k + 1) ^ 2 = Nat.fib n * Nat.fib (n + 1) := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [Finset.sum_range_succ, ih]
    have hfib := Nat.fib_add_two (n := n)
    -- F_n*F_{n+1} + F_{n+1}^2 = F_{n+1}*(F_n+F_{n+1}) = F_{n+1}*F_{n+2}
    rw [show Nat.fib (n + 1) ^ 2 = Nat.fib (n + 1) * Nat.fib (n + 1) from sq _, hfib]
    ring

/-- Σ_{k<n} F_{2(k+1)} = F_{2n+1} - 1. -/
theorem fib_even_sum (n : Nat) :
    ∑ k ∈ Finset.range n, Nat.fib (2 * (k + 1)) = Nat.fib (2 * n + 1) - 1 := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [Finset.sum_range_succ, ih]
    -- Normalize: 2*(n+1) = 2*n+2, 2*(n+1)+1 = 2*n+3, 2*(n+1+1) = 2*n+4
    -- But these may not match syntactically. Use conv/show.
    -- Goal: F(2n+1)-1 + F(2*(n+1)) = F(2*(n+1)+1)-1
    -- = F(2n+1)-1 + F(2n+2) = F(2n+3)-1
    -- F(2n+3) = F(2n+1) + F(2n+2)
    rw [show 2 * (n + 1) = 2 * n + 2 from by ring,
        show 2 * n + 2 + 1 = 2 * n + 3 from by ring]
    have := Nat.fib_add_two (n := 2 * n + 1)
    rw [show 2 * n + 1 + 2 = 2 * n + 3 from rfl, show 2 * n + 1 + 1 = 2 * n + 2 from rfl] at this
    have : 0 < Nat.fib (2 * n + 1) := fib_succ_pos (2 * n)
    have : 0 < Nat.fib (2 * n + 2) := fib_succ_pos (2 * n + 1)
    omega

/-- Σ_{k<n} F_{2k+1} = F_{2n}. -/
theorem fib_odd_sum (n : Nat) :
    ∑ k ∈ Finset.range n, Nat.fib (2 * k + 1) = Nat.fib (2 * n) := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [Finset.sum_range_succ, ih]
    have h1 : 2 * (n + 1) = 2 * n + 2 := by ring
    rw [h1]
    have := Nat.fib_add_two (n := 2 * n)
    rw [show 2 * n + 2 = 2 * n + 2 from rfl] at this
    omega

-- ══════════════════════════════════════════════════════════════
-- Advanced Fibonacci identities
-- ══════════════════════════════════════════════════════════════

/-- 3 ∣ F(n) ↔ 4 ∣ n. -/
theorem fib_div_three_iff (n : Nat) : 3 ∣ Nat.fib n ↔ 4 ∣ n := by
  constructor
  · -- 3|F(n) → 4|n: by strong induction + Pisano period
    intro h
    induction n using Nat.strongRecOn with
    | _ n ih =>
      match n with
      | 0 => exact dvd_zero 4
      | 1 => simp [Nat.fib] at h
      | 2 => simp [Nat.fib] at h
      | 3 => simp [Nat.fib] at h
      | n + 4 =>
        -- F(n+4) = F(n+3)+F(n+2) = (F(n+2)+F(n+1))+F(n+2) = 2F(n+2)+F(n+1)
        -- F(n+2) = F(n+1)+F(n)
        -- F(n+4) = 2(F(n+1)+F(n))+F(n+1) = 3F(n+1)+2F(n)
        -- If 3|F(n+4): 3|3F(n+1)+2F(n) → 3|2F(n) → 3|F(n) (since gcd(3,2)=1)
        have hfib2 := Nat.fib_add_two (n := n)
        have hfib3 := Nat.fib_add_two (n := n + 1)
        have hfib4 := Nat.fib_add_two (n := n + 2)
        rw [show n + 1 + 2 = n + 3 from rfl, show n + 1 + 1 = n + 2 from rfl] at hfib3
        rw [show n + 2 + 2 = n + 4 from rfl, show n + 2 + 1 = n + 3 from rfl] at hfib4
        have h3fn : 3 ∣ Nat.fib n := by
          have : Nat.fib (n + 4) = 3 * Nat.fib (n + 1) + 2 * Nat.fib n := by
            rw [hfib4, hfib3, hfib2]; ring
          rw [this] at h
          have h2fn : 3 ∣ 2 * Nat.fib n := by omega
          have : 3 ∣ Nat.fib n * 2 := by rwa [Nat.mul_comm] at h2fn
          exact (Nat.Coprime.dvd_of_dvd_mul_right (by decide : Nat.Coprime 3 2) this)
        have := ih n (by omega) h3fn
        omega
  · -- 4|n → 3|F(n): F_4=3 divides F_{4k}
    intro ⟨k, hk⟩; rw [hk]
    exact dvd_trans (show (3 : Nat) ∣ Nat.fib 4 from by decide) (Nat.fib_dvd 4 (4 * k) ⟨k, rfl⟩)

/-- F(n+1) ≤ 2·F(n) for n ≥ 1. -/
theorem fib_succ_le_double (n : Nat) (hn : 1 ≤ n) :
    Nat.fib (n + 1) ≤ 2 * Nat.fib n := by
  -- F(n+1) = F(n-1) + F(n) ≤ F(n) + F(n) = 2F(n)
  have hrec := Nat.fib_add_two (n := n - 1)
  rw [show n - 1 + 2 = n + 1 from by omega, show n - 1 + 1 = n from by omega] at hrec
  have hmono : Nat.fib (n - 1) ≤ Nat.fib n := Nat.fib_mono (by omega)
  omega

end Omega
