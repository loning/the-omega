# Problem 3 Review

- Problem: `Q3`
- Review Version: `Q3-R3`
- Verdict: `FAIL`

## Blocking Issues

1. The final stationary formula is proved for unstarred objects `F_\eta(x;1,t), P_\lambda(x;1,t)` (ASEP/Macdonald from the Ayyer--Martin--Williams theorem), while the problem asks for starred interpolation objects `F^*_\mu, P^*_\lambda`. The proof currently does not include a theorem or derivation identifying these two pairs in the required regime, so the target statement is not yet established exactly as asked.

## Required Fixes

1. Add one precise bridge result (with exact citation and hypotheses) that gives
   - either `F^*_\mu(x;1,t)=F_\mu(x;1,t)` and `P^*_\lambda(x;1,t)=P_\lambda(x;1,t)` on your state space/parameter regime,
   - or directly states that your ring inhomogeneous `t`-PushTASEP has stationary law `F^*_\mu/P^*_\lambda`.
2. After adding the bridge, rewrite the final theorem statement and normalization line entirely in starred notation to match Q3 verbatim.
