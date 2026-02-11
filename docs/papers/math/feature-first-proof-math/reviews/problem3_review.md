# Problem 3 Review

- Problem: `Q3`
- Submission Version: `Q3-V8`
- Review Version: `Q3-R8`
- Verdict: `PASS` (original starred question closed as `NO in general`)

## Correctness Check

1. Core logic is now complete:
   a negative value of
   `pi(mu)=F^*_mu(x;1,t)/P^*_lambda(x;1,t)` for one state is enough to rule out existence of any Markov chain with that stationary law.

2. The submission provides a concrete restricted strict partition counterexample
   `lambda=(2,0)` and explicit parameter choice `(t,x1,x2)=(1/2,5,1/2)`, together with symbolic derivation from BDW formulas (`Example 1.16`, `T_1` definition, `Prop. 2.10`, and `P^* = sum F^*`), yielding:
   `P^*_{(2,0)} > 0` and `pi(0,2) < 0`.

3. Therefore the original unconditional Q3 statement is resolved as:
   `NO in general`.

## Accepted Final Position

1. Unconditional answer to original starred Q3: `NO in general` (closed).
2. Previous MH construction remains valid only as a conditional theorem on the positivity domain.
