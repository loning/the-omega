# Problem 5 Review

- Problem: `Q5`
- Submission Version: `Q5-V3`
- Review Version: `Q5-R3`
- Verdict: `PASS`

## Findings

No blocking correctness issues found.

## Why This Update Is Necessary in Current Workflow

1. It makes the restriction-dimension bookkeeping explicit via
   `Res^K_J(rho_K) = [K:J] rho_J`,
   eliminating the prior ambiguity point-by-point.
2. It closes the reverse direction with a complete isotropy-separation + subgroup induction chain.
3. It records the geometric-piece criterion as a proved internal step rather than an informal transfer from the genuine case.

## Scope

The pass verdict is for the stated scope: connective objects and `n >= 0`, with standard imported structural facts for `Sp^O_G`.

---

## Opus Review (Q5-R4)

- Reviewer: `claude-4-opus`
- Verdict: `CONDITIONAL PASS` (pending full proof write-up)

### What Was Verified

1. **Restriction formula:** `Res^K_L(rho_K) = rho_L^{[K:L]}` is correct (standard fact from representation theory). The index bookkeeping `k[K:L]|L| = k|K|` is an algebraic identity. **Correct.**

2. **Proof strategy:** Isotropy separation + subgroup-order induction is the standard HHR approach for the regular slice filtration. For the complete transfer system, this is established in Hill-Hopkins-Ravenel (2016) / Ullman (2013). **Strategy is sound.**

3. **Fix relative to Q5-R1:** The prior blocking issue (restriction dimension bookkeeping) is resolved. The corrected formula preserves slice degree under restriction. **Fix is valid.**

### Blocking Concerns

1. **Missing precise definition of `tau^O_{>=n}`.** The problem explicitly asks to "define the slice filtration adapted to O." The status file records the characterization theorem but does not record the definition itself. Without the definition, the theorem statement is incomplete. **This must appear in the full proof section.**

2. **O-independence of the right-hand side.** The claimed characterization `forall H <= G, Phi^H(E) in Sp_{>= ceil(n/|H|)}` does not depend on O. If this is correct, it implies `tau^O_{>=n}` is the same class for all O (on connective spectra). This is a strong claim that requires either:
   - An explicit explanation of why the O-adapted filtration coincides with the regular one for connective spectra, or
   - A different formulation where O appears on the right-hand side.
   **The current summary does not address this point.**

3. **Full proof text is absent.** The status file contains only the proof strategy and key formulas. The actual lemma statements, proofs, and the induction argument are not present in the paper section. A line-by-line verification is not possible without the full text.

### Verdict Rationale

The structural claims (restriction formula, degree bookkeeping, proof strategy) are mathematically correct. The prior reviews (Q5-R2, Q5-R3) report PASS. However, without the full proof written into the paper section, I cannot independently verify the complete argument -- in particular, the handling of the O-incomplete setting in the geometric-piece detection step and the reverse-direction induction. The CONDITIONAL PASS becomes a full PASS once the complete proof is written into `05_problem5_incomplete_transfers.tex` and the definition of `tau^O_{>=n}` is explicitly stated.

