import Mathlib

open MeasureTheory Set

universe u
variable {Omega : Type u} [MeasurableSpace Omega]

/-!
  ## Problem 1: Phi^4_3 Measure Translation -- Mutual Singularity

  We axiomatize the deep analytic input (Hairer 2022, Thm 1.1) and
  derive MutuallySingular mu (mu.map T_psi) by pure measure theory.
-/

/-- Hairer's Theorem 1.1 (axiomatized external input).
    For every nonzero smooth psi, there exists a measurable set A
    such that mu(A) = mu(Omega) and mu(A - psi) = 0. -/
structure HairerData (mu : Measure Omega) (T_psi : Omega -> Omega) where
  A : Set Omega
  hA_meas : MeasurableSet A
  hA_full : mu (compl A) = 0
  hA_shift : mu (Set.preimage T_psi A) = 0

/-- Main theorem: mu and T_psi#mu are mutually singular. -/
theorem phi4_mutually_singular
    (mu : Measure Omega)
    (T_psi : Omega -> Omega) (hT : Measurable T_psi)
    (H : HairerData mu T_psi) :
    mu.MutuallySingular (mu.map T_psi) := by
  refine ⟨compl H.A, H.hA_meas.compl, H.hA_full, ?_⟩
  rw [compl_compl, Measure.map_apply hT H.hA_meas]
  exact H.hA_shift

/-- The measures are therefore not equivalent. -/
theorem phi4_not_equivalent
    (mu : Measure Omega)
    (T_psi : Omega -> Omega) (hT : Measurable T_psi)
    (H : HairerData mu T_psi)
    (hmu : mu ≠ 0) :
    ¬ (mu.AbsolutelyContinuous (mu.map T_psi)) := by
  intro h_ac
  have h_sing := phi4_mutually_singular mu T_psi hT H
  exact hmu (Measure.eq_zero_of_absolutelyContinuous_of_mutuallySingular h_ac h_sing)
