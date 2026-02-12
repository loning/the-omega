# Problem 4 Review

- Problem: `Q4`
- Submission Version: `Q4-V6` (general-n reduction strengthened)
- Review Version: `Q4-R6`
- Verdict: `PARTIAL PASS` (special cases closed; all-`n` reduced to one explicit open bottleneck)

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
9. New: exact reduction from target inequality to weighted quadratic superadditivity `(A)` (Proposition `q4-reductionA`).

## Remaining Open Step

The full all-`n` theorem is now equivalent to proving, for every admissible weight system `w`,
the root-level inequality

`Q_w(gamma(p boxplus_n q)) >= Q_w(lambda(p)) + Q_w(mu(q))`.

This is the unique unresolved bottleneck.

## Conclusion

The manuscript now has a strict and explicit reduction framework for the general case.
Status remains `PARTIAL PASS` because proposition `(A)` is still unproved.
