# Problem 9 Review

- Problem: `Q9`
- Submission Version: `Q9-V5`
- Review Version: `Q9-R5`
- Verdict: `FAIL` (biconditional not fully closed)

## Verified Correct Parts

1. Reindexing to a global 4-way tensor and Tucker/Levi-Civita structure is correct.
2. Using all `5x5` minors of mode unfoldings as a universal bounded-degree detector candidate is valid.
3. Separable scaling (`lambda = u \otimes v \otimes w \otimes x`) implies vanishing of these minors.

## Blocking Issue

1. The converse direction (minor vanishing implies global separable factorization on all non-identical quadruples) is not fully closed in a strict proof chain in the current manuscript.

## Current Position

Q9 remains partial: strong structural progress and a valid one-way theorem are established, but the full iff statement is still open in this draft.
