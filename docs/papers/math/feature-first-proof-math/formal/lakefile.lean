import Lake
open Lake DSL

package «omega-verify» where
  leanOptions := #[⟨`autoImplicit, false⟩]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4" @ "master"

-- Formal proof skeletons for the eight complete solutions (Q1–Q3, Q5, Q7–Q10)
-- and the partial result Q4 (n=2, n=3 cases).
@[default_target]
lean_lib Problem1
@[default_target]
lean_lib Problem2
@[default_target]
lean_lib Problem3
@[default_target]
lean_lib Problem4
@[default_target]
lean_lib Problem5
@[default_target]
lean_lib Problem7
@[default_target]
lean_lib Problem8
@[default_target]
lean_lib Problem9
@[default_target]
lean_lib Problem10

-- Q6 RDI counterexample formalization
@[default_target]
lean_lib Q6Formal
