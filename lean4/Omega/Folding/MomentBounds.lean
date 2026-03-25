import Omega.Folding.MomentRecurrence

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- S_2 triple bound
-- ══════════════════════════════════════════════════════════════

/-- S_2(m+1) ≤ 3·S_2(m). Tighter than the quadruple bound. -/
theorem momentSum_two_succ_le_triple (m : Nat) :
    momentSum 2 (m + 1) ≤ 3 * momentSum 2 m := by
  match m with
  | 0 => rw [momentSum_two_one, momentSum_two_zero]; omega
  | 1 => rw [momentSum_two_two, momentSum_two_one]
  | 2 => rw [momentSum_two_three, momentSum_two_two]; omega
  | m + 3 =>
    -- S(m+4) = 2S(m+3) + 2S(m+2) - 2S(m+1)  [from recurrence at m+1]
    -- Need: S(m+4) ≤ 3·S(m+3), i.e., 2S(m+2) - 2S(m+1) ≤ S(m+3)
    -- From succ_ge_double at m+2: S(m+3) ≥ 2·S(m+2) ≥ 2S(m+2) - 2S(m+1)
    have hrec := momentSum_two_recurrence (m + 1)
    have hge := momentSum_two_succ_ge_double (m + 2) (by omega)
    linarith

-- ══════════════════════════════════════════════════════════════
-- Snoc embedding: ewc(m,n) ≤ d_{m+1}(ofNat(m+1,n))
-- ══════════════════════════════════════════════════════════════

/-- The snoc-false embedding: every word of weight n at level m
    extends to a preimage of ofNat(m+1,n) at level m+1,
    giving ewc(m,n) ≤ d_{m+1}(ofNat(m+1,n)). -/
theorem fiberMultiplicity_ge_ewc_via_snoc (m n : Nat) :
    exactWeightCount m n ≤ X.fiberMultiplicity (X.ofNat (m + 1) n) := by
  classical
  let y := X.ofNat (m + 1) n
  show (Finset.univ.filter (fun w : Word m => weight w = n)).card ≤ (X.fiber y).card
  apply Finset.card_le_card_of_injOn (fun w => snoc w false)
    (fun w hw => by
      have hwn : weight w = n := by simpa using hw
      show snoc w false ∈ X.fiber y
      rw [X.mem_fiber]
      rw [Fold_snoc_false_eq, hwn])
    (fun w₁ _ w₂ _ h => by
      have := congr_arg truncate h; simp at this; exact this)

-- ══════════════════════════════════════════════════════════════
-- S_2 mod 8 divisibility
-- ══════════════════════════════════════════════════════════════

/-- S_2(m) ≡ 0 (mod 8) for m ≥ 8. -/
theorem momentSum_two_mod_eight (m : Nat) (hm : 8 ≤ m) : 8 ∣ momentSum 2 m := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 => omega
    | 8 => exact ⟨169, by rw [momentSum_two_eight_rec]⟩
    | 9 => exact ⟨419, by rw [momentSum_two_nine_rec]⟩
    | 10 =>
      have h := momentSum_two_recurrence 7
      simp only [show (7 : Nat) + 3 = 10 from rfl, show (7 : Nat) + 2 = 9 from rfl,
        show (7 : Nat) + 1 = 8 from rfl, momentSum_two_seven_rec,
        momentSum_two_eight_rec, momentSum_two_nine_rec] at h
      exact ⟨1040, by omega⟩
    | m + 11 =>
      have hrec := momentSum_two_recurrence (m + 8)
      rw [show (m + 8 + 3 : Nat) = m + 11 from rfl,
        show (m + 8 + 2 : Nat) = m + 10 from rfl,
        show (m + 8 + 1 : Nat) = m + 9 from rfl] at hrec
      have h8 := ih (m + 8) (by omega) (by omega)
      have h9 := ih (m + 9) (by omega) (by omega)
      have h10 := ih (m + 10) (by omega) (by omega)
      obtain ⟨a, ha⟩ := h8; obtain ⟨b, hb⟩ := h9; obtain ⟨c, hc⟩ := h10
      rw [ha, hb, hc] at hrec
      have hab : a ≤ b := by
        have := momentSum_two_mono' (m + 8)
        rw [ha, show (m + 8 + 1 : Nat) = m + 9 from rfl, hb] at this; omega
      exact ⟨2 * (c + b) - 2 * a, by omega⟩

end Omega
