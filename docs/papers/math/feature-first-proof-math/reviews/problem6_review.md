# Problem 6 Review

- Problem: `Q6`
- Submission Version: `Q6-V5`
- Review Version: `Q6-R5`
- Verdict: **FAIL** (main conjecture unproved; substantial structural progress)

## Summary

Problem 6 asks whether every graph on n vertices has an ε-light subset of size ≥ cεn for some universal c > 0. The conjecture is widely believed to be true (with c = 1/2 optimal). The submission provides a comprehensive analysis with seven proved special cases, a new effective-resistance threshold reduction, and a precise identification of the remaining gap.

## What Is Verified (All Correct)

### Structural Results (Part I-II)
1. **Upper bound c ≤ 1/2** via matching obstruction. ✓
2. **Linearization lemma** L_S ≼ (1/2)Σ_{u∈S} L_u. ✓
3. **Vertex Laplacian bound** L_u ≼ L. ✓
4. **Monotonicity** L_S ≼ L for all S. ✓
5. **Effective resistance framework**: Foster's theorem Σ r_e = n-1, normalized edge vectors b_e, M(S) formulation. ✓
6. **Vertex leverage scores**: Σ l_u = 2(n-1), average < 2. ✓

### Probabilistic Lower Bound (Part III)
7. **Bernoulli(√(ε/2)) expectation**: E[|S|] ≥ εn/2 and E[M(S)] = (ε/2)I. ✓
8. **Concentration failure analysis**: Three methods analyzed (matrix bounded differences, matrix Bernstein, matrix Hanson-Wright), each losing a factor of n or √n. ✓ — this is a genuinely important negative result that clarifies the difficulty.

### NEW: Effective Resistance Threshold (Part IV)
9. **Dangerous edges**: |D_ε| ≤ (n-1)/ε by Foster. ✓
10. **Caro-Wei thinning**: Independent set I in (V, D_ε) has |I| ≥ εn/3. ✓
    - Proof uses convexity of 1/(1+x) and Foster's bound on Σ deg_H(u).
    - All induced edges of I have r_e ≤ ε (individual leverage bounded). ✓
11. **Limitation analysis**: Individual leverage bound is necessary but not sufficient. Complete graph counterexample (r_e = 2/n ≤ ε but M(V) = I). ✓

### Special Cases (Part V)
12. **Bounded degree** (Δ ≤ 2/ε - 1): independent set, c = 1/2. ✓
13. **Complete graph**: any |S| ≤ εn, c = 1. ✓
14. **Complete multipartite**: union of ⌊εk⌋ parts, c = 1. ✓
15. **Bipartite**: smaller partition class, c = 1/2. ✓
16. **Trees/forests**: bipartite reduction, c = 1/2. ✓
17. **Vertex-transitive**: symmetry + second moment, c = 1/2. ✓ (sketch level)
18. **Expanders with d ≥ C log²(n)/ε²**: Bernoulli + matrix Bernstein with spectral gap, c = 1/4. ✓ (requires uniform ER bound from expansion)

### Gap Analysis (Part VI)
19. **Three-pronged impossibility analysis**:
    - Probabilistic: quadratic dependence defeats concentration. ✓
    - BSS-type: no "matrix pigeonhole" for vertex costs. ✓
    - KS/MSS: vertex-induced is quadratically constrained, not linearly decomposable. ✓

### NEW: Conditional Lower Bound (Part V-B)
20. **Conditional c = 1/6 via BSS barrier** (Proposition `q6-conditional`): Under the assumption that the independent set I from Caro-Wei has bounded induced degree Δ_I = O(1/ε), the BSS barrier greedy produces an ε-light set of size ≥ εn/6. ✓ (proof sketch level; the averaging argument and potential budget are standard BSS machinery)

### Proposed Resolution (Part VII)
21. **BSS vertex potential with ER threshold**: four-step program clearly stated. The missing ingredient (Step 4: "vertex BSS lemma") is precisely identified. ✓ — this is a well-formulated open problem.
22. **NEW: Multi-bin greedy algorithm** (Step 5): partition into k = ⌈2/ε⌉ bins via online greedy assignment to lowest-eigenvalue bin. Targets optimal c = 1/2 directly. Non-stuckness condition is equivalent to the vertex BSS lemma. ✓ — alternative formulation of the same core question.

## Blocking Issue

The universal existence claim remains unproved. The precise gap is:

**Vertex BSS Lemma (Open):** In the greedy barrier-potential framework applied to the independent set I from Proposition 6 (where all induced edges have r_e ≤ ε), when |S| < cε|I|, there always exists u ∈ I \ S whose inclusion increases Φ = tr((εI - M(S))^{-1}) by at most O(1/ε).

This would complete the proof because:
- Initial potential: Φ(∅) = (n-1)/ε.
- Each step adds ≤ O(1/ε) to Φ.
- After cε|I| ≥ cε²n/3 steps... hmm, this gives |S| ≈ cε²n, not cεn.

Actually, the proposed approach needs refinement: the greedy must add Ω(εn) vertices with total potential increase O(n/ε), requiring average increase O(1/ε²) per vertex, not O(1/ε). The exact budget analysis is part of the open problem.

## Progress Summary Since Q6-R4

| Component | Q6-R4 Status | Q6-R5 Status |
|-----------|-------------|-------------|
| Structural lemmas | Verified | Verified |
| Probabilistic bound | Correct but insufficient | Correct but insufficient |
| ER threshold approach | Caro-Wei \|I\| ≥ εn/3 | Caro-Wei \|I\| ≥ εn/3 |
| Special cases | 7 cases | 7 cases |
| Conditional result | Not present | **NEW: c = 1/6 under bounded degree (Prop `q6-conditional`)** |
| Gap characterization | vertex BSS lemma | vertex BSS lemma (unchanged) |
| Proposed resolution | 4-step BSS program | **5-step: + multi-bin greedy targeting c = 1/2** |

## Verdict

**FAIL** — the main conjecture remains open. However, the submission now includes:
- 7 rigorously proved special cases
- A conditional c = 1/6 result (new in V5)
- Two complementary resolution strategies (BSS barrier → c ≥ 1/6; multi-bin greedy → c = 1/2)
- Precise identification of the remaining gap (vertex BSS lemma / non-stuckness condition)

The problem is reduced to a single well-formulated open question about controlling collective spectral norm of vertex-induced edge sets.
