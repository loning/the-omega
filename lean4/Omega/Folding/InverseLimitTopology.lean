import Mathlib.Topology.Connected.TotallyDisconnected
import Omega.Folding.InverseLimit

namespace Omega.X

/-- No11Inf is a closed subset of the product space ℕ → Bool. -/
theorem isClosed_no11Inf : IsClosed {a : ℕ → Bool | No11Inf a} := by
  simp only [No11Inf, Set.setOf_forall]
  apply isClosed_iInter; intro i
  apply IsOpen.isClosed_compl
  -- Show {a | a i = true ∧ a (i+1) = true} is open
  have hOpen_i : IsOpen ((fun a : ℕ → Bool => a i) ⁻¹' {true}) :=
    (isOpen_discrete ({true} : Set Bool)).preimage (continuous_apply i)
  have hOpen_i1 : IsOpen ((fun a : ℕ → Bool => a (i + 1)) ⁻¹' {true}) :=
    (isOpen_discrete ({true} : Set Bool)).preimage (continuous_apply (i + 1))
  convert hOpen_i.inter hOpen_i1 using 1

/-- XInfinity is compact: closed subset of compact product space ℕ → Bool. -/
instance : CompactSpace XInfinity :=
  isCompact_iff_compactSpace.mp isClosed_no11Inf.isCompact

/-- XInfinity is totally disconnected: subspace of ℕ → Bool (product of discrete spaces). -/
instance : TotallyDisconnectedSpace XInfinity :=
  Subtype.totallyDisconnectedSpace

end Omega.X
