import Mathlib.Algebra.Group.Subgroup.Basic
import Mathlib.Data.Fintype.Card
import Mathlib.Data.ZMod.Basic

namespace Omega

/-- The fiber of a group homomorphism over a target point. -/
def fiberAt {G H : Type*} [Group G] [Group H] (π : G →* H) (t : H) :=
  {g : G // π g = t}

/-- Any two points in the same fiber differ by a unique kernel element on the right. -/
theorem fiber_torsor_by_kernel
    {G H : Type*} [Group G] [Group H]
    (π : G →* H) (t : H) :
    ∀ x y : fiberAt π t,
      ∃! k : π.ker, y.1 = x.1 * k.1 := by
  intro x y
  refine ⟨⟨x.1⁻¹ * y.1, ?_⟩, ?_, ?_⟩
  · change π (x.1⁻¹ * y.1) = 1
    rw [map_mul, map_inv, x.2, y.2]
    simp
  · calc
      y.1 = 1 * y.1 := by simp
      _ = x.1 * (x.1⁻¹ * y.1) := by simp
  · intro k hk
    apply Subtype.ext
    have hk' : x.1⁻¹ * y.1 = k.1 := by
      have := congrArg (fun z : G => x.1⁻¹ * z) hk
      simpa [mul_assoc] using this
    exact hk'.symm

noncomputable section

/-- As finite sets, `ZMod (2^N)` and length-`N` bitstrings have the same cardinality. -/
theorem zmodTwoPow_card_eq_bits (N : ℕ) :
    Fintype.card (ZMod (2 ^ N)) = Fintype.card (Fin N → Bool) := by
  rw [ZMod.card, Fintype.card_fun, Fintype.card_fin, Fintype.card_bool]

/-- Nonconstructive finite-set equivalence between `ZMod (2^N)` and length-`N` bitstrings.
This is an equivalence of underlying finite sets, not a group isomorphism. -/
noncomputable def zmodTwoPowBitsEquiv (N : ℕ) : ZMod (2 ^ N) ≃ (Fin N → Bool) :=
  Fintype.equivOfCardEq (zmodTwoPow_card_eq_bits N)

/-- Coordinatewise bitstring encoding on six copies. -/
noncomputable def sixZmodTwoPowBitsEquiv (N : ℕ) :
    (Fin 6 → ZMod (2 ^ N)) ≃ (Fin 6 → Fin N → Bool) where
  toFun f i := zmodTwoPowBitsEquiv N (f i)
  invFun g i := (zmodTwoPowBitsEquiv N).symm (g i)
  left_inv f := by
    funext i
    exact (zmodTwoPowBitsEquiv N).left_inv (f i)
  right_inv g := by
    funext i
    exact (zmodTwoPowBitsEquiv N).right_inv (g i)

end

end Omega
