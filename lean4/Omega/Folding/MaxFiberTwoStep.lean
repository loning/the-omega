import Omega.Folding.MaxFiber

namespace Omega

/-- When n < fib(m+3), X.ofNat(m+2, n) has bit m+1 = false. -/
theorem ofNat_last_false_of_lt (m n : Nat) (hn : n < Nat.fib (m + 3)) :
    (X.ofNat (m + 2) n).1 ⟨m + 1, by omega⟩ = false := by
  by_contra h
  push_neg at h
  have htrue : get (X.ofNat (m + 2) n).1 (m + 1) = true := by
    rw [get_of_lt _ (show m + 1 < m + 2 from by omega)]
    cases hb : (X.ofNat (m + 2) n).1 ⟨m + 1, by omega⟩ <;> simp_all
  have hmem : (m + 1) + 2 ∈ Nat.zeckendorf n :=
    (X.get_ofNat_eq_true_iff (show m + 1 < m + 2 from by omega)).mp htrue
  have hle := X.fib_le_of_mem_zeckendorf hmem
  simp only [show m + 1 + 2 = m + 3 from by omega] at hle
  exact absurd hn (not_lt.mpr hle)

/-- When fib(m+3) ≤ n < fib(m+4), X.ofNat(m+2, n) has bit m+1 = true. -/
theorem ofNat_last_true_of_ge (m n : Nat)
    (hlo : Nat.fib (m + 3) ≤ n) (hhi : n < Nat.fib (m + 4)) :
    (X.ofNat (m + 2) n).1 ⟨m + 1, by omega⟩ = true := by
  have hlt : m + 1 < m + 2 := by omega
  rw [show (X.ofNat (m + 2) n).1 ⟨m + 1, by omega⟩ =
    get (X.ofNat (m + 2) n).1 (m + 1) from by rw [get_of_lt _ hlt]]
  rw [X.get_ofNat_eq_true_iff hlt]
  have hpos : 0 < n := Nat.lt_of_lt_of_le (Nat.fib_pos.mpr (by omega)) hlo
  rw [Nat.zeckendorf_of_pos hpos]
  have hGF : Nat.greatestFib n = m + 3 :=
    Nat.le_antisymm
      (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hhi))
      (Nat.le_greatestFib.mpr hlo)
  rw [hGF]; simp only [show m + 1 + 2 = m + 3 from by omega]
  exact List.mem_cons_self ..

-- ══════════════════════════════════════════════════════════════
-- Hidden bit count
-- ══════════════════════════════════════════════════════════════

/-- Count of words with weight ≥ fib(m+2). -/
def hiddenBitCount (m : Nat) : Nat :=
  (Finset.univ (α := Word m)).filter (fun w => Nat.fib (m + 2) ≤ weight w) |>.card

theorem hiddenBitCount_zero : hiddenBitCount 0 = 0 := by decide

theorem hiddenBitCount_one : hiddenBitCount 1 = 0 := by decide

-- ══════════════════════════════════════════════════════════════
-- Helper: if weight w ≥ fib(m+4) for w : Word(m+2), then w[m+1]=true
-- ══════════════════════════════════════════════════════════════

private theorem last_true_of_heavy (m : Nat) (w : Word (m + 2))
    (hw : Nat.fib (m + 4) ≤ weight w) : w ⟨m + 1, by omega⟩ = true := by
  by_contra h
  have hfalse : w ⟨m + 1, by omega⟩ = false := Bool.eq_false_iff.mpr h
  have hwd : weight w = weight (truncate w) := by simp [weight, hfalse]
  -- truncate w : Word (m + 1), so weight < Nat.fib (m + 4)
  have hlt : weight (truncate w) < Nat.fib ((m + 1) + 3) := X.weight_lt_fib _
  rw [show (m + 1) + 3 = m + 4 from by omega] at hlt
  omega

-- ══════════════════════════════════════════════════════════════
-- Recurrence: hiddenBitCount (m+2) = 2^m + hiddenBitCount m
-- ══════════════════════════════════════════════════════════════

theorem hiddenBitCount_recurrence (m : Nat) :
    hiddenBitCount (m + 2) = 2 ^ m + hiddenBitCount m := by
  unfold hiddenBitCount
  -- Abbreviations
  have hfib4 : Nat.fib (m + 4) = Nat.fib (m + 2) + Nat.fib (m + 3) := by
    have := fib_succ_succ' (m + 2)
    rw [show m + 2 + 2 = m + 4 from by omega, show m + 2 + 1 = m + 3 from by omega] at this
    omega
  -- B_{m+2}: {w : Word(m+2) | fib(m+4) ≤ weight w}
  -- Split into BF = {w | ... ∧ w[m]=false} and BT = {w | ... ∧ w[m]=true}
  -- Define BF and BT as single filters on Finset.univ
  let BF := (Finset.univ (α := Word (m + 2))).filter
    (fun w => Nat.fib (m + 2 + 2) ≤ weight w ∧ w ⟨m, by omega⟩ = false)
  let BT := (Finset.univ (α := Word (m + 2))).filter
    (fun w => Nat.fib (m + 2 + 2) ≤ weight w ∧ w ⟨m, by omega⟩ = true)
  -- B = BF ∪ BT
  have hpartition : (Finset.univ (α := Word (m + 2))).filter
      (fun w => Nat.fib (m + 2 + 2) ≤ weight w) = BF ∪ BT := by
    ext w
    simp only [Finset.mem_filter, Finset.mem_univ, true_and, Finset.mem_union, BF, BT]
    constructor
    · intro hw
      by_cases hb : w ⟨m, by omega⟩ = true
      · right; exact ⟨hw, hb⟩
      · left; exact ⟨hw, Bool.eq_false_iff.mpr hb⟩
    · rintro (⟨hw, _⟩ | ⟨hw, _⟩) <;> exact hw
  have hdisjoint : Disjoint BF BT := by
    simp only [BF, BT, Finset.disjoint_filter]
    intro w _ ⟨_, hF⟩ ⟨_, hT⟩; rw [hF] at hT; exact Bool.noConfusion hT
  -- |BF| = hiddenBitCount m
  have hBF_card : BF.card =
      ((Finset.univ (α := Word m)).filter (fun w => Nat.fib (m + 2) ≤ weight w)).card := by
    apply Finset.card_bij (fun w _ => truncate (truncate w))
    · -- maps into target
      intro w hw
      simp only [Finset.mem_filter, Finset.mem_univ, true_and, BF] at hw ⊢
      have hwt := hw.1
      have hwf := hw.2
      have hlast : w ⟨m + 1, by omega⟩ = true :=
        last_true_of_heavy m w (by rw [show m + 2 + 2 = m + 4 from by omega] at hwt; exact hwt)
      have hwd : weight w = weight (truncate (truncate w)) + Nat.fib (m + 3) := by
        conv_lhs => rw [weight_of_lastTrue hlast]
        rw [weight_of_lastFalse (show (truncate w) ⟨m, _⟩ = false by simp [truncate, hwf])]
      rw [show m + 2 + 2 = m + 4 from by omega] at hwt
      omega
    · -- injective
      intro w1 hw1 w2 hw2 heq
      simp only [Finset.mem_filter, Finset.mem_univ, true_and, BF] at hw1 hw2
      have h1l : w1 ⟨m + 1, by omega⟩ = true :=
        last_true_of_heavy m w1 (by rw [show m + 2 + 2 = m + 4 from by omega] at hw1; exact hw1.1)
      have h2l : w2 ⟨m + 1, by omega⟩ = true :=
        last_true_of_heavy m w2 (by rw [show m + 2 + 2 = m + 4 from by omega] at hw2; exact hw2.1)
      funext i
      by_cases h1 : i.val < m
      · -- For i < m, use heq (truncate ∘ truncate agrees)
        have := congrFun heq ⟨i.val, h1⟩
        simp [truncate] at this
        exact this
      · by_cases h2 : i.val = m
        · -- At position m, both are false
          have hi : i = ⟨m, by omega⟩ := Fin.ext h2
          rw [hi, hw1.2, hw2.2]
        · -- At position m+1, both are true
          have h3 : i.val = m + 1 := by omega
          have hi : i = ⟨m + 1, by omega⟩ := Fin.ext h3
          rw [hi, h1l, h2l]
    · -- surjective
      intro u hu
      simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hu
      refine ⟨snoc (snoc u false) true, ?_, by simp⟩
      simp only [Finset.mem_filter, Finset.mem_univ, true_and, BF]
      refine ⟨?_, ?_⟩
      · show Nat.fib (m + 2 + 2) ≤ weight (snoc (snoc u false) true)
        rw [weight_snoc, weight_snoc]
        simp only [Bool.false_eq_true, ite_false, Nat.add_zero, ite_true]
        rw [show m + 2 + 2 = m + 4 from by omega, show m + 1 + 2 = m + 3 from by omega]; omega
      · show snoc (snoc u false) true ⟨m, by omega⟩ = false
        simp [snoc, show m < m + 1 from by omega]
  -- |BT| = 2^m
  have hBT_card : BT.card = 2 ^ m := by
    have hcard_word : (Finset.univ (α := Word m)).card = 2 ^ m := by
      simp [Fintype.card_fin, Fintype.card_bool]
    rw [← hcard_word]; symm
    apply Finset.card_bij (fun w _ => snoc (snoc w true) true)
    · -- maps into target
      intro w _
      simp only [Finset.mem_filter, Finset.mem_univ, true_and, BT]
      refine ⟨?_, ?_⟩
      · show Nat.fib (m + 2 + 2) ≤ weight (snoc (snoc w true) true)
        rw [weight_snoc, weight_snoc]; simp only [ite_true]
        rw [show m + 2 + 2 = m + 4 from by omega, show m + 1 + 2 = m + 3 from by omega]; omega
      · show snoc (snoc w true) true ⟨m, by omega⟩ = true
        simp [snoc, show m < m + 1 from by omega]
    · -- injective
      intro w1 _ w2 _ h
      have : ∀ i : Fin m, w1 i = w2 i := by
        intro i
        have := congr_fun h (⟨i.val, by omega⟩ : Fin (m + 2))
        simp [snoc, show i.val < m from i.isLt, show i.val < m + 1 from by omega] at this
        exact this
      exact funext this
    · -- surjective
      intro w hw
      simp only [Finset.mem_filter, Finset.mem_univ, true_and, BT] at hw
      have hwt := hw.1
      have hwb := hw.2
      have hlast : w ⟨m + 1, by omega⟩ = true := by
        apply last_true_of_heavy m w
        rw [show m + 2 + 2 = m + 4 from by omega] at hwt; exact hwt
      refine ⟨truncate (truncate w), Finset.mem_univ _, ?_⟩
      funext i
      by_cases h1 : i.val < m
      · simp [snoc, truncate, h1, show i.val < m + 1 from by omega]
      · by_cases h2 : i.val = m
        · have hi : (⟨m, by omega⟩ : Fin (m + 2)) = i := Fin.ext h2.symm
          rw [← hi]; simp [snoc, show m < m + 1 from by omega, hwb]
        · have h3 : i.val = m + 1 := by omega
          have hi : (⟨m + 1, by omega⟩ : Fin (m + 2)) = i := Fin.ext h3.symm
          rw [← hi]; simp [snoc, hlast]
  -- Combine
  rw [hpartition, Finset.card_union_of_disjoint hdisjoint, hBF_card, hBT_card]
  omega

-- ══════════════════════════════════════════════════════════════
-- Closed form: hiddenBitCount m * 3 + δ = 2^m
-- ══════════════════════════════════════════════════════════════

theorem hiddenBitCount_closed (m : Nat) :
    hiddenBitCount m * 3 + (if m % 2 = 0 then 1 else 2) = 2 ^ m := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => simp [hiddenBitCount_zero]
    | 1 => simp [hiddenBitCount_one]
    | m + 2 =>
      rw [hiddenBitCount_recurrence]
      have ihm := ih m (by omega)
      have hmod : (m + 2) % 2 = m % 2 := by omega
      rw [hmod]
      have h2 : 2 ^ (m + 2) = 4 * 2 ^ m := by ring
      omega

end Omega
