# Problem 5 Review

- Problem: `Q5`
- Review Version: `Q5-R1`
- Verdict: `FAIL`

## Blocking Issues

1. Lemma 5.1 has a core inequality error. From `k|K|\ge n` and `J\le K`, the proof claims `k|J|\ge n`; this is false in general since `|J|\le |K|`. So restriction-preservation at the same slice level is not proved.
2. In the same restriction step, the representation part is mishandled: under restriction to `J=H\cap gKg^{-1}`, one must account for `\rho_{gKg^{-1}}|_J\cong [gKg^{-1}:J]\rho_J`, not just replace by `\rho_J` with the same coefficient. This affects the slice-dimension bookkeeping.
3. Lemma 5.5 is asserted without a complete argument in the `\mathcal O`-incomplete setting. The claim that geometric objects are detected only by `H=G` slice cells needs a rigorous proof (or an exact cited theorem in this setting).
4. The main theorem's reverse implication uses subgroup-size induction but does not formally establish the induction basis/step under the corrected restriction behavior, so the global equivalence is not closed.

## Required Fixes

1. Correct the restriction formula and dimension bookkeeping for slice cells (including representation restriction indices), then re-prove the restriction lemma.
2. Provide a complete proof (or exact theorem citation) for the geometric-piece criterion in the incomplete-transfer `\mathcal O`-stable category.
3. Rebuild the `(2)\Rightarrow(1)` induction with explicit base case and valid subgroup step after Fix 1.
