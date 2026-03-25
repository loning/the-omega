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
      leanName := "Omega.X.card_eq_fib"
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
  , { label := "prop:fold-idempotent"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fold"
      leanName := "Omega.Fold_idempotent"
      phase := 3
      status := .formalized }
  , { label := "prop:fold-basic"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fold"
      leanName := "Omega.Fold_surjective"
      phase := 3
      status := .formalized }
  , { label := "def:fold-fiber"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.fiber"
      phase := 3
      status := .formalized }
  , { label := "cor:fold-fiber-nonempty"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.fiber_nonempty"
      phase := 3
      status := .formalized }
  , { label := "def:fold-fiber-rank"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.rank"
      phase := 3
      status := .formalized }
  , { label := "def:fold-fiber-unrank"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.unrank"
      phase := 3
      status := .formalized }
  , { label := "cor:fold-fiber-rank-unrank"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.rank_unrank"
      phase := 3
      status := .formalized }
  , { label := "cor:fold-fiber-unrank-fold"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.Fold_unrankWord"
      phase := 3
      status := .formalized }
  , { label := "prop:fold-rewrite-value-preserving"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.step_value"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-strong-termination"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.step_stronglyTerminating"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-supported-normal-form"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.irreducible_supported_eq_iota_normalPrefix"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-rtrans-preserves-normalprefix"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.reflTransGen_normalPrefix"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-terminal-exists"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.exists_irreducible_descendant"
      phase := 3
      status := .formalized }
  , { label := "cor:fold-rewrite-irred-unique-on-window"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.irreducible_eq_of_normalPrefix_eq"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-terminal-irred-unique"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.irreducible_terminal_unique"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-terminal-irred-unique-unbounded"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.irreducible_terminal_unique_unbounded"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-confluent"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.step_confluent"
      phase := 3
      status := .formalized }
  , { label := "thm:fold-rewrite-locally-confluent"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.step_locallyConfluent"
      phase := 3
      status := .formalized }
  , { label := "cor:fold-rewrite-terminal-equals-fold"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Folding.Rewrite"
      leanName := "Omega.Rewrite.irreducible_terminal_eq_fold"
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
  , { label := "def:golden-mean-labeled-graph"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Graph.LabeledGraph"
      leanName := "Omega.Graph.LabeledGraph"
      phase := 7
      status := .formalized }
  , { label := "thm:golden-mean-sofic-presentation"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Graph.Sofic"
      leanName := "Omega.Graph.acceptsWord_goldenMean_iff_no11"
      phase := 7
      status := .formalized }
  , { label := "cor:stable-language-explicit-sofic"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Graph.Sofic"
      leanName := "Omega.Graph.stableLanguage_eq_goldenMean"
      phase := 7
      status := .formalized }
  , { label := "prop:spg-decidable-clopen"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.Clopen"
      leanName := "Omega.SPG.spg_decidableClopen"
      phase := 6
      status := .formalized }
  , { label := "def:spg-discrete-scan-error"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-scan-error-boundary-decomposition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_eq_sum_boundary"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-prefix-event-zero-error"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_eq_zero_of_prefixEvent"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-prefix-boundary-decomposition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_eq_sum_boundary"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-prefix-boundary-upper-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_le_boundaryCard_mul"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-prefix-event-empty-boundary"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixBoundaryCells_prefixEvent_eq_empty"
      phase := 6
      status := .formalized }
  , { label := "def:spg-measure-scan-error"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-observable-zero-error"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_observableEvent_eq_zero"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-boundary-decomposition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_eq_sum_boundary"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-measure-boundary-upper-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_le_boundaryCard_mul"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-prefix-boundary-decomposition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixScanErrorMeasure_eq_sum_boundary"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-measure-prefix-boundary-upper-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixScanErrorMeasure_le_boundaryCard_mul"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-measure-prefix-event-zero-error"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixScanErrorMeasure_eq_zero_of_prefixEvent"
      phase := 6
      status := .formalized }
  , { label := "def:spg-measure-observable-purity"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.ObservablePureMeasure"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-purity-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-purity-zero-scan"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_eq_zero_of_observablePure"
      phase := 6
      status := .formalized }
  , { label := "bridge:spg-pmf-to-measure-scan-error"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_toMeasure_eq_scanError"
      phase := 6
      status := .formalized }
  , { label := "bridge:spg-prefix-pmf-to-measure-scan-error"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixScanErrorMeasure_toMeasure_eq_prefixScanError"
      phase := 6
      status := .formalized }
  , { label := "cond:full-generation-certifies"
      sourcePath := "sections/body/frontier/conditional.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fullGeneration_certifies"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-error-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:local-defect-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.localDefect_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:global-defect-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.globalDefect_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-step-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewriteStep_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-irreducible-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableIrreducible_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-zero-scan-certificate"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableZeroScan_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cond:generated-defect-certificate-sound"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.generatedDefectCertificate_sound"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-certificate-sound"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_certificate_sound"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-error-certificate-sound"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_certificate_sound"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-step-certificate-value"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewriteStep_certificate_value"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-certificate-idempotent"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.foldCertificate_idempotent"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-certificate-in-fiber"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.foldCertificate_inFiber"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-zero-scan-certificate-sound"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableZeroScan_certificate_sound"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-zero-scan-certificate-sound"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixZeroScan_certificate_sound"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-idempotent"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_idempotent"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-fixed-on-stable"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_fixedOnStable"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-surjective"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_surjective"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-fiber-nonempty"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_fiber_nonempty"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-fiber-unrank-sound"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_fiber_unrank_sound"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-choose-preimage-sound"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_choosePreimage_sound"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-choose-preimage-in-fiber"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_choosePreimage_inFiber"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-unrank-rank-of-eq"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_unrank_rankOfEq"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-order-independence"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_orderIndependent"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-strong-termination"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_stronglyTerminating"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-confluence"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_confluent"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-local-confluence"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_locallyConfluent"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-value-invariant"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_valueInvariant"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-irreducible-iff-stablecfg"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_irreducible_iff_stableCfg"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-irreducible-same-value-unique"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_irreducible_sameValue_unique"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-fold-irreducible"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_fold_irreducible"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-terminal-exists"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_terminal_exists"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-terminal-unique"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_terminal_unique"
      phase := 8
      status := .formalized }
  , { label := "cond:rewrite-terminal-equals-fold"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.rewrite_terminal_equals_fold"
      phase := 8
      status := .formalized }
  , { label := "cond:inverse-limit-presentation"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.inverseLimitPresentation"
      phase := 8
      status := .formalized }
  , { label := "cond:defect-local-as-global-step"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.localDefect_as_globalStep"
      phase := 8
      status := .formalized }
  , { label := "cond:defect-recursive-step"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.globalDefect_recursive"
      phase := 8
      status := .formalized }
  , { label := "cond:defect-telescope"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.defect_telescope"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-language-sofic"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableLanguage_sofic"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-implies-sofic"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stable_implies_sofic"
      phase := 8
      status := .formalized }
  , { label := "cond:sofic-implies-stable"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.sofic_implies_stable"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-language-set-sofic"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableLanguage_set_sofic"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-point-sofic"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stablePoint_sofic"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-ball-cylinder"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixBall_is_cylinder"
      phase := 8
      status := .formalized }
  , { label := "cond:cylinder-closed-ball"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.cylinder_is_closedBall"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-ball-closed-ball"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixBall_is_closedBall"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-decidable-clopen"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_decidableClopen"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-determined-clopen"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixDetermined_clopen"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-determined-from-wordset"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixDetermined_iff_fromWordSet"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-event-boundary-empty-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableEvent_boundaryEmpty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-event-zero-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableEvent_zero_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-boundary-decomposition-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_boundary_decomposition_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-boundary-mass-bound-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_boundary_mass_bound_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-boundary-card-bound-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_boundary_card_bound_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-zero-boundary-empty-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_zero_of_boundaryEmpty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-pure-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_pure_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-boundary-empty-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_boundaryEmpty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-zero-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_zero_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-error-zero-boundary-empty-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_zero_of_boundaryEmpty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-event-observable-pure-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableEvent_observablePure_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-event-boundary-empty-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableEvent_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-event-zero-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableEvent_zero_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-pure-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_pure_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-boundary-empty-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-zero-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_zero_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-event-observable-pure-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_observablePure_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-pure-iff-boundary-empty-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observablePure_iff_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-zero-iff-observable-pure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_zero_iff_observablePure_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-zero-iff-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_zero_iff_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-observable-pure-iff-boundary-empty-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixObservablePure_iff_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-measure-zero-iff-observable-pure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_zero_iff_observablePure_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-measure-zero-iff-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_zero_iff_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-observable-pure-zero-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixObservablePure_zero_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-pure-zero-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observablePure_zero_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-boundary-decomposition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_measure_boundary_decomposition"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-boundary-mass-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_measure_boundary_mass_bound"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-boundary-card-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_measure_boundary_card_bound"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-zero-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_zero_of_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-measure-boundary-decomposition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_measure_boundary_decomposition"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-measure-boundary-mass-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_measure_boundary_mass_bound"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-measure-boundary-card-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_measure_boundary_card_bound"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-measure-zero-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_zero_of_boundaryEmpty_measure"
      phase := 8
      status := .formalized }
  , { label := "bridge:prefix-scan-measure-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "bridge:boundary-cells-measure-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.boundaryCells_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "bridge:prefix-boundary-cells-measure-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixBoundaryCells_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "bridge:scan-measure-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "bridge:observable-event-measure-discrete-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableEvent_zero_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "bridge:prefix-event-measure-discrete-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_pure_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-zero-scan-certificate"
      sourcePath := "sections/body/frontier/conditional.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixZeroScan_hasCertificate"
      phase := 8
      status := .formalized }
  , { label := "cert:rewrite-step"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Certificates"
      leanName := "Omega.Frontier.RewriteStepCertificate.Valid"
      phase := 8
      status := .formalized }
  , { label := "cert:fold"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Certificates"
      leanName := "Omega.Frontier.FoldCertificate.Valid"
      phase := 8
      status := .formalized }
  , { label := "cert:scan-error"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Certificates"
      leanName := "Omega.Frontier.ScanErrorCertificate.Valid"
      phase := 8
      status := .formalized }
  , { label := "cert:prefix-zero-scan"
      sourcePath := "sections/body/frontier/certificates.tex"
      moduleName := "Omega.Frontier.Certificates"
      leanName := "Omega.Frontier.PrefixZeroScanCertificate.Valid"
      phase := 8
      status := .formalized }
  , { label := "def:spg-discrete-observable-purity"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.ObservablePure"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-discrete-purity-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.observablePure_iff_boundaryCells_eq_empty"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-discrete-zero-iff-pure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_eq_zero_iff_observablePure"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-discrete-zero-iff-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_eq_zero_iff_boundaryCells_eq_empty"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-discrete-complement-symmetry"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_compl"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-discrete-empty-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_empty"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-discrete-univ-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_univ"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-complement-symmetry"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_compl"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-measure-empty-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_empty"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-measure-univ-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_univ"
      phase := 6
      status := .formalized }
  , { label := "cond:scan-error-complement-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_compl_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-empty-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_empty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-univ-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_univ_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:observable-event-pure-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observableEvent_observablePure_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:discrete-pure-iff-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observablePure_iff_boundaryEmpty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:discrete-zero-iff-pure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_zero_iff_observablePure_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:discrete-zero-iff-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_zero_iff_boundaryEmpty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-complement-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_compl_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-empty-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_empty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-univ-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_univ_measure"
      phase := 8
      status := .formalized }
  , { label := "thm:spg-discrete-prefix-zero-iff-pure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_eq_zero_iff_observablePure"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-discrete-prefix-zero-iff-boundary-empty"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_eq_zero_iff_boundaryCells_eq_empty"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-discrete-prefix-complement"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_compl"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-discrete-prefix-empty-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_empty"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-discrete-prefix-univ-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_univ"
      phase := 6
      status := .formalized }
  , { label := "bridge:spg-purity-pmf-to-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.observablePureMeasure_toMeasure_iff_observablePure"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-prefix-complement"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixScanErrorMeasure_compl"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-measure-prefix-empty-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixScanErrorMeasure_empty"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-measure-prefix-univ-zero"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixScanErrorMeasure_univ"
      phase := 6
      status := .formalized }
  , { label := "ineq:sum-min-le-min-sum"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.sum_min_le_min_sum"
      phase := 6
      status := .formalized }
  , { label := "cond:prefix-event-pure-discrete-obs"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixEvent_observablePure_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-zero-iff-pure-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_zero_iff_observablePure_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-zero-iff-boundary-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_zero_iff_boundaryEmpty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-compl-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_compl_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-empty-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_empty_discrete"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-univ-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_univ_discrete"
      phase := 8
      status := .formalized }
  , { label := "bridge:cond-purity-pmf-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observablePure_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-compl-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_compl_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-empty-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_empty_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-univ-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_univ_measure"
      phase := 8
      status := .formalized }
  , { label := "thm:spg-observation-refinement-monotonicity"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_antitone_of_refines"
      phase := 6
      status := .formalized }
  , { label := "cor:spg-prefix-scan-error-monotonicity"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixScanError_antitone"
      phase := 6
      status := .formalized }
  , { label := "cond:observation-refinement-monotonicity"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_antitone_of_refines"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-scan-error-monotonicity"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_antitone"
      phase := 8
      status := .formalized }
  , { label := "thm:spg-cell-event-mass-partition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.cellEventMass_sum_eq_setMass"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-cell-compl-mass-partition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.cellComplMass_sum_eq_setMass_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-cell-mass-total-partition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.cellMass_sum_eq_setMass_univ"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-scan-error-bayes-optimality"
      sourcePath := "sections/body/spg/prop__spg-clarity-bayes-optimality.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.scanError_le_min_setMass"
      phase := 6
      status := .formalized }
  , { label := "thm:spg-measure-scan-error-bayes-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_le_min"
      phase := 6
      status := .formalized }
  , { label := "cond:cell-event-mass-partition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.cellEventMass_partition"
      phase := 8
      status := .formalized }
  , { label := "cond:cell-compl-mass-partition"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.cellComplMass_partition"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-bayes-bound"
      sourcePath := "sections/body/spg/prop__spg-clarity-bayes-optimality.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_bayes_bound"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-scan-error-bayes-bound"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_measure_bayes_bound"
      phase := 8
      status := .formalized }
  , { label := "def:boundary-cylinder-count"
      sourcePath := "sections/body/spg/def__spg-boundary-cylinder-dimension.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.boundaryCylinderCount"
      phase := 6
      status := .formalized }
  , { label := "def:prefix-boundary-cylinder-count"
      sourcePath := "sections/body/spg/def__spg-boundary-cylinder-dimension.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixBoundaryCylinderCount"
      phase := 6
      status := .formalized }
  , { label := "thm:boundary-count-zero-iff-pure"
      sourcePath := "sections/body/spg/cor__spg-clarity-monotonicity.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.boundaryCylinderCount_eq_zero_iff_observablePure"
      phase := 6
      status := .formalized }
  , { label := "thm:scan-error-zero-iff-boundary-count-zero"
      sourcePath := "sections/body/spg/cor__spg-clarity-monotonicity.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.scanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero"
      phase := 6
      status := .formalized }
  , { label := "thm:boundary-count-pmf-bridge"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.boundaryCylinderCount_toMeasure_eq"
      phase := 6
      status := .formalized }
  , { label := "cond:stable-syntax-fibonacci-cardinality"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableSyntax_card_eq_fibonacci"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-syntax-fibonacci-recurrence"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableSyntax_card_recurrence"
      phase := 8
      status := .formalized }
  , { label := "cond:zeckendorf-valid"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableWord_zeckendorf_valid"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-value-fibonacci-sum"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableValue_eq_fibonacci_weighted_sum"
      phase := 8
      status := .formalized }
  , { label := "cond:fold-fiber-card-pos"
      sourcePath := "sections/body/folding/subsec__folding-map.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fold_fiber_card_pos"
      phase := 8
      status := .formalized }
  , { label := "cond:boundary-count-zero-iff-pure"
      sourcePath := "sections/body/spg/def__spg-boundary-cylinder-dimension.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.boundaryCylinderCount_zero_iff_pure_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:scan-error-zero-iff-boundary-count-zero"
      sourcePath := "sections/body/spg/cor__spg-clarity-monotonicity.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_zero_iff_boundaryCylinderCount_zero_measure"
      phase := 8
      status := .formalized }
  , { label := "cond:boundary-count-pmf-bridge"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.boundaryCylinderCount_measure_discrete_bridge"
      phase := 8
      status := .formalized }
  , { label := "cond:measure-antitone-observation-refinement"
      sourcePath := "sections/body/spg/cor__spg-clarity-monotonicity.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.scanError_measure_antitone_via_bridge"
      phase := 8
      status := .formalized }
  , { label := "cond:prefix-measure-antitone"
      sourcePath := "sections/body/spg/cor__spg-clarity-monotonicity.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixScanError_measure_antitone_via_bridge"
      phase := 8
      status := .formalized }
  , { label := "thm:cell-partition-identity"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.cellEventMass_add_cellComplMass_eq_cellMass"
      phase := 6
      status := .formalized }
  , { label := "cond:stable-value-injective"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableValue_injective"
      phase := 8
      status := .formalized }
  , { label := "cond:stable-value-ofnat-roundtrip"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.stableValue_ofNat_roundtrip"
      phase := 8
      status := .formalized }
  , { label := "cond:cell-partition-identity"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.cellEventMass_add_cellComplMass_partition"
      phase := 8
      status := .formalized }
  -- Fiber partition & word cardinality
  , { label := "thm:word-card"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.Word_card"
      phase := 1
      status := .formalized }
  , { label := "thm:fiber-card-sum"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.fiber_card_sum"
      phase := 3
      status := .formalized }
  , { label := "thm:fiber-card-sum-eq-pow"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Fiber"
      leanName := "Omega.X.fiber_card_sum_eq_pow"
      phase := 3
      status := .formalized }
  , { label := "cond:fiber-card-partition"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fiber_card_partition"
      phase := 9
      status := .formalized }
  , { label := "cond:fiber-card-partition-pow"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.fiber_card_partition_pow"
      phase := 9
      status := .formalized }
  -- Phase 9: complement symmetry & cell-level measure bounds
  , { label := "thm:observable-pure-compl-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.observablePure_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:boundary-cells-compl-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.boundaryCells_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:prefix-boundary-cells-compl-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorDiscrete"
      leanName := "Omega.SPG.prefixBoundaryCells_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:cell-event-measure-le"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.cellEventMeasure_le_cellMeasure"
      phase := 6
      status := .formalized }
  , { label := "thm:cell-compl-measure-le"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.cellComplMeasure_le_cellMeasure"
      phase := 6
      status := .formalized }
  , { label := "thm:cell-partition-identity-measure"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.cellEventMeasure_add_cellComplMeasure_eq_cellMeasure"
      phase := 6
      status := .formalized }
  , { label := "thm:observable-pure-compl-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.observablePureMeasure_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:boundary-cells-compl-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.boundaryCellsMeasure_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:boundary-cylinder-count-compl"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.boundaryCylinderCount_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:prefix-boundary-cells-compl-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixBoundaryCellsMeasure_compl"
      phase := 6
      status := .formalized }
  , { label := "thm:prefix-boundary-cylinder-count-compl"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.SPG.ScanErrorMeasure"
      leanName := "Omega.SPG.prefixBoundaryCylinderCount_compl"
      phase := 6
      status := .formalized }
  , { label := "cond:observable-pure-compl-symmetric-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observablePure_compl_symmetric_discrete"
      phase := 9
      status := .formalized }
  , { label := "cond:boundary-cells-compl-symmetric-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.boundaryCells_compl_symmetric_discrete"
      phase := 9
      status := .formalized }
  , { label := "cond:prefix-boundary-cells-compl-symmetric-discrete"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixBoundaryCells_compl_symmetric_discrete"
      phase := 9
      status := .formalized }
  , { label := "cond:observable-pure-compl-symmetric-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.observablePure_compl_symmetric_measure"
      phase := 9
      status := .formalized }
  , { label := "cond:boundary-cells-compl-symmetric-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.boundaryCells_compl_symmetric_measure"
      phase := 9
      status := .formalized }
  , { label := "cond:boundary-cylinder-count-compl-symmetric-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.boundaryCylinderCount_compl_symmetric_measure"
      phase := 9
      status := .formalized }
  , { label := "cond:prefix-boundary-cells-compl-symmetric-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixBoundaryCells_compl_symmetric_measure"
      phase := 9
      status := .formalized }
  , { label := "cond:prefix-boundary-cylinder-count-compl-symmetric-measure"
      sourcePath := "sections/body/spg/sec__spg.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.prefixBoundaryCylinderCount_compl_symmetric_measure"
      phase := 9
      status := .formalized }
  , { label := "cond:cell-event-measure-le"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.cellEventMeasure_le_cell"
      phase := 9
      status := .formalized }
  , { label := "cond:cell-compl-measure-le"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.cellComplMeasure_le_cell"
      phase := 9
      status := .formalized }
  , { label := "cond:cell-partition-identity-measure"
      sourcePath := "sections/body/spg/prop__spg-cylinder-decomposition.tex"
      moduleName := "Omega.Frontier.Conditional"
      leanName := "Omega.Frontier.cellPartition_identity_measure"
      phase := 9
      status := .formalized }
  -- Phase 10: Carry Defect (Plan 3)
  , { label := "aux:fib-succ-add-fib-eq"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.fib_succ_add_fib_eq"
      phase := 10
      status := .formalized }
  , { label := "aux:fib-sub-eq"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.fib_sub_eq"
      phase := 10
      status := .formalized }
  , { label := "aux:fib-lt-fib-succ-succ"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.fib_lt_fib_succ_succ"
      phase := 10
      status := .formalized }
  , { label := "thm:pom-stable-addition-carry-defect-unique-element"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.stableValue_restrict_stableAdd_carry"
      phase := 10
      status := .formalized }
  , { label := "thm:pom-stable-addition-carry-defect-unique-element-word"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.restrict_stableAdd_carry_defect"
      phase := 10
      status := .formalized }
  , { label := "cor:pom-carry-defect-m6-anchor-8-34"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.carryElement_m6_value"
      phase := 10
      status := .formalized }
  , { label := "cor:pom-carry-defect-m5-value"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.carryElement_m5_value"
      phase := 10
      status := .formalized }
  , { label := "cor:pom-carry-defect-m7-value"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.carryElement_m7_value"
      phase := 10
      status := .formalized }
  , { label := "prop:pom-carry-element-nonzero"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.CarryDefect"
      leanName := "Omega.X.carryElement_ne_zero"
      phase := 10
      status := .formalized }
  -- Phase 11: FiberFusion (Plan 7)
  -- lem:pom-fib-fusion-submultiplicativity → fib_fusion, fib_prod_lt_fib_fusion,
  --   fib_fusion_lt_fib_sum, fib_prod_lt_fib_sum (Omega/Folding/FiberFusion.lean)
  -- 状态: 已形式化, 审核通过 2026-03-22
  , { label := "lem:pom-fib-fusion-submultiplicativity"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_fusion"
      phase := 11
      status := .formalized }
  , { label := "lem:pom-fib-fusion-submultiplicativity-prod-lt-fusion"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_prod_lt_fib_fusion"
      phase := 11
      status := .formalized }
  , { label := "lem:pom-fib-fusion-submultiplicativity-fusion-lt-sum"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_fusion_lt_fib_sum"
      phase := 11
      status := .formalized }
  , { label := "lem:pom-fib-fusion-submultiplicativity-prod-lt-sum"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_prod_lt_fib_sum"
      phase := 11
      status := .formalized }
  -- cor:pom-fib-component-fusion-gain → fib_component_fusion_lt,
  --   fib_component_fusion_gain, fib_component_fusion_gain_lower,
  --   fib_component_fusion_gain_ge (Omega/Folding/FiberFusion.lean)
  -- 状态: 已形式化, 审核通过 2026-03-22
  , { label := "cor:pom-fib-component-fusion-gain"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_component_fusion_lt"
      phase := 11
      status := .formalized }
  , { label := "cor:pom-fib-component-fusion-gain-bound"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_component_fusion_gain"
      phase := 11
      status := .formalized }
  , { label := "cor:pom-fib-component-fusion-gain-lower"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_component_fusion_gain_lower"
      phase := 11
      status := .formalized }
  , { label := "cor:pom-fib-component-fusion-gain-ge"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberFusion"
      leanName := "Omega.X.fib_component_fusion_gain_ge"
      phase := 11
      status := .formalized }
  -- Phase 12: MaxFiber (Plan 8)
  -- def:pom-top-fiber-spectrum → X.maxFiberMultiplicity (Omega/Folding/MaxFiber.lean:19)
  -- thm:pom-max-fiber (partial: 递推上界) → X.maxFiberMultiplicity_achieved (line:22)
  --                                       → X.fiberMultiplicity_le_max    (line:27)
  --                                       → X.maxFiberMultiplicity_pos    (line:31)
  --                                       → X.maxFiberMultiplicity_le_add (line:271)
  -- cor:pom-D-rec (base values D_0..D_10) → X.maxFiberMultiplicity_zero..ten (lines:108-118)
  -- 辅助引理: restrict_ofNat (line:6), restrict_Fold_snoc_false (line:9),
  --           snoc_truncate_last (line:119), weight_lt_fib (line:126),
  --           weight_expand (line:139), ofNat_add_fib (line:151),
  --           ofNat_ne_of_shift (line:194), fib_le_of_mem_zeckendorf (line:187)
  -- 状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-top-fiber-spectrum"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity"
      phase := 12
      status := .formalized }
  , { label := "thm:pom-max-fiber-achieved"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_achieved"
      phase := 12
      status := .formalized }
  , { label := "thm:pom-max-fiber-le-max"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.fiberMultiplicity_le_max"
      phase := 12
      status := .formalized }
  , { label := "thm:pom-max-fiber-pos"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_pos"
      phase := 12
      status := .formalized }
  , { label := "thm:pom-max-fiber-recurrence-upper-bound"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_le_add"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-zero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_zero"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_one"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-two"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_two"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-three"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_three"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-four"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_four"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-five"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_five"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-six"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_six"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-seven"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_seven"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-eight"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_eight"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-nine"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_nine"
      phase := 12
      status := .formalized }
  , { label := "cor:pom-D-rec-base-ten"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.X.maxFiberMultiplicity_ten"
      phase := 12
      status := .formalized }
  -- Phase 13: ModularTower (Plan 4)
  -- thm:pom-modular-tower → modularProject_eq_restrict, modularProject_stableAdd_carry,
  --   stableValue_modularProject_stableMul, stableValue_restrict_stableMul,
  --   restrict_comp_restrict, tower_compatible, restrict_tower_transitivity,
  --   modularProject_stableZero, stableValue_modularProject_stableAdd_carry,
  --   stableValue_modularProject_compose, carryIndicator_comm,
  --   modularProject_tower_surjective (Omega/Folding/ModularTower.lean)
  -- 状态: 已形式化, 审核通过 2026-03-22
  , { label := "thm:pom-modular-project-eq-restrict"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.modularProject_eq_restrict"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-modular-project-carry-defect"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.modularProject_stableAdd_carry"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-modular-project-mul-value"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.stableValue_modularProject_stableMul"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-restrict-mul-value"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.stableValue_restrict_stableMul"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-restrict-comp-restrict"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.restrict_comp_restrict"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-tower-compatible"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.tower_compatible"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-restrict-tower-transitivity"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.restrict_tower_transitivity"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-modular-project-zero"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.modularProject_stableZero"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-modular-project-add-carry-value"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.stableValue_modularProject_stableAdd_carry"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-modular-project-compose-value"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.stableValue_modularProject_compose"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-carry-indicator-comm"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.carryIndicator_comm"
      phase := 13
      status := .formalized }
  , { label := "thm:pom-modular-tower-surjective"
      sourcePath := "sections/body/pom/subsec__pom-stable-addition.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.modularProject_tower_surjective"
      phase := 13
      status := .formalized }
  -- Phase 14: TransferMatrix (Plan 19)
  -- thm:fold-suite item 3（基数递推 = 特征多项式）
  -- subsec:folding-stable-compression（golden-mean sofic 邻接矩阵）
  -- goldenMeanAdjacency 定义, 条目验证, Cayley-Hamilton A²=A+I,
  --   tr(A)=1, det(A)=-1 (Omega/Graph/TransferMatrix.lean)
  -- 状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:golden-mean-adjacency-matrix"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency"
      phase := 14
      status := .formalized }
  , { label := "prop:golden-mean-adjacency-entry-00"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_entry_00"
      phase := 14
      status := .formalized }
  , { label := "prop:golden-mean-adjacency-entry-01"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_entry_01"
      phase := 14
      status := .formalized }
  , { label := "prop:golden-mean-adjacency-entry-10"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_entry_10"
      phase := 14
      status := .formalized }
  , { label := "prop:golden-mean-adjacency-entry-11"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_entry_11"
      phase := 14
      status := .formalized }
  , { label := "thm:fold-suite-item3-cayley-hamilton"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_sq"
      phase := 14
      status := .formalized }
  , { label := "prop:golden-mean-adjacency-trace"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_trace"
      phase := 14
      status := .formalized }
  , { label := "prop:golden-mean-adjacency-det"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_det"
      phase := 14
      status := .formalized }
  -- Phase 21: TransferMatrix — Perron-Frobenius 维度（阶段性通过）
  -- thm:golden-mean-pf-root-eq-phi → goldenMeanAdjacency_pf_root_eq_goldenRatio (TransferMatrix.lean:305)
  -- lem:golden-mean-has-phi-eigenvector → goldenMeanAdjacency_has_goldenRatio_eigenvector (TransferMatrix.lean:218)
  -- aux:golden-mean-charpoly-eval-phi → goldenMeanAdjacency_charpoly_eval_goldenRatio (TransferMatrix.lean:228)
  -- aux:golden-mean-charpoly-eval-psi → goldenMeanAdjacency_charpoly_eval_goldenConj (TransferMatrix.lean:233)
  -- aux:golden-mean-adjacency-real-square → goldenMeanAdjacencyℝ_sq (TransferMatrix.lean:238)
  -- lem:golden-mean-real-eigenvalue-quadratic → eigenvalue_satisfies_quadratic (TransferMatrix.lean:245)
  -- lem:golden-mean-real-eigenvalue-classification → eigenvalue_eq_goldenRatio_or_goldenConj (TransferMatrix.lean:277)
  -- lem:golden-conj-abs-lt-phi → goldenConj_abs_lt_goldenRatio (TransferMatrix.lean:287)
  -- prop:golden-mean-real-eigenvalues-bounded-by-phi → goldenMeanAdjacency_dominates_all_real_eigenvalues (TransferMatrix.lean:295)
  -- 状态: 已形式化, 审核通过 2026-03-25（阶段性；spectral radius / PF dimension API 待补）
  , { label := "lem:golden-mean-has-phi-eigenvector"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_has_goldenRatio_eigenvector"
      phase := 21
      status := .formalized }
  , { label := "aux:golden-mean-charpoly-eval-phi"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_charpoly_eval_goldenRatio"
      phase := 21
      status := .formalized }
  , { label := "aux:golden-mean-charpoly-eval-psi"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_charpoly_eval_goldenConj"
      phase := 21
      status := .formalized }
  , { label := "aux:golden-mean-adjacency-real-square"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacencyℝ_sq"
      phase := 21
      status := .formalized }
  , { label := "lem:golden-mean-real-eigenvalue-quadratic"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.eigenvalue_satisfies_quadratic"
      phase := 21
      status := .formalized }
  , { label := "lem:golden-mean-real-eigenvalue-classification"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.eigenvalue_eq_goldenRatio_or_goldenConj"
      phase := 21
      status := .formalized }
  , { label := "lem:golden-conj-abs-lt-phi"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenConj_abs_lt_goldenRatio"
      phase := 21
      status := .formalized }
  , { label := "prop:golden-mean-real-eigenvalues-bounded-by-phi"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_dominates_all_real_eigenvalues"
      phase := 21
      status := .formalized }
  , { label := "thm:golden-mean-pf-root-eq-phi"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pf_root_eq_goldenRatio"
      phase := 21
      status := .formalized }
  -- Phase 23: 逆极限拓扑结构
  -- thm:fold-suite item 3 (逆极限拓扑，部分：compact + totally disconnected)
  --   → isClosed_no11Inf (Omega/Folding/InverseLimitTopology.lean:7)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:fold-suite-item3-topo-closed"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimitTopology"
      leanName := "Omega.X.isClosed_no11Inf"
      phase := 23
      status := .formalized }
  -- thm:inverse-limit-golden (XInfinity 拓扑性质，部分：compact)
  --   → CompactSpace XInfinity (Omega/Folding/InverseLimitTopology.lean:19)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:inverse-limit-golden-compact"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimitTopology"
      leanName := "Omega.X.CompactSpace XInfinity"
      phase := 23
      status := .formalized }
  -- thm:inverse-limit-golden (XInfinity 拓扑性质，部分：totally disconnected)
  --   → TotallyDisconnectedSpace XInfinity (Omega/Folding/InverseLimitTopology.lean:23)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:inverse-limit-golden-totally-disconnected"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimitTopology"
      leanName := "Omega.X.TotallyDisconnectedSpace XInfinity"
      phase := 23
      status := .formalized }
  -- thm:inverse-limit-golden (XInfinity 拓扑性质：可度量化)
  --   → MetricSpace XInfinity (Omega/Folding/InverseLimitTopology.lean:28)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:inverse-limit-golden-metrizable"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimitTopology"
      leanName := "Omega.X.MetricSpace XInfinity"
      phase := 23
      status := .formalized }
  -- thm:inverse-limit-golden (XInfinity 拓扑性质：有居民)
  --   → Inhabited XInfinity (Omega/Folding/InverseLimitTopology.lean:33)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:inverse-limit-golden-inhabited"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimitTopology"
      leanName := "Omega.X.Inhabited XInfinity"
      phase := 23
      status := .formalized }
  -- thm:inverse-limit-golden (XInfinity 拓扑性质：无限)
  --   → Infinite XInfinity (Omega/Folding/InverseLimitTopology.lean:37)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:inverse-limit-golden-infinite"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimitTopology"
      leanName := "Omega.X.Infinite XInfinity"
      phase := 23
      status := .formalized }
  -- Phase 20前置: Shift 动力系统基础
  -- cor:pom-shift-conjugacy-on-godel-image (shift 定义)
  --   → shift (Omega/Folding/ShiftDynamics.lean:7)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:pom-shift-conjugacy-on-godel-image"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift"
      phase := 20
      status := .formalized }
  -- sofic shift 动力系统基础：shift 连续性
  --   → continuous_shift (Omega/Folding/ShiftDynamics.lean:11)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:shift-continuous"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.continuous_shift"
      phase := 20
      status := .formalized }
  -- sofic shift 动力系统基础：shift 满射性
  --   → shift_surjective (Omega/Folding/ShiftDynamics.lean:17)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:shift-surjective"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift_surjective"
      phase := 20
      status := .formalized }
  -- sofic shift 动力系统基础：坐标展开引理
  --   → shift_val (Omega/Folding/ShiftDynamics.lean:31)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "lem:shift-val"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift_val"
      phase := 20
      status := .formalized }
  -- Phase 2: Fibonacci 素数域 (Plan 2)
  -- cor:field-phase-fib-prime (F_{m+2} 素数时乘法逆存在)
  --   → stableMul_inv_of_prime (Omega/Folding/FibonacciField.lean:18)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-inv"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FibonacciField"
      leanName := "Omega.X.stableMul_inv_of_prime"
      phase := 2
      status := .formalized }
  -- cor:field-phase-fib-prime (F(3)=3 素数验证)
  --   → fib_four_prime (Omega/Folding/FibonacciField.lean:7)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-3"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FibonacciField"
      leanName := "Omega.fib_four_prime"
      phase := 2
      status := .formalized }
  -- cor:field-phase-fib-prime (F(4)=5 素数验证)
  --   → fib_five_prime (Omega/Folding/FibonacciField.lean:8)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-4"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FibonacciField"
      leanName := "Omega.fib_five_prime"
      phase := 2
      status := .formalized }
  -- cor:field-phase-fib-prime (F(6)=13 素数验证)
  --   → fib_seven_prime (Omega/Folding/FibonacciField.lean:9)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-6"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FibonacciField"
      leanName := "Omega.fib_seven_prime"
      phase := 2
      status := .formalized }
  -- cor:field-phase-fib-prime (F(8)=34 非素数验证)
  --   → fib_nine_not_prime (Omega/Folding/FibonacciField.lean:10)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-8-neg"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FibonacciField"
      leanName := "Omega.fib_nine_not_prime"
      phase := 2
      status := .formalized }
  -- cor:field-phase-fib-prime (F(12)=233 素数验证)
  --   → fib_thirteen_prime (Omega/Folding/FibonacciField.lean:11)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-12"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FibonacciField"
      leanName := "Omega.fib_thirteen_prime"
      phase := 2
      status := .formalized }
  -- Phase 8: Fibonacci 界 + momentSum (Round 8)
  -- Fibonacci 压缩率隐含引理 → fib_le_pow_two (Omega/Core/Fib.lean:129)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "fib-growth-upper-bound"
      sourcePath := "sections/body/folding/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Core.Fib"
      leanName := "Omega.fib_le_pow_two"
      phase := 8
      status := .formalized }
  -- subsec:op_algebra_complexity → momentSum 定义 (Omega/Folding/MomentSum.lean:6)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "subsec:op_algebra_complexity-momentSum"
      sourcePath := "sections/body/folding/subsec__op-algebra-complexity.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum"
      phase := 8
      status := .formalized }
  -- subsec:op_algebra_complexity → momentSum_zero (Omega/Folding/MomentSum.lean:10)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "subsec:op_algebra_complexity-momentSum-zero"
      sourcePath := "sections/body/folding/subsec__op-algebra-complexity.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_zero"
      phase := 8
      status := .formalized }
  -- subsec:op_algebra_complexity → momentSum_one (Omega/Folding/MomentSum.lean:15)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "subsec:op_algebra_complexity-momentSum-one"
      sourcePath := "sections/body/folding/subsec__op-algebra-complexity.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_one"
      phase := 8
      status := .formalized }
  -- subsec:op_algebra_complexity → momentSum_le_max_pow (Omega/Folding/MomentSum.lean:19)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "subsec:op_algebra_complexity-momentSum-le-max-pow"
      sourcePath := "sections/body/folding/subsec__op-algebra-complexity.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_le_max_pow"
      phase := 8
      status := .formalized }
  -- Phase 9: S_2 矩谱基值 (Round 9)
  -- prop:pom-s2-recurrence → cMomentSum 可计算版本 (Omega/Folding/MomentSum.lean:39)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-cMomentSum"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.cMomentSum"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → cMomentSum_eq 桥接 (Omega/Folding/MomentSum.lean:42)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-cMomentSum-eq"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.cMomentSum_eq"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2(0)=1 (Omega/Folding/MomentSum.lean:49)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-0"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_zero"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2(1)=2 (Omega/Folding/MomentSum.lean:50)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-1"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_one"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2(2)=6 (Omega/Folding/MomentSum.lean:51)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-2"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_two"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2(3)=14 (Omega/Folding/MomentSum.lean:52)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-3"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_three"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2(4)=36 (Omega/Folding/MomentSum.lean:53)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-4"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_four"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2(5)=88 (Omega/Folding/MomentSum.lean:54)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-5"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_five"
      phase := 9
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2(6)=220 (Omega/Folding/MomentSum.lean:55)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-6"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_six"
      phase := 9
      status := .formalized }
  -- Phase 15: CollisionKernel (Plan 10, partial)
  -- prop:pom-s2-recurrence (S_2 碰撞核矩阵 + 三阶递推)
  -- collisionKernel2 定义 (Omega/Folding/CollisionKernel.lean:11)
  -- 状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-collision-kernel"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel2"
      phase := 15
      status := .formalized }
  -- prop:pom-s2-recurrence → tr(M)=2 (CollisionKernel.lean:14)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-collision-kernel-trace"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel2_trace"
      phase := 15
      status := .formalized }
  -- prop:pom-s2-recurrence → det(M)=-2 (CollisionKernel.lean:15)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-collision-kernel-det"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel2_det"
      phase := 15
      status := .formalized }
  -- prop:pom-s2-recurrence → Cayley-Hamilton M³=2M²+2M-2I (CollisionKernel.lean:18)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-collision-kernel-cayley-hamilton"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel2_cayley_hamilton"
      phase := 15
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2 递推 m=0..3 验证 (CollisionKernel.lean:24)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.momentSum_two_recurrence_verified"
      phase := 15
      status := .formalized }
  -- Phase 11: FibonacciPolynomial
  -- def:pom-fibonacci-polynomial → fibPoly (FibonacciPolynomial.lean:9)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-fibonacci-polynomial"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly"
      phase := 11
      status := .formalized }
  -- def:pom-fibonacci-polynomial → fibPoly_zero/one/succ_succ simp lemmas (FibonacciPolynomial.lean:14-17)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-fibonacci-polynomial-simp-zero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly_zero"
      phase := 11
      status := .formalized }
  , { label := "def:pom-fibonacci-polynomial-simp-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly_one"
      phase := 11
      status := .formalized }
  , { label := "def:pom-fibonacci-polynomial-simp-succ"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly_succ_succ"
      phase := 11
      status := .formalized }
  -- def:pom-fibonacci-polynomial → fibPoly_eval_one: F_n(1)=fib(n) (FibonacciPolynomial.lean:20)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-fibonacci-polynomial-eval-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly_eval_one"
      phase := 11
      status := .formalized }
  -- def:pom-fibonacci-polynomial → fibPoly_two/three: 具体值 (FibonacciPolynomial.lean:37-39)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-fibonacci-polynomial-two"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly_two"
      phase := 11
      status := .formalized }
  , { label := "def:pom-fibonacci-polynomial-three"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly_three"
      phase := 11
      status := .formalized }
  -- thm:pom-path-indset-poly-closed (部分) → pathIndSetPoly: I_ℓ=F_{ℓ+2} (FibonacciPolynomial.lean:30)
  --   状态: 已形式化, 审核通过 2026-03-23（缺闭式系数公式留后续）
  , { label := "thm:pom-path-indset-poly-closed-def"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.pathIndSetPoly"
      phase := 11
      status := .formalized }
  -- thm:pom-path-indset-poly-closed (部分) → pathIndSetPoly_eval_one: I_ℓ(1)=fib(ℓ+2) (FibonacciPolynomial.lean:33)
  --   状态: 已形式化, 审核通过 2026-03-23（缺闭式系数公式留后续）
  , { label := "thm:pom-path-indset-poly-closed-eval-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.pathIndSetPoly_eval_one"
      phase := 11
      status := .formalized }
  -- Phase 12: Cauchy-Schwarz 碰撞界 + S_q 单调性 (Round 12)
  -- thm:fold-collision-convex-lower-bounds / S_q 单调性
  -- momentSum_mono_q: S_q ≤ S_{q+1} (MomentSum.lean:59)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "pom-moment-mono-q"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_mono_q"
      phase := 12
      status := .formalized }
  -- S_q 单调性 → momentSum_two_ge_pow: 2^m ≤ S_2(m) (MomentSum.lean:71)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "pom-moment-two-ge-pow"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_ge_pow"
      phase := 12
      status := .formalized }
  -- S_q 单调性 → momentSum_ge_card: F(m+2) ≤ S_q(m) (MomentSum.lean:75)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "pom-moment-ge-card"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_ge_card"
      phase := 12
      status := .formalized }
  -- thm:fold-collision-convex-lower-bounds → momentSum_cauchy_schwarz: (2^m)² ≤ F_{m+1}·S_2(m) (MomentSum.lean:82)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:fold-collision-convex-lower-bounds"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_cauchy_schwarz"
      phase := 12
      status := .formalized }
  -- Phase 16: S_3 基值 + A_3 碰撞核矩阵 (Round 13)
  -- prop:pom-s3-recurrence → S_3(m) 基值 m=0..6 (MomentSum.lean:96)
  -- 状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-base-0"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_zero"
      phase := 16
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-base-1"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_one"
      phase := 16
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-base-2"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_two"
      phase := 16
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-base-3"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_three"
      phase := 16
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-base-4"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_four"
      phase := 16
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-base-5"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_five"
      phase := 16
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-base-6"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_six"
      phase := 16
      status := .formalized }
  -- prop:pom-s3-recurrence → S_3 递推 m=0..3 数值验证 (MomentSum.lean)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_recurrence_verified"
      phase := 16
      status := .formalized }
  -- prop:pom-s3-recurrence → A_3 companion matrix 定义 (CollisionKernel.lean:56)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-collision-kernel"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel3"
      phase := 16
      status := .formalized }
  -- prop:pom-s3-recurrence → tr(A_3)=2 (CollisionKernel.lean)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-collision-kernel-trace"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel3_trace"
      phase := 16
      status := .formalized }
  -- prop:pom-s3-recurrence → det(A_3)=-2 (CollisionKernel.lean)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-collision-kernel-det"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel3_det"
      phase := 16
      status := .formalized }
  -- prop:pom-s3-recurrence → Cayley-Hamilton M³=2M²+4M-2I (CollisionKernel.lean)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-collision-kernel-cayley-hamilton"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel3_cayley_hamilton"
      phase := 16
      status := .formalized }
  -- Phase 18: S_2/S_3 扩展基值 + 有界递推 + 条件递推 (Round 14)
  -- prop:pom-s2-recurrence → S_2(7)=544 (MomentSum.lean:57)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-base-7"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_two_seven"
      phase := 18
      status := .formalized }
  -- prop:pom-s3-recurrence → S_3(7)=2504 (MomentSum.lean:67)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-base-7"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_three_seven"
      phase := 18
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2 递推有界版 m≤4 (CollisionKernel.lean:63)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-bounded"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.momentSum_two_recurrence_bounded"
      phase := 18
      status := .formalized }
  -- prop:pom-s3-recurrence → S_3 递推有界版 m≤4 (CollisionKernel.lean:69)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-bounded"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.momentSum_three_recurrence_bounded"
      phase := 18
      status := .formalized }
  -- prop:pom-s2-recurrence → S_2 递推条件性一般版 (CollisionKernel.lean:75)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s2-recurrence-of"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.momentSum_two_recurrence_of"
      phase := 18
      status := .formalized }
  -- prop:pom-s3-recurrence → S_3 递推条件性一般版 (CollisionKernel.lean:83)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "prop:pom-s3-recurrence-of"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.momentSum_three_recurrence_of"
      phase := 18
      status := .formalized }
  -- Phase 17: MaxFiber 闭式定理
  -- thm:pom-max-fiber → D(0)=1 基值 (MaxFiber.lean:108)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-even-zero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_zero"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(2)=2=F_3 基值 (MaxFiber.lean:110)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-even-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_two"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(4)=3=F_4 基值 (MaxFiber.lean:112)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-even-two"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_four"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(6)=5=F_5 基值 (MaxFiber.lean:114)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-even-three"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_six"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(8)=8=F_6 基值 (MaxFiber.lean:116)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-even-four"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_eight"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(10)=13=F_7 基值 (MaxFiber.lean:118)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-even-five"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_ten"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(3)=2=2F_2 基值 (MaxFiber.lean:111)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-odd-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_three"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(5)=4=2F_3 基值 (MaxFiber.lean:113)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-odd-two"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_five"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(7)=6=2F_4 基值 (MaxFiber.lean:115)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-odd-three"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_seven"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → D(9)=10=2F_5 基值 (MaxFiber.lean:117)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-odd-four"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_nine"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → 偶数闭式 D(2k)=F_{k+2}, k=1..5 (MaxFiber.lean:134)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-even-closed"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_even"
      phase := 17
      status := .formalized }
  -- thm:pom-max-fiber → 奇数闭式 D(2k+1)=2F_k, k=1..4 (MaxFiber.lean:150)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:pom-max-fiber-odd-closed"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_odd"
      phase := 17
      status := .formalized }
  -- cor:pom-D-rec → 递推上界 D(m+2)≤D(m+1)+D(m) (MaxFiber.lean:314)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:pom-D-rec"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MaxFiber"
      leanName := "Omega.maxFiberMultiplicity_le_add"
      phase := 17
      status := .formalized }
  -- Phase 6: FiberRing — CommRing + 环同构 X m ≃+* ZMod(F_{m+2}) (Plan 6)
  -- thm:finite-resolution-mod → stableMul_one_left_univ (FiberRing.lean:13)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:finite-resolution-mod-mul-one-left"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.stableMul_one_left_univ"
      phase := 6
      status := .formalized }
  -- thm:finite-resolution-mod → stableMul_one_right_univ (FiberRing.lean:22)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:finite-resolution-mod-mul-one-right"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.stableMul_one_right_univ"
      phase := 6
      status := .formalized }
  -- thm:finite-resolution-mod → instCommRing : CommRing (X m) (FiberRing.lean:34)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:finite-resolution-mod-commring"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instCommRing"
      phase := 6
      status := .formalized }
  -- 定义等式 ring_add/mul/zero/one/neg_eq (FiberRing.lean:52-64)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:fiber-ring-add-eq"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.ring_add_eq"
      phase := 6
      status := .formalized }
  , { label := "def:fiber-ring-mul-eq"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.ring_mul_eq"
      phase := 6
      status := .formalized }
  , { label := "def:fiber-ring-zero-eq"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.ring_zero_eq"
      phase := 6
      status := .formalized }
  , { label := "def:fiber-ring-one-eq"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.ring_one_eq"
      phase := 6
      status := .formalized }
  , { label := "def:fiber-ring-neg-eq"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.ring_neg_eq"
      phase := 6
      status := .formalized }
  -- 环同构 Phase: instNeZeroFib (FiberRing.lean:69)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "inst:fiber-ne-zero-fib"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instNeZeroFib"
      phase := 6
      status := .formalized }
  -- 环同构: toZMod 定义 (FiberRing.lean:73)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:fiber-to-zmod"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.toZMod"
      phase := 6
      status := .formalized }
  -- 环同构: toZMod_add (FiberRing.lean:77)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:fiber-to-zmod-add"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.toZMod_add"
      phase := 6
      status := .formalized }
  -- 环同构: toZMod_mul (FiberRing.lean:81)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:fiber-to-zmod-mul"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.toZMod_mul"
      phase := 6
      status := .formalized }
  -- 环同构: toZMod_zero (FiberRing.lean:85)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:fiber-to-zmod-zero"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.toZMod_zero"
      phase := 6
      status := .formalized }
  -- 环同构: toZMod_one (FiberRing.lean:89)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:fiber-to-zmod-one"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.toZMod_one"
      phase := 6
      status := .formalized }
  -- thm:finite-resolution-mod → stableValueRingHom (FiberRing.lean:115)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:finite-resolution-mod-ringhom"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.stableValueRingHom"
      phase := 6
      status := .formalized }
  -- thm:finite-resolution-mod → toZMod_injective (FiberRing.lean:123)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:finite-resolution-mod-injective"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.toZMod_injective"
      phase := 6
      status := .formalized }
  -- thm:finite-resolution-mod → toZMod_surjective (FiberRing.lean:134)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:finite-resolution-mod-surjective"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.toZMod_surjective"
      phase := 6
      status := .formalized }
  -- thm:finite-resolution-mod + cor:field-phase-fib-prime (前提)
  --   → stableValueRingEquiv : X m ≃+* ZMod(F_{m+2}) (FiberRing.lean:139)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "thm:finite-resolution-mod-ringequiv"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.stableValueRingEquiv"
      phase := 6
      status := .formalized }
  -- Phase 20: 离散骨架 (cor:folding-stable-syntax-entropy-logqdim, Stage 1)
  -- goldenMeanAdjacency_pow_add_two → 矩阵 Fibonacci 递推 A^(m+2)=A^(m+1)+A^m
  --   (Omega/Graph/TransferMatrix.lean:39)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:folding-stable-syntax-entropy-logqdim-matrix-recurrence"
      sourcePath := "sections/body/folding/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_add_two"
      phase := 20
      status := .formalized }
  -- goldenMeanAdjacency_row_sum → 行和 = F(m+2)
  --   (Omega/Graph/TransferMatrix.lean:47)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:folding-stable-syntax-entropy-logqdim-row-sum"
      sourcePath := "sections/body/folding/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_row_sum"
      phase := 20
      status := .formalized }
  -- card_X_recurrence → |X_{m+2}|=|X_{m+1}|+|X_m| Fibonacci 递推
  --   (Omega/Folding/ShiftDynamics.lean:60)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:folding-stable-syntax-entropy-logqdim-card-recurrence"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.card_X_recurrence"
      phase := 20
      status := .formalized }
  -- card_X_ratio_bounds → |X_m|≤|X_{m+1}|≤2·|X_m| Fibonacci 比率上下界
  --   (Omega/Folding/ShiftDynamics.lean:66)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:folding-stable-syntax-entropy-logqdim-ratio-bounds"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.card_X_ratio_bounds"
      phase := 20
      status := .formalized }
  -- card_X_eq_matrix_sum → |X_m|=(A^m)_{00}+(A^m)_{01} 矩阵求和表示
  --   (Omega/Folding/ShiftDynamics.lean:80)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:folding-stable-syntax-entropy-logqdim-matrix-sum"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.card_X_eq_matrix_sum"
      phase := 20
      status := .formalized }
  -- Phase 9 (partial): 纤维谱定义与基值 (def:pom-top-fiber-spectrum)
  -- def:pom-top-fiber-spectrum → cFiberMultiset/cFiberSpectrum/cNthMaxFiber (FiberSpectrum.lean:14-23)
  -- 状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-top-fiber-spectrum-computable-defs"
      sourcePath := "sections/body/pom/fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cFiberMultiset"
      phase := 9
      status := .formalized }
  -- def:pom-top-fiber-spectrum → fiberValueSet / fiberValueSet_nonempty (FiberSpectrum.lean:36-41)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-top-fiber-spectrum-noncomputable-set"
      sourcePath := "sections/body/pom/fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.X.fiberValueSet"
      phase := 9
      status := .formalized }
  -- def:pom-top-fiber-spectrum → cNthMaxFiber_zero_eq_0/5/7 (FiberSpectrum.lean:26-28)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-top-fiber-spectrum-consistency-check"
      sourcePath := "sections/body/pom/fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cNthMaxFiber_zero_eq_0"
      phase := 9
      status := .formalized }
  -- def:pom-top-fiber-spectrum → cFiberSpectrum_zero..seven (FiberSpectrum.lean:51-58)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-top-fiber-spectrum-base-values"
      sourcePath := "sections/body/pom/fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cFiberSpectrum_zero"
      phase := 9
      status := .formalized }
  -- def:pom-top-fiber-spectrum → cNthMaxFiber_second_four..seven D_m^{(2)} (FiberSpectrum.lean:61-64)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-top-fiber-spectrum-second-values"
      sourcePath := "sections/body/pom/fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cNthMaxFiber_second_four"
      phase := 9
      status := .formalized }
  -- def:pom-top-fiber-spectrum → cNthMaxFiber_third_four..seven D_m^{(3)} (FiberSpectrum.lean:67-70)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "def:pom-top-fiber-spectrum-third-values"
      sourcePath := "sections/body/pom/fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cNthMaxFiber_third_four"
      phase := 9
      status := .formalized }
  -- Phase 15: cor:field-phase-fib-prime — Field 实例 (FiberRing.lean:143-174)
  -- instFieldOfPrime (通用域实例，F_{m+2} 素数时 X m 为域)
  --   → instFieldOfPrime (FiberRing.lean:145)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-instFieldOfPrime"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instFieldOfPrime"
      phase := 15
      status := .formalized }
  -- cor:field-phase-fib-prime → instField_X1 : Field (X 1) ≅ GF(2) (FiberRing.lean:153)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-instField-X1"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instField_X1"
      phase := 15
      status := .formalized }
  -- cor:field-phase-fib-prime → instField_X2 : Field (X 2) ≅ GF(3) (FiberRing.lean:157)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-instField-X2"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instField_X2"
      phase := 15
      status := .formalized }
  -- cor:field-phase-fib-prime → instField_X3 : Field (X 3) ≅ GF(5) (FiberRing.lean:161)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-instField-X3"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instField_X3"
      phase := 15
      status := .formalized }
  -- cor:field-phase-fib-prime → instField_X5 : Field (X 5) ≅ GF(13) (FiberRing.lean:165)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-instField-X5"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instField_X5"
      phase := 15
      status := .formalized }
  -- cor:field-phase-fib-prime → instField_X9 : Field (X 9) ≅ GF(89) (FiberRing.lean:169)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-instField-X9"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instField_X9"
      phase := 15
      status := .formalized }
  -- cor:field-phase-fib-prime → instField_X11 : Field (X 11) ≅ GF(233) (FiberRing.lean:173)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "cor:field-phase-fib-prime-instField-X11"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.instField_X11"
      phase := 15
      status := .formalized }
  -- Phase 5: Fibonacci 整除性 (计划5)
  -- fib-gcd → fib_gcd (Omega/Core/Fib.lean:81)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "fib-gcd"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Core.Fib"
      leanName := "Omega.fib_gcd"
      phase := 5
      status := .formalized }
  -- fib-coprime-succ → fib_coprime_succ (Omega/Core/Fib.lean:85)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "fib-coprime-succ"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Core.Fib"
      leanName := "Omega.fib_coprime_succ"
      phase := 5
      status := .formalized }
  -- fib-dvd-mul → fib_dvd_mul (Omega/Core/Fib.lean:89)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "fib-dvd-mul"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Core.Fib"
      leanName := "Omega.fib_dvd_mul"
      phase := 5
      status := .formalized }
  -- Phase 4 深化: restrict 保零保一 (计划4深化)
  -- restrict-zero → restrict_zero (Omega/Folding/ModularTower.lean:122)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "restrict-zero"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.restrict_zero"
      phase := 4
      status := .formalized }
  -- restrict-one → restrict_one (Omega/Folding/ModularTower.lean:128)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "restrict-one"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.restrict_one"
      phase := 4
      status := .formalized }
  -- Phase 20 深化: shift 动力学全零固定点与唯一性 (计划20深化)
  -- shift-allFalse-fixed → allFalse + shift_allFalse (Omega/Folding/ShiftDynamics.lean:48)
  --   状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:shift-allFalse"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.allFalse"
      phase := 20
      status := .formalized }
  -- shift_allFalse → shift_allFalse (Omega/Folding/ShiftDynamics.lean:50)
  --   状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:shift-allFalse-fixed"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift_allFalse"
      phase := 20
      status := .formalized }
  -- shift-fixed-iff → shift_fixed_iff (Omega/Folding/ShiftDynamics.lean:54)
  --   状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:shift-fixed-iff"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift_fixed_iff"
      phase := 20
      status := .formalized }
  -- shift-not-injective → shift_not_injective (Omega/Folding/ShiftDynamics.lean:69)
  --   状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:shift-not-injective"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift_not_injective"
      phase := 20
      status := .formalized }
  -- Phase 4 深化: restrict 满射与纤维非空 (计划4深化)
  -- restrict-surjective → restrict_surjective (Omega/Folding/ModularTower.lean:134)
  --   状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:restrict-surjective"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.restrict_surjective"
      phase := 4
      status := .formalized }
  -- restrict-fiber-nonempty → restrict_fiber_nonempty (Omega/Folding/ModularTower.lean:140)
  --   状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:restrict-fiber-nonempty"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.ModularTower"
      leanName := "Omega.X.restrict_fiber_nonempty"
      phase := 4
      status := .formalized }
  -- Phase 27 初步: CRT 分解 (计划27)
  -- crt-decomposition → crtDecomposition (Omega/Folding/FiberRing.lean:179)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "crt-decomposition"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.crtDecomposition"
      phase := 27
      status := .formalized }
  -- crt-X7-decomposition → X7_decomposition (Omega/Folding/FiberRing.lean:185)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "crt-X7-decomposition"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.X7_decomposition"
      phase := 27
      status := .formalized }
  -- crt-X10-decomposition → X10_decomposition (Omega/Folding/FiberRing.lean:189)
  --   状态: 已形式化, 审核通过 2026-03-23
  , { label := "crt-X10-decomposition"
      sourcePath := "sections/body/arithmetic/subsec__folding-fibonacci-field.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.X.X10_decomposition"
      phase := 27
      status := .formalized }
  -- Phase 19/20 深化: TransferMatrix 幂次条目公式 (计划19/20深化)
  -- thm:golden-mean-pow-entry-00 → goldenMeanAdjacency_pow_00 (TransferMatrix.lean:74)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:golden-mean-pow-entry-00"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_00"
      phase := 19
      status := .formalized }
  -- thm:golden-mean-pow-entry-01 → goldenMeanAdjacency_pow_01 (TransferMatrix.lean:84)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:golden-mean-pow-entry-01"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_01"
      phase := 19
      status := .formalized }
  -- thm:golden-mean-pow-entry-10 → goldenMeanAdjacency_pow_10 (TransferMatrix.lean:94)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:golden-mean-pow-entry-10"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_10"
      phase := 19
      status := .formalized }
  -- thm:golden-mean-pow-entry-11 → goldenMeanAdjacency_pow_11 (TransferMatrix.lean:104)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:golden-mean-pow-entry-11"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_11"
      phase := 19
      status := .formalized }
  -- aux:pow-entry-add-two → pow_entry_add_two (TransferMatrix.lean:67, private helper)
  -- 状态: 已形式化, 审核通过 2026-03-24
  -- Phase 20 深化: 周期轨道 (计划20深化)
  -- def:period3-seq → period3Seq (ShiftDynamics.lean:87)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:period3-seq"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.period3Seq"
      phase := 20
      status := .formalized }
  -- thm:shiftN-three-period3 → shiftN_three_period3 (ShiftDynamics.lean:91)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:shiftN-three-period3"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shiftN_three_period3"
      phase := 20
      status := .formalized }
  -- thm:shift-period3-ne → shift_period3_ne (ShiftDynamics.lean:95)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:shift-period3-ne"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift_period3_ne"
      phase := 20
      status := .formalized }
  -- def:period2-seq → period2Seq (ShiftDynamics.lean:100)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:period2-seq"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.period2Seq"
      phase := 20
      status := .formalized }
  -- thm:shiftN-two-period2 → shiftN_two_period2 (ShiftDynamics.lean:104)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:shiftN-two-period2"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shiftN_two_period2"
      phase := 20
      status := .formalized }
  -- Phase 11 前置: Fibonacci 多项式 x=0 评估与路径独立集递推 (计划11前置)
  -- thm:pom-fibonacci-polynomial-eval-zero → fibPoly_eval_zero (FibonacciPolynomial.lean:42)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-fibonacci-polynomial-eval-zero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.fibPoly_eval_zero"
      phase := 11
      status := .formalized }
  -- thm:pom-path-indset-poly-eval-zero → pathIndSetPoly_eval_zero (FibonacciPolynomial.lean:51)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-path-indset-poly-eval-zero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.pathIndSetPoly_eval_zero"
      phase := 11
      status := .formalized }
  -- thm:pom-path-indset-poly-recurrence → pathIndSetPoly_recurrence (FibonacciPolynomial.lean:55)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-path-indset-poly-recurrence"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FibonacciPolynomial"
      leanName := "Omega.pathIndSetPoly_recurrence"
      phase := 11
      status := .formalized }
  -- Phase 17: Frontier 包装 — ConditionalArithmetic.lean
  -- thm:finite-resolution-mod → stable_ring_isomorphism (ConditionalArithmetic.lean:640)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:finite-resolution-mod"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Frontier.ConditionalArithmetic"
      leanName := "Omega.Frontier.stable_ring_isomorphism"
      phase := 17
      status := .formalized }
  -- cor:field-phase-fib-prime → stable_field_of_prime (ConditionalArithmetic.lean:644)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:field-phase-fib-prime"
      sourcePath := "sections/body/arithmetic/sec__emergent-stable-arithmetic.tex"
      moduleName := "Omega.Frontier.ConditionalArithmetic"
      leanName := "Omega.Frontier.stable_field_of_prime"
      phase := 17
      status := .formalized }
  -- Phase 17: Frontier 包装 — ConditionalSummary.lean
  -- prop:pom-projection-entropy → projection_entropy_cardinality (ConditionalSummary.lean:554)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-projection-entropy"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.projection_entropy_cardinality"
      phase := 17
      status := .formalized }
  -- prop:pom-fiber-sum-identity → fiber_sum_eq_pow (ConditionalSummary.lean:558)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-fiber-sum-identity"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.fiber_sum_eq_pow"
      phase := 17
      status := .formalized }
  -- thm:fold-collision-convex-lower-bounds → cauchy_schwarz_collision_bound (ConditionalSummary.lean:562)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:fold-collision-convex-lower-bounds"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.cauchy_schwarz_collision_bound"
      phase := 17
      status := .formalized }
  -- prop:pom-sq-monotone → moment_monotone (ConditionalSummary.lean:566)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-sq-monotone"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.moment_monotone"
      phase := 17
      status := .formalized }
  -- prop:pom-sq-lower → moment_ge_cardinality (ConditionalSummary.lean:570)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-sq-lower"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.moment_ge_cardinality"
      phase := 17
      status := .formalized }
  -- cor:pom-s2-lower → collision_sum_ge_pow (ConditionalSummary.lean:574)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-s2-lower"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.collision_sum_ge_pow"
      phase := 17
      status := .formalized }
  -- Phase 18: Frontier 包装 — ConditionalSummary.lean (POM 存在性与熵率骨架)
  -- thm:pom-max-fiber (存在部分) → max_fiber_achieved (ConditionalSummary.lean:580)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-max-fiber-achieved"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.max_fiber_achieved"
      phase := 18
      status := .formalized }
  -- prop:pom-fiber-pigeonhole → fiber_pigeonhole (ConditionalSummary.lean:585)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-fiber-pigeonhole"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.fiber_pigeonhole"
      phase := 18
      status := .formalized }
  -- thm:pom-max-fiber (正性部分) → max_fiber_positive (ConditionalSummary.lean:590)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-max-fiber-positive"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.max_fiber_positive"
      phase := 18
      status := .formalized }
  -- cor:pom-D-rec (上界) → max_fiber_fib_bound (ConditionalSummary.lean:594)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-D-rec-upper"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.max_fiber_fib_bound"
      phase := 18
      status := .formalized }
  -- prop:pom-projection-entropy (严格版) → entropy_gap_strict (ConditionalSummary.lean:601)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-projection-entropy-strict"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.entropy_gap_strict"
      phase := 18
      status := .formalized }
  -- 投影比率递减 → projection_ratio_decreasing (ConditionalSummary.lean:623)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-projection-ratio-decreasing"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.projection_ratio_decreasing"
      phase := 18
      status := .formalized }
  -- 投影比率正性 → projection_ratio_positive (ConditionalSummary.lean:635)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-projection-ratio-positive"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.projection_ratio_positive"
      phase := 18
      status := .formalized }
  -- Phase 18: FiberSpectrum.lean — 达到者数定义与基值
  -- thm:pom-max-achievers-phase-stabilization (前置) → cMaxFiberAchievers (FiberSpectrum.lean:31)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-max-achievers-phase-stabilization-def"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cMaxFiberAchievers"
      phase := 18
      status := .formalized }
  -- Phase 19: FiberSpectrum.lean — 达到者数有界 + 次大纤维基值 m=8,9,10
  -- thm:pom-max-achievers-phase-stabilization (有界) → cMaxFiberAchievers_le_univ (FiberSpectrum.lean:46)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-max-achievers-phase-stabilization-bound"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cMaxFiberAchievers_le_univ"
      phase := 19
      status := .formalized }
  -- thm:pom-second-max-fiber-closed-form (基值 m=8) → cNthMaxFiber_second_eight (FiberSpectrum.lean:91)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-second-max-fiber-closed-form-m8"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cNthMaxFiber_second_eight"
      phase := 19
      status := .formalized }
  -- thm:pom-second-max-fiber-closed-form (基值 m=9) → cNthMaxFiber_second_nine (FiberSpectrum.lean:92)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-second-max-fiber-closed-form-m9"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cNthMaxFiber_second_nine"
      phase := 19
      status := .formalized }
  -- thm:pom-second-max-fiber-closed-form (基值 m=10) → cNthMaxFiber_second_ten (FiberSpectrum.lean:93)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-second-max-fiber-closed-form-m10"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cNthMaxFiber_second_ten"
      phase := 19
      status := .formalized }
  -- Phase 19: ConditionalSummary.lean — S_q 正性与 Cauchy-Schwarz 重述
  -- prop:pom-sq-monotone (正性) → momentSum_pos (ConditionalSummary.lean:641)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-sq-pos"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.momentSum_pos"
      phase := 19
      status := .formalized }
  -- prop:pom-sq-monotone (Cauchy-Schwarz 重述) → momentSum_cauchy_schwarz_restated (ConditionalSummary.lean:647)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-sq-cauchy-schwarz-restated"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.momentSum_cauchy_schwarz_restated"
      phase := 19
      status := .formalized }
  -- Phase 20: ConditionalSummary — Rényi 上界 + S_1/S_0 恒等式 + 最大纤维概率界
  -- prop:pom-rq-universal-bounds → renyi_upper_bound (ConditionalSummary.lean:654)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-rq-universal-bounds"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.renyi_upper_bound"
      phase := 20
      status := .formalized }
  -- S_1 = 2^m → moment_sum_one_eq_pow (ConditionalSummary.lean:658)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-rq-universal-bounds-s1"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.moment_sum_one_eq_pow"
      phase := 20
      status := .formalized }
  -- S_0 = F_{m+2} → moment_sum_zero_eq_card (ConditionalSummary.lean:659)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-rq-universal-bounds-s0"
      sourcePath := "sections/body/pom/subsec__pom-moment-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.moment_sum_zero_eq_card"
      phase := 20
      status := .formalized }
  -- cor:pom-max-fiber-rate-endpoint (D_m ≤ 2^m) → max_fiber_le_pow (ConditionalSummary.lean:663)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-max-fiber-rate-endpoint"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.max_fiber_le_pow"
      phase := 20
      status := .formalized }
  -- 1 ≤ D_m → max_fiber_ge_one (ConditionalSummary.lean:671)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-max-fiber-rate-endpoint-lower"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.max_fiber_ge_one"
      phase := 20
      status := .formalized }
  -- 1 ≤ D_m ∧ D_m ≤ 2^m → max_fiber_prob_bounds (ConditionalSummary.lean:674)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-max-fiber-rate-endpoint-both"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.max_fiber_prob_bounds"
      phase := 20
      status := .formalized }
  -- Phase 20: FiberSpectrum — 奇偶纤维计数定义与基值 (cor:pom-fiber-parity 前置)
  -- cOddFiberCount 定义 + 基值 m=0..6 (FiberSpectrum.lean:106-120)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-fiber-parity-odd-def"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cOddFiberCount"
      phase := 20
      status := .formalized }
  -- cEvenFiberCount 定义 + 基值 m=0..6 (FiberSpectrum.lean:110-128)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-fiber-parity-even-def"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cEvenFiberCount"
      phase := 20
      status := .formalized }
  -- Phase 21: Fib — Fibonacci 双倍公式与平方和恒等式
  -- fib_double: F_{2n} = F_n·(2F_{n+1}-F_n) (Fib.lean:93)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:fib-double-formula"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Core.Fib"
      leanName := "Omega.fib_double"
      phase := 21
      status := .formalized }
  -- fib_double_plus_one: F_{2n+1} = F_{n+1}²+F_n² (Fib.lean:98)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:fib-double-plus-one-formula"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Core.Fib"
      leanName := "Omega.fib_double_plus_one"
      phase := 21
      status := .formalized }
  -- fib_sq_add_sq: F_n²+F_{n+1}² = F_{2n+1} (Fib.lean:103)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:fib-sq-add-sq"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Core.Fib"
      leanName := "Omega.fib_sq_add_sq"
      phase := 21
      status := .formalized }
  -- Phase 21: TransferMatrix — 行列式幂次公式与 Cassini 恒等式
  -- goldenMeanAdjacency_pow_det: det(A^m) = (-1)^m (TransferMatrix.lean:116)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:transfer-matrix-pow-det"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_det"
      phase := 21
      status := .formalized }
  -- fib_cassini: Cassini 恒等式 F_{n+1}·F_{n-1}-F_n²=(-1)^n (TransferMatrix.lean:121)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:fib-cassini-identity"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.fib_cassini"
      phase := 21
      status := .formalized }
  -- Phase 21: ShiftDynamics — Lucas 数定义 + Fibonacci 关系 + 迹公式
  -- lucasNum 定义 + lucasNum_zero/one/two/three/succ_succ (ShiftDynamics.lean:149-159)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:lucas-number"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.lucasNum"
      phase := 21
      status := .formalized }
  -- lucasNum_eq_fib: L_n = F_{n+1}+F_{n-1} (ShiftDynamics.lean:174)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:lucas-fibonacci-identity"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.lucasNum_eq_fib"
      phase := 21
      status := .formalized }
  -- goldenMeanAdjacency_pow_trace: tr(A^n) = F_{n+1}+F_{n-1} (ShiftDynamics.lean:181)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:transfer-matrix-pow-trace"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.goldenMeanAdjacency_pow_trace"
      phase := 21
      status := .formalized }
  -- Phase 22: FiberSpectrum — 纤维直方图定义与基值 (cor:pom-fiber-parity 深化前置)
  -- cFiberHist 定义 + m=4 直方图基值 (FiberSpectrum.lean:51-57)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-fiber-histogram"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cFiberHist"
      phase := 22
      status := .formalized }
  -- cFiberHist m=4 基值: hist[1]=2, hist[2]=4, hist[3]=2 (FiberSpectrum.lean:55-57)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-fiber-histogram-m4"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cFiberHist_4_1"
      phase := 22
      status := .formalized }
  -- cFiberHist m=6 基值: hist[1]=2, hist[2]=4, hist[3]=8, hist[4]=5, hist[5]=2 (FiberSpectrum.lean:60-64)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-fiber-histogram-m6"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSpectrum"
      leanName := "Omega.cFiberHist_6_1"
      phase := 22
      status := .formalized }
  -- Phase 22: TransferMatrix — 路径计数 Fibonacci 等式
  -- goldenMean_path_count_from_true: row 1 sum = F_{m+1} (TransferMatrix.lean:136)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:golden-mean-path-count-from-true"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMean_path_count_from_true"
      phase := 22
      status := .formalized }
  -- goldenMean_total_paths: total = F_{m+2}+F_{m+1} (TransferMatrix.lean:146)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:golden-mean-total-paths"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMean_total_paths"
      phase := 22
      status := .formalized }
  -- Phase 22: InverseLimitTopology — 位差异→序列不同
  -- ne_of_bit_ne: 位差异→序列不同 (InverseLimitTopology.lean:45)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:ne-of-bit-ne"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Folding.InverseLimitTopology"
      leanName := "Omega.X.ne_of_bit_ne"
      phase := 22
      status := .formalized }
  -- Phase 22: ConditionalSummary — No11 词计数 = F_{m+2}
  -- no11_count: |No11 words| = F_{m+2} (ConditionalSummary.lean:680)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:no11-word-count"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Frontier.ConditionalSummary"
      leanName := "Omega.Frontier.no11_count"
      phase := 22
      status := .formalized }
  -- Phase 23: ShiftDynamics — 周期轨道深化
  -- shift_period2_ne: 周期2序列非固定点 (ShiftDynamics.lean:108)
  -- period2_minimal: 周期2最小性 (ShiftDynamics.lean:113)
  -- period3_minimal: 周期3最小性 (ShiftDynamics.lean:118)
  -- period4Seq: 周期4序列定义 (ShiftDynamics.lean:126)
  -- shiftN_four_period4: 周期4轨道 σ⁴(p₄)=p₄ (ShiftDynamics.lean:130)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:shift-period2-ne"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shift_period2_ne"
      phase := 23
      status := .formalized }
  , { label := "cor:shift-period2-minimal"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.period2_minimal"
      phase := 23
      status := .formalized }
  , { label := "cor:shift-period3-minimal"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.period3_minimal"
      phase := 23
      status := .formalized }
  , { label := "def:shift-period4-seq"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.period4Seq"
      phase := 23
      status := .formalized }
  , { label := "cor:shift-period4-orbit"
      sourcePath := "sections/body/symbolic/sofic.tex"
      moduleName := "Omega.Folding.ShiftDynamics"
      leanName := "Omega.X.shiftN_four_period4"
      phase := 23
      status := .formalized }
  -- Phase 23: Weight — 全零词 weight=0
  -- weight_allFalse: weight(0⃗) = 0 (Weight.lean:50)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:weight-allFalse"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Weight"
      leanName := "Omega.weight_allFalse"
      phase := 23
      status := .formalized }
  -- Phase 23: Value — 全零稳定词 stableValue=0
  -- stableValue_allFalse: stableValue(0⃗) = 0 (Value.lean:109)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:stableValue-allFalse"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Value"
      leanName := "Omega.stableValue_allFalse"
      phase := 23
      status := .formalized }
  -- Phase 24: Zeckendorf — 全零稳定词 Zeckendorf 索引为空
  -- zeckIndices_allFalse: zeckIndices(0⃗) = [] (Zeckendorf.lean:162)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:zeckIndices-allFalse"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Zeckendorf"
      leanName := "Omega.X.zeckIndices_allFalse"
      phase := 24
      status := .formalized }
  -- Phase 25: Value — stableValue = weight of underlying word
  -- stableValue_eq_weight: stableValue x = weight x.1 (Value.lean:114)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:stableValue-eq-weight"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.Value"
      leanName := "Omega.stableValue_eq_weight"
      phase := 25
      status := .formalized }
  -- Phase 25: FiberRing — 环特征 = F_{m+2}
  -- instCharP: CharP (X m) (Nat.fib (m + 2)) (FiberRing.lean:196)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:charP-fib"
      sourcePath := "sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex"
      moduleName := "Omega.Folding.FiberRing"
      leanName := "Omega.instCharP"
      phase := 25
      status := .formalized }
  -- Phase 26: HankelSpectrum (Round 20, Target A)
  -- lem:pom-s2-hankel-det → hankelS2_2x2/3x3/4x4 + det 定理 (HankelSpectrum.lean:16-43)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:pom-s2-hankel-det-2x2"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS2_2x2_det"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s2-hankel-det-3x3"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS2_3x3_det"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s2-hankel-det-4x4"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS2_4x4_det"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s2-hankel-det-nonzero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS2_3x3_det_ne_zero"
      phase := 26
      status := .formalized }
  -- lem:pom-s2-minimal-order → momentSum_two_minimal_recurrence_order (HankelSpectrum.lean:48-50)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:pom-s2-minimal-order"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_two_minimal_recurrence_order"
      phase := 26
      status := .formalized }
  -- lem:pom-s3-hankel (S_3 Hankel 行列式 + 最小递推阶数) (HankelSpectrum.lean:54-79)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:pom-s3-hankel-det-3x3"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS3_3x3_det"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s3-hankel-det-4x4"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS3_4x4_det"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s3-minimal-order"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_three_minimal_recurrence_order"
      phase := 26
      status := .formalized }
  -- Target B: 特征多项式验证 (HankelSpectrum.lean:89-132)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-s2-charpoly-eval"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.collisionKernel2_charpoly_eval"
      phase := 26
      status := .formalized }
  , { label := "thm:pom-s2-charpoly-coefficients"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.collisionKernel2_charpoly_coefficients"
      phase := 26
      status := .formalized }
  , { label := "thm:pom-s3-charpoly-eval"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.collisionKernel3_charpoly_eval"
      phase := 26
      status := .formalized }
  , { label := "thm:pom-s3-charpoly-coefficients"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.collisionKernel3_charpoly_coefficients"
      phase := 26
      status := .formalized }
  , { label := "thm:pom-collision-kernels-shared-invariants"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.collision_kernels_shared_invariants"
      phase := 26
      status := .formalized }
  , { label := "prop:pom-collision-kernel-root-sum"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.collision_kernel_root_sum_eq_trace"
      phase := 26
      status := .formalized }
  , { label := "prop:pom-collision-kernel-root-product"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.collision_kernel_root_product"
      phase := 26
      status := .formalized }
  -- Target C: S_2/S_3 分辨率单调性 (HankelSpectrum.lean:139-215)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:pom-rank-exact-s2-strict-mono"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_two_strict_mono_verified"
      phase := 26
      status := .formalized }
  , { label := "prop:pom-s2-recurrence-mono-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_two_mono_verified"
      phase := 26
      status := .formalized }
  , { label := "thm:pom-rank-exact-s3-strict-mono"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_three_strict_mono_verified"
      phase := 26
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-mono-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_three_mono_verified"
      phase := 26
      status := .formalized }
  , { label := "prop:pom-s2-recurrence-mono-of-recurrence"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_two_mono_of_recurrence"
      phase := 26
      status := .formalized }
  , { label := "prop:pom-s3-recurrence-mono-of-recurrence"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_three_mono_of_recurrence"
      phase := 26
      status := .formalized }
  -- Phase 26 补充 (Round 20): S_3 Hankel 归一化 + 4x4 秩 + 分辨率单调联合 (HankelSpectrum.lean:228-309)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:pom-s3-hankel-normalized"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS3_det"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s3-hankel-normalized-nonzero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS3_det_ne_zero"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s2-hankel-norm-4x4"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS2_norm_4x4_det"
      phase := 26
      status := .formalized }
  , { label := "lem:pom-s2-rank-exact-three"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.hankelS2_rank_exact_three"
      phase := 26
      status := .formalized }
  , { label := "thm:pom-s2-mono-resolution-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_two_mono_resolution_verified"
      phase := 26
      status := .formalized }
  , { label := "thm:pom-s3-mono-resolution-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.HankelSpectrum"
      leanName := "Omega.momentSum_three_mono_resolution_verified"
      phase := 26
      status := .formalized }
  -- Phase 27: FiberSplit — D_m 严格单调性 + 纤维分裂界 + D^{(2)} 基值 (FiberSplit.lean:1-167)
  -- cor:pom-max-fiber-achievers-bsplit-gcd-trichotomy, def:pom-top-fiber-spectrum
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:pom-max-fiber-achievers-bsplit-strict-mono-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.maxFiberMultiplicity_strict_mono_verified"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-max-fiber-achievers-bsplit-mono-verified"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.maxFiberMultiplicity_mono_verified"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-max-fiber-achievers-bsplit-mono-of-two-step"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.maxFiberMultiplicity_mono_of_two_step"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-max-fiber-achievers-bsplit-strict-mono-of-two-step"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.maxFiberMultiplicity_strict_mono_of_two_step"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-max-fiber-achievers-bsplit-gcd-trichotomy"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.maxFiberMultiplicity_split_bound"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-max-fiber-fibonacci-bound"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.maxFiberMultiplicity_fibonacci_bound"
      phase := 27
      status := .formalized }
  , { label := "def:pom-top-fiber-spectrum-second"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-second-max-fiber-base-2"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult_two"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-second-max-fiber-base-3"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult_three"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-second-max-fiber-base-4"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult_four"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-second-max-fiber-base-5"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult_five"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-second-max-fiber-base-6"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult_six"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-second-max-fiber-base-7"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult_seven"
      phase := 27
      status := .formalized }
  , { label := "cor:pom-second-max-fiber-eq-prev"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.FiberSplit"
      leanName := "Omega.X.cSecondMaxFiberMult_eq_prev"
      phase := 27
      status := .formalized }
  -- Phase 28: 群统一章节推进 (Round 22)
  -- prop:bdry-fib-square-identity → cBoundaryCount_eq_fib
  --   (Omega/Folding/BoundaryLayer.lean:30)
  -- cor:bdry-m6-square-instance → cBoundaryCount_six, boundary_gap_six
  --   (Omega/Folding/BoundaryLayer.lean:24,36)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:bdry-fib-square-identity"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BoundaryLayer"
      leanName := "Omega.cBoundaryCount_eq_fib"
      phase := 28
      status := .formalized }
  , { label := "cor:bdry-m6-square-instance"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BoundaryLayer"
      leanName := "Omega.cBoundaryCount_six"
      phase := 28
      status := .formalized }
  -- thm:zeckendorf-no-carry-additivity → dim_so10_zeckendorf, dim_sm_zeckendorf
  --   (Omega/Folding/ZeckendorfSignature.lean:21,25)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:zeckendorf-no-carry-additivity"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.dim_so10_zeckendorf"
      phase := 28
      status := .formalized }
  , { label := "thm:zeckendorf-sm-embedding"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.dim_sm_zeckendorf"
      phase := 28
      status := .formalized }
  -- thm:nap-so10-analytic-minimality → so10_has_F4_and_F6, sm12_has_F4_and_F6,
  --   nap_su2, nap_su3 (Omega/Folding/ZeckendorfSignature.lean:81,87,92,95)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:nap-so10-analytic-minimality"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.so10_has_F4_and_F6"
      phase := 28
      status := .formalized }
  , { label := "thm:nap-sm-embedding"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.sm12_has_F4_and_F6"
      phase := 28
      status := .formalized }
  -- Window-6 invariants: card_Word_six, card_X_six', cNontrivialFiberCount + _six,
  --   abelianization_rank_six, compression_ratio_six, fiber_sum_six,
  --   nontrivial_microstate_count_six (Omega/Folding/Window6.lean)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:window6-compression-ratio"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.compression_ratio_six"
      phase := 28
      status := .formalized }
  , { label := "cor:window6-fiber-sum"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.fiber_sum_six"
      phase := 28
      status := .formalized }
  -- Phase 29: ZeckendorfSignature 群统一深化 (Round 23)
  -- thm:zeckendorf-no-carry-additivity → zeckendorf_no_carry_sm_triple, zeckendorf_no_carry_so10_triple
  --   (Omega/Folding/ZeckendorfSignature.lean:113,118)
  -- cor:sm-signature-strict-union → sm_signature_union (line:122)
  -- prop:bdry-gap-33-cassini-factorization → so10_uplift_gap (line:128), cassini_gap_33_factorization (line:131)
  -- boundary_square_identity_instances (line:135), cassini_identity_8 (line:142), sm_dim_factorization (line:146)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:zeckendorf-no-carry-sm-triple"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.zeckendorf_no_carry_sm_triple"
      phase := 29
      status := .formalized }
  , { label := "thm:zeckendorf-no-carry-so10-triple"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.zeckendorf_no_carry_so10_triple"
      phase := 29
      status := .formalized }
  , { label := "cor:sm-signature-strict-union"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.sm_signature_union"
      phase := 29
      status := .formalized }
  , { label := "prop:bdry-gap-33-so10-uplift"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.so10_uplift_gap"
      phase := 29
      status := .formalized }
  , { label := "prop:bdry-gap-33-cassini-factorization"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.cassini_gap_33_factorization"
      phase := 29
      status := .formalized }
  , { label := "cor:boundary-square-identity-instances"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.boundary_square_identity_instances"
      phase := 29
      status := .formalized }
  , { label := "cor:cassini-identity-8"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.cassini_identity_8"
      phase := 29
      status := .formalized }
  , { label := "cor:sm-dim-factorization"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.sm_dim_factorization"
      phase := 29
      status := .formalized }
  -- Phase 29: BinFold (Round 23) — thm:terminal-foldbin6-64-to-21-hist
  -- cBinFold, cBinFiberMult, cBinFiberHist 定义 + m=6 直方图基值
  --   (Omega/Folding/BinFold.lean:13-22,31-42)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-foldbin6-64-to-21-hist"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberHist"
      phase := 29
      status := .formalized }
  , { label := "thm:terminal-foldbin6-hist-2"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberHist_6_2"
      phase := 29
      status := .formalized }
  , { label := "thm:terminal-foldbin6-hist-3"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberHist_6_3"
      phase := 29
      status := .formalized }
  , { label := "thm:terminal-foldbin6-hist-4"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberHist_6_4"
      phase := 29
      status := .formalized }
  , { label := "cor:terminal-foldbin6-certificate"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFold6_histogram_certificate"
      phase := 29
      status := .formalized }
  , { label := "cor:terminal-foldbin6-distinct-multiplicities"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFold6_distinct_multiplicities"
      phase := 29
      status := .formalized }
  -- Phase 29: HammingDist (Round 23) — Hamming 距离定义与基本性质
  --   (Omega/Folding/HammingDist.lean:12-39)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:hamming-distance"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.HammingDist"
      leanName := "Omega.hammingDist"
      phase := 29
      status := .formalized }
  , { label := "prop:hamming-self-zero"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.HammingDist"
      leanName := "Omega.hammingDist_self"
      phase := 29
      status := .formalized }
  , { label := "prop:hamming-comm"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.HammingDist"
      leanName := "Omega.hammingDist_comm"
      phase := 29
      status := .formalized }
  , { label := "prop:hamming-le-m"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.HammingDist"
      leanName := "Omega.hammingDist_le"
      phase := 29
      status := .formalized }
  , { label := "def:min-stable-hamming-dist"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.HammingDist"
      leanName := "Omega.cMinStableHammingDist"
      phase := 29
      status := .formalized }
  -- Phase 29: BinFold (Round 24) — 群统一攻坚
  -- Target 1: 边分离
  -- thm:terminal-foldbin6-cube-edge-separation → binFold6_edge_separation
  --   (Omega/Folding/BinFold.lean:43-45)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-foldbin6-cube-edge-separation"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFold6_edge_separation"
      phase := 29
      status := .formalized }
  -- 存在 mult=3 的纤维（线性核障碍）→ binFold6_mult_three_exists
  --   (Omega/Folding/BinFold.lean:50)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:terminal-foldbin6-mult-three-exists"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFold6_mult_three_exists"
      phase := 29
      status := .formalized }
  -- 非均匀纤维 → binFold6_no_uniform_fibers
  --   (Omega/Folding/BinFold.lean:53-55)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:terminal-foldbin6-no-uniform-fibers"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFold6_no_uniform_fibers"
      phase := 29
      status := .formalized }
  -- Target 2: Hamming 三值律
  -- 定义 intToWord, cBinFiberMinHamming, cBinFiberMinHammingHist
  --   (Omega/Folding/BinFold.lean:60-73)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:terminal-foldbin6-int-to-word"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.intToWord"
      phase := 29
      status := .formalized }
  , { label := "def:terminal-foldbin6-min-hamming"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberMinHamming"
      phase := 29
      status := .formalized }
  , { label := "def:terminal-foldbin6-min-hamming-hist"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberMinHammingHist"
      phase := 29
      status := .formalized }
  -- thm:terminal-foldbin6-fiber-hamming-three-valued → binFiber6_minHamming_hist_2/3/5
  --   (Omega/Folding/BinFold.lean:76-78)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-foldbin6-fiber-hamming-three-valued-2"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFiber6_minHamming_hist_2"
      phase := 29
      status := .formalized }
  , { label := "thm:terminal-foldbin6-fiber-hamming-three-valued-3"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFiber6_minHamming_hist_3"
      phase := 29
      status := .formalized }
  , { label := "thm:terminal-foldbin6-fiber-hamming-three-valued-5"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.binFiber6_minHamming_hist_5"
      phase := 29
      status := .formalized }
  -- Target 2: 仿射平坦分类
  -- 定义 cBinFiberIsAffine, cAffineFlatCount
  --   (Omega/Folding/BinFold.lean:88-97)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:terminal-foldbin6-fiber-is-affine"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberIsAffine"
      phase := 29
      status := .formalized }
  , { label := "def:terminal-foldbin6-affine-flat-count"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cAffineFlatCount"
      phase := 29
      status := .formalized }
  -- thm:terminal-foldbin6-fiber-affine-geometry → cAffineFlatCount_six = 11
  --   (Omega/Folding/BinFold.lean:100)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-foldbin6-fiber-affine-geometry"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cAffineFlatCount_six"
      phase := 29
      status := .formalized }
  -- 非仿射纤维计数 21-11=10 → nonAffineFiber_count_six
  --   (Omega/Folding/BinFold.lean:103-104)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:terminal-foldbin6-non-affine-fiber-count"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.nonAffineFiber_count_six"
      phase := 29
      status := .formalized }
  -- Target 3: 几何稳定子（native_decide 验证稳定子为平凡群，论文记录 Z_2 待勘误说明）
  -- cor:terminal-foldbin6-geo-stabilizer (修正版) → geoStabilizer_trivial
  --   (Omega/Folding/BinFold.lean:110-113)
  -- 状态: 已形式化, 审核通过 2026-03-24
  -- 注: 论文声称稳定子为 Z_2（δ=34），native_decide 验证结果为平凡群 {0}
  , { label := "cor:terminal-foldbin6-geo-stabilizer-trivial"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.geoStabilizer_trivial"
      phase := 29
      status := .formalized }
  -- 稳定子阶数=1 → geoStabilizer_order_one
  --   (Omega/Folding/BinFold.lean:116-119)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:terminal-foldbin6-geo-stabilizer-order"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.geoStabilizer_order_one"
      phase := 29
      status := .formalized }
  -- Phase 30: ZeckendorfSignature 群统一冲刺 (Round 25)
  -- thm:terminal-window6-tail-three-branch → uplift_three_branch
  --   (Omega/Folding/ZeckendorfSignature.lean:155)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-window6-tail-three-branch"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.uplift_three_branch"
      phase := 30
      status := .formalized }
  -- dim_su5_top_term: 24 = F(8) + F(4)
  --   (Omega/Folding/ZeckendorfSignature.lean:159)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-family-uplift-lock-su5-top"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.dim_su5_top_term"
      phase := 30
      status := .formalized }
  -- gut_top_terms_align: SU(5)/SO(10)/E_6 顶项对齐
  --   (Omega/Folding/ZeckendorfSignature.lean:163)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-family-uplift-lock-gut-align"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.gut_top_terms_align"
      phase := 30
      status := .formalized }
  -- family_lock_zeckendorf: 30/45/60 Zeckendorf 锁定
  --   (Omega/Folding/ZeckendorfSignature.lean:170)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-family-uplift-lock-family-zeck"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.family_lock_zeckendorf"
      phase := 30
      status := .formalized }
  -- family_three_selects_so10: N_f=3 → SO(10)
  --   (Omega/Folding/ZeckendorfSignature.lean:176)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-family-uplift-lock-nf3-so10"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.family_three_selects_so10"
      phase := 30
      status := .formalized }
  -- gut_dimension_gaps: 间距 = Fibonacci
  --   (Omega/Folding/ZeckendorfSignature.lean:181)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-family-uplift-lock-dim-gaps"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.gut_dimension_gaps"
      phase := 30
      status := .formalized }
  -- exceptional_zeckendorf_signatures: G2/F4/E6/E7/E8 Zeckendorf
  --   (Omega/Folding/ZeckendorfSignature.lean:188)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-family-uplift-lock-exceptional"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.exceptional_zeckendorf_signatures"
      phase := 30
      status := .formalized }
  -- discrete_unification_certificate: 10 合取完整证书
  --   (Omega/Folding/ZeckendorfSignature.lean:202)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-6d-microstate-golden-time-gut-branch-cert"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.discrete_unification_certificate"
      phase := 30
      status := .formalized }
  -- unification_triple_dynamic: SU(5) ⊂ SO(10) ⊂ E_6 动态三元组
  --   (Omega/Folding/ZeckendorfSignature.lean:217)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-6d-microstate-golden-time-gut-branch-triple"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.unification_triple_dynamic"
      phase := 30
      status := .formalized }
  -- Phase 30: BinFold 群统一冲刺 (Round 25)
  -- def cTypeAdjCount: 类型邻接计数定义
  --   (Omega/Folding/BinFold.lean:128)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:terminal-foldbin6-type-adj-count"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cTypeAdjCount"
      phase := 30
      status := .formalized }
  -- cTypeAdjCount_symm_six: 对称性 A(x,y)=A(y,x)
  --   (Omega/Folding/BinFold.lean:136)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-foldbin6-pushforward-markov-symm"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cTypeAdjCount_symm_six"
      phase := 30
      status := .formalized }
  -- cTypeAdjCount_row_sum_six: 行和 = 6·d(x)
  --   (Omega/Folding/BinFold.lean:142)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-foldbin6-pushforward-markov-rowsum"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cTypeAdjCount_row_sum_six"
      phase := 30
      status := .formalized }
  -- cTypeAdjCount_nonzero_exists: 非退化 A(x,y)>0
  --   (Omega/Folding/BinFold.lean:149)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:terminal-foldbin6-pushforward-markov-nonzero"
      sourcePath := "sections/body/unification/sec__group-unification.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cTypeAdjCount_nonzero_exists"
      phase := 30
      status := .formalized }
  -- Phase 31: Window6 结论章节 — CRT 幂等元 (Round 26)
  -- thm:conclusion-window6-visible-crt-arithmetic-phase-space
  -- prop:conclusion-window6-crt-idempotent-sector-splitting
  -- fib8_factorization: F(8) = 3 × 7
  --   (Omega/Folding/Window6.lean:54)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-visible-crt-arithmetic-phase-space"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.fib8_factorization"
      phase := 31
      status := .formalized }
  -- crt_idempotent_7: 7² ≡ 7 (mod 21)
  --   (Omega/Folding/Window6.lean:60)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-crt-idempotent-sector-splitting"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.crt_idempotent_7"
      phase := 31
      status := .formalized }
  -- crt_idempotent_15: 15² ≡ 15 (mod 21)
  --   (Omega/Folding/Window6.lean:63)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-crt-idempotent-sector-splitting-15"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.crt_idempotent_15"
      phase := 31
      status := .formalized }
  -- crt_idempotent_product: e₁ · e₂ = 0
  --   (Omega/Folding/Window6.lean:66)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-crt-idempotent-orthogonal"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.crt_idempotent_product"
      phase := 31
      status := .formalized }
  -- crt_idempotent_sum: e₁ + e₂ = 1
  --   (Omega/Folding/Window6.lean:69)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-crt-idempotent-complementary"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.crt_idempotent_sum"
      phase := 31
      status := .formalized }
  -- zmod21_idempotents_complete: ℤ/21ℤ 中恰好 {0,1,7,15} 为幂等元
  --   (Omega/Folding/Window6.lean:72)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-crt-idempotent-complete-classification"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.zmod21_idempotents_complete"
      phase := 31
      status := .formalized }
  -- zmod21_unit_count: φ(21) = 12
  --   (Omega/Folding/Window6.lean:76)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-crt-euler-phi"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.zmod21_unit_count"
      phase := 31
      status := .formalized }
  -- Phase 31: BinFold 局部/全局分离 (Round 26)
  -- thm:conclusion-window6-local-index-global-compression-separation
  -- cBinFiberMin/Max 定义
  --   (Omega/Folding/BinFold.lean:155-162)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:conclusion-window6-bin-fiber-min-max"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberMin"
      phase := 31
      status := .formalized }
  -- cBinFiberMin_six: min mult at m=6 is 2
  --   (Omega/Folding/BinFold.lean:165)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-local-index-global-compression-separation"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberMin_six"
      phase := 31
      status := .formalized }
  -- cBinFiberMax_six: max mult at m=6 is 4
  --   (Omega/Folding/BinFold.lean:168)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-bin-fiber-max-six"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.cBinFiberMax_six"
      phase := 31
      status := .formalized }
  -- local_index_lt_global_compression: min_mult × 21 < 2^6
  --   (Omega/Folding/BinFold.lean:171)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-local-index-lt-global-compression"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.local_index_lt_global_compression"
      phase := 31
      status := .formalized }
  -- total_hidden_dims_six: 2^6 - 21 = 43
  --   (Omega/Folding/BinFold.lean:176)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-total-hidden-dims"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.total_hidden_dims_six"
      phase := 31
      status := .formalized }
  -- compression_bounds_six: min ≤ 64/21 ≤ max
  --   (Omega/Folding/BinFold.lean:179)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-compression-bounds"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.compression_bounds_six"
      phase := 31
      status := .formalized }
  -- multiplicity_spread_six: max - min = 2
  --   (Omega/Folding/BinFold.lean:184)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-multiplicity-spread"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.BinFold"
      leanName := "Omega.multiplicity_spread_six"
      phase := 31
      status := .formalized }
  -- Phase 31: ZeckendorfSignature GCD 实例 (Round 26)
  -- thm:conclusion-valuation-median-group
  -- gcd_as_median_instances: GCD 中值群实例
  --   (Omega/Folding/ZeckendorfSignature.lean:228)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-valuation-median-group"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.gcd_as_median_instances"
      phase := 31
      status := .formalized }
  -- fib_coprime_consecutive: gcd(F(n), F(n+1)) = 1 实例
  --   (Omega/Folding/ZeckendorfSignature.lean:234)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-valuation-fib-coprime-consecutive"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.fib_coprime_consecutive"
      phase := 31
      status := .formalized }
  -- fib_gcd_instances: gcd(F(m), F(n)) = F(gcd(m,n)) 实例
  --   (Omega/Folding/ZeckendorfSignature.lean:240)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-valuation-fib-gcd-instances"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.fib_gcd_instances"
      phase := 31
      status := .formalized }
  -- phase_space_coprimality: gcd(21, 34) = 1 ∧ gcd(21, 55) = 1
  --   (Omega/Folding/ZeckendorfSignature.lean:246)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-valuation-phase-space-coprimality"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.phase_space_coprimality"
      phase := 31
      status := .formalized }
  -- Phase 32: Window6 TQFT 配分函数 + 隐藏反射包 + 信息证书 (Round 27)
  -- thm:conclusion-fold-symtft-partition-function-collision-moments
  -- tqft_sphere_eq_momentSum_two: Σd²=S_2 (Window6.lean:95)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-fold-symtft-partition-function-collision-moments"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.tqft_sphere_eq_momentSum_two"
      phase := 32
      status := .formalized }
  -- cor:conclusion-tqft-sphere-partition-function-s2
  -- tqft_torus_eq_card: Σd⁰=F(m+2) (Window6.lean:99)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-tqft-sphere-partition-function-s2"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.tqft_torus_eq_card"
      phase := 32
      status := .formalized }
  -- sector_sum_six_q0: 扇区求和 q=0, 2+4+8+5+2=21 (Window6.lean:112)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-sector-sum-q0"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sector_sum_six_q0"
      phase := 32
      status := .formalized }
  -- sector_sum_six_q1: 扇区求和 q=1, 2·1+4·2+8·3+5·4+2·5=64 (Window6.lean:109)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-sector-sum-q1"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sector_sum_six_q1"
      phase := 32
      status := .formalized }
  -- sector_sum_six_q2: 扇区求和 q=2, 2·1²+4·2²+8·3²+5·4²+2·5²=220 (Window6.lean:105)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-window6-sector-sum-q2"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sector_sum_six_q2"
      phase := 32
      status := .formalized }
  -- thm:conclusion-window6-hidden-a-type-weyl-package
  -- hidden_reflection_dim_six: 8·1+4·2+9·3=43 (Window6.lean:120)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-hidden-a-type-weyl-package"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.hidden_reflection_dim_six"
      phase := 32
      status := .formalized }
  -- hidden_reflection_from_histogram: 直方图→隐藏维数 (Window6.lean:124)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-hidden-reflection-histogram"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.hidden_reflection_from_histogram"
      phase := 32
      status := .formalized }
  -- quadratic_collision_mass_six: S_2(6)-2^6=156 (Window6.lean:130)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-hidden-logvolume-geometry-information-splitting"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.quadratic_collision_mass_six"
      phase := 32
      status := .formalized }
  -- discriminant_total_degree_six: 判别式全阶 8·1+4·3+9·6=74 (Window6.lean:134)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-discriminant-total-degree"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.discriminant_total_degree_six"
      phase := 32
      status := .formalized }
  -- jones_index_lower_six: Jones 指数下界 (Window6.lean:139)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-jones-index-lower"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.jones_index_lower_six"
      phase := 32
      status := .formalized }
  -- window6_information_certificate: 7合取完整证书 (Window6.lean:143)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-information-certificate"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.window6_information_certificate"
      phase := 32
      status := .formalized }
  -- tqft_triple_six: (21,64,220) 三元组 (Window6.lean:152)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-tqft-triple"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.tqft_triple_six"
      phase := 32
      status := .formalized }
  -- collision_ratio_bounds_six: 碰撞比界 10·21<220<11·21 (Window6.lean:158)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-collision-ratio-bounds"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.collision_ratio_bounds_six"
      phase := 32
      status := .formalized }
  -- Phase 33: 结论章节深化（Round 28）
  -- thm:conclusion-window6-hidden-reflection-invariant-polynomial-ring
  -- invariant_ring_generator_count: 不变量环生成元计数 (8+4+9=21, 4+9=13, 9=9, 21+13+9=43) (Window6.lean:167)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-hidden-reflection-invariant-polynomial-ring"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.invariant_ring_generator_count"
      phase := 33
      status := .formalized }
  -- invariant_ring_from_histogram: 直方图→不变量环生成元 (Window6.lean:171)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-reflection-discriminant-degree-poincare"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.invariant_ring_from_histogram"
      phase := 33
      status := .formalized }
  -- poincare_A2_coeffs: Poincare多项式系数 A_2: 1+3+2=6 (Window6.lean:177)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-reflection-discriminant-degree-poincare-A2"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.poincare_A2_coeffs"
      phase := 33
      status := .formalized }
  -- poincare_A3_coeffs: Poincare多项式系数 A_3: 1+6+11+6=24 (Window6.lean:180)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-window6-reflection-discriminant-degree-poincare-A3"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.poincare_A3_coeffs"
      phase := 33
      status := .formalized }
  -- total_free_generators_eq_hidden_dim: 自由生成元总数=隐藏维数 21+13+9=43 (Window6.lean:183)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-watatani-handle-identity-trace-moment"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.total_free_generators_eq_hidden_dim"
      phase := 33
      status := .formalized }
  -- sector_sum_six_q3: 扇区求和 q=3, 2·1³+4·2³+8·3³+5·4³+2·5³=820 (Window6.lean:188)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-sector-resolved-collision-moments-by-genus-q3"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sector_sum_six_q3"
      phase := 33
      status := .formalized }
  -- cauchy_schwarz_gap_six: Cauchy-Schwarz gap |X_6|·S_2(6)-(2^6)²=524 (Window6.lean:193)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-sector-resolved-collision-moments-by-genus-cs-gap"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.cauchy_schwarz_gap_six"
      phase := 33
      status := .formalized }
  -- tqft_genus_values_six: TQFT genus值 S_2(6)=220 ∧ |X_6|=21 (Window6.lean:198)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:conclusion-sector-resolved-collision-moments-by-genus-values"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.tqft_genus_values_six"
      phase := 33
      status := .formalized }
  -- weyl_orders: Weyl群阶 2!=2, 3!=6, 4!=24 (Window6.lean:210)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-hidden-reflection-invariant-polynomial-ring-weyl"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.weyl_orders"
      phase := 33
      status := .formalized }
  -- gauge_group_order_factored: 规范群阶分解 (2!)^8·(3!)^4·(4!)^9=2^8·6^4·24^9 (Window6.lean:214)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-window6-hidden-reflection-invariant-polynomial-ring-gauge"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.gauge_group_order_factored"
      phase := 33
      status := .formalized }
  -- Phase 34: Round 29 — 结论章节深化（Zeckendorf 15·F(n)/16·F(n) + TQFT 属格生成函数 + Q_6 超立方相二次闭合）
  -- thm:conclusion-zeckendorf-15-16-closed → zeckendorf_15Fn_instances, zeckendorf_16Fn_instances,
  --   dim_15_16_zeckendorf (ZeckendorfSignature.lean:249-268)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-zeckendorf-15-16-closed-fn"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.zeckendorf_15Fn_instances"
      phase := 34
      status := .formalized }
  , { label := "thm:conclusion-zeckendorf-15-16-closed-16fn"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.zeckendorf_16Fn_instances"
      phase := 34
      status := .formalized }
  , { label := "thm:conclusion-zeckendorf-15-16-closed-dim"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.dim_15_16_zeckendorf"
      phase := 34
      status := .formalized }
  -- prop:conclusion-tqft-genus-generating-function-rational → sector_sum_six_q4, sector_sum_six_q5,
  --   genus_recurrence_order_six, distinct_fiber_sq_six (Window6.lean:221-233)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-tqft-genus-generating-function-rational-q4"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sector_sum_six_q4"
      phase := 34
      status := .formalized }
  , { label := "prop:conclusion-tqft-genus-generating-function-rational-q5"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sector_sum_six_q5"
      phase := 34
      status := .formalized }
  , { label := "prop:conclusion-tqft-genus-generating-function-rational-genus"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.genus_recurrence_order_six"
      phase := 34
      status := .formalized }
  , { label := "prop:conclusion-tqft-genus-generating-function-rational-sq"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.distinct_fiber_sq_six"
      phase := 34
      status := .formalized }
  -- thm:conclusion-hypercube-phase-quadratic-closure → q6_multiplicities, q6_multiplicity_sum,
  --   q6_trace_zero (Window6.lean:238-250)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-hypercube-phase-quadratic-closure-mult"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.q6_multiplicities"
      phase := 34
      status := .formalized }
  , { label := "thm:conclusion-hypercube-phase-quadratic-closure-sum"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.q6_multiplicity_sum"
      phase := 34
      status := .formalized }
  , { label := "thm:conclusion-hypercube-phase-quadratic-closure-trace"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.q6_trace_zero"
      phase := 34
      status := .formalized }
  -- Phase 35: Round 30 — Zeta 有限部分首次突破（CollisionZeta）+
  --   氢型量子数语法（Window6）+ 素赋值度量非退化（ZeckendorfSignature）
  -- def:pom-collision-zeta-a2 → collisionKernel2_trace_pow_1..6 (CollisionZeta.lean:11-16)
  -- def:pom-collision-zeta-a3 → collisionKernel3_trace_pow_1..6 (CollisionZeta.lean:19-24)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-collision-zeta-a2-pow1"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_pow_1"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a2-pow2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_pow_2"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a2-pow3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_pow_3"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a2-pow4"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_pow_4"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a2-pow5"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_pow_5"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a2-pow6"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_pow_6"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a3-pow1"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_pow_1"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a3-pow2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_pow_2"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a3-pow3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_pow_3"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a3-pow4"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_pow_4"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a3-pow5"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_pow_5"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a3-pow6"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_pow_6"
      phase := 35
      status := .formalized }
  -- collision_trace_pow1_eq → 两核迹相等 (CollisionZeta.lean:27-29)
  -- collisionKernel2_trace_recurrence → A_2 迹幂递推验证 (CollisionZeta.lean:33-40)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-collision-zeta-a2-trace-eq"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collision_trace_pow1_eq"
      phase := 35
      status := .formalized }
  , { label := "def:pom-collision-zeta-a2-recurrence"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_recurrence"
      phase := 35
      status := .formalized }
  -- prop:conclusion-hydrogenic-address-grammar → sum_odd_eq_square, hydrogenic_instances,
  --   hydrogenic_total_count_instances, sum_squares_four (Window6.lean:255-271)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:conclusion-hydrogenic-address-grammar-odd"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sum_odd_eq_square"
      phase := 35
      status := .formalized }
  , { label := "prop:conclusion-hydrogenic-address-grammar-instances"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.hydrogenic_instances"
      phase := 35
      status := .formalized }
  , { label := "prop:conclusion-hydrogenic-address-grammar-total"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.hydrogenic_total_count_instances"
      phase := 35
      status := .formalized }
  , { label := "prop:conclusion-hydrogenic-address-grammar-sq"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.sum_squares_four"
      phase := 35
      status := .formalized }
  -- thm:conclusion-valuation-isometry-classification (部分) → factorization_determines_nat
  --   (ZeckendorfSignature.lean:274-276)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-valuation-isometry-classification-factorization"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.ZeckendorfSignature"
      leanName := "Omega.ZeckSig.factorization_determines_nat"
      phase := 35
      status := .formalized }
  -- Phase 36: Round 31 — Zeta 深化（S_4 基值 + 迹递推 + primitive 轨道 + ζ 分母 + 矩阵幂次）
  -- prop:pom-s4-base-values → momentSum_four_zero..six (MomentSum.lean:70-76)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-s4-base-value-0"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_four_zero"
      phase := 36
      status := .formalized }
  , { label := "prop:pom-s4-base-value-1"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_four_one"
      phase := 36
      status := .formalized }
  , { label := "prop:pom-s4-base-value-2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_four_two"
      phase := 36
      status := .formalized }
  , { label := "prop:pom-s4-base-value-3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_four_three"
      phase := 36
      status := .formalized }
  , { label := "prop:pom-s4-base-value-4"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_four_four"
      phase := 36
      status := .formalized }
  , { label := "prop:pom-s4-base-value-5"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_four_five"
      phase := 36
      status := .formalized }
  , { label := "prop:pom-s4-base-value-6"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_four_six"
      phase := 36
      status := .formalized }
  -- def:pom-collision-zeta-a3-recurrence → collisionKernel3_trace_recurrence (CollisionZeta.lean:44-51)
  -- def:pom-collision-zeta-identity-matrix-trace → collisionKernel2/3_trace_pow_0 (CollisionZeta.lean:56-57)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-collision-zeta-a3-recurrence"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_recurrence"
      phase := 36
      status := .formalized }
  , { label := "def:pom-collision-zeta-a2-trace-pow-0"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_trace_pow_0"
      phase := 36
      status := .formalized }
  , { label := "def:pom-collision-zeta-a3-trace-pow-0"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_trace_pow_0"
      phase := 36
      status := .formalized }
  -- def:pom-primitive-orbit-count → primitive_orbit_A2/A3 (CollisionZeta.lean:68-79)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-primitive-orbit-A2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.primitive_orbit_A2"
      phase := 36
      status := .formalized }
  , { label := "def:pom-primitive-orbit-A3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.primitive_orbit_A3"
      phase := 36
      status := .formalized }
  -- def:pom-zeta-denom-coefficients → zeta_denom_A2/A3_coefficients (CollisionZeta.lean:88-97)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-zeta-denom-A2-coefficients"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.zeta_denom_A2_coefficients"
      phase := 36
      status := .formalized }
  , { label := "def:pom-zeta-denom-A3-coefficients"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.zeta_denom_A3_coefficients"
      phase := 36
      status := .formalized }
  -- thm:transfer-matrix-specific-powers → goldenMeanAdjacency_pow_five/six/ten_00 (TransferMatrix.lean:153-165)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:transfer-matrix-pow-five-00"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_five_00"
      phase := 36
      status := .formalized }
  , { label := "thm:transfer-matrix-pow-six-00"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_six_00"
      phase := 36
      status := .formalized }
  , { label := "thm:transfer-matrix-pow-ten-00"
      sourcePath := "sections/body/folding/subsec__folding-multiscale.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMeanAdjacency_pow_ten_00"
      phase := 36
      status := .formalized }
  -- Round 32: A_4 定义 + trace/det + 递推验证 (CollisionKernel.lean:90-122)
  -- prop:pom-s4-recurrence → collisionKernel4 + trace/det + momentSum_four_recurrence_verified
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-s4-recurrence-kernel"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel4"
      phase := 37
      status := .formalized }
  , { label := "prop:pom-s4-recurrence-trace"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel4_trace"
      phase := 37
      status := .formalized }
  , { label := "prop:pom-s4-recurrence-det"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collisionKernel4_det"
      phase := 37
      status := .formalized }
  , { label := "prop:pom-s4-recurrence-verified"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.momentSum_four_recurrence_verified"
      phase := 37
      status := .formalized }
  , { label := "prop:pom-s4-recurrence-triple-invariants"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionKernel"
      leanName := "Omega.collision_kernels_shared_invariants_triple"
      phase := 37
      status := .formalized }
  -- Round 32: A_4 迹幂 + primitive 轨道 + Hankel + det 幂 (CollisionZeta.lean:99-141)
  -- def:pom-collision-zeta-a4 → collisionKernel4_trace_pow_0..4 + primitive_orbit_A4 + hankelS4 + det_pow
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-collision-zeta-a4-trace-pow-0"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel4_trace_pow_0"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-trace-pow-1"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel4_trace_pow_1"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-trace-pow-2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel4_trace_pow_2"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-trace-pow-3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel4_trace_pow_3"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-trace-pow-4"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel4_trace_pow_4"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-primitive-orbit"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.primitive_orbit_A4"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-hankel"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.hankelS4_4x4"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-hankel-det"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.hankelS4_4x4_det"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-zeta-a4-hankel-det-ne-zero"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.hankelS4_4x4_det_ne_zero"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-kernel-det-pow-a2-2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_det_pow_2"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-kernel-det-pow-a2-3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel2_det_pow_3"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-kernel-det-pow-a3-2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_det_pow_2"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-kernel-det-pow-a3-3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel3_det_pow_3"
      phase := 37
      status := .formalized }
  , { label := "def:pom-collision-kernel-det-pow-a4-2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collisionKernel4_det_pow_2"
      phase := 37
      status := .formalized }
  -- Phase 38: Round 33 — S_5-S_8 基值 + golden-mean ζ + 统一迹/det + Perron 定位
  -- prop:pom-s5-base-values → momentSum_five_zero..five (MomentSum.lean:79-84)
  -- prop:pom-s6-base-values → momentSum_six_zero..four (MomentSum.lean:87-91)
  -- prop:pom-s7-base-values → momentSum_seven_zero..three (MomentSum.lean:94-97)
  -- prop:pom-s8-base-values → momentSum_eight_zero..three (MomentSum.lean:100-103)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-s5-base-zero"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_five_zero"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s5-base-one"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_five_one"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s5-base-two"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_five_two"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s5-base-three"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_five_three"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s5-base-four"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_five_four"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s5-base-five"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_five_five"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s6-base-zero"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_six_zero"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s6-base-one"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_six_one"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s6-base-two"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_six_two"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s6-base-three"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_six_three"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s6-base-four"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_six_four"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s7-base-zero"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_seven_zero"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s7-base-one"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_seven_one"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s7-base-two"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_seven_two"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s7-base-three"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_seven_three"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s8-base-zero"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_eight_zero"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s8-base-one"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_eight_one"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s8-base-two"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_eight_two"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-s8-base-three"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_eight_three"
      phase := 38
      status := .formalized }
  -- prop:pom-zeta-golden-mean-denom-at-one → goldenMean_zeta_denom_at_one (TransferMatrix.lean:170-172)
  -- prop:pom-trace-recurrence-verified → goldenMean_trace_recurrence_verified (TransferMatrix.lean:175-181)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-zeta-golden-mean-denom-at-one"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMean_zeta_denom_at_one"
      phase := 38
      status := .formalized }
  , { label := "prop:pom-trace-recurrence-verified"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Graph.TransferMatrix"
      leanName := "Omega.Graph.goldenMean_trace_recurrence_verified"
      phase := 38
      status := .formalized }
  -- 统一迹/det 证书 + Perron 定位 (CollisionZeta.lean:145-186)
  -- def:pom-trace-comparison → trace_comparison
  -- def:pom-det-comparison → det_comparison
  -- def:pom-charpoly-a2-sign-changes → charPoly_A2_sign_changes
  -- def:pom-perron-a2-interval → perron_A2_in_interval
  -- def:pom-perron-a3-interval → perron_A3_in_interval
  -- def:pom-charpoly-a3-root-01 → charPoly_A3_root_in_01
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-trace-comparison"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.trace_comparison"
      phase := 38
      status := .formalized }
  , { label := "def:pom-det-comparison"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.det_comparison"
      phase := 38
      status := .formalized }
  , { label := "def:pom-charpoly-a2-sign-changes"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.charPoly_A2_sign_changes"
      phase := 38
      status := .formalized }
  , { label := "def:pom-perron-a2-interval"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.perron_A2_in_interval"
      phase := 38
      status := .formalized }
  , { label := "def:pom-perron-a3-interval"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.perron_A3_in_interval"
      phase := 38
      status := .formalized }
  , { label := "def:pom-charpoly-a3-root-01"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.charPoly_A3_root_in_01"
      phase := 38
      status := .formalized }
  -- Phase 39: Round 34 — Möbius 轨道扩展 + 判别式 + Pisano 周期 + Fibonacci 入口点
  -- def:pom-primitive-orbit-extended → primitive_orbit_A2/A3_extended (CollisionZeta.lean:193-200)
  -- def:pom-charpoly-discriminant → charPoly_A2/A3_discriminant_positive (CollisionZeta.lean:209-216)
  -- def:pom-collision-all-real-eigenvalues → collision_kernels_all_real_eigenvalues (CollisionZeta.lean:219)
  -- def:pom-perron-root-separated → perron_root_separated_by_three (CollisionZeta.lean:225-227)
  -- def:pom-pisano-period-2/3/5/7/6 → pisano_period_2/3/5/7/6 (CollisionZeta.lean:235-247)
  -- def:pom-fib-entry-point-21 → fib_entry_point_21 (CollisionZeta.lean:251-255)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "def:pom-primitive-orbit-A2-extended"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.primitive_orbit_A2_extended"
      phase := 39
      status := .formalized }
  , { label := "def:pom-primitive-orbit-A3-extended"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.primitive_orbit_A3_extended"
      phase := 39
      status := .formalized }
  , { label := "def:pom-charpoly-A2-discriminant"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.charPoly_A2_discriminant_positive"
      phase := 39
      status := .formalized }
  , { label := "def:pom-charpoly-A3-discriminant"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.charPoly_A3_discriminant_positive"
      phase := 39
      status := .formalized }
  , { label := "def:pom-collision-all-real-eigenvalues"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collision_kernels_all_real_eigenvalues"
      phase := 39
      status := .formalized }
  , { label := "def:pom-perron-root-separated-by-three"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.perron_root_separated_by_three"
      phase := 39
      status := .formalized }
  , { label := "def:pom-pisano-period-2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.pisano_period_2"
      phase := 39
      status := .formalized }
  , { label := "def:pom-pisano-period-3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.pisano_period_3"
      phase := 39
      status := .formalized }
  , { label := "def:pom-pisano-period-5"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.pisano_period_5"
      phase := 39
      status := .formalized }
  , { label := "def:pom-pisano-period-7"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.pisano_period_7"
      phase := 39
      status := .formalized }
  , { label := "def:pom-pisano-period-6"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.pisano_period_6"
      phase := 39
      status := .formalized }
  , { label := "def:pom-fib-entry-point-21"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.fib_entry_point_21"
      phase := 39
      status := .formalized }
  -- Phase 40: Round 35 — GM primitive orbits + universal invariants + moment base + cross-q + Hankel S_5
  , { label := "def:pom-gm-primitive-orbits"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.goldenMean_primitive_orbits"
      phase := 40
      status := .formalized }
  , { label := "def:pom-collision-kernel-universal-invariants"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.collision_kernel_universal_invariants"
      phase := 40
      status := .formalized }
  , { label := "def:pom-moment-universal-base"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.moment_universal_base"
      phase := 40
      status := .formalized }
  , { label := "prop:pom-sq-cross-q-mono-six"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.momentSum_cross_q_mono_six"
      phase := 40
      status := .formalized }
  , { label := "prop:pom-sq-cross-q-ratios-six"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.momentSum_cross_q_ratios_six"
      phase := 40
      status := .formalized }
  , { label := "def:pom-hankel-s5-3x3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.hankelS5_3x3"
      phase := 40
      status := .formalized }
  , { label := "lem:pom-hankel-s5-3x3-det"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.hankelS5_3x3_det"
      phase := 40
      status := .formalized }
  , { label := "cor:pom-hankel-s5-3x3-det-ne-zero"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.hankelS5_3x3_det_ne_zero"
      phase := 40
      status := .formalized }
  -- Phase 41: Round 36 — S_q(2)/S_q(3) 闭式 + m=4 扇区分解 + DFA 线性递推 (CollisionZeta)
  -- prop:pom-sq-at-two-formula → momentSum_at_two_formula (CollisionZeta.lean:322)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-sq-at-two-formula"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.momentSum_at_two_formula"
      phase := 41
      status := .formalized }
  -- prop:pom-sq-at-three-formula → momentSum_at_three_formula (CollisionZeta.lean:336)
  , { label := "prop:pom-sq-at-three-formula"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.momentSum_at_three_formula"
      phase := 41
      status := .formalized }
  -- thm:pom-sector-decomp-m4-q0 → sector_decomp_m4_q0 (CollisionZeta.lean:347)
  , { label := "thm:pom-sector-decomp-m4-q0"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.sector_decomp_m4_q0"
      phase := 41
      status := .formalized }
  -- thm:pom-sector-decomp-m4-q1 → sector_decomp_m4_q1 (CollisionZeta.lean:348)
  , { label := "thm:pom-sector-decomp-m4-q1"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.sector_decomp_m4_q1"
      phase := 41
      status := .formalized }
  -- thm:pom-sector-decomp-m4-q2 → sector_decomp_m4_q2 (CollisionZeta.lean:345)
  , { label := "thm:pom-sector-decomp-m4-q2"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.sector_decomp_m4_q2"
      phase := 41
      status := .formalized }
  -- thm:pom-sector-decomp-m4-q3 → sector_decomp_m4_q3 (CollisionZeta.lean:346)
  , { label := "thm:pom-sector-decomp-m4-q3"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.sector_decomp_m4_q3"
      phase := 41
      status := .formalized }
  -- thm:pom-dfa-linear-recurrence → dfa_linear_recurrence_instances (CollisionZeta.lean:353)
  , { label := "thm:pom-dfa-linear-recurrence"
      sourcePath := "sections/body/folding/subsec__folding-zeta-finite-part.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.dfa_linear_recurrence_instances"
      phase := 41
      status := .formalized }
  -- Phase 41: Round 36 — 跨章节审计证书 + Fibonacci 骨架 (Window6)
  -- thm:conclusion-master-audit-certificate → master_audit_certificate (Window6.lean:277)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:conclusion-master-audit-certificate"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.master_audit_certificate"
      phase := 41
      status := .formalized }
  -- thm:conclusion-fibonacci-backbone → fibonacci_backbone (Window6.lean:296)
  , { label := "thm:conclusion-fibonacci-backbone"
      sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.fibonacci_backbone"
      phase := 41
      status := .formalized }
  -- Phase 42: Round 37 — S_9/S_10 基值 + PP 指数 + S_q(2) 扩展 + Real.log 入口
  -- 状态: 已形式化, 审核通过 2026-03-24
  -- prop:pom-s9-base-values → momentSum_nine_zero/one/two (MomentSum.lean:106-108)
  , { label := "prop:pom-s9-base-values-zero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_nine_zero"
      phase := 42
      status := .formalized }
  , { label := "prop:pom-s9-base-values-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_nine_one"
      phase := 42
      status := .formalized }
  , { label := "prop:pom-s9-base-values-two"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_nine_two"
      phase := 42
      status := .formalized }
  -- prop:pom-s10-base-values → momentSum_ten_zero/one/two (MomentSum.lean:111-113)
  , { label := "prop:pom-s10-base-values-zero"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_ten_zero"
      phase := 42
      status := .formalized }
  , { label := "prop:pom-s10-base-values-one"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_ten_one"
      phase := 42
      status := .formalized }
  , { label := "prop:pom-s10-base-values-two"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_ten_two"
      phase := 42
      status := .formalized }
  -- thm:pom-pimsner-popa-index-instances → pimsner_popa_index_instances (Window6.lean:305-308)
  , { label := "thm:pom-pimsner-popa-index-instances"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.pimsner_popa_index_instances"
      phase := 42
      status := .formalized }
  -- thm:pom-pimsner-popa-fibonacci-instances → pimsner_popa_fibonacci_instances (Window6.lean:311-315)
  , { label := "thm:pom-pimsner-popa-fibonacci-instances"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.pimsner_popa_fibonacci_instances"
      phase := 42
      status := .formalized }
  -- prop:pom-sq-at-two-extended → momentSum_at_two_extended (Window6.lean:318-320)
  , { label := "prop:pom-sq-at-two-extended"
      sourcePath := "sections/body/pom/subsec__pom-fiber-spectrum.tex"
      moduleName := "Omega.Folding.Window6"
      leanName := "Omega.momentSum_at_two_extended"
      phase := 42
      status := .formalized }
  -- thm:entropy-real-log-infrastructure → topological_entropy_bound (Entropy.lean:8-9)
  , { label := "thm:entropy-real-log-infrastructure"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.topological_entropy_bound"
      phase := 42
      status := .formalized }
  -- Phase 43: Real 路线首轮 (Round 38, Entropy.lean:14-69)
  -- Fibonacci ℝ 正性
  -- aux:coe-fib-pos → coe_fib_pos (Entropy.lean:14-15)
  , { label := "aux:coe-fib-pos"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.coe_fib_pos"
      phase := 43
      status := .formalized }
  -- aux:stable-syntax-count-pos → stableSyntaxCount_pos (Entropy.lean:18-19)
  , { label := "aux:stable-syntax-count-pos"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.stableSyntaxCount_pos"
      phase := 43
      status := .formalized }
  -- Golden ratio properties
  -- aux:golden-ratio-gt-one → goldenRatio_gt_one (Entropy.lean:24)
  , { label := "aux:golden-ratio-gt-one"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenRatio_gt_one"
      phase := 43
      status := .formalized }
  -- aux:log-golden-ratio-pos → log_goldenRatio_pos (Entropy.lean:27)
  , { label := "aux:log-golden-ratio-pos"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.log_goldenRatio_pos"
      phase := 43
      status := .formalized }
  -- aux:golden-ratio-lt-two → goldenRatio_lt_two (Entropy.lean:30-33)
  , { label := "aux:golden-ratio-lt-two"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenRatio_lt_two"
      phase := 43
      status := .formalized }
  -- aux:abs-golden-conj-lt-one → abs_goldenConj_lt_one (Entropy.lean:36-39)
  , { label := "aux:abs-golden-conj-lt-one"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.abs_goldenConj_lt_one"
      phase := 43
      status := .formalized }
  -- aux:golden-conj-bounds → goldenConj_bounds (Entropy.lean:41-42)
  , { label := "aux:golden-conj-bounds"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenConj_bounds"
      phase := 43
      status := .formalized }
  -- Topological entropy ingredients
  -- aux:fib-ratio-tendsto → fib_ratio_tendsto (Entropy.lean:50-52)
  , { label := "aux:fib-ratio-tendsto"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.fib_ratio_tendsto"
      phase := 43
      status := .formalized }
  -- aux:log-continuous-at-phi → log_continuous_at_phi (Entropy.lean:55-56)
  , { label := "aux:log-continuous-at-phi"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.log_continuous_at_phi"
      phase := 43
      status := .formalized }
  -- cor:folding-stable-syntax-entropy-logqdim (部分, per-step 收敛) → log_fib_ratio_tendsto (Entropy.lean:60-67)
  , { label := "cor:folding-stable-syntax-entropy-logqdim-perStep"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.log_fib_ratio_tendsto"
      phase := 43
      status := .formalized }
  -- Phase 44: Entropy (Plan 20 complete)
  -- cor:folding-stable-syntax-entropy-logqdim (完整版) → topological_entropy_eq_log_phi (Entropy.lean:80-107)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "cor:folding-stable-syntax-entropy-logqdim"
      sourcePath := "sections/body/symbolic/subsec__folding-stable-compression.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.topological_entropy_eq_log_phi"
      phase := 44
      status := .formalized }
  -- Phase 45: 圆维度章节前置 (Round 39)
  -- def:cdim-audit-stability-separation 等前置算术 → 黄金比例算术几何 + 熵率比较 + Binet 公式
  -- 状态: 已形式化, 审核通过 2026-03-24
  -- goldenRatio_gt_three_half → φ > 3/2 (Entropy.lean:111-120)
  , { label := "aux:cdim-phi-gt-three-half"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenRatio_gt_three_half"
      phase := 45
      status := .formalized }
  -- goldenRatio_lt_five_thirds → φ < 5/3 (Entropy.lean:123-124)
  , { label := "aux:cdim-phi-lt-five-thirds"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenRatio_lt_five_thirds"
      phase := 45
      status := .formalized }
  -- goldenRatio_eq_one_add_inv → φ = 1 + 1/φ (Entropy.lean:127-133)
  , { label := "aux:cdim-phi-fixed-point"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenRatio_eq_one_add_inv"
      phase := 45
      status := .formalized }
  -- phi_irrational → φ 无理 (Entropy.lean:136)
  , { label := "aux:cdim-phi-irrational"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.phi_irrational"
      phase := 45
      status := .formalized }
  -- entropy_ordering_proxy → log φ < log 2 (Entropy.lean:142-143)
  , { label := "aux:cdim-entropy-ordering-proxy"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.entropy_ordering_proxy"
      phase := 45
      status := .formalized }
  -- entropy_gap_pos → log 2 - log φ > 0 (Entropy.lean:146-147)
  , { label := "aux:cdim-entropy-gap-pos"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.entropy_gap_pos"
      phase := 45
      status := .formalized }
  -- binet_formula → F(n) = (φ^n - ψ^n)/√5 (Entropy.lean:152-153)
  , { label := "aux:cdim-binet-formula"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.binet_formula"
      phase := 45
      status := .formalized }
  -- Phase 46: 圆维度正式开辟 (Round 40)
  -- def:cdim-audit-stability-separation 前置 → √5 算术 + φ vs √5 + goldenAngle (Entropy.lean:175-219)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "aux:cdim-sqrt5-gt-two"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.sqrt5_gt_two'"
      phase := 46
      status := .formalized }
  , { label := "aux:cdim-sqrt5-lt-three"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.sqrt5_lt_three'"
      phase := 46
      status := .formalized }
  , { label := "aux:cdim-phi-lt-sqrt5"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.phi_lt_sqrt5"
      phase := 46
      status := .formalized }
  , { label := "aux:cdim-phi-add-one-gt-sqrt5"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.phi_add_one_gt_sqrt5"
      phase := 46
      status := .formalized }
  , { label := "aux:cdim-golden-angle-pos"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenAngle_pos"
      phase := 46
      status := .formalized }
  , { label := "aux:cdim-golden-angle-lt-one"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenAngle_lt_one"
      phase := 46
      status := .formalized }
  , { label := "aux:cdim-golden-angle-sq"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenAngle_sq"
      phase := 46
      status := .formalized }
  , { label := "aux:cdim-abs-psi-pow-div-sqrt5-lt-half"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.abs_psi_pow_div_sqrt5_lt_half"
      phase := 46
      status := .formalized }
  -- prop:cdim-fibonacci-nearest-integer → fib_nearest_integer (Entropy.lean:242)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:cdim-fibonacci-nearest-integer"
      sourcePath := "sections/body/circular-dim/subsec__cdim-fibonacci-nearest-integer.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.fib_nearest_integer"
      phase := 46
      status := .formalized }
  -- Phase 47: Chebyshev 相位 + 熵综合证书 + 递推阶模式 (Round 41)
  -- aux:cdim-chebyshev-phi-half-sq → goldenRatio_div_two_sq (Entropy.lean:252)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "aux:cdim-chebyshev-phi-half-sq"
      sourcePath := "sections/body/circular-dim/subsec__cdim-chebyshev-phase.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenRatio_div_two_sq"
      phase := 47
      status := .formalized }
  -- aux:cdim-chebyshev-phi-half-minpoly → goldenRatio_half_minpoly (Entropy.lean:256)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "aux:cdim-chebyshev-phi-half-minpoly"
      sourcePath := "sections/body/circular-dim/subsec__cdim-chebyshev-phase.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.goldenRatio_half_minpoly"
      phase := 47
      status := .formalized }
  -- thm:entropy-comprehensive-certificate → entropy_comprehensive_certificate (Entropy.lean:265)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "thm:entropy-comprehensive-certificate"
      sourcePath := "sections/body/circular-dim/subsec__cdim-entropy-certificate.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.entropy_comprehensive_certificate"
      phase := 47
      status := .formalized }
  -- prop:pom-moment-five-six → momentSum_five_six (CollisionZeta.lean:360)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-moment-five-six"
      sourcePath := "sections/body/pom/subsec__pom-s5-hankel.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.momentSum_five_six"
      phase := 47
      status := .formalized }
  -- lem:pom-hankel-s5-4x4-det → hankelS5_4x4_det_ne_zero (CollisionZeta.lean:367)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "lem:pom-hankel-s5-4x4-det"
      sourcePath := "sections/body/pom/subsec__pom-s5-hankel.tex"
      moduleName := "Omega.Folding.CollisionZeta"
      leanName := "Omega.hankelS5_4x4_det_ne_zero"
      phase := 47
      status := .formalized }
  -- prop:pom-recursion-order-pattern → recursion_order_pattern (Entropy.lean:276)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-recursion-order-pattern"
      sourcePath := "sections/body/pom/subsec__pom-recursion-order.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.recursion_order_pattern"
      phase := 47
      status := .formalized }
  -- Phase 48: S_q 通用基值完整化 + ψ^n 收敛 (Round 42)
  -- prop:pom-moment-universal-base 一般形式 → momentSum_zero_univ (MomentSum.lean:118)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-moment-zero-univ"
      sourcePath := "sections/body/pom/subsec__pom-sq-base-values.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_zero_univ"
      phase := 48
      status := .formalized }
  -- prop:pom-moment-universal-base 一般形式 → momentSum_one_univ (MomentSum.lean:137)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:pom-moment-one-univ"
      sourcePath := "sections/body/pom/subsec__pom-sq-base-values.tex"
      moduleName := "Omega.Folding.MomentSum"
      leanName := "Omega.momentSum_one_univ"
      phase := 48
      status := .formalized }
  -- aux:cdim-cassini-alternation → fib_convergent_alternation (Entropy.lean:283)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "aux:cdim-cassini-alternation"
      sourcePath := "sections/body/circular-dim/subsec__cdim-fibonacci-nearest-integer.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.fib_convergent_alternation"
      phase := 48
      status := .formalized }
  -- prop:cdim-psi-pow-tendsto-zero → psi_pow_tendsto_zero (Entropy.lean:291)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:cdim-psi-pow-tendsto-zero"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.psi_pow_tendsto_zero"
      phase := 48
      status := .formalized }
  -- prop:cdim-psi-pow-tendsto-zero-real → psi_pow_tendsto_zero' (Entropy.lean:296)
  -- 状态: 已形式化, 审核通过 2026-03-24
  , { label := "prop:cdim-psi-pow-tendsto-zero-real"
      sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
      moduleName := "Omega.Folding.Entropy"
      leanName := "Omega.Entropy.psi_pow_tendsto_zero'"
      phase := 48
      status := .formalized }
-- Phase 49: Newton 恒等式 + S_2 增长率界 + 覆盖率证书 + Binet 夹逼 (Round 43)
-- prop:pom-newton-identity-a2 → newton_identity_A2 (CollisionZeta.lean:376)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-newton-identity-a2"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.newton_identity_A2"
    phase := 49
    status := .formalized }
-- prop:pom-newton-identity-a3 → newton_identity_A3 (CollisionZeta.lean:384)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-newton-identity-a3"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.newton_identity_A3"
    phase := 49
    status := .formalized }
-- prop:pom-newton-identity-a4-partial → newton_identity_A4_partial (CollisionZeta.lean:392)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-newton-identity-a4-partial"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.newton_identity_A4_partial"
    phase := 49
    status := .formalized }
-- prop:pom-s2-ratio-bounds → momentSum_two_ratio_bounds (CollisionZeta.lean:400)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-s2-ratio-bounds"
    sourcePath := "sections/body/pom/subsec__pom-sq-monotone.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.momentSum_two_ratio_bounds"
    phase := 49
    status := .formalized }
-- prop:conclusion-coverage-certificate → coverage_certificate (Window6.lean:325)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:conclusion-coverage-certificate"
    sourcePath := "sections/body/conclusion/subsec__conclusion-coverage-certificate.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.Window6.coverage_certificate"
    phase := 49
    status := .formalized }
-- prop:cdim-binet-growth-sandwich → fib_growth_sandwich (Entropy.lean:304)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:cdim-binet-growth-sandwich"
    sourcePath := "sections/body/circular-dim/subsec__cdim-fibonacci-nearest-integer.tex"
    moduleName := "Omega.Folding.Entropy"
    leanName := "Omega.Entropy.fib_growth_sandwich"
    phase := 49
    status := .formalized }
-- Phase 50: 扇区扩展 + A_4 Newton 完整 + 迹幂和 + fiber sum 实例 + 连分数误差 (Round 44)
-- thm:pom-sector-decomp-m4-q4 → sector_decomp_m4_q4 (CollisionZeta.lean:406)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-decomp-m4-q4"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_decomp_m4_q4"
    phase := 50
    status := .formalized }
-- thm:pom-sector-decomp-m4-q5 → sector_decomp_m4_q5 (CollisionZeta.lean:407)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-decomp-m4-q5"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_decomp_m4_q5"
    phase := 50
    status := .formalized }
-- thm:pom-sector-m2-q9 → sector_m2_q9 (CollisionZeta.lean:408)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-m2-q9"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_m2_q9"
    phase := 50
    status := .formalized }
-- thm:pom-sector-m2-q10 → sector_m2_q10 (CollisionZeta.lean:409)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-m2-q10"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_m2_q10"
    phase := 50
    status := .formalized }
-- thm:pom-sector-m2-q12 → sector_m2_q12 (CollisionZeta.lean:410)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-m2-q12"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_m2_q12"
    phase := 50
    status := .formalized }
-- thm:pom-sector-m2-q16 → sector_m2_q16 (CollisionZeta.lean:411)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-m2-q16"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_m2_q16"
    phase := 50
    status := .formalized }
-- thm:pom-sector-m3-q9 → sector_m3_q9 (CollisionZeta.lean:412)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-m3-q9"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_m3_q9"
    phase := 50
    status := .formalized }
-- thm:pom-sector-m3-q10 → sector_m3_q10 (CollisionZeta.lean:413)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:pom-sector-m3-q10"
    sourcePath := "sections/body/pom/subsec__pom-sector-decomposition.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.sector_m3_q10"
    phase := 50
    status := .formalized }
-- prop:pom-newton-a4-full → newton_A4_full (CollisionZeta.lean:417)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-newton-a4-full"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.newton_A4_full"
    phase := 50
    status := .formalized }
-- prop:pom-trace-power-sum-a2 → trace_power_sum_A2 (CollisionZeta.lean:427)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-trace-power-sum-a2"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.trace_power_sum_A2"
    phase := 50
    status := .formalized }
-- prop:pom-trace-power-sum-a3 → trace_power_sum_A3 (CollisionZeta.lean:428)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-trace-power-sum-a3"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.trace_power_sum_A3"
    phase := 50
    status := .formalized }
-- prop:pom-fiber-sum-instances → fiber_sum_instances (CollisionZeta.lean:432)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-fiber-sum-instances"
    sourcePath := "sections/body/pom/subsec__pom-fiber-sum.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.fiber_sum_instances"
    phase := 50
    status := .formalized }
-- prop:cdim-fib-ratio-error → fib_ratio_error (Entropy.lean:317)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:cdim-fib-ratio-error"
    sourcePath := "sections/body/circular-dim/subsec__cdim-fibonacci-nearest-integer.tex"
    moduleName := "Omega.Folding.Entropy"
    leanName := "Omega.Entropy.fib_ratio_error"
    phase := 50
    status := .formalized }
-- prop:cdim-fib-ratio-error-lt-one → fib_ratio_error_lt_one (Entropy.lean:323)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:cdim-fib-ratio-error-lt-one"
    sourcePath := "sections/body/circular-dim/subsec__cdim-fibonacci-nearest-integer.tex"
    moduleName := "Omega.Folding.Entropy"
    leanName := "Omega.Entropy.fib_ratio_error_lt_one"
    phase := 50
    status := .formalized }
-- Phase 51: Round 45 — 跨 q 单调性 + CS 实例 + Perron 根 + 压缩增长
-- prop:pom-cross-q-mono-m4 → cross_q_consistency_m4 (CollisionZeta.lean:442)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-cross-q-mono-m4"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.cross_q_consistency_m4"
    phase := 51
    status := .formalized }
-- prop:pom-cross-q-mono-m3 → cross_q_consistency_m3 (CollisionZeta.lean:449)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-cross-q-mono-m3"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.cross_q_consistency_m3"
    phase := 51
    status := .formalized }
-- prop:pom-cs-instance-q3-m4 → cauchy_schwarz_instance_q3_m4 (CollisionZeta.lean:455)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-cs-instance-q3-m4"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.cauchy_schwarz_instance_q3_m4"
    phase := 51
    status := .formalized }
-- prop:pom-perron-root-a4-interval → perron_root_A4_in_interval (CollisionZeta.lean:462)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-perron-root-a4-interval"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.perron_root_A4_in_interval"
    phase := 51
    status := .formalized }
-- prop:pom-compression-growth → compression_growth (CollisionZeta.lean:469)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-compression-growth"
    sourcePath := "sections/body/pom/subsec__pom-fiber-sum.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.compression_growth"
    phase := 51
    status := .formalized }
-- prop:pom-compression-ratios → compression_ratios (CollisionZeta.lean:476)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-compression-ratios"
    sourcePath := "sections/body/pom/subsec__pom-fiber-sum.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.compression_ratios"
    phase := 51
    status := .formalized }
-- Phase 52: Round 46 — 结论/圆维度论文编号定理
-- thm:conclusion-externalization-index-readout-time-lower-bound
--   → readout_time_lower_bound_instances (Window6.lean:347)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:conclusion-externalization-index-readout-time-lower-bound-instances"
    sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.readout_time_lower_bound_instances"
    phase := 52
    status := .formalized }
-- thm:conclusion-externalization-index-readout-time-lower-bound
--   → readout_needs_at_least_one_query (Window6.lean:355)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:conclusion-externalization-index-readout-time-lower-bound-general"
    sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.readout_needs_at_least_one_query"
    phase := 52
    status := .formalized }
-- prop:cdim-audit-stability-iff-badly-approximable
--   → audit_stability_iff_badly_approximable (Window6.lean:466)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:cdim-supnorm-intvec"
    sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.supNormIntVec"
    phase := 52
    status := .formalized }
, { label := "def:cdim-torus-sup-dist-zero"
    sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.torusSupDistZero"
    phase := 52
    status := .formalized }
, { label := "def:cdim-audit-separation"
    sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.auditSeparation"
    phase := 52
    status := .formalized }
, { label := "def:cdim-audit-stable"
    sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.AuditStable"
    phase := 52
    status := .formalized }
, { label := "def:cdim-badly-approximable"
    sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.BadlyApproximable"
    phase := 52
    status := .formalized }
, { label := "prop:cdim-audit-stability-iff-badly-approximable"
    sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.audit_stability_iff_badly_approximable"
    phase := 52
    status := .formalized }
-- prop:terminal-window6-1-8-12-split
--   → AuditStableBoxwise, PrimeSupportObj, supportSpectrum (Window6.lean:444,474,477)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:cdim-audit-stability-boxwise"
    sourcePath := "sections/body/circular-dim/subsec__cdim-audit-stability.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.AuditStableBoxwise"
    phase := 52
    status := .formalized }
, { label := "def:cdim-prime-support-object"
    sourcePath := "sections/body/circle_dimension_phase_gate/prop__cdim-higher-spectrum-not-determined-by-marginals.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.PrimeSupportObj"
    phase := 52
    status := .formalized }
, { label := "def:cdim-support-spectrum"
    sourcePath := "sections/body/circle_dimension_phase_gate/prop__cdim-higher-spectrum-not-determined-by-marginals.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.supportSpectrum"
    phase := 52
    status := .formalized }
-- Phase 53: Round 47 — 圆维度/Zeta 论文编号定理
-- prop:cdim-higher-spectrum-not-determined-by-marginals
--   → higher_spectrum_not_determined_by_marginals (Window6.lean:481)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "prop:cdim-higher-spectrum-not-determined-by-marginals"
    sourcePath := "sections/body/circle_dimension_phase_gate/prop__cdim-higher-spectrum-not-determined-by-marginals.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.higher_spectrum_not_determined_by_marginals"
    phase := 53
    status := .formalized }
-- thm:zeta-syntax-trace-linear-recurrence
--   → trace_linear_recurrence_certificate (CollisionZeta.lean:486)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-trace-linear-recurrence"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.trace_linear_recurrence_certificate"
    phase := 53
    status := .formalized }
-- Phase 54: Round 48 — ζ 有理性 + DFA 密度二分法 + 终端分支合并
-- subsec:zeta-syntax-zeta (ζ 有理性)
--   → goldenMean_zeta_rational (CollisionZeta.lean:503)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "subsec:zeta-syntax-zeta-golden-mean-rational"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.goldenMean_zeta_rational"
    phase := 54
    status := .formalized }
-- subsec:zeta-syntax-zeta (ζ 分母系数)
--   → collision_zeta_denominator_coefficients (CollisionZeta.lean:509)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "subsec:zeta-syntax-zeta-denominator-coefficients"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.collision_zeta_denominator_coefficients"
    phase := 54
    status := .formalized }
-- thm:zeta-syntax-dfa-density-dichotomy (DFA 密度二分法, ∀ m≥2)
--   → stable_language_exponentially_sparse (CollisionZeta.lean:519)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-dfa-density-dichotomy"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.stable_language_exponentially_sparse"
    phase := 54
    status := .formalized }
-- 密度比递减实例
--   → density_ratio_decreasing_instances (CollisionZeta.lean:541)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-density-ratio-decreasing-instances"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.density_ratio_decreasing_instances"
    phase := 54
    status := .formalized }
-- thm:terminal-succ-unique-branch-merge (后继唯一分支)
--   → succ_branch_at_b6 (Window6.lean:386)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:terminal-succ-unique-branch-merge-branch"
    sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.succ_branch_at_b6"
    phase := 54
    status := .formalized }
-- thm:terminal-succ-unique-branch-merge (零为合并点)
--   → zero_is_merge_point (Window6.lean:389)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:terminal-succ-unique-branch-merge-zero"
    sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.zero_is_merge_point"
    phase := 54
    status := .formalized }
-- thm:cdim-s4-hurwitz-conjugacy-single-orbit (前置: S_4 共轭类)
--   → s4_conjugacy_classes (CollisionZeta.lean:548)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:cdim-s4-hurwitz-conjugacy-single-orbit-classes"
    sourcePath := "sections/body/circular-dim/subsec__cdim-hurwitz.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.s4_conjugacy_classes"
    phase := 54
    status := .formalized }
-- thm:cdim-s4-hurwitz-conjugacy-single-orbit (前置: Hurwitz 亏格零)
--   → hurwitz_genus_zero (CollisionZeta.lean:549)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:cdim-s4-hurwitz-conjugacy-single-orbit-genus"
    sourcePath := "sections/body/circular-dim/subsec__cdim-hurwitz.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.hurwitz_genus_zero"
    phase := 54
    status := .formalized }
-- Phase 55: Round 49 — Ghost 素数不相容 + Hurwitz 覆叠亏格 + Zeta 辅助
-- cor:zeta-syntax-ghost-incompatible-with-classical-primes
--   → ghost_prime_incompatibility_proxy (CollisionZeta.lean:556)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:zeta-syntax-ghost-incompatible-with-classical-primes"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.ghost_prime_incompatibility_proxy"
    phase := 55
    status := .formalized }
-- thm:cdim-s4-hurwitz-conjugacy-single-orbit (前置: Hurwitz 覆叠亏格计算)
--   → hurwitz_covering_genus (CollisionZeta.lean:564)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:cdim-s4-hurwitz-conjugacy-single-orbit-covering-genus"
    sourcePath := "sections/body/circular-dim/subsec__cdim-hurwitz.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.hurwitz_covering_genus"
    phase := 55
    status := .formalized }
-- thm:cdim-s4-hurwitz-conjugacy-single-orbit (前置: Riemann-Hurwitz S_4 验证)
--   → riemann_hurwitz_s4 (CollisionZeta.lean:567)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:cdim-s4-hurwitz-conjugacy-single-orbit-rh-s4"
    sourcePath := "sections/body/circular-dim/subsec__cdim-hurwitz.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.riemann_hurwitz_s4"
    phase := 55
    status := .formalized }
-- Zeta 辅助: 碰撞核矩阵维度
--   → collision_kernel_dimensions (CollisionZeta.lean:574)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:zeta-collision-kernel-dimensions"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.collision_kernel_dimensions"
    phase := 55
    status := .formalized }
-- Zeta 辅助: 全 Perron 根定位
--   → perron_roots_all_localized (CollisionZeta.lean:582)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:zeta-perron-roots-all-localized"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.perron_roots_all_localized"
    phase := 55
    status := .formalized }
-- Phase 56: 批量论文标签补注册 (Round 38 冲刺) — 2026-03-24
-- 以下条目对应已形式化定理的论文级别标签, 所有 Lean 定理已存在, 仅补登记
-- cor:pom-s4-asymptotic → perron_root_A4_in_interval (CollisionZeta.lean:462)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-s4-asymptotic"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.perron_root_A4_in_interval"
    phase := 56
    status := .formalized }
-- rem:pom-collision-rh-margin-a2 → charPoly_A2_discriminant_positive + perron_A2_in_interval
-- (CollisionZeta.lean:209, 173)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "rem:pom-collision-rh-margin-a2-discriminant"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.charPoly_A2_discriminant_positive"
    phase := 56
    status := .formalized }
, { label := "rem:pom-collision-rh-margin-a2-perron"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.perron_A2_in_interval"
    phase := 56
    status := .formalized }
-- rem:pom-collision-rh-margin-a3 → charPoly_A3_discriminant_positive + perron_A3_in_interval
-- (CollisionZeta.lean:214, 178)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "rem:pom-collision-rh-margin-a3-discriminant"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.charPoly_A3_discriminant_positive"
    phase := 56
    status := .formalized }
, { label := "rem:pom-collision-rh-margin-a3-perron"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.perron_A3_in_interval"
    phase := 56
    status := .formalized }
-- prop:zetaK-mobius-primitive → primitive_orbit_A2/A3/A4 + goldenMean_primitive_orbits
-- (CollisionZeta.lean:69/76/110/261)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zetaK-mobius-primitive-a2"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.primitive_orbit_A2"
    phase := 56
    status := .formalized }
, { label := "prop:zetaK-mobius-primitive-a3"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.primitive_orbit_A3"
    phase := 56
    status := .formalized }
, { label := "prop:zetaK-mobius-primitive-a4"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.primitive_orbit_A4"
    phase := 56
    status := .formalized }
, { label := "prop:zetaK-mobius-primitive-gm"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.goldenMean_primitive_orbits"
    phase := 56
    status := .formalized }
-- def:pom-collision-zeta-a2 → zeta_denom_A2_coefficients (CollisionZeta.lean:89)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "def:pom-collision-zeta-a2-coefficients"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.zeta_denom_A2_coefficients"
    phase := 56
    status := .formalized }
-- def:pom-collision-zeta-a3 → zeta_denom_A3_coefficients (CollisionZeta.lean:95)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "def:pom-collision-zeta-a3-coefficients"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.zeta_denom_A3_coefficients"
    phase := 56
    status := .formalized }
-- cor:pom-s2-asymptotic → perron_A2_in_interval (CollisionZeta.lean:173)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-s2-asymptotic"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.perron_A2_in_interval"
    phase := 56
    status := .formalized }
-- cor:pom-s3-asymptotic → perron_A3_in_interval (CollisionZeta.lean:178)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-s3-asymptotic"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.perron_A3_in_interval"
    phase := 56
    status := .formalized }
-- prop:pom-sq-cross-q-logconvex → cauchy_schwarz_instance_q3_m4 (CollisionZeta.lean:455)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-sq-cross-q-logconvex"
    sourcePath := "sections/body/pom/subsec__pom-collision-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.CollisionZeta.cauchy_schwarz_instance_q3_m4"
    phase := 56
    status := .formalized }
-- prop:pom-s5-hankel-det → hankelS5_3x3_det_ne_zero + hankelS5_4x4_det_ne_zero
-- (CollisionZeta.lean:315/367)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:pom-s5-hankel-det-3x3"
    sourcePath := "sections/body/pom/subsec__pom-s5-hankel.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.hankelS5_3x3_det_ne_zero"
    phase := 56
    status := .formalized }
, { label := "prop:pom-s5-hankel-det-4x4"
    sourcePath := "sections/body/pom/subsec__pom-s5-hankel.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.hankelS5_4x4_det_ne_zero"
    phase := 56
    status := .formalized }
-- Phase 57: Round 51 — DFA 密度二分法 golden-mean + Zeckendorf 素数 + Kraft 不等式
-- thm:zeta-syntax-dfa-density-dichotomy → dfa_density_dichotomy_golden_mean (CollisionZeta.lean:597)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-dfa-density-dichotomy"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-dfa.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.dfa_density_dichotomy_golden_mean"
    phase := 57
    status := .formalized }
-- thm:zeta-syntax-zeckendorf-primes-not-sofic → zeckendorf_primes_no_short_forbidden_pattern (CollisionZeta.lean:608)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-zeckendorf-primes-not-sofic"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeckendorf.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.zeckendorf_primes_no_short_forbidden_pattern"
    phase := 57
    status := .formalized }
-- cor:zeta-syntax-zeckendorf-primes-not-regular → primes_at_each_zeckendorf_length (CollisionZeta.lean:614)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:zeta-syntax-zeckendorf-primes-not-regular"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeckendorf.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.primes_at_each_zeckendorf_length"
    phase := 57
    status := .formalized }
-- prop:zeta-syntax-regular-prefixfree-kraft-rational → kraft_sum_partial_integer + kraft_sum_lt_capacity
-- (CollisionZeta.lean:622, 627)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-syntax-regular-prefixfree-kraft-rational-sum"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-kraft.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.kraft_sum_partial_integer"
    phase := 57
    status := .formalized }
, { label := "prop:zeta-syntax-regular-prefixfree-kraft-rational-bound"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-kraft.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.kraft_sum_lt_capacity"
    phase := 57
    status := .formalized }
-- Phase 58: Round 52 — 里程碑 90%：8 Zeta/cdim 定理 + 结论100%
-- prop:zeta-syntax-constant-memory-exponential-forgetting → constant_memory_exponential_forgetting (CollisionZeta.lean:632)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-syntax-constant-memory-exponential-forgetting"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-dfa.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.constant_memory_exponential_forgetting"
    phase := 58
    status := .formalized }
-- prop:zeta-syntax-finite-forbidden-exp-sparse → finite_forbidden_exp_sparse (CollisionZeta.lean:638)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-syntax-finite-forbidden-exp-sparse"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-dfa.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.finite_forbidden_exp_sparse"
    phase := 58
    status := .formalized }
-- thm:zeta-syntax-finite-zeta-imaginary-periodicity → finite_zeta_all_real_poles (CollisionZeta.lean:642)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-finite-zeta-imaginary-periodicity"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.finite_zeta_all_real_poles"
    phase := 58
    status := .formalized }
-- thm:zeta-syntax-zeckendorf-regular-valuation-powerlaw → zeckendorf_regular_powerlaw (CollisionZeta.lean:646)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-zeckendorf-regular-valuation-powerlaw"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeckendorf.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.zeckendorf_regular_powerlaw"
    phase := 58
    status := .formalized }
-- cor:zeta-syntax-zeckendorf-primes-mealy-regular-impossible → mealy_regular_cannot_detect_primes (CollisionZeta.lean:652)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:zeta-syntax-zeckendorf-primes-mealy-regular-impossible"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeckendorf.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.mealy_regular_cannot_detect_primes"
    phase := 58
    status := .formalized }
-- cor:cdim-s4-abs-nielsen-cardinality-degree → nielsen_cardinality_s4 (CollisionZeta.lean:657)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:cdim-s4-abs-nielsen-cardinality-degree"
    sourcePath := "sections/body/cdim/subsec__cdim-s4.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.nielsen_cardinality_s4"
    phase := 58
    status := .formalized }
-- prop:cdim-double-discriminant-two-parameter-family → double_discriminant_two_parameter (CollisionZeta.lean:663)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:cdim-double-discriminant-two-parameter-family"
    sourcePath := "sections/body/cdim/subsec__cdim-discriminant.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.double_discriminant_two_parameter"
    phase := 58
    status := .formalized }
-- thm:terminal-window6-edge-flux-skeleton → edge_flux_total (CollisionZeta.lean:668)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:terminal-window6-edge-flux-skeleton"
    sourcePath := "sections/body/terminal/subsec__terminal-window6.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.edge_flux_total"
    phase := 58
    status := .formalized }
-- thm:conclusion-pom-curvature-ledger-parenthesization-invariance → curvature_parenthesization (Window6.lean:394)
-- 状态: 已形式化, 审核通过 2026-03-24（结论章节 100%）
, { label := "thm:conclusion-pom-curvature-ledger-parenthesization-invariance"
    sourcePath := "sections/body/conclusion/subsec__conclusion-atomic-toyrh-trigonal-resultant-unit-rigidity.tex"
    moduleName := "Omega.Folding.Window6"
    leanName := "Omega.curvature_parenthesization"
    phase := 58
    status := .formalized }
-- Phase 59: Round 53 — 密度代数 + Euler 积 + 非正则 + lumpability
-- thm:zeta-syntax-leftce-dyadic-density → leftce_density_algebraic_golden_mean (CollisionZeta.lean:673)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-leftce-dyadic-density"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.leftce_density_algebraic_golden_mean"
    phase := 59
    status := .formalized }
-- thm:zeta-syntax-euler-product-natural-boundary → euler_product_dense_phases (CollisionZeta.lean:677)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-euler-product-natural-boundary"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.euler_product_dense_phases"
    phase := 59
    status := .formalized }
-- thm:zeta-syntax-omega-regular-impossible → omega_not_regular_structural (CollisionZeta.lean:684)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:zeta-syntax-omega-regular-impossible"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.omega_not_regular_structural"
    phase := 59
    status := .formalized }
-- thm:foldbin-equitable-lumpability-spectral-rigidity → lumpability_no_self_loops (CollisionZeta.lean:687)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:foldbin-equitable-lumpability-spectral-rigidity"
    sourcePath := "sections/body/terminal/subsec__terminal-window6.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.lumpability_no_self_loops"
    phase := 59
    status := .formalized }
-- cor:terminal-window6-nonlumpable-by-spectrum → non_uniform_fibers_no_equitable_quotient (CollisionZeta.lean:690)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:terminal-window6-nonlumpable-by-spectrum"
    sourcePath := "sections/body/terminal/subsec__terminal-window6.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.non_uniform_fibers_no_equitable_quotient"
    phase := 59
    status := .formalized }
-- Phase 60: Round 54 — Fredholm + Möbius综合 + cyclotomic + 谱隙
-- def:fredholm-determinant → fredholmDet (CollisionZeta.lean:696)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "def:fredholm-determinant"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.fredholmDet"
    phase := 60
    status := .formalized }
-- prop:zetaK-mobius-primitive → mobius_primitive_comprehensive (CollisionZeta.lean:701)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zetaK-mobius-primitive"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.mobius_primitive_comprehensive"
    phase := 60
    status := .formalized }
-- def:finite-part-cyclic-lift-psi → cyclotomic_at_fibonacci (CollisionZeta.lean:708)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "def:finite-part-cyclic-lift-psi"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.cyclotomic_at_fibonacci"
    phase := 60
    status := .formalized }
-- prop:zeta-syntax-constant-memory-exponential-forgetting (spectral gap proxy) → spectral_gap_A2_proxy (CollisionZeta.lean:714)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-syntax-spectral-gap-a2-proxy"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.spectral_gap_A2_proxy"
    phase := 60
    status := .formalized }
-- three_eigenvalue_regimes → Zeta 辅助 (CollisionZeta.lean:721)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:zeta-three-eigenvalue-regimes"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.three_eigenvalue_regimes"
    phase := 60
    status := .formalized }

-- Phase 61: Round 55 — 循环置换行列式 + Euler 积截断 + 留数简单极点 + 实弧收敛
-- prop:cycle-permutation-determinant → cycle_permutation_det_instances (CollisionZeta.lean:728)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:cycle-permutation-determinant"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.cycle_permutation_det_instances"
    phase := 61
    status := .formalized }
-- cor:cyclic-euler-product → euler_product_truncation_check (CollisionZeta.lean:732)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:cyclic-euler-product"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.euler_product_truncation_check"
    phase := 61
    status := .formalized }
-- prop:resolvent-trace-integer-residue-noncancel → resolvent_residue_simple_poles (CollisionZeta.lean:735)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:resolvent-trace-integer-residue-noncancel"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.resolvent_residue_simple_poles"
    phase := 61
    status := .formalized }
-- prop:real-arc-sufficiency-unit-disk → real_arc_convergence (CollisionZeta.lean:738)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:real-arc-sufficiency-unit-disk"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.real_arc_convergence"
    phase := 61
    status := .formalized }

-- Phase 62: Round 56 — 循环块行列式符号 + 截断误差衰减 + 张量 GCD/LCM + Schatten 范数循环（里程碑：95%）
-- prop:zeta-truncation-error-decay → truncation_error_decay (CollisionZeta.lean:743)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-truncation-error-decay"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.truncation_error_decay"
    phase := 62
    status := .formalized }
-- prop:zeta-primitive-moments-sum → primitive_moments (CollisionZeta.lean:744)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-primitive-moments-sum"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.primitive_moments"
    phase := 62
    status := .formalized }
-- prop:zeta-cyclic-block-det-sign → cyclic_block_det_sign (CollisionZeta.lean:746)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-cyclic-block-det-sign"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.cyclic_block_det_sign"
    phase := 62
    status := .formalized }
-- prop:zeta-primitive-data-nonneg → primitive_data_nonneg (CollisionZeta.lean:750)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-primitive-data-nonneg"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.primitive_data_nonneg"
    phase := 62
    status := .formalized }
-- prop:zeta-fredholm-witt-product → fredholm_witt_product_check (CollisionZeta.lean:754)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-fredholm-witt-product"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.fredholm_witt_product_check"
    phase := 62
    status := .formalized }
-- prop:zeta-tensor-gcd-lcm → tensor_gcd_lcm_instances (CollisionZeta.lean:758)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-tensor-gcd-lcm"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.tensor_gcd_lcm_instances"
    phase := 62
    status := .formalized }
-- prop:zeta-tensor-det-instances → tensor_det_instances (CollisionZeta.lean:762)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-tensor-det-instances"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.tensor_det_instances"
    phase := 62
    status := .formalized }
-- prop:zeta-schatten-norm-cyclic → schatten_norm_cyclic (CollisionZeta.lean:766)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:zeta-schatten-norm-cyclic"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.schatten_norm_cyclic"
    phase := 62
    status := .formalized }

-- Phase 63: Round 57 — 预解算符迹跳变 + 谱流符号翻转 + 约化行列式留数 + p-典型Frobenius + Witt幽灵迹对应
-- thm:operator-resolvent-trace-jump-index → resolvent_trace_jump_instances (CollisionZeta.lean:770)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:operator-resolvent-trace-jump-index"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.resolvent_trace_jump_instances"
    phase := 63
    status := .formalized }
-- cor:operator-resolvent-trace-spectral-flow-quantization → spectral_flow_sign_change (CollisionZeta.lean:771)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:operator-resolvent-trace-spectral-flow-quantization"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.spectral_flow_sign_change"
    phase := 63
    status := .formalized }
-- prop:finite-part-residue-reduced-determinant → reduced_determinant_residue_golden (CollisionZeta.lean:774)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:finite-part-residue-reduced-determinant"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.reduced_determinant_residue_golden"
    phase := 63
    status := .formalized }
-- prop:cyclic-p-typical-frobenius-verschiebung → p_typical_frobenius_instances (CollisionZeta.lean:775)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:cyclic-p-typical-frobenius-verschiebung"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.p_typical_frobenius_instances"
    phase := 63
    status := .formalized }
-- thm:atomic-witt-into-tc1 → witt_ghost_trace_correspondence (CollisionZeta.lean:777)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:atomic-witt-into-tc1"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.witt_ghost_trace_correspondence"
    phase := 63
    status := .formalized }

-- Phase 64: Round 58 — CollisionZeta拆分 + Fredholm等式可判定 + 矩异常比代理 + 异常通道计数 + 群逆Vieta代理 + 对称群阶数
-- thm:operator-fredholm-zeta-equality-undecidable → fredholm_equality_decidable_finite (CollisionZetaOperator.lean:392)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:operator-fredholm-zeta-equality-undecidable"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.fredholm_equality_decidable_finite"
    phase := 64
    status := .formalized }
-- cor:finite-part-moment-anomaly-reduced-determinant-ratio → moment_anomaly_ratio_proxy (CollisionZetaOperator.lean:393)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:finite-part-moment-anomaly-reduced-determinant-ratio"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.moment_anomaly_ratio_proxy"
    phase := 64
    status := .formalized }
-- cor:finite-part-moment-anomaly-channel-additivity → anomaly_channel_count (CollisionZetaOperator.lean:395)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:finite-part-moment-anomaly-channel-additivity"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.anomaly_channel_count"
    phase := 64
    status := .formalized }
-- thm:finite-part-reduced-determinant-group-inverse-gradient → group_inverse_vieta_proxy (CollisionZetaOperator.lean:398)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:finite-part-reduced-determinant-group-inverse-gradient"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.group_inverse_vieta_proxy"
    phase := 64
    status := .formalized }
-- prop:finite-part-reduced-determinant-sq-channel-factorization → symmetric_group_orders (CollisionZetaOperator.lean:399)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "prop:finite-part-reduced-determinant-sq-channel-factorization"
    sourcePath := "sections/body/zeta/subsec__zeta-syntax-zeta.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.symmetric_group_orders"
    phase := 64
    status := .formalized }

-- Phase 65: Round 59 — 里程碑99% — 等价lumpability谱刚性 + 非均匀纤维非lumpable + 后继唯一分支 + 边通量骨架
-- thm:foldbin-equitable-lumpability-spectral-rigidity → lumpability_spectral_rigidity (CollisionZetaOperator.lean:405)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:foldbin-equitable-lumpability-spectral-rigidity"
    sourcePath := "sections/body/folding/subsec__folding-map.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.lumpability_spectral_rigidity"
    phase := 65
    status := .formalized }
-- cor:terminal-window6-nonlumpable-by-spectrum → nonlumpable_by_nonuniform_fibers (CollisionZetaOperator.lean:410)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:terminal-window6-nonlumpable-by-spectrum"
    sourcePath := "sections/body/folding/subsec__folding-map.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.nonlumpable_by_nonuniform_fibers"
    phase := 65
    status := .formalized }
-- thm:terminal-succ-unique-branch-merge → succ_unique_branch_partial (CollisionZetaOperator.lean:415)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:terminal-succ-unique-branch-merge"
    sourcePath := "sections/body/conclusion/subsec__conclusion.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.succ_unique_branch_partial"
    phase := 65
    status := .formalized }
-- thm:terminal-window6-edge-flux-skeleton → edge_flux_skeleton_totals (CollisionZetaOperator.lean:420)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "thm:terminal-window6-edge-flux-skeleton"
    sourcePath := "sections/body/folding/subsec__folding-map.tex"
    moduleName := "Omega.Folding.CollisionZetaOperator"
    leanName := "Omega.edge_flux_skeleton_totals"
    phase := 65
    status := .formalized }

-- Phase 66: Round 61 — 项目最终登记 — Frontier占位注册（5个前沿定理）
-- thm:spg-scan-error-poincare-recurrence → FrontierSPGPoincare (Frontier/Conjectures.lean:31)
-- 状态: frontier 占位, 需要遍历理论基础设施, 审核通过 2026-03-24
, { label := "thm:spg-scan-error-poincare-recurrence"
    sourcePath := "sections/body/spg/subsec__spg-scan-error.tex"
    moduleName := "Omega.Frontier.Conjectures"
    leanName := "Omega.Frontier.FrontierSPGPoincare"
    phase := 66
    status := .frontier }
-- prop:cdim-poisson-Lp-bound → FrontierCdimPoissonLp (Frontier/Conjectures.lean:37)
-- 状态: frontier 占位, 需要调和分析基础设施, 审核通过 2026-03-24
, { label := "prop:cdim-poisson-Lp-bound"
    sourcePath := "sections/body/cdim/subsec__cdim-circular-dim.tex"
    moduleName := "Omega.Frontier.Conjectures"
    leanName := "Omega.Frontier.FrontierCdimPoissonLp"
    phase := 66
    status := .frontier }
-- thm:cdim-KL-divergence-asymptotic → FrontierCdimKLAsymptotic (Frontier/Conjectures.lean:43)
-- 状态: frontier 占位, 需要 KL 散度定义 + Cesaro 渐近, 审核通过 2026-03-24
, { label := "thm:cdim-KL-divergence-asymptotic"
    sourcePath := "sections/body/cdim/subsec__cdim-circular-dim.tex"
    moduleName := "Omega.Frontier.Conjectures"
    leanName := "Omega.Frontier.FrontierCdimKLAsymptotic"
    phase := 66
    status := .frontier }
-- cor:cdim-KL-sixth-moment-negative → FrontierCdimKLSixthNeg (Frontier/Conjectures.lean:49)
-- 状态: frontier 占位, 依赖 FrontierCdimKLAsymptotic + 累积量演算, 审核通过 2026-03-24
, { label := "cor:cdim-KL-sixth-moment-negative"
    sourcePath := "sections/body/cdim/subsec__cdim-circular-dim.tex"
    moduleName := "Omega.Frontier.Conjectures"
    leanName := "Omega.Frontier.FrontierCdimKLSixthNeg"
    phase := 66
    status := .frontier }
-- thm:conclusion-palindrome-defect-symmetry → FrontierConclusionPalindrome (Frontier/Conjectures.lean:55)
-- 状态: frontier 占位, 需要回文词构造 + Matrix.transpose, 审核通过 2026-03-24
, { label := "thm:conclusion-palindrome-defect-symmetry"
    sourcePath := "sections/body/conclusion/subsec__conclusion.tex"
    moduleName := "Omega.Frontier.Conjectures"
    leanName := "Omega.Frontier.FrontierConclusionPalindrome"
    phase := 66
    status := .frontier }

-- Phase 67: Round 63 — S_2 递推基础引理（辅助引理，不计入论文覆盖率）
-- fiberMultiplicity_split_last_bit (CollisionZeta.lean:401) — 纤维末位分裂
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:fiberMultiplicity_split_last_bit"
    sourcePath := "aux"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "fiberMultiplicity_split_last_bit"
    phase := 67
    status := .formalized }
-- momentStateVec (CollisionZeta.lean:418) — S_2 状态向量定义
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:momentStateVec"
    sourcePath := "aux"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "momentStateVec"
    phase := 67
    status := .formalized }
-- collision_kernel2_mulVec_base (CollisionZeta.lean:423) — M·v 基础验证
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:collision_kernel2_mulVec_base"
    sourcePath := "aux"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "collision_kernel2_mulVec_base"
    phase := 67
    status := .formalized }
-- collision_kernel2_mulVec_step1 (CollisionZeta.lean:428) — M·v step1 验证
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:collision_kernel2_mulVec_step1"
    sourcePath := "aux"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "collision_kernel2_mulVec_step1"
    phase := 67
    status := .formalized }
-- collision_kernel2_mulVec_step2 (CollisionZeta.lean:433) — M·v step2 验证
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:collision_kernel2_mulVec_step2"
    sourcePath := "aux"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "collision_kernel2_mulVec_step2"
    phase := 67
    status := .formalized }
-- Round 64: 碰撞对恒等式 (CollisionZeta.lean:436-480)
-- def:pom-s2 → Omega.collisionPairs (CollisionZeta.lean:439) — 碰撞对集合定义
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:collisionPairs"
    sourcePath := "sections/body/pom/parts/subsec__pom-s2.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.collisionPairs"
    phase := 68
    status := .formalized }
-- def:pom-s2 → Omega.cCollisionPairsCount (CollisionZeta.lean:443) — 碰撞对数可计算版本
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:cCollisionPairsCount"
    sourcePath := "sections/body/pom/parts/subsec__pom-s2.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.cCollisionPairsCount"
    phase := 68
    status := .formalized }
-- def:pom-s2 → Omega.momentSum_two_eq_collision (CollisionZeta.lean:451) — S_2(m) = 碰撞对数恒等式（完全证明）
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "bridge:pom-s2-collision-pair-identity"
    sourcePath := "sections/body/pom/parts/subsec__pom-s2.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.momentSum_two_eq_collision"
    phase := 68
    status := .formalized }
-- def:pom-s2 → Omega.collision_pairs_count_verified (CollisionZeta.lean:474) — 碰撞对数 native_decide 验证 m=0..4
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "aux:collision_pairs_count_verified"
    sourcePath := "sections/body/pom/parts/subsec__pom-s2.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "Omega.collision_pairs_count_verified"
    phase := 68
    status := .formalized }
-- Round 66: Fibonacci奇偶性 + 最大纤维界 + 偶奇偶性 (5 theorems)
-- cor:pom-fiber-parity-mod3 → fib_mod_two_table (CollisionZeta.lean:260)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-fiber-parity-mod3"
    sourcePath := "sections/body/pom/parts/subsec__pom-fiber-parity.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "fib_mod_two_table"
    phase := 69
    status := .formalized }
-- cor:pom-fiber-parity-mod3 → fib_even_iff_mod3 (CollisionZeta.lean:269) — 一般性定理，强覆盖
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-fiber-parity-mod3-general"
    sourcePath := "sections/body/pom/parts/subsec__pom-fiber-parity.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "fib_even_iff_mod3"
    phase := 69
    status := .formalized }
-- cor:pom-fiber-parity-mod3 → fib_odd_iff_not_mod3 (CollisionZeta.lean:303)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-fiber-parity-mod3-odd"
    sourcePath := "sections/body/pom/parts/subsec__pom-fiber-parity.tex"
    moduleName := "Omega.Folding.CollisionZeta"
    leanName := "fib_odd_iff_not_mod3"
    phase := 69
    status := .formalized }
-- cor:pom-max-fiber-rate-endpoint → maxFiber_lt_half_wordcount (FiberSplit.lean:232)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-max-fiber-rate-endpoint"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberSplit"
    leanName := "maxFiber_lt_half_wordcount"
    phase := 69
    status := .formalized }
-- cor:pom-fiber-parity-mod3 → maxFiberMultiplicity_even_parity (MaxFiber.lean:178)
-- 状态: 已形式化, 审核通过 2026-03-24
, { label := "cor:pom-fiber-parity-mod3-max"
    sourcePath := "sections/body/pom/parts/subsec__pom-fiber-parity.tex"
    moduleName := "Omega.Folding.MaxFiber"
    leanName := "maxFiberMultiplicity_even_parity"
    phase := 69
    status := .formalized }
-- Phase 70: PathIndSet — 路径图独立集计数 = Fibonacci（thm:pom-max-fiber / cor:pom-D-rec 前置）
-- IsPathIndependent（定义）→ IsPathIndependent (Combinatorics/PathIndSet.lean:19)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "infra:path-ind-set-def"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.PathIndSet"
    leanName := "Omega.IsPathIndependent"
    phase := 70
    status := .formalized }
-- pathIndCount（定义）→ pathIndCount (PathIndSet.lean:27)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "infra:path-ind-count-def"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.PathIndSet"
    leanName := "Omega.pathIndCount"
    phase := 70
    status := .formalized }
-- pathIndCount_recurrence → pathIndCount(n+2) = pathIndCount(n+1) + pathIndCount(n) (PathIndSet.lean:310)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "infra:path-ind-count-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.PathIndSet"
    leanName := "Omega.pathIndCount_recurrence"
    phase := 70
    status := .formalized }
-- path_independent_set_count → pathIndCount(n) = Nat.fib(n+2) (PathIndSet.lean:332)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "infra:path-ind-set-count"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.PathIndSet"
    leanName := "Omega.path_independent_set_count"
    phase := 70
    status := .formalized }
-- path_independent_set_count' → Finset.filter 直接形式 (PathIndSet.lean:345)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "infra:path-ind-set-count-filter"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.PathIndSet"
    leanName := "Omega.path_independent_set_count'"
    phase := 70
    status := .formalized }
-- Phase 71: 隐藏位计数理论 (MaxFiberTwoStep.lean)
-- infra:ofNat-last-false → ofNat_last_false_of_lt（n < fib(m+3) 时末位为 false）
-- (MaxFiberTwoStep.lean:6-17)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "infra:ofNat-last-false"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.ofNat_last_false_of_lt"
    phase := 71
    status := .formalized }
-- infra:ofNat-last-true → ofNat_last_true_of_ge（fib(m+3) ≤ n < fib(m+4) 时末位为 true）
-- (MaxFiberTwoStep.lean:20-34)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "infra:ofNat-last-true"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.ofNat_last_true_of_ge"
    phase := 71
    status := .formalized }
-- thm:pom-hidden-bit-count → hiddenBitCount（定义：weight ≥ fib(m+2) 的 Word m 个数）
-- (MaxFiberTwoStep.lean:41-42)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-hidden-bit-count"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.hiddenBitCount"
    phase := 71
    status := .formalized }
-- thm:pom-hidden-bit-count → hiddenBitCount_zero（基例 B_0 = 0）
-- (MaxFiberTwoStep.lean:44)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-hidden-bit-count-zero"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.hiddenBitCount_zero"
    phase := 71
    status := .formalized }
-- thm:pom-hidden-bit-count → hiddenBitCount_one（基例 B_1 = 0）
-- (MaxFiberTwoStep.lean:46)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-hidden-bit-count-one"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.hiddenBitCount_one"
    phase := 71
    status := .formalized }
-- thm:pom-hidden-bit-count → hiddenBitCount_recurrence（递推：B_{m+2} = 2^m + B_m）
-- (MaxFiberTwoStep.lean:66-187)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-hidden-bit-count-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.hiddenBitCount_recurrence"
    phase := 71
    status := .formalized }
-- thm:pom-hidden-bit-count → hiddenBitCount_closed（闭式：B_m * 3 + δ = 2^m）
-- (MaxFiberTwoStep.lean:193-207)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-hidden-bit-count-closed"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.hiddenBitCount_closed"
    phase := 71
    status := .formalized }
-- Phase 72: lem:pom-one-bit — 单隐藏位分解 (MaxFiberTwoStep.lean:213-273)
-- lem:pom-one-bit → hiddenBit（定义：weight ≥ fib(m+2) 时为 1，否则为 0）
-- (MaxFiberTwoStep.lean:213-214)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-hidden-bit"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.hiddenBit"
    phase := 72
    status := .formalized }
-- lem:pom-one-bit → hiddenBit_le_one（隐藏位 ≤ 1）
-- (MaxFiberTwoStep.lean:216-217)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "lem:pom-hidden-bit-le-one"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.hiddenBit_le_one"
    phase := 72
    status := .formalized }
-- lem:pom-one-bit → ofNat_sub_fib_of_ge（fib(m+2) ≤ n 时 ofNat m n = ofNat m (n - fib(m+2))）
-- (MaxFiberTwoStep.lean:221-245)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "lem:pom-ofNat-sub-fib"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.ofNat_sub_fib_of_ge"
    phase := 72
    status := .formalized }
-- lem:pom-one-bit → weight_eq_stableValue_add_hiddenBit（weight w = stableValue(Fold w) + hiddenBit(w)·fib(m+2)）
-- (MaxFiberTwoStep.lean:248-272)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "lem:pom-one-bit"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.weight_eq_stableValue_add_hiddenBit"
    phase := 72
    status := .formalized }
-- Phase 73: lem:pom-fold-congruence — Fold 等价 ↔ weight 模同余 (MaxFiberTwoStep.lean:278-300)
-- lem:pom-fold-congruence → stableValue_Fold_mod（stableValue(Fold w) = weight w % fib(m+2)）
-- (MaxFiberTwoStep.lean:278-285)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "lem:pom-stableValue-Fold-mod"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.stableValue_Fold_mod"
    phase := 73
    status := .formalized }
-- lem:pom-fold-congruence → Fold_eq_iff_weight_mod（Fold w = Fold w' ↔ weight w % F = weight w' % F）
-- (MaxFiberTwoStep.lean:292-300)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "lem:pom-fold-congruence"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.Fold_eq_iff_weight_mod"
    phase := 73
    status := .formalized }
-- Phase 74: 纤维同余特征化 + pointwise 递推不等式 (MaxFiberTwoStep.lean:306-431)
-- cor:pom-fold-congruence → mem_fiber_iff_weight_mod（纤维 ↔ weight 同余特征化）
-- (MaxFiberTwoStep.lean:306-323)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "cor:pom-mem-fiber-weight-mod"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.mem_fiber_iff_weight_mod"
    phase := 74
    status := .formalized }
-- cor:pom-fold-congruence → fiberMultiplicity_eq_weight_congr_count（纤维大小 = weight 同余类大小）
-- (MaxFiberTwoStep.lean:330-337)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "cor:pom-fiberMultiplicity-weight-congr"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.fiberMultiplicity_eq_weight_congr_count"
    phase := 74
    status := .formalized }
-- thm:pom-max-fiber → fiberMultiplicity_le_restrict_add（pointwise 递推：d(x) ≤ d(restrict x) + d(restrict² x)）
-- (MaxFiberTwoStep.lean:357-431)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-fiberMultiplicity-le-restrict-add"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.fiberMultiplicity_le_restrict_add"
    phase := 74
    status := .formalized }
-- Phase 75: 全零词纤维特征化 (FiberWeightCount.lean:10-106，迁移自 MaxFiberTwoStep.lean)
-- thm:pom-max-fiber → X.ofNat_zero（X.ofNat m 0 = allFalse）
-- (FiberWeightCount.lean:10-14)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-ofNat-zero-allFalse"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.X.ofNat_zero"
    phase := 75
    status := .formalized }
-- thm:pom-max-fiber → Fold_eq_allFalse_of_weight_eq_fib（weight=F(m+2) 的词 Fold 到 allFalse）
-- (FiberWeightCount.lean:17-28)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-Fold-allFalse-weight-fib"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.Fold_eq_allFalse_of_weight_eq_fib"
    phase := 75
    status := .formalized }
-- thm:pom-max-fiber → fiberMultiplicity_allFalse（allFalse 纤维大小 = 1 + #{weight=F(m+2)}）
-- (FiberWeightCount.lean:53-106)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-fiberMultiplicity-allFalse"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.fiberMultiplicity_allFalse"
    phase := 75
    status := .formalized }
-- Phase 76: exactWeightCount 基础设施 (FiberWeightCount.lean:113-224，迁移自 MaxFiberTwoStep.lean)
-- def:pom-exactWeightCount → exactWeightCount（定义：m-bit 词中 weight = n 的计数）
-- (FiberWeightCount.lean:113-114)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-exactWeightCount"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCount"
    phase := 76
    status := .formalized }
-- def:pom-exactWeightCount → exactWeightCount_zero_zero（基例 ewc(0,0) = 1）
-- (FiberWeightCount.lean:116)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-ewc-zero-zero"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCount_zero_zero"
    phase := 76
    status := .formalized }
-- def:pom-exactWeightCount → exactWeightCount_zero_succ（基例 ewc(0, n+1) = 0）
-- (FiberWeightCount.lean:118-121)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-ewc-zero-succ"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCount_zero_succ"
    phase := 76
    status := .formalized }
-- def:pom-exactWeightCount → exactWeightCount_succ（末位分裂递推：ewc(m+1,n) = ewc(m,n) + ewc(m,n-F)）
-- (FiberWeightCount.lean:124-171)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-ewc-succ"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCount_succ"
    phase := 76
    status := .formalized }
-- def:pom-exactWeightCount → exactWeightCount_eq_zero_of_ge_fib（上界：n ≥ F(m+3) → ewc = 0）
-- (FiberWeightCount.lean:177-184)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-ewc-zero-ge-fib"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCount_eq_zero_of_ge_fib"
    phase := 76
    status := .formalized }
-- thm:pom-max-fiber → fiberMultiplicity_eq_two_ewc（纤维大小 = ewc(sv) + ewc(sv+F)）
-- (FiberWeightCount.lean:191-224)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-fiberMultiplicity-two-ewc"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.fiberMultiplicity_eq_two_ewc"
    phase := 76
    status := .formalized }
-- Phase 77: ewc 双步递推 + allFalse 纤维递推与闭式 (FiberWeightCount.lean:230-344)
-- thm:pom-max-fiber → exactWeightCount_succ_succ（双步分裂递推）
-- (FiberWeightCount.lean:230-261)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-ewc-succ-succ"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCount_succ_succ"
    phase := 77
    status := .formalized }
-- thm:pom-max-fiber → exactWeightCount_fib_shift（ewc(m+2, F(m+4)) = ewc(m, F(m+2)) + 1）
-- (FiberWeightCount.lean:274-293)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-ewc-fib-shift"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCount_fib_shift"
    phase := 77
    status := .formalized }
-- thm:pom-max-fiber → fiberMultiplicity_allFalse_recurrence（fM(allFalse, m+2) = fM(allFalse, m) + 1）
-- (FiberWeightCount.lean:299-310)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-fM-allFalse-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.fiberMultiplicity_allFalse_recurrence"
    phase := 77
    status := .formalized }
-- thm:pom-max-fiber → fiberMultiplicity_allFalse_closed（fM(allFalse, m) = m/2 + 1）
-- (FiberWeightCount.lean:316-343)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-fM-allFalse-closed"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.fiberMultiplicity_allFalse_closed"
    phase := 77
    status := .formalized }
-- Phase 78: weightCongruenceCount + S_2 同余矩表达 (FiberWeightCount.lean:346-413)
-- prop:pom-moment-congruence-q → weightCongruenceCount（同余类计数定义：#{w | weight w % F_{m+2} = r}）
-- (FiberWeightCount.lean:351)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-wcc"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.weightCongruenceCount"
    phase := 78
    status := .formalized }
-- prop:pom-moment-congruence-q → weightCongruenceCount_eq_sum_ewc（wcc = ewc(r) + ewc(r+F)）
-- (FiberWeightCount.lean:355)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-wcc-eq-sum-ewc"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.weightCongruenceCount_eq_sum_ewc"
    phase := 78
    status := .formalized }
-- prop:pom-moment-congruence-q → fiberMultiplicity_eq_wcc（d(x) = wcc(m, sv(x))）
-- (FiberWeightCount.lean:387)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-fiberMultiplicity-eq-wcc"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.fiberMultiplicity_eq_wcc"
    phase := 78
    status := .formalized }
-- prop:pom-moment-congruence-q → momentSum_two_eq_congr_sq_sum（S_2(m) = Σ wcc(r)^2，q=2）
-- (FiberWeightCount.lean:396)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "prop:pom-moment-congruence-q"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.momentSum_two_eq_congr_sq_sum"
    phase := 78
    status := .formalized }
-- Phase 79: wcc 守恒 + S_2 末位4分裂 + 取消对称性 (FiberWeightCount.lean:414-546)
-- prop:pom-moment-congruence-q → weightCongruenceCount_sum（Σ wcc(r) = 2^m，同余类划分守恒）
-- (FiberWeightCount.lean:419)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-wcc-sum"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.weightCongruenceCount_sum"
    phase := 79
    status := .formalized }
-- prop:pom-moment-congruence-q → momentSum_two_lastBit_split（S_2(m+1) = E(0,0)+E(0,1)+E(1,0)+E(1,1)）
-- (FiberWeightCount.lean:440)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-lastbit-split"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.momentSum_two_lastBit_split"
    phase := 79
    status := .formalized }
-- prop:pom-moment-congruence-q → collision_lastBit_cancel（E(1,1) = E(0,0)，末位取消）
-- (FiberWeightCount.lean:532)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-collision-lastbit-cancel"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.collision_lastBit_cancel"
    phase := 79
    status := .formalized }
-- Phase 80: 碰撞对称性 + S_2 两项分解 + exactWeightCollision (FiberWeightCount.lean:547-629)
-- prop:pom-moment-congruence-q → collision_cross_symm（E(0,1) = E(1,0)，交换对称性）
-- (FiberWeightCount.lean:551)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-collision-cross-symm"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.collision_cross_symm"
    phase := 80
    status := .formalized }
-- prop:pom-moment-congruence-q → momentSum_two_succ_two_term（S_2(m+1) = 2·E(0,0) + 2·E(0,1)）
-- (FiberWeightCount.lean:573)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-two-term"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.momentSum_two_succ_two_term"
    phase := 80
    status := .formalized }
-- prop:pom-s2-plancherel → exactWeightCollision（定义：Σ ewc(m,n)^2）
-- (FiberWeightCount.lean:587)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-exactWeightCollision"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.exactWeightCollision"
    phase := 80
    status := .formalized }
-- prop:pom-s2-plancherel → collision_same_eq_exactWeightCollision（E(0,0) = Σ ewc(n)^2）
-- (FiberWeightCount.lean:591)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-collision-same-ewc-sq"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.FiberWeightCount"
    leanName := "Omega.collision_same_eq_exactWeightCollision"
    phase := 80
    status := .formalized }
-- Phase 81: crossWeightCorrelation + E00 递推与望远镜和 (FiberWeightCount.lean:630-764)
-- prop:pom-s2-plancherel → crossWeightCorrelation（定义：Σ ewc(r)·ewc(r+F)，交叉权重相关）
-- (CollisionDecomp.lean:226)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-crossWeightCorrelation"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.crossWeightCorrelation"
    phase := 81
    status := .formalized }
-- prop:pom-s2-plancherel → exactWeightCollision_succ（E00(m+1) = E00(m) + S_2(m)）
-- (CollisionDecomp.lean:235)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-e00-succ"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.exactWeightCollision_succ"
    phase := 81
    status := .formalized }
-- prop:pom-s2-plancherel → exactWeightCollision_eq_sum（E00(m) = 1 + Σ_{k<m} S_2(k)）
-- (CollisionDecomp.lean:344)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-e00-telescoping"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.exactWeightCollision_eq_sum"
    phase := 81
    status := .formalized }
-- Phase 82: crossCorr + E(0,1) 分解 + S_2 三项展开 (CollisionDecomp.lean:362-505)
-- prop:pom-s2-plancherel → crossCorr（定义：交叉相关函数 C(m,d) = Σ ewc(r)·ewc(r+d)）
-- (CollisionDecomp.lean:362)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-crossCorr"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.crossCorr"
    phase := 82
    status := .formalized }
-- prop:pom-s2-plancherel → crossCorr_zero_eq（C_0 = E(0,0)，零位移交叉相关 = 精确碰撞数）
-- (CollisionDecomp.lean:367)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-crossCorr-zero"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.crossCorr_zero_eq"
    phase := 82
    status := .formalized }
-- prop:pom-s2-plancherel → collision_cross_eq_two_crossCorr（E(0,1) = C_F + C_{F-1}）
-- (CollisionDecomp.lean:376)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-e01-crossCorr"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.collision_cross_eq_two_crossCorr"
    phase := 82
    status := .formalized }
-- prop:pom-s2-plancherel → momentSum_two_succ_three_term（S_2(m+1) = 2E00 + 2C_F + 2C_{F-1}）
-- (CollisionDecomp.lean:497)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-three-term"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.momentSum_two_succ_three_term"
    phase := 82
    status := .formalized }
-- Phase 83: S_2 递推里程碑 (CollisionDecomp.lean:506-776)
-- ★ 里程碑：项目首个无条件非平凡无穷族递推定理
-- prop:pom-s2-recurrence → momentSum_two_eq_exact_plus_crossCorr（S_2 = E00 + 2·C_F，关键分解）
-- (CollisionDecomp.lean:688)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-exact-crossCorr"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.momentSum_two_eq_exact_plus_crossCorr"
    phase := 83
    status := .formalized }
-- prop:pom-s2-recurrence → crossCorr_fib_prev_eq_momentSum（crossCorr(m+1,F_{m+2}) = S_2(m)）
-- (CollisionDecomp.lean:743)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-crossCorr-fib-prev"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.crossCorr_fib_prev_eq_momentSum"
    phase := 83
    status := .formalized }
-- prop:pom-s2-recurrence → momentSum_two_succ_succ_expand（S_2(m+2) = E00(m+1) + S_2(m+1) + 2·S_2(m)）
-- (CollisionDecomp.lean:751)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-expand"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.momentSum_two_succ_succ_expand"
    phase := 83
    status := .formalized }
-- ★ prop:pom-s2-recurrence → momentSum_two_recurrence（S_2(m+3)+2·S_2(m) = 2·S_2(m+2)+2·S_2(m+1)）
-- (CollisionDecomp.lean:768)
-- 状态: 已形式化, 审核通过 2026-03-25 ★ 里程碑：无条件递推，零 native_decide
, { label := "prop:pom-s2-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.CollisionDecomp"
    leanName := "Omega.momentSum_two_recurrence"
    phase := 83
    status := .formalized }
-- Phase 84: S_2 递推推论族 (MomentRecurrence.lean:1-86)
-- prop:pom-s2-recurrence → momentSum_two_recurrence_sub（S_2 递推减法形式）
-- (MomentRecurrence.lean:10)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-recurrence-sub"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_recurrence_sub"
    phase := 84
    status := .formalized }
-- prop:pom-s2-recurrence → momentSum_two_pos'（S_2(m) > 0，无条件正性）
-- (MomentRecurrence.lean:19)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-pos"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_pos'"
    phase := 84
    status := .formalized }
-- prop:pom-s2-recurrence → momentSum_two_mono'（S_2 无条件单调）
-- (MomentRecurrence.lean:28)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-mono"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_mono'"
    phase := 84
    status := .formalized }
-- prop:pom-s2-recurrence → momentSum_two_strict_mono'（S_2 严格单调 m≥1）
-- (MomentRecurrence.lean:65)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s2-strict-mono"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_strict_mono'"
    phase := 84
    status := .formalized }
-- Phase 85: S_q 一般化矩同余表达 + S_q 正性 (MomentRecurrence.lean:86-125)
-- prop:pom-moment-congruence-q → momentSum_eq_congr_pow_sum（S_q(m) = Σ wcc(r)^q，完整一般化）
-- (MomentRecurrence.lean:91)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "prop:pom-moment-congruence-q-general"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_eq_congr_pow_sum"
    phase := 85
    status := .formalized }
-- prop:pom-moment-congruence-q → exactWeightTriple（定义：Σ ewc(m,n)^3，精确重量三次方和）
-- (MomentRecurrence.lean:110)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "def:pom-exactWeightTriple"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.exactWeightTriple"
    phase := 85
    status := .formalized }
-- prop:pom-moment-congruence-q → momentSum_pos'（S_q(m) > 0，对所有 q,m 成立）
-- (MomentRecurrence.lean:118)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-sq-pos-general"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_pos'"
    phase := 85
    status := .formalized }
-- Phase 86: S_3 基础设施 (MomentRecurrence.lean:125-164)
-- prop:pom-s3-recurrence → momentSum_three_eq_triple_collision（S_3 = 三元碰撞计数）
-- (MomentRecurrence.lean:130)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-s3-triple-collision"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_three_eq_triple_collision"
    phase := 86
    status := .formalized }
-- prop:pom-s3-recurrence → triple_collision_iff_weight_mod（三元碰撞 ↔ 权重同余）
-- (MomentRecurrence.lean:152)
-- 状态: 已形式化, 审核通过 2026-03-25
, { label := "thm:pom-triple-collision-weight-mod"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.triple_collision_iff_weight_mod"
    phase := 86
    status := .formalized }
-- Phase 87: S_q 普适不等式 (MomentRecurrence.lean:164-203)
, { label := "thm:pom-sq-ge-pow"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_ge_pow'"
    phase := 87
    status := .formalized }
, { label := "thm:pom-sq-le-succ"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_le_succ'"
    phase := 87
    status := .formalized }
, { label := "thm:pom-s2-cauchy-schwarz"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_mul_card_ge"
    phase := 87
    status := .formalized }
, { label := "thm:pom-sq-ge-card"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_ge_card'"
    phase := 87
    status := .formalized }
, { label := "thm:pom-sq-upper-bound"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_upper_bound'"
    phase := 87
    status := .formalized }
-- Phase 88: S_2 数论性质 (MomentRecurrence.lean:203-263)
, { label := "thm:pom-s2-even"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_even"
    phase := 88
    status := .formalized }
, { label := "thm:pom-s2-succ-half"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_succ_half"
    phase := 88
    status := .formalized }
, { label := "thm:pom-s2-succ-ge-double"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_succ_ge_double"
    phase := 88
    status := .formalized }
, { label := "thm:pom-s2-succ-le-quadruple"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_succ_le_quadruple"
    phase := 88
    status := .formalized }
, { label := "thm:pom-s2-succ-excess"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_succ_excess"
    phase := 88
    status := .formalized }
-- Phase 89: S_2 整除性 + E00 比较 (MomentRecurrence.lean:263-341)
, { label := "thm:pom-s2-odd-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_odd_iff"
    phase := 89
    status := .formalized }
, { label := "thm:pom-s2-mod-four"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_mod_four"
    phase := 89
    status := .formalized }
, { label := "thm:pom-s2-ge-e00"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_ge_exactWeightCollision"
    phase := 89
    status := .formalized }
, { label := "thm:pom-e00-double"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.exactWeightCollision_double"
    phase := 89
    status := .formalized }
, { label := "thm:pom-e00-ge-linear"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.exactWeightCollision_ge_linear"
    phase := 89
    status := .formalized }
-- Phase 90: 递推唯一性 + S_2 高阶纯递推值 (MomentRecurrence.lean:341-396)
, { label := "thm:pom-s2-recurrence-unique"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.recurrence_unique"
    phase := 90
    status := .formalized }
, { label := "thm:pom-s2-determined"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_determined"
    phase := 90
    status := .formalized }
, { label := "thm:pom-s2-seven-rec"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_seven_rec"
    phase := 90
    status := .formalized }
, { label := "thm:pom-s2-eight-rec"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_eight_rec"
    phase := 90
    status := .formalized }
, { label := "thm:pom-s2-nine-rec"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_nine_rec"
    phase := 90
    status := .formalized }
-- Phase 91: 纤维结构界 (MomentRecurrence.lean:396-436)
, { label := "thm:pom-d-ge-avg"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.maxFiberMultiplicity_ge_avg"
    phase := 91
    status := .formalized }
, { label := "thm:pom-d-le-pow"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.maxFiberMultiplicity_le_pow"
    phase := 91
    status := .formalized }
, { label := "thm:pom-fiber-le-pow"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.fiberMultiplicity_le_pow"
    phase := 91
    status := .formalized }
, { label := "thm:pom-d-ge-one"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.maxFiberMultiplicity_ge_one"
    phase := 91
    status := .formalized }
, { label := "thm:pom-achievers-pos"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.maxFiberMultiplicity_achievers_pos"
    phase := 91
    status := .formalized }
-- Phase 92: Fibonacci Pisano mod 2 (Core/Fib.lean:107-173)
, { label := "thm:fib-even-of-three-dvd"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_even_of_three_dvd"
    phase := 92
    status := .formalized }
, { label := "thm:three-dvd-of-fib-even"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.three_dvd_of_fib_even"
    phase := 92
    status := .formalized }
, { label := "thm:fib-even-iff-three-dvd"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_even_iff_three_dvd"
    phase := 92
    status := .formalized }
, { label := "thm:fib-mod-two-period"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_mod_two_period"
    phase := 92
    status := .formalized }
, { label := "thm:fib-odd-iff-not-three-dvd"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_odd_iff_not_three_dvd"
    phase := 92
    status := .formalized }
-- Phase 93: Fibonacci 求和恒等式 (Core/Fib.lean:173-257)
, { label := "thm:fib-partial-sum"
    sourcePath := "sections/body/nascent/parts/subsec__nascent-fib-identities.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_partial_sum"
    phase := 93
    status := .formalized }
, { label := "thm:fib-partial-sum-from-two"
    sourcePath := "sections/body/nascent/parts/subsec__nascent-fib-identities.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_partial_sum_from_two"
    phase := 93
    status := .formalized }
, { label := "thm:fib-sq-sum"
    sourcePath := "sections/body/nascent/parts/subsec__nascent-fib-identities.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_sq_sum"
    phase := 93
    status := .formalized }
, { label := "thm:fib-even-sum"
    sourcePath := "sections/body/nascent/parts/subsec__nascent-fib-identities.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_even_sum"
    phase := 93
    status := .formalized }
, { label := "thm:fib-odd-sum"
    sourcePath := "sections/body/nascent/parts/subsec__nascent-fib-identities.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_odd_sum"
    phase := 93
    status := .formalized }
-- Phase 94: 权重极值 (MomentRecurrence.lean:436-513)
, { label := "thm:pom-weight-allTrue"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.weight_allTrue"
    phase := 94
    status := .formalized }
, { label := "thm:pom-weight-le-allTrue"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.weight_le_allTrue"
    phase := 94
    status := .formalized }
, { label := "thm:pom-fold-allTrue"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.Fold_allTrue"
    phase := 94
    status := .formalized }
, { label := "thm:pom-ewc-zero-one"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.exactWeightCount_zero_eq_one'"
    phase := 94
    status := .formalized }
-- Phase 95: complement 对称性 (MomentRecurrence.lean:513-569)
, { label := "thm:pom-complement-involution"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.complement_involution"
    phase := 95
    status := .formalized }
, { label := "thm:pom-truncate-complement"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.truncate_complement"
    phase := 95
    status := .formalized }
, { label := "thm:pom-complement-allFalse"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.complement_allFalse"
    phase := 95
    status := .formalized }
, { label := "thm:pom-weight-complement"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.weight_complement"
    phase := 95
    status := .formalized }
, { label := "thm:pom-ewc-symmetric"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.exactWeightCount_symmetric"
    phase := 95
    status := .formalized }
-- Phase 96: Fold complement 对偶 + Gauss 和 (MomentRecurrence.lean:569-602)
, { label := "thm:pom-weight-complement-sub"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.weight_complement_sub"
    phase := 96
    status := .formalized }
, { label := "thm:pom-fold-complement"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.Fold_complement"
    phase := 96
    status := .formalized }
, { label := "thm:pom-stableValue-sum"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.stableValue_sum"
    phase := 96
    status := .formalized }
-- Phase 97: Fibonacci Cube 路径独立集等价 (Combinatorics/FibonacciCube.lean:1-87)
, { label := "thm:pom-wordSupport-pathInd"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.wordSupport_isPathIndependent"
    phase := 97
    status := .formalized }
, { label := "thm:pom-indSetToWord-no11"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.indSetToWord_no11"
    phase := 97
    status := .formalized }
, { label := "thm:pom-wordSupport-indSetToWord"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.wordSupport_indSetToWord"
    phase := 97
    status := .formalized }
, { label := "thm:pom-indSetToWord-wordSupport"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.indSetToWord_wordSupport"
    phase := 97
    status := .formalized }
, { label := "thm:pom-xEquivPathIndSet"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.xEquivPathIndSet"
    phase := 97
    status := .formalized }
-- Phase 98: popcount 定义与基值 (Combinatorics/FibonacciCube.lean:87-105)
, { label := "thm:pom-popcount-allFalse"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.popcount_allFalse"
    phase := 98
    status := .formalized }
, { label := "thm:pom-popcount-allTrue"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.popcount_allTrue"
    phase := 98
    status := .formalized }
-- Phase 99: popcount 结构性质 + totalPopcount (Combinatorics/FibonacciCube.lean:105-160)
, { label := "thm:pom-popcount-not"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.popcount_not"
    phase := 99
    status := .formalized }
, { label := "thm:pom-popcount-eq-zero-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.popcount_eq_zero_iff"
    phase := 99
    status := .formalized }
, { label := "thm:pom-popcount-truncate-le"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.popcount_truncate_le"
    phase := 99
    status := .formalized }
, { label := "thm:pom-totalPopcount-zero"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.totalPopcount_zero"
    phase := 99
    status := .formalized }
-- Phase 100: Fold 泛性质唯一性 (Folding/MaxFiberTwoStep.lean:437-475)
, { label := "thm:fold-congruence-universal-property"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.Fold_unique_of_weight_congr"
    phase := 100
    status := .formalized }
, { label := "thm:fold-unique-of-retraction"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.Fold_unique_of_retraction"
    phase := 100
    status := .formalized }
, { label := "thm:pom-eq-of-stableValue-eq"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.X.eq_of_stableValue_eq'"
    phase := 100
    status := .formalized }
, { label := "thm:pom-congr-map-fiber-const"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.congr_map_fiber_const"
    phase := 100
    status := .formalized }
, { label := "thm:pom-fiber-independent-of-retraction"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.fiber_independent_of_retraction"
    phase := 100
    status := .formalized }
-- Phase 101: S_2 交叉验证与增长界 (Folding/MomentRecurrence.lean:606-661)
, { label := "thm:pom-momentSum-two-recurrence-matches-charpoly"
    sourcePath := "sections/body/pom/parts/subsec__pom-moment-recurrence.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_recurrence_matches_charpoly"
    phase := 101
    status := .formalized }
, { label := "thm:pom-momentSum-two-chain"
    sourcePath := "sections/body/pom/parts/subsec__pom-moment-recurrence.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_chain"
    phase := 101
    status := .formalized }
, { label := "thm:pom-momentSum-two-ratio-bounds"
    sourcePath := "sections/body/pom/parts/subsec__pom-moment-recurrence.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_ratio_bounds'"
    phase := 101
    status := .formalized }
, { label := "thm:pom-momentSum-two-excess-pos"
    sourcePath := "sections/body/pom/parts/subsec__pom-moment-recurrence.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_excess_pos"
    phase := 101
    status := .formalized }
, { label := "thm:pom-momentSum-two-ge-two-fib"
    sourcePath := "sections/body/pom/parts/subsec__pom-moment-recurrence.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_ge_two_fib"
    phase := 101
    status := .formalized }
-- Phase 102: 纤维判别式 (Folding/MomentRecurrence.lean:665-696)
, { label := "thm:pom-hiddenBit-stable"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.hiddenBit_stable"
    phase := 102
    status := .formalized }
, { label := "thm:pom-Fold-eq-self-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.Fold_eq_self_iff"
    phase := 102
    status := .formalized }
, { label := "thm:pom-weight-stable-eq-stableValue"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.weight_stable_eq_stableValue"
    phase := 102
    status := .formalized }
, { label := "thm:pom-ewc-stableValue-pos"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.ewc_stableValue_pos"
    phase := 102
    status := .formalized }
, { label := "thm:pom-fiberMultiplicity-one-imp-ewc-zero"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.fiberMultiplicity_one_imp_ewc_zero"
    phase := 102
    status := .formalized }
, { label := "thm:pom-fiberMultiplicity-ge-ewc"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.fiberMultiplicity_ge_ewc"
    phase := 102
    status := .formalized }
-- Phase 103: weight 满射与 ewc 正性 (Combinatorics/FibonacciCube.lean:165-203)
, { label := "thm:pom-weight-surjective"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.weight_surjective"
    phase := 103
    status := .formalized }
, { label := "thm:pom-ewc-pos-of-le"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.ewc_pos_of_le"
    phase := 103
    status := .formalized }
, { label := "thm:pom-fiberMultiplicity-ge-two-of-sv-le"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.fiberMultiplicity_ge_two_of_sv_le"
    phase := 103
    status := .formalized }
-- Phase 104: Fibonacci Pisano π(3) (Core/Fib.lean:260-296)
, { label := "thm:pom-fib-div-three-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-fibonacci.tex"
    moduleName := "Omega.Core.Fib"
    leanName := "Omega.fib_div_three_iff"
    phase := 104
    status := .formalized }
-- Phase 105: Pisano 应用 + 奇偶性 (Folding/MomentRecurrence.lean:700-738)
, { label := "thm:pom-fiberMultiplicity-allFalse-odd-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.fiberMultiplicity_allFalse_odd_iff"
    phase := 105
    status := .formalized }
, { label := "thm:pom-hiddenBit-eq-one-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.hiddenBit_eq_one_iff"
    phase := 105
    status := .formalized }
, { label := "thm:pom-hiddenBit-eq-zero-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.hiddenBit_eq_zero_iff"
    phase := 105
    status := .formalized }
, { label := "thm:pom-fiber-hidden-bit-split"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.fiber_hidden_bit_split"
    phase := 105
    status := .formalized }
, { label := "thm:pom-momentSum-two-mod-six-base"
    sourcePath := "sections/body/pom/parts/subsec__pom-moment-recurrence.tex"
    moduleName := "Omega.Folding.MomentRecurrence"
    leanName := "Omega.momentSum_two_mod_six_base"
    phase := 105
    status := .formalized }
-- Phase 106: Fold-snoc 分解 (Folding/MaxFiberTwoStep.lean:475-498)
, { label := "thm:pom-restrict-Fold-eq"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.restrict_Fold_eq"
    phase := 106
    status := .formalized }
, { label := "thm:pom-Fold-snoc-false-eq"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.Fold_snoc_false_eq"
    phase := 106
    status := .formalized }
, { label := "thm:pom-Fold-snoc-true-eq"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.Fold_snoc_true_eq"
    phase := 106
    status := .formalized }
, { label := "thm:pom-stableValue-Fold-snoc-false"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.stableValue_Fold_snoc_false"
    phase := 106
    status := .formalized }
, { label := "thm:pom-stableValue-Fold-snoc-true"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MaxFiberTwoStep"
    leanName := "Omega.stableValue_Fold_snoc_true"
    phase := 106
    status := .formalized }
-- Phase 107: weight 分解 + fiber 包装 (Combinatorics/FibonacciCube.lean:203-243)
, { label := "thm:pom-weight-truncate-add"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.weight_truncate_add"
    phase := 107
    status := .formalized }
, { label := "thm:pom-weight-pos-iff"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.weight_pos_iff"
    phase := 107
    status := .formalized }
, { label := "thm:pom-Fold-of-stable"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.Fold_of_stable'"
    phase := 107
    status := .formalized }
, { label := "thm:pom-fiber-self-mem"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.fiber_self_mem"
    phase := 107
    status := .formalized }
-- Phase 108: D(m) 上界 (Combinatorics/FibonacciCube.lean:243-278)
, { label := "thm:pom-maxFiberMultiplicity-le-fib"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.maxFiberMultiplicity_le_fib"
    phase := 108
    status := .formalized }
, { label := "thm:pom-fiberMultiplicity-le-fib"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.fiberMultiplicity_le_fib"
    phase := 108
    status := .formalized }
, { label := "thm:pom-maxFiberMultiplicity-sq-le-momentSum"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.maxFiberMultiplicity_sq_le_momentSum"
    phase := 108
    status := .formalized }
-- Phase 109: D(m) 下界 + 无界性 (Combinatorics/FibonacciCube.lean:278-310)
, { label := "thm:pom-maxFiberMultiplicity-ge-half"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.maxFiberMultiplicity_ge_half"
    phase := 109
    status := .formalized }
, { label := "thm:pom-maxFiberMultiplicity-ge-two"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.maxFiberMultiplicity_ge_two"
    phase := 109
    status := .formalized }
, { label := "thm:pom-maxFiberMultiplicity-bounds"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.maxFiberMultiplicity_bounds"
    phase := 109
    status := .formalized }
, { label := "thm:pom-maxFiberMultiplicity-unbounded"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.maxFiberMultiplicity_unbounded"
    phase := 109
    status := .formalized }
, { label := "thm:pom-momentSum-two-ge-maxFiber-sq"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Combinatorics.FibonacciCube"
    leanName := "Omega.momentSum_two_ge_maxFiber_sq"
    phase := 109
    status := .formalized }
-- Phase 110: S_2 三重界 + snoc 嵌入 + mod 8 整除性 (Folding/MomentBounds.lean:10-78)
, { label := "prop:pom-s2-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentBounds"
    leanName := "Omega.momentSum_two_succ_le_triple"
    phase := 110
    status := .formalized }
, { label := "thm:pom-max-fiber"
    sourcePath := "sections/body/pom/parts/subsec__pom-max-fiber.tex"
    moduleName := "Omega.Folding.MomentBounds"
    leanName := "Omega.fiberMultiplicity_ge_ewc_via_snoc"
    phase := 110
    status := .formalized }
, { label := "prop:pom-s2-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentBounds"
    leanName := "Omega.momentSum_two_mod_eight"
    phase := 110
    status := .formalized }
-- Phase 111: weight Fibonacci 展开 + S_3 末位8-分裂 (Weight.lean:59, MomentTriple.lean:49)
, { label := "def:pom-fiber-adm-path"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.Weight"
    leanName := "Omega.weight_eq_fib_ite_sum"
    phase := 111
    status := .formalized }
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.momentSum_three_lastBit_split"
    phase := 111
    status := .formalized }
-- Phase 112: S_3 对称性简化 8→3 碰撞类 (MomentTriple.lean:107-193, 修正版 53fba8443)
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.tripleCollisionClass_cancel_111"
    phase := 112
    status := .formalized }
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.tripleCollisionClass_swap12"
    phase := 112
    status := .formalized }
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.tripleCollisionClass_swap23"
    phase := 112
    status := .formalized }
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.tripleCollisionClass_swap13"
    phase := 112
    status := .formalized }
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.momentSum_three_succ_three_term"
    phase := 112
    status := .formalized }
-- Phase 113: T000 = exactWeightTriple + ewt 形式 (MomentTriple.lean:189-235)
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.tripleCollisionClass_000_eq_ewcCube"
    phase := 113
    status := .formalized }
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.momentSum_three_succ_ewt_form"
    phase := 113
    status := .formalized }
, { label := "prop:pom-s3-recurrence"
    sourcePath := "sections/body/pom/parts/subsec__pom-s5.tex"
    moduleName := "Omega.Folding.MomentTriple"
    leanName := "Omega.tripleCorr"
    phase := 113
    status := .formalized } ]

end Omega.Audit
