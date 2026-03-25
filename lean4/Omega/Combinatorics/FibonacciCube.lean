import Omega.Combinatorics.PathIndSet
import Omega.Folding.Weight
import Omega.Folding.Fold
import Omega.Folding.MaxFiber

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

end Omega
