import Omega.Folding.InverseLimit

namespace Omega

/-- Restrict a length-`n` word to its first `m` bits. -/
def restrictWord (h : m ≤ n) (w : Word n) : Word m :=
  fun i => w ⟨i.1, Nat.lt_of_lt_of_le i.2 h⟩

@[simp] theorem restrictWord_refl (w : Word m) :
    restrictWord (Nat.le_refl m) w = w := by
  funext i
  rfl

@[simp] theorem restrictWord_succ (w : Word (m + 1)) :
    restrictWord (Nat.le_succ m) w = truncate w := by
  funext i
  rfl

@[simp] theorem get_restrictWord (h : m ≤ n) (w : Word n) {i : Nat} (hi : i < m) :
    get (restrictWord h w) i = get w i := by
  have hin : i < n := Nat.lt_of_lt_of_le hi h
  simp [restrictWord, get, hi, hin]

theorem restrictWord_comp (h₁ : m ≤ n) (h₂ : n ≤ k) (w : Word k) :
    restrictWord h₁ (restrictWord h₂ w) = restrictWord (Nat.le_trans h₁ h₂) w := by
  funext i
  rfl

@[simp] theorem restrictWord_trans_succ (h : m ≤ n) (w : Word (n + 1)) :
    restrictWord (Nat.le_trans h (Nat.le_succ n)) w = restrictWord h (truncate w) := by
  funext i
  rfl

theorem no11_restrictWord (h : m ≤ n) {w : Word n} (hw : No11 w) :
    No11 (restrictWord h w) := by
  intro i hi hi1
  have hiLt : i < m := lt_of_get_eq_true hi
  have hi1Lt : i + 1 < m := lt_of_get_eq_true_succ hi1
  have hwi : get w i = true := by
    rw [← get_restrictWord h w hiLt]
    exact hi
  have hwi1 : get w (i + 1) = true := by
    rw [← get_restrictWord h w hi1Lt]
    exact hi1
  exact hw i hwi hwi1

namespace X

/-- Restrict a stable length-`n` word to its first `m` bits. -/
def restrictLE (h : m ≤ n) (x : X n) : X m :=
  ⟨restrictWord h x.1, no11_restrictWord h x.2⟩

@[simp] theorem restrictLE_val (h : m ≤ n) (x : X n) :
    (restrictLE h x).1 = restrictWord h x.1 := rfl

@[simp] theorem restrictLE_refl (x : X m) :
    restrictLE (Nat.le_refl m) x = x := by
  apply Subtype.ext
  simp [restrictLE, restrictWord_refl]

@[simp] theorem restrictLE_succ (x : X (m + 1)) :
    restrictLE (Nat.le_succ m) x = restrict x := by
  apply Subtype.ext
  simp [restrictLE, restrictWord_succ, restrict]

theorem restrictLE_comp (h₁ : m ≤ n) (h₂ : n ≤ k) (x : X k) :
    restrictLE h₁ (restrictLE h₂ x) = restrictLE (Nat.le_trans h₁ h₂) x := by
  apply Subtype.ext
  simp [restrictLE, restrictWord_comp]

@[simp] theorem restrictLE_trans_succ (h : m ≤ n) (x : X (n + 1)) :
    restrictLE (Nat.le_trans h (Nat.le_succ n)) x = restrictLE h (restrict x) := by
  apply Subtype.ext
  exact restrictWord_trans_succ h x.1

end X

/-- The zero defect word. -/
def zeroWord (m : Nat) : Word m :=
  fun _ => false

/-- Pointwise xor of fixed-length words. -/
def xorWord (a b : Word m) : Word m :=
  fun i => a i ^^ b i

@[simp] theorem xorWord_apply (a b : Word m) (i : Fin m) :
    xorWord a b i = (a i ^^ b i) := rfl

@[simp] theorem xorWord_zero_left (a : Word m) :
    xorWord (zeroWord m) a = a := by
  funext i
  simp [xorWord, zeroWord]

@[simp] theorem xorWord_zero_right (a : Word m) :
    xorWord a (zeroWord m) = a := by
  funext i
  simp [xorWord, zeroWord]

@[simp] theorem xorWord_self (a : Word m) :
    xorWord a a = zeroWord m := by
  funext i
  simp [xorWord, zeroWord]

theorem xorWord_comm (a b : Word m) :
    xorWord a b = xorWord b a := by
  funext i
  simp [xorWord, Bool.xor_comm]

theorem xorWord_assoc (a b c : Word m) :
    xorWord (xorWord a b) c = xorWord a (xorWord b c) := by
  funext i
  simp [xorWord]

theorem restrictWord_xor (h : m ≤ n) (a b : Word n) :
    restrictWord h (xorWord a b) = xorWord (restrictWord h a) (restrictWord h b) := by
  funext i
  rfl

theorem xorWord_cancel_middle (a b c : Word m) :
    xorWord (xorWord a b) (xorWord c b) = xorWord a c := by
  funext i
  cases ha : a i <;> cases hb : b i <;> cases hc : c i <;> simp [xorWord, ha, hb, hc]

theorem xorWord_cancel_right (a b c : Word m) :
    xorWord a (xorWord b (xorWord b c)) = xorWord a c := by
  calc
    xorWord a (xorWord b (xorWord b c))
        = xorWord (xorWord a b) (xorWord b c) := by
            rw [← xorWord_assoc]
    _ = xorWord (xorWord a b) (xorWord c b) := by
          rw [xorWord_comm b c]
    _ = xorWord a c := xorWord_cancel_middle a b c

theorem xorWord_cancel_far (a b c : Word m) :
    xorWord b (xorWord c (xorWord a b)) = xorWord a c := by
  calc
    xorWord b (xorWord c (xorWord a b))
        = xorWord (xorWord b c) (xorWord a b) := by
            rw [← xorWord_assoc]
    _ = xorWord (xorWord c b) (xorWord a b) := by
          rw [xorWord_comm b c]
    _ = xorWord c a := xorWord_cancel_middle c b a
    _ = xorWord a c := xorWord_comm _ _

/-- The one-step local exchange defect `κ_{m+1→m}`. -/
def localDefect (η : Word (m + 1)) : Word m :=
  xorWord (Fold (truncate η)).1 (X.restrict (Fold η)).1

/-- The one-step nonzero defect indicator. -/
def localCurvature (η : Word (m + 1)) : Prop :=
  localDefect η ≠ zeroWord m

/-- The global exchange defect `D_{n→m}`. -/
def globalDefect (h : m ≤ n) (ω : Word n) : Word m :=
  xorWord (Fold (restrictWord h ω)).1 (X.restrictLE h (Fold ω)).1

@[simp] theorem globalDefect_refl (ω : Word m) :
    globalDefect (Nat.le_refl m) ω = zeroWord m := by
  simp [globalDefect, X.restrictLE_refl, xorWord_self]

@[simp] theorem localDefect_eq_globalDefect (η : Word (m + 1)) :
    localDefect η = globalDefect (Nat.le_succ m) η := by
  simp [localDefect, globalDefect, X.restrictLE_succ, restrictWord_succ]

theorem globalDefect_step (h : m ≤ n) (ω : Word (n + 1)) :
    globalDefect (Nat.le_trans h (Nat.le_succ n)) ω
      = xorWord (restrictWord h (localDefect ω)) (globalDefect h (truncate ω)) := by
  simp [localDefect, globalDefect, restrictWord_xor]
  symm
  simpa [xorWord_comm] using
    (xorWord_cancel_middle
      (a := restrictWord h (truncate (Fold ω).1))
      (b := restrictWord h (Fold (truncate ω)).1)
      (c := (Fold (restrictWord h (truncate ω))).1))

/-- Recursive xor-sum of all projected local defects between resolutions `m` and `m+k`. -/
def defectChain (m : Nat) : ∀ k : Nat, Word (m + k) → Word m
  | 0, _ω => zeroWord m
  | k + 1, ω =>
      xorWord
        (restrictWord (Nat.le_add_right m k) (localDefect ω))
        (defectChain m k (truncate ω))

/-- Finite-layer discrete Stokes identity in recursive form. -/
theorem globalDefect_eq_defectChain (m k : Nat) (ω : Word (m + k)) :
    globalDefect (Nat.le_add_right m k) ω = defectChain m k ω := by
  induction k with
  | zero =>
      rw [defectChain]
      exact globalDefect_refl ω
  | succ k ih =>
      calc
        globalDefect (Nat.le_add_right m (k + 1)) ω
            = xorWord
                (restrictWord (Nat.le_add_right m k) (localDefect ω))
                (globalDefect (Nat.le_add_right m k) (truncate ω)) := by
                    simpa [Nat.add_assoc] using
                      (globalDefect_step (m := m) (n := m + k) (h := Nat.le_add_right m k) (ω := ω))
        _ = xorWord
              (restrictWord (Nat.le_add_right m k) (localDefect ω))
              (defectChain m k (truncate ω)) := by
                rw [ih]
        _ = defectChain m (k + 1) ω := by
              rfl

end Omega
