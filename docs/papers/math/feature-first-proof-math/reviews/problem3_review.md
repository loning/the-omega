# Problem 3 Review

- Problem: `Q3`
- Submission Version: `Q3-V6`
- Review Version: `Q3-R6`
- Verdict: `FAIL` (for the original starred question)

## Blocking Issues

1. The proof adds extra hypotheses
   `P^*_lambda(x;1,t)>0` and `F^*_mu(x;1,t) >= 0` for all states,
   but does not derive them from the original Q3 assumptions.
   Therefore it does not close the original unconditional problem.

2. The theorem claims unconditional existence of a `nontrivial` chain,
   but the given kernel can become trivial in edge cases (e.g. only one positive-mass state with all zero-mass states made absorbing).
   Nontriviality is proved only under an extra support-connectivity condition.

## Accepted Part

1. Conditional statement is correct:
   on a finite state space, if weights are nonnegative and normalized by
   `Z = sum_mu F^*_mu`, a Metropolis--Hastings construction yields a stationary law
   `pi(mu)=F^*_mu/P^*_lambda`.

## Required Fixes

1. Either prove the positivity domain for starred weights in the required regime, or restate the result explicitly as conditional (not as a full solution to original Q3).
2. If nontriviality is required in the theorem statement, provide a kernel that is nontrivial in all admissible cases (or weaken the claim to existence of a Markov chain).
