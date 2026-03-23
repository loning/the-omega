import Omega.Folding.FiberSpectrum
import Omega.Folding.FiberArithmetic

/-! ### Window-6 invariants

The resolution m = 6 window provides a computationally accessible test case:
|X_6| = 21 stable words, |Word 6| = 64 microstates, D_6 = 5. -/

namespace Omega

/-- |Word 6| = 2^6 = 64. -/
theorem card_Word_six : Fintype.card (Word 6) = 64 := by rw [X.Word_card]; norm_num

/-- |X_6| = F(8) = 21. -/
theorem card_X_six' : Fintype.card (X 6) = 21 := X.card_X_six

/-- The number of stable words with nontrivial fiber (multiplicity ≥ 2). -/
def cNontrivialFiberCount (m : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).filter (fun x => cFiberMult x ≥ 2) |>.card

/-- At resolution 6, exactly 19 stable words have nontrivial fibers. -/
theorem cNontrivialFiberCount_six : cNontrivialFiberCount 6 = 19 := by native_decide

/-- The trivial fiber count at resolution 6: exactly 2 words have multiplicity 1. -/
theorem cTrivialFiberCount_six : cFiberHist 6 1 = 2 := cFiberHist_6_1

/-- Abelianization rank at resolution 6: |X_6| - #{x : d(x) = 1} = 19.
    This counts the stable words that participate in nontrivial folding. -/
theorem abelianization_rank_six :
    Fintype.card (X 6) - cFiberHist 6 1 = 19 := by
  rw [X.card_X_six, cFiberHist_6_1]

/-- The compression ratio at resolution 6: 64 microstates fold onto 21 types.
    Compression factor = 64/21 ≈ 3.05. -/
theorem compression_ratio_six :
    Fintype.card (Word 6) = 64 ∧ Fintype.card (X 6) = 21 :=
  ⟨card_Word_six, X.card_X_six⟩

/-- The fiber sum identity at resolution 6: ∑ d(x) = 2^6 = 64. -/
theorem fiber_sum_six : ∑ x : X 6, X.fiberMultiplicity x = 64 := by
  rw [X.fiberMultiplicity_sum_eq_pow]; norm_num

/-- Nontrivial fibers account for 64 - 2 = 62 of the 64 microstates. -/
theorem nontrivial_microstate_count_six :
    Fintype.card (Word 6) - cFiberHist 6 1 = 62 := by
  rw [card_Word_six, cFiberHist_6_1]

end Omega
