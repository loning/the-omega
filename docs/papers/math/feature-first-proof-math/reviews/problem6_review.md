# Problem 6 Review

- Problem: `Q6`
- Submission Version: `Q6-V1`
- Review Version: `Q6-R1`
- Verdict: `FAIL`

## Blocking Issues

1. The main statement is not closed: the draft does not prove (or disprove) the universal existence claim
   `exists c>0` such that for every graph and every `epsilon in (0,1)` there is an
   `epsilon`-light set `S` with `|S| >= c * epsilon * |V|`.

## Verified Correct Parts

1. The matching obstruction proving the necessary upper bound `c <= 1/2` is correct.
2. The linearization lemma
   `L_S <= (1/2) * sum_{u in S} L_u`
   and the corollary
   `sum_{u in S} L_u <= 2 epsilon L => L_S <= epsilon L`
   are correct.
