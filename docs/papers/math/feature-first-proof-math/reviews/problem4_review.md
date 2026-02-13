# Problem 4 Review

- Problem: `Q4`
- Submission Version: `Q4-V27`
- Review Version: `Q4-R37`
- Verdict: `PARTIAL PASS`

## Closed Results

1. Pairwise inverse-square identity for `Phi_n` (all `n`).
2. Full equality for `n=2`.
3. Full inequality for `n=3`.
4. Degenerate shift case `p(x)=(x-a)^n` (all `n`), with equality.
5. Variance additivity under `boxplus_n` (all `n`).
5b. Universal sharp-form upper bound:
    `1/Phi_n(p) <= 4 Var(p)/(n(n-1)^2)` for every real-rooted degree-`n` polynomial
    (proved by the exact identity `sum lambda_i s_i = n(n-1)/2` + Cauchy).
5c. Semi-Gaussian linear two-sided control:
    for `f_p(t)=1/Phi_n(p boxplus q_t)`, constants
    `C_n=4/(n(n-1))`, `D_n=4/(n(n-1)^2)`,
    \[
      f_p(0)+C_n t \le f_p(t)\le D_n Var(p)+C_n t.
    \]
    Hence `f_p(t)-C_n t` is monotone increasing, bounded above, and has finite limit.
5d. Exact asymptotic offset (all `n`):
    \[
      \frac{1}{\Phi_n(p\boxplus q_t)}
      =
      C_n t + D_n Var(p) + O(t^{-1/2}),\quad t\to\infty,
    \]
    so the offset from 5c is exactly `B_n(p)=D_n Var(p)`.
5e. Two-scale bridge tail is now rigorous:
    for
    \[
      J_{p,q}(t)=\frac1{\Phi_n((p\boxplus q)\boxplus q_{2t})}
      -\frac1{\Phi_n(p\boxplus q_t)}
      -\frac1{\Phi_n(q\boxplus q_t)},
    \]
    one has `lim_{t->infty} J_{p,q}(t)=0` (using 5d + variance additivity).
5f. Two-scale smoothing factorization:
    \[
      ((p\boxplus q)\boxplus q_{2t})=((p\boxplus q_t)\boxplus(q\boxplus q_t)),
    \]
    so `J_{p,q}(t)` is exactly the Stam gap of the smoothed pair
    `(p\boxplus q_t,\ q\boxplus q_t)`.
5g. Deficit bridge decomposition (exact):
    with
    `delta_u(t)=D_n Var(u) - (1/Phi_n(u boxplus q_t)-C_n t)`,
    one has
    \[
      J_{p,q}(t)=\delta_p(t)+\delta_q(t)-\delta_{p\boxplus q}(2t),
    \]
    and
    \[
      \delta_u(t)=\int_t^\infty\!\left(\frac{d}{ds}\frac1{\Phi_n(u\boxplus q_s)}-C_n\right)ds.
    \]
5h. Exact permutation-average representation:
    \[
      p\boxplus_n q = \frac1{n!}\sum_{\pi\in S_n}\prod_i \bigl(x-(\lambda_i+\mu_{\pi(i)})\bigr),
    \]
    with a full coefficient-level combinatorial proof.
5i. Orbit-Jensen reduction:
    if one proves
    \[
      \frac1{\Phi_n(p\boxplus q)}\ge \frac1{n!}\sum_\pi \frac1{\Phi_n(r_\pi)},
    \]
    then the full Stam inequality follows immediately by combining with the
    all-`n` monotone-sum theorem on each `r_\pi`.
5j. Orbit-Jensen pressure test:
    full-permutation (not subsampled) scans up to `n=8` found no violation of
    \[
      \frac1{\Phi_n(p\boxplus q)}\ge \frac1{n!}\sum_{\pi}\frac1{\Phi_n(r_\pi)}.
    \]
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
21. New exact defect-split identity:
    concavity numerator equals
    `4[(||s||^2||Ls||^2-(sum g_{ij}^2)^2) + (||s||^2 sum g_{ij}^3-(sum g_{ij}^2)^2)]`,
    i.e. Cauchy-Schwarz defect + signed edge-moment defect.
22. **NEW: Edge-score first-moment identity** (Lemma `q4-edge-score`):
    `sum_{i<j} g_{ij} = Phi_n`. Simple but foundational for the semi-Gaussian proof.
23. **NEW: Hermite Fisher information** (Lemma `q4-hermite-phi`):
    `Phi_n(He_n) = n(n-1)/4`. Computed from the Hermite ODE eigenrelation `s_i = lambda_i/2`.
24. **NEW: Scaled-Hermite transform identity** (Lemma `q4-hermite-transform`):
    `T_n(t^{n/2} He_n(x/sqrt(t))) = n! exp(-t z^2/2)` in `R[z]/(z^{n+1})`.
25. **NEW: Semi-Gaussian flow identity** (Lemma `q4-semi-gauss-flow`):
    `p boxplus_n (t^{n/2} He_n(x/sqrt(t))) = H_{-t/2} p`.
26. **NEW: Semi-Gaussian Stam inequality (all n, unconditional)** (Theorem `q4-semi-gaussian`):
    For every `n >= 2`, `p` monic real-rooted, `s > 0`:
    `1/Phi_n(p boxplus_n sqrt(s) He_n) >= 1/Phi_n(p) + 1/Phi_n(sqrt(s) He_n)`.
    Proof uses backward-heat representation + root ODE + edge-score Cauchy bound,
    then removes temporary simple-root assumptions by discriminant partition + continuity.
    Equality family is verified for scaled Hermite inputs.
27. New explicit working conjecture:
    edge-cubic nonnegativity `sum_{i<j} g_{ij}^3 >= 0` (verified numerically in adversarial search up to tested `n=12`).
28. **NEW: First-order step evidence**:
    for real `alpha` and real-rooted `p`, numerical tests (n=3,4,5,6,8,10)
    support
    `1/Phi_n((I-alpha D)p) >= 1/Phi_n(p)` whenever `(I-alpha D)p` stays real-rooted.
    This is the `N(q_alpha)=0` boundary case with `q_alpha(x)=x^n-n alpha x^{n-1}`.
29. **NEW: Quadratic-step route falsified**:
    direct monotonicity for
    `I - beta D + gamma D^2` (`gamma>0`, `beta^2<4gamma`) is false even on real-rooted inputs/outputs.
    Explicit `n=4` counterexample added in section text.
29b. **NEW: Admissible-block strengthening**:
    the same quadratic-step failure persists when `(beta,gamma)` is not arbitrary
    but comes from an actual complex root pair of `T_n(q)` for a real-rooted `q`.
    So a factor-by-factor closure through quadratic blocks is ruled out even on the
    admissible parameter locus.
30. **NEW: First-order step closed for low degree**:
    proposition `q4-firststep-n23` proves
    `N((I-alpha D)p) >= N(p)` for all real-rooted monic `p` when `n=2,3`.
    (`n=2` by explicit discriminant increment; `n=3` by applying the proved full `n=3` Stam inequality to `q_alpha`.)
31. **NEW: Defect-split identity (exact algebraic decomposition)**:
    with `S1=sum g`, `S2=sum g^2`, `S3=sum g^3`, `rho=S2/S1`,
    the concavity numerator decomposes as
    `A+B`, where
    `A=S1||Ls-rho s||^2 >= 0`
    and
    `B=S1 sum g(g-rho)^2` (signed).
    This isolates the all-`n` bottleneck to balancing a nonnegative Laplacian defect
    against a signed edge-cubic defect.
32. **NEW: Explicit bounded counterexample to the stronger sufficient condition `B>=0`**:
    for `n=8`, a concrete root configuration gives `B<0` while `A+B>0`.
    So `B>=0` is not the right closure target; `A+B>=0` remains the true criterion.
33. **NEW: Incidence-matrix bottleneck form**:
    with weighted edge-incidence `D`, `g=Ds`, `L=D^T D`, `rho=S2/S1`, `h=g-rho*1`,
    the unresolved term is exactly
    `(A+B)/S1 = ||D^T h||^2 + h^T diag(g) h`.
    This recasts general-`n` closure as one signed quadratic-form inequality on `h`.
34. **NEW: Affine-root lift identity**:
    `1 = D lambda`, `g = D s`, hence
    `h = g - rho*1 = D(s-rho*lambda)`.
    So the critical defect vector is always in the cut subspace `Im(D)`.
35. **NEW: Vertex-space form of the bottleneck**:
    with `K = L^2 + D^T diag(g) D` and `v = s-rho*lambda`,
    one has `(A+B)/S1 = v^T K v`.
    So closure reduces to positivity on one specific direction `v`,
    not to global PSD of `K`.
36. **NEW: Convexity of inverse-square interaction**:
    for
    `V(lambda)=sum_{i<j} (lambda_i-lambda_j)^{-2}=Phi_n/2`,
    `nabla^2 V = 6 sum_{i<j} (e_i-e_j)(e_i-e_j)^T/(lambda_i-lambda_j)^4 >= 0`.
37. **NEW: Hessian identity in edge notation**:
    `nabla^2 V = L^2 + 2 D^T diag(g) D`.
38. **NEW: Bottleneck closure**:
    using items 36-37 with `v=s-rho*lambda`,
    `A+2B = S1 * v^T (nabla^2 V) v >= 0`,
    hence `A+B = ((A+2B)+A)/2 >= 0`.
    So the semi-Gaussian concavity algebraic bottleneck is now fully closed.
39. **NEW: Two-scale smoothed-gap bridge candidate recorded**:
    `J_{p,q}(t)=N((p boxplus q) boxplus q_{2t})-N(p boxplus q_t)-N(q boxplus q_t)`,
    where `q_t=sqrt(t)^n He_n(x/sqrt(t))`.
    `J_{p,q}(0)` is exactly the target Stam gap.
    Extensive scans (up to `n=8`) found no negative values on tested `t`-grids.
40. **NEW: All-`n` semi-Gaussian concavity promoted to theorem**:
    `t -> N_n(p boxplus_n q_t)` is now proved concave (simple-root intervals + continuity closure),
    no longer only a conjectural bottleneck for this flow family.

## Findings From Independent Re-check

1. Bridge `(A)` is too strong and cannot be the final closure mechanism.
2. Additional stress tests found no violation of `(star)`:
   random search (`n=4..12`), adversarial local descent near `n=4`, and near-degenerate families.
3. Candidate bridge `1/Phi(roots(p boxplus q)) >= 1/Phi(sort(lambda+mu))` is false numerically.
4. The new sufficient inequality in item (20) is mathematically valid as a sufficient route, but it is too strong in general:
   explicit numerical counterexamples appear already at `n=8`, while the full concavity condition in (18) can still hold on the same root configuration.
5. Direct adversarial search on the exact concavity numerator
   `2(Phi')^2 - Phi'' Phi` (whose positivity would refute concavity)
   found no positive values for tested dimensions `n=8,10,12,14`;
   best values approached `0` from below.
6. The defect decomposition clarifies mechanism:
   failures of item (20) correspond to negative signed edge-moment defect,
   but they can be absorbed by a positive Cauchy-Schwarz defect.
7. Additional search found no negative value for `sum g_{ij}^3` in tested dimensions (up to `n=12`) under random + local minimization.
8. Local minimization confirms `B` can be negative (moderate bounded configurations),
   while the full concavity numerator `A+B` remained positive on the same samples.
9. Section stress-tests explicitly separate:
   `margin` near-zero behavior for `(star)` and signed-defect behavior for `B`,
   consistent with the now-proved `A+B>=0` closure.
10. Structural simplification:
    the troublesome vector is not arbitrary edge data; it has an explicit vertex potential lift
    `s-rho*lambda`. This is now encoded in the section as a proved lemma.
11. High-precision checks on near-collision samples show previously observed negative
    floating-point values of `v^T K v` are numerical artifacts; multiprecision evaluation gives positivity.
12. New bridge observable `J_{p,q}(t)` remains numerically nonnegative in broad tests and decays toward `0`,
    suggesting a plausible final route from semi-Gaussian smoothing back to `t=0`.

## Remaining Gap

The all-`n` statement of `(star)` for arbitrary `p, q` with `n>=4` is still unproved.
Current proved infinite families:
- **n=2**: all `p, q` (equality).
- **n=3**: all `p, q` (strict inequality).
- **All n, shift**: `p = (x-a)^n` (equality).
- **All n, monotone coupling**: `nu_i = lambda_i + mu_i`.
- **All n, semi-Gaussian**: `q = sqrt(s) He_n`.

Current main closure routes:

1. **Bridge route beyond semi-Gaussian concavity:** convert the now-closed concavity block
   into full Stam for arbitrary `q` (the current missing bridge).
2. **Single-bottleneck route (known too strong globally):** the inequality
   `(sum g_{ij}^2)^2 <= (sum g_{ij})(sum g_{ij}^3)`
   implies concavity, but cannot be the final all-`n` closure target.
3. **Score decomposition route:** establish a polynomial Blachman-Stam analogue for `boxplus_n`.
4. **Elementary-step composition route:** the semi-Gaussian Stam combined with the
   transform-factorization (Lemma `q4-transform-factor`) suggests decomposing `p boxplus_n q`
   into elementary steps `(I - alpha_m D)` and proving the inequality inductively.
5. **First-order step route:** prove the one-step monotonicity
   `N((I-alpha D)p) >= N(p)` for all real-rooted admissible steps; combine with a
   factorization regime where `T_n(q)` can be handled without relying on naive quadratic-step monotonicity.

## Conclusion

`Q4` remains `PARTIAL PASS`: `n=2,3` closed for all `(p,q)` (and first-order step fully closed there); semi-Gaussian case closed for all `n`; the semi-Gaussian concavity bottleneck (`A+B>=0`) is now closed; general `n>=4` still needs the final bridge from these blocks to arbitrary `q`.
