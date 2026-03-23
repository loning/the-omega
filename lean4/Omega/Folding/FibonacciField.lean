import Mathlib.Data.ZMod.Basic
import Mathlib.Algebra.Field.ZMod
import Omega.Folding.FiberArithmetic

namespace Omega

theorem paperFib_three_prime : Nat.Prime (paperFib 3) := by native_decide
theorem paperFib_four_prime : Nat.Prime (paperFib 4) := by native_decide
theorem paperFib_six_prime : Nat.Prime (paperFib 6) := by native_decide
theorem paperFib_eight_not_prime : ¬ Nat.Prime (paperFib 8) := by native_decide
theorem paperFib_twelve_prime : Nat.Prime (paperFib 12) := by native_decide

namespace X

noncomputable section

/-- When paperFib(m+1) is prime, every nonzero element has a multiplicative inverse. -/
theorem stableMul_inv_of_prime (hp : Nat.Prime (paperFib (m + 1))) (x : X m)
    (hx : x ≠ stableZero) :
    ∃ y : X m, stableMul x y = stableOne := by
  have hP : 1 < paperFib (m + 1) := hp.one_lt
  have hne : NeZero (paperFib (m + 1)) := ⟨by omega⟩
  have hsv_ne : stableValue x ≠ 0 := fun h =>
    hx ((X.ofNat_stableValue x).symm.trans (by rw [h]; rfl))
  have hsv_lt := stableValue_lt_paperFib_succ x
  have hcop : Nat.Coprime (stableValue x) (paperFib (m + 1)) :=
    (hp.coprime_iff_not_dvd.mpr (Nat.not_dvd_of_pos_of_lt (Nat.pos_of_ne_zero hsv_ne) hsv_lt)).symm
  -- In ZMod p, stableValue x is a unit with inverse (sv : ZMod p)⁻¹
  have hUnit := (ZMod.isUnit_iff_coprime (stableValue x) (paperFib (m + 1))).mpr hcop
  -- Take k = ((sv : ZMod p)⁻¹).val
  set p := paperFib (m + 1)
  set sv_zmod := (stableValue x : ZMod p)
  set k := (sv_zmod⁻¹).val
  use X.ofNat m k
  -- Prove via stableValue injectivity
  apply (Function.HasLeftInverse.injective ⟨X.ofNat m, X.ofNat_stableValue⟩)
  simp only [X.ofNat_stableValue, stableValue_stableMul, stableValue_stableOne hP,
    stableValue_ofNat_lt k (ZMod.val_lt _)]
  -- Goal: (stableValue x * k) % p = 1
  -- From ZMod: sv_zmod * sv_zmod⁻¹ = 1, taking .val gives the mod equation
  have hsv_ne_zmod : sv_zmod ≠ 0 := by
    simp only [sv_zmod, ne_eq, ZMod.natCast_eq_zero_iff]
    exact Nat.not_dvd_of_pos_of_lt (Nat.pos_of_ne_zero hsv_ne) hsv_lt
  have : Fact (Nat.Prime p) := ⟨hp⟩
  have hmul_zmod : sv_zmod * sv_zmod⁻¹ = 1 := mul_inv_cancel₀ hsv_ne_zmod
  have hmul : (sv_zmod * sv_zmod⁻¹).val = (1 : ZMod p).val := congr_arg ZMod.val hmul_zmod
  rw [ZMod.val_one] at hmul
  simp only [ZMod.val_mul] at hmul
  -- hmul : sv_zmod.val * sv_zmod⁻¹.val % p = 1
  -- Goal : stableValue x * k % paperFib (m + 1) = 1
  -- sv_zmod.val = (stableValue x : ZMod p).val = stableValue x (by val_natCast_of_lt)
  -- k = sv_zmod⁻¹.val (by definition)
  -- p = paperFib (m + 1) (by definition)
  rw [show sv_zmod.val = stableValue x from ZMod.val_natCast_of_lt (by omega)] at hmul
  exact hmul

end

end X

end Omega
