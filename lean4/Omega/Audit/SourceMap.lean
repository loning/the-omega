namespace Omega.Audit

inductive EntryStatus where
  | planned
  | formalized
  | deferred
  | frontier
  deriving Repr, DecidableEq, Inhabited

structure SourceMapEntry where
  label : String
  sourcePath : String
  moduleName : String
  leanName : String
  phase : Nat
  status : EntryStatus
  deriving Repr, Inhabited

def initialEntries : List SourceMapEntry :=
  [ { label := "engine:no11-truncate"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Core.No11"
      leanName := "Omega.no11_truncate"
      phase := 0
      status := .formalized }
  , { label := "engine:x-restrict"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.StableSyntax"
      leanName := "Omega.X.restrict"
      phase := 0
      status := .formalized }
  , { label := "prop:folding-stable-syntax-fibonacci-count"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.StableSyntax"
      leanName := "Omega.X.card_eq_paperFib_succ"
      phase := 1
      status := .formalized }
  , { label := "prop:folding-stable-syntax-terminal-recursion"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.StableSyntax"
      leanName := "Omega.X.card_recurrence"
      phase := 1
      status := .formalized }
  , { label := "bridge:stable-value-zeck-indices"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Zeckendorf"
      leanName := "Omega.X.stableValue_eq_sum_fib_zeckIndices"
      phase := 2
      status := .formalized }
  , { label := "bridge:stable-word-is-zeckendorf-rep"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Zeckendorf"
      leanName := "Omega.X.zeckIndices_isZeckendorfRep"
      phase := 2
      status := .formalized }
  , { label := "bridge:mathlib-zeckendorf-equiv"
      sourcePath := "mathlib/Data/Nat/Fib/Zeckendorf.lean"
      moduleName := "Omega.Folding.Zeckendorf"
      leanName := "Omega.natZeckendorfEquiv"
      phase := 2
      status := .formalized }
  , { label := "def:fold-word"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fold"
      leanName := "Omega.Fold"
      phase := 3
      status := .formalized }
  , { label := "prop:fold-basic"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fold"
      leanName := "Omega.Fold_surjective"
      phase := 3
      status := .formalized }
  , { label := "prop:fold-rewrite-value-preserving"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.step_value"
      phase := 3
      status := .formalized }
  , { label := "cor:foldm-order-indep-bridge"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.normalPrefix_iota_eq_Fold"
      phase := 3
      status := .formalized }
  , { label := "thm:inverse-limit-golden"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimit"
      leanName := "Omega.X.inverseLimitEquiv"
      phase := 4
      status := .formalized }
  , { label := "def:fold-local-curvature-defect"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.Defect"
      leanName := "Omega.localDefect"
      phase := 4
      status := .formalized }
  , { label := "def:fold-global-stokes-defect"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.Defect"
      leanName := "Omega.globalDefect"
      phase := 4
      status := .formalized }
  , { label := "thm:fold-discrete-stokes-defect"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.Defect"
      leanName := "Omega.globalDefect_eq_defectChain"
      phase := 4
      status := .formalized }
  , { label := "prop:spg-decidable-clopen"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.Clopen"
      leanName := "Omega.SPG.spg_decidableClopen"
      phase := 6
      status := .formalized } ]

end Omega.Audit
