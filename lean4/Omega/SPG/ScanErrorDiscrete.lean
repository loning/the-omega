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

end

end Omega.SPG
