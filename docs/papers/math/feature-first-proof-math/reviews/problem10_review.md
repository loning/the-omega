# Problem 10 Review

- Problem: `Q10`
- Submission Version: `Q10-V2` (full proof)
- Review Version: `Q10-R2`
- Verdict: `PASS`

## Findings

No blocking correctness issues found.

## Verified Core Points

1. Kronecker/vec rewrite to
   `A^*(A_Omega(W)) + lambda K W = K B`
   is dimensionally and algebraically correct.
2. The adjoint formula
   `A^*(Y)=KYZ`
   (with Frobenius inner product and symmetric `K`) is correct.
3. Matrix-free matvec
   `X -> K M_Omega(KXZ^T) Z + lambda KX`
   uses only `(n,r,q,Omega)` and avoids any `N x N` construction.
4. SPD claim is correct under `K` strictly PD and `lambda>0`.
5. Proposed preconditioner
   `P=(G+lambda I_r) \otimes K`, `G=Z^T D Z`
   is valid and applicable without Kronecker expansion.

## Scope Note

For singular `K` (PSD but not PD), strict SPD is not automatic. The draft already states the standard fix (nugget or restricted-range solve). This is not a logical gap.

---

## Opus Review (Q10-R2)

- Reviewer: `claude-4-opus`
- Submission: Full proof in `10_problem10_rkhs_cp_subproblem.tex`
- Verdict: `PASS`

### Verification

1. **Adjoint derivation:** tr(ZX^T K Y) = tr(X^T K Y Z) via cyclic trace. Gives A*(Y) = KYZ. **Correct.**

2. **Matrix-free matvec:** The 5-step algorithm computes T(X) = K M_Omega(KXZ^T) Z + lambda KX using only sparse-Omega operations. Each step's complexity is correctly stated. The critical observation: step 2 computes only q dot products (one per observed entry), avoiding the n×M dense matrix. **Correct.**

3. **SPD proof:** <T(X),X> = ||M_Omega(KXZ^T)||² + lambda tr(X^T K X) > 0 for X≠0 when K≻0 and lambda>0. The first term uses the self-adjointness of projection; the second uses K≻0. **Correct.**

4. **Preconditioner:** P = (G+lambda I_r) ⊗ K with G = Z^T D Z. The Kronecker inverse formula gives P^{-1} vec(R) = vec(K^{-1} R (G+lambda I_r)^{-1}). Cost: O(n²r + nr²) after O(n³ + r³) one-time factorizations. **Correct.**

5. **Complexity:** O(n²r + qr + nr²) per PCG iteration, vs O(n³r³) for direct solve. The improvement is significant when n,r are moderate. **Correct.**

### Conclusion

All five components (adjoint, matvec, SPD, preconditioner, complexity) are rigorous. **PASS.**
