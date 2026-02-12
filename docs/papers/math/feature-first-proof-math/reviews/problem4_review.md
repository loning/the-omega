# Problem 4 Review

- Problem: `Q4`
- Submission Version: `Q4-V6` (general-n reduction strengthened)
- Review Version: `Q4-R6`
- Verdict: `PARTIAL PASS` (special cases closed; current general-`n` bridge remains open)

## What Is Closed

1. Pairwise inverse-square identity for `Phi_n` (all `n`).
2. Full equality for `n=2`.
3. Full inequality for `n=3`.
4. Degenerate shift case `p(x)=(x-a)^n` (all `n`).
5. Variance additivity under `boxplus_n` (all `n`).
6. de Bruijn-type identity for polynomial heat flow.
7. New: differential-operator representation
   `(p boxplus_n q)(x) = (1/n!) sum_{k=0}^n p^{(k)}(x) q^{(n-k)}(0)`.
8. New: variational formula
   `1/Phi_n(p) = min_{sum w=1} sum w_{ij}^2 (lambda_i-lambda_j)^2`.
9. New: exact implication `(A) => (star)` (Proposition `q4-reductionA`), valid as a sufficient route.

## Remaining Open Step

The full all-`n` theorem remains open for `n >= 4`.
The manuscript now explicitly notes that uniform-in-`w` quadratic superadditivity `(A)` is generally too strong (numerically false), so closure must come from a weaker global mechanism.

## Conclusion

The manuscript now has a strict and explicit reduction framework for the general case.
Status remains `PARTIAL PASS` because proposition `(A)` is still unproved.
