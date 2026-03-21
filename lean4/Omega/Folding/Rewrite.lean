import Mathlib.Data.Finsupp.Basic
import Mathlib.Data.Finsupp.Order
import Mathlib.Tactic
import Omega.Folding.InverseLimit

namespace Omega

namespace Rewrite

open Finsupp

/-- Finite-support nonnegative digit configurations for local folding rewrites. -/
abbrev DigitCfg := Nat →₀ Nat

/-- Fibonacci weight carried by the zero-based digit position `k`. -/
def digitWeight (k : Nat) : Nat :=
  fib (k + 2)

/-- Generic weighted sum over a digit configuration. -/
def weighted (w : Nat → Nat) (a : DigitCfg) : Nat :=
  a.sum (fun k n => n * w k)

/-- The arithmetic value preserved by the rewrite rules. -/
def value : DigitCfg → Nat :=
  weighted digitWeight

/-- Total multiplicity `A(a)` in the paper's termination measure. -/
def mass : DigitCfg → Nat :=
  weighted (fun _ => 1)

/-- First moment `B(a) = \sum (k+1)a_k` in zero-based indexing. -/
def moment : DigitCfg → Nat :=
  weighted (fun k => k + 1)

/-- Critical coordinate `C(a) = a_2`, zero-based as index `1`. -/
def critical (a : DigitCfg) : Nat :=
  a 1

noncomputable def decDigit (a : DigitCfg) (k : Nat) : DigitCfg :=
  a.update k (a k - 1)

noncomputable def incDigit (a : DigitCfg) (k : Nat) : DigitCfg :=
  a + Finsupp.single k 1

@[simp] theorem decDigit_apply_same (a : DigitCfg) (k : Nat) :
    decDigit a k k = a k - 1 := by
  classical
  simp [decDigit]

@[simp] theorem decDigit_apply_ne (a : DigitCfg) {k j : Nat} (h : j ≠ k) :
    decDigit a k j = a j := by
  classical
  simp [decDigit, h]

@[simp] theorem incDigit_apply_same (a : DigitCfg) (k : Nat) :
    incDigit a k k = a k + 1 := by
  classical
  simp [incDigit]

@[simp] theorem incDigit_apply_ne (a : DigitCfg) {k j : Nat} (h : j ≠ k) :
    incDigit a k j = a j := by
  classical
  simp [incDigit, h]

theorem weighted_decDigit_add (w : Nat → Nat) (a : DigitCfg) (k : Nat) (hk : 0 < a k) :
    weighted w (decDigit a k) + w k = weighted w a := by
  classical
  unfold weighted decDigit
  let g : Nat → Nat → Nat := fun j n => n * w j
  have h := Finsupp.sum_update_add a k (a k - 1) g
    (fun _ => by simp [g])
    (fun _ x y => by simp [g, Nat.add_mul])
  have hk' : a k = (a k - 1) + 1 := by
    omega
  rw [hk'] at h
  have h' : (update a k (a k - 1)).sum g + w k + ((a k - 1) * w k) =
      a.sum g + ((a k - 1) * w k) := by
    simpa [g, Nat.add_mul, add_assoc, add_left_comm, add_comm] using h
  exact Nat.add_right_cancel h'

theorem weighted_incDigit (w : Nat → Nat) (a : DigitCfg) (k : Nat) :
    weighted w (incDigit a k) = weighted w a + w k := by
  classical
  unfold weighted incDigit
  rw [Finsupp.sum_add_index']
  · simp [add_comm]
  · intro
    simp
  · intro
    simp [Nat.add_mul]

@[simp] theorem value_decDigit_add (a : DigitCfg) (k : Nat) (hk : 0 < a k) :
    value (decDigit a k) + digitWeight k = value a :=
  weighted_decDigit_add digitWeight a k hk

@[simp] theorem value_incDigit (a : DigitCfg) (k : Nat) :
    value (incDigit a k) = value a + digitWeight k :=
  weighted_incDigit digitWeight a k

@[simp] theorem mass_decDigit_add (a : DigitCfg) (k : Nat) (hk : 0 < a k) :
    mass (decDigit a k) + 1 = mass a := by
  simpa [mass, weighted] using (weighted_decDigit_add (fun _ => 1) a k hk)

@[simp] theorem mass_incDigit (a : DigitCfg) (k : Nat) :
    mass (incDigit a k) = mass a + 1 := by
  simpa [mass, weighted] using (weighted_incDigit (fun _ => 1) a k)

@[simp] theorem moment_decDigit_add (a : DigitCfg) (k : Nat) (hk : 0 < a k) :
    moment (decDigit a k) + (k + 1) = moment a := by
  simpa [moment, weighted] using (weighted_decDigit_add (fun j => j + 1) a k hk)

@[simp] theorem moment_incDigit (a : DigitCfg) (k : Nat) :
    moment (incDigit a k) = moment a + (k + 1) := by
  simpa [moment, weighted] using (weighted_incDigit (fun j => j + 1) a k)

@[simp] theorem digitWeight_zero : digitWeight 0 = 1 := by
  simp [digitWeight]

@[simp] theorem digitWeight_one : digitWeight 1 = 2 := by
  simp [digitWeight]

@[simp] theorem digitWeight_two : digitWeight 2 = 3 := by
  norm_num [digitWeight]

theorem digitWeight_adj (k : Nat) :
    digitWeight k + digitWeight (k + 1) = digitWeight (k + 2) := by
  calc
    digitWeight k + digitWeight (k + 1) = fib (k + 2) + fib (k + 3) := by
      simp [digitWeight]
    _ = fib ((k + 2) + 1) + fib (k + 2) := by
      simp [Nat.add_left_comm, Nat.add_comm]
    _ = fib ((k + 2) + 2) := by
      rw [(fib_succ_succ (k + 2)).symm]
    _ = digitWeight (k + 2) := by
      simp [digitWeight]

theorem digitWeight_dedupZero :
    2 * digitWeight 0 = digitWeight 1 := by
  norm_num [digitWeight]

theorem digitWeight_dedupOne :
    2 * digitWeight 1 = digitWeight 0 + digitWeight 2 := by
  norm_num [digitWeight]

theorem digitWeight_dedupSucc (k : Nat) :
    digitWeight k + digitWeight (k + 3) = 2 * digitWeight (k + 2) := by
  rw [two_mul]
  calc
    digitWeight k + digitWeight (k + 3)
        = fib (k + 2) + fib (k + 5) := by
            simp [digitWeight, Nat.add_left_comm, Nat.add_comm]
    _ = fib (k + 2) + (fib (k + 4) + fib (k + 3)) := by
          rw [fib_succ_succ (k + 3)]
    _ = (fib (k + 2) + fib (k + 3)) + fib (k + 4) := by
          ac_rfl
    _ = fib (k + 4) + fib (k + 4) := by
          have hAdj : fib (k + 2) + fib (k + 3) = fib (k + 4) := by
            calc
              fib (k + 2) + fib (k + 3) = fib ((k + 2) + 1) + fib (k + 2) := by
                simp [Nat.add_left_comm, Nat.add_comm]
              _ = fib ((k + 2) + 2) := by
                rw [(fib_succ_succ (k + 2)).symm]
              _ = fib (k + 4) := by
                simp [Nat.add_assoc]
          simpa [add_assoc] using congrArg (fun t => t + fib (k + 4)) hAdj
    _ = digitWeight (k + 2) + digitWeight (k + 2) := by
          simp [digitWeight]

/-- Embed a finite binary word into a digit configuration. -/
noncomputable def iota : {m : Nat} → Word m → DigitCfg
  | 0, _ => 0
  | m + 1, w =>
      let tail := iota (truncate w)
      if Omega.last w then incDigit tail m else tail

@[simp] theorem iota_zero (w : Word 0) : iota w = 0 := rfl

@[simp] theorem iota_snoc (w : Word m) (b : Bool) :
    iota (snoc w b) = if b then incDigit (iota w) m else iota w := by
  simp [iota, truncate_snoc, last_snoc]

@[simp] theorem value_iota : ∀ {m : Nat} (w : Word m), value (iota w) = weight w
  | 0, _w => by
      simp [iota, value, weighted, weight]
  | m + 1, w => by
      by_cases hLast : Omega.last w = true
      · calc
          value (iota w)
              = value (incDigit (iota (truncate w)) m) := by
                  simp [iota, hLast]
          _ = value (iota (truncate w)) + digitWeight m := value_incDigit _ _
          _ = weight (truncate w) + paperFib (m + 1) := by
                  rw [value_iota (truncate w), digitWeight, paperFib]
          _ = weight w := by
                  have hBit : w ⟨m, Nat.lt_succ_self m⟩ = true := by
                    simpa [Omega.last] using hLast
                  simp [weight, hBit]
      · have hLastFalse : Omega.last w = false := by
          cases hBit : Omega.last w <;> simp [hBit] at hLast ⊢
        calc
          value (iota w)
              = value (iota (truncate w)) := by
                  simp [iota, hLastFalse]
          _ = weight (truncate w) := value_iota (truncate w)
          _ = weight w := by
                  have hBit : w ⟨m, Nat.lt_succ_self m⟩ = false := by
                    simpa [Omega.last] using hLastFalse
                  simp [weight, hBit]

/-- Canonical stable prefix read off from a configuration by its Zeckendorf value. -/
def normalPrefix (a : DigitCfg) (m : Nat) : X m :=
  X.ofNat m (value a)

@[simp] theorem normalPrefix_iota_eq_Fold (w : Word m) :
    normalPrefix (iota w) m = Fold w := by
  simp [normalPrefix, Fold, value_iota]

noncomputable def adjTarget (a : DigitCfg) (k : Nat) : DigitCfg :=
  incDigit (decDigit (decDigit a k) (k + 1)) (k + 2)

noncomputable def dedupZeroTarget (a : DigitCfg) : DigitCfg :=
  incDigit (decDigit (decDigit a 0) 0) 1

noncomputable def dedupOneTarget (a : DigitCfg) : DigitCfg :=
  incDigit (incDigit (decDigit (decDigit a 1) 1) 0) 2

noncomputable def dedupSuccTarget (a : DigitCfg) (k : Nat) : DigitCfg :=
  incDigit (incDigit (decDigit (decDigit a (k + 2)) (k + 2)) k) (k + 3)

theorem value_adjTarget (a : DigitCfg) (k : Nat) (hk : 0 < a k) (hk1 : 0 < a (k + 1)) :
    value (adjTarget a k) = value a := by
  have hk1' : 0 < (decDigit a k) (k + 1) := by
    simpa [Nat.succ_ne_self] using hk1
  have h1 := value_decDigit_add a k hk
  have h2 := value_decDigit_add (decDigit a k) (k + 1) hk1'
  have hw := digitWeight_adj k
  calc
    value (adjTarget a k) = value (decDigit (decDigit a k) (k + 1)) + digitWeight (k + 2) := by
      simp [adjTarget]
    _ = value a := by
      omega

theorem value_dedupZeroTarget (a : DigitCfg) (h0 : 1 < a 0) :
    value (dedupZeroTarget a) = value a := by
  have h1 : 0 < (decDigit a 0) 0 := by
    simp [decDigit, h0]
  have hDec1 := value_decDigit_add a 0 (by omega : 0 < a 0)
  have hDec2 := value_decDigit_add (decDigit a 0) 0 h1
  have hw := digitWeight_dedupZero
  calc
    value (dedupZeroTarget a) = value (decDigit (decDigit a 0) 0) + digitWeight 1 := by
      simp [dedupZeroTarget]
    _ = value a := by
      omega

theorem value_dedupOneTarget (a : DigitCfg) (h1 : 1 < a 1) :
    value (dedupOneTarget a) = value a := by
  have h1' : 0 < (decDigit a 1) 1 := by
    simp [decDigit, h1]
  have hDec1 := value_decDigit_add a 1 (by omega : 0 < a 1)
  have hDec2 := value_decDigit_add (decDigit a 1) 1 h1'
  have hw := digitWeight_dedupOne
  calc
    value (dedupOneTarget a)
        = value (decDigit (decDigit a 1) 1) + digitWeight 0 + digitWeight 2 := by
            simp [dedupOneTarget, add_left_comm, add_comm]
    _ = value a := by
      omega

theorem value_dedupSuccTarget (a : DigitCfg) (k : Nat) (hk : 1 < a (k + 2)) :
    value (dedupSuccTarget a k) = value a := by
  have hk' : 0 < (decDigit a (k + 2)) (k + 2) := by
    simp [decDigit, hk]
  have hDec1 := value_decDigit_add a (k + 2) (by omega : 0 < a (k + 2))
  have hDec2 := value_decDigit_add (decDigit a (k + 2)) (k + 2) hk'
  have hw := digitWeight_dedupSucc k
  calc
    value (dedupSuccTarget a k)
        = value (decDigit (decDigit a (k + 2)) (k + 2)) + digitWeight k + digitWeight (k + 3) := by
            simp [dedupSuccTarget, add_left_comm, add_comm]
    _ = value a := by
      omega

theorem mass_adjTarget_add (a : DigitCfg) (k : Nat) (hk : 0 < a k) (hk1 : 0 < a (k + 1)) :
    mass (adjTarget a k) + 1 = mass a := by
  have hk1' : 0 < (decDigit a k) (k + 1) := by
    simpa [Nat.succ_ne_self] using hk1
  have h1 := mass_decDigit_add a k hk
  have h2 := mass_decDigit_add (decDigit a k) (k + 1) hk1'
  have h3 := mass_incDigit (decDigit (decDigit a k) (k + 1)) (k + 2)
  calc
    mass (adjTarget a k) + 1 = mass (decDigit (decDigit a k) (k + 1)) + 2 := by
      simp [adjTarget, h3]
    _ = mass a := by
      omega

theorem mass_dedupZeroTarget_add (a : DigitCfg) (h0 : 1 < a 0) :
    mass (dedupZeroTarget a) + 1 = mass a := by
  have h1 : 0 < (decDigit a 0) 0 := by
    simp [decDigit, h0]
  have hDec1 := mass_decDigit_add a 0 (by omega : 0 < a 0)
  have hDec2 := mass_decDigit_add (decDigit a 0) 0 h1
  have hInc := mass_incDigit (decDigit (decDigit a 0) 0) 1
  calc
    mass (dedupZeroTarget a) + 1 = mass (decDigit (decDigit a 0) 0) + 2 := by
      simp [dedupZeroTarget, hInc]
    _ = mass a := by
      omega

theorem mass_dedupOneTarget (a : DigitCfg) (h1 : 1 < a 1) :
    mass (dedupOneTarget a) = mass a := by
  have h1' : 0 < (decDigit a 1) 1 := by
    simp [decDigit, h1]
  have hDec1 := mass_decDigit_add a 1 (by omega : 0 < a 1)
  have hDec2 := mass_decDigit_add (decDigit a 1) 1 h1'
  have hInc1 := mass_incDigit (decDigit (decDigit a 1) 1) 0
  have hInc2 := mass_incDigit (incDigit (decDigit (decDigit a 1) 1) 0) 2
  calc
    mass (dedupOneTarget a) = mass (decDigit (decDigit a 1) 1) + 2 := by
      simp [dedupOneTarget, hInc1, hInc2]
    _ = mass a := by
      omega

theorem moment_dedupOneTarget (a : DigitCfg) (h1 : 1 < a 1) :
    moment (dedupOneTarget a) = moment a := by
  have h1' : 0 < (decDigit a 1) 1 := by
    simp [decDigit, h1]
  have hDec1 := moment_decDigit_add a 1 (by omega : 0 < a 1)
  have hDec2 := moment_decDigit_add (decDigit a 1) 1 h1'
  have hInc1 := moment_incDigit (decDigit (decDigit a 1) 1) 0
  have hInc2 := moment_incDigit (incDigit (decDigit (decDigit a 1) 1) 0) 2
  calc
    moment (dedupOneTarget a) = moment (decDigit (decDigit a 1) 1) + 4 := by
      simp [dedupOneTarget, hInc1, hInc2]
    _ = moment a := by
      omega

theorem critical_dedupOneTarget_add (a : DigitCfg) (h1 : 1 < a 1) :
    critical (dedupOneTarget a) + 2 = critical a := by
  simp [critical, dedupOneTarget, decDigit, incDigit]
  omega

theorem mass_dedupSuccTarget (a : DigitCfg) (k : Nat) (hk : 1 < a (k + 2)) :
    mass (dedupSuccTarget a k) = mass a := by
  have hk' : 0 < (decDigit a (k + 2)) (k + 2) := by
    simp [decDigit, hk]
  have hDec1 := mass_decDigit_add a (k + 2) (by omega : 0 < a (k + 2))
  have hDec2 := mass_decDigit_add (decDigit a (k + 2)) (k + 2) hk'
  have hInc1 := mass_incDigit (decDigit (decDigit a (k + 2)) (k + 2)) k
  have hInc2 := mass_incDigit (incDigit (decDigit (decDigit a (k + 2)) (k + 2)) k) (k + 3)
  calc
    mass (dedupSuccTarget a k) = mass (decDigit (decDigit a (k + 2)) (k + 2)) + 2 := by
      simp [dedupSuccTarget, hInc1, hInc2]
    _ = mass a := by
      omega

theorem moment_dedupSuccTarget_add (a : DigitCfg) (k : Nat) (hk : 1 < a (k + 2)) :
    moment (dedupSuccTarget a k) + 1 = moment a := by
  have hk' : 0 < (decDigit a (k + 2)) (k + 2) := by
    simp [decDigit, hk]
  have hDec1 := moment_decDigit_add a (k + 2) (by omega : 0 < a (k + 2))
  have hDec2 := moment_decDigit_add (decDigit a (k + 2)) (k + 2) hk'
  have hInc1 := moment_incDigit (decDigit (decDigit a (k + 2)) (k + 2)) k
  have hInc2 := moment_incDigit (incDigit (decDigit (decDigit a (k + 2)) (k + 2)) k) (k + 3)
  calc
    moment (dedupSuccTarget a k) + 1
        = moment (incDigit (decDigit (decDigit a (k + 2)) (k + 2)) k) + (k + 4) + 1 := by
            simp [dedupSuccTarget, hInc2]
    _ = moment (decDigit (decDigit a (k + 2)) (k + 2)) + (k + 1) + (k + 4) + 1 := by
          simp [hInc1]
    _ = moment (decDigit (decDigit a (k + 2)) (k + 2)) + (2 * (k + 3)) := by
          omega
    _ = moment a := by
      omega

/-- One local rewrite step of the folding normalization system. -/
inductive Step : DigitCfg → DigitCfg → Prop
  | adj (a : DigitCfg) (k : Nat) (hk : 0 < a k) (hk1 : 0 < a (k + 1)) :
      Step a (adjTarget a k)
  | dedupZero (a : DigitCfg) (h0 : 1 < a 0) :
      Step a (dedupZeroTarget a)
  | dedupOne (a : DigitCfg) (h1 : 1 < a 1) :
      Step a (dedupOneTarget a)
  | dedupSucc (a : DigitCfg) (k : Nat) (hk : 1 < a (k + 2)) :
      Step a (dedupSuccTarget a k)

theorem step_value {a b : DigitCfg} (h : Step a b) : value b = value a := by
  cases h with
  | adj k hk hk1 =>
      exact value_adjTarget a k hk hk1
  | dedupZero h0 =>
      exact value_dedupZeroTarget a h0
  | dedupOne h1 =>
      exact value_dedupOneTarget a h1
  | dedupSucc k hk =>
      exact value_dedupSuccTarget a k hk

/-- Lexicographic decrease relation used for termination bookkeeping. -/
def MeasureDrop (a b : DigitCfg) : Prop :=
  mass b < mass a ∨
    (mass b = mass a ∧ moment b < moment a) ∨
    (mass b = mass a ∧ moment b = moment a ∧ critical b < critical a)

theorem step_measureDrop {a b : DigitCfg} (h : Step a b) : MeasureDrop a b := by
  cases h with
  | adj k hk hk1 =>
      left
      have hMass := mass_adjTarget_add a k hk hk1
      omega
  | dedupZero h0 =>
      left
      have hMass := mass_dedupZeroTarget_add a h0
      omega
  | dedupOne h1 =>
      right
      right
      have hMass := mass_dedupOneTarget a h1
      have hMoment := moment_dedupOneTarget a h1
      have hCrit := critical_dedupOneTarget_add a h1
      refine ⟨?_, ?_, ?_⟩ <;> omega
  | dedupSucc k hk =>
      right
      left
      have hMass := mass_dedupSuccTarget a k hk
      have hMoment := moment_dedupSuccTarget_add a k hk
      refine ⟨?_, ?_⟩ <;> omega

@[simp] theorem normalPrefix_step {a b : DigitCfg} (h : Step a b) :
    normalPrefix b m = normalPrefix a m := by
  simp [normalPrefix, step_value h]

end Rewrite

end Omega
