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
      status := .formalized } ]

end Omega.Audit
