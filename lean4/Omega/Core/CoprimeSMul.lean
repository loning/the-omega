import Mathlib.GroupTheory.GroupAction.Basic
import Mathlib.Data.Int.GCD

/-! ### Coprime scalar annihilation

Bézout's identity in additive abelian groups: if two coprime integers both
annihilate an element, the element must be zero. -/

namespace Omega

/-- Coprime annihilators in an additive commutative group force zero:
    if q₁ • a = 0 and q₂ • a = 0 and gcd(q₁,q₂) = 1, then a = 0.
    Bézout identity applied in an abelian group.
    thm:pom-anom-coprime-two-point-test -/
theorem coprime_smul_eq_zero_of_both {G : Type*} [AddCommGroup G]
    (a : G) (q₁ q₂ : ℤ)
    (h1 : q₁ • a = 0) (h2 : q₂ • a = 0)
    (hcoprime : Int.gcd q₁ q₂ = 1) :
    a = 0 := by
  -- Obtain Bézout coefficients: ∃ u v, u * q₁ + v * q₂ = gcd q₁ q₂
  have hbez := Int.gcd_eq_gcd_ab q₁ q₂
  -- gcd q₁ q₂ = 1 (as Int)
  have hone : (Int.gcd q₁ q₂ : ℤ) = 1 := by exact_mod_cast hcoprime
  rw [hone] at hbez
  -- a = 1 • a = (u*q₁ + v*q₂) • a = u•(q₁•a) + v•(q₂•a) = 0
  have key : (1 : ℤ) • a = (0 : G) := by
    conv_lhs => rw [show (1 : ℤ) = q₁ * Int.gcdA q₁ q₂ + q₂ * Int.gcdB q₁ q₂ from hbez]
    rw [add_smul, mul_smul, mul_smul, smul_comm q₁, smul_comm q₂, h1, h2,
        smul_zero, smul_zero, add_zero]
  rwa [one_smul] at key

end Omega
