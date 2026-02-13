# Formal Verification (Lean 4 / Mathlib)

Lean 4 formal proof skeletons for the "First Proof" benchmark solutions.

## Structure

| File | Problem | Status |
|------|---------|--------|
| `Problem1.lean` | Q1: Phi^4_3 measure translation | **QED** |
| `Problem2.lean` | Q2: Rankin-Selberg test vector | **QED** |
| `Problem3.lean` | Q3: Interpolation ASEP ratio | **QED** |
| `Problem4.lean` | Q4: boxplus-Phi inequality (n=2, n=3) | Partial |
| `Problem5.lean` | Q5: O-slice filtration | **QED** |
| `Problem7.lean` | Q7: Lattices with 2-torsion | **QED** |
| `Problem8.lean` | Q8: Polyhedral Lagrangian smoothing | **QED** |
| `Problem9.lean` | Q9: Tensor scale synchronization | **QED** |
| `Problem10.lean` | Q10: RKHS-constrained CP subproblem | **QED** |
| `Q6Formal/Basic.lean` | Q6: RDI counterexample arithmetic | Partial |

## Methodology

Each `.lean` file **axiomatizes** external deep theorems (e.g., regularity
structures, Bernstein-Zelevinsky derivatives, the Farrell-Jones conjecture)
and **verifies** the logical deduction chain from axioms to the claimed result.
This bridges traditional mathematical proof with machine-checkable formalization.

- **8 complete solutions** (Q1-Q3, Q5, Q7-Q10): full deduction chains verified.
- **Q4 partial**: the n=2 exact identity and n=3 strict inequality are formalized;
  the general semi-Gaussian theorem is proved on paper only.
- **Q6 partial**: arithmetic unboundedness of the RDI counterexample family
  is formalized; the unconditional sqrt(epsilon*n) bound is proved on paper only.

## Build

Requires Lean 4 and Mathlib. To build:

```bash
lake update
lake build
```

Note: first build downloads Mathlib and may take significant time.
