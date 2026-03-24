import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.SpecificLimits.Fibonacci
import Mathlib.Analysis.Asymptotics.SpecificAsymptotics
import Mathlib.NumberTheory.Real.GoldenRatio
import Omega.Folding.ShiftDynamics

open scoped goldenRatio
open Filter Topology

namespace Omega.Entropy

/-! ### Binet corollaries: positivity of Fibonacci casts -/

/-- Nat.fib n is positive for n ≥ 1 (cast to ℝ). -/
theorem coe_fib_pos (n : Nat) (hn : 1 ≤ n) : (0 : ℝ) < (Nat.fib n : ℝ) := by
  exact_mod_cast Nat.fib_pos.mpr (by omega)

/-- |X_m| = F(m+2) is positive (cast to ℝ). -/
theorem stableSyntaxCount_pos (n : Nat) : (0 : ℝ) < (Nat.fib (n + 2) : ℝ) :=
  coe_fib_pos (n + 2) (by omega)

/-! ### Golden ratio properties -/

/-- φ > 1. -/
theorem goldenRatio_gt_one : φ > 1 := Real.one_lt_goldenRatio

/-- log(φ) > 0: the topological entropy is positive. -/
theorem log_goldenRatio_pos : Real.log φ > 0 := Real.log_pos Real.one_lt_goldenRatio

/-- φ < 2. -/
theorem goldenRatio_lt_two : φ < 2 := by
  have : φ ^ 2 = φ + 1 := Real.goldenRatio_sq
  -- φ < 2 ↔ φ² < 2φ (since φ > 0) ↔ φ+1 < 2φ ↔ 1 < φ, which is true
  nlinarith [Real.one_lt_goldenRatio]

/-- |ψ| < 1: the golden conjugate is contractive. -/
theorem abs_goldenConj_lt_one : |ψ| < 1 := by
  rw [abs_lt]
  exact ⟨by linarith [Real.neg_one_lt_goldenConj], by linarith [Real.goldenConj_neg]⟩

/-- ψ is between -1 and 0. -/
theorem goldenConj_bounds : -1 < ψ ∧ ψ < 0 :=
  ⟨Real.neg_one_lt_goldenConj, Real.goldenConj_neg⟩

/-! ### Topological entropy ingredients

The topological entropy of the golden-mean shift is h_top = log φ.
Key ingredients: F(n+1)/F(n) → φ and continuity of log. -/

/-- F(n+1)/F(n) → φ (from mathlib). -/
theorem fib_ratio_tendsto :
    Tendsto (fun n => (Nat.fib (n + 1) : ℝ) / Nat.fib n) atTop (𝓝 φ) :=
  tendsto_fib_succ_div_fib_atTop

/-- log is continuous at φ (since φ > 0). -/
theorem log_continuous_at_phi : ContinuousAt Real.log φ :=
  Real.continuousAt_log (ne_of_gt Real.goldenRatio_pos)

/-- log(F(n+2)/F(n+1)) → log φ as n → ∞.
    This is the key per-step entropy convergence. -/
theorem log_fib_ratio_tendsto :
    Tendsto (fun n => Real.log ((Nat.fib (n + 2) : ℝ) / Nat.fib (n + 1)))
      atTop (𝓝 (Real.log φ)) := by
  -- F(n+2)/F(n+1) = F((n+1)+1)/F(n+1) → φ by tendsto_fib_succ_div_fib_atTop shifted
  have hshift : Tendsto (fun n => (Nat.fib (n + 1 + 1) : ℝ) / Nat.fib (n + 1))
      atTop (𝓝 φ) :=
    tendsto_fib_succ_div_fib_atTop.comp (tendsto_add_atTop_nat 1)
  exact (Real.continuousAt_log (ne_of_gt Real.goldenRatio_pos)).tendsto.comp hshift

/-! ### Topological entropy = log φ (complete proof)

The topological entropy of the golden-mean shift:
  h_top = lim_{n→∞} (1/n) · log |X_n| = lim_{n→∞} (1/n) · log F(n+2) = log φ.

Proof: telescope log F(n+2) = Σ log(F(k+3)/F(k+2)) + log F(2), apply Cesaro to
log_fib_ratio_tendsto, and simplify log F(2) = 0. -/

/-- **Topological entropy of the golden-mean shift equals log φ.**
    This is the central dynamical invariant of the No11-constrained system. -/
theorem topological_entropy_eq_log_phi :
    Tendsto (fun n => Real.log (Nat.fib (n + 2) : ℝ) / (n : ℝ)) atTop (𝓝 (Real.log φ)) := by
  let u : ℕ → ℝ := fun k => Real.log ((Nat.fib (k + 3) : ℝ) / Nat.fib (k + 2))
  have hu : Tendsto u atTop (𝓝 (Real.log φ)) := by
    simpa [u, add_assoc] using log_fib_ratio_tendsto.comp (tendsto_add_atTop_nat 1)
  have hcesaro : Tendsto (fun n : ℕ => (n : ℝ)⁻¹ * (∑ i ∈ Finset.range n, u i))
      atTop (𝓝 (Real.log φ)) :=
    hu.cesaro
  refine Filter.Tendsto.congr' (Filter.Eventually.of_forall fun n => ?_) hcesaro
  calc
    (n : ℝ)⁻¹ * (∑ i ∈ Finset.range n, u i)
        = (n : ℝ)⁻¹ * (∑ i ∈ Finset.range n,
            (Real.log (Nat.fib (i + 3) : ℝ) - Real.log (Nat.fib (i + 2) : ℝ))) := by
              congr 2; ext i; dsimp [u]
              have hnum : (Nat.fib (i + 3) : ℝ) ≠ 0 := by
                exact ne_of_gt (by simpa [add_assoc] using stableSyntaxCount_pos (i + 1))
              have hden : (Nat.fib (i + 2) : ℝ) ≠ 0 := by
                exact ne_of_gt (stableSyntaxCount_pos i)
              rw [Real.log_div hnum hden]
    _ = (n : ℝ)⁻¹ * (Real.log (Nat.fib (n + 2) : ℝ) - Real.log (Nat.fib 2 : ℝ)) := by
          congr 1
          simpa [add_assoc] using
            (Finset.sum_range_sub (fun i => Real.log (Nat.fib (i + 2) : ℝ)) n)
    _ = (n : ℝ)⁻¹ * Real.log (Nat.fib (n + 2) : ℝ) := by
          norm_num [Nat.fib]
    _ = Real.log (Nat.fib (n + 2) : ℝ) / (n : ℝ) := by
          rw [div_eq_mul_inv, mul_comm]

end Omega.Entropy
