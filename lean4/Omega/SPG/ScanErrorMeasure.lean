import Mathlib.MeasureTheory.Measure.ProbabilityMeasure
import Mathlib.Probability.ProbabilityMassFunction.Basic
import Omega.SPG.ScanErrorDiscrete

open scoped BigOperators

namespace Omega.SPG

noncomputable section

/-- Event mass inside a single observation cell for a general measure. -/
def cellEventMeasure {α β : Type*} [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) (b : β) : ENNReal :=
  μ (P ∩ observableCell obs b)

/-- Complement mass inside a single observation cell for a general measure. -/
def cellComplMeasure {α β : Type*} [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) (b : β) : ENNReal :=
  μ (observableCell obs b \ P)

/-- Total mass of a single observation cell for a general measure. -/
def cellMeasure {α β : Type*} [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (b : β) : ENNReal :=
  μ (observableCell obs b)

/-- Scan error for a finite observable under a general measure. -/
def scanErrorMeasure {α β : Type*} [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) : ENNReal :=
  ∑ b, min (cellEventMeasure μ obs P b) (cellComplMeasure μ obs P b)

@[simp] theorem cellEventMeasure_observableEvent_of_mem {α β : Type*} [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) (b : β) (hb : b ∈ A) :
    cellEventMeasure μ obs (observableEvent obs A) b = cellMeasure μ obs b := by
  rw [cellEventMeasure, cellMeasure, observableEvent_inter_cell obs A b hb]

@[simp] theorem cellEventMeasure_observableEvent_of_not_mem {α β : Type*} [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) (b : β) (hb : b ∉ A) :
    cellEventMeasure μ obs (observableEvent obs A) b = 0 := by
  rw [cellEventMeasure, observableEvent_inter_cell_of_not_mem obs A b hb, MeasureTheory.measure_empty]

@[simp] theorem cellComplMeasure_observableEvent_of_mem {α β : Type*} [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) (b : β) (hb : b ∈ A) :
    cellComplMeasure μ obs (observableEvent obs A) b = 0 := by
  rw [cellComplMeasure, cell_diff_observableEvent obs A b hb, MeasureTheory.measure_empty]

@[simp] theorem cellComplMeasure_observableEvent_of_not_mem {α β : Type*} [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) (b : β) (hb : b ∉ A) :
    cellComplMeasure μ obs (observableEvent obs A) b = cellMeasure μ obs b := by
  rw [cellComplMeasure, cellMeasure, cell_diff_observableEvent_of_not_mem obs A b hb]

theorem scanErrorMeasure_observableEvent_eq_zero {α β : Type*} [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) :
    scanErrorMeasure μ obs (observableEvent obs A) = 0 := by
  classical
  unfold scanErrorMeasure
  refine (Fintype.sum_eq_zero_iff_of_nonneg (f := fun b =>
    min (cellEventMeasure μ obs (observableEvent obs A) b)
      (cellComplMeasure μ obs (observableEvent obs A) b)) ?_).2 ?_
  · intro b
    exact bot_le
  · funext b
    by_cases hb : b ∈ A
    · simp [hb]
    · simp [hb]

/-- Observation cells where the event is not pure under a general measure. -/
def boundaryCellsMeasure {α β : Type*} [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) : Finset β :=
  Finset.univ.filter fun b => cellEventMeasure μ obs P b ≠ 0 ∧ cellComplMeasure μ obs P b ≠ 0

@[simp] theorem boundaryCellsMeasure_observableEvent_eq_empty
    {α β : Type*} [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) :
    boundaryCellsMeasure μ obs (observableEvent obs A) = ∅ := by
  classical
  ext b
  by_cases hA : b ∈ A
  · simp [boundaryCellsMeasure, hA]
  · simp [boundaryCellsMeasure, hA]

theorem scanErrorMeasure_eq_sum_boundary {α β : Type*} [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    scanErrorMeasure μ obs P
      = Finset.sum (boundaryCellsMeasure μ obs P) (fun b =>
          min (cellEventMeasure μ obs P b) (cellComplMeasure μ obs P b)) := by
  classical
  unfold scanErrorMeasure boundaryCellsMeasure
  rw [← Finset.sum_subset (Finset.subset_univ (boundaryCellsMeasure μ obs P)) (by
    intro b _hb hbNotMem
    simp only [boundaryCellsMeasure, Finset.mem_filter, Finset.mem_univ, true_and] at hbNotMem
    simp only [not_and_or] at hbNotMem
    rcases hbNotMem with hEvent | hCompl
    · have hEvent' : cellEventMeasure μ obs P b = 0 := by simpa using hEvent
      simp [hEvent']
    · have hCompl' : cellComplMeasure μ obs P b = 0 := by simpa using hCompl
      simp [hCompl'])]
  simp [boundaryCellsMeasure]

theorem scanErrorMeasure_le_boundaryMass {α β : Type*} [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    scanErrorMeasure μ obs P
      ≤ Finset.sum (boundaryCellsMeasure μ obs P) (fun b => cellMeasure μ obs b) := by
  rw [scanErrorMeasure_eq_sum_boundary]
  refine Finset.sum_le_sum ?_
  intro b _hb
  exact (min_le_left _ _).trans <| by
    unfold cellEventMeasure cellMeasure
    exact MeasureTheory.measure_mono (by intro x hx; exact hx.2)

theorem scanErrorMeasure_le_boundaryCard_mul {α β : Type*} [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) (κ : ENNReal)
    (hκ : ∀ b, cellMeasure μ obs b ≤ κ) :
    scanErrorMeasure μ obs P ≤ (boundaryCellsMeasure μ obs P).card * κ := by
  calc
    scanErrorMeasure μ obs P
        ≤ Finset.sum (boundaryCellsMeasure μ obs P) (fun b => cellMeasure μ obs b) :=
          scanErrorMeasure_le_boundaryMass μ obs P
    _ ≤ Finset.sum (boundaryCellsMeasure μ obs P) (fun _b => κ) := by
      refine Finset.sum_le_sum ?_
      intro b hb
      exact hκ b
    _ = (boundaryCellsMeasure μ obs P).card * κ := by
      simp

/-- Prefix scan error for a general measure on finite words. -/
def prefixScanErrorMeasure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) : ENNReal :=
  scanErrorMeasure μ (prefixObservation h) P

/-- Prefix boundary cells for a general measure on finite words. -/
def prefixBoundaryCellsMeasure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) : Finset (Word m) :=
  boundaryCellsMeasure μ (prefixObservation h) P

theorem prefixScanErrorMeasure_eq_sum_boundary [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    prefixScanErrorMeasure μ h P
      = Finset.sum (prefixBoundaryCellsMeasure μ h P) (fun b =>
          min (cellEventMeasure μ (prefixObservation h) P b)
            (cellComplMeasure μ (prefixObservation h) P b)) := by
  exact scanErrorMeasure_eq_sum_boundary μ (prefixObservation h) P

theorem prefixScanErrorMeasure_le_boundaryMass [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    prefixScanErrorMeasure μ h P
      ≤ Finset.sum (prefixBoundaryCellsMeasure μ h P) (fun b =>
          cellMeasure μ (prefixObservation h) b) := by
  exact scanErrorMeasure_le_boundaryMass μ (prefixObservation h) P

theorem prefixScanErrorMeasure_le_boundaryCard_mul [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) (κ : ENNReal)
    (hκ : ∀ b, cellMeasure μ (prefixObservation h) b ≤ κ) :
    prefixScanErrorMeasure μ h P ≤ (prefixBoundaryCellsMeasure μ h P).card * κ := by
  exact scanErrorMeasure_le_boundaryCard_mul μ (prefixObservation h) P κ hκ

@[simp] theorem prefixBoundaryCellsMeasure_prefixEvent_eq_empty [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    prefixBoundaryCellsMeasure μ h (prefixEvent h A) = ∅ := by
  exact boundaryCellsMeasure_observableEvent_eq_empty μ (prefixObservation h) A

theorem prefixScanErrorMeasure_eq_zero_of_prefixEvent [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    prefixScanErrorMeasure μ h (prefixEvent h A) = 0 :=
  scanErrorMeasure_observableEvent_eq_zero μ (prefixObservation h) A

theorem cellEventMeasure_toMeasure_eq_cellEventMass {α β : Type*} [Fintype α] [MeasurableSpace α]
    [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    cellEventMeasure μ.toMeasure obs P b = cellEventMass μ obs P b := by
  rw [cellEventMeasure, cellEventMass, setMass, PMF.toMeasure_apply_fintype]

theorem cellComplMeasure_toMeasure_eq_cellComplMass {α β : Type*} [Fintype α] [MeasurableSpace α]
    [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    cellComplMeasure μ.toMeasure obs P b = cellComplMass μ obs P b := by
  rw [cellComplMeasure, cellComplMass, setMass, PMF.toMeasure_apply_fintype]

theorem cellMeasure_toMeasure_eq_cellMass {α β : Type*} [Fintype α] [MeasurableSpace α]
    [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (b : β) :
    cellMeasure μ.toMeasure obs b = cellMass μ obs b := by
  rw [cellMeasure, cellMass, setMass, PMF.toMeasure_apply_fintype]

theorem scanErrorMeasure_toMeasure_eq_scanError {α β : Type*} [Fintype α] [Fintype β]
    [MeasurableSpace α] [MeasurableSingletonClass α] (μ : PMF α) (obs : α → β) (P : Set α) :
    scanErrorMeasure μ.toMeasure obs P = scanError μ obs P := by
  simp [scanErrorMeasure, scanError, cellEventMeasure_toMeasure_eq_cellEventMass,
    cellComplMeasure_toMeasure_eq_cellComplMass]

end

end Omega.SPG
