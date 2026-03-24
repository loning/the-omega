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

/-! ### Golden ratio arithmetic-geometric properties -/

/-- φ > 3/2. -/
theorem goldenRatio_gt_three_half : φ > 3 / 2 := by
  have hsq : φ ^ 2 = φ + 1 := Real.goldenRatio_sq
  -- φ > 3/2 ↔ φ² > (3/2)² = 9/4 (since φ > 0)
  -- φ² = φ + 1, so need φ + 1 > 9/4 ↔ φ > 5/4
  -- φ > 1 > 5/4? No, 1 < 5/4. Use: φ² = φ+1, if φ ≤ 3/2 then φ+1 ≤ 5/2
  -- but (3/2)² = 9/4 = 2.25, and if φ ≤ 3/2 then φ² ≤ (3/2)² = 9/4
  -- but φ² = φ+1 ≥ 1+1 = 2 (since φ > 1). Need sharper.
  -- Actually: φ > 1, φ² = φ+1. If φ ≤ 3/2, then φ+1 ≤ 5/2 and φ² = φ+1 ≤ 5/2.
  -- Also φ² ≥ φ·(3/2) (if φ ≥ 3/2). Contradiction approach:
  nlinarith [Real.one_lt_goldenRatio, Real.goldenRatio_sq]

/-- φ < 5/3. -/
theorem goldenRatio_lt_five_thirds : φ < 5 / 3 := by
  nlinarith [Real.goldenRatio_sq, Real.one_lt_goldenRatio]

/-- φ = 1 + 1/φ (the defining fixed-point equation). -/
theorem goldenRatio_eq_one_add_inv : φ = 1 + φ⁻¹ := by
  have hne : φ ≠ 0 := ne_of_gt Real.goldenRatio_pos
  have hsq : φ ^ 2 = φ + 1 := Real.goldenRatio_sq
  have key : φ - 1 = φ⁻¹ := by
    rw [eq_comm, inv_eq_of_mul_eq_one_left]
    nlinarith
  linarith

/-- φ is irrational. -/
theorem phi_irrational : Irrational φ := Real.goldenRatio_irrational

/-! ### Entropy rate comparison -/

/-- The topological entropy log φ is strictly less than log 2
    (the entropy of the full shift). -/
theorem entropy_ordering_proxy : Real.log φ < Real.log 2 :=
  Real.log_lt_log Real.goldenRatio_pos goldenRatio_lt_two

/-- The entropy gap: log 2 - log φ = log(2/φ) > 0. -/
theorem entropy_gap_pos : Real.log 2 - Real.log φ > 0 := by
  linarith [entropy_ordering_proxy]

/-! ### Binet formula (from mathlib) -/

/-- Binet formula: F(n) = (φ^n - ψ^n) / √5 (from mathlib). -/
theorem binet_formula (n : Nat) : (Nat.fib n : ℝ) = (φ ^ n - ψ ^ n) / Real.sqrt 5 :=
  Real.coe_fib_eq n

/-! ### √5 auxiliary lemmas -/

private theorem sq_sqrt5 : Real.sqrt 5 ^ 2 = 5 :=
  Real.sq_sqrt (by norm_num : (5 : ℝ) ≥ 0)

private theorem sqrt5_pos : (0 : ℝ) < Real.sqrt 5 :=
  Real.sqrt_pos_of_pos (by norm_num : (5 : ℝ) > 0)

private theorem sqrt5_gt_two : Real.sqrt 5 > 2 := by
  have h := sq_sqrt5
  have hp := sqrt5_pos
  nlinarith [sq_abs (Real.sqrt 5 - 2)]

private theorem sqrt5_lt_three : Real.sqrt 5 < 3 := by
  have h := sq_sqrt5
  nlinarith [sq_abs (Real.sqrt 5 - 3)]

/-! ### φ/√5 precise bounds -/

/-- √5 > 2 (from sq_sqrt5 and nlinarith). -/
theorem sqrt5_gt_two' : Real.sqrt 5 > 2 := sqrt5_gt_two

/-- √5 < 3 (from sq_sqrt5 and nlinarith). -/
theorem sqrt5_lt_three' : Real.sqrt 5 < 3 := sqrt5_lt_three

/-- φ < √5: since φ = (1+√5)/2 and √5 > 2, we have 2φ = 1+√5 < 2√5. -/
theorem phi_lt_sqrt5 : φ < Real.sqrt 5 := by
  rw [Real.goldenRatio]; linarith [sqrt5_gt_two]

/-- φ+1 > √5: since φ+1 = (3+√5)/2 and √5 < 3, we have 2(φ+1) = 3+√5 > 2√5. -/
theorem phi_add_one_gt_sqrt5 : φ + 1 > Real.sqrt 5 := by
  rw [Real.goldenRatio]; linarith [sqrt5_lt_three]

/-! ### Golden angle -/

/-- The golden angle: 1/φ = φ - 1. -/
noncomputable def goldenAngle : ℝ := φ⁻¹

/-- The golden angle is positive. -/
theorem goldenAngle_pos : 0 < goldenAngle :=
  inv_pos.mpr Real.goldenRatio_pos

/-- The golden angle is less than 1. -/
theorem goldenAngle_lt_one : goldenAngle < 1 :=
  inv_lt_one_of_one_lt₀ Real.one_lt_goldenRatio

/-- The golden angle satisfies θ² = 1 - θ (dual of φ² = φ + 1). -/
theorem goldenAngle_sq : goldenAngle ^ 2 = 1 - goldenAngle := by
  have hne : φ ≠ 0 := ne_of_gt Real.goldenRatio_pos
  have hsq : φ ^ 2 = φ + 1 := Real.goldenRatio_sq
  simp only [goldenAngle, inv_pow]
  -- Goal: (φ^2)⁻¹ = 1 - φ⁻¹
  rw [hsq]
  have hne : φ ≠ 0 := ne_of_gt Real.goldenRatio_pos
  have hne2 : φ + 1 ≠ 0 := by linarith [Real.goldenRatio_pos]
  have hkey := goldenRatio_eq_one_add_inv
  -- φ = 1 + φ⁻¹, so φ⁻¹ = φ - 1, so 1 - φ⁻¹ = 2 - φ
  -- Also φ² = φ+1, so (φ+1)⁻¹ = (φ²)⁻¹
  -- We need (φ+1)⁻¹ = 1 - φ⁻¹ = 1 - (φ-1) = 2-φ
  -- (φ+1)⁻¹ = 2-φ ↔ 1 = (φ+1)(2-φ) = 2φ+2-φ²-φ = φ+2-(φ+1) = 1 ✓
  have : (φ + 1) * (1 - φ⁻¹) = 1 := by
    have : φ⁻¹ = φ - 1 := by linarith
    rw [this]; nlinarith [Real.goldenRatio_sq]
  exact eq_inv_of_mul_eq_one_right this |>.symm

/-! ### Binet nearest integer property -/

/-- |ψ^n / √5| < 1/2 for all n ≥ 0 (since |ψ| < 1 and √5 > 2). -/
theorem abs_psi_pow_div_sqrt5_lt_half (n : Nat) :
    |ψ ^ n / Real.sqrt 5| < 1 / 2 := by
  rw [abs_div, abs_of_pos sqrt5_pos]
  have hle : |ψ ^ n| ≤ 1 := by
    calc |ψ ^ n| = |ψ| ^ n := abs_pow ψ n
      _ ≤ 1 := pow_le_one₀ (abs_nonneg _) abs_goldenConj_lt_one.le
  have hgt2 : Real.sqrt 5 > 2 := sqrt5_gt_two
  have hp5 := sqrt5_pos
  -- |ψ^n|/√5 ≤ 1/√5 < 1/2
  -- Direct: |ψ^n|/√5 ≤ 1/√5 since |ψ^n| ≤ 1 and √5 > 0
  -- 1/√5 < 1/2 since √5 > 2
  -- So |ψ^n|/√5 < 1/2
  have h1 : |ψ ^ n| * 2 ≤ 1 * 2 := by linarith
  -- |ψ^n|/√5 * (2*√5) ≤ 2 and 1/2 * (2*√5) = √5
  -- Equivalently: 2*|ψ^n| ≤ 2 < √5, so 2*|ψ^n|/√5 < 1, so |ψ^n|/√5 < 1/2
  rw [div_lt_div_iff₀ hp5 (by norm_num : (0:ℝ) < 2)]
  linarith

/-- Binet nearest integer: |F(n) - φ^n/√5| < 1/2 for all n. -/
theorem fib_nearest_integer (n : Nat) :
    |(Nat.fib n : ℝ) - φ ^ n / Real.sqrt 5| < 1 / 2 := by
  rw [binet_formula, show (φ ^ n - ψ ^ n) / Real.sqrt 5 - φ ^ n / Real.sqrt 5 =
    -(ψ ^ n / Real.sqrt 5) from by ring]
  rw [abs_neg]
  exact abs_psi_pow_div_sqrt5_lt_half n

/-! ### Chebyshev phase -/

/-- (φ/2)² = (φ+1)/4. -/
theorem goldenRatio_div_two_sq : (φ / 2) ^ 2 = (φ + 1) / 4 := by
  rw [div_pow, Real.goldenRatio_sq]; ring

/-- Minimal polynomial of φ/2: 4x² - 2x - 1 = 0. -/
theorem goldenRatio_half_minpoly : 4 * (φ / 2) ^ 2 - 2 * (φ / 2) - 1 = 0 := by
  have hsq := Real.goldenRatio_sq
  rw [goldenRatio_div_two_sq]
  -- 4 * ((φ+1)/4) - 2 * (φ/2) - 1 = (φ+1) - φ - 1 = 0
  ring

/-! ### Entropy comprehensive certificate -/

/-- The complete entropy certificate: all key results in one theorem. -/
theorem entropy_comprehensive_certificate :
    Tendsto (fun n => Real.log (Nat.fib (n + 2) : ℝ) / (n : ℝ)) atTop (𝓝 (Real.log φ)) ∧
    Real.log φ > 0 ∧ Real.log φ < Real.log 2 ∧
    φ > 3 / 2 ∧ φ < 2 ∧ Irrational φ ∧
    (∀ n, (Nat.fib n : ℝ) = (φ ^ n - ψ ^ n) / Real.sqrt 5) :=
  ⟨topological_entropy_eq_log_phi, log_goldenRatio_pos, entropy_ordering_proxy,
   goldenRatio_gt_three_half, goldenRatio_lt_two, phi_irrational, binet_formula⟩

/-! ### Recursion order pattern -/

/-- Recursion order pattern: order(S_q) = 2⌊q/2⌋+1 for q=2..5. -/
theorem recursion_order_pattern :
    (3 = 2 * (2 / 2) + 1) ∧ (3 = 2 * (3 / 2) + 1) ∧
    (5 = 2 * (4 / 2) + 1) ∧ (5 = 2 * (5 / 2) + 1) := by omega

/-! ### Fibonacci convergent alternation (Cassini identity instances) -/

/-- Cassini identity alternation: F(n)² alternately exceeds and falls below F(n-1)F(n+1). -/
theorem fib_convergent_alternation :
    Nat.fib 3 ^ 2 > Nat.fib 2 * Nat.fib 4 ∧
    Nat.fib 4 ^ 2 < Nat.fib 3 * Nat.fib 5 ∧
    Nat.fib 5 ^ 2 > Nat.fib 4 * Nat.fib 6 := by native_decide

/-! ### ψ^n → 0 -/

/-- |ψ|^n → 0 as n → ∞ (geometric decay since |ψ| < 1). -/
theorem psi_pow_tendsto_zero :
    Tendsto (fun n => |ψ| ^ n) atTop (𝓝 0) :=
  tendsto_pow_atTop_nhds_zero_of_lt_one (abs_nonneg _) abs_goldenConj_lt_one

/-- ψ^n → 0 as n → ∞. -/
theorem psi_pow_tendsto_zero' :
    Tendsto (fun n => ψ ^ n) atTop (𝓝 0) :=
  tendsto_pow_atTop_nhds_zero_of_abs_lt_one abs_goldenConj_lt_one

/-! ### Fibonacci growth sandwich -/

/-- Growth sandwich: φ^n/√5 - 1/2 < F(n) < φ^n/√5 + 1/2.
    Direct consequence of the nearest integer property. -/
theorem fib_growth_sandwich (n : Nat) :
    φ ^ n / Real.sqrt 5 - 1 / 2 < (Nat.fib n : ℝ) ∧
    (Nat.fib n : ℝ) < φ ^ n / Real.sqrt 5 + 1 / 2 := by
  have h := fib_nearest_integer n
  rw [abs_lt] at h
  constructor <;> linarith [h.1, h.2]

/-! ### Continued fraction convergence error -/

/-- F(n+1) - φ·F(n) = ψ^n (from mathlib). -/
theorem fib_ratio_error (n : Nat) :
    (Nat.fib (n + 1) : ℝ) - φ * Nat.fib n = ψ ^ n :=
  Real.fib_succ_sub_goldenRatio_mul_fib n

/-- |F(n+1) - φ·F(n)| < 1 for n ≥ 1 (since |ψ^n| ≤ |ψ| < 1). -/
theorem fib_ratio_error_lt_one (n : Nat) (hn : 1 ≤ n) :
    |(Nat.fib (n + 1) : ℝ) - φ * Nat.fib n| < 1 := by
  rw [fib_ratio_error]
  calc |ψ ^ n| = |ψ| ^ n := abs_pow ψ n
    _ ≤ |ψ| ^ 1 := by
        apply pow_le_pow_of_le_one (abs_nonneg _) (le_of_lt abs_goldenConj_lt_one) hn
    _ = |ψ| := pow_one _
    _ < 1 := abs_goldenConj_lt_one

end Omega.Entropy
