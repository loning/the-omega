# Formal Verification (Lean 4 / Mathlib)

Lean 4 formal proof skeletons for the "First Proof" benchmark solutions.

## Files

| File | Problem | Status |
|------|---------|--------|
| `Problem1.lean`  | Q1: Phi^4_3 measure translation      | **QED** |
| `Problem2.lean`  | Q2: Rankin-Selberg test vector        | **QED** |
| `Problem3.lean`  | Q3: Interpolation ASEP ratio          | **QED** |
| `Problem4.lean`  | Q4: boxplus-Phi inequality (n=2, n=3 + n=4 quartic-delta algebra + denominator-clearing bridge + chamber-plus denominator/quotient interface + factorized-chamber equivalence + B=0 closure + c=0 closure) | Partial |
| `Problem5.lean`  | Q5: O-slice filtration                | **QED** |
| `Problem6.lean`  | Q6: RDI counterexample arithmetic     | Partial |
| `Problem7.lean`  | Q7: Lattices with 2-torsion           | **QED** |
| `Problem8.lean`  | Q8: Polyhedral Lagrangian smoothing   | **QED** |
| `Problem9.lean`  | Q9: Tensor scale synchronization      | **QED** |
| `Problem10.lean` | Q10: RKHS-constrained CP subproblem   | **QED** |

## Methodology

Each file axiomatizes external deep theorems (e.g., regularity structures,
Bernstein-Zelevinsky derivatives, the Farrell-Jones conjecture) and verifies
the logical deduction chain from axioms to the claimed result.

- **8 complete** (Q1-Q3, Q5, Q7-Q10): full deduction chains verified.
- **Q4 partial**: n=2 exact identity, n=3 strict inequality bridge, n=4 quartic `delta` closed-form algebra identity, denominator-clearing reduction `G4 = Xi4/(D1 D2 D12)`, chamber-plus denominator positivity and quotient identity interfaces, factorized-chamber (`D=144LQ`) sign bridge, formal Titu/Engel closure in the quartic `B=0` subfamily, and formal `c=0` closure (including Cauchy mixing bound + monotone-convex `phi` bridge).
- **Q6 partial**: RDI counterexample family arithmetic formalized.

## Build

Requires Lean 4 and Mathlib:

```bash
lake update
lake build
```
