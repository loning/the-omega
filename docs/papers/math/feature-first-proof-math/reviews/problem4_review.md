# Problem 4 Review

- Problem: `Q4`
- Submission Version: `Q4-V15`
- Review Version: `Q4-R15`
- Verdict: `PARTIAL PASS`

## Closed Results

1. Pairwise inverse-square identity for `Phi_n` (all `n`).
2. Full equality for `n=2`.
3. Full inequality for `n=3`.
4. Degenerate shift case `p(x)=(x-a)^n` (all `n`), with equality.
5. Variance additivity under `boxplus_n` (all `n`).
6. de Bruijn-type identity for polynomial heat flow.
7. Differential-operator representation:
   `(p boxplus_n q)(x) = (1/n!) sum_{k=0}^n p^{(k)}(x) q^{(n-k)}(0)`.
8. Variational formula:
   `1/Phi_n(p) = min_{sum w=1} sum w_{ij}^2 (lambda_i-lambda_j)^2`.
9. Sufficient reduction `(A) => (star)` is logically correct.
10. All-`n` theorem for the monotone root-sum model
    `nu_i = lambda_i + mu_i`:
    `1/Phi_n(nu) >= 1/Phi_n(lambda) + 1/Phi_n(mu)`.
11. Heat intertwining identity:
    `H_{2t}(p boxplus_n q) = (H_t p) boxplus_n (H_t q)` for `H_t = exp(t d^2/dx^2)`.
12. Derivative recursion:
    `(d/dx)(p boxplus_n q) = (1/n) (p' boxplus_{n-1} q')`, plus iterated form.
13. Transform-factorization lemma:
    `T_n(p boxplus_n q) = (1/n!) T_n(p)T_n(q)` and decomposition
    `p boxplus_n q = (prod_m (I-alpha_m D))p` after factoring `T_n(q)=n! prod_m (1-alpha_m z)`.
14. Root score ODE (Section 13):
    `d/dt Phi_n(p_t) = 2 sum_{i!=j} (s_i-s_j)^2/(lambda_i-lambda_j)^2 >= 0`.
15. Polynomial entropy power `N_n=1/Phi_n` is linear for `n=2`.
16. Concavity of `N_3(p_t)` for `n=3`.
17. Concavity implies Stam reduction (Costa-style route).
18. Exact concavity-equivalent algebraic condition:
    `(4||Ls||^2 + 4 sum g_{ij}^3)||s||^2 >= 8(sum g_{ij}^2)^2`.
19. New exact identity:
    `sum_{i<j} g_{ij} = ||s||^2 = Phi_n`.
20. New one-inequality sufficient reduction:
    If `(sum g_{ij}^2)^2 <= (sum g_{ij})(sum g_{ij}^3)`, then the full concavity condition in (18) follows.

## Findings From Independent Re-check

1. Bridge `(A)` is too strong and cannot be the final closure mechanism.
2. Additional stress tests found no violation of `(star)`:
   random search (`n=4..12`), adversarial local descent near `n=4`, and near-degenerate families.
3. Candidate bridge `1/Phi(roots(p boxplus q)) >= 1/Phi(sort(lambda+mu))` is false numerically.
4. The new sufficient inequality in item (20) is mathematically valid as a sufficient route, but it is too strong in general:
   explicit numerical counterexamples appear already at `n=8`, while the full concavity condition in (18) can still hold on the same root configuration.

## Remaining Gap

The all-`n` statement of `(star)` for `n>=4` is still unproved.
Current main closure routes:

1. **Entropy power route (Section 13):** prove concavity of `N_n(p_t)` for `n>=4`.
2. **Single-bottleneck route (new, now known too strong globally):** the inequality
   `(sum g_{ij}^2)^2 <= (sum g_{ij})(sum g_{ij}^3)`
   implies concavity, but cannot be the final all-`n` closure target.
3. **Score decomposition route:** establish a polynomial Blachman-Stam analogue for `boxplus_n`.

## Conclusion

`Q4` remains `PARTIAL PASS`: `n=2,3` closed; `n>=4` reduced to precise algebraic bottlenecks.
