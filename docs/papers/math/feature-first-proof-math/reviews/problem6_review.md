# Problem 6 Review

- Problem: `Q6`
- Submission Version: `Q6-V3`
- Review Version: `Q6-R3`
- Verdict: `FAIL` (main existence unproved; structural components verified)

## Blocking Issue

1. The universal existence claim (`exists c > 0, for all G, for all epsilon, exists S epsilon-light with |S| >= c epsilon n`) remains unproved. The probabilistic argument establishes E[L_S] = (epsilon/2)L (factor-of-2 margin), but converting this expectation bound to a spectral-norm bound (lambda_max <= epsilon) requires a concentration argument that overcomes the n-dimensional union bound. Standard tools (matrix Chernoff, Hanson-Wright, matrix Freedman) all lose a factor of n that cannot be absorbed.

## What Is Verified (All Correct)

1. **Matching obstruction c <= 1/2:** For a perfect matching with epsilon < 1, any epsilon-light set includes at most one endpoint per edge, giving c <= 1/2. **Correct.**

2. **Linearization lemma:** L_S <= (1/2) sum_{u in S} L_u, with gap = L_cut >= 0. **Correct.**

3. **Linearization is strictly stronger:** For matchings, linearized condition fails at epsilon < 1/2 for sets of the right size, while L_S = 0 for independent sets trivially. **Correct logical point.**

4. **Effective resistance connection:** tr(L^+ L_S) = sum of effective resistances of internal edges. Foster: sum over all edges = n-1. **Correct.**

5. **Vertex Laplacian bound:** L_u <= L for all u (complement is PSD). **Correct.**

6. **Probabilistic lower bound:** E[L_S] = p^2 L = (epsilon/2)L for p = sqrt(epsilon/2). Markov on trace: P(tr(L^+ L_S) > epsilon n) < 1/2. **Correct but insufficient** (trace controls sum of eigenvalues, not maximum).

7. **Special cases:** Complete, bounded-degree, bipartite graphs. **Correct.**

## Technical Analysis of the Gap

The gap is trace-to-spectral-norm. For random L_S from Bernoulli(p) vertex sampling:
- tr(L^{-1/2} L_S L^{-1/2}) = sum of eigenvalues of L^{-1/2} L_S L^{-1/2}
- lambda_max <= tr (always), but tr can be up to n * lambda_max
- Need: lambda_max <= epsilon (not lambda_max <= epsilon * n)

Closing requires one of:
1. BSS-type deterministic potential argument adapted to vertex (not edge) selection
2. A structural property of induced-subgraph Laplacians that bounds spectral spread
3. An effective-resistance-based sampling scheme with per-edge spectral control

## Recommended Next Step

The most promising route is a BSS-type barrier potential function phi(A) = tr((epsilon L - A)^{-1}) with a greedy vertex-addition algorithm, proving that at least Omega(epsilon n) vertices can be added before the potential diverges. This requires adapting the BSS framework from edge sparsification to vertex selection.
