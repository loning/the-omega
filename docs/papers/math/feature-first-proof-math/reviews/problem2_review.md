# Problem 2 Review

- Problem: `Q2`
- Review Version: `Q2-R3`
- Verdict: `PASS`

## Blocking Issues

None.

## Required Fixes

None.

---

## Opus Review (Q2-R4)

- Reviewer: `claude-4-opus`
- Verdict: `PASS`

### Line-by-Line Verification

1. **Lemma 1 (Mirabolic restriction, strong form):** The BZ/Kirillov theorem states that for a generic irreducible admissible representation of GL_{n+1}(F), the restriction to the mirabolic subgroup P_{n+1} contains the compactly induced (N_{n+1}, psi^{-1})-equivariant module. This is a standard and well-established result in the theory of p-adic GL_m. Correctly cited as external input.

2. **Lemma 2 (Integrand descent):** Verified. For n_0 in N_n, the embedding diag(n_0, 1) lies in N_{n+1} with the (n, n+1)-superdiagonal entry equal to 0. Thus psi^{-1}(diag(n_0, 1)) = psi^{-1}(n_0) (generic character of N_n). Combined with V(n_0 g) = psi(n_0) V(g) and |det(n_0)| = 1, the characters cancel and Phi_s is N_n-invariant on the left.

3. **Construction of f (lines 74-81):** Verified well-definedness: if n_1 h_1 u_Q = n_2 h_2 u_Q, then n_2^{-1} n_1 = h_2 h_1^{-1} in N_{n+1} cap H, where psi^{-1} is trivial (since K subset G_n(o) and psi has conductor o). The function f is locally constant (p-adic smoothness) because N_{n+1} H u_Q is open and psi^{-1} is locally constant. Compact support mod N_{n+1}: the support is contained in H u_Q, which is compact.

4. **Key structural point:** diag(g, 1) u_Q is in P_{n+1} for all g in G_n. This holds because u_Q = I_{n+1} + Q E_{n,n+1} has the block form (I_n, Q e_n; 0, 1) in P_{n+1}, and P_{n+1} is a group. Therefore W|_{P_{n+1}} = f controls W on the entire domain of integration. This is the non-obvious but correct reason the Kirillov-model argument works.

5. **Support analysis (lines 88-96):** If W(diag(g,1) u_Q) != 0, then diag(g,1) u_Q in N_{n+1} H u_Q, so diag(g,1) = n diag(k,1) for n in N_{n+1}, k in K. Writing n in block form with n_0 in N_n and v in F^n, comparison with diag(g,1) forces v = 0 and g = n_0 k in N_n K. Verified.

6. **Final computation (lines 104-118):** For g = n_0 k: W(diag(g,1) u_Q) = psi^{-1}(n_0), V(g) = psi(n_0) V(I_n), product = V(I_n). Since |det g| = 1 on N_n K (as K subset GL_n(o)), the integral reduces to V(I_n) * vol((N_n cap K) \ K), a nonzero s-independent constant. Verified.

### Conclusion

The proof correctly answers Q2 with YES by explicit construction. The external input (BZ/Kirillov mirabolic restriction) is standard and properly cited. The construction of the compactly-supported equivariant function f, the support analysis via block-matrix comparison, and the constant-integral computation are all rigorous. No gaps, no unjustified steps.
