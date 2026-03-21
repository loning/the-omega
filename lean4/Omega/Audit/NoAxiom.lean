import Omega.Folding.StableSyntax
import Omega.Folding.Zeckendorf
import Omega.Folding.Fold
import Omega.Folding.Fiber
import Omega.Folding.InverseLimit
import Omega.Folding.Rewrite
import Omega.Folding.Defect
import Omega.Graph.Sofic
import Omega.SPG.Clopen
import Omega.SPG.ScanErrorDiscrete
import Omega.SPG.ScanErrorMeasure
import Omega.Audit.SourceMap

namespace Omega.Audit

/-
Run these commands manually during audit:

  #print axioms Omega.no11_truncate
  #print axioms Omega.X.restrict
  #print axioms Omega.paperFib_recurrence
  #print axioms Omega.X.card_eq_paperFib_succ
  #print axioms Omega.X.zeckIndices_isZeckendorfRep
  #print axioms Omega.X.stableValue_eq_sum_fib_zeckIndices
  #print axioms Omega.Fold_stable
  #print axioms Omega.Fold_idempotent
  #print axioms Omega.X.fiber_nonempty
  #print axioms Omega.X.inverseLimitEquiv
  #print axioms Omega.Rewrite.step_value
  #print axioms Omega.Rewrite.step_stronglyTerminating
  #print axioms Omega.Rewrite.irreducible_supported_eq_iota_normalPrefix
  #print axioms Omega.Rewrite.irreducible_eq_of_normalPrefix_eq
  #print axioms Omega.Rewrite.reflTransGen_normalPrefix
  #print axioms Omega.Rewrite.irreducible_terminal_unique
  #print axioms Omega.Rewrite.irreducible_terminal_eq_fold
  #print axioms Omega.globalDefect_eq_defectChain
  #print axioms Omega.Graph.acceptsWord_goldenMean_iff_no11
  #print axioms Omega.SPG.spg_decidableClopen
  #print axioms Omega.SPG.scanError_eq_sum_boundary
  #print axioms Omega.SPG.prefixScanError_eq_zero_of_prefixEvent
  #print axioms Omega.SPG.scanErrorMeasure_observableEvent_eq_zero
  #print axioms Omega.SPG.scanErrorMeasure_eq_sum_boundary
  #print axioms Omega.SPG.scanErrorMeasure_toMeasure_eq_scanError
  #print axioms Omega.Frontier.RewriteStepCertificate.value_preserved
  #print axioms Omega.Frontier.FoldCertificate.idempotent
  #print axioms Omega.Frontier.PrefixZeroScanCertificate.canonical

The goal of phase 0/1 is that these core theorems use no project-defined axioms.
-/

def coreAuditTargets : List String :=
  [ "Omega.paperFib_recurrence"
  , "Omega.no11_truncate"
  , "Omega.X.restrict"
  , "Omega.X.card_eq_paperFib_succ"
  , "Omega.X.zeckIndices_isZeckendorfRep"
  , "Omega.X.stableValue_eq_sum_fib_zeckIndices"
  , "Omega.Fold_stable"
  , "Omega.Fold_idempotent"
  , "Omega.X.fiber_nonempty"
  , "Omega.X.inverseLimitEquiv"
  , "Omega.Rewrite.step_value"
  , "Omega.Rewrite.step_stronglyTerminating"
  , "Omega.Rewrite.irreducible_supported_eq_iota_normalPrefix"
  , "Omega.Rewrite.irreducible_eq_of_normalPrefix_eq"
  , "Omega.Rewrite.reflTransGen_normalPrefix"
  , "Omega.Rewrite.irreducible_terminal_unique"
  , "Omega.Rewrite.irreducible_terminal_eq_fold"
  , "Omega.globalDefect_eq_defectChain"
  , "Omega.Graph.acceptsWord_goldenMean_iff_no11"
  , "Omega.SPG.spg_decidableClopen"
  , "Omega.SPG.scanError_eq_sum_boundary"
  , "Omega.SPG.prefixScanError_eq_zero_of_prefixEvent"
  , "Omega.SPG.scanErrorMeasure_observableEvent_eq_zero"
  , "Omega.SPG.scanErrorMeasure_eq_sum_boundary"
  , "Omega.SPG.scanErrorMeasure_toMeasure_eq_scanError"
  , "Omega.Frontier.RewriteStepCertificate.value_preserved"
  , "Omega.Frontier.FoldCertificate.idempotent"
  , "Omega.Frontier.PrefixZeroScanCertificate.canonical" ]

end Omega.Audit
