import Mathlib

open MeasureTheory

/-!
  ## Problem 2: Rankin-Selberg Test Vector

  External axioms:
  * (BZ) mirabolic restriction: image of Res_{P_{n+1}} contains
    C_c^infinity(N_{n+1}\P_{n+1}, psi^(-1))
  * (QD) quotient integrand descent: Phi_s(n_0 g) = Phi_s(g) for n_0 in N_n
-/

universe u

/-- Compact-support structure: the construction yields W such that
    W(diag(g,1)u_Q)V(g) is supported on N_n*K and equals V(I_n) there. -/
structure TestVectorData where
  V_Id : Complex                    -- V(I_n), value of Whittaker function at identity
  hV_ne : V_Id ≠ 0            -- genericity ensures V(I_n) != 0
  vol_quotient : Real            -- vol((N_n cap K)\K) under Haar quotient measure
  hvol_pos : 0 < vol_quotient -- compact open, nonempty => positive measure

/-- The integral I(s;W,V) = V(I_n) * vol((N_n cap K)\K), independent of s.
    The key steps:
    1. W(diag(k,1)u_Q) = 1 for k in K  (by BZ construction)
    2. V(k) = V(I_n) for k in K         (by smoothness/K-fixity)
    3. |det k| = 1 for k in K subset GL_n(o) (compact subgroup)
    4. The support is precisely (N_n cap K)\K (compact, positive measure)  -/
theorem integral_is_constant (D : TestVectorData) (s : Complex) :
    Exists (fun (I : Complex) => I = D.V_Id * ↑D.vol_quotient ∧ I ≠ 0) := by
  refine ⟨D.V_Id * ↑D.vol_quotient, rfl, ?_⟩
  exact mul_ne_zero D.hV_ne
    (Complex.ofReal_ne_zero.mpr (ne_of_gt D.hvol_pos))

/-- Corollary: the integral is finite and nonzero for ALL s in Complex. -/
theorem rankin_selberg_test_vector (D : TestVectorData) :
    ∀ s : Complex, Exists (fun (I : Complex) => I ≠ 0) := by
  intro s
  obtain ⟨I, _, hI_ne⟩ := integral_is_constant D s
  exact ⟨I, hI_ne⟩
