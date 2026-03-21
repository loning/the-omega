import Omega.Folding.StableSyntax
import Omega.Folding.Zeckendorf
import Omega.Folding.Fold
import Omega.Folding.InverseLimit
import Omega.Folding.Rewrite
import Omega.Folding.Defect
import Omega.SPG.Clopen
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
  #print axioms Omega.X.inverseLimitEquiv
  #print axioms Omega.Rewrite.step_value
  #print axioms Omega.globalDefect_eq_defectChain
  #print axioms Omega.SPG.spg_decidableClopen

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
  , "Omega.X.inverseLimitEquiv"
  , "Omega.Rewrite.step_value"
  , "Omega.globalDefect_eq_defectChain"
  , "Omega.SPG.spg_decidableClopen" ]

end Omega.Audit
