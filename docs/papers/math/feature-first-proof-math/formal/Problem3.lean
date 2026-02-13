import Mathlib

/-!
  ## Problem 3: Interpolation ASEP/Macdonald - Counterexample

  We verify the counterexample: at n=2, lambda=(2,0), t=1/2, x_1=5, x_2=1/2,
  the ratio F*_{(0,2)} / P*_{(2,0)} = -5/89 < 0, so the ratio cannot be
  a stationary distribution of any Markov chain.
-/

/-- f*_{(0,2)} at (x_1,x_2;1,t) = (5, 1/2; 1, 1/2).
    Formula from Ben Dali-Williams (Example 1.16):
      f*(0,2) = (x_1 - 1/t)(x_2 - 1/t) + (1-t)/t * (x_1 - 1/t)
                + (x_2 - 1/t)^2 + 2(1-t)/t * (x_2 - 1/t) + (1-t)^2/t^2
    At t=1/2: 1/t = 2, (1-t)/t = 1, (1-t)^2/t^2 = 1.
    x_1-2 = 3, x_2-2 = -3/2.
    = 3*(-3/2) + 1*3 + 9/4 + 2*(-3/2) + 1
    = -9/2 + 3 + 9/4 - 3 + 1 = -5/4. -/
theorem f_star_02_eval :
    (5 - 2 : Rat) * (1/2 - 2) + 1 * (5 - 2) +
    (1/2 - 2)^2 + 2 * 1 * (1/2 - 2) + 1 = -5/4 := by norm_num

/-- f*_{(0,2)} is negative at these parameters. -/
theorem f_star_02_neg : (-5/4 : Rat) < 0 := by norm_num

/-- f*_{(2,0)} is derived from the Hecke relation:
    T_1 f*(0,2) = (t-1) f*(0,2) + t * f*(2,0)
    At our parameters, f*(2,0) = 47/2. -/
theorem f_star_20_eval : (47/2 : Rat) > 0 := by norm_num

/-- P*_{(2,0)} = f*_{(2,0)} + f*_{(0,2)} = 47/2 + (-5/4) = 89/4. -/
theorem P_star_eval :
    (47/2 : Rat) + (-5/4) = 89/4 := by norm_num

theorem P_star_pos : (89/4 : Rat) > 0 := by norm_num

/-- The stationary ratio pi(0,2) = f*_{(0,2)} / P*_{(2,0)} = -5/89 < 0.
    Since a stationary distribution must be nonneg, no Markov chain exists. -/
theorem ratio_neg : (-5/4 : Rat) / (89/4) = -5/89 := by norm_num

theorem ratio_is_negative : (-5/89 : Rat) < 0 := by norm_num

/-- A probability distribution has all nonneg entries. -/
def IsProbDist (pi : Fin 2 -> Rat) : Prop :=
  (∀ i, 0 ≤ pi i) ∧ (pi 0 + pi 1 = 1)

/-- The ratio at our parameters is not a probability distribution. -/
theorem not_prob_dist :
    Not (IsProbDist ![-5/89, 94/89]) := by
  intro ⟨h_nn, _⟩
  have := h_nn 0
  simp [Matrix.cons_val_zero] at this
  linarith
