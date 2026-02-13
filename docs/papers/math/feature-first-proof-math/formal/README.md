# q6_formal

Lean4 formalization workspace for Problem Q6 development.

Current checked content:
- `Q6Formal.Basic.ratio_unbounded_nat`
- `Q6Formal.Basic.no_uniform_bound_nat`

These theorems formalize the arithmetic unboundedness step used in the
new counterexample-family argument (RDI route is false).

Build:
```powershell
$env:ELAN_HOME='C:\Users\zwl62\.elan'
$env:HOME='C:\Users\zwl62'
cd C:\OMEGA\the-omega\docs\papers\math\feature-first-proof-math\formal
lake build
```
