# Version Registry

This file tracks the latest reviewed version for each problem.

| Problem | Latest Version | Status |
|---|---|---|
| Q1 | Q1-R4 | PASS |
| Q2 | Q2-R5 | PASS |
| Q3 | Q3-R8 | PASS (closed as NO in general via explicit negative-ratio counterexample) |
| Q4 | Q4-R28 | PARTIAL PASS (special cases + monotone-sum all-n theorem + heat intertwining + derivative recursion + transform-factor decomposition closed; edge-score first-moment identity, Hermite Phi formula, scaled-Hermite transform identity, and semi-Gaussian flow identity closed; semi-Gaussian Stam inequality proved for all n via root-ODE/Cauchy integration plus discriminant-partition/continuity closure; first-order step monotonicity fully proved for n=2,3; quadratic-step naive monotonicity falsified by explicit n=4 counterexample; defect-split `A+B` machinery refined with affine-root lift and vertex-space form; NEW convexity identity `nabla^2 V = 6 sum (e_i-e_j)(e_i-e_j)^T/(lambda_i-lambda_j)^4 >= 0` and equivalent `nabla^2 V = L^2 + 2 D^T diag(g) D` close the semi-Gaussian concavity bottleneck (`A+B>=0`); final all-n bridge to arbitrary q remains open) |
| Q5 | Q5-R5 | PASS |
| Q6 | Q6-R3 | FAIL (partial results verified; main existence still open) |
| Q7 | Q7-R5 | FAIL (odd-torsion no-go closed; pure 2-primary case open) |
| Q8 | Q8-R3 | FAIL (YES proof attempt still has local-to-global gaps) |
| Q9 | Q9-R6 | PASS |
| Q10 | Q10-R2 | PASS |

Process rule:
1. New user submission is first written to the corresponding section file in `paper/sections/`.
2. Then a versioned review is written to `reviews/problemX_review.md`.
3. This registry is updated.
