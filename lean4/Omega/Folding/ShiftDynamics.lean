import Omega.Folding.InverseLimitTopology

namespace Omega.X

/-- The left shift on XInfinity: σ(a)(i) = a(i+1). -/
def shift (a : XInfinity) : XInfinity :=
  ⟨fun i => a.1 (i + 1), fun i h => a.2 (i + 1) h⟩

/-- The shift map is continuous (composition of continuous projections). -/
theorem continuous_shift : Continuous shift := by
  apply Continuous.subtype_mk
  exact continuous_pi fun i => (continuous_apply (i + 1)).comp continuous_subtype_val

/-- The shift map is surjective: prepend false to any sequence. -/
theorem shift_surjective : Function.Surjective shift := by
  intro b
  refine ⟨⟨fun i => if i = 0 then false else b.1 (i - 1), fun i ⟨hi, hi1⟩ => ?_⟩, ?_⟩
  · -- No11Inf proof for prepended sequence
    cases i with
    | zero => simp at hi
    | succ i =>
      simp only [Nat.succ_ne_zero, ↓reduceIte] at hi hi1
      exact b.2 i ⟨hi, by rwa [show i + 1 + 1 - 1 = i + 1 from by omega] at hi1⟩
  · -- shift of constructed sequence = b
    ext i; simp [shift]

/-- Coordinate formula for the left shift: the i-th entry of σ(a) equals a(i+1). -/
theorem shift_val (a : XInfinity) (i : Nat) : (shift a).1 i = a.1 (i + 1) := rfl

end Omega.X
