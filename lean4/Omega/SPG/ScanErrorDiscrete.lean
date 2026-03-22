import Mathlib.Probability.ProbabilityMassFunction.Basic
import Omega.Folding.Defect

open scoped BigOperators

namespace Omega.SPG

noncomputable section

/-- Finite mass of a set under a discrete probability law. -/
def setMass {α : Type*} [Fintype α] (μ : PMF α) (s : Set α) : ENNReal :=
  ∑ x, s.indicator μ x

@[simp] theorem setMass_empty {α : Type*} [Fintype α] (μ : PMF α) :
    setMass μ ∅ = 0 := by
  simp [setMass]

theorem setMass_mono {α : Type*} [Fintype α] (μ : PMF α) {s t : Set α} (hst : s ⊆ t) :
    setMass μ s ≤ setMass μ t := by
  simp [setMass]
  refine Finset.sum_le_sum ?_
  intro x _hx
  by_cases hs : x ∈ s
  · have ht : x ∈ t := hst hs
    simp [Set.indicator, hs, ht]
  · by_cases ht : x ∈ t
    · simp [Set.indicator, hs, ht]
    · simp [Set.indicator, hs, ht]

/-- The observation fiber over `b`. -/
def observableCell {α β : Type*} (obs : α → β) (b : β) : Set α :=
  {x | obs x = b}

/-- Events decided by the observable `obs`. -/
def observableEvent {α β : Type*} (obs : α → β) (A : Set β) : Set α :=
  {x | obs x ∈ A}

/-- Event mass inside a single observation cell. -/
def cellEventMass {α β : Type*} [Fintype α] (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    ENNReal :=
  setMass μ (P ∩ observableCell obs b)

/-- Complement mass inside a single observation cell. -/
def cellComplMass {α β : Type*} [Fintype α] (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    ENNReal :=
  setMass μ (observableCell obs b \ P)

/-- Total mass of a single observation cell. -/
def cellMass {α β : Type*} [Fintype α] (μ : PMF α) (obs : α → β) (b : β) : ENNReal :=
  setMass μ (observableCell obs b)

/-- The discrete scan-error profile induced by the observable `obs`. -/
def scanError {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) : ENNReal :=
  ∑ b, min (cellEventMass μ obs P b) (cellComplMass μ obs P b)

theorem cellEventMass_le_cellMass {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    cellEventMass μ obs P b ≤ cellMass μ obs b :=
  setMass_mono μ (by intro x hx; exact hx.2)

theorem cellComplMass_le_cellMass {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    cellComplMass μ obs P b ≤ cellMass μ obs b :=
  setMass_mono μ (by intro x hx; exact hx.1)

theorem observableEvent_inter_cell {α β : Type*} (obs : α → β) (A : Set β) (b : β)
    (hb : b ∈ A) :
    observableEvent obs A ∩ observableCell obs b = observableCell obs b := by
  ext x
  constructor
  · intro hx
    exact hx.2
  · intro hx
    have hEq : obs x = b := by
      simpa [observableCell] using hx
    refine ⟨?_, hx⟩
    change obs x ∈ A
    exact hEq ▸ hb

theorem observableEvent_inter_cell_of_not_mem {α β : Type*} (obs : α → β) (A : Set β) (b : β)
    (hb : b ∉ A) :
    observableEvent obs A ∩ observableCell obs b = ∅ := by
  ext x
  constructor
  · intro hx
    have hEq : obs x = b := hx.2
    have hMem : obs x ∈ A := hx.1
    exact False.elim (hb (by simpa [hEq] using hMem))
  · intro hx
    cases hx

theorem cell_diff_observableEvent {α β : Type*} (obs : α → β) (A : Set β) (b : β)
    (hb : b ∈ A) :
    observableCell obs b \ observableEvent obs A = ∅ := by
  ext x
  constructor
  · intro hx
    have hEq : obs x = b := hx.1
    have hMem : x ∈ observableEvent obs A := by
      simpa [observableEvent, hEq] using hb
    exact False.elim (hx.2 hMem)
  · intro hx
    cases hx

theorem cell_diff_observableEvent_of_not_mem {α β : Type*} (obs : α → β) (A : Set β) (b : β)
    (hb : b ∉ A) :
    observableCell obs b \ observableEvent obs A = observableCell obs b := by
  ext x
  constructor
  · intro hx
    exact hx.1
  · intro hx
    refine ⟨hx, ?_⟩
    intro hxA
    have hMem : obs x ∈ A := by
      simpa [observableEvent] using hxA
    have hEq : obs x = b := by
      simpa [observableCell] using hx
    have hb' : b ∈ A := by
      exact hEq.symm ▸ hMem
    exact hb hb'

@[simp] theorem cellEventMass_observableEvent_of_mem {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (A : Set β) (b : β) (hb : b ∈ A) :
    cellEventMass μ obs (observableEvent obs A) b = cellMass μ obs b := by
  rw [cellEventMass, cellMass, observableEvent_inter_cell obs A b hb]

@[simp] theorem cellEventMass_observableEvent_of_not_mem {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (A : Set β) (b : β) (hb : b ∉ A) :
    cellEventMass μ obs (observableEvent obs A) b = 0 := by
  rw [cellEventMass, observableEvent_inter_cell_of_not_mem obs A b hb, setMass_empty]

@[simp] theorem cellComplMass_observableEvent_of_mem {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (A : Set β) (b : β) (hb : b ∈ A) :
    cellComplMass μ obs (observableEvent obs A) b = 0 := by
  rw [cellComplMass, cell_diff_observableEvent obs A b hb, setMass_empty]

@[simp] theorem cellComplMass_observableEvent_of_not_mem {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (A : Set β) (b : β) (hb : b ∉ A) :
    cellComplMass μ obs (observableEvent obs A) b = cellMass μ obs b := by
  rw [cellComplMass, cellMass, cell_diff_observableEvent_of_not_mem obs A b hb]

 theorem scanError_observableEvent_eq_zero {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    scanError μ obs (observableEvent obs A) = 0 := by
  classical
  unfold scanError
  refine (Fintype.sum_eq_zero_iff_of_nonneg (f := fun b =>
    min (cellEventMass μ obs (observableEvent obs A) b)
      (cellComplMass μ obs (observableEvent obs A) b)) ?_).2 ?_
  · intro b
    exact bot_le
  · funext b
    by_cases hb : b ∈ A
    · simp [hb]
    · simp [hb]

/-- Observation cells where the event is not pure. -/
def boundaryCells {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) : Finset β :=
  Finset.univ.filter fun b => cellEventMass μ obs P b ≠ 0 ∧ cellComplMass μ obs P b ≠ 0

@[simp] theorem boundaryCells_observableEvent_eq_empty {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    boundaryCells μ obs (observableEvent obs A) = ∅ := by
  classical
  ext b
  by_cases hA : b ∈ A
  · simp [boundaryCells, hA]
  · simp [boundaryCells, hA]

theorem scanError_eq_sum_boundary {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    scanError μ obs P
      = Finset.sum (boundaryCells μ obs P) (fun b =>
          min (cellEventMass μ obs P b) (cellComplMass μ obs P b)) := by
  classical
  unfold scanError boundaryCells
  rw [← Finset.sum_subset (Finset.subset_univ (boundaryCells μ obs P)) (by
    intro b _hb hbNotMem
    simp only [boundaryCells, Finset.mem_filter, Finset.mem_univ, true_and] at hbNotMem
    simp only [not_and_or] at hbNotMem
    rcases hbNotMem with hEvent | hCompl
    · have hEvent' : cellEventMass μ obs P b = 0 := by simpa using hEvent
      simp [hEvent']
    · have hCompl' : cellComplMass μ obs P b = 0 := by simpa using hCompl
      simp [hCompl'])]
  simp [boundaryCells]

theorem scanError_le_boundaryMass {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    scanError μ obs P ≤ Finset.sum (boundaryCells μ obs P) (fun b => cellMass μ obs b) := by
  rw [scanError_eq_sum_boundary]
  refine Finset.sum_le_sum ?_
  intro b hb
  exact (min_le_left _ _).trans (cellEventMass_le_cellMass μ obs P b)

theorem scanError_le_boundaryCard_mul {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) (κ : ENNReal)
    (hκ : ∀ b, cellMass μ obs b ≤ κ) :
    scanError μ obs P ≤ (boundaryCells μ obs P).card * κ := by
  calc
    scanError μ obs P ≤ Finset.sum (boundaryCells μ obs P) (fun b => cellMass μ obs b) :=
      scanError_le_boundaryMass μ obs P
    _ ≤ Finset.sum (boundaryCells μ obs P) (fun _b => κ) := by
      refine Finset.sum_le_sum ?_
      intro b hb
      exact hκ b
    _ = (boundaryCells μ obs P).card * κ := by
      simp

/-- Prefix observation on length-`n` words at resolution `m`. -/
def prefixObservation (h : m ≤ n) : Word n → Word m :=
  restrictWord h

/-- Finite prefix events on `Word n`. -/
def prefixEvent {m n : Nat} (h : m ≤ n) (A : Set (Word m)) : Set (Word n) :=
  observableEvent (prefixObservation h) A

/-- Discrete scan error for the prefix observable. -/
def prefixScanError (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) : ENNReal :=
  scanError μ (prefixObservation h) P

/-- Boundary cells for the prefix observable at resolution `m`. -/
def prefixBoundaryCells (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) : Finset (Word m) :=
  boundaryCells μ (prefixObservation h) P

theorem prefixScanError_eq_sum_boundary (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    prefixScanError μ h P
      = Finset.sum (prefixBoundaryCells μ h P) (fun b =>
          min (cellEventMass μ (prefixObservation h) P b)
            (cellComplMass μ (prefixObservation h) P b)) := by
  exact scanError_eq_sum_boundary μ (prefixObservation h) P

theorem prefixScanError_le_boundaryMass (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    prefixScanError μ h P
      ≤ Finset.sum (prefixBoundaryCells μ h P) (fun b =>
          cellMass μ (prefixObservation h) b) := by
  exact scanError_le_boundaryMass μ (prefixObservation h) P

theorem prefixScanError_le_boundaryCard_mul (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) (κ : ENNReal)
    (hκ : ∀ b, cellMass μ (prefixObservation h) b ≤ κ) :
    prefixScanError μ h P ≤ (prefixBoundaryCells μ h P).card * κ := by
  exact scanError_le_boundaryCard_mul μ (prefixObservation h) P κ hκ

@[simp] theorem prefixBoundaryCells_prefixEvent_eq_empty
    (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    prefixBoundaryCells μ h (prefixEvent h A) = ∅ := by
  exact boundaryCells_observableEvent_eq_empty μ (prefixObservation h) A

theorem prefixScanError_eq_zero_of_prefixEvent (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    prefixScanError μ h (prefixEvent h A) = 0 :=
  scanError_observableEvent_eq_zero μ (prefixObservation h) A

/-- Set-level: complement intersected with a cell equals the cell minus the event. -/
theorem compl_inter_cell_eq_cell_diff {α β : Type*} (obs : α → β) (P : Set α) (b : β) :
    Pᶜ ∩ observableCell obs b = observableCell obs b \ P := by
  ext x; simp [observableCell]; tauto

/-- Set-level: a cell minus the complement equals the event intersected with the cell. -/
theorem cell_diff_compl_eq_inter_cell {α β : Type*} (obs : α → β) (P : Set α) (b : β) :
    observableCell obs b \ Pᶜ = P ∩ observableCell obs b := by
  ext x; simp [observableCell]; tauto

theorem cellEventMass_compl {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    cellEventMass μ obs Pᶜ b = cellComplMass μ obs P b := by
  rw [cellEventMass, cellComplMass, compl_inter_cell_eq_cell_diff]

theorem cellComplMass_compl {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    cellComplMass μ obs Pᶜ b = cellEventMass μ obs P b := by
  rw [cellComplMass, cellEventMass, cell_diff_compl_eq_inter_cell]

@[simp] theorem cellEventMass_empty {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (b : β) :
    cellEventMass μ obs ∅ b = 0 := by
  have : (∅ : Set α) ∩ observableCell obs b = ∅ := by ext x; simp
  rw [cellEventMass, this, setMass_empty]

@[simp] theorem cellComplMass_univ {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (b : β) :
    cellComplMass μ obs Set.univ b = 0 := by
  have : observableCell obs b \ Set.univ = (∅ : Set α) := by ext x; simp
  rw [cellComplMass, this, setMass_empty]

/-- Scan error is invariant under complementation of the event. -/
theorem scanError_compl {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    scanError μ obs Pᶜ = scanError μ obs P := by
  unfold scanError
  refine Finset.sum_congr rfl (fun b _ => ?_)
  rw [cellEventMass_compl, cellComplMass_compl, min_comm]

/-- Discrete observable purity: every observation cell is all-in or all-out. -/
def ObservablePure {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) : Prop :=
  ∀ b, cellEventMass μ obs P b = 0 ∨ cellComplMass μ obs P b = 0

theorem observablePure_observableEvent {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    ObservablePure μ obs (observableEvent obs A) := by
  intro b
  by_cases hb : b ∈ A
  · right; simp [hb]
  · left; simp [hb]

theorem observablePure_iff_boundaryCells_eq_empty {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    ObservablePure μ obs P ↔ boundaryCells μ obs P = ∅ := by
  classical
  constructor
  · intro hPure
    ext b
    constructor
    · intro hb
      simp only [boundaryCells, Finset.mem_filter, Finset.mem_univ, true_and] at hb
      rcases hPure b with hEvent | hCompl
      · exact False.elim (hb.1 hEvent)
      · exact False.elim (hb.2 hCompl)
    · intro hb; cases hb
  · intro hEmpty b
    by_cases hEvent : cellEventMass μ obs P b = 0
    · exact Or.inl hEvent
    · right
      by_contra hCompl
      have hb : b ∈ boundaryCells μ obs P := by
        simp [boundaryCells, hEvent, hCompl]
      rw [hEmpty] at hb
      simp at hb

theorem scanError_eq_zero_of_observablePure {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α)
    (hPure : ObservablePure μ obs P) :
    scanError μ obs P = 0 := by
  classical
  unfold scanError
  refine (Fintype.sum_eq_zero_iff_of_nonneg (f := fun b =>
    min (cellEventMass μ obs P b) (cellComplMass μ obs P b)) ?_).2 ?_
  · intro b; exact bot_le
  · funext b
    rcases hPure b with hEvent | hCompl
    · simp [hEvent]
    · simp [hCompl]

theorem boundaryCells_eq_empty_of_scanError_eq_zero {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α)
    (hZero : scanError μ obs P = 0) :
    boundaryCells μ obs P = ∅ := by
  classical
  by_contra hNotEmpty
  obtain ⟨b, hb⟩ := Finset.nonempty_iff_ne_empty.mpr hNotEmpty
  have hTerms := (Fintype.sum_eq_zero_iff_of_nonneg (f := fun b =>
    min (cellEventMass μ obs P b) (cellComplMass μ obs P b)) (by
      intro b; exact bot_le)).1 (by simpa [scanError] using hZero)
  have hTermZero : min (cellEventMass μ obs P b) (cellComplMass μ obs P b) = 0 := by
    simpa using congrFun hTerms b
  have hb' : cellEventMass μ obs P b ≠ 0 ∧ cellComplMass μ obs P b ≠ 0 := by
    simpa [boundaryCells] using hb
  have hPosEvent : 0 < cellEventMass μ obs P b := pos_iff_ne_zero.mpr hb'.1
  have hPosCompl : 0 < cellComplMass μ obs P b := pos_iff_ne_zero.mpr hb'.2
  have hPosMin : 0 < min (cellEventMass μ obs P b) (cellComplMass μ obs P b) :=
    lt_min hPosEvent hPosCompl
  rw [hTermZero] at hPosMin
  exact lt_irrefl _ hPosMin

theorem observablePure_of_scanError_eq_zero {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α)
    (hZero : scanError μ obs P = 0) :
    ObservablePure μ obs P :=
  (observablePure_iff_boundaryCells_eq_empty μ obs P).2
    (boundaryCells_eq_empty_of_scanError_eq_zero μ obs P hZero)

theorem scanError_eq_zero_iff_observablePure {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    scanError μ obs P = 0 ↔ ObservablePure μ obs P :=
  ⟨observablePure_of_scanError_eq_zero μ obs P,
   scanError_eq_zero_of_observablePure μ obs P⟩

theorem scanError_eq_zero_iff_boundaryCells_eq_empty {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    scanError μ obs P = 0 ↔ boundaryCells μ obs P = ∅ := by
  rw [scanError_eq_zero_iff_observablePure, observablePure_iff_boundaryCells_eq_empty]

@[simp] theorem scanError_empty {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) :
    scanError μ obs ∅ = 0 :=
  scanError_eq_zero_of_observablePure μ obs ∅ (fun b => Or.inl (cellEventMass_empty μ obs b))

@[simp] theorem scanError_univ {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) :
    scanError μ obs Set.univ = 0 :=
  scanError_eq_zero_of_observablePure μ obs Set.univ (fun b => Or.inr (cellComplMass_univ μ obs b))

theorem prefixObservablePure_prefixEvent (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    ObservablePure μ (prefixObservation h) (prefixEvent h A) :=
  observablePure_observableEvent μ (prefixObservation h) A

theorem prefixScanError_eq_zero_of_observablePure (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) (hPure : ObservablePure μ (prefixObservation h) P) :
    prefixScanError μ h P = 0 :=
  scanError_eq_zero_of_observablePure μ (prefixObservation h) P hPure

theorem prefixBoundaryCells_eq_empty_of_scanError_eq_zero (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) (hZero : prefixScanError μ h P = 0) :
    prefixBoundaryCells μ h P = ∅ :=
  boundaryCells_eq_empty_of_scanError_eq_zero μ (prefixObservation h) P hZero

theorem prefixObservablePure_of_scanError_eq_zero (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) (hZero : prefixScanError μ h P = 0) :
    ObservablePure μ (prefixObservation h) P :=
  observablePure_of_scanError_eq_zero μ (prefixObservation h) P hZero

theorem prefixScanError_eq_zero_iff_observablePure (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) :
    prefixScanError μ h P = 0 ↔ ObservablePure μ (prefixObservation h) P :=
  scanError_eq_zero_iff_observablePure μ (prefixObservation h) P

theorem prefixScanError_eq_zero_iff_boundaryCells_eq_empty (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) :
    prefixScanError μ h P = 0 ↔ prefixBoundaryCells μ h P = ∅ :=
  scanError_eq_zero_iff_boundaryCells_eq_empty μ (prefixObservation h) P

theorem prefixScanError_compl (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    prefixScanError μ h Pᶜ = prefixScanError μ h P :=
  scanError_compl μ (prefixObservation h) P

@[simp] theorem prefixScanError_empty (μ : PMF (Word n)) (h : m ≤ n) :
    prefixScanError μ h ∅ = 0 :=
  scanError_empty μ (prefixObservation h)

@[simp] theorem prefixScanError_univ (μ : PMF (Word n)) (h : m ≤ n) :
    prefixScanError μ h Set.univ = 0 :=
  scanError_univ μ (prefixObservation h)

/-- Cell event mass under a refined observation decomposes as a fiberwise sum. -/
theorem cellEventMass_refines_sum {α β γ : Type*} [Fintype α] [Fintype γ] [DecidableEq β]
    (μ : PMF α) (obs₁ : α → β) (obs₂ : α → γ) (f : γ → β)
    (hRef : ∀ a, obs₁ a = f (obs₂ a)) (P : Set α) (b : β) :
    (Finset.univ.filter (fun c => f c = b)).sum (fun c => cellEventMass μ obs₂ P c)
      = cellEventMass μ obs₁ P b := by
  classical
  simp only [cellEventMass, setMass, Set.indicator_apply, Set.mem_inter_iff,
    observableCell, Set.mem_setOf_eq]
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl (fun x _ => ?_)
  by_cases hxP : x ∈ P
  · simp only [hxP, true_and, Finset.sum_ite_eq, Finset.mem_filter, Finset.mem_univ,
      true_and, (hRef x).symm]
  · simp only [hxP, false_and, ite_false, Finset.sum_const_zero]

/-- Cell complement mass under a refined observation decomposes as a fiberwise sum. -/
theorem cellComplMass_refines_sum {α β γ : Type*} [Fintype α] [Fintype γ] [DecidableEq β]
    (μ : PMF α) (obs₁ : α → β) (obs₂ : α → γ) (f : γ → β)
    (hRef : ∀ a, obs₁ a = f (obs₂ a)) (P : Set α) (b : β) :
    (Finset.univ.filter (fun c => f c = b)).sum (fun c => cellComplMass μ obs₂ P c)
      = cellComplMass μ obs₁ P b := by
  simp_rw [← cellEventMass_compl]
  exact cellEventMass_refines_sum μ obs₁ obs₂ f hRef Pᶜ b

/-- Finer observation reduces scan error: if obs₁ = f ∘ obs₂, then SE(obs₂) ≤ SE(obs₁). -/
theorem scanError_antitone_of_refines {α β γ : Type*} [Fintype α] [Fintype β] [Fintype γ]
    (μ : PMF α) (obs₁ : α → β) (obs₂ : α → γ) (f : γ → β)
    (hRef : ∀ x, obs₁ x = f (obs₂ x)) (P : Set α) :
    scanError μ obs₂ P ≤ scanError μ obs₁ P := by
  classical
  let filt := fun b => Finset.univ.filter (fun c => f c = b)
  let g := fun c => min (cellEventMass μ obs₂ P c) (cellComplMass μ obs₂ P c)
  suffices hKey : ∀ b : β,
      (filt b).sum g ≤ min (cellEventMass μ obs₁ P b) (cellComplMass μ obs₁ P b) by
    show (∑ c, g c) ≤ ∑ b, min (cellEventMass μ obs₁ P b) (cellComplMass μ obs₁ P b)
    have hFib : ∑ c, g c = ∑ b, (filt b).sum g := by
      symm
      rw [← Finset.sum_biUnion]
      · refine Finset.sum_congr ?_ (fun _ _ => rfl)
        ext c; simp [filt, Finset.mem_biUnion, Finset.mem_filter]
      · intro b₁ _ b₂ _ hne
        exact Finset.disjoint_filter.2 (fun c _ h₁ h₂ => hne (h₁.symm.trans h₂))
    rw [hFib]
    exact Finset.sum_le_sum (fun b _ => hKey b)
  intro b
  calc (filt b).sum g
      ≤ min ((filt b).sum (fun c => cellEventMass μ obs₂ P c))
          ((filt b).sum (fun c => cellComplMass μ obs₂ P c)) :=
        le_min (Finset.sum_le_sum (fun i _ => min_le_left _ _))
          (Finset.sum_le_sum (fun i _ => min_le_right _ _))
    _ = min (cellEventMass μ obs₁ P b) (cellComplMass μ obs₁ P b) := by
        rw [cellEventMass_refines_sum μ obs₁ obs₂ f hRef P b,
            cellComplMass_refines_sum μ obs₁ obs₂ f hRef P b]

/-- Prefix scan error is monotonically non-increasing in the prefix resolution. -/
theorem prefixScanError_antitone {m₁ m₂ n : Nat}
    (μ : PMF (Word n)) (h₁ : m₁ ≤ n) (h₂ : m₂ ≤ n) (hm : m₁ ≤ m₂)
    (P : Set (Word n)) :
    prefixScanError μ h₂ P ≤ prefixScanError μ h₁ P :=
  scanError_antitone_of_refines μ (prefixObservation h₁) (prefixObservation h₂)
    (restrictWord hm) (fun w => (restrictWord_comp hm h₂ w).symm) P

/-- Cell event masses partition the total event mass. -/
theorem cellEventMass_sum_eq_setMass {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    ∑ b, cellEventMass μ obs P b = setMass μ P := by
  classical
  simp only [cellEventMass, setMass, Set.indicator_apply, Set.mem_inter_iff,
    observableCell, Set.mem_setOf_eq]
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl (fun x _ => ?_)
  by_cases hxP : x ∈ P
  · simp only [hxP, true_and, Finset.sum_ite_eq, Finset.mem_univ, ite_true]
  · simp only [hxP, false_and, ite_false, Finset.sum_const_zero]

/-- Cell complement masses partition the total complement mass. -/
theorem cellComplMass_sum_eq_setMass_compl {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    ∑ b, cellComplMass μ obs P b = setMass μ Pᶜ := by
  simp_rw [← cellEventMass_compl]
  exact cellEventMass_sum_eq_setMass μ obs Pᶜ

/-- Total cell masses partition the total probability mass. -/
theorem cellMass_sum_eq_setMass_univ {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) :
    ∑ b, cellMass μ obs b = setMass μ Set.univ := by
  have : ∀ b, cellMass μ obs b = cellEventMass μ obs Set.univ b := by
    intro b; simp [cellMass, cellEventMass, Set.univ_inter]
  simp_rw [this]
  exact cellEventMass_sum_eq_setMass μ obs Set.univ

/-- Scan error is bounded by the smaller of event mass and complement mass (Bayes optimality). -/
theorem scanError_le_min_setMass {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    scanError μ obs P ≤ min (setMass μ P) (setMass μ Pᶜ) := by
  calc scanError μ obs P
      = ∑ b, min (cellEventMass μ obs P b) (cellComplMass μ obs P b) := rfl
    _ ≤ min (∑ b, cellEventMass μ obs P b) (∑ b, cellComplMass μ obs P b) :=
        le_min (Finset.sum_le_sum (fun b _ => min_le_left _ _))
          (Finset.sum_le_sum (fun b _ => min_le_right _ _))
    _ = min (setMass μ P) (setMass μ Pᶜ) := by
        rw [cellEventMass_sum_eq_setMass, cellComplMass_sum_eq_setMass_compl]

end

end Omega.SPG
