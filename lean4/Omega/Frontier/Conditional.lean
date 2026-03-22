import Omega.Frontier.Certificates
import Omega.Graph.Sofic
import Omega.SPG.Clopen
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

/-- Any concrete local defect claim carries a canonical valid certificate. -/
theorem localDefect_hasCertificate (η : Word (m + 1)) :
    LocalDefectCertificate.Valid { m := m, input := η, claimed := localDefect η } :=
  rfl

/-- Any concrete global defect claim carries a canonical valid certificate. -/
theorem globalDefect_hasCertificate (m k : Nat) (ω : Word (m + k)) :
    DefectCertificate.Valid
      ({ m := m, k := k, input := ω
       , claimed := globalDefect (Nat.le_add_right m k) ω } : DefectCertificate) :=
  rfl

/-- Any one-step rewrite witness is already a valid rewrite-step certificate. -/
theorem rewriteStep_hasCertificate {a b : Rewrite.DigitCfg} (h : Rewrite.Step a b) :
    RewriteStepCertificate.Valid { source := a, target := b } :=
  h

/-- Stable words yield canonical irreducibility certificates for their rewrite embeddings. -/
theorem stableIrreducible_hasCertificate (x : X m) :
    RewriteIrreducibleCertificate.Valid { source := Rewrite.iota x.1 } :=
  Rewrite.irreducible_iota_of_stable x

/-- Any folded image carries a canonical valid fold certificate. -/
theorem fold_hasCertificate (w : Word m) :
    FoldCertificate.Valid { m := m, input := w, claimed := Fold w } :=
  rfl

/-- Observable events carry canonical zero-scan certificates in the discrete model. -/
theorem observableZeroScan_hasCertificate {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    ObservableZeroScanCertificate.Valid { μ := μ, obs := obs, event := A } :=
  ObservableZeroScanCertificate.canonical μ obs A

/-- Any discrete scan-error claim has a canonical exact-value certificate. -/
theorem scanError_hasCertificate {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    ScanErrorCertificate.Valid
      ({ μ := μ, obs := obs, event := P
       , claimed := SPG.scanError μ obs P } : ScanErrorCertificate α β) :=
  rfl

/-- Any prefix scan-error claim has a canonical exact-value certificate. -/
theorem prefixScanError_hasCertificate {m n : Nat}
    (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    PrefixScanErrorCertificate.Valid
      ({ m := m, n := n, h := h, μ := μ, event := P
       , claimed := SPG.prefixScanError μ h P } : PrefixScanErrorCertificate) :=
  rfl

/-- Canonical full-generation certificates are sound. -/
theorem generatedDefectCertificate_sound (m : Nat) (h : FullGeneration m) (d : Word m) :
    globalDefect (Nat.le_add_right m (generatedDefectCertificate m h d).k)
        (generatedDefectCertificate m h d).input
      = d := by
  simpa [generatedDefectCertificate_claimed] using
    (generatedDefectCertificate m h d).sound (generatedDefectCertificate_valid m h d)

/-- Canonical rewrite-step certificates preserve the represented value. -/
theorem rewriteStep_certificate_value {a b : Rewrite.DigitCfg} (h : Rewrite.Step a b) :
  Rewrite.value b = Rewrite.value a :=
  RewriteStepCertificate.value_preserved { source := a, target := b } h

/-- Canonical fold certificates are idempotent on their claimed stable image. -/
theorem foldCertificate_idempotent (w : Word m) :
    Fold (Fold w).1 = Fold w :=
  FoldCertificate.idempotent { m := m, input := w, claimed := Fold w } (fold_hasCertificate w)

/-- Canonical fold certificates place the source word inside the target fiber. -/
theorem foldCertificate_inFiber (w : Word m) :
    w ∈ X.fiber (Fold w) :=
  FoldCertificate.inFiber { m := m, input := w, claimed := Fold w } (fold_hasCertificate w)

/-- Canonical discrete observable-event zero-scan certificates are sound. -/
theorem observableZeroScan_certificate_sound {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    SPG.scanError μ obs (SPG.observableEvent obs A) = 0 :=
  ObservableZeroScanCertificate.sound { μ := μ, obs := obs, event := A }
    (observableZeroScan_hasCertificate μ obs A)

/-- Canonical prefix zero-scan certificates are sound. -/
theorem prefixZeroScan_certificate_sound {m n : Nat}
    (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixScanError μ h (SPG.prefixEvent h A) = 0 :=
  PrefixZeroScanCertificate.sound { m := m, n := n, h := h, μ := μ, event := A }
    (PrefixZeroScanCertificate.canonical μ h A)

/-- Exact scan-error certificates are sound by construction. -/
theorem scanError_certificate_sound {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P = SPG.scanError μ obs P :=
  ScanErrorCertificate.sound
    ({ μ := μ, obs := obs, event := P
     , claimed := SPG.scanError μ obs P } : ScanErrorCertificate α β)
    (scanError_hasCertificate μ obs P)

/-- Exact prefix scan-error certificates are sound by construction. -/
theorem prefixScanError_certificate_sound {m n : Nat}
    (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanError μ h P = SPG.prefixScanError μ h P :=
  PrefixScanErrorCertificate.sound
    ({ m := m, n := n, h := h, μ := μ, event := P
     , claimed := SPG.prefixScanError μ h P } : PrefixScanErrorCertificate)
    (prefixScanError_hasCertificate μ h P)

/-- The finite folding map is idempotent on arbitrary raw words. -/
theorem fold_idempotent (w : Word m) :
    Fold (Fold w).1 = Fold w :=
  Omega.Fold_idempotent w

/-- Stable words are fixed points of the finite folding map. -/
theorem fold_fixedOnStable (x : X m) :
    Fold x.1 = x :=
  Omega.Fold_stable x

/-- The finite folding map is surjective onto the stable syntax space. -/
theorem fold_surjective (m : Nat) :
    Function.Surjective (Fold (m := m)) :=
  Omega.Fold_surjective m

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

/-- Every stable target has a canonical chosen raw preimage. -/
theorem fold_choosePreimage_sound (x : X m) :
    Fold (X.choosePreimage x) = x :=
  X.Fold_choosePreimage x

/-- The canonical chosen raw preimage lies in the target fiber. -/
theorem fold_choosePreimage_inFiber (x : X m) :
    X.choosePreimage x ∈ X.fiber x :=
  X.choosePreimage_mem_fiber x

/-- Ranking a known preimage and unranking it recovers the original raw word. -/
theorem fold_unrank_rankOfEq (x : X m) (w : Word m) (h : Fold w = x) :
    X.unrankWord x (X.rankOfFoldEq x w h) = w :=
  X.unrankWord_rankOfFoldEq x w h

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

/-- Rewrite descendants preserve the represented Fibonacci value. -/
theorem rewrite_valueInvariant {a b : Rewrite.DigitCfg}
    (hab : Relation.ReflTransGen Rewrite.Step a b) :
    Rewrite.value b = Rewrite.value a :=
  Rewrite.reflTransGen_value hab

/-- Rewrite irreducibility is equivalent to being a stable digit configuration. -/
theorem rewrite_irreducible_iff_stableCfg {a : Rewrite.DigitCfg} :
    Rewrite.Irreducible a ↔ Rewrite.StableCfg a :=
  Rewrite.irreducible_iff_stableCfg

/-- Two irreducible configurations with the same represented value must agree. -/
theorem rewrite_irreducible_sameValue_unique {a b : Rewrite.DigitCfg}
    (hIrrA : Rewrite.Irreducible a) (hIrrB : Rewrite.Irreducible b)
    (hVal : Rewrite.value a = Rewrite.value b) :
    a = b :=
  Rewrite.irreducible_eq_of_value_eq hIrrA hIrrB hVal

/-- Folded stable embeddings are irreducible in the rewrite system. -/
theorem rewrite_fold_irreducible (w : Word m) :
    Rewrite.Irreducible (Rewrite.iota (Fold w).1) :=
  Rewrite.irreducible_iota_Fold w

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

/-- Any `No11` word is accepted by the explicit two-state golden-mean graph. -/
theorem stable_implies_sofic {w : Word m} (hNo11 : No11 w) :
    Omega.Graph.AcceptsWord Omega.Graph.goldenMeanGraph false w :=
  Omega.Graph.acceptsWord_goldenMean_of_no11 hNo11

/-- Any word accepted by the explicit two-state golden-mean graph is stable. -/
theorem sofic_implies_stable {w : Word m}
    (hAcc : Omega.Graph.AcceptsWord Omega.Graph.goldenMeanGraph false w) :
    No11 w :=
  Omega.Graph.no11_of_acceptsWord_goldenMean hAcc

/-- The stable length-`m` language equals the explicit golden-mean sofic language as a set. -/
theorem stableLanguage_set_sofic (m : Nat) :
    {w : Word m | No11 w}
      = {w : Word m | Omega.Graph.AcceptsWord Omega.Graph.goldenMeanGraph false w} :=
  Omega.Graph.stableLanguage_eq_goldenMean m

/-- Stable syntax points are accepted by the explicit two-state golden-mean presentation. -/
theorem stablePoint_sofic (x : X m) :
    Omega.Graph.AcceptsWord Omega.Graph.goldenMeanGraph false x.1 :=
  Omega.Graph.acceptsWord_of_stable x

/-- Prefix balls are exactly the cylinders cut out by the corresponding finite address. -/
theorem prefixBall_is_cylinder (x : SPG.OmegaInfinity) (m : Nat) :
    SPG.prefixBall x m = SPG.cylinderWord (SPG.prefixWord x m) :=
  SPG.prefixBall_eq_cylinderWord x m

/-- Cylinders are closed balls for the prefix ultrametric. -/
theorem cylinder_is_closedBall (w : Word m) :
    SPG.cylinderWord w
      = {x : SPG.OmegaInfinity | SPG.prefixDist x (SPG.extendWord w) ≤ (1 / 2 : ℝ) ^ m} :=
  SPG.cylinderWord_eq_closedBall w

/-- Prefix balls are closed balls for the prefix ultrametric. -/
theorem prefixBall_is_closedBall (x : SPG.OmegaInfinity) (m : Nat) :
    SPG.prefixBall x m = {y : SPG.OmegaInfinity | SPG.prefixDist y x ≤ (1 / 2 : ℝ) ^ m} :=
  SPG.prefixBall_eq_closedBall x m

/-- Finite-prefix events are clopen in the SPG symbolic topology. -/
theorem prefixEvent_decidableClopen (A : Set (Word m)) :
    IsClopen (SPG.fromWordSet A) :=
  SPG.spg_decidableClopen A

/-- Prefix-determined symbolic events are clopen. -/
theorem prefixDetermined_clopen (s : Set SPG.OmegaInfinity) (m : Nat)
    (hs : SPG.PrefixDetermined s m) :
    IsClopen s :=
  SPG.prefixDetermined_isClopen m hs

/-- A symbolic event is prefix-determined exactly when it is cut out by some finite address set. -/
theorem prefixDetermined_iff_fromWordSet (s : Set SPG.OmegaInfinity) (m : Nat) :
    SPG.PrefixDetermined s m ↔ ∃ A : Set (Word m), s = SPG.fromWordSet A :=
  SPG.prefixDetermined_iff_exists_fromWordSet s m

/-- Observable events have empty discrete scan-error boundary. -/
theorem observableEvent_boundaryEmpty_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    SPG.boundaryCells μ obs (SPG.observableEvent obs A) = ∅ :=
  SPG.boundaryCells_observableEvent_eq_empty μ obs A

/-- Observable events have zero discrete scan error. -/
theorem observableEvent_zero_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    SPG.scanError μ obs (SPG.observableEvent obs A) = 0 :=
  SPG.scanError_observableEvent_eq_zero μ obs A

/-- The discrete scan-error profile admits the exact boundary-cell decomposition. -/
theorem scanError_boundary_decomposition_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P
      = Finset.sum (SPG.boundaryCells μ obs P) (fun b =>
          min (SPG.cellEventMass μ obs P b) (SPG.cellComplMass μ obs P b)) :=
  SPG.scanError_eq_sum_boundary μ obs P

/-- The discrete scan-error profile is bounded by the total boundary-cell mass. -/
theorem scanError_boundary_mass_bound_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P
      ≤ Finset.sum (SPG.boundaryCells μ obs P) (fun b =>
          SPG.cellMass μ obs b) :=
  SPG.scanError_le_boundaryMass μ obs P

/-- The discrete scan-error profile is bounded by a uniform cell-mass cap times boundary size. -/
theorem scanError_boundary_card_bound_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) (κ : ENNReal)
    (hκ : ∀ b, SPG.cellMass μ obs b ≤ κ) :
    SPG.scanError μ obs P ≤ (SPG.boundaryCells μ obs P).card * κ :=
  SPG.scanError_le_boundaryCard_mul μ obs P κ hκ

/-- Empty discrete boundary forces zero scan error. -/
theorem scanError_zero_of_boundaryEmpty_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α)
    (hEmpty : SPG.boundaryCells μ obs P = ∅) :
    SPG.scanError μ obs P = 0 := by
  rw [scanError_boundary_decomposition_discrete, hEmpty]
  simp

/-- Observable events are observable-pure in the finite-observable measure model. -/
theorem observableEvent_observablePure_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) :
    SPG.ObservablePureMeasure μ obs (SPG.observableEvent obs A) :=
  SPG.observablePureMeasure_observableEvent μ obs A

/-- Observable events have empty boundary in the finite-observable measure model. -/
theorem observableEvent_boundaryEmpty_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) :
    SPG.boundaryCellsMeasure μ obs (SPG.observableEvent obs A) = ∅ :=
  SPG.boundaryCellsMeasure_observableEvent_eq_empty μ obs A

/-- Observable events have zero scan error in the finite-observable measure model. -/
theorem observableEvent_zero_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) :
    SPG.scanErrorMeasure μ obs (SPG.observableEvent obs A) = 0 :=
  SPG.scanErrorMeasure_observableEvent_eq_zero μ obs A

/-- The measure scan-error profile admits the exact boundary-cell decomposition. -/
theorem scanError_measure_boundary_decomposition [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ obs P
      = Finset.sum (SPG.boundaryCellsMeasure μ obs P) (fun b =>
          min (SPG.cellEventMeasure μ obs P b) (SPG.cellComplMeasure μ obs P b)) :=
  SPG.scanErrorMeasure_eq_sum_boundary μ obs P

/-- The measure scan-error profile is bounded by the total boundary-cell mass. -/
theorem scanError_measure_boundary_mass_bound [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ obs P
      ≤ Finset.sum (SPG.boundaryCellsMeasure μ obs P) (fun b =>
          SPG.cellMeasure μ obs b) :=
  SPG.scanErrorMeasure_le_boundaryMass μ obs P

/-- The measure scan-error profile is bounded by a uniform cell-mass cap times boundary size. -/
theorem scanError_measure_boundary_card_bound [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) (κ : ENNReal)
    (hκ : ∀ b, SPG.cellMeasure μ obs b ≤ κ) :
    SPG.scanErrorMeasure μ obs P ≤ (SPG.boundaryCellsMeasure μ obs P).card * κ :=
  SPG.scanErrorMeasure_le_boundaryCard_mul μ obs P κ hκ

/-- Empty boundary forces zero scan error in the finite-observable measure model. -/
theorem scanError_zero_of_boundaryEmpty_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α)
    (hEmpty : SPG.boundaryCellsMeasure μ obs P = ∅) :
    SPG.scanErrorMeasure μ obs P = 0 := by
  have hPure : SPG.ObservablePureMeasure μ obs P :=
    (SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty μ obs P).2 hEmpty
  exact SPG.scanErrorMeasure_eq_zero_of_observablePure μ obs P hPure

/-- The general measure scan-error profile reduces to the discrete one on finite PMFs. -/
theorem scanError_measure_discrete_bridge {α β : Type*} [Fintype α] [Fintype β]
    [MeasurableSpace α] [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ.toMeasure obs P = SPG.scanError μ obs P :=
  SPG.scanErrorMeasure_toMeasure_eq_scanError μ obs P

/-- Observable events remain zero-error after passing from finite PMFs to measures. -/
theorem observableEvent_zero_measure_discrete_bridge {α β : Type*} [Fintype α] [Fintype β]
    [MeasurableSpace α] [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    SPG.scanErrorMeasure μ.toMeasure obs (SPG.observableEvent obs A) = 0 := by
  rw [scanError_measure_discrete_bridge μ obs]
  exact SPG.scanError_observableEvent_eq_zero μ obs A

/-- Prefix events are pure for the discrete scan-error profile. -/
theorem prefixEvent_pure_discrete (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixBoundaryCells μ h (SPG.prefixEvent h A) = ∅ ∧
      SPG.prefixScanError μ h (SPG.prefixEvent h A) = 0 := by
  exact ⟨SPG.prefixBoundaryCells_prefixEvent_eq_empty μ h A,
    SPG.prefixScanError_eq_zero_of_prefixEvent μ h A⟩

/-- Prefix events have empty discrete boundary at every finite resolution. -/
theorem prefixEvent_boundaryEmpty_discrete (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixBoundaryCells μ h (SPG.prefixEvent h A) = ∅ :=
  SPG.prefixBoundaryCells_prefixEvent_eq_empty μ h A

/-- Prefix events have zero discrete scan error at every finite resolution. -/
theorem prefixEvent_zero_discrete (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixScanError μ h (SPG.prefixEvent h A) = 0 :=
  SPG.prefixScanError_eq_zero_of_prefixEvent μ h A

/-- Empty prefix boundary forces zero discrete prefix scan error. -/
theorem prefixScanError_zero_of_boundaryEmpty_discrete (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) (hEmpty : SPG.prefixBoundaryCells μ h P = ∅) :
    SPG.prefixScanError μ h P = 0 := by
  rw [SPG.prefixScanError_eq_sum_boundary, hEmpty]
  simp

/-- Prefix events are pure for the finite-observable measure scan-error profile. -/
theorem prefixEvent_pure_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixBoundaryCellsMeasure μ h (SPG.prefixEvent h A) = ∅ ∧
      SPG.prefixScanErrorMeasure μ h (SPG.prefixEvent h A) = 0 := by
  exact ⟨SPG.prefixBoundaryCellsMeasure_prefixEvent_eq_empty μ h A,
    SPG.prefixScanErrorMeasure_eq_zero_of_prefixEvent μ h A⟩

/-- Prefix events have empty measure-theoretic boundary at every finite resolution. -/
theorem prefixEvent_boundaryEmpty_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixBoundaryCellsMeasure μ h (SPG.prefixEvent h A) = ∅ :=
  SPG.prefixBoundaryCellsMeasure_prefixEvent_eq_empty μ h A

/-- Prefix events have zero measure scan error at every finite resolution. -/
theorem prefixEvent_zero_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixScanErrorMeasure μ h (SPG.prefixEvent h A) = 0 :=
  SPG.prefixScanErrorMeasure_eq_zero_of_prefixEvent μ h A

/-- Empty prefix boundary forces zero measure prefix scan error. -/
theorem prefixScanError_zero_of_boundaryEmpty_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n))
    (hEmpty : SPG.prefixBoundaryCellsMeasure μ h P = ∅) :
    SPG.prefixScanErrorMeasure μ h P = 0 := by
  have hPure : SPG.ObservablePureMeasure μ (SPG.prefixObservation h) P :=
    (SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty μ (SPG.prefixObservation h) P).2 hEmpty
  exact SPG.prefixScanErrorMeasure_eq_zero_of_observablePure μ h P hPure

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

/-- Zero scan error is equivalent to observable purity in the finite-observable measure model. -/
theorem scanError_zero_iff_observablePure_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ obs P = 0 ↔ SPG.ObservablePureMeasure μ obs P :=
  SPG.scanErrorMeasure_eq_zero_iff_observablePure μ obs P

/-- Zero scan error is equivalent to having empty boundary in the finite-observable measure model. -/
theorem scanError_zero_iff_boundaryEmpty_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ obs P = 0 ↔ SPG.boundaryCellsMeasure μ obs P = ∅ :=
  SPG.scanErrorMeasure_eq_zero_iff_boundaryCellsMeasure_eq_empty μ obs P

/-- Prefix-observable purity is equivalent to an empty prefix boundary. -/
theorem prefixObservablePure_iff_boundaryEmpty_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.ObservablePureMeasure μ (SPG.prefixObservation h) P
      ↔ SPG.prefixBoundaryCellsMeasure μ h P = ∅ :=
  SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty μ (SPG.prefixObservation h) P

/-- Zero prefix scan error is equivalent to prefix-observable purity in the measure model. -/
theorem prefixScanError_zero_iff_observablePure_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ h P = 0
      ↔ SPG.ObservablePureMeasure μ (SPG.prefixObservation h) P :=
  SPG.prefixScanErrorMeasure_eq_zero_iff_observablePure μ h P

/-- Zero prefix scan error is equivalent to having empty prefix boundary in the measure model. -/
theorem prefixScanError_zero_iff_boundaryEmpty_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ h P = 0 ↔ SPG.prefixBoundaryCellsMeasure μ h P = ∅ :=
  SPG.prefixScanErrorMeasure_eq_zero_iff_boundaryCellsMeasure_eq_empty μ h P

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

/-- Boundary cells commute with the PMF-to-measure bridge for finite observables. -/
theorem boundaryCells_measure_discrete_bridge {α β : Type*} [Fintype α] [Fintype β]
    [MeasurableSpace α] [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.boundaryCellsMeasure μ.toMeasure obs P = SPG.boundaryCells μ obs P :=
  SPG.boundaryCellsMeasure_toMeasure_eq_boundaryCells μ obs P

/-- Prefix boundary cells commute with the PMF-to-measure bridge. -/
theorem prefixBoundaryCells_measure_discrete_bridge [MeasurableSpace (Word n)]
    [MeasurableSingletonClass (Word n)]
    (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixBoundaryCellsMeasure μ.toMeasure h P = SPG.prefixBoundaryCells μ h P :=
  SPG.prefixBoundaryCellsMeasure_toMeasure_eq_prefixBoundaryCells μ h P

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

/-- Scan error is symmetric under complement of the event (discrete). -/
theorem scanError_compl_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs Pᶜ = SPG.scanError μ obs P :=
  SPG.scanError_compl μ obs P

/-- Scan error of the empty event is zero (discrete). -/
theorem scanError_empty_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) :
    SPG.scanError μ obs ∅ = 0 :=
  SPG.scanError_empty μ obs

/-- Scan error of the full event is zero (discrete). -/
theorem scanError_univ_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) :
    SPG.scanError μ obs Set.univ = 0 :=
  SPG.scanError_univ μ obs

/-- Observable events are observable-pure in the discrete model. -/
theorem observableEvent_observablePure_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (A : Set β) :
    SPG.ObservablePure μ obs (SPG.observableEvent obs A) :=
  SPG.observablePure_observableEvent μ obs A

/-- Discrete observable purity is equivalent to having empty boundary. -/
theorem observablePure_iff_boundaryEmpty_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.ObservablePure μ obs P ↔ SPG.boundaryCells μ obs P = ∅ :=
  SPG.observablePure_iff_boundaryCells_eq_empty μ obs P

/-- Zero discrete scan error is equivalent to discrete observable purity. -/
theorem scanError_zero_iff_observablePure_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P = 0 ↔ SPG.ObservablePure μ obs P :=
  SPG.scanError_eq_zero_iff_observablePure μ obs P

/-- Zero discrete scan error is equivalent to empty boundary. -/
theorem scanError_zero_iff_boundaryEmpty_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P = 0 ↔ SPG.boundaryCells μ obs P = ∅ :=
  SPG.scanError_eq_zero_iff_boundaryCells_eq_empty μ obs P

/-- Scan error is symmetric under complement of the event (measure). -/
theorem scanError_compl_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ obs Pᶜ = SPG.scanErrorMeasure μ obs P :=
  SPG.scanErrorMeasure_compl μ obs P

/-- Scan error of the empty event is zero (measure). -/
theorem scanError_empty_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) :
    SPG.scanErrorMeasure μ obs ∅ = 0 :=
  SPG.scanErrorMeasure_empty μ obs

/-- Scan error of the full event is zero (measure). -/
theorem scanError_univ_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) :
    SPG.scanErrorMeasure μ obs Set.univ = 0 :=
  SPG.scanErrorMeasure_univ μ obs

/-- Prefix events are observable-pure in the discrete model. -/
theorem prefixEvent_observablePure_discrete (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.ObservablePure μ (SPG.prefixObservation h) (SPG.prefixEvent h A) :=
  SPG.prefixObservablePure_prefixEvent μ h A

/-- Zero discrete prefix scan error is equivalent to prefix-observable purity. -/
theorem prefixScanError_zero_iff_observablePure_discrete (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) :
    SPG.prefixScanError μ h P = 0 ↔ SPG.ObservablePure μ (SPG.prefixObservation h) P :=
  SPG.prefixScanError_eq_zero_iff_observablePure μ h P

/-- Zero discrete prefix scan error is equivalent to empty prefix boundary. -/
theorem prefixScanError_zero_iff_boundaryEmpty_discrete (μ : PMF (Word n)) (h : m ≤ n)
    (P : Set (Word n)) :
    SPG.prefixScanError μ h P = 0 ↔ SPG.prefixBoundaryCells μ h P = ∅ :=
  SPG.prefixScanError_eq_zero_iff_boundaryCells_eq_empty μ h P

/-- Prefix scan error is symmetric under complement (discrete). -/
theorem prefixScanError_compl_discrete (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanError μ h Pᶜ = SPG.prefixScanError μ h P :=
  SPG.prefixScanError_compl μ h P

/-- Prefix scan error of the empty event is zero (discrete). -/
theorem prefixScanError_empty_discrete (μ : PMF (Word n)) (h : m ≤ n) :
    SPG.prefixScanError μ h ∅ = 0 :=
  SPG.prefixScanError_empty μ h

/-- Prefix scan error of the full event is zero (discrete). -/
theorem prefixScanError_univ_discrete (μ : PMF (Word n)) (h : m ≤ n) :
    SPG.prefixScanError μ h Set.univ = 0 :=
  SPG.prefixScanError_univ μ h

/-- Discrete observable purity is equivalent to measure-theoretic purity under PMF.toMeasure. -/
theorem observablePure_measure_discrete_bridge {α β : Type*} [Fintype α] [Fintype β]
    [MeasurableSpace α] [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.ObservablePureMeasure μ.toMeasure obs P ↔ SPG.ObservablePure μ obs P :=
  SPG.observablePureMeasure_toMeasure_iff_observablePure μ obs P

/-- Prefix scan error is symmetric under complement (measure). -/
theorem prefixScanError_compl_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ h Pᶜ = SPG.prefixScanErrorMeasure μ h P :=
  SPG.prefixScanErrorMeasure_compl μ h P

/-- Prefix scan error of the empty event is zero (measure). -/
theorem prefixScanError_empty_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) :
    SPG.prefixScanErrorMeasure μ h ∅ = 0 :=
  SPG.prefixScanErrorMeasure_empty μ h

/-- Prefix scan error of the full event is zero (measure). -/
theorem prefixScanError_univ_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) :
    SPG.prefixScanErrorMeasure μ h Set.univ = 0 :=
  SPG.prefixScanErrorMeasure_univ μ h

/-- Finer observation reduces discrete scan error (observation refinement monotonicity). -/
theorem scanError_antitone_of_refines {α β γ : Type*} [Fintype α] [Fintype β] [Fintype γ]
    (μ : PMF α) (obs₁ : α → β) (obs₂ : α → γ) (f : γ → β)
    (hRef : ∀ x, obs₁ x = f (obs₂ x)) (P : Set α) :
    SPG.scanError μ obs₂ P ≤ SPG.scanError μ obs₁ P :=
  SPG.scanError_antitone_of_refines μ obs₁ obs₂ f hRef P

/-- Prefix scan error is monotonically non-increasing in the prefix resolution. -/
theorem prefixScanError_antitone {m₁ m₂ n : Nat}
    (μ : PMF (Word n)) (h₁ : m₁ ≤ n) (h₂ : m₂ ≤ n) (hm : m₁ ≤ m₂)
    (P : Set (Word n)) :
    SPG.prefixScanError μ h₂ P ≤ SPG.prefixScanError μ h₁ P :=
  SPG.prefixScanError_antitone μ h₁ h₂ hm P

/-- Cell event masses partition the total event mass (discrete). -/
theorem cellEventMass_partition {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    ∑ b, SPG.cellEventMass μ obs P b = SPG.setMass μ P :=
  SPG.cellEventMass_sum_eq_setMass μ obs P

/-- Cell complement masses partition the total complement mass (discrete). -/
theorem cellComplMass_partition {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    ∑ b, SPG.cellComplMass μ obs P b = SPG.setMass μ Pᶜ :=
  SPG.cellComplMass_sum_eq_setMass_compl μ obs P

/-- Scan error is bounded by the Bayes-optimal error min(μ(P), μ(Pᶜ)) (discrete). -/
theorem scanError_bayes_bound {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P ≤ min (SPG.setMass μ P) (SPG.setMass μ Pᶜ) :=
  SPG.scanError_le_min_setMass μ obs P

/-- Scan error under a general measure is bounded by the Bayes-optimal bound. -/
theorem scanError_measure_bayes_bound [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ obs P ≤ min
        (∑ b, SPG.cellEventMeasure μ obs P b) (∑ b, SPG.cellComplMeasure μ obs P b) :=
  SPG.scanErrorMeasure_le_min μ obs P

/-! ### Paper Section 4: Stable Syntax Cardinality & Zeckendorf Bridge -/

/-- |X_m| = paperFib(m+1) = F_{m+2} (paper Proposition 4.1: Fibonacci cardinality). -/
theorem stableSyntax_card_eq_fibonacci (m : Nat) :
    Fintype.card (X m) = paperFib (m + 1) :=
  X.card_eq_paperFib_succ m

/-- |X_{m+2}| = |X_{m+1}| + |X_m| (paper Proposition 4.1: Fibonacci recurrence). -/
theorem stableSyntax_card_recurrence (m : Nat) :
    Fintype.card (X (m + 2)) = Fintype.card (X (m + 1)) + Fintype.card (X m) :=
  X.card_recurrence m

/-- Active positions of a stable word form a Zeckendorf representation (paper Theorem 4.1). -/
theorem stableWord_zeckendorf_valid (x : X m) :
    (X.zeckIndices x).IsZeckendorfRep :=
  X.zeckIndices_isZeckendorfRep x

/-- The stable value equals the Fibonacci-weighted sum at active positions (paper Theorem 4.1). -/
theorem stableValue_eq_fibonacci_weighted_sum (x : X m) :
    stableValue x = ((X.zeckIndices x).map Nat.fib).sum :=
  X.stableValue_eq_sum_fib_zeckIndices x

/-- The Zeckendorf encoding of a stable word sums to its stable value. -/
theorem stableValue_eq_zeckRep_sum (x : X m) :
    ((X.zeckRep x).1.map fib).sum = stableValue x :=
  X.sum_fib_zeckRep x

/-- Every stable target has a positive fiber cardinality under Fold. -/
theorem fold_fiber_card_pos (x : X m) :
    0 < (X.fiber x).card :=
  X.fiber_card_pos x

/-! ### Paper Section 6: Stable Value & Modular Arithmetic -/

/-- The stable value map is injective: distinct stable words have distinct values (paper Theorem 6.1). -/
theorem stableValue_injective (m : Nat) :
    Function.Injective (stableValue (m := m)) :=
  Function.HasLeftInverse.injective ⟨X.ofNat m, X.ofNat_stableValue⟩

/-- Constructing a stable word from its value recovers the original word (paper Theorem 6.1). -/
theorem stableValue_ofNat_roundtrip (x : X m) :
    X.ofNat m (stableValue x) = x :=
  X.ofNat_stableValue x

/-- Fold followed by ofNat recovers the fold: ofNat m (stableValue (Fold w)) = Fold w. -/
theorem fold_ofNat_roundtrip (w : Word m) :
    X.ofNat m (stableValue (Fold w)) = Fold w :=
  X.ofNat_stableValue (Fold w)

/-! ### Paper Section 3 / Definition 3.5: Boundary Cylinder Count -/

/-- Boundary cylinder count equals zero iff the event is observable-pure (measure, paper Corollary 3.1). -/
theorem boundaryCylinderCount_zero_iff_pure_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.boundaryCylinderCount μ obs P = 0 ↔ SPG.ObservablePureMeasure μ obs P :=
  SPG.boundaryCylinderCount_eq_zero_iff_observablePure μ obs P

/-- Zero scan error iff zero boundary cylinder count (measure, paper Corollary 3.1). -/
theorem scanError_zero_iff_boundaryCylinderCount_zero_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.scanErrorMeasure μ obs P = 0 ↔ SPG.boundaryCylinderCount μ obs P = 0 :=
  SPG.scanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero μ obs P

/-- Observable-event boundary cylinder count vanishes for any measure. -/
theorem boundaryCylinderCount_observableEvent_zero [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (A : Set β) :
    SPG.boundaryCylinderCount μ obs (SPG.observableEvent obs A) = 0 :=
  SPG.boundaryCylinderCount_observableEvent_eq_zero μ obs A

/-- Prefix event boundary cylinder count vanishes for any measure. -/
theorem prefixBoundaryCylinderCount_prefixEvent_zero [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    SPG.prefixBoundaryCylinderCount μ h (SPG.prefixEvent h A) = 0 :=
  SPG.prefixBoundaryCylinderCount_prefixEvent_eq_zero μ h A

/-- Prefix boundary cylinder count equals zero iff the event is observable-pure (measure). -/
theorem prefixBoundaryCylinderCount_zero_iff_pure_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixBoundaryCylinderCount μ h P = 0
      ↔ SPG.ObservablePureMeasure μ (SPG.prefixObservation h) P :=
  SPG.prefixBoundaryCylinderCount_eq_zero_iff_observablePure μ h P

/-- Zero prefix scan error iff zero prefix boundary cylinder count (measure). -/
theorem prefixScanError_zero_iff_boundaryCylinderCount_zero_measure
    [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ h P = 0 ↔ SPG.prefixBoundaryCylinderCount μ h P = 0 :=
  SPG.prefixScanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero μ h P

/-- Boundary cylinder count commutes with the PMF-to-measure bridge. -/
theorem boundaryCylinderCount_measure_discrete_bridge {α β : Type*} [Fintype α] [Fintype β]
    [MeasurableSpace α] [MeasurableSingletonClass α]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.boundaryCylinderCount μ.toMeasure obs P = (SPG.boundaryCells μ obs P).card :=
  SPG.boundaryCylinderCount_toMeasure_eq μ obs P

/-- Prefix boundary cylinder count commutes with the PMF-to-measure bridge. -/
theorem prefixBoundaryCylinderCount_measure_discrete_bridge
    [MeasurableSpace (Word n)] [MeasurableSingletonClass (Word n)]
    (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixBoundaryCylinderCount μ.toMeasure h P
      = (SPG.prefixBoundaryCells μ h P).card :=
  SPG.prefixBoundaryCylinderCount_toMeasure_eq μ h P

/-! ### Paper Section 3: Cell Partition Identity -/

/-- Cell event mass plus complement mass equals total cell mass (paper Proposition 3.2 partition). -/
theorem cellEventMass_add_cellComplMass_partition {α β : Type*} [Fintype α]
    (μ : PMF α) (obs : α → β) (P : Set α) (b : β) :
    SPG.cellEventMass μ obs P b + SPG.cellComplMass μ obs P b = SPG.cellMass μ obs b :=
  SPG.cellEventMass_add_cellComplMass_eq_cellMass μ obs P b

/-! ### Measure Monotonicity via PMF Bridge (paper Corollary 3.1) -/

/-- Scan error monotonicity under observation refinement, measure version via PMF bridge. -/
theorem scanError_measure_antitone_via_bridge
    {α β γ : Type*} [Fintype α] [Fintype β] [Fintype γ]
    [MeasurableSpace α] [MeasurableSingletonClass α]
    (μ : PMF α) (obs₁ : α → β) (obs₂ : α → γ) (f : γ → β)
    (hRef : ∀ x, obs₁ x = f (obs₂ x)) (P : Set α) :
    SPG.scanErrorMeasure μ.toMeasure obs₂ P ≤ SPG.scanErrorMeasure μ.toMeasure obs₁ P := by
  rw [SPG.scanErrorMeasure_toMeasure_eq_scanError,
    SPG.scanErrorMeasure_toMeasure_eq_scanError]
  exact SPG.scanError_antitone_of_refines μ obs₁ obs₂ f hRef P

/-- Prefix scan error under measure is monotonically non-increasing for PMF-lifted measures
    (paper Corollary 3.1: clarity monotonicity). -/
theorem prefixScanError_measure_antitone_via_bridge {m₁ m₂ n : Nat}
    [MeasurableSpace (Word n)] [MeasurableSingletonClass (Word n)]
    (μ : PMF (Word n)) (h₁ : m₁ ≤ n) (h₂ : m₂ ≤ n) (hm : m₁ ≤ m₂)
    (P : Set (Word n)) :
    SPG.prefixScanErrorMeasure μ.toMeasure h₂ P
      ≤ SPG.prefixScanErrorMeasure μ.toMeasure h₁ P := by
  rw [SPG.prefixScanErrorMeasure_toMeasure_eq_prefixScanError,
    SPG.prefixScanErrorMeasure_toMeasure_eq_prefixScanError]
  exact SPG.prefixScanError_antitone μ h₁ h₂ hm P

/-! ### Paper Proposition 3.x: Bayes Half-Bound -/

/-- Event mass + complement mass = total PMF mass (discrete partition). -/
theorem setMass_partition_discrete {α β : Type*} [Fintype α]
    (μ : PMF α) (P : Set α) :
    SPG.setMass μ P + SPG.setMass μ Pᶜ = ∑ x, (μ x : ENNReal) :=
  SPG.setMass_add_setMass_compl μ P

/-- Total PMF mass over a Fintype is 1. -/
theorem PMF_total_mass_one {α : Type*} [Fintype α] (μ : PMF α) :
    ∑ x, (μ x : ENNReal) = 1 :=
  SPG.PMF_sum_coe_eq_one μ

/-- Scan error is bounded by 1/2 for any PMF: 2 · ε ≤ 1 (paper Bayes optimality bound). -/
theorem scanError_bayes_half_bound {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    2 * SPG.scanError μ obs P ≤ 1 :=
  SPG.two_mul_scanError_le_one μ obs P

/-! ### Paper Theorem 6.1: Stable Value Bound & Arithmetic -/

/-- Stable values are strictly bounded by the Fibonacci cardinality (paper Theorem 6.1). -/
theorem stableValue_bounded (x : X m) : stableValue x < paperFib (m + 1) :=
  stableValue_lt_paperFib_succ x

/-- Stable values can be viewed as Fin-indexed values (paper Theorem 6.1). -/
theorem stableValue_as_fin (x : X m) :
    (X.stableValueFin x).val = stableValue x := rfl

/-- The stable value Fin map is injective. -/
theorem stableValueFin_injective_wrapper (m : Nat) :
    Function.Injective (X.stableValueFin (m := m)) :=
  X.stableValueFin_injective m

/-- Stable addition is commutative (paper Proposition 6.x). -/
theorem stableAdd_commutative (x y : X m) :
    X.stableAdd x y = X.stableAdd y x :=
  X.stableAdd_comm x y

/-- For n < F_{m+2}, X.ofNat m n has stable value n (paper Theorem 6.1 inverse). -/
theorem stableValue_ofNat_inverse {m : Nat} (n : Nat) (hn : n < paperFib (m + 1)) :
    stableValue (X.ofNat m n) = n :=
  X.stableValue_ofNat_lt n hn

/-- Stable value of ofNat respects modular reduction. -/
theorem stableValue_ofNat_mod_wrapper {m : Nat} (n : Nat) :
    stableValue (X.ofNat m (n % paperFib (m + 1))) = n % paperFib (m + 1) :=
  X.stableValue_ofNat_mod n

/-- stableZero has value 0. -/
theorem stableZero_value : stableValue (X.stableZero (m := m)) = 0 :=
  X.stableValue_stableZero

/-- Stable addition has a left identity. -/
theorem stableAdd_left_identity (x : X m) :
    X.stableAdd X.stableZero x = x :=
  X.stableAdd_zero_left x

/-- Stable addition has a right identity. -/
theorem stableAdd_right_identity (x : X m) :
    X.stableAdd x X.stableZero = x :=
  X.stableAdd_zero_right x

/-- Stable addition is associative (paper Section 6 emergent arithmetic). -/
theorem stableAdd_associative (x y z : X m) :
    X.stableAdd (X.stableAdd x y) z = X.stableAdd x (X.stableAdd y z) :=
  X.stableAdd_assoc x y z

/-- The stable syntax space is equivalent to Fin(F_{m+2}) as a finite type. -/
noncomputable def stableValueEquiv_wrapper (m : Nat) : X m ≃ Fin (paperFib (m + 1)) :=
  X.stableValueEquiv m

/-- The stableValue map into Fin is surjective (paper Theorem 6.1 surjectivity). -/
theorem stableValueFin_surjective_wrapper (m : Nat) :
    Function.Surjective (X.stableValueFin (m := m)) :=
  X.stableValueFin_surjective m

/-- The stableValue map into Fin is bijective (paper Theorem 6.1 bijectivity). -/
theorem stableValueFin_bijective_wrapper (m : Nat) :
    Function.Bijective (X.stableValueFin (m := m)) :=
  X.stableValueFin_bijective m

/-! ### Paper Theorem 4.2: Fiber Partition -/

/-- The word space has cardinality 2^m. -/
theorem word_card (m : Nat) : Fintype.card (Word m) = 2 ^ m :=
  X.Word_card m

/-- Fiber cardinalities sum to the total word count (paper Theorem 4.2: fibers partition). -/
theorem fiber_card_partition (m : Nat) :
    ∑ x : X m, (X.fiber x).card = Fintype.card (Word m) :=
  X.fiber_card_sum m

/-- Fiber cardinalities sum to 2^m. -/
theorem fiber_card_partition_pow (m : Nat) :
    ∑ x : X m, (X.fiber x).card = 2 ^ m :=
  X.fiber_card_sum_eq_pow m

/-! ### Paper Proposition 3.x: Complement Symmetry -/

/-- Discrete observable purity is symmetric under complement of the event. -/
theorem observablePure_compl_symmetric_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.ObservablePure μ obs Pᶜ ↔ SPG.ObservablePure μ obs P :=
  SPG.observablePure_compl μ obs P

/-- Discrete boundary cells are the same for the event and its complement. -/
theorem boundaryCells_compl_symmetric_discrete {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.boundaryCells μ obs Pᶜ = SPG.boundaryCells μ obs P :=
  SPG.boundaryCells_compl μ obs P

/-- Discrete prefix boundary cells are the same for the event and its complement. -/
theorem prefixBoundaryCells_compl_symmetric_discrete
    (μ : PMF (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixBoundaryCells μ h Pᶜ = SPG.prefixBoundaryCells μ h P :=
  SPG.prefixBoundaryCells_compl μ h P

/-- Measure observable purity is symmetric under complement of the event. -/
theorem observablePure_compl_symmetric_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.ObservablePureMeasure μ obs Pᶜ ↔ SPG.ObservablePureMeasure μ obs P :=
  SPG.observablePureMeasure_compl μ obs P

/-- Measure boundary cells are the same for the event and its complement. -/
theorem boundaryCells_compl_symmetric_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.boundaryCellsMeasure μ obs Pᶜ = SPG.boundaryCellsMeasure μ obs P :=
  SPG.boundaryCellsMeasure_compl μ obs P

/-- Measure boundary cylinder count is the same for the event and its complement. -/
theorem boundaryCylinderCount_compl_symmetric_measure [MeasurableSpace α] [Fintype β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) :
    SPG.boundaryCylinderCount μ obs Pᶜ = SPG.boundaryCylinderCount μ obs P :=
  SPG.boundaryCylinderCount_compl μ obs P

/-- Measure prefix boundary cells are the same for the event and its complement. -/
theorem prefixBoundaryCells_compl_symmetric_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixBoundaryCellsMeasure μ h Pᶜ = SPG.prefixBoundaryCellsMeasure μ h P :=
  SPG.prefixBoundaryCellsMeasure_compl μ h P

/-- Measure prefix boundary cylinder count is the same for the event and its complement. -/
theorem prefixBoundaryCylinderCount_compl_symmetric_measure [MeasurableSpace (Word n)]
    (μ : MeasureTheory.Measure (Word n)) (h : m ≤ n) (P : Set (Word n)) :
    SPG.prefixBoundaryCylinderCount μ h Pᶜ = SPG.prefixBoundaryCylinderCount μ h P :=
  SPG.prefixBoundaryCylinderCount_compl μ h P

/-! ### Paper Proposition 3.2: Cell-Level Bounds (measure) -/

/-- Cell event mass is bounded by cell total mass (measure). -/
theorem cellEventMeasure_le_cell [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) (b : β) :
    SPG.cellEventMeasure μ obs P b ≤ SPG.cellMeasure μ obs b :=
  SPG.cellEventMeasure_le_cellMeasure μ obs P b

/-- Cell complement mass is bounded by cell total mass (measure). -/
theorem cellComplMeasure_le_cell [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) (b : β) :
    SPG.cellComplMeasure μ obs P b ≤ SPG.cellMeasure μ obs b :=
  SPG.cellComplMeasure_le_cellMeasure μ obs P b

/-! ### Paper Proposition 3.2: Cell Partition Identity (measure, with measurability) -/

/-- Cell event mass + cell complement mass = total cell mass under a measurable event
    (measure-theoretic analogue of the discrete partition identity). -/
theorem cellPartition_identity_measure [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) (P : Set α) (b : β)
    (hP : MeasurableSet P) :
    SPG.cellEventMeasure μ obs P b + SPG.cellComplMeasure μ obs P b = SPG.cellMeasure μ obs b :=
  SPG.cellEventMeasure_add_cellComplMeasure_eq_cellMeasure μ obs P b hP

/-! ### Paper Corollary 3.1: Direct Measure Observation Refinement Monotonicity -/

/-- Observation refinement reduces scan error (direct measure version, paper Corollary 3.1). -/
theorem scanError_measure_antitone_direct [MeasurableSpace α] [Fintype β] [Fintype γ]
    [MeasurableSpace γ] [MeasurableSingletonClass γ] [DecidableEq β]
    (μ : MeasureTheory.Measure α) (obs₁ : α → β) (obs₂ : α → γ)
    (f : γ → β) (hRef : ∀ x, obs₁ x = f (obs₂ x))
    (hObs₂ : Measurable obs₂) (P : Set α) (hP : MeasurableSet P) :
    SPG.scanErrorMeasure μ obs₂ P ≤ SPG.scanErrorMeasure μ obs₁ P :=
  SPG.scanErrorMeasure_antitone_of_refines μ obs₁ obs₂ f hRef hObs₂ P hP

/-! ### Paper Section POM: Fiber Multiplicity -/

/-- Fiber multiplicity: number of raw words folding to a given stable word. -/
theorem fiberMultiplicity_positive (x : X m) : 0 < X.fiberMultiplicity x :=
  X.fiberMultiplicity_pos x

/-- Fiber multiplicities sum to 2^m (paper POM fiber partition). -/
theorem fiberMultiplicity_sum (m : Nat) :
    ∑ x : X m, X.fiberMultiplicity x = 2 ^ m :=
  X.fiberMultiplicity_sum_eq_pow m

/-! ### Paper Proposition 3.2: Measure Cell Mass Sum Identities -/

/-- Cell event measures sum to the event measure (with measurability). -/
theorem cellEventMeasure_sum_eq_event [MeasurableSpace α] [Fintype β]
    [MeasurableSpace β] [MeasurableSingletonClass β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (hObs : Measurable obs)
    (P : Set α) (hP : MeasurableSet P) :
    ∑ b, SPG.cellEventMeasure μ obs P b = μ P :=
  SPG.cellEventMeasure_sum μ obs hObs P hP

/-- Cell complement measures sum to the complement measure (with measurability). -/
theorem cellComplMeasure_sum_eq_compl [MeasurableSpace α] [Fintype β]
    [MeasurableSpace β] [MeasurableSingletonClass β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (hObs : Measurable obs)
    (P : Set α) (hP : MeasurableSet P) :
    ∑ b, SPG.cellComplMeasure μ obs P b = μ Pᶜ :=
  SPG.cellComplMeasure_sum μ obs hObs P hP

/-- Cell total measures sum to the total measure (with measurability). -/
theorem cellMeasure_sum_eq_total [MeasurableSpace α] [Fintype β]
    [MeasurableSpace β] [MeasurableSingletonClass β]
    (μ : MeasureTheory.Measure α) (obs : α → β) (hObs : Measurable obs) :
    ∑ b, SPG.cellMeasure μ obs b = μ Set.univ :=
  SPG.cellMeasure_sum μ obs hObs

/-! ### Paper Defect Section: Zero Defect Characterization -/

/-- Local defect vanishes iff Fold commutes with restriction (paper Defect characterization). -/
theorem localDefect_zero_iff_fold_commutes (η : Word (m + 1)) :
    localDefect η = zeroWord m ↔ Fold (truncate η) = X.restrict (Fold η) :=
  localDefect_eq_zero_iff_fold_commutes η

/-- Global defect vanishes iff Fold commutes with restriction across resolutions. -/
theorem globalDefect_zero_iff (h : m ≤ n) (ω : Word n) :
    globalDefect h ω = zeroWord m ↔
      Fold (restrictWord h ω) = X.restrictLE h (Fold ω) :=
  globalDefect_eq_zero_iff h ω

/-- Non-curvature is equivalent to Fold-restriction commutativity. -/
theorem non_curvature_iff_commutes (η : Word (m + 1)) :
    ¬ localCurvature η ↔ Fold (truncate η) = X.restrict (Fold η) :=
  not_localCurvature_iff_fold_commutes η

/-! ### Paper Recursive Addressing: Prefix Determination -/

/-- Prefix determination is monotone in depth (paper prefix non-expansion). -/
theorem prefixDetermined_monotone {s : Set SPG.OmegaInfinity} {m n : Nat}
    (h : m ≤ n) (hs : SPG.PrefixDetermined s m) : SPG.PrefixDetermined s n :=
  SPG.prefixDetermined_of_le h hs

/-- Prefix-determined sets form a Boolean algebra (intersection). -/
theorem prefixDetermined_inter_closure {s t : Set SPG.OmegaInfinity} {m : Nat}
    (hs : SPG.PrefixDetermined s m) (ht : SPG.PrefixDetermined t m) :
    SPG.PrefixDetermined (s ∩ t) m :=
  SPG.prefixDetermined_inter hs ht

/-- Prefix-determined sets form a Boolean algebra (union). -/
theorem prefixDetermined_union_closure {s t : Set SPG.OmegaInfinity} {m : Nat}
    (hs : SPG.PrefixDetermined s m) (ht : SPG.PrefixDetermined t m) :
    SPG.PrefixDetermined (s ∪ t) m :=
  SPG.prefixDetermined_union hs ht

/-- Prefix-determined sets form a Boolean algebra (complement). -/
theorem prefixDetermined_compl_closure {s : Set SPG.OmegaInfinity} {m : Nat}
    (hs : SPG.PrefixDetermined s m) : SPG.PrefixDetermined sᶜ m :=
  SPG.prefixDetermined_compl hs

/-! ### Paper Section 6: Stable Multiplication & Ring Structure -/

/-- Stable multiplication is commutative. -/
theorem stableMul_commutative (x y : X m) :
    X.stableMul x y = X.stableMul y x :=
  X.stableMul_comm x y

/-- Stable multiplication distributes over stable addition. -/
theorem stableMul_distributes_left (x y z : X m) :
    X.stableMul x (X.stableAdd y z) = X.stableAdd (X.stableMul x y) (X.stableMul x z) :=
  X.stableMul_stableAdd_left x y z

/-- stableZero annihilates under multiplication. -/
theorem stableMul_zero (x : X m) : X.stableMul X.stableZero x = X.stableZero :=
  X.stableMul_zero_left x

/-- stableOne is the multiplicative identity (when F_{m+2} > 1). -/
theorem stableMul_one (hm : 1 < paperFib (m + 1)) (x : X m) :
    X.stableMul X.stableOne x = x :=
  X.stableMul_one_left hm x

/-- Stable multiplication is associative (paper Section 6). -/
theorem stableMul_associative (x y z : X m) :
    X.stableMul (X.stableMul x y) z = X.stableMul x (X.stableMul y z) :=
  X.stableMul_assoc x y z

/-- Fiber multiplicity depends only on the stable value index. -/
theorem fiberMultiplicity_value_dependent (x : X m) :
    X.fiberMultiplicity x = X.fiberMultiplicityByValue m (stableValue x) :=
  X.fiberMultiplicity_eq_byValue x

/-! ### Paper Theorem 4.1: Zeckendorf Bit Characterization -/

/-- The bit pattern of X.ofNat m n is given by the Zeckendorf representation (paper Theorem 4.1). -/
theorem zeckendorf_bit_characterization (n : Nat) {i : Nat} (h : i < m) :
    get (X.ofNat m n).1 i = true ↔ i + 2 ∈ Nat.zeckendorf n :=
  X.get_ofNat_eq_true_iff h

/-- Active positions of a stable word form a valid Zeckendorf representation. -/
theorem stable_zeckendorf_valid_wrapper (x : X m) :
    (X.zeckIndices x).IsZeckendorfRep :=
  X.zeckIndices_isZeckendorfRep x

/-! ### Paper Proposition 3.x: Scan Error Single-Sided Bounds -/

/-- Scan error is bounded by the event mass (discrete). -/
theorem scanError_le_event_mass {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P ≤ SPG.setMass μ P :=
  SPG.scanError_le_setMass μ obs P

/-- Scan error is bounded by the complement mass (discrete). -/
theorem scanError_le_compl_mass {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    SPG.scanError μ obs P ≤ SPG.setMass μ Pᶜ :=
  SPG.scanError_le_setMass_compl μ obs P

/-! ### Paper Corollary 3.1: Measure Prefix Monotonicity & Probability Half-Bound -/

/-- Prefix scan error is monotonically non-increasing (direct measure version). -/
theorem prefixScanError_measure_antitone_direct {m₁ m₂ n : Nat}
    [MeasurableSpace (Word n)]
    [MeasurableSpace (Word m₂)] [MeasurableSingletonClass (Word m₂)]
    (μ : MeasureTheory.Measure (Word n))
    (h₁ : m₁ ≤ n) (h₂ : m₂ ≤ n) (hm : m₁ ≤ m₂)
    (hObs : Measurable (SPG.prefixObservation h₂))
    (P : Set (Word n)) (hP : MeasurableSet P) :
    SPG.prefixScanErrorMeasure μ h₂ P ≤ SPG.prefixScanErrorMeasure μ h₁ P :=
  SPG.prefixScanErrorMeasure_antitone_direct μ h₁ h₂ hm hObs P hP

/-- Scan error under a probability measure is bounded by 1/2 (measure version). -/
theorem scanError_measure_half_bound [MeasurableSpace α] [Fintype β]
    [MeasurableSpace β] [MeasurableSingletonClass β]
    (μ : MeasureTheory.Measure α) [MeasureTheory.IsProbabilityMeasure μ]
    (obs : α → β) (hObs : Measurable obs) (P : Set α) (hP : MeasurableSet P) :
    2 * SPG.scanErrorMeasure μ obs P ≤ 1 :=
  SPG.scanErrorMeasure_le_half μ obs hObs P hP

/-! ### Paper Theorem 6.1: stableValue Range Characterization -/

/-- The range of stableValue is exactly {0,...,F_{m+2}-1}. -/
theorem stableValue_range_eq (m : Nat) :
    Set.range (stableValue (m := m)) = {n | n < paperFib (m + 1)} :=
  X.stableValue_range m

/-! ### Paper Defect Section: Defect Chain Structure -/

/-- The defect chain connects to the global defect. -/
theorem defectChain_is_globalDefect (m k : Nat) (x : X (m + k)) :
    defectChain m k x.1 = globalDefect (Nat.le_add_right m k) x.1 :=
  defectChain_stable m k x

/-! ### Paper Fold Section: Rewrite System Properties -/

/-- Each rewrite step preserves the Fibonacci value (already wrapped, for completeness). -/
theorem rewrite_value_preserved {a b : Rewrite.DigitCfg} (h : Rewrite.Step a b) :
    Rewrite.value b = Rewrite.value a :=
  Rewrite.step_value h

/-- Each rewrite step does not increase the mass (rewrite monotonicity). -/
theorem rewrite_mass_nonincreasing {a b : Rewrite.DigitCfg} (h : Rewrite.Step a b) :
    Rewrite.mass b ≤ Rewrite.mass a :=
  Rewrite.step_mass_le h

/-! ### Paper Graph Section: Golden-Mean Edge Structure -/

/-- The golden-mean graph has edges from state 0 to state 0 (via bit 0). -/
theorem goldenMean_allows_00 :
    Omega.Graph.goldenMeanGraph.edge false false false :=
  Omega.Graph.goldenMean_edge_ff

/-- The golden-mean graph has edges from state 0 to state 1 (via bit 1). -/
theorem goldenMean_allows_01 :
    Omega.Graph.goldenMeanGraph.edge false true true :=
  Omega.Graph.goldenMean_edge_ft

/-- The golden-mean graph has edges from state 1 to state 0 (via bit 0). -/
theorem goldenMean_allows_10 :
    Omega.Graph.goldenMeanGraph.edge true false false :=
  Omega.Graph.goldenMean_edge_tf

/-- The golden-mean graph forbids the 11 transition. -/
theorem goldenMean_forbids_11 (q' : Bool) :
    ¬ Omega.Graph.goldenMeanGraph.edge true true q' :=
  Omega.Graph.goldenMean_no_edge_tt q'

/-! ### Paper Section 6: Stable Value Homomorphism -/

/-- stableValue encodes addition modulo F_{m+2}. -/
theorem stableValue_add_homomorphism (x y : X m) :
    stableValue (X.stableAdd x y) = (stableValue x + stableValue y) % paperFib (m + 1) :=
  X.stableValue_stableAdd x y

/-- stableValue encodes multiplication modulo F_{m+2}. -/
theorem stableValue_mul_homomorphism (x y : X m) :
    stableValue (X.stableMul x y) = (stableValue x * stableValue y) % paperFib (m + 1) :=
  X.stableValue_stableMul x y

/-! ### Paper SPG Section: Cell Event Measure Monotonicity -/

/-- Cell event measure is monotone in the event (measure). -/
theorem cellEventMeasure_event_monotone [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) {P Q : Set α} (h : P ⊆ Q) (b : β) :
    SPG.cellEventMeasure μ obs P b ≤ SPG.cellEventMeasure μ obs Q b :=
  SPG.cellEventMeasure_mono μ obs h b

/-! ### Paper SPG Section: Cylinder & Prefix Resolution -/

/-- Prefix determination is closed under mixed-resolution intersections. -/
theorem prefixDetermined_inter_mixed {s t : Set SPG.OmegaInfinity} {m₁ m₂ : Nat}
    (hs : SPG.PrefixDetermined s m₁) (ht : SPG.PrefixDetermined t m₂) :
    SPG.PrefixDetermined (s ∩ t) (max m₁ m₂) :=
  SPG.prefixDetermined_inter_resolutions hs ht

/-! ### Paper Defect Section: Defect Resolution Structure -/

/-- Global defect at identity resolution is always zero. -/
theorem globalDefect_identity (ω : Word m) :
    globalDefect (Nat.le_refl m) ω = zeroWord m :=
  globalDefect_refl ω

/-- Global defect at adjacent resolutions equals local defect. -/
theorem globalDefect_adjacent (η : Word (m + 1)) :
    globalDefect (Nat.le_succ m) η = localDefect η :=
  globalDefect_succ η

/-! ### Paper Fold Section: Rewrite Chain Properties -/

/-- Mass is non-increasing along rewrite chains. -/
theorem rewrite_mass_chain_nonincreasing {a b : Rewrite.DigitCfg}
    (h : Relation.ReflTransGen Rewrite.Step a b) :
    Rewrite.mass b ≤ Rewrite.mass a :=
  Rewrite.reflTransGen_mass_le h

/-! ### Paper Section 4: Weight & Append Structure -/

/-- Weight is preserved under appending false (extending by zero bit). -/
theorem weight_preserved_appendFalse (x : X m) :
    weight (X.appendFalse x).1 = weight x.1 :=
  weight_appendFalse x

/-- Weight increases by paperFib(m+1) under appending true. -/
theorem weight_increases_appendTrue (x : X m) (hLast : get x.1 (m - 1) = false) :
    weight (X.appendTrue x hLast).1 = weight x.1 + paperFib (m + 1) :=
  weight_appendTrue x hLast

/-- The constant observation has a single cell covering everything. -/
theorem constant_observation_cell (c : β) :
    SPG.observableCell (fun _ : α => c) c = Set.univ :=
  SPG.observableCell_const_eq_univ c

/-! ### Paper POM Section: Carry Defect Structure -/

/-- stableValue decomposes as restrict value + last bit contribution. -/
theorem stableValue_last_bit_decomposition (x : X (m + 1)) :
    stableValue x = stableValue (X.restrict x) +
      (if x.1 ⟨m, Nat.lt_succ_self m⟩ = true then paperFib (m + 1) else 0) :=
  stableValue_eq_restrict_add_last x

/-- The carry indicator is bounded by 1. -/
theorem carry_indicator_bounded (x y : X (m + 1)) :
    carryIndicator x y ≤ 1 :=
  X.carryIndicator_le_one x y

/-! ### Paper InverseLimit: Extensionality -/

/-- Infinite stable words are uniquely determined by their prefixes. -/
theorem XInfinity_uniqueness {a b : X.XInfinity} (h : ∀ m, X.prefixWord a m = X.prefixWord b m) :
    a = b :=
  X.XInfinity_ext h

/-- Zeckendorf indices have length at most m. -/
theorem zeckIndices_bounded (x : X m) : (X.zeckIndices x).length ≤ m :=
  X.zeckIndices_length_le x

/-! ### Paper SPG Section: Boundary Cell & Scan Error Structure -/

/-- Boundary cell count is bounded by the total number of observation cells. -/
theorem boundaryCells_count_bounded {α β : Type*} [Fintype α] [Fintype β]
    (μ : PMF α) (obs : α → β) (P : Set α) :
    (SPG.boundaryCells μ obs P).card ≤ Fintype.card β :=
  SPG.boundaryCells_card_le μ obs P

/-- Observable events from coarser observables have at most the same error under finer observables. -/
theorem observable_event_refined_monotone {α β γ : Type*} [Fintype α] [Fintype β] [Fintype γ]
    (μ : PMF α) (obs₁ : α → β) (obs₂ : α → γ) (f : γ → β)
    (hRef : ∀ x, obs₁ x = f (obs₂ x)) (A : Set β) :
    SPG.scanError μ obs₂ (SPG.observableEvent obs₁ A) ≤
      SPG.scanError μ obs₁ (SPG.observableEvent obs₁ A) :=
  SPG.scanError_observableEvent_refines_zero μ obs₁ obs₂ f hRef A

/-- Cell complement measure is anti-monotone in event containment. -/
theorem cellComplMeasure_antimonotone [MeasurableSpace α]
    (μ : MeasureTheory.Measure α) (obs : α → β) {P Q : Set α} (h : P ⊆ Q) (b : β) :
    SPG.cellComplMeasure μ obs Q b ≤ SPG.cellComplMeasure μ obs P b :=
  SPG.cellComplMeasure_anti μ obs h b

/-! ### Paper Defect Section: xor-truncation compatibility -/

/-- Truncation distributes over xor of words. -/
theorem truncate_distributes_xor (a b : Word (m + 1)) :
    truncate (xorWord a b) = xorWord (truncate a) (truncate b) :=
  truncate_xorWord a b

end

end Omega.Frontier
