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
  ## Problem 4 (quartic Route-1 algebra): exact closed form for `δ`

  For the centered quartic flow normal form
    r_{u,B,c}(x) = x^4 - 6u x^2 + Bx + (3u^2 + c),
  the Route-1 derivation uses the identity
    δ(u,B,c) = ((u/3) * R(u,B,c) - Δ(u,B,c)) / R(u,B,c),
  where `Δ` is the quartic discriminant and `R = Φ * Δ`.

  The theorem below formally checks that this expression is exactly the
  closed rational formula used in the paper.
-/

namespace Problem4Quartic

def discQ4 (u B c : ℝ) : ℝ :=
  -27 * B ^ 4
    - 864 * B ^ 2 * c * u
    - 1728 * B ^ 2 * u ^ 3
    + 256 * c ^ 3
    - 2304 * c ^ 2 * u ^ 2
    + 27648 * u ^ 6

def denomQ4 (u B c : ℝ) : ℝ :=
  144 * (6 * u ^ 2 + c) * (96 * u ^ 3 - 16 * u * c - 3 * B ^ 2)

noncomputable def deltaQ4Closed (u B c : ℝ) : ℝ :=
  (27 * B ^ 4
      + 144 * u * B ^ 2 * (5 * c + 6 * u ^ 2)
      + 256 * c ^ 2 * (6 * u ^ 2 - c)) /
    denomQ4 u B c

noncomputable def deltaQ4FromDisc (u B c : ℝ) : ℝ :=
  ((u / 3) * denomQ4 u B c - discQ4 u B c) / denomQ4 u B c

theorem deltaQ4_numerator_identity (u B c : ℝ) :
    (u / 3) * denomQ4 u B c - discQ4 u B c =
      27 * B ^ 4
        + 144 * u * B ^ 2 * (5 * c + 6 * u ^ 2)
        + 256 * c ^ 2 * (6 * u ^ 2 - c) := by
  unfold denomQ4 discQ4
  ring

theorem deltaQ4_closed_eq (u B c : ℝ) :
    deltaQ4FromDisc u B c = deltaQ4Closed u B c := by
  unfold deltaQ4FromDisc deltaQ4Closed
  rw [deltaQ4_numerator_identity]

end Problem4Quartic

/-!
  ## Problem 4 (quartic Route-1 bridge): denominator-clearing reduction

  For two quartic Route-1 states `(u₁,B₁,c₁)` and `(u₂,B₂,c₂)`, set
    `(u₁₂,B₁₂,c₁₂) = (u₁+u₂, B₁+B₂, c₁+c₂)`.
  The smoothed bridge gap at fixed time can be written as
    G₄ = δ(u₁,B₁,c₁) + δ(u₂,B₂,c₂) - δ(u₁₂,B₁₂,c₁₂),
  with each `δ` a rational function.

  This namespace formalizes the exact denominator-clearing identity
    G₄ = Ξ₄ / (D₁ D₂ D₁₂),
  so proving `G₄ ≥ 0` on a chamber with positive denominators reduces to
  proving the polynomial inequality `Ξ₄ ≥ 0`.
-/

namespace Problem4QuarticBridge

def numQ4 (u B c : ℝ) : ℝ :=
  27 * B ^ 4
    + 144 * u * B ^ 2 * (5 * c + 6 * u ^ 2)
    + 256 * c ^ 2 * (6 * u ^ 2 - c)

def denQ4 (u B c : ℝ) : ℝ := Problem4Quartic.denomQ4 u B c

noncomputable def delta4 (u B c : ℝ) : ℝ := numQ4 u B c / denQ4 u B c

noncomputable def G4 (u1 B1 c1 u2 B2 c2 : ℝ) : ℝ :=
  delta4 u1 B1 c1
    + delta4 u2 B2 c2
    - delta4 (u1 + u2) (B1 + B2) (c1 + c2)

def Xi4 (u1 B1 c1 u2 B2 c2 : ℝ) : ℝ :=
  numQ4 u1 B1 c1
      * denQ4 u2 B2 c2
      * denQ4 (u1 + u2) (B1 + B2) (c1 + c2)
    + numQ4 u2 B2 c2
      * denQ4 u1 B1 c1
      * denQ4 (u1 + u2) (B1 + B2) (c1 + c2)
    - numQ4 (u1 + u2) (B1 + B2) (c1 + c2)
      * denQ4 u1 B1 c1
      * denQ4 u2 B2 c2

def denBridge4 (u1 B1 c1 u2 B2 c2 : ℝ) : ℝ :=
  denQ4 u1 B1 c1 * denQ4 u2 B2 c2 * denQ4 (u1 + u2) (B1 + B2) (c1 + c2)

def lFac (u c : ℝ) : ℝ := 6 * u ^ 2 + c

def qFac (u B c : ℝ) : ℝ := 96 * u ^ 3 - 16 * u * c - 3 * B ^ 2

def chamberPlus (u B c : ℝ) : Prop :=
  0 < lFac u c ∧ 0 < qFac u B c

theorem denQ4_eq_factorized (u B c : ℝ) :
    denQ4 u B c = 144 * lFac u c * qFac u B c := by
  rfl

theorem denQ4_pos_of_chamberPlus
    (u B c : ℝ) (hC : chamberPlus u B c) :
    0 < denQ4 u B c := by
  rcases hC with ⟨hL, hQ⟩
  rw [denQ4_eq_factorized]
  have h144 : (0 : ℝ) < 144 := by norm_num
  exact mul_pos (mul_pos h144 hL) hQ

theorem denBridge4_pos_of_chamberPlus
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (hC1 : chamberPlus u1 B1 c1)
    (hC2 : chamberPlus u2 B2 c2)
    (hC12 : chamberPlus (u1 + u2) (B1 + B2) (c1 + c2)) :
    0 < denBridge4 u1 B1 c1 u2 B2 c2 := by
  have h1 : 0 < denQ4 u1 B1 c1 := denQ4_pos_of_chamberPlus u1 B1 c1 hC1
  have h2 : 0 < denQ4 u2 B2 c2 := denQ4_pos_of_chamberPlus u2 B2 c2 hC2
  have h12 : 0 < denQ4 (u1 + u2) (B1 + B2) (c1 + c2) :=
    denQ4_pos_of_chamberPlus (u1 + u2) (B1 + B2) (c1 + c2) hC12
  unfold denBridge4
  exact mul_pos (mul_pos h1 h2) h12

theorem G4_eq_Xi4_div
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (h1 : denQ4 u1 B1 c1 ≠ 0)
    (h2 : denQ4 u2 B2 c2 ≠ 0)
    (h12 : denQ4 (u1 + u2) (B1 + B2) (c1 + c2) ≠ 0) :
    G4 u1 B1 c1 u2 B2 c2 =
      Xi4 u1 B1 c1 u2 B2 c2 / denBridge4 u1 B1 c1 u2 B2 c2 := by
  unfold G4 delta4 Xi4 denBridge4
  field_simp [h1, h2, h12]

theorem G4_eq_Xi4_div_of_chamberPlus
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (hC1 : chamberPlus u1 B1 c1)
    (hC2 : chamberPlus u2 B2 c2)
    (hC12 : chamberPlus (u1 + u2) (B1 + B2) (c1 + c2)) :
    G4 u1 B1 c1 u2 B2 c2 =
      Xi4 u1 B1 c1 u2 B2 c2 / denBridge4 u1 B1 c1 u2 B2 c2 := by
  have h1 : denQ4 u1 B1 c1 ≠ 0 := ne_of_gt (denQ4_pos_of_chamberPlus u1 B1 c1 hC1)
  have h2 : denQ4 u2 B2 c2 ≠ 0 := ne_of_gt (denQ4_pos_of_chamberPlus u2 B2 c2 hC2)
  have h12 : denQ4 (u1 + u2) (B1 + B2) (c1 + c2) ≠ 0 := by
    exact ne_of_gt (denQ4_pos_of_chamberPlus (u1 + u2) (B1 + B2) (c1 + c2) hC12)
  exact G4_eq_Xi4_div u1 B1 c1 u2 B2 c2 h1 h2 h12

theorem G4_nonneg_of_Xi4_nonneg
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (h1 : 0 < denQ4 u1 B1 c1)
    (h2 : 0 < denQ4 u2 B2 c2)
    (h12 : 0 < denQ4 (u1 + u2) (B1 + B2) (c1 + c2))
    (hXi : 0 ≤ Xi4 u1 B1 c1 u2 B2 c2) :
    0 ≤ G4 u1 B1 c1 u2 B2 c2 := by
  have hz1 : denQ4 u1 B1 c1 ≠ 0 := ne_of_gt h1
  have hz2 : denQ4 u2 B2 c2 ≠ 0 := ne_of_gt h2
  have hz12 : denQ4 (u1 + u2) (B1 + B2) (c1 + c2) ≠ 0 := ne_of_gt h12
  have hEq := G4_eq_Xi4_div u1 B1 c1 u2 B2 c2 hz1 hz2 hz12
  have hDenPos : 0 < denBridge4 u1 B1 c1 u2 B2 c2 := by
    unfold denBridge4
    exact mul_pos (mul_pos h1 h2) h12
  rw [hEq]
  exact div_nonneg hXi hDenPos.le

theorem Xi4_nonneg_of_G4_nonneg
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (h1 : 0 < denQ4 u1 B1 c1)
    (h2 : 0 < denQ4 u2 B2 c2)
    (h12 : 0 < denQ4 (u1 + u2) (B1 + B2) (c1 + c2))
    (hG : 0 ≤ G4 u1 B1 c1 u2 B2 c2) :
    0 ≤ Xi4 u1 B1 c1 u2 B2 c2 := by
  have hz1 : denQ4 u1 B1 c1 ≠ 0 := ne_of_gt h1
  have hz2 : denQ4 u2 B2 c2 ≠ 0 := ne_of_gt h2
  have hz12 : denQ4 (u1 + u2) (B1 + B2) (c1 + c2) ≠ 0 := ne_of_gt h12
  have hEq := G4_eq_Xi4_div u1 B1 c1 u2 B2 c2 hz1 hz2 hz12
  have hDenPos : 0 < denBridge4 u1 B1 c1 u2 B2 c2 := by
    unfold denBridge4
    exact mul_pos (mul_pos h1 h2) h12
  rw [hEq] at hG
  have hMul : 0 ≤
      (Xi4 u1 B1 c1 u2 B2 c2 / denBridge4 u1 B1 c1 u2 B2 c2)
        * denBridge4 u1 B1 c1 u2 B2 c2 := by
    exact mul_nonneg hG hDenPos.le
  have hRewrite :
      (Xi4 u1 B1 c1 u2 B2 c2 / denBridge4 u1 B1 c1 u2 B2 c2)
        * denBridge4 u1 B1 c1 u2 B2 c2 =
      Xi4 u1 B1 c1 u2 B2 c2 := by
    field_simp [denBridge4, hz1, hz2, hz12]
  simpa [hRewrite] using hMul

theorem G4_nonneg_iff_Xi4_nonneg
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (h1 : 0 < denQ4 u1 B1 c1)
    (h2 : 0 < denQ4 u2 B2 c2)
    (h12 : 0 < denQ4 (u1 + u2) (B1 + B2) (c1 + c2)) :
    (0 ≤ G4 u1 B1 c1 u2 B2 c2) ↔ (0 ≤ Xi4 u1 B1 c1 u2 B2 c2) := by
  constructor
  · exact Xi4_nonneg_of_G4_nonneg u1 B1 c1 u2 B2 c2 h1 h2 h12
  · exact G4_nonneg_of_Xi4_nonneg u1 B1 c1 u2 B2 c2 h1 h2 h12

theorem G4_nonneg_of_Xi4_nonneg_chamberPlus
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (hC1 : chamberPlus u1 B1 c1)
    (hC2 : chamberPlus u2 B2 c2)
    (hC12 : chamberPlus (u1 + u2) (B1 + B2) (c1 + c2))
    (hXi : 0 ≤ Xi4 u1 B1 c1 u2 B2 c2) :
    0 ≤ G4 u1 B1 c1 u2 B2 c2 := by
  have h1 : 0 < denQ4 u1 B1 c1 := denQ4_pos_of_chamberPlus u1 B1 c1 hC1
  have h2 : 0 < denQ4 u2 B2 c2 := denQ4_pos_of_chamberPlus u2 B2 c2 hC2
  have h12 : 0 < denQ4 (u1 + u2) (B1 + B2) (c1 + c2) :=
    denQ4_pos_of_chamberPlus (u1 + u2) (B1 + B2) (c1 + c2) hC12
  exact G4_nonneg_of_Xi4_nonneg u1 B1 c1 u2 B2 c2 h1 h2 h12 hXi

theorem Xi4_nonneg_of_G4_nonneg_chamberPlus
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (hC1 : chamberPlus u1 B1 c1)
    (hC2 : chamberPlus u2 B2 c2)
    (hC12 : chamberPlus (u1 + u2) (B1 + B2) (c1 + c2))
    (hG : 0 ≤ G4 u1 B1 c1 u2 B2 c2) :
    0 ≤ Xi4 u1 B1 c1 u2 B2 c2 := by
  have h1 : 0 < denQ4 u1 B1 c1 := denQ4_pos_of_chamberPlus u1 B1 c1 hC1
  have h2 : 0 < denQ4 u2 B2 c2 := denQ4_pos_of_chamberPlus u2 B2 c2 hC2
  have h12 : 0 < denQ4 (u1 + u2) (B1 + B2) (c1 + c2) :=
    denQ4_pos_of_chamberPlus (u1 + u2) (B1 + B2) (c1 + c2) hC12
  exact Xi4_nonneg_of_G4_nonneg u1 B1 c1 u2 B2 c2 h1 h2 h12 hG

theorem G4_nonneg_iff_Xi4_nonneg_chamberPlus
    (u1 B1 c1 u2 B2 c2 : ℝ)
    (hC1 : chamberPlus u1 B1 c1)
    (hC2 : chamberPlus u2 B2 c2)
    (hC12 : chamberPlus (u1 + u2) (B1 + B2) (c1 + c2)) :
    (0 ≤ G4 u1 B1 c1 u2 B2 c2) ↔ (0 ≤ Xi4 u1 B1 c1 u2 B2 c2) := by
  constructor
  · exact Xi4_nonneg_of_G4_nonneg_chamberPlus u1 B1 c1 u2 B2 c2 hC1 hC2 hC12
  · exact G4_nonneg_of_Xi4_nonneg_chamberPlus u1 B1 c1 u2 B2 c2 hC1 hC2 hC12

end Problem4QuarticBridge

namespace Problem4QuarticEven

/-- Two-variable Titu/Engel form. -/
theorem titu2 (x y a b : ℝ) (ha : 0 < a) (hb : 0 < b) :
    (x + y) ^ 2 / (a + b) ≤ x ^ 2 / a + y ^ 2 / b := by
  have hab : a + b ≠ 0 := by linarith
  have hEq :
      x ^ 2 / a + y ^ 2 / b - (x + y) ^ 2 / (a + b) =
        (b * x - a * y) ^ 2 / (a * b * (a + b)) := by
    field_simp [ha.ne', hb.ne', hab]
    ring
  have hDenPos : 0 < a * b * (a + b) := by
    exact mul_pos (mul_pos ha hb) (add_pos ha hb)
  have hNonneg :
      0 ≤ (b * x - a * y) ^ 2 / (a * b * (a + b)) := by
    exact div_nonneg (sq_nonneg _) hDenPos.le
  have hMain : 0 ≤ x ^ 2 / a + y ^ 2 / b - (x + y) ^ 2 / (a + b) := by
    rw [hEq]
    exact hNonneg
  linarith

noncomputable def G4Even (u1 c1 u2 c2 : ℝ) : ℝ :=
  (c1 ^ 2 / (u1 * (6 * u1 ^ 2 + c1))
      + c2 ^ 2 / (u2 * (6 * u2 ^ 2 + c2))
      - (c1 + c2) ^ 2 / ((u1 + u2) * (6 * (u1 + u2) ^ 2 + (c1 + c2)))) / 9

/-- In the `B=0` quartic subfamily, the bridge gap is nonnegative under
natural lower-bound chamber conditions on `c`. -/
theorem G4Even_nonneg_of_bounds
    (u1 c1 u2 c2 : ℝ)
    (hu1 : 0 < u1) (hu2 : 0 < u2)
    (hc1 : -3 * u1 ^ 2 ≤ c1) (hc2 : -3 * u2 ^ 2 ≤ c2) :
    0 ≤ G4Even u1 c1 u2 c2 := by
  let A : ℝ := u1 * (6 * u1 ^ 2 + c1)
  let B : ℝ := u2 * (6 * u2 ^ 2 + c2)
  let C : ℝ := (u1 + u2) * (6 * (u1 + u2) ^ 2 + (c1 + c2))
  have hAfac : 0 < 6 * u1 ^ 2 + c1 := by
    have hu1sq : 0 < u1 ^ 2 := sq_pos_of_ne_zero (by exact hu1.ne')
    nlinarith
  have hBfac : 0 < 6 * u2 ^ 2 + c2 := by
    have hu2sq : 0 < u2 ^ 2 := sq_pos_of_ne_zero (by exact hu2.ne')
    nlinarith
  have hApos : 0 < A := by
    dsimp [A]
    exact mul_pos hu1 hAfac
  have hBpos : 0 < B := by
    dsimp [B]
    exact mul_pos hu2 hBfac
  have hDiff :
      C - (A + B) =
        18 * u1 ^ 2 * u2 + 18 * u1 * u2 ^ 2 + u1 * c2 + u2 * c1 := by
    dsimp [A, B, C]
    ring
  have hCross1 : u1 * c2 ≥ -3 * u1 * u2 ^ 2 := by
    nlinarith
  have hCross2 : u2 * c1 ≥ -3 * u2 * u1 ^ 2 := by
    nlinarith
  have hCgeAB : A + B ≤ C := by
    rw [← sub_nonneg, hDiff]
    nlinarith [hCross1, hCross2, hu1, hu2]
  have hABpos : 0 < A + B := add_pos hApos hBpos
  have hCpos : 0 < C := lt_of_lt_of_le hABpos hCgeAB
  have hInv : (1 : ℝ) / C ≤ (1 : ℝ) / (A + B) := by
    exact one_div_le_one_div_of_le hABpos hCgeAB
  have hSq : 0 ≤ (c1 + c2) ^ 2 := sq_nonneg (c1 + c2)
  have hScale :
      (c1 + c2) ^ 2 / C ≤ (c1 + c2) ^ 2 / (A + B) := by
    have hMul := mul_le_mul_of_nonneg_left hInv hSq
    simpa [div_eq_mul_inv, mul_comm, mul_left_comm, mul_assoc] using hMul
  have hTitu :
      (c1 + c2) ^ 2 / (A + B) ≤ c1 ^ 2 / A + c2 ^ 2 / B := by
    exact titu2 c1 c2 A B hApos hBpos
  have hCore :
      0 ≤ c1 ^ 2 / A + c2 ^ 2 / B - (c1 + c2) ^ 2 / C := by
    nlinarith [hScale, hTitu]
  have hNine : 0 < (9 : ℝ) := by norm_num
  unfold G4Even
  have hDiv : 0 ≤
      (c1 ^ 2 / (u1 * (6 * u1 ^ 2 + c1))
        + c2 ^ 2 / (u2 * (6 * u2 ^ 2 + c2))
        - (c1 + c2) ^ 2 / ((u1 + u2) * (6 * (u1 + u2) ^ 2 + (c1 + c2)))) := by
    simpa [A, B, C] using hCore
  exact div_nonneg hDiv hNine.le

end Problem4QuarticEven

namespace Problem4QuarticOdd

noncomputable def phi (x : ℝ) : ℝ := x * (1 + x) / (1 - x)

noncomputable def deltaC0 (u x : ℝ) : ℝ := (u / 3) * phi x

noncomputable def G4C0 (u1 x1 u2 x2 x12 : ℝ) : ℝ :=
  deltaC0 u1 x1 + deltaC0 u2 x2 - deltaC0 (u1 + u2) x12

noncomputable def xParam (u B : ℝ) : ℝ := B ^ 2 / (32 * u ^ 3)

theorem xParam_nonneg (u B : ℝ) (hu : 0 < u) : 0 ≤ xParam u B := by
  unfold xParam
  exact div_nonneg (sq_nonneg B) (by positivity)

theorem xParam_lt_one_of_bound
    (u B : ℝ) (hu : 0 < u) (hB : B ^ 2 < 32 * u ^ 3) :
    xParam u B < 1 := by
  unfold xParam
  have hden : 0 < 32 * u ^ 3 := by positivity
  have hdiv : B ^ 2 / (32 * u ^ 3) < (32 * u ^ 3) / (32 * u ^ 3) :=
    div_lt_div_of_pos_right hB hden
  simpa [hden.ne'] using hdiv

theorem xParam_add_le_weighted
    (u1 B1 u2 B2 : ℝ) (hu1 : 0 < u1) (hu2 : 0 < u2) :
    xParam (u1 + u2) (B1 + B2)
      ≤ (u1 / (u1 + u2)) * xParam u1 B1
          + (u2 / (u1 + u2)) * xParam u2 B2 := by
  have hu12 : 0 < u1 + u2 := add_pos hu1 hu2
  have hcs :
      (B1 + B2) ^ 2
        ≤ ((B1 / u1) ^ 2 + (B2 / u2) ^ 2) * (u1 ^ 2 + u2 ^ 2) := by
    have hsq : 0 ≤ ((B1 / u1) * u2 - (B2 / u2) * u1) ^ 2 := sq_nonneg _
    have hsq_expand :
        ((B1 / u1) * u2 - (B2 / u2) * u1) ^ 2
          =
          ((B1 / u1) ^ 2 + (B2 / u2) ^ 2) * (u1 ^ 2 + u2 ^ 2)
            - (B1 + B2) ^ 2 := by
      field_simp [hu1.ne', hu2.ne']
      ring
    have haux :
        0 ≤
          ((B1 / u1) ^ 2 + (B2 / u2) ^ 2) * (u1 ^ 2 + u2 ^ 2)
            - (B1 + B2) ^ 2 := by
      simpa [hsq_expand] using hsq
    nlinarith
  have hsum : u1 ^ 2 + u2 ^ 2 ≤ (u1 + u2) ^ 2 := by
    nlinarith [sq_nonneg (u1 - u2)]
  have hfac_nonneg : 0 ≤ (B1 / u1) ^ 2 + (B2 / u2) ^ 2 := by nlinarith
  have hmain :
      (B1 + B2) ^ 2
        ≤ ((B1 / u1) ^ 2 + (B2 / u2) ^ 2) * (u1 + u2) ^ 2 := by
    exact le_trans hcs (mul_le_mul_of_nonneg_left hsum hfac_nonneg)
  have hdiv :
      (B1 + B2) ^ 2 / (32 * (u1 + u2) ^ 3)
        ≤ (((B1 / u1) ^ 2 + (B2 / u2) ^ 2) * (u1 + u2) ^ 2) /
            (32 * (u1 + u2) ^ 3) := by
    exact div_le_div_of_nonneg_right hmain (by positivity)
  have hrewrite :
      (((B1 / u1) ^ 2 + (B2 / u2) ^ 2) * (u1 + u2) ^ 2) /
          (32 * (u1 + u2) ^ 3)
      =
      (u1 / (u1 + u2)) * xParam u1 B1
        + (u2 / (u1 + u2)) * xParam u2 B2 := by
    unfold xParam
    field_simp [hu1.ne', hu2.ne', hu12.ne']
  unfold xParam at hdiv ⊢
  calc
    (B1 + B2) ^ 2 / (32 * (u1 + u2) ^ 3)
        ≤ (((B1 / u1) ^ 2 + (B2 / u2) ^ 2) * (u1 + u2) ^ 2) /
            (32 * (u1 + u2) ^ 3) := hdiv
    _ = (u1 / (u1 + u2)) * (B1 ^ 2 / (32 * u1 ^ 3))
          + (u2 / (u1 + u2)) * (B2 ^ 2 / (32 * u2 ^ 3)) := hrewrite

/-- Monotonicity of `phi` on `[0,1)`. -/
theorem phi_mono_nonneg_lt1
    {x y : ℝ} (hx0 : 0 ≤ x) (hxy : x ≤ y) (hy1 : y < 1) :
    phi x ≤ phi y := by
  have hx1 : x < 1 := lt_of_le_of_lt hxy hy1
  have hy0 : 0 ≤ y := le_trans hx0 hxy
  have hxden : 0 < 1 - x := sub_pos.mpr hx1
  have hyden : 0 < 1 - y := sub_pos.mpr hy1
  have hfac_nonneg : 0 ≤ 1 + x + y - x * y := by
    have hy1mx_nonneg : 0 ≤ y * (1 - x) := mul_nonneg hy0 hxden.le
    have hrewrite : 1 + x + y - x * y = 1 + x + y * (1 - x) := by ring
    rw [hrewrite]
    nlinarith
  have hdiff :
      phi y - phi x =
        (y - x) * (1 + x + y - x * y) / ((1 - x) * (1 - y)) := by
    unfold phi
    field_simp [hxden.ne', hyden.ne']
    ring
  have hnum_nonneg : 0 ≤ (y - x) * (1 + x + y - x * y) := by
    exact mul_nonneg (sub_nonneg.mpr hxy) hfac_nonneg
  have hden_pos : 0 < (1 - x) * (1 - y) := mul_pos hxden hyden
  have hsub_nonneg : 0 ≤ phi y - phi x := by
    rw [hdiff]
    exact div_nonneg hnum_nonneg hden_pos.le
  linarith

/-- Two-point convexity inequality for `phi` on `(-∞,1)`. -/
theorem phi_convex_two_point
    (w x y : ℝ)
    (hw0 : 0 ≤ w) (hw1 : w ≤ 1)
    (hx1 : x < 1) (hy1 : y < 1) :
    phi (w * x + (1 - w) * y) ≤ w * phi x + (1 - w) * phi y := by
  let m : ℝ := w * x + (1 - w) * y
  have hwm_nonneg : 0 ≤ 1 - w := by linarith
  have hdx : 0 < 1 - x := sub_pos.mpr hx1
  have hdy : 0 < 1 - y := sub_pos.mpr hy1
  have hm1 : m < 1 := by
    have hterm1_nonneg : 0 ≤ w * (1 - x) := mul_nonneg hw0 hdx.le
    have hterm2_nonneg : 0 ≤ (1 - w) * (1 - y) := mul_nonneg hwm_nonneg hdy.le
    have hsum : 0 < w * (1 - x) + (1 - w) * (1 - y) := by
      by_cases hwz : w = 0
      · subst hwz
        have hterm2_pos : 0 < (1 - (0 : ℝ)) * (1 - y) := by nlinarith [hdy]
        nlinarith [hterm2_pos]
      · have hwpos : 0 < w := lt_of_le_of_ne hw0 (Ne.symm hwz)
        have hterm1_pos : 0 < w * (1 - x) := mul_pos hwpos hdx
        nlinarith [hterm1_pos, hterm2_nonneg]
    have hrewrite : 1 - m = w * (1 - x) + (1 - w) * (1 - y) := by
      dsimp [m]
      ring
    have : 0 < 1 - m := by simpa [hrewrite] using hsum
    exact sub_pos.mp this
  have hdm : 0 < 1 - m := sub_pos.mpr hm1
  have hgap :
      w * phi x + (1 - w) * phi y - phi m =
        2 * w * (1 - w) * (x - y) ^ 2 /
          ((1 - x) * (1 - y) * (1 - m)) := by
    unfold phi
    field_simp [hdx.ne', hdy.ne', hdm.ne']
    ring
  have hnum_nonneg : 0 ≤ 2 * w * (1 - w) * (x - y) ^ 2 := by
    have hsq : 0 ≤ (x - y) ^ 2 := sq_nonneg (x - y)
    have hww : 0 ≤ w * (1 - w) := mul_nonneg hw0 hwm_nonneg
    nlinarith
  have hden_pos : 0 < (1 - x) * (1 - y) * (1 - m) := by
    exact mul_pos (mul_pos hdx hdy) hdm
  have hgap_nonneg : 0 ≤ w * phi x + (1 - w) * phi y - phi m := by
    rw [hgap]
    exact div_nonneg hnum_nonneg hden_pos.le
  have : phi m ≤ w * phi x + (1 - w) * phi y := by linarith
  simpa [m] using this

/-- Convex+monotone one-step bridge for the `c=0` quartic reduction.
This is the exact inequality used in the paper proof once
`x12 ≤ (u1/(u1+u2))x1 + (u2/(u1+u2))x2` is supplied. -/
theorem G4C0_nonneg_of_convex_mono
    (u1 x1 u2 x2 x12 : ℝ)
    (hu1 : 0 ≤ u1) (hu2 : 0 ≤ u2) (hTot : 0 < u1 + u2)
    (hx1_lt_one : x1 < 1) (hx2_lt_one : x2 < 1)
    (hx12_nonneg : 0 ≤ x12)
    (hBound :
      x12 ≤ (u1 / (u1 + u2)) * x1 + (u2 / (u1 + u2)) * x2)
    (hMixLt :
      (u1 / (u1 + u2)) * x1 + (u2 / (u1 + u2)) * x2 < 1)
    (hMono :
      ∀ {x y : ℝ}, 0 ≤ x → x ≤ y → y < 1 → phi x ≤ phi y)
    (hConv :
      ∀ (w x y : ℝ), 0 ≤ w → w ≤ 1 → x < 1 → y < 1 →
        phi (w * x + (1 - w) * y) ≤ w * phi x + (1 - w) * phi y) :
    0 ≤ G4C0 u1 x1 u2 x2 x12 := by
  let w : ℝ := u1 / (u1 + u2)
  have hw0 : 0 ≤ w := by
    dsimp [w]
    exact div_nonneg hu1 (le_of_lt hTot)
  have hw1 : w ≤ 1 := by
    dsimp [w]
    have hden : u1 + u2 ≠ 0 := ne_of_gt hTot
    field_simp [hden]
    linarith
  have hwComp :
      1 - w = u2 / (u1 + u2) := by
    dsimp [w]
    field_simp [hTot.ne']
    ring
  have hMixEq :
      w * x1 + (1 - w) * x2 =
        (u1 / (u1 + u2)) * x1 + (u2 / (u1 + u2)) * x2 := by
    rw [hwComp]
  have hPhiMono :
      phi x12 ≤ phi (w * x1 + (1 - w) * x2) := by
    apply hMono hx12_nonneg
    · rw [hMixEq]
      exact hBound
    · rw [hMixEq]
      exact hMixLt
  have hPhiConv :
      phi (w * x1 + (1 - w) * x2) ≤ w * phi x1 + (1 - w) * phi x2 := by
    exact hConv w x1 x2 hw0 hw1 hx1_lt_one hx2_lt_one
  have hPhi :
      phi x12 ≤ w * phi x1 + (1 - w) * phi x2 := by
    exact le_trans hPhiMono hPhiConv
  have hScale :
      (u1 + u2) / 3 * phi x12
        ≤ (u1 + u2) / 3 * (w * phi x1 + (1 - w) * phi x2) := by
    exact mul_le_mul_of_nonneg_left hPhi (by positivity)
  have hRewrite :
      (u1 + u2) / 3 * (w * phi x1 + (1 - w) * phi x2)
        = u1 / 3 * phi x1 + u2 / 3 * phi x2 := by
    dsimp [w]
    field_simp [hTot.ne']
    ring
  unfold G4C0 deltaC0
  linarith [hScale, hRewrite]

theorem G4C0_nonneg
    (u1 x1 u2 x2 x12 : ℝ)
    (hu1 : 0 ≤ u1) (hu2 : 0 ≤ u2) (hTot : 0 < u1 + u2)
    (hx1_lt_one : x1 < 1) (hx2_lt_one : x2 < 1)
    (hx12_nonneg : 0 ≤ x12)
    (hBound :
      x12 ≤ (u1 / (u1 + u2)) * x1 + (u2 / (u1 + u2)) * x2)
    (hMixLt :
      (u1 / (u1 + u2)) * x1 + (u2 / (u1 + u2)) * x2 < 1) :
    0 ≤ G4C0 u1 x1 u2 x2 x12 := by
  refine G4C0_nonneg_of_convex_mono
      u1 x1 u2 x2 x12 hu1 hu2 hTot hx1_lt_one hx2_lt_one
      hx12_nonneg hBound hMixLt ?_ ?_
  · intro x y hx0 hxy hy1
    exact phi_mono_nonneg_lt1 hx0 hxy hy1
  · intro w x y hw0 hw1 hx1 hy1
    exact phi_convex_two_point w x y hw0 hw1 hx1 hy1

theorem G4C0_nonneg_of_B_bounds
    (u1 B1 u2 B2 : ℝ)
    (hu1 : 0 < u1) (hu2 : 0 < u2)
    (hB1 : B1 ^ 2 < 32 * u1 ^ 3)
    (hB2 : B2 ^ 2 < 32 * u2 ^ 3) :
    0 ≤ G4C0 u1 (xParam u1 B1) u2 (xParam u2 B2) (xParam (u1 + u2) (B1 + B2)) := by
  have hu12 : 0 < u1 + u2 := add_pos hu1 hu2
  have hx1_lt1 : xParam u1 B1 < 1 := xParam_lt_one_of_bound u1 B1 hu1 hB1
  have hx2_lt1 : xParam u2 B2 < 1 := xParam_lt_one_of_bound u2 B2 hu2 hB2
  have hx12_nonneg : 0 ≤ xParam (u1 + u2) (B1 + B2) := xParam_nonneg (u1 + u2) (B1 + B2) hu12
  have hBound :
      xParam (u1 + u2) (B1 + B2)
        ≤ (u1 / (u1 + u2)) * xParam u1 B1
            + (u2 / (u1 + u2)) * xParam u2 B2 := by
    exact xParam_add_le_weighted u1 B1 u2 B2 hu1 hu2
  have hw0 : 0 ≤ u1 / (u1 + u2) := div_nonneg hu1.le hu12.le
  have hw1 : 0 ≤ u2 / (u1 + u2) := div_nonneg hu2.le hu12.le
  have hw0pos : 0 < u1 / (u1 + u2) := div_pos hu1 hu12
  have hw1pos : 0 < u2 / (u1 + u2) := div_pos hu2 hu12
  have hwsum : u1 / (u1 + u2) + u2 / (u1 + u2) = 1 := by
    field_simp [hu12.ne']
  have hMixLt :
      (u1 / (u1 + u2)) * xParam u1 B1 + (u2 / (u1 + u2)) * xParam u2 B2 < 1 := by
    have hterm1 :
        (u1 / (u1 + u2)) * xParam u1 B1
          < (u1 / (u1 + u2)) * 1 := by
      exact mul_lt_mul_of_pos_left hx1_lt1 hw0pos
    have hterm2 :
        (u2 / (u1 + u2)) * xParam u2 B2
          < (u2 / (u1 + u2)) * 1 := by
      exact mul_lt_mul_of_pos_left hx2_lt1 hw1pos
    have hsumlt :
        (u1 / (u1 + u2)) * xParam u1 B1 + (u2 / (u1 + u2)) * xParam u2 B2
          <
        (u1 / (u1 + u2)) * 1 + (u2 / (u1 + u2)) * 1 := by
      exact add_lt_add hterm1 hterm2
    have hRhs :
        (u1 / (u1 + u2)) * 1 + (u2 / (u1 + u2)) * 1 = 1 := by
      nlinarith [hwsum]
    nlinarith [hsumlt, hRhs]
  exact
    G4C0_nonneg u1 (xParam u1 B1) u2 (xParam u2 B2) (xParam (u1 + u2) (B1 + B2))
      hu1.le hu2.le hu12 hx1_lt1 hx2_lt1 hx12_nonneg hBound hMixLt

end Problem4QuarticOdd

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
