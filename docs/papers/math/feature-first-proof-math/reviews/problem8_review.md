# Problem 8 Review

- Problem: `Q8`
- Review Version: `Q8-R1`
- Verdict: `FAIL`

## Blocking Issues

1. The proposed polyhedral surface `K` is not embedded as required. Two non-adjacent faces intersect:
   - Face `conv(T,E2,E3)` and face `conv(B,E4,E1)` meet at
     `P=(9/560, 3/28, -1/4, 3/20)`.
   - Verification by exact barycentric coordinates:
     `P = T + (3/56)(E2-T) + (5/112)(E3-T)` with positive interior coefficients,
     and simultaneously
     `P = B + 0*(E4-B) + (1/4)(E1-B)`.
   Hence the complex is not a topological 2-submanifold, so it does not satisfy the hypothesis of the problem.
2. Because the constructed `K` fails the embedding/submanifold condition, the non-smoothability argument does not establish the required counterexample.

## Required Fixes

1. Replace the current coordinate model by an embedded polyhedral Lagrangian surface with exactly four faces at each vertex, and provide a complete non-self-intersection proof.
2. Then re-run the obstruction argument (Lagrangian sphere in `R^4` implies exactness, contradicting Gromov) on the corrected `K`.
