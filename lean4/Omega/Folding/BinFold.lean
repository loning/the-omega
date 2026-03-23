import Omega.Folding.FiberSpectrum

/-! ### Binary Fold: folding integers via Zeckendorf projection

The BinFold map sends a natural number N < 2^m to the stable word X.ofNat m N.
This provides a "binary-to-Fibonacci" projection that partitions {0, ..., 2^m - 1}
into fibers over X_m. The resulting histogram differs from the standard fiber
histogram (which uses weight-based folding of Word m). -/

namespace Omega

/-- BinFold: project a natural number onto X_m via Zeckendorf truncation. -/
def cBinFold (m N : Nat) : X m := X.ofNat m N

/-- The BinFold fiber multiplicity: number of integers in {0, ..., 2^m - 1}
    that map to x under BinFold. -/
def cBinFiberMult (m : Nat) (x : X m) : Nat :=
  (Finset.range (2 ^ m)).filter (fun N => cBinFold m N = x) |>.card

/-- The BinFold fiber histogram: number of stable words with BinFold multiplicity k. -/
def cBinFiberHist (m k : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).filter (fun x => cBinFiberMult m x = k) |>.card

/-! ### m = 6 BinFold histogram

At resolution 6, BinFold maps {0, ..., 63} onto 21 stable words.
The histogram is: multiplicity 2 → 8 words, multiplicity 3 → 4 words,
multiplicity 4 → 9 words. -/

/-- BinFold histogram at m = 6: 8 stable words have BinFold multiplicity 2. -/
theorem cBinFiberHist_6_2 : cBinFiberHist 6 2 = 8 := by native_decide
/-- BinFold histogram at m = 6: 4 stable words have BinFold multiplicity 3. -/
theorem cBinFiberHist_6_3 : cBinFiberHist 6 3 = 4 := by native_decide
/-- BinFold histogram at m = 6: 9 stable words have BinFold multiplicity 4. -/
theorem cBinFiberHist_6_4 : cBinFiberHist 6 4 = 9 := by native_decide

/-- The BinFold histogram accounts for all 64 microstates: 8·2 + 4·3 + 9·4 = 64. -/
theorem binFold6_histogram_certificate : 8 * 2 + 4 * 3 + 9 * 4 = 64 := by omega

/-- No stable word has BinFold multiplicity 0 or 1 at m = 6. -/
theorem cBinFiberHist_6_0 : cBinFiberHist 6 0 = 0 := by native_decide
theorem cBinFiberHist_6_1 : cBinFiberHist 6 1 = 0 := by native_decide

/-- The total number of distinct BinFold multiplicities at m = 6 is 3 (values 2, 3, 4). -/
theorem binFold6_distinct_multiplicities :
    cBinFiberHist 6 2 + cBinFiberHist 6 3 + cBinFiberHist 6 4 = 21 := by
  rw [cBinFiberHist_6_2, cBinFiberHist_6_3, cBinFiberHist_6_4]

/-- BinFold multiplicity sum verification: ∑ k · h(k) = 2^m at m = 6. -/
theorem binFold6_sum_check :
    cBinFiberHist 6 0 * 0 + cBinFiberHist 6 1 * 1 + cBinFiberHist 6 2 * 2 +
    cBinFiberHist 6 3 * 3 + cBinFiberHist 6 4 * 4 = 64 := by
  rw [cBinFiberHist_6_0, cBinFiberHist_6_1, cBinFiberHist_6_2,
    cBinFiberHist_6_3, cBinFiberHist_6_4]

end Omega
