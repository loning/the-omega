import Lake
open Lake DSL

package hyperkernel_min_std where
  -- No external dependencies: Std is shipped with Lean.
  moreServerArgs := #["-DautoImplicit=false"]

@[default_target]
lean_lib HyperKernel

lean_exe hyperkernel where
  root := `Main

lean_exe analyze where
  root := `MainAnalyze
