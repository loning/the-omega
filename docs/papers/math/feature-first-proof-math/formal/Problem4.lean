import Mathlib

/-!
  ## Problem 4 (progress): n = 2 identity, fully formalized

  For monic quadratics
    p(x) = x^2 + a₁ x + a₂,  q(x) = x^2 + b₁ x + b₂,
  the degree-2 symmetric additive convolution has coefficients
    c₁ = a₁ + b₁,
    c₂ = a₂ + b₂ + (a₁ b₁)/2.

  If we define
    N₂(a₁,a₂) := (a₁^2 - 4 a₂)/2,
  then the exact Stam identity is
    N₂(c₁,c₂) = N₂(a₁,a₂) + N₂(b₁,b₂).

  This is the fully closed n=2 case used by the paper proof.
-/

namespace Problem4

/-- Degree-2 convolution coefficient `c₁`. -/
def boxplus2C1 (a1 b1 : ℝ) : ℝ := a1 + b1

/-- Degree-2 convolution coefficient `c₂`. -/
noncomputable def boxplus2C2 (a1 a2 b1 b2 : ℝ) : ℝ := a2 + b2 + (a1 * b1) / 2

/-- Quadratic entropy-power proxy used in the `n=2` proof. -/
noncomputable def N2 (a1 a2 : ℝ) : ℝ := (a1 ^ 2 - 4 * a2) / 2

/-- `n=2` polynomial Stam identity in coefficient form. -/
theorem stam_n2_identity (a1 a2 b1 b2 : ℝ) :
    N2 (boxplus2C1 a1 b1) (boxplus2C2 a1 a2 b1 b2) = N2 a1 a2 + N2 b1 b2 := by
  unfold N2 boxplus2C1 boxplus2C2
  ring

end Problem4

/-!
  ## Problem 4 (reduction layer): one-gap closure template

  This section does not yet prove the all-`n` Stam inequality.
  It formalizes the exact logical reduction:

  1) If the deficit has the `δ`-decomposition
       Gap(p,q) = δ(p) + δ(q) - δ(p ⊞ q),
     and `δ` is subadditive under `⊞`,
     then `Gap(p,q) ≥ 0`.

  2) If the same gap is represented as an integral of a nonnegative bridge
     integrand, then `Gap(p,q) ≥ 0`.

  So the all-`n` closure is reduced to one bridge inequality.
-/

namespace Problem4Bridge

open MeasureTheory

variable {P : Type}
variable (boxplus : P → P → P)
variable (gap : P → P → ℝ)
variable (delta : P → ℝ)
variable (omega : P → ℝ → ℝ)

/-- Bridge integrand used in the two-scale representation. -/
noncomputable def bridgeIntegrand (p q : P) (t : ℝ) : ℝ :=
  omega p t + omega q t - 2 * omega (boxplus p q) (2 * t)

/-- If `gap = δ(p)+δ(q)-δ(p⊞q)` and `δ` is `⊞`-subadditive, then Stam gap is nonnegative. -/
theorem gap_nonneg_of_delta_subadd
    (hGapDelta :
      ∀ p q, gap p q = delta p + delta q - delta (boxplus p q))
    (hDeltaSub :
      ∀ p q, delta (boxplus p q) ≤ delta p + delta q)
    (p q : P) :
    0 ≤ gap p q := by
  rw [hGapDelta p q]
  linarith [hDeltaSub p q]

/-- If the gap has an integral representation with pointwise nonnegative bridge integrand,
then the gap is nonnegative. -/
theorem gap_nonneg_of_bridge_integral
    (hGapInt :
      ∀ p q, gap p q = ∫ t, bridgeIntegrand boxplus omega p q t)
    (hBridgeNonneg :
      ∀ p q t, 0 ≤ bridgeIntegrand boxplus omega p q t)
    (p q : P) :
    0 ≤ gap p q := by
  rw [hGapInt p q]
  exact integral_nonneg (fun t => hBridgeNonneg p q t)

/-- Concrete Stam form: if `gap(p,q)` is identified with
`N(p⊞q)-N(p)-N(q)`, then `gap_nonneg_of_delta_subadd` gives the target inequality. -/
theorem stam_nonneg_of_delta_bridge
    (N : P → ℝ)
    (hGapDef :
      ∀ p q, gap p q = N (boxplus p q) - N p - N q)
    (hGapDelta :
      ∀ p q, gap p q = delta p + delta q - delta (boxplus p q))
    (hDeltaSub :
      ∀ p q, delta (boxplus p q) ≤ delta p + delta q)
    (p q : P) :
  0 ≤ N (boxplus p q) - N p - N q := by
  rw [← hGapDef p q]
  exact gap_nonneg_of_delta_subadd (boxplus := boxplus) (gap := gap) (delta := delta)
    hGapDelta hDeltaSub p q

/-- At `t = 0`, the `δ`-subadditivity bridge is equivalent to Stam itself,
once `δ(u) = D * Var(u) - N(u)` and `Var` is additive under `⊞`. -/
theorem delta_subadd_t0_iff_stam
    (N : P → ℝ)
    (Var : P → ℝ)
    (D : ℝ)
    (delta0 : P → ℝ)
    (hDelta0 : ∀ u, delta0 u = D * Var u - N u)
    (hVarAdd : ∀ p q, Var (boxplus p q) = Var p + Var q) :
    (∀ p q, delta0 (boxplus p q) ≤ delta0 p + delta0 q) ↔
    (∀ p q, N (boxplus p q) ≥ N p + N q) := by
  constructor
  · intro hSub p q
    have h := hSub p q
    rw [hDelta0 (boxplus p q), hDelta0 p, hDelta0 q, hVarAdd p q] at h
    linarith
  · intro hStam p q
    have h := hStam p q
    rw [hDelta0 (boxplus p q), hDelta0 p, hDelta0 q, hVarAdd p q]
    linarith

end Problem4Bridge

/-!
  ## Problem 4 (Omega route template): KL projector mechanism

  This is the abstract closure pattern suggested by the Omega/POM documents:
  if the Q4 deficit can be represented as a KL distance to a reflector,
  and `⊞` is implemented by a pushforward of tensorized micro-laws,
  then subadditivity follows from:
  - KL tensorization (additivity on product laws),
  - data processing inequality (contractivity under pushforward).
-/

namespace Problem4Omega

variable {P X Y : Type}
variable (boxplus : P → P → P)
variable (μ : P → X)
variable (R : X → X)
variable (tensor : X → X → Y)
variable (push : Y → X)
variable (KLX : X → X → ℝ)
variable (KLY : Y → Y → ℝ)
variable (delta0 : P → ℝ)

/-- Abstract KL-mechanism: from tensorization + data processing to `δ`-subadditivity. -/
theorem delta_subadd_of_KL_projector
    (hDelta :
      ∀ p, delta0 p = KLX (μ p) (R (μ p)))
    (hBoxplusLaw :
      ∀ p q, μ (boxplus p q) = push (tensor (μ p) (μ q)))
    (hBoxplusRefLaw :
      ∀ p q, R (μ (boxplus p q)) = push (tensor (R (μ p)) (R (μ q))))
    (hDPI :
      ∀ a b, KLX (push a) (push b) ≤ KLY a b)
    (hTensorKL :
      ∀ a b c d, KLY (tensor a b) (tensor c d) = KLX a c + KLX b d)
    (p q : P) :
    delta0 (boxplus p q) ≤ delta0 p + delta0 q := by
  have hRef :
      R (push (tensor (μ p) (μ q))) = push (tensor (R (μ p)) (R (μ q))) := by
    simpa [hBoxplusLaw p q] using hBoxplusRefLaw p q
  rw [hDelta (boxplus p q), hBoxplusLaw p q, hRef]
  calc
    KLX (push (tensor (μ p) (μ q))) (push (tensor (R (μ p)) (R (μ q))))
        ≤ KLY (tensor (μ p) (μ q)) (tensor (R (μ p)) (R (μ q))) := hDPI _ _
    _ = KLX (μ p) (R (μ p)) + KLX (μ q) (R (μ q)) := hTensorKL _ _ _ _
    _ = delta0 p + delta0 q := by rw [hDelta p, hDelta q]

/-- Omega/KL route to Stam:
if `δ` is both a KL-projector defect and of the form `D*Var - N`,
then Stam follows. -/
theorem stam_of_KL_projector
    (N : P → ℝ)
    (Var : P → ℝ)
    (D : ℝ)
    (hDelta0Shape : ∀ u, delta0 u = D * Var u - N u)
    (hVarAdd : ∀ p q, Var (boxplus p q) = Var p + Var q)
    (hDelta :
      ∀ p, delta0 p = KLX (μ p) (R (μ p)))
    (hBoxplusLaw :
      ∀ p q, μ (boxplus p q) = push (tensor (μ p) (μ q)))
    (hBoxplusRefLaw :
      ∀ p q, R (μ (boxplus p q)) = push (tensor (R (μ p)) (R (μ q))))
    (hDPI :
      ∀ a b, KLX (push a) (push b) ≤ KLY a b)
    (hTensorKL :
      ∀ a b c d, KLY (tensor a b) (tensor c d) = KLX a c + KLX b d) :
    ∀ p q, N (boxplus p q) ≥ N p + N q := by
  have hSub : ∀ p q, delta0 (boxplus p q) ≤ delta0 p + delta0 q :=
    delta_subadd_of_KL_projector (boxplus := boxplus) (μ := μ) (R := R)
      (tensor := tensor) (push := push) (KLX := KLX) (KLY := KLY) (delta0 := delta0)
      hDelta hBoxplusLaw hBoxplusRefLaw hDPI hTensorKL
  exact
    (Problem4Bridge.delta_subadd_t0_iff_stam
      (boxplus := boxplus) (N := N) (Var := Var) (D := D) (delta0 := delta0)
      hDelta0Shape hVarAdd).mp hSub

end Problem4Omega

/-!
  ## Problem 4 (Omega route, Q4-specialized interface)

  A concrete assumption bundle for the all-`n` closure target.
  Once these assumptions are instantiated for finite free convolution,
  the Stam inequality is immediate from `stam_of_assumptions`.
-/

namespace Problem4OmegaQ4

structure Assumptions where
  P : Type
  boxplus : P → P → P
  N : P → ℝ
  Var : P → ℝ
  D : ℝ
  delta0 : P → ℝ
  X : Type
  Y : Type
  mu : P → X
  R : X → X
  tensor : X → X → Y
  push : Y → X
  KLX : X → X → ℝ
  KLY : Y → Y → ℝ
  delta0_shape : ∀ u, delta0 u = D * Var u - N u
  var_add : ∀ p q, Var (boxplus p q) = Var p + Var q
  delta_kl : ∀ p, delta0 p = KLX (mu p) (R (mu p))
  boxplus_law : ∀ p q, mu (boxplus p q) = push (tensor (mu p) (mu q))
  boxplus_ref_law : ∀ p q, R (mu (boxplus p q)) = push (tensor (R (mu p)) (R (mu q)))
  dPI : ∀ a b, KLX (push a) (push b) ≤ KLY a b
  tensor_kl : ∀ a b c d, KLY (tensor a b) (tensor c d) = KLX a c + KLX b d

/-- Q4 Omega closure theorem:
instantiating this assumption record is enough to close Stam. -/
theorem stam_of_assumptions (A : Assumptions) :
    ∀ p q : A.P, A.N (A.boxplus p q) ≥ A.N p + A.N q := by
  simpa using
    (Problem4Omega.stam_of_KL_projector
      (boxplus := A.boxplus) (μ := A.mu) (R := A.R)
      (tensor := A.tensor) (push := A.push)
      (KLX := A.KLX) (KLY := A.KLY) (delta0 := A.delta0)
      (N := A.N) (Var := A.Var) (D := A.D)
      A.delta0_shape A.var_add A.delta_kl A.boxplus_law A.boxplus_ref_law A.dPI A.tensor_kl)

end Problem4OmegaQ4

/-!
  ## Problem 4 (single-gap bridge): pointwise `DIFF`  ->  Stam

  This section isolates the exact remaining analytic gap in an abstract form:
  a pointwise two-scale differential inequality (`omega` bridge) implies
  scaled `delta`-subadditivity, which at `t = 0` is equivalent to Stam.
-/

namespace Problem4DiffBridge

variable {P : Type}
variable (boxplus : P → P → P)
variable (N : P → ℝ)
variable (Var : P → ℝ)
variable (D : ℝ)
variable (delta : P → ℝ → ℝ)
variable (delta0 : P → ℝ)
variable (omega : P → ℝ → ℝ)
variable (Tail : (ℝ → ℝ) → ℝ → ℝ)

/-- Scaled `delta`-subadditivity immediately gives the `t=0` form. -/
theorem delta_subadd_t0_of_scaled
    (hScaled : ∀ p q t, delta (boxplus p q) (2 * t) ≤ delta p t + delta q t) :
    ∀ p q, delta (boxplus p q) 0 ≤ delta p 0 + delta q 0 := by
  intro p q
  simpa using hScaled p q 0

/-- Abstract tail-calculus step:
pointwise two-scale bridge inequality implies scaled `delta`-subadditivity. -/
theorem scaled_delta_subadd_of_pointwise_diff
    (hDeltaTail : ∀ u t, delta u t = Tail (omega u) t)
    (hScale : ∀ f t, Tail f (2 * t) = 2 * Tail (fun s => f (2 * s)) t)
    (hMono : ∀ f g t, (∀ s, f s ≤ g s) → Tail f t ≤ Tail g t)
    (hAdd : ∀ f g t, Tail (fun s => f s + g s) t = Tail f t + Tail g t)
    (hSmul : ∀ c f t, Tail (fun s => c * f s) t = c * Tail f t)
    (hPoint :
      ∀ p q s, omega (boxplus p q) (2 * s) ≤ (omega p s + omega q s) / 2) :
    ∀ p q t, delta (boxplus p q) (2 * t) ≤ delta p t + delta q t := by
  intro p q t
  rw [hDeltaTail (boxplus p q) (2 * t), hDeltaTail p t, hDeltaTail q t]
  have hTailLe :
      Tail (fun s => omega (boxplus p q) (2 * s)) t
        ≤ Tail (fun s => (omega p s + omega q s) / 2) t :=
    hMono _ _ t (by
      intro s
      exact hPoint p q s)
  calc
    Tail (omega (boxplus p q)) (2 * t)
        = 2 * Tail (fun s => omega (boxplus p q) (2 * s)) t := hScale _ _
    _ ≤ 2 * Tail (fun s => (omega p s + omega q s) / 2) t := by
      exact mul_le_mul_of_nonneg_left hTailLe (by positivity)
    _ = 2 * Tail (fun s => (1 / 2 : ℝ) * (omega p s + omega q s)) t := by
      congr 2
      ext s
      ring
    _ = 2 * ((1 / 2 : ℝ) * Tail (fun s => omega p s + omega q s) t) := by
      rw [hSmul (1 / 2 : ℝ) (fun s => omega p s + omega q s) t]
    _ = Tail (fun s => omega p s + omega q s) t := by ring
    _ = Tail (omega p) t + Tail (omega q) t := hAdd _ _ _

/-- If `delta0` is the `t=0` slice of `delta`, then a pointwise two-scale bridge
closes Stam through the `delta_subadd_t0_iff_stam` bridge. -/
theorem stam_of_pointwise_diff
    (hDelta0 : ∀ u, delta0 u = delta u 0)
    (hDelta0Shape : ∀ u, delta0 u = D * Var u - N u)
    (hVarAdd : ∀ p q, Var (boxplus p q) = Var p + Var q)
    (hDeltaTail : ∀ u t, delta u t = Tail (omega u) t)
    (hScale : ∀ f t, Tail f (2 * t) = 2 * Tail (fun s => f (2 * s)) t)
    (hMono : ∀ f g t, (∀ s, f s ≤ g s) → Tail f t ≤ Tail g t)
    (hAdd : ∀ f g t, Tail (fun s => f s + g s) t = Tail f t + Tail g t)
    (hSmul : ∀ c f t, Tail (fun s => c * f s) t = c * Tail f t)
    (hPoint :
      ∀ p q s, omega (boxplus p q) (2 * s) ≤ (omega p s + omega q s) / 2) :
    ∀ p q, N (boxplus p q) ≥ N p + N q := by
  have hScaled :
      ∀ p q t, delta (boxplus p q) (2 * t) ≤ delta p t + delta q t :=
    scaled_delta_subadd_of_pointwise_diff
      (boxplus := boxplus) (delta := delta) (omega := omega) (Tail := Tail)
      hDeltaTail hScale hMono hAdd hSmul hPoint
  have hSubDelta0 :
      ∀ p q, delta0 (boxplus p q) ≤ delta0 p + delta0 q := by
    intro p q
    have h0 : delta (boxplus p q) 0 ≤ delta p 0 + delta q 0 :=
      delta_subadd_t0_of_scaled (boxplus := boxplus) (delta := delta) hScaled p q
    rw [hDelta0 (boxplus p q), hDelta0 p, hDelta0 q]
    exact h0
  exact
    (Problem4Bridge.delta_subadd_t0_iff_stam
      (boxplus := boxplus) (N := N) (Var := Var) (D := D) (delta0 := delta0)
      hDelta0Shape hVarAdd).mp hSubDelta0

end Problem4DiffBridge

/-!
  ## Problem 4 (Auric direct usage): no extra adapter layer

  This theorem is a direct bridge from the existing Auric theorem pattern
  (KL ledger + reflector + DPI + tensor KL) to Stam.
-/

namespace Problem4AuricDirect

variable {P X Y : Type}
variable (boxplus : P → P → P)
variable (N : P → ℝ)
variable (Var : P → ℝ)
variable (D : ℝ)
variable (delta0 : P → ℝ)
variable (mu : P → X)
variable (reflector : X → X)
variable (tensor : X → X → Y)
variable (push : Y → X)
variable (KLX : X → X → ℝ)
variable (KLY : Y → Y → ℝ)

/-- Direct closure theorem:
if existing Auric results provide these seven facts, Stam follows immediately. -/
theorem stam_of_existing_auric_results
    (h_kl_ledger : ∀ u, delta0 u = D * Var u - N u)
    (h_var_add : ∀ p q, Var (boxplus p q) = Var p + Var q)
    (h_delta_kl : ∀ p, delta0 p = KLX (mu p) (reflector (mu p)))
    (h_boxplus_law : ∀ p q, mu (boxplus p q) = push (tensor (mu p) (mu q)))
    (h_reflector_exchange :
      ∀ p q, reflector (mu (boxplus p q)) = push (tensor (reflector (mu p)) (reflector (mu q))))
    (h_dpi : ∀ a b, KLX (push a) (push b) ≤ KLY a b)
    (h_tensor_kl : ∀ a b c d, KLY (tensor a b) (tensor c d) = KLX a c + KLX b d) :
    ∀ p q, N (boxplus p q) ≥ N p + N q := by
  exact
    Problem4Omega.stam_of_KL_projector
      (boxplus := boxplus) (N := N) (Var := Var) (D := D)
      (μ := mu) (R := reflector) (tensor := tensor) (push := push)
      (KLX := KLX) (KLY := KLY) (delta0 := delta0)
      h_kl_ledger h_var_add h_delta_kl h_boxplus_law h_reflector_exchange h_dpi h_tensor_kl

end Problem4AuricDirect
