# Problem 9 Review

- Problem: `Q9`
- Submission Version: `Q9-V2`
- Review Version: `Q9-R2`
- Verdict: `FAIL`

## Blocking Issues

1. `Lemma 3.1` is not fully justified for all nonconstant triples `(beta,gamma,delta)`.
   The explicit witness assignment chooses three different camera matrices
   `A^(beta), A^(gamma), A^(delta)` independently.
   This does not cover cases with repeated indices (e.g. `beta=gamma!=delta`),
   where those matrices are not independent objects.
   Since later steps require rank-4 for every nonconstant triple, this gap is blocking.

## Fixed Relative to Q9-R1

1. Diagonal-block issue is repaired by proving `Q^(aaaa) == 0`.
2. Rigidity lemma is now block-consistent (`diag(d_alpha I_3)` with 3D row-space argument).
3. The minor-based construction of `F` has uniform degree `5` and is independent of `A`.

## Required Fix

1. Complete `Lemma 3.1` with a valid argument for repeated-index nonconstant triples,
   e.g. explicit case split (`all distinct`, `exactly two equal`) or a uniform algebraic proof.
