# Version Registry

This file tracks the latest reviewed version for each problem.

| Problem | Latest Version | Status |
|---|---|---|
| Q1 | Q1-R4 | PASS |
| Q2 | Q2-R5 | PASS |
| Q3 | Q3-R8 | PASS (closed as NO in general via explicit negative-ratio counterexample) |
| Q4 | Q4-R42 | PARTIAL PASS (special cases + monotone-sum all-n theorem + heat intertwining + derivative recursion + transform-factor decomposition closed; edge-score first-moment identity, Hermite Phi formula, scaled-Hermite transform identity, and semi-Gaussian flow identity closed; semi-Gaussian Stam inequality proved for all n via root-ODE/Cauchy integration plus discriminant-partition/continuity closure; first-order step monotonicity fully proved for n=2,3; quadratic-step monotonicity falsified by explicit n=4 counterexample and strengthened by an admissible-block counterexample where `(beta,gamma)` comes from a real-rooted `q`; defect-split `A+B` machinery refined with affine-root lift and vertex-space form; convexity identity `nabla^2 V = 6 sum (e_i-e_j)(e_i-e_j)^T/(lambda_i-lambda_j)^4 >= 0` and equivalent `nabla^2 V = L^2 + 2 D^T diag(g) D` close the semi-Gaussian concavity bottleneck (`A+B>=0`); all-n concavity along the semi-Gaussian family `t -> N_n(p boxplus q_t)` promoted to theorem; universal bound `1/Phi_n(p) <= 4 Var(p)/(n(n-1)^2)` proved from `sum lambda_i s_i = n(n-1)/2`; linear two-sided flow control `f_p(0)+C_n t <= f_p(t) <= D_n Var(p)+C_n t` strengthened to exact asymptotic law `f_p(t)=C_n t + D_n Var(p) + O(t^{-1/2})` and exact offset `B_n(p)=D_n Var(p)`; two-scale smoothing factorization `((p boxplus q) boxplus q_{2t})=((p boxplus q_t) boxplus (q boxplus q_t))` closed; two-scale bridge has rigorous tail `lim_{t->infty} J_{p,q}(t)=0`; exact deficit decomposition `J_{p,q}(t)=delta_p(t)+delta_q(t)-delta_{p boxplus q}(2t)` with integral representation of `delta`; exact permutation-average representation of `boxplus_n` and orbit-Jensen reduction established; explicit closed-form upper bound for `avg_pi N(r_pi)` via permutation moments and the variational formula; full-permutation scans up to `n=8` show no orbit-Jensen violation; route eliminations now include (i) local transposition midpoint-Jensen failure on orbit points and (ii) non-monotonicity of `J_{p,q}(t)` via high-precision `n=4` example; **new:** exact heat-deconvolution identity `q=(H_{t/2}q) boxplus q_t`, forward-heat lower estimate `1/Phi_n(q) >= 1/Phi_n(H_{t/2}q)+C_n t` on the real-rooted interval, and survival-time bound `1/Phi_n(q) >= C_n tau_+(q)` with `tau_+(q)=sup{t: H_{t/2}q real-rooted}`; proving `N(p boxplus q) >= avg_pi N(r_pi)` remains the clean final all-n closure target) |
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
