import Omega.Folding.MaxFiber

/-! ### Fiber spectrum: sorted distinct fiber multiplicities

The fiber spectrum at resolution m is the sorted descending list of distinct
fiber multiplicities {|fiber(x)| : x ∈ X_m}. The k-th entry (0-indexed) gives
the (k+1)-th largest distinct multiplicity D_m^{(k+1)}. -/

namespace Omega

section Computable

/-- The multiset of all fiber multiplicities at resolution m. -/
def cFiberMultiset (m : Nat) : Multiset Nat :=
  (@Finset.univ (X m) (fintypeX m)).val.map cFiberMult

/-- The sorted descending list of distinct fiber multiplicities at resolution m. -/
def cFiberSpectrum (m : Nat) : List Nat :=
  (cFiberMultiset m).dedup.sort (· ≥ ·)

/-- The k-th largest distinct fiber multiplicity (0-indexed). Returns 0 if k is out of range. -/
def cNthMaxFiber (m k : Nat) : Nat :=
  (cFiberSpectrum m).getD k 0

-- Verify consistency: first entry matches cMaxFiberMult for small m
theorem cNthMaxFiber_zero_eq_0 : cNthMaxFiber 0 0 = cMaxFiberMult 0 := by native_decide
theorem cNthMaxFiber_zero_eq_5 : cNthMaxFiber 5 0 = cMaxFiberMult 5 := by native_decide
theorem cNthMaxFiber_zero_eq_7 : cNthMaxFiber 7 0 = cMaxFiberMult 7 := by native_decide

/-- Number of stable words achieving the maximum fiber multiplicity. -/
def cMaxFiberAchievers (m : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).filter (fun x => cFiberMult x = cMaxFiberMult m) |>.card

-- Achiever counts for small m
theorem cMaxFiberAchievers_zero : cMaxFiberAchievers 0 = 1 := by native_decide
theorem cMaxFiberAchievers_one : cMaxFiberAchievers 1 = 2 := by native_decide
theorem cMaxFiberAchievers_two : cMaxFiberAchievers 2 = 1 := by native_decide
theorem cMaxFiberAchievers_three : cMaxFiberAchievers 3 = 3 := by native_decide
theorem cMaxFiberAchievers_four : cMaxFiberAchievers 4 = 2 := by native_decide
theorem cMaxFiberAchievers_five : cMaxFiberAchievers 5 = 1 := by native_decide
theorem cMaxFiberAchievers_six : cMaxFiberAchievers 6 = 2 := by native_decide
theorem cMaxFiberAchievers_seven : cMaxFiberAchievers 7 = 4 := by native_decide

-- Achiever positivity: at least one element achieves the max
-- Achiever count bounded by total cardinality
theorem cMaxFiberAchievers_le_univ (m : Nat) :
    cMaxFiberAchievers m ≤ (@Finset.univ (X m) (fintypeX m)).card := by
  exact Finset.card_filter_le _ _

/-- Fiber histogram: number of stable words with fiber multiplicity exactly k. -/
def cFiberHist (m k : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).filter (fun x => cFiberMult x = k) |>.card

-- m=4 histogram: multiplicities 1,2,3 have counts 2,4,2
theorem cFiberHist_4_1 : cFiberHist 4 1 = 2 := by native_decide
theorem cFiberHist_4_2 : cFiberHist 4 2 = 4 := by native_decide
theorem cFiberHist_4_3 : cFiberHist 4 3 = 2 := by native_decide

-- m=6 histogram: multiplicities 1..5 have counts 2,4,8,5,2
theorem cFiberHist_6_1 : cFiberHist 6 1 = 2 := by native_decide
theorem cFiberHist_6_2 : cFiberHist 6 2 = 4 := by native_decide
theorem cFiberHist_6_3 : cFiberHist 6 3 = 8 := by native_decide
theorem cFiberHist_6_4 : cFiberHist 6 4 = 5 := by native_decide
theorem cFiberHist_6_5 : cFiberHist 6 5 = 2 := by native_decide

end Computable

namespace X
noncomputable section

/-- The set of distinct fiber multiplicities at resolution m. -/
noncomputable def fiberValueSet (m : Nat) : Finset Nat :=
  (Finset.univ : Finset (X m)).image fiberMultiplicity

/-- The fiber value set is nonempty. -/
theorem fiberValueSet_nonempty (m : Nat) : (fiberValueSet m).Nonempty :=
  Finset.Nonempty.image Finset.univ_nonempty _

end
end X

/-! ### Base value verification via native_decide -/

section BaseValues

-- Fiber spectrum for small m values
theorem cFiberSpectrum_zero : cFiberSpectrum 0 = [1] := by native_decide
theorem cFiberSpectrum_one : cFiberSpectrum 1 = [1] := by native_decide
theorem cFiberSpectrum_two : cFiberSpectrum 2 = [2, 1] := by native_decide
theorem cFiberSpectrum_three : cFiberSpectrum 3 = [2, 1] := by native_decide
theorem cFiberSpectrum_four : cFiberSpectrum 4 = [3, 2, 1] := by native_decide
theorem cFiberSpectrum_five : cFiberSpectrum 5 = [4, 3, 2, 1] := by native_decide
theorem cFiberSpectrum_six : cFiberSpectrum 6 = [5, 4, 3, 2, 1] := by native_decide
theorem cFiberSpectrum_seven : cFiberSpectrum 7 = [6, 5, 4, 3, 2, 1] := by native_decide
theorem cFiberSpectrum_eight : cFiberSpectrum 8 = [8, 7, 6, 5, 4, 3, 2, 1] := by native_decide
theorem cFiberSpectrum_nine : cFiberSpectrum 9 =
    [10, 9, 8, 7, 6, 5, 4, 3, 2, 1] := by native_decide
theorem cFiberSpectrum_ten : cFiberSpectrum 10 =
    [13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1] := by native_decide

-- Second largest fiber multiplicities: D_m^{(2)}
theorem cNthMaxFiber_second_four : cNthMaxFiber 4 1 = 2 := by native_decide
theorem cNthMaxFiber_second_five : cNthMaxFiber 5 1 = 3 := by native_decide
theorem cNthMaxFiber_second_six : cNthMaxFiber 6 1 = 4 := by native_decide
theorem cNthMaxFiber_second_seven : cNthMaxFiber 7 1 = 5 := by native_decide

theorem cNthMaxFiber_second_eight : cNthMaxFiber 8 1 = 7 := by native_decide
theorem cNthMaxFiber_second_nine : cNthMaxFiber 9 1 = 9 := by native_decide
theorem cNthMaxFiber_second_ten : cNthMaxFiber 10 1 = 12 := by native_decide

-- Third largest fiber multiplicities: D_m^{(3)}
theorem cNthMaxFiber_third_four : cNthMaxFiber 4 2 = 1 := by native_decide
theorem cNthMaxFiber_third_five : cNthMaxFiber 5 2 = 2 := by native_decide
theorem cNthMaxFiber_third_six : cNthMaxFiber 6 2 = 3 := by native_decide
theorem cNthMaxFiber_third_seven : cNthMaxFiber 7 2 = 4 := by native_decide

end BaseValues

section Parity

/-- Count of stable words with odd fiber multiplicity. -/
def cOddFiberCount (m : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).filter (fun x => cFiberMult x % 2 = 1) |>.card

/-- Count of stable words with even fiber multiplicity. -/
def cEvenFiberCount (m : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).filter (fun x => cFiberMult x % 2 = 0) |>.card

-- Parity base values
theorem cOddFiberCount_zero : cOddFiberCount 0 = 1 := by native_decide
theorem cOddFiberCount_one : cOddFiberCount 1 = 2 := by native_decide
theorem cOddFiberCount_two : cOddFiberCount 2 = 2 := by native_decide
theorem cOddFiberCount_three : cOddFiberCount 3 = 2 := by native_decide
theorem cOddFiberCount_four : cOddFiberCount 4 = 4 := by native_decide
theorem cOddFiberCount_five : cOddFiberCount 5 = 8 := by native_decide
theorem cOddFiberCount_six : cOddFiberCount 6 = 12 := by native_decide

theorem cEvenFiberCount_zero : cEvenFiberCount 0 = 0 := by native_decide
theorem cEvenFiberCount_one : cEvenFiberCount 1 = 0 := by native_decide
theorem cEvenFiberCount_two : cEvenFiberCount 2 = 1 := by native_decide
theorem cEvenFiberCount_three : cEvenFiberCount 3 = 3 := by native_decide
theorem cEvenFiberCount_four : cEvenFiberCount 4 = 4 := by native_decide
theorem cEvenFiberCount_five : cEvenFiberCount 5 = 5 := by native_decide
theorem cEvenFiberCount_six : cEvenFiberCount 6 = 9 := by native_decide

end Parity

end Omega
