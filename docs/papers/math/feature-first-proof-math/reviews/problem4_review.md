# Problem 4 Review

- Problem: `Q4`
- Submission Version: `Q4-V5` (consolidated)
- Review Version: `Q4-R5`
- Verdict: `PARTIAL PASS` (n=2 exact, n=3 full, degenerate case; general n open)

## Blocking Issues

1. The full all-`n` inequality remains unproved for n >= 4.
2. This is an intrinsic mathematical difficulty: the n=3 proof relies on an explicit closed-form for 1/Phi_3 as a function of two parameters (A, B), which allows a direct Cauchy--Schwarz argument. For n >= 4, no such closed form exists.

## What Is Proved (Verified)

### 1. Pairwise inverse-square identity (Lemma, all n)
The cancellation of triple sums via the partial-fraction identity 1/((a-b)(a-c)) + cyclic = 0 is correct. This gives Phi_n(p) = 2 sum_{i<j} 1/(lambda_i - lambda_j)^2. **Correct.**

### 2. Exact equality for n=2 (Proposition)
For quadratics: c_1 = a_1+b_1, c_2 = a_2+b_2+(1/2)a_1 b_1. The discriminant is additive: Delta_r = Delta_p + Delta_q. Since 1/Phi_2 = Delta/2, the inequality holds with equality. **Correct. Rigorous.**

### 3. Full inequality for n=3 (Proposition)
After centering (root mean = 0), a centered cubic r(x) = x^3 + Ax + B has:
- 1/Phi_3(r) = Delta(r)/(18A^2) = -2A/9 - (3/2)B^2/A^2.
- Boxplus_3 is additive in (A, B) for centered cubics.
- The difference 1/Phi_3(r) - 1/Phi_3(p) - 1/Phi_3(q) reduces to showing a weighted Jensen/Cauchy inequality for (ux+vy)^2/(u+v)^2 <= x^2 + y^2.
**Correct. Rigorous. Complete proof.**

### 4. Degenerate shift case (Proposition, all n)
If p(x) = (x-a)^n, then p boxplus_n q = q(x-a). Phi_n is translation-invariant, and 1/Phi_n((x-a)^n) = 0. So equality holds. **Correct.**

### 5. Variance additivity under boxplus_n (Proposition, all n)
The empirical variance of roots is additive: Var(p boxplus_n q) = Var(p) + Var(q). Verified via the c_1, c_2 coefficient formulas. **Correct.**

### 6. de Bruijn-type identity (Lemma, all n)
(d/dt) log Disc(p_t) = -4 Phi_n(p_t) under the polynomial heat flow. Derived from lambda_i' = -2 sum_{j≠i} 1/(lambda_i - lambda_j). **Correct.**

## Mathematical Analysis of the Gap

The key difficulty for n >= 4 is:
1. **No closed form for 1/Phi_n:** For n >= 4, 1/Phi_n cannot be expressed as a simple rational function of the coefficients. The n=3 proof crucially uses the explicit formula 1/Phi_3 = -2A/9 - (3/2)B^2/A^2.

2. **Entropy-power analogy:** The remark on the "finite-degree EPI" is mathematically sound: the inequality 1/Phi_n(p boxplus_n q) >= 1/Phi_n(p) + 1/Phi_n(q) is analogous to the entropy-power inequality exp(2h(X+Y)/n) >= exp(2h(X)/n) + exp(2h(Y)/n), with Phi_n playing the role of Fisher information (via the de Bruijn identity) and 1/Disc^{2/n(n-1)} playing the role of entropy power. A proof via this route would require establishing a monotonicity result for Disc under the polynomial heat flow analog of boxplus_n, which is currently open.

3. **Potential route via interlacing polynomials:** The boxplus_n operation preserves real-rootedness (Marcus-Spielman-Srivastava / Borcea-Brändén). Combined with the convexity structure of Phi_n, one might establish the inequality via a barrier argument, but this remains unverified.

## Conclusion

The section provides complete and rigorous proofs for n=2 (with equality), n=3 (with inequality), the degenerate shift case, and important structural results (variance additivity, de Bruijn identity). The general n >= 4 case is left as an identified open problem with a concrete program toward resolution. **PARTIAL PASS.**
