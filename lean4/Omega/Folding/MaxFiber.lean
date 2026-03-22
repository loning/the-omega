import Mathlib.Data.Finset.Lattice.Fold
import Omega.Folding.Fiber

namespace Omega

theorem restrict_ofNat (m n : Nat) : X.restrict (X.ofNat (m + 1) n) = X.ofNat m n := by
  apply Subtype.ext; funext i; simp [X.restrict, X.ofNat, X.ofIndices, X.wordOfIndices, truncate]

theorem restrict_Fold_snoc_false {m : Nat} (w : Word (m + 1)) :
    X.restrict (Fold (snoc w false)) = Fold w := by
  unfold Fold; rw [weight_snoc]; simp only [Bool.false_eq_true, ↓reduceIte, Nat.add_zero]
  exact restrict_ofNat (m + 1) (weight w)

namespace X
noncomputable section

instance instNonempty (m : Nat) : Nonempty (X m) := ⟨⟨fun _ => false, no11_allFalse⟩⟩

noncomputable def maxFiberMultiplicity (m : Nat) : Nat :=
  Finset.sup' Finset.univ Finset.univ_nonempty (fun x : X m => fiberMultiplicity x)

theorem maxFiberMultiplicity_achieved (m : Nat) :
    ∃ x : X m, fiberMultiplicity x = maxFiberMultiplicity m := by
  obtain ⟨x, _, hx⟩ := Finset.exists_mem_eq_sup' Finset.univ_nonempty
    (fun x : X m => fiberMultiplicity x); exact ⟨x, hx.symm⟩

theorem fiberMultiplicity_le_max (x : X m) :
    fiberMultiplicity x ≤ maxFiberMultiplicity m :=
  Finset.le_sup' _ (Finset.mem_univ x)

theorem maxFiberMultiplicity_pos (m : Nat) : 0 < maxFiberMultiplicity m := by
  obtain ⟨x, hx⟩ := maxFiberMultiplicity_achieved m; rw [← hx]; exact fiberMultiplicity_pos x

end
end X

section Computable

private def no11Bool' : (m : Nat) → Word m → Bool
  | 0, _ => true
  | 1, _ => true
  | m + 2, w => no11Bool' (m + 1) (truncate w) && !(w ⟨m, by omega⟩ && w ⟨m + 1, by omega⟩)

private theorem no11Bool'_iff : ∀ {m : Nat} (w : Word m), no11Bool' m w = true ↔ No11 w
  | 0, w => ⟨fun _ i h _ => absurd (lt_of_get_eq_true h) (Nat.not_lt_zero _),
             fun _ => rfl⟩
  | 1, w => ⟨fun _ i h h1 => by
      have := lt_of_get_eq_true h; have := lt_of_get_eq_true h1; omega,
    fun _ => rfl⟩
  | m + 2, w => by
    simp only [no11Bool', Bool.and_eq_true, Bool.not_eq_true', Bool.and_eq_false_iff]
    constructor
    · rintro ⟨hPrev, hLast⟩ i hgi hgi1
      have hi := lt_of_get_eq_true hgi
      have hi1 := lt_of_get_eq_true hgi1
      by_cases hEq : i = m
      · subst hEq
        simp only [get, hi, dite_true] at hgi
        simp only [get, hi1, dite_true] at hgi1
        rcases hLast with h | h <;> [rw [hgi] at h; rw [hgi1] at h] <;> simp at h
      · have hiLt : i < m + 1 := by omega
        have hi1Lt : i + 1 < m + 2 := hi1
        have hgi' : get (truncate w) i = true := by
          rw [truncate_get_eq w (by omega : i < m + 1)]; exact hgi
        have hgi1' : get (truncate w) (i + 1) = true := by
          rw [truncate_get_eq w (by omega : i + 1 < m + 1)]; exact hgi1
        exact ((no11Bool'_iff (truncate w)).mp hPrev) i hgi' hgi1'
    · intro h
      exact ⟨(no11Bool'_iff (truncate w)).mpr (no11_truncate h), by
        by_cases hm : w ⟨m, by omega⟩ = true
        · right; by_contra hc; push_neg at hc
          exact h m (by simp [get, show m < m + 2 from by omega, hm])
            (by simp [get, show m + 1 < m + 2 from by omega, hc])
        · left; exact Bool.eq_false_iff.mpr hm⟩

private def decNo11 (w : Word m) : Decidable (No11 w) :=
  if h : no11Bool' m w = true then isTrue ((no11Bool'_iff w).mp h)
  else isFalse (fun hNo11 => h ((no11Bool'_iff w).mpr hNo11))

private def fintypeX (m : Nat) : Fintype (X m) :=
  @Subtype.fintype _ _ (fun w => decNo11 w) inferInstance

private instance decEqX (m : Nat) : DecidableEq (X m) :=
  fun a b => decidable_of_iff (a.1 = b.1) Subtype.ext_iff.symm

private def cFiberMult (x : X m) : Nat :=
  (Finset.univ.filter (fun w : Word m => Fold w = x)).card

private theorem cFiberMult_eq (x : X m) : cFiberMult x = X.fiberMultiplicity x := by
  unfold cFiberMult X.fiberMultiplicity; congr 1; unfold X.fiber; ext w
  simp only [Finset.mem_filter, Finset.mem_univ, true_and]

def cMaxFiberMult (m : Nat) : Nat :=
  (@Finset.univ (X m) (fintypeX m)).sup'
    (@Finset.univ_nonempty _ (fintypeX m) (X.instNonempty m)) (fun x => cFiberMult x)

private theorem cMaxFiberMult_eq (m : Nat) : cMaxFiberMult m = X.maxFiberMultiplicity m := by
  simp only [cMaxFiberMult, X.maxFiberMultiplicity]; apply le_antisymm
  · exact Finset.sup'_le _ _ fun x _ => by rw [cFiberMult_eq]; exact X.fiberMultiplicity_le_max x
  · exact Finset.sup'_le _ _ fun x _ => by
      rw [← cFiberMult_eq]; exact Finset.le_sup' _ (@Finset.mem_univ _ (fintypeX m) x)

end Computable

namespace X
section ClosedForm

theorem maxFiberMultiplicity_zero : maxFiberMultiplicity 0 = 1 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_one : maxFiberMultiplicity 1 = 1 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_two : maxFiberMultiplicity 2 = 2 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_three : maxFiberMultiplicity 3 = 2 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_four : maxFiberMultiplicity 4 = 3 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_five : maxFiberMultiplicity 5 = 4 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_six : maxFiberMultiplicity 6 = 5 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_seven : maxFiberMultiplicity 7 = 6 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_eight : maxFiberMultiplicity 8 = 8 := by rw [← cMaxFiberMult_eq]; native_decide
theorem maxFiberMultiplicity_nine : maxFiberMultiplicity 9 = 10 := by rw [← cMaxFiberMult_eq]; native_decide

private theorem snoc_truncate_last {m : Nat} (w : Word (m + 1)) :
    snoc (truncate w) (w ⟨m, Nat.lt_succ_self m⟩) = w := by
  funext i; by_cases h : i.1 < m
  · simp [snoc, truncate, h]
  · have : i = ⟨m, Nat.lt_succ_self m⟩ := Fin.ext (Nat.eq_of_lt_succ_of_not_lt i.isLt h)
    subst this; simp [snoc, h]

private theorem weight_lt_paperFib {m : Nat} (w : Word m) : weight w < paperFib (m + 2) := by
  induction m with
  | zero => simp [weight, paperFib]
  | succ m ih =>
    simp only [weight]
    have htr := ih (truncate w)
    have hRec : paperFib (m + 2) + paperFib (m + 1) = paperFib (m + 3) := paperFib_add (m + 1)
    cases h : w ⟨m, Nat.lt_succ_self m⟩
    · simp only [h, Bool.false_eq_true, ↓reduceIte, Nat.add_zero]
      show weight (truncate w) < paperFib (m + 3); omega
    · simp only [h, ↓reduceIte]
      show weight (truncate w) + paperFib (m + 1) < paperFib (m + 3); omega

private theorem weight_expand {m : Nat} (w : Word (m + 2)) (hLast : w ⟨m + 1, by omega⟩ = true) :
    weight w = weight (truncate (truncate w)) +
    (if w ⟨m, by omega⟩ = true then paperFib (m + 1) else 0) + paperFib (m + 2) := by
  have h1 : weight w = weight (truncate w) + paperFib (m + 2) := by
    rw [weight]; simp only [hLast, ↓reduceIte]
  have h2 : weight (truncate w) = weight (truncate (truncate w)) +
      (if (truncate w) ⟨m, Nat.lt_succ_self m⟩ = true then paperFib (m + 1) else 0) := by
    rw [weight]
  have h3 : (truncate w) ⟨m, Nat.lt_succ_self m⟩ = w ⟨m, by omega⟩ := by
    simp [truncate]
  rw [h1, h2, h3]

private theorem ofNat_add_paperFib {m : Nat} (k : Nat) (hk : m + 2 ≤ k)
    (n : Nat) (hn : n < paperFib k) : X.ofNat m (n + paperFib k) = X.ofNat m n := by
  apply Subtype.ext; funext j
  simp only [X.ofNat, X.ofIndices, X.wordOfIndices]; congr 1; apply propext
  change j.1 + 2 ∈ Nat.zeckendorf (n + Nat.fib (k + 1)) ↔ j.1 + 2 ∈ Nat.zeckendorf n
  have hFk : 0 < Nat.fib k := Nat.fib_pos.mpr (by omega)
  have hFk1 : 0 < Nat.fib (k + 1) := Nat.fib_pos.mpr (by omega)
  have hFibR : Nat.fib (k + 2) = Nat.fib k + Nat.fib (k + 1) := Nat.fib_add_two
  have hFibR2 : Nat.fib (k + 3) = Nat.fib (k + 1) + Nat.fib (k + 2) := Nat.fib_add_two
  have hn' : n < Nat.fib (k + 1) := hn
  have hPos : 0 < n + Nat.fib (k + 1) := by omega
  rw [Nat.zeckendorf_of_pos hPos]
  by_cases hSmall : n < Nat.fib k
  · -- greatestFib(n + fib(k+1)) = k+1
    have hUp : n + Nat.fib (k + 1) < Nat.fib (k + 2) := by omega
    have hGF : Nat.greatestFib (n + Nat.fib (k + 1)) = k + 1 :=
      Nat.le_antisymm (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hUp))
        (Nat.le_greatestFib.mpr (by omega))
    rw [hGF, Nat.add_sub_cancel]; simp only [List.mem_cons]
    exact ⟨fun h => h.elim (by omega) id, Or.inr⟩
  · -- greatestFib(n + fib(k+1)) = k+2
    push_neg at hSmall
    have hUp : n + Nat.fib (k + 1) < Nat.fib (k + 3) := by omega
    have hLo : Nat.fib (k + 2) ≤ n + Nat.fib (k + 1) := by omega
    have hGF : Nat.greatestFib (n + Nat.fib (k + 1)) = k + 2 :=
      Nat.le_antisymm (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hUp))
        (Nat.le_greatestFib.mpr hLo)
    have hSub : n + Nat.fib (k + 1) - Nat.fib (k + 2) = n - Nat.fib k := by omega
    rw [hGF, hSub]
    have hn_pos : 0 < n := by omega
    have hGF_n : Nat.greatestFib n = k :=
      Nat.le_antisymm (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hn'))
        (Nat.le_greatestFib.mpr hSmall)
    rw [Nat.zeckendorf_of_pos hn_pos, hGF_n]; simp only [List.mem_cons]
    exact ⟨fun h => h.elim (by omega) (Or.inr ·), fun h => h.elim (by omega) (Or.inr ·)⟩

private theorem fib_le_of_mem_zeckendorf {k n : Nat} (h : k ∈ Nat.zeckendorf n) :
    Nat.fib k ≤ n := by
  have hMem : Nat.fib k ∈ (Nat.zeckendorf n).map Nat.fib := List.mem_map.mpr ⟨k, h, rfl⟩
  calc Nat.fib k ≤ ((Nat.zeckendorf n).map Nat.fib).sum :=
        List.single_le_sum (fun _ _ => Nat.zero_le _) _ hMem
    _ = n := Nat.sum_zeckendorf_fib n

private theorem ofNat_ne_of_shift {m : Nat} (wt : Nat) (hwt : wt < paperFib (m + 2)) :
    X.ofNat (m + 2) (wt + paperFib (m + 2)) ≠ X.ofNat (m + 2) (wt + paperFib (m + 3)) := by
  intro heq
  have hFib4 : Nat.fib (m + 4) = Nat.fib (m + 2) + Nat.fib (m + 3) := Nat.fib_add_two
  have hFib5 : Nat.fib (m + 5) = Nat.fib (m + 3) + Nat.fib (m + 4) := Nat.fib_add_two
  have hwt' : wt < Nat.fib (m + 3) := hwt
  -- n₂ = wt + fib(m+4): zeck = (m+4) :: zeck(wt)
  have hN2_up : wt + Nat.fib (m + 4) < Nat.fib (m + 5) := by omega
  have hN2_lo : Nat.fib (m + 4) ≤ wt + Nat.fib (m + 4) := by omega
  have hN2_gf : Nat.greatestFib (wt + Nat.fib (m + 4)) = m + 4 :=
    Nat.le_antisymm (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hN2_up))
      (Nat.le_greatestFib.mpr hN2_lo)
  have hN2_zeck : Nat.zeckendorf (wt + Nat.fib (m + 4)) = (m + 4) :: Nat.zeckendorf wt := by
    rw [Nat.zeckendorf_of_pos (by omega), hN2_gf, Nat.add_sub_cancel]
  -- (m+3) ∉ zeck(n₂)
  have hM3_not_n2 : (m + 3) ∉ Nat.zeckendorf (wt + Nat.fib (m + 4)) := by
    rw [hN2_zeck]; simp only [List.mem_cons]
    intro h; cases h with
    | inl h => omega
    | inr h => exact absurd (fib_le_of_mem_zeckendorf h) (by omega)
  -- Extract bit (m+1) iff from heq
  have hm1_lt : m + 1 < m + 2 := by omega
  -- If the two X.ofNat values are equal, their bits agree. Bit (m+1) encodes (m+3) membership.
  have hBit : (m + 3 ∈ Nat.zeckendorf (wt + Nat.fib (m + 3))) ↔
      (m + 3 ∈ Nat.zeckendorf (wt + Nat.fib (m + 4))) := by
    have hBitEq : get (X.ofNat (m + 2) (wt + Nat.fib (m + 3))).1 (m + 1) =
        get (X.ofNat (m + 2) (wt + Nat.fib (m + 4))).1 (m + 1) := by
      simp only [get, hm1_lt, dite_true]; exact congr_arg (fun x => x.1 ⟨m + 1, hm1_lt⟩) heq
    rw [show m + 3 = (m + 1) + 2 from by omega]
    rw [← X.get_ofNat_eq_true_iff hm1_lt, ← X.get_ofNat_eq_true_iff hm1_lt]
    exact ⟨fun h => by rw [← hBitEq]; exact h, fun h => by rw [hBitEq]; exact h⟩
  by_cases hSmall : wt < Nat.fib (m + 2)
  · -- Case A: gf(n₁) = m+3, so (m+3) ∈ zeck(n₁). Contradiction with (m+3) ∉ zeck(n₂).
    have hN1_up : wt + Nat.fib (m + 3) < Nat.fib (m + 4) := by omega
    have hN1_gf : Nat.greatestFib (wt + Nat.fib (m + 3)) = m + 3 :=
      Nat.le_antisymm (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hN1_up))
        (Nat.le_greatestFib.mpr (by omega))
    have hM3_in_n1 : (m + 3) ∈ Nat.zeckendorf (wt + Nat.fib (m + 3)) := by
      rw [Nat.zeckendorf_of_pos (by omega), hN1_gf]; exact List.mem_cons_self ..
    exact hM3_not_n2 (hBit.mp hM3_in_n1)
  · -- Case B: use bit m. (m+2) ∈ zeck(n₂) but (m+2) ∉ zeck(n₁).
    push_neg at hSmall
    have hm_lt : m < m + 2 := by omega
    have hBitM : (m + 2 ∈ Nat.zeckendorf (wt + Nat.fib (m + 3))) ↔
        (m + 2 ∈ Nat.zeckendorf (wt + Nat.fib (m + 4))) := by
      have hBitEqM : get (X.ofNat (m + 2) (wt + Nat.fib (m + 3))).1 m =
          get (X.ofNat (m + 2) (wt + Nat.fib (m + 4))).1 m := by
        simp only [get, hm_lt, dite_true]; exact congr_arg (fun x => x.1 ⟨m, hm_lt⟩) heq
      rw [← X.get_ofNat_eq_true_iff hm_lt, ← X.get_ofNat_eq_true_iff hm_lt]
      exact ⟨fun h => by rw [← hBitEqM]; exact h, fun h => by rw [hBitEqM]; exact h⟩
    -- (m+2) ∈ zeck(wt) since gf(wt) = m+2
    have hGF_wt : Nat.greatestFib wt = m + 2 :=
      Nat.le_antisymm (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hwt'))
        (Nat.le_greatestFib.mpr hSmall)
    have hFib2_pos : 0 < Nat.fib (m + 2) := Nat.fib_pos.mpr (by omega)
    have hM2_in_wt : (m + 2) ∈ Nat.zeckendorf wt := by
      rw [Nat.zeckendorf_of_pos (by omega), hGF_wt]; exact List.mem_cons_self ..
    have hM2_in_n2 : (m + 2) ∈ Nat.zeckendorf (wt + Nat.fib (m + 4)) := by
      rw [hN2_zeck]; exact List.mem_cons.mpr (Or.inr hM2_in_wt)
    -- (m+2) ∉ zeck(n₁): gf(n₁)=m+4, tail=zeck(wt-fib(m+2)), indices < fib(m+1) so ≤ m
    have hN1_lo : Nat.fib (m + 4) ≤ wt + Nat.fib (m + 3) := by omega
    have hN1_up : wt + Nat.fib (m + 3) < Nat.fib (m + 5) := by omega
    have hN1_gf : Nat.greatestFib (wt + Nat.fib (m + 3)) = m + 4 :=
      Nat.le_antisymm (Nat.lt_succ_iff.mp (Nat.greatestFib_lt.mpr hN1_up))
        (Nat.le_greatestFib.mpr hN1_lo)
    have hN1_sub : wt + Nat.fib (m + 3) - Nat.fib (m + 4) = wt - Nat.fib (m + 2) := by omega
    have hM2_not_n1 : (m + 2) ∉ Nat.zeckendorf (wt + Nat.fib (m + 3)) := by
      rw [Nat.zeckendorf_of_pos (by omega), hN1_gf, hN1_sub]
      simp only [List.mem_cons]
      intro h; rcases h with h | h; · omega
      · have hTailBound : wt - Nat.fib (m + 2) < Nat.fib (m + 1) := by
          have : Nat.fib (m + 3) = Nat.fib (m + 1) + Nat.fib (m + 2) := Nat.fib_add_two
          omega
        have hFibMono : Nat.fib (m + 1) ≤ Nat.fib (m + 2) := Nat.fib_mono (by omega)
        exact absurd (fib_le_of_mem_zeckendorf h) (by omega)
    exact hM2_not_n1 (hBitM.mpr hM2_in_n2)

theorem maxFiberMultiplicity_le_add (m : Nat) :
    maxFiberMultiplicity (m + 2) ≤ maxFiberMultiplicity (m + 1) + maxFiberMultiplicity m := by
  apply Finset.sup'_le; intro x _; classical
  let y := X.restrict x; let z := X.restrict y
  -- False-ending bound
  have hFalse : ((fiber x).filter (fun w => w ⟨m+1, by omega⟩ = false)).card ≤
      maxFiberMultiplicity (m + 1) := by
    have h1 : ((fiber x).filter (fun w => w ⟨m+1, by omega⟩ = false)).card ≤ (fiber y).card :=
      Finset.card_le_card_of_injOn truncate
        (fun w hw => by
          rw [Finset.mem_coe, Finset.mem_filter] at hw; rw [Finset.mem_coe, mem_fiber]
          have hFold := mem_fiber.mp hw.1; have hLast := hw.2
          rw [← snoc_truncate_last w] at hFold; rw [hLast] at hFold
          rw [← restrict_Fold_snoc_false (truncate w)]; exact congrArg X.restrict hFold)
        (fun w₁ hw₁ w₂ hw₂ hEq => by
          rw [Finset.mem_coe, Finset.mem_filter] at hw₁ hw₂
          rw [← snoc_truncate_last w₁, ← snoc_truncate_last w₂, hEq, hw₁.2, hw₂.2])
    exact h1.trans (fiberMultiplicity_le_max _)
  -- True-ending bound
  have hTrue : ((fiber x).filter (fun w => w ⟨m+1, by omega⟩ = true)).card ≤
      maxFiberMultiplicity m := by
    have h1 : ((fiber x).filter (fun w => w ⟨m+1, by omega⟩ = true)).card ≤ (fiber z).card :=
      Finset.card_le_card_of_injOn (fun w => truncate (truncate w))
        (fun w hw => by
          rw [Finset.mem_coe, Finset.mem_filter] at hw; rw [Finset.mem_coe, mem_fiber]
          have hFold := mem_fiber.mp hw.1; have hLast := hw.2
          have hWT := weight_lt_paperFib (truncate (truncate w))
          show Fold (truncate (truncate w)) = X.restrict (X.restrict x)
          rw [← hFold]; simp only [Fold, restrict_ofNat]
          -- Goal: X.ofNat m (weight(tt w)) = X.ofNat m (weight w)
          rw [weight_expand w hLast]
          cases hMid : w ⟨m, by omega⟩
          · simp only [Bool.false_eq_true, ↓reduceIte, Nat.add_zero]
            exact (ofNat_add_paperFib (m + 2) (le_refl _) _ hWT).symm
          · simp only [↓reduceIte]
            rw [show weight (truncate (truncate w)) + paperFib (m + 1) + paperFib (m + 2) =
                weight (truncate (truncate w)) + (paperFib (m + 2) + paperFib (m + 1)) from by ring,
                paperFib_add (m + 1)]
            exact (ofNat_add_paperFib (m + 3) (by omega) _
              (Nat.lt_of_lt_of_le hWT (paperFib_le_succ (m + 2)))).symm)
        (fun w₁ hw₁ w₂ hw₂ hEq => by
          rw [Finset.mem_coe, Finset.mem_filter] at hw₁ hw₂
          have hL1 := hw₁.2; have hL2 := hw₂.2
          have hWT := weight_lt_paperFib (truncate (truncate w₁))
          -- Show w₁[m] = w₂[m] via ofNat_ne_of_shift
          have hMidEq : w₁ ⟨m, by omega⟩ = w₂ ⟨m, by omega⟩ := by
            by_contra hne
            have hFE : X.ofNat (m + 2) (weight w₁) = X.ofNat (m + 2) (weight w₂) := by
              change Fold w₁ = Fold w₂; exact (mem_fiber.mp hw₁.1).trans (mem_fiber.mp hw₂.1).symm
            have hWEq : weight (truncate (truncate w₁)) = weight (truncate (truncate w₂)) :=
              congr_arg weight hEq
            -- Expand weights
            rw [weight_expand w₁ hL1, weight_expand w₂ hL2, hWEq] at hFE
            cases h₁ : w₁ ⟨m, by omega⟩ <;> cases h₂ : w₂ ⟨m, by omega⟩
            -- hFE from the outer scope was rewritten by weight_expand and hWEq.
            -- In the off-diagonal cases (false.true and true.false), hFE gives
            -- X.ofNat(m+2, wt + F) = X.ofNat(m+2, wt + F₁ + F) (or reverse).
            -- ofNat_ne_of_shift says these differ. Use absurd.
            -- In the diagonal cases, hne says ¬(false = false) or ¬(true = true). Both are False.
            <;> simp only [h₁, h₂, Bool.false_eq_true, ↓reduceIte, Nat.add_zero] at hFE
            · exact absurd (by rw [h₁, h₂]) hne  -- false.false
            · -- false.true: hFE : ofNat(m+2, wt + pF(m+2)) = ofNat(m+2, wt + pF(m+1) + pF(m+2))
              exfalso
              apply ofNat_ne_of_shift (weight (truncate (truncate w₂))) (hWEq ▸ hWT)
              have hRec : paperFib (m + 2) + paperFib (m + 1) = paperFib (m + 3) :=
                paperFib_add (m + 1)
              exact hFE.trans (congr_arg (X.ofNat (m + 2)) (by omega))
            · -- true.false: hFE : ofNat(m+2, wt + pF(m+1) + pF(m+2)) = ofNat(m+2, wt + pF(m+2))
              exfalso
              apply ofNat_ne_of_shift (weight (truncate (truncate w₂))) (hWEq ▸ hWT)
              have hRec : paperFib (m + 2) + paperFib (m + 1) = paperFib (m + 3) :=
                paperFib_add (m + 1)
              exact hFE.symm.trans (congr_arg (X.ofNat (m + 2)) (by omega))
            · exact absurd (by rw [h₁, h₂]) hne  -- true.true
          -- Reconstruct: wᵢ = snoc (truncate wᵢ) (wᵢ[m+1]) = snoc (truncate wᵢ) true
          -- truncate wᵢ = snoc (truncate (truncate wᵢ)) ((truncate wᵢ)[m]) = snoc (...) (wᵢ[m])
          -- From hEq and hMidEq: truncate w₁ = truncate w₂
          have hTrEq : truncate w₁ = truncate w₂ := by
            rw [← snoc_truncate_last (truncate w₁), ← snoc_truncate_last (truncate w₂)]
            exact congr_arg₂ snoc hEq hMidEq
          rw [← snoc_truncate_last w₁, ← snoc_truncate_last w₂, hL1, hL2, hTrEq])
    exact h1.trans (fiberMultiplicity_le_max _)
  -- Combine
  calc fiberMultiplicity x = (fiber x).card := rfl
    _ = ((fiber x).filter (fun w => w ⟨m+1, by omega⟩ = false)).card +
        ((fiber x).filter (fun w => w ⟨m+1, by omega⟩ = true)).card := by
      rw [← Finset.card_union_of_disjoint (Finset.disjoint_filter.mpr fun w _ h1 h2 => by
        rw [h1] at h2; exact Bool.false_ne_true h2)]
      congr 1; ext w; simp only [Finset.mem_union, Finset.mem_filter]
      exact ⟨fun h => by cases w ⟨m+1, by omega⟩ <;> simp_all, fun h => h.elim And.left And.left⟩
    _ ≤ _ := Nat.add_le_add hFalse hTrue

end ClosedForm
end X
end Omega
