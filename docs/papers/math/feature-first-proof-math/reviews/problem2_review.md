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
- (Superseded by Q2-R5 below.)

---

## Opus Review (Q2-R5) -- Fresh strict re-audit

- Reviewer: `claude-4-opus`
- Verdict: `PASS`

### Audit Methodology

Independent line-by-line verification of every mathematical claim, re-examining the original question's quantifier structure, all block-matrix identities, the BZ/Kirillov external input, and the final integration.

### Detailed Findings

**1. BZ/Kirillov external input (Lemma 1, lines 16-31).**
The standard Bernstein-Zelevinsky derivative theory + Kirillov model for generic GL_{n+1}(F) guarantees that the restriction of W(Pi, psi^{-1}) to P_{n+1} surjects onto the compactly induced representation c-Ind_{N_{n+1}}^{P_{n+1}} psi^{-1}. Correctly cited. **Minor notation issue:** line 24 writes `f in C_c^infty(P_{n+1})`, but equivariant functions with N_{n+1}-invariant support cannot be compactly supported on P_{n+1} (since N_{n+1} is non-compact). The correct reading is "compactly supported modulo N_{n+1}." The function f constructed later is indeed compactly supported mod N_{n+1}, so the lemma applies. **Non-blocking.**

**2. Integrand descent (Lemma 2, lines 37-54).**
Verified every sub-step:
- diag(n_0 g, 1) = diag(n_0, 1) * diag(g, 1) by block multiplication. Correct.
- diag(n_0, 1) in N_{n+1}: the (i,i+1)-superdiagonal entries are (n_0)_{i,i+1} for i < n and 0 for i = n. Correct.
- psi^{-1}(diag(n_0, 1)) = psi^{-1}(sum_{i=1}^{n-1} (n_0)_{i,i+1}) = psi^{-1}(n_0). Correct.
- Character cancellation psi^{-1}(n_0) * psi(n_0) = 1. Correct.
- |det(n_0 g)| = |det g| since det(n_0) = 1. Correct.

**3. Choice of V and construction of K (lines 63-66).**
pi generic => exists V with V(I_n) != 0. Smoothness gives compact open stabilizer K_0; K = K_0 cap GL_n(o) is nonempty (contains I_n), compact open, and V is constant = V(I_n) on K. Correct.

**4. Triviality of psi on N_{n+1} cap H (line 72).**
K subset GL_n(o) => N_n cap K subset N_n(o). Superdiagonal entries in o. Conductor of psi is o => psi trivial on o. Hence generic character trivial on N_n(o), and on N_{n+1} cap H. Correct.

**5. Well-definedness of f (line 81).**
n_1 h_1 u_Q = n_2 h_2 u_Q. Since u_Q is invertible (u_Q^{-1} = I - Q E_{n,n+1} because E_{n,n+1}^2 = 0), cancel to get n_2^{-1} n_1 = h_2 h_1^{-1} in N_{n+1} cap H. By step 4, psi^{-1}(n_1) = psi^{-1}(n_2). Correct.

**6. Linchpin: diag(g,1) u_Q in P_{n+1} (implicit at line 83-86).**
u_Q has block form (I_n, Q e_n; 0, 1) in P_{n+1}. P_{n+1} is a group (verified: closed under multiplication and inversion). diag(g,1) in P_{n+1}. Product in P_{n+1}. Therefore W|_{P_{n+1}} = f controls W on the entire integration domain. **This is the non-obvious structural key to the proof.** Correct.

**7. Support analysis (lines 88-96).**
If W(diag(g,1) u_Q) != 0, then diag(g,1) u_Q in N_{n+1} H u_Q. Cancel u_Q: diag(g,1) = n * diag(k,1). Block comparison:
- n = (n_0, v; 0, 1), diag(k,1) = (k, 0; 0, 1).
- Product: (n_0 k, v; 0, 1).
- Equals (g, 0; 0, 1), so v = 0, g = n_0 k in N_n K. Correct.

**8. Final computation (lines 104-118).**
- W(diag(n_0 k, 1) u_Q) = psi^{-1}(n_0) * f(diag(k,1) u_Q) = psi^{-1}(n_0) * 1. Correct.
- V(n_0 k) = psi(n_0) V(k) = psi(n_0) V(I_n). Correct.
- Product: V(I_n), constant. Correct.
- |det(n_0 k)| = |det n_0| * |det k| = 1 * 1 = 1 (k in GL_n(o)). Correct.
- I(s; W, V) = V(I_n) * vol((N_n cap K) \ K), nonzero s-independent constant. Correct.

**9. Quantifier structure note.**
The original question introduces pi as part of the "property" of W, which could be read as requiring a single W for all generic pi. The proof constructs W depending on pi (through K and u_Q). However, since u_Q itself depends on the conductor of pi, even the integrand changes with pi. In the Rankin-Selberg literature, the standard interpretation is: given (Pi, pi), find (W, V). The proof correctly addresses this reading. If the stronger universal reading is intended, the proof would need extension, but this interpretation is non-standard and unlikely intended.

### Conclusion

The proof is mathematically rigorous for the standard reading (given Pi and pi, construct W and V). All block-matrix identities, equivariance computations, support arguments, and the final integration are correct. The single minor issue is a notational imprecision in the definition of C_c^infty(N_{n+1} \ P_{n+1}, psi^{-1}) which does not affect any mathematical step. **PASS.**
