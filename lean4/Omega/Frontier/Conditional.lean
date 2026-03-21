import Omega.Frontier.Certificates
import Omega.Graph.Sofic
import Omega.SPG.ScanErrorMeasure

namespace Omega.Frontier

noncomputable section

/-- The realization map from finite witnesses to their projected defect patterns. -/
def defectRealizationMap (m : Nat) : (Σ k : Nat, Word (m + k)) → Word m
  | ⟨k, ω⟩ => globalDefect (Nat.le_add_right m k) ω

theorem fullGeneration_surjective (m : Nat) (h : FullGeneration m) :
    Function.Surjective (defectRealizationMap m) := by
  intro d
  rcases h d with ⟨k, ω, hω⟩
  exact ⟨⟨k, ω⟩, hω⟩

theorem uniformGap_bounds (h : UniformGap) :
    0 < h.η ∧ h.η < 1 :=
  ⟨h.η_pos, h.η_lt_one⟩

theorem defectBudget_has_bound (m k : Nat) (h : DefectBudget m) :
    ∃ C : Nat, C ≤ m + k :=
  h k

theorem globalFullGeneration_specializes (h : GlobalFullGeneration) (m : Nat) :
    FullGeneration m :=
  h m

theorem globalDefectBudget_specializes (h : GlobalDefectBudget) (m : Nat) :
    DefectBudget m :=
  h m

/-- A canonical certified realization supplied by the full-generation hypothesis. -/
noncomputable def generatedDefectCertificate (m : Nat) (h : FullGeneration m) (d : Word m) :
    DefectCertificate :=
  let k := Classical.choose (h d)
  let hk := Classical.choose_spec (h d)
  let ω := Classical.choose hk
  { m := m, k := k, input := ω, claimed := d }

@[simp] theorem generatedDefectCertificate_claimed (m : Nat) (h : FullGeneration m) (d : Word m) :
    (generatedDefectCertificate m h d).claimed = d := rfl

theorem generatedDefectCertificate_valid (m : Nat) (h : FullGeneration m) (d : Word m) :
    (generatedDefectCertificate m h d).Valid := by
  dsimp [generatedDefectCertificate, DefectCertificate.Valid]
  let k := Classical.choose (h d)
  let hk := Classical.choose_spec (h d)
  let ω := Classical.choose hk
  let hω := Classical.choose_spec hk
  simpa [k, hk, ω] using hω

theorem fullGeneration_certifies (m : Nat) (h : FullGeneration m) (d : Word m) :
    (generatedDefectCertificate m h d).Valid :=
  generatedDefectCertificate_valid m h d

/-- The finite folding map is idempotent on arbitrary raw words. -/
theorem fold_idempotent (w : Word m) :
    Fold (Fold w).1 = Fold w :=
  Omega.Fold_idempotent w

/-- Every stable target has a nonempty finite fiber under `Fold`. -/
theorem fold_fiber_nonempty (x : X m) :
    (X.fiber x).Nonempty :=
  X.fiber_nonempty x

/-- The finite fiber over a stable target admits canonical rank/unrank coordinates. -/
theorem fold_fiber_rank_unrank (x : X m) (i : Fin (X.fiber x).card) :
    X.rank x (X.unrank x i) = i :=
  X.rank_unrank x i

/-- Unranking a fiber index returns a raw word folding back to the target stable word. -/
theorem fold_fiber_unrank_sound (x : X m) (i : Fin (X.fiber x).card) :
    Fold (X.unrankWord x i) = x :=
  X.Fold_unrankWord x i

/-- Paper-facing order independence for finite folding windows. -/
theorem fold_orderIndependent {m : Nat} (w : Word m) {b : Rewrite.DigitCfg}
    (hab : Relation.ReflTransGen Rewrite.Step (Rewrite.iota w) b)
    (hIrr : Rewrite.Irreducible b) (hSup : Rewrite.SupportedBelow b m) :
    b = Rewrite.iota (Fold w).1 :=
  Rewrite.irreducible_terminal_eq_fold hab hIrr hSup

/-- Any two irreducible terminals reachable from the same configuration must agree. -/
theorem rewrite_terminal_unique {a b c : Rewrite.DigitCfg}
    (hab : Relation.ReflTransGen Rewrite.Step a b)
    (hac : Relation.ReflTransGen Rewrite.Step a c)
    (hIrrB : Rewrite.Irreducible b) (hIrrC : Rewrite.Irreducible c) :
    b = c :=
  Rewrite.irreducible_terminal_unique_unbounded hab hac hIrrB hIrrC

/-- The rewrite relation is strongly terminating. -/
theorem rewrite_stronglyTerminating :
    WellFounded (flip Rewrite.Step) :=
  Rewrite.step_stronglyTerminating

/-- The rewrite relation is globally confluent. -/
theorem rewrite_confluent {a b c : Rewrite.DigitCfg}
    (hab : Relation.ReflTransGen Rewrite.Step a b)
    (hac : Relation.ReflTransGen Rewrite.Step a c) :
    Relation.Join (Relation.ReflTransGen Rewrite.Step) b c :=
  Rewrite.step_confluent hab hac

/-- The rewrite relation is locally confluent. -/
theorem rewrite_locallyConfluent {a b c : Rewrite.DigitCfg}
    (hab : Rewrite.Step a b) (hac : Rewrite.Step a c) :
    Relation.Join (Relation.ReflTransGen Rewrite.Step) b c :=
  Rewrite.step_locallyConfluent hab hac

/-- Any configuration admits an irreducible descendant under the rewrite relation. -/
theorem rewrite_terminal_exists (a : Rewrite.DigitCfg) :
    ∃ b : Rewrite.DigitCfg, Relation.ReflTransGen Rewrite.Step a b ∧ Rewrite.Irreducible b :=
  Rewrite.exists_irreducible_descendant a

/-- Any irreducible terminal reached from a finite window agrees with the folded normal form. -/
theorem rewrite_terminal_equals_fold {w : Word m} {b : Rewrite.DigitCfg}
    (hab : Relation.ReflTransGen Rewrite.Step (Rewrite.iota w) b)
    (hIrr : Rewrite.Irreducible b) (hSup : Rewrite.SupportedBelow b m) :
    b = Rewrite.iota (Fold w).1 :=
  Rewrite.irreducible_terminal_eq_fold hab hIrr hSup

/-- The inverse-limit presentation identifies compatible stable families with infinite stable words. -/
def inverseLimitPresentation : X.CompatibleFamily ≃ X.XInfinity :=
  X.inverseLimitEquiv

/-- The inverse-limit presentation is exact on the compatible-family side. -/
theorem inverseLimitPresentation_left (F : X.CompatibleFamily) :
    inverseLimitPresentation.symm (inverseLimitPresentation F) = F :=
  X.inverseLimitEquiv.left_inv F

/-- The inverse-limit presentation is exact on the infinite-stable-word side. -/
theorem inverseLimitPresentation_right (a : X.XInfinity) :
    inverseLimitPresentation (inverseLimitPresentation.symm a) = a :=
  X.inverseLimitEquiv.right_inv a

/-- The one-step defect is the special case of the global defect at adjacent resolutions. -/
theorem localDefect_as_globalStep (η : Word (m + 1)) :
    localDefect η = globalDefect (Nat.le_succ m) η :=
  localDefect_eq_globalDefect η

/-- Global defect satisfies the recursive xor-step identity. -/
theorem globalDefect_recursive (h : m ≤ n) (ω : Word (n + 1)) :
    globalDefect (Nat.le_trans h (Nat.le_succ n)) ω
      = xorWord (restrictWord h (localDefect ω)) (globalDefect h (truncate ω)) :=
  globalDefect_step h ω

/-- Global defect is the xor-telescope of projected local defects. -/
theorem defect_telescope (m k : Nat) (ω : Word (m + k)) :
    globalDefect (Nat.le_add_right m k) ω = defectChain m k ω :=
  globalDefect_eq_defectChain m k ω

/-- The stable finite language is presented by the explicit two-state golden-mean graph. -/
theorem stableLanguage_sofic (w : Word m) :
    Omega.Graph.AcceptsWord Omega.Graph.goldenMeanGraph false w ↔ No11 w :=
  Omega.Graph.acceptsWord_goldenMean_iff_no11 w

/-- Prefix events are pure for the discrete scan-error profile. -/
theorem prefixEvent_pure_discrete (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixBoundaryCells μ h (SPG.prefixEvent h A) = ∅ ∧
      SPG.prefixScanError μ h (SPG.prefixEvent h A) = 0 := by
  exact ⟨SPG.prefixBoundaryCells_prefixEvent_eq_empty μ h A,
    SPG.prefixScanError_eq_zero_of_prefixEvent μ h A⟩

/-- Prefix events are pure for the finite-observable measure scan-error profile. -/
theorem prefixEvent_pure_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixBoundaryCellsMeasure μ h (SPG.prefixEvent h A) = ∅ ∧
      SPG.prefixScanErrorMeasure μ h (SPG.prefixEvent h A) = 0 := by
  exact ⟨SPG.prefixBoundaryCellsMeasure_prefixEvent_eq_empty μ h A,
    SPG.prefixScanErrorMeasure_eq_zero_of_prefixEvent μ h A⟩

/-- Prefix events are observable-pure in the measure scan-error model. -/
theorem prefixEvent_observablePure_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.ObservablePureMeasure μ (SPG.prefixObservation h) (SPG.prefixEvent h A) :=
  SPG.prefixObservablePureMeasure_prefixEvent μ h A

/-- Observable purity is equivalent to having no boundary cells in the finite-observable measure model. -/
theorem observablePure_iff_boundaryEmpty_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.ObservablePureMeasure μ obs P ↔ SPG.boundaryCellsMeasure μ obs P = ∅ :=
  SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty μ obs P

/-- Prefix-observable purity is equivalent to an empty prefix boundary. -/
theorem prefixObservablePure_iff_boundaryEmpty_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.ObservablePureMeasure μ (SPG.prefixObservation h) P
      ↔ SPG.prefixBoundaryCellsMeasure μ h P = ∅ :=
  SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty μ (SPG.prefixObservation h) P

/-- Observable purity forces zero prefix scan error in the measure model. -/
theorem prefixObservablePure_zero_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n))
    (hPure : SPG.ObservablePureMeasure μ (SPG.prefixObservation h) P) :
    SPG.prefixScanErrorMeasure μ h P = 0 :=
  SPG.prefixScanErrorMeasure_eq_zero_of_observablePure μ h P hPure

/-- Observable purity forces zero scan error for any finite observable measure model. -/
theorem observablePure_zero_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α)
    (hPure : SPG.ObservablePureMeasure μ obs P) :
    SPG.scanErrorMeasure μ obs P = 0 :=
  SPG.scanErrorMeasure_eq_zero_of_observablePure μ obs P hPure

/-- Prefix scan error admits the boundary-cell decomposition in the measure model. -/
theorem prefixScanError_measure_boundary_decomposition [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ h P
      = Finset.sum (SPG.prefixBoundaryCellsMeasure μ h P) (fun b =>
          min (SPG.cellEventMeasure μ (SPG.prefixObservation h) P b)
            (SPG.cellComplMeasure μ (SPG.prefixObservation h) P b)) :=
  SPG.prefixScanErrorMeasure_eq_sum_boundary μ h P

/-- Prefix scan error is bounded by the total boundary-cell mass in the measure model. -/
theorem prefixScanError_measure_boundary_mass_bound [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ h P
      ≤ Finset.sum (SPG.prefixBoundaryCellsMeasure μ h P) (fun b =>
          SPG.cellMeasure μ (SPG.prefixObservation h) b) :=
  SPG.prefixScanErrorMeasure_le_boundaryMass μ h P

/-- Prefix scan error is bounded by boundary cardinality times a uniform cell-mass cap. -/
theorem prefixScanError_measure_boundary_card_bound [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) (κ : ENNReal)
    (hκ : ∀ b, SPG.cellMeasure μ (SPG.prefixObservation h) b ≤ κ) :
    SPG.prefixScanErrorMeasure μ h P ≤ (SPG.prefixBoundaryCellsMeasure μ h P).card * κ :=
  SPG.prefixScanErrorMeasure_le_boundaryCard_mul μ h P κ hκ

/-- The measure-theoretic prefix scan error reduces to the discrete one for a finite PMF. -/
theorem prefixScanError_measure_discrete_bridge [MeasurableSpace (Word n)]
    [MeasurableSingletonClass (Word n)]
    (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ.toMeasure h P = SPG.prefixScanError μ h P :=
  SPG.prefixScanErrorMeasure_toMeasure_eq_prefixScanError μ h P

/-- Pure prefix events remain zero-error after passing from PMFs to measures. -/
theorem prefixEvent_pure_measure_discrete_bridge [MeasurableSpace (Word n)]
    [MeasurableSingletonClass (Word n)]
    (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixScanErrorMeasure μ.toMeasure h (SPG.prefixEvent h A) = 0 := by
  rw [prefixScanError_measure_discrete_bridge μ h]
  exact SPG.prefixScanError_eq_zero_of_prefixEvent μ h A

/-- Prefix zero-error certificates are canonically valid. -/
theorem prefixZeroScan_hasCertificate {m n : Nat}
    (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    PrefixZeroScanCertificate.Valid { m := m, n := n, h := h, μ := μ, event := A } :=
  PrefixZeroScanCertificate.canonical μ h A

end

end Omega.Frontier
