# Problem 4 Review

- Problem: `Q4`
- Submission Version: `Q4-V11`
- Review Version: `Q4-R11`
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
10. New all-`n` theorem proved for the monotone root-sum model
    `nu_i = lambda_i + mu_i`:
    `1/Phi_n(nu) >= 1/Phi_n(lambda) + 1/Phi_n(mu)`.
11. New exact semigroup identity:
    `H_{2t}(p boxplus_n q) = (H_t p) boxplus_n (H_t q)` for `H_t = exp(t d^2/dx^2)`.
12. New derivative recursion:
    `(d/dx)(p boxplus_n q) = (1/n) (p' boxplus_{n-1} q')`,
    and its iterated `m`-th derivative form.

## Findings From Independent Re-check

1. The bridge `(A)` is too strong and cannot be used as the final closure mechanism.
   Numerical counterexamples exist for `(A)` while `(star)` still appears true on those same inputs.
2. Additional stress tests found no violation of `(star)`:
   random search (`n=4..8`, `6e4` samples per `n`), adversarial local descent for `n=4`, and near-degenerate families.
3. Near `(x-a)^n` inputs, the margin behaves like `+C eps^2` in tested families, consistent with stable equality at the degenerate endpoint.
4. Additional random stress tests up to `n=12` (real-rooted inputs) did not produce violations of `(star)`; observed margins stayed positive.
5. Candidate bridge `1/Phi(roots(p boxplus q)) >= 1/Phi(sort(lambda+mu))` is false numerically and cannot be used for closure.

## Remaining Gap

The all-`n` statement of `(star)` for `n>=4` is still unproved.
Current bottleneck is a weaker global mechanism replacing uniform-in-`w` superadditivity; the new heat-intertwining lemma provides the algebraic backbone for an eventual entropy-power route but does not itself close `(star)`.

## Conclusion

`Q4` remains `PARTIAL PASS`: the section is now internally consistent and technically stronger, but a full all-`n` proof is still missing.
