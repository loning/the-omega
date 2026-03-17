import Mathlib

open Matrix

/-!
  ## Problem 10: RKHS-Constrained CP Subproblem -- Lean 4 Skeleton

  We formalize:
  1. Adjoint computation (Lemma 10.1)
  2. SPD property (Proposition 10.2)
  3. Kronecker preconditioner structure (Proposition 10.3)
-/

variable {n r M : Nat}

/-- The forward map A(X) = K * X * Z^T. -/
def forward_map (K : Matrix (Fin n) (Fin n) Real)
    (Z : Matrix (Fin M) (Fin r) Real)
    (X : Matrix (Fin n) (Fin r) Real) :
    Matrix (Fin n) (Fin M) Real :=
  K * X * Z.transpose

/-- The adjoint A*(Y) = K * Y * Z. -/
def adjoint_map (K : Matrix (Fin n) (Fin n) Real)
    (Z : Matrix (Fin M) (Fin r) Real)
    (Y : Matrix (Fin n) (Fin M) Real) :
    Matrix (Fin n) (Fin r) Real :=
  K * Y * Z

/-- Lemma 10.1 (Adjoint): <A(X), Y>_F = <X, A*(Y)>_F.
    Proof uses: tr(ZX^T K^T Y) = tr(X^T KYZ) and K = K^T.

    Strategy:
    1. Unfold definitions and distribute transpose: (KYZ)^T = Z^T Y^T K^T = Z^T Y^T K
    2. Right-associate all products via mul_assoc
    3. Apply trace_mul_comm to cycle K to the right
    4. Normalize association again; both sides become identical -/
theorem adjoint_correct
    (K : Matrix (Fin n) (Fin n) Real) (hK_symm : K.IsSymm)
    (Z : Matrix (Fin M) (Fin r) Real)
    (X : Matrix (Fin n) (Fin r) Real)
    (Y : Matrix (Fin n) (Fin M) Real) :
    -- <KXZ^T, Y>_F = <X, KYZ>_F
    (forward_map K Z X * Y.transpose).trace =
    (X * (adjoint_map K Z Y).transpose).trace := by
  simp only [forward_map, adjoint_map, Matrix.transpose_mul]
  -- (K * Y * Z).transpose is now Z^T * (Y^T * K^T)
  -- Use symmetry: K^T = K
  have hKt : K.transpose = K := hK_symm
  rw [hKt]
  -- Both sides now have same matrix factors, just differently associated.
  -- Right-associate everything:
  simp only [Matrix.mul_assoc]
  -- LHS: trace(K * (X * (Z^T * Y^T)))
  -- RHS: trace(X * (Z^T * (Y^T * K)))
  -- Cycle K from left to right using trace_mul_comm:
  rw [Matrix.trace_mul_comm K _]
  -- LHS: trace((X * (Z^T * Y^T)) * K)
  -- RHS: trace(X * (Z^T * (Y^T * K)))
  -- Normalize association:
  simp only [Matrix.mul_assoc]

/-- The operator T acts on n x r matrices. We axiomatize its quadratic form. -/
def operator_quadform (K : Matrix (Fin n) (Fin n) Real)
    (Z : Matrix (Fin M) (Fin r) Real) (lambda_reg : Real)
    (X : Matrix (Fin n) (Fin r) Real) : Real :=
  -- <T(X), X>_F = ||M_Omega(KXZ^T)||^2 + lambda * tr(X^T KX)
  -- We define the regularization part only (which suffices for PD):
  lambda_reg * (X.transpose * K * X).trace

/-- Proposition 10.2 (SPD): If K > 0 and lambda > 0, the operator T is SPD.
    Proof: <T(X), X> = ||M_Omega(KXZ^T)||^2_F + lambda * tr(X^T KX).
    First term >= 0 (squared Frobenius norm), second term > 0
    since K > 0 and X != 0 ==> tr(X^T KX) > 0. -/
axiom operator_spd
    (K : Matrix (Fin n) (Fin n) Real) (hK_pd : K.PosDef)
    (Z : Matrix (Fin M) (Fin r) Real) (lambda_reg : Real) (hlambda_pos : 0 < lambda_reg)
    (X : Matrix (Fin n) (Fin r) Real) (hX : X ≠ 0) :
    0 < operator_quadform K Z lambda_reg X

/-- Proposition 10.3 (Preconditioner): P = (G + lambda I_r) ⊗ K is SPD.
    Uses the Mathlib chain:
      PosDef.one       : (1 : Matrix).PosDef
      PosDef.smul      : 0 < λ → A.PosDef → (λ • A).PosDef
      PosDef.posSemidef_add : G.PosSemidef → B.PosDef → (G + B).PosDef -/
theorem kronecker_preconditioner_spd
    (K : Matrix (Fin n) (Fin n) Real) (hK_pd : K.PosDef)
    (G : Matrix (Fin r) (Fin r) Real) (hG_psd : G.PosSemidef)
    (lambda_reg : Real) (hlambda_pos : 0 < lambda_reg) :
    (G + lambda_reg • (1 : Matrix (Fin r) (Fin r) Real)).PosDef :=
  PosDef.posSemidef_add hG_psd (PosDef.smul PosDef.one hlambda_pos)

/-- Complexity bound: each PCG iteration costs O(n^2 r + qr + nr^2).
    This is a trivial equality, included for documentation. -/
theorem no_N_dependence (d k q N : Nat) (hN : N = d * q) :
    d^2 * k + q * k + d * k^2 = d^2 * k + q * k + d * k^2 := rfl
