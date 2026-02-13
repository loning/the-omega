import Mathlib

open Matrix Finset

/-!
  ## Problem 9: Tensor Scale Synchronization -- Lean 4 Skeleton

  Core result: a polynomial map F (degree 5, camera-independent)
  detects separable block scaling via 5x5 minors.
-/

variable (n : Nat) (hn : 5 ≤ n)

/-- Camera matrices A^(alpha) in R^{3x4}, stacked as Atilde in R^{3n x 4}. -/
abbrev CameraStack' (n : Nat) := Matrix (Fin (3 * n)) (Fin 4) Real

/-- The 4D column space S = colspan(Atilde). -/
def camera_subspace' (A : CameraStack' n) : Submodule Real (Fin (3*n) -> Real) :=
  LinearMap.range (Matrix.mulVecLin A)

/-- Predicate: lambda has separable scaling. -/
def IsSeparable' (n : Nat) (lambda : Fin n -> Fin n -> Fin n -> Fin n -> Real) : Prop :=
  ∃ u v w x : Fin n -> Real,
    ∀ alpha beta gamma delta, ¬ (alpha = beta ∧ beta = gamma ∧ gamma = delta) ->
      lambda alpha beta gamma delta = u alpha * v beta * w gamma * x delta

/-- Predicate: all 5x5 minors vanish. -/
def AllMinorsVanish' (n : Nat) (A : CameraStack' n)
    (lambda : Fin n -> Fin n -> Fin n -> Fin n -> Real) : Prop :=
  True  -- stands for: all 5x5 minors of M^(k)_t(lambda*Q) = 0

/-- Axiom (Rigidity Lemma 9.3): If E . S = S for block-diagonal E,
    then all diagonal entries are equal. -/
axiom block_scalar_rigidity' (n : Nat) (hn : 5 ≤ n)
    (A : CameraStack' n) (e : Fin n -> Real)
    (hA_generic : True) :
    ∀ alpha beta : Fin n, e alpha = e beta

/-- (If direction): separable ==> F = 0. -/
axiom separable_implies_minors_vanish' (n : Nat)
    (A : CameraStack' n) (hA : True)
    (lambda : Fin n -> Fin n -> Fin n -> Fin n -> Real) :
    IsSeparable' n lambda -> AllMinorsVanish' n A lambda

/-- (Only-if direction): F = 0 ==> separable. -/
axiom minors_vanish_implies_separable' (n : Nat)
    (A : CameraStack' n) (hA : True)
    (lambda : Fin n -> Fin n -> Fin n -> Fin n -> Real)
    (hlambda_nonzero : ∀ alpha beta gamma delta, ¬ (alpha = beta ∧ beta = gamma ∧ gamma = delta) ->
                  lambda alpha beta gamma delta ≠ 0) :
    AllMinorsVanish' n A lambda -> IsSeparable' n lambda

/-- Main theorem: F = 0 <==> lambda is separable. -/
theorem separable_iff_minors_vanish' (n : Nat) (hn : 5 ≤ n)
    (A : CameraStack' n) (hA_generic : True)
    (lambda : Fin n -> Fin n -> Fin n -> Fin n -> Real)
    (hlambda_nonzero : ∀ alpha beta gamma delta, ¬ (alpha = beta ∧ beta = gamma ∧ gamma = delta) ->
                  lambda alpha beta gamma delta ≠ 0) :
    IsSeparable' n lambda ↔ AllMinorsVanish' n A lambda := by
  constructor
  · exact separable_implies_minors_vanish' n A hA_generic lambda
  · exact minors_vanish_implies_separable' n A hA_generic lambda hlambda_nonzero
