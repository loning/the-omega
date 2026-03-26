import Omega.Folding.MomentSum
import Omega.Folding.Weight
import Omega.Core.Fib
import Mathlib.Logic.Function.Basic

namespace Omega

-- ══════════════════════════════════════════════════════════════
-- Phase 148: weight total sum
-- ══════════════════════════════════════════════════════════════

/-- For a fixed bit i : Fin m, |{w : Word m | w i = true}| = 2^{m-1}. -/
theorem card_true_at_bit (m : Nat) (hm : 1 ≤ m) (i : Fin m) :
    (Finset.univ.filter (fun w : Word m => w i = true)).card = 2 ^ (m - 1) := by
  -- Define involution: negate bit i
  set neg_i := fun (w : Word m) => Function.update w i (!w i) with neg_i_def
  -- neg_i is an involution
  have hinv : ∀ w : Word m, neg_i (neg_i w) = w := by
    intro w; ext j; simp only [neg_i_def]
    by_cases hj : j = i
    · subst hj; simp [Function.update_self, Bool.not_not]
    · simp [Function.update_of_ne hj]
  -- neg_i swaps true-set and false-set
  have hswap : ∀ w : Word m,
      w i = true ↔ neg_i w i = false := by
    intro w; simp [neg_i_def, Function.update_self]
  -- So |true-set| = |false-set|
  have hsize : (Finset.univ.filter (fun w : Word m => w i = true)).card =
      (Finset.univ.filter (fun w : Word m => w i = false)).card := by
    apply Finset.card_bij (fun w _ => neg_i w)
    · intro w hw; simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hw ⊢
      exact (hswap w).mp hw
    · intro w₁ _ w₂ _ h
      have := congr_arg neg_i h
      rwa [hinv, hinv] at this
    · intro w hw
      simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hw
      exact ⟨neg_i w, by simp [Finset.mem_filter, (hswap (neg_i w)).mpr (by rw [hinv]; exact hw)],
        hinv w⟩
  -- |true-set| + |false-set| = 2^m
  have htotal : (Finset.univ.filter (fun w : Word m => w i = true)).card +
      (Finset.univ.filter (fun w : Word m => w i = false)).card = 2 ^ m := by
    rw [← Finset.card_union_of_disjoint (by
      rw [Finset.disjoint_left]; intro w hw1 hw2
      simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hw1 hw2
      exact absurd (hw1.symm.trans hw2) (by decide))]
    have : Finset.univ.filter (fun w : Word m => w i = true) ∪
        Finset.univ.filter (fun w : Word m => w i = false) = Finset.univ := by
      ext w; simp only [Finset.mem_union, Finset.mem_filter, Finset.mem_univ, true_and]
      exact ⟨fun _ => trivial, fun _ => by cases w i <;> simp⟩
    rw [this, Finset.card_univ, Fintype.card_fun, Fintype.card_bool, Fintype.card_fin]
  have hpow : 2 ^ m = 2 * 2 ^ (m - 1) := by
    obtain ⟨k, rfl⟩ := Nat.exists_eq_succ_of_ne_zero (by omega : m ≠ 0)
    simp [pow_succ, mul_comm]
  linarith

/-- The total weight sum: Σ_w weight(w) = 2^{m-1} · (F_{m+3} - 2) for m ≥ 1. -/
theorem weight_total_sum (m : Nat) (hm : 1 ≤ m) :
    ∑ w : Word m, weight w = 2 ^ (m - 1) * (Nat.fib (m + 3) - 2) := by
  simp_rw [weight_eq_fib_ite_sum]
  rw [Finset.sum_comm]
  simp_rw [show ∀ i : Fin m, (fun w : Word m => if w i then Nat.fib (i.val + 2) else 0) =
      (fun w => Nat.fib (i.val + 2) * if w i then 1 else 0) from
      fun i => by ext w; split_ifs <;> simp]
  simp_rw [← Finset.mul_sum]
  have hcount : ∀ i : Fin m,
      ∑ w : Word m, (if w i then (1 : Nat) else 0) = 2 ^ (m - 1) := by
    intro i
    change Finset.univ.sum _ = _
    rw [show (fun w : Word m => if w i then (1 : Nat) else 0) =
        (fun w => if w i = true then 1 else 0) from by ext w; simp]
    rw [Finset.sum_boole]
    exact_mod_cast card_true_at_bit m hm i
  simp_rw [hcount, ← Finset.sum_mul]
  rw [show ∑ i : Fin m, Nat.fib (i.val + 2) =
      ∑ i ∈ Finset.range m, Nat.fib (i + 2) from
    Fin.sum_univ_eq_sum_range (n := m) (fun i => Nat.fib (i + 2))]
  rw [fib_partial_sum_from_two, Nat.mul_comm]

end Omega
