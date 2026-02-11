# Problem 9 Review

- Problem: `Q9`
- Review Version: `Q9-R1`
- Verdict: `FAIL`

## Blocking Issues

1. The core step in Lemma 4 is not proved: from one block-column family of `\mathcal T_{(1)}` you conclude `D^{(1)}_{\beta\gamma\delta}\,\mathrm{colspan}(C)\subseteq S`. This requires that the corresponding block of `\mathcal Q_{(1)}` spans `\mathrm{colspan}(C)` (rank 4) for each relevant triple `(\beta,\gamma,\delta)`, which is not established.
2. Lemma 3 (diagonal symmetry rigidity) is not valid as written for the block-diagonal form `\mathrm{diag}(e_1 I_3,\dots,e_n I_3)`: the row argument must respect the 3-row block coupling per camera. The current proof treats row scalings as if independently assignable and does not close the generic statement.
3. In the `if` direction, the sentence "diagonal blocks are zeroed but that does not increase mode ranks" is not justified. (This can be repaired if one proves/uses that `Q^{(\alpha\alpha\alpha\alpha)}\equiv 0`, so diagonal values of `\lambda` are irrelevant for `\lambda*Q`.) As written, this step is a logical gap.

## Required Fixes

1. Add a proof that each required block in `\mathcal Q_{(1)}` has rank 4 generically (or replace Lemma 4 by an argument that does not need this claim).
2. Rewrite Lemma 3 with a block-consistent construction/proof for `\mathrm{diag}(e_\alpha I_3)` symmetries.
3. Repair the `if` direction by explicitly handling diagonal blocks (preferably via `Q^{(\alpha\alpha\alpha\alpha)}=0`).
