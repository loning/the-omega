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

/-- Prefix zero-error certificates are canonically valid. -/
theorem prefixZeroScan_hasCertificate {m n : Nat}
    (μ : PMF (Word n)) (h : m ≤ n) (A : Set (Word m)) :
    PrefixZeroScanCertificate.Valid { m := m, n := n, h := h, μ := μ, event := A } :=
  PrefixZeroScanCertificate.canonical μ h A

end

end Omega.Frontier
