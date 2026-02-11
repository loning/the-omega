# Problem 3 Review

- Problem: `Q3`
- Submission Version: `Q3-V7`
- Review Version: `Q3-R7`
- Verdict: `FAIL` (for the original starred question)

## Blocking Issues

1. The proof is conditional on extra assumptions
   `P^*_lambda(x;1,t) > 0` and `F^*_mu(x;1,t) >= 0` for all states.
   These are not derived from the original Q3 hypotheses, so the original problem is not closed.

2. The theorem headline states existence of a `nontrivial` chain, but nontriviality is only shown under an additional support condition (`R(mu,nu)>0` and both weights positive on an edge). Without that condition, the constructed chain can be trivial.

## Accepted Part

1. Conditional result is correct: on a finite state space, if the starred weights are nonnegative and normalized by
   `Z = sum_mu F^*_mu`, the Metropolis--Hastings kernel yields stationarity
   `pi(mu)=F^*_mu/P^*_lambda`.

## Required Fixes

1. Either prove positivity conditions in the target regime or restate the claim as conditional rather than full Q3 closure.
2. If `nontrivial` is part of the theorem statement, add a global assumption guaranteeing at least one positive-mass transition edge, or weaken to existence of a Markov chain.
