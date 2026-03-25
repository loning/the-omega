import Omega.Combinatorics.PathIndSet
import Omega.Folding.Weight
import Omega.Folding.Fold
import Omega.Folding.MaxFiber
import Omega.Folding.MomentRecurrence

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- wordSupport: X_m → independent sets
-- ══════════════════════════════════════════════════════════════

/-- The support of a word: {i : Fin m | w i = true}. -/
def wordSupport (w : Word m) : Finset (Fin m) :=
  Finset.univ.filter (fun i => w i = true)

/-- No11 word's support is path-independent. -/
theorem wordSupport_isPathIndependent {w : Word m} (hw : No11 w) :
    IsPathIndependent m (wordSupport w) := by
  intro i hi j hj hadj
  simp only [wordSupport, Finset.mem_filter, Finset.mem_univ, true_and] at hi hj
  -- i.val + 1 = j.val, w i = true, w j = true → contradicts No11
  have hiLt : i.val < m := i.isLt
  have hjLt : j.val < m := j.isLt
  have hget_i : get w i.val = true := by rw [get]; simp [hiLt, hi]
  have hget_j : get w (i.val + 1) = true := by
    rw [get]; rw [hadj]; simp [hjLt, hj]
  exact hw i.val hget_i hget_j

-- ══════════════════════════════════════════════════════════════
-- indSetToWord: independent sets → Word m
-- ══════════════════════════════════════════════════════════════

/-- Characteristic function of an independent set as a word. -/
def indSetToWord (S : Finset (Fin m)) : Word m :=
  fun i => if i ∈ S then true else false

/-- Independent set's word satisfies No11. -/
theorem indSetToWord_no11 {S : Finset (Fin m)} (hS : IsPathIndependent m S) :
    No11 (indSetToWord S) := by
  intro i hi hi1
  -- Extract i < m from get(indSetToWord S, i) = true
  unfold get indSetToWord at hi hi1
  split at hi
  · rename_i hiLt
    split at hi1
    · rename_i hi1Lt
      -- hi : (if ⟨i,_⟩ ∈ S then true else false) = true
      -- hi1 : (if ⟨i+1,_⟩ ∈ S then true else false) = true
      have h1 : (⟨i, hiLt⟩ : Fin m) ∈ S := by split at hi <;> simp_all
      have h2 : (⟨i + 1, hi1Lt⟩ : Fin m) ∈ S := by split at hi1 <;> simp_all
      exact hS ⟨i, hiLt⟩ h1 ⟨i + 1, hi1Lt⟩ h2 rfl
    · exact absurd hi1 Bool.false_ne_true
  · exact absurd hi Bool.false_ne_true

-- ══════════════════════════════════════════════════════════════
-- Mutual inverses
-- ══════════════════════════════════════════════════════════════

/-- wordSupport ∘ indSetToWord = id. -/
theorem wordSupport_indSetToWord (S : Finset (Fin m)) :
    wordSupport (indSetToWord S) = S := by
  ext i
  simp only [wordSupport, indSetToWord, Finset.mem_filter, Finset.mem_univ, true_and]
  split <;> simp_all

/-- indSetToWord ∘ wordSupport = id. -/
theorem indSetToWord_wordSupport (w : Word m) :
    indSetToWord (wordSupport w) = w := by
  funext i
  simp only [indSetToWord, wordSupport, Finset.mem_filter, Finset.mem_univ, true_and]
  cases w i <;> simp

-- ══════════════════════════════════════════════════════════════
-- Equivalence X_m ≃ PathIndSets
-- ══════════════════════════════════════════════════════════════

/-- The type of path-independent sets on Fin m. -/
def PathIndSets (m : Nat) := { S : Finset (Fin m) // IsPathIndependent m S }

/-- X_m ≃ independent sets on P_m. -/
noncomputable def xEquivPathIndSet (m : Nat) : X m ≃ PathIndSets m where
  toFun x := ⟨wordSupport x.1, wordSupport_isPathIndependent x.2⟩
  invFun S := ⟨indSetToWord S.1, indSetToWord_no11 S.2⟩
  left_inv x := Subtype.ext (indSetToWord_wordSupport x.1)
  right_inv S := Subtype.ext (wordSupport_indSetToWord S.1)



-- ══════════════════════════════════════════════════════════════
-- popcount
-- ══════════════════════════════════════════════════════════════

/-- Number of true bits in a word. -/
def popcount (w : Word m) : Nat := (wordSupport w).card

theorem popcount_eq_count_true (w : Word m) :
    popcount w = (Finset.univ.filter (fun i : Fin m => w i = true)).card := rfl

theorem popcount_allFalse : popcount (fun (_ : Fin m) => false) = 0 := by
  simp [popcount, wordSupport]

theorem popcount_allTrue : popcount (fun (_ : Fin m) => true) = m := by
  simp [popcount, wordSupport]

-- ══════════════════════════════════════════════════════════════
-- popcount complement + statistics
-- ══════════════════════════════════════════════════════════════

/-- popcount(bitwise complement) + popcount = m. -/
theorem popcount_not (w : Word m) :
    popcount (fun i => !w i) + popcount w = m := by
  simp only [popcount, wordSupport]
  have hsplit : (Finset.univ : Finset (Fin m)) =
      Finset.univ.filter (fun i => (!w i) = true) ∪
      Finset.univ.filter (fun i => w i = true) := by
    ext i; simp only [Finset.mem_univ, Finset.mem_union, Finset.mem_filter, true_and]
    cases w i <;> simp
  have hdisj : Disjoint (Finset.univ.filter (fun i : Fin m => (!w i) = true))
      (Finset.univ.filter (fun i : Fin m => w i = true)) := by
    apply Finset.disjoint_filter.mpr; intro i _ h1 h2
    cases hb : w i <;> simp [hb] at h1 h2
  calc (Finset.univ.filter (fun i : Fin m => (!w i) = true)).card +
      (Finset.univ.filter (fun i : Fin m => w i = true)).card
      = (Finset.univ.filter (fun i => (!w i) = true) ∪
        Finset.univ.filter (fun i => w i = true)).card :=
          (Finset.card_union_of_disjoint hdisj).symm
    _ = Finset.univ.card := by rw [← hsplit]
    _ = Fintype.card (Fin m) := by rw [Finset.card_univ]
    _ = m := Fintype.card_fin m

/-- popcount = 0 iff word is all-false. -/
theorem popcount_eq_zero_iff (x : X m) :
    popcount x.1 = 0 ↔ x = ⟨fun _ => false, no11_allFalse⟩ := by
  constructor
  · intro h
    have hempty : wordSupport x.1 = ∅ := Finset.card_eq_zero.mp h
    apply Subtype.ext; funext i
    have : i ∉ wordSupport x.1 := by rw [hempty]; simp
    simp [wordSupport, Finset.mem_filter] at this; exact this
  · intro h; rw [h]; exact popcount_allFalse

/-- popcount(truncate w) ≤ popcount(w). -/
theorem popcount_truncate_le (w : Word (m + 1)) : popcount (truncate w) ≤ popcount w := by
  simp only [popcount, wordSupport]
  -- Inject Fin m → Fin (m+1) via Fin.castSucc
  apply Finset.card_le_card_of_injOn Fin.castSucc
  · intro i hi
    simp only [Finset.mem_coe, Finset.mem_filter, Finset.mem_univ, true_and] at hi ⊢
    simp [truncate] at hi; exact hi
  · intro i _ j _ h; exact Fin.castSucc_injective _ h

/-- Total popcount across X_m. -/
noncomputable def totalPopcount (m : Nat) : Nat := ∑ x : X m, popcount x.1

theorem totalPopcount_zero : totalPopcount 0 = 0 := by
  simp [totalPopcount, popcount, wordSupport]

-- totalPopcount_one deferred (noncomputable + decide incompatible)

-- ══════════════════════════════════════════════════════════════
-- Weight surjectivity
-- ══════════════════════════════════════════════════════════════

/-- Every weight value in [0, F_{m+3}-2] is achieved by some word. -/
theorem weight_surjective (m n : Nat) (hn : n ≤ Nat.fib (m + 3) - 2) :
    ∃ w : Word m, weight w = n := by
  induction m generalizing n with
  | zero =>
    have : n = 0 := by simp [Nat.fib] at hn; omega
    exact ⟨fun i => False.elim (Nat.not_lt_zero _ i.isLt), by simp [weight]; omega⟩
  | succ m ih =>
    by_cases hlt : n ≤ Nat.fib (m + 3) - 2
    · obtain ⟨v, hv⟩ := ih n hlt
      exact ⟨snoc v false, by simp [weight, weight_snoc, hv]⟩
    · push_neg at hlt
      have hfib4 := Nat.fib_add_two (n := m + 2)
      rw [show m + 2 + 2 = m + 4 from rfl, show m + 2 + 1 = m + 3 from rfl] at hfib4
      have hge : Nat.fib (m + 2) ≤ n := by
        have hfib3 := Nat.fib_add_two (n := m + 1)
        rw [show m + 1 + 2 = m + 3 from rfl, show m + 1 + 1 = m + 2 from rfl] at hfib3
        have := fib_succ_pos m
        omega
      have hle : n - Nat.fib (m + 2) ≤ Nat.fib (m + 3) - 2 := by
        have : Nat.fib (m + 1 + 3) = Nat.fib (m + 4) := rfl; omega
      obtain ⟨v, hv⟩ := ih (n - Nat.fib (m + 2)) hle
      exact ⟨snoc v true, by simp [weight, weight_snoc, hv]; omega⟩

/-- ewc(m, n) > 0 for n ≤ F_{m+3}-2. -/
theorem ewc_pos_of_le (m n : Nat) (hn : n ≤ Nat.fib (m + 3) - 2) :
    0 < exactWeightCount m n := by
  obtain ⟨w, hw⟩ := weight_surjective m n hn
  exact Finset.card_pos.mpr ⟨w, Finset.mem_filter.mpr ⟨Finset.mem_univ _, hw⟩⟩

/-- d(x) ≥ 2 when sv(x) + F ≤ max weight. -/
theorem fiberMultiplicity_ge_two_of_sv_le (x : X m)
    (h : stableValue x + Nat.fib (m + 2) ≤ Nat.fib (m + 3) - 2) :
    2 ≤ X.fiberMultiplicity x := by
  rw [fiberMultiplicity_eq_two_ewc]
  have h1 := ewc_stableValue_pos x
  have h2 := ewc_pos_of_le m _ h; omega

-- ══════════════════════════════════════════════════════════════
-- Weight decomposition + fiber wrappers
-- ══════════════════════════════════════════════════════════════

theorem weight_truncate_add (w : Word (m + 1)) :
    weight w = weight (truncate w) +
    if w ⟨m, Nat.lt_succ_self m⟩ = true then Nat.fib (m + 2) else 0 := rfl

theorem weight_pos_iff (w : Word m) :
    0 < weight w ↔ ∃ i : Fin m, w i = true := by
  constructor
  · intro hpos; by_contra h; push_neg at h
    have hall : w = fun _ => false := funext (fun i => by
      have := h i; simp only [ne_eq, Bool.not_eq_true] at this; exact this)
    rw [hall, weight_allFalse] at hpos; omega
  · intro ⟨i, hi⟩
    -- weight ≥ F_{i+2} ≥ 1
    calc 0 < 1 := by omega
      _ ≤ Nat.fib (i.val + 2) := fib_succ_pos (i.val + 1)
      _ ≤ weight w := by
        -- The contribution of bit i is F_{i+2}, which is ≤ weight
        induction m with
        | zero => exact absurd i.isLt (Nat.not_lt_zero _)
        | succ n ih =>
          rw [weight_truncate_add]
          by_cases hlt : i.val < n
          · have : Nat.fib (i.val + 2) ≤ weight (truncate w) :=
              ih (truncate w) ⟨i.val, hlt⟩ (by simp [truncate]; exact hi)
            omega
          · have : i.val = n := Nat.eq_of_lt_succ_of_not_lt i.isLt hlt
            rw [this]; simp [show w ⟨n, Nat.lt_succ_self n⟩ = true from by
              have : i = ⟨n, Nat.lt_succ_self n⟩ := Fin.ext this
              rw [← this]; exact hi]

theorem Fold_of_stable' (x : X m) : Fold x.1 = x := Fold_stable x

theorem fiber_self_mem (x : X m) : x.1 ∈ X.fiber x := X.self_mem_fiber x

-- fiberMultiplicity_eq_one_of_sv_ge deferred (ewc uniqueness proof complex)

-- ══════════════════════════════════════════════════════════════
-- D(m) bounds
-- ══════════════════════════════════════════════════════════════

/-- D(m) ≤ F(m+2). -/
theorem maxFiberMultiplicity_le_fib (m : Nat) :
    X.maxFiberMultiplicity m ≤ Nat.fib (m + 2) := by
  induction m using Nat.strongRecOn with
  | _ m ih =>
    match m with
    | 0 => rw [X.maxFiberMultiplicity_zero]; exact one_le_fib_succ 1
    | 1 => rw [X.maxFiberMultiplicity_one]; exact one_le_fib_succ 2
    | m + 2 =>
      have h1 := ih (m + 1) (by omega)
      have h2 := ih m (by omega)
      have hle := X.maxFiberMultiplicity_le_add m
      have hfib := fib_succ_succ' (m + 2)
      rw [show m + 2 + 2 = m + 4 from rfl, show m + 2 + 1 = m + 3 from rfl] at hfib
      linarith

/-- d(x) ≤ F(m+2) for all x. -/
theorem fiberMultiplicity_le_fib (x : X m) :
    X.fiberMultiplicity x ≤ Nat.fib (m + 2) :=
  (X.fiberMultiplicity_le_max x).trans (maxFiberMultiplicity_le_fib m)

/-- D(m)² ≤ S_2(m). -/
theorem maxFiberMultiplicity_sq_le_momentSum (m : Nat) :
    X.maxFiberMultiplicity m ^ 2 ≤ momentSum 2 m := by
  obtain ⟨x, hx⟩ := X.maxFiberMultiplicity_achieved m
  calc X.maxFiberMultiplicity m ^ 2 = X.fiberMultiplicity x ^ 2 := by rw [hx]
    _ ≤ ∑ y : X m, X.fiberMultiplicity y ^ 2 :=
        Finset.single_le_sum (f := fun y => X.fiberMultiplicity y ^ 2)
          (fun y _ => Nat.zero_le _) (Finset.mem_univ x)
    _ = momentSum 2 m := rfl

end Omega
