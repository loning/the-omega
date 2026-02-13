# Version Registry

This file tracks the latest reviewed version for each problem.

| Problem | Latest Version | Status |
|---|---|---|
| Q1 | Q1-R4 | PASS |
| Q2 | Q2-R5 | PASS |
| Q3 | Q3-R8 | PASS (closed as NO in general via explicit negative-ratio counterexample) |
| Q4 | Q4-R27 | PARTIAL PASS (special cases + monotone-sum all-n theorem + heat intertwining + derivative recursion + transform-factor decomposition closed; added edge-score first-moment identity, Hermite Phi formula, scaled-Hermite transform identity, and semi-Gaussian flow identity; semi-Gaussian Stam inequality proved for all n via explicit root-ODE/Cauchy integration plus discriminant-partition/continuity closure, with scaled-Hermite equality family; first-order step monotonicity fully proved for n=2,3; explicit counterexample shows naive quadratic-step monotonicity fails; exact defect-split identity isolates concavity numerator into nonnegative Laplacian defect + signed edge-cubic defect, with bounded n=8 example showing `B<0` but `A+B>0`; affine-root lift identity `h=D(s-rho lambda)` constrains the bottleneck vector to the cut subspace; new vertex-space reduction `(A+B)/S1 = (s-rho lambda)^T K (s-rho lambda)` with `K=L^2 + D^T diag(g)D`; stress tests separate near-zero `(star)` margins from signed-defect behavior; general boxplus n>=4 still open) |
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
