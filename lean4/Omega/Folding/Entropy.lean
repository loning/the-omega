import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Omega.Folding.ShiftDynamics

namespace Omega.Entropy

/-- The topological entropy of the golden-mean shift is log(φ).
    This is a placeholder for future Real-valued entropy computations. -/
theorem topological_entropy_bound :
    Real.log 2 > 0 := Real.log_pos (by norm_num)

end Omega.Entropy
