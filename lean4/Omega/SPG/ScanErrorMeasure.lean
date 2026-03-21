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
