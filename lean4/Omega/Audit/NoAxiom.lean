import Omega.Folding.StableSyntax
import Omega.Folding.Zeckendorf
import Omega.Folding.Fold
import Omega.Folding.Fiber
import Omega.Folding.InverseLimit
import Omega.Folding.Rewrite
import Omega.Folding.Defect
import Omega.Graph.Sofic
import Omega.SPG.Clopen
import Omega.SPG.ScanErrorDiscrete
import Omega.SPG.ScanErrorMeasure
import Omega.Frontier.Conditional
import Omega.Folding.CarryDefect
import Omega.Folding.ModularTower
import Omega.Folding.InverseLimitTopology
import Omega.Folding.ShiftDynamics
import Omega.Folding.FibonacciField
import Omega.Folding.MomentSum
import Omega.Folding.CollisionKernel
import Omega.Folding.FibonacciPolynomial
import Omega.Folding.MaxFiber
import Omega.Audit.SourceMap

namespace Omega.Audit

/-
Run these commands manually during audit:

  #print axioms Omega.no11_truncate
  #print axioms Omega.X.restrict
  #print axioms Omega.paperFib_recurrence
  #print axioms Omega.X.card_eq_paperFib_succ
  #print axioms Omega.X.zeckIndices_isZeckendorfRep
  #print axioms Omega.X.stableValue_eq_sum_fib_zeckIndices
  #print axioms Omega.Fold_stable
  #print axioms Omega.Fold_idempotent
  #print axioms Omega.X.fiber_nonempty
  #print axioms Omega.X.rank_unrank
  #print axioms Omega.X.Fold_unrankWord
  #print axioms Omega.X.inverseLimitEquiv
  #print axioms Omega.Rewrite.step_value
  #print axioms Omega.Rewrite.step_stronglyTerminating
  #print axioms Omega.Rewrite.irreducible_supported_eq_iota_normalPrefix
  #print axioms Omega.Rewrite.irreducible_eq_of_normalPrefix_eq
  #print axioms Omega.Rewrite.reflTransGen_normalPrefix
  #print axioms Omega.Rewrite.exists_irreducible_descendant
  #print axioms Omega.Rewrite.irreducible_terminal_unique
  #print axioms Omega.Rewrite.irreducible_terminal_unique_unbounded
  #print axioms Omega.Rewrite.irreducible_terminal_eq_fold
  #print axioms Omega.Rewrite.step_confluent
  #print axioms Omega.Rewrite.step_locallyConfluent
  #print axioms Omega.globalDefect_eq_defectChain
  #print axioms Omega.Graph.acceptsWord_goldenMean_iff_no11
  #print axioms Omega.SPG.spg_decidableClopen
  #print axioms Omega.SPG.scanError_eq_sum_boundary
  #print axioms Omega.SPG.prefixScanError_eq_sum_boundary
  #print axioms Omega.SPG.prefixScanError_eq_zero_of_prefixEvent
  #print axioms Omega.SPG.scanErrorMeasure_observableEvent_eq_zero
  #print axioms Omega.SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty
  #print axioms Omega.SPG.scanErrorMeasure_eq_zero_of_observablePure
  #print axioms Omega.SPG.scanErrorMeasure_eq_sum_boundary
  #print axioms Omega.SPG.prefixScanErrorMeasure_eq_sum_boundary
  #print axioms Omega.SPG.prefixScanErrorMeasure_eq_zero_of_prefixEvent
  #print axioms Omega.SPG.scanErrorMeasure_toMeasure_eq_scanError
  #print axioms Omega.SPG.prefixScanErrorMeasure_toMeasure_eq_prefixScanError
  #print axioms Omega.Frontier.fullGeneration_certifies
  #print axioms Omega.Frontier.scanError_hasCertificate
  #print axioms Omega.Frontier.prefixScanError_hasCertificate
  #print axioms Omega.Frontier.localDefect_hasCertificate
  #print axioms Omega.Frontier.globalDefect_hasCertificate
  #print axioms Omega.Frontier.rewriteStep_hasCertificate
  #print axioms Omega.Frontier.stableIrreducible_hasCertificate
  #print axioms Omega.Frontier.fold_hasCertificate
  #print axioms Omega.Frontier.observableZeroScan_hasCertificate
  #print axioms Omega.Frontier.generatedDefectCertificate_sound
  #print axioms Omega.Frontier.scanError_certificate_sound
  #print axioms Omega.Frontier.prefixScanError_certificate_sound
  #print axioms Omega.Frontier.rewriteStep_certificate_value
  #print axioms Omega.Frontier.foldCertificate_idempotent
  #print axioms Omega.Frontier.foldCertificate_inFiber
  #print axioms Omega.Frontier.observableZeroScan_certificate_sound
  #print axioms Omega.Frontier.prefixZeroScan_certificate_sound
  #print axioms Omega.Frontier.fold_idempotent
  #print axioms Omega.Frontier.fold_fixedOnStable
  #print axioms Omega.Frontier.fold_surjective
  #print axioms Omega.Frontier.fold_fiber_nonempty
  #print axioms Omega.Frontier.fold_fiber_unrank_sound
  #print axioms Omega.Frontier.fold_choosePreimage_sound
  #print axioms Omega.Frontier.fold_choosePreimage_inFiber
  #print axioms Omega.Frontier.fold_unrank_rankOfEq
  #print axioms Omega.Frontier.fold_orderIndependent
  #print axioms Omega.Frontier.rewrite_stronglyTerminating
  #print axioms Omega.Frontier.rewrite_confluent
  #print axioms Omega.Frontier.rewrite_locallyConfluent
  #print axioms Omega.Frontier.rewrite_valueInvariant
  #print axioms Omega.Frontier.rewrite_irreducible_iff_stableCfg
  #print axioms Omega.Frontier.rewrite_irreducible_sameValue_unique
  #print axioms Omega.Frontier.rewrite_fold_irreducible
  #print axioms Omega.Frontier.rewrite_terminal_exists
  #print axioms Omega.Frontier.prefixEvent_pure_discrete
  #print axioms Omega.Frontier.prefixEvent_pure_measure
  #print axioms Omega.Frontier.rewrite_terminal_equals_fold
  #print axioms Omega.Frontier.inverseLimitPresentation
  #print axioms Omega.Frontier.localDefect_as_globalStep
  #print axioms Omega.Frontier.globalDefect_recursive
  #print axioms Omega.Frontier.defect_telescope
  #print axioms Omega.Frontier.stable_implies_sofic
  #print axioms Omega.Frontier.sofic_implies_stable
  #print axioms Omega.Frontier.stableLanguage_set_sofic
  #print axioms Omega.Frontier.prefixBall_is_cylinder
  #print axioms Omega.Frontier.cylinder_is_closedBall
  #print axioms Omega.Frontier.prefixBall_is_closedBall
  #print axioms Omega.Frontier.prefixEvent_decidableClopen
  #print axioms Omega.Frontier.prefixDetermined_clopen
  #print axioms Omega.Frontier.prefixDetermined_iff_fromWordSet
  #print axioms Omega.Frontier.prefixEvent_observablePure_measure
  #print axioms Omega.Frontier.observableEvent_boundaryEmpty_discrete
  #print axioms Omega.Frontier.observableEvent_zero_discrete
  #print axioms Omega.Frontier.scanError_boundary_decomposition_discrete
  #print axioms Omega.Frontier.scanError_boundary_mass_bound_discrete
  #print axioms Omega.Frontier.scanError_boundary_card_bound_discrete
  #print axioms Omega.Frontier.scanError_zero_of_boundaryEmpty_discrete
  #print axioms Omega.Frontier.observableEvent_observablePure_measure
  #print axioms Omega.Frontier.observableEvent_boundaryEmpty_measure
  #print axioms Omega.Frontier.observableEvent_zero_measure
  #print axioms Omega.Frontier.prefixEvent_boundaryEmpty_discrete
  #print axioms Omega.Frontier.prefixEvent_zero_discrete
  #print axioms Omega.Frontier.prefixScanError_zero_of_boundaryEmpty_discrete
  #print axioms Omega.Frontier.observablePure_iff_boundaryEmpty_measure
  #print axioms Omega.Frontier.scanError_zero_iff_observablePure_measure
  #print axioms Omega.Frontier.scanError_zero_iff_boundaryEmpty_measure
  #print axioms Omega.Frontier.prefixEvent_boundaryEmpty_measure
  #print axioms Omega.Frontier.prefixEvent_zero_measure
  #print axioms Omega.Frontier.prefixObservablePure_iff_boundaryEmpty_measure
  #print axioms Omega.Frontier.prefixScanError_zero_iff_observablePure_measure
  #print axioms Omega.Frontier.prefixScanError_zero_iff_boundaryEmpty_measure
  #print axioms Omega.Frontier.prefixObservablePure_zero_measure
  #print axioms Omega.Frontier.scanError_measure_boundary_decomposition
  #print axioms Omega.Frontier.scanError_measure_boundary_mass_bound
  #print axioms Omega.Frontier.scanError_measure_boundary_card_bound
  #print axioms Omega.Frontier.scanError_zero_of_boundaryEmpty_measure
  #print axioms Omega.Frontier.scanError_measure_discrete_bridge
  #print axioms Omega.Frontier.boundaryCells_measure_discrete_bridge
  #print axioms Omega.Frontier.prefixBoundaryCells_measure_discrete_bridge
  #print axioms Omega.Frontier.observableEvent_zero_measure_discrete_bridge
  #print axioms Omega.Frontier.prefixScanError_measure_discrete_bridge
  #print axioms Omega.Frontier.observablePure_zero_measure
  #print axioms Omega.Frontier.prefixScanError_measure_boundary_decomposition
  #print axioms Omega.Frontier.prefixScanError_measure_boundary_mass_bound
  #print axioms Omega.Frontier.prefixScanError_measure_boundary_card_bound
  #print axioms Omega.Frontier.prefixScanError_zero_of_boundaryEmpty_measure
  #print axioms Omega.Frontier.prefixEvent_pure_measure_discrete_bridge
  #print axioms Omega.Frontier.RewriteStepCertificate.value_preserved
  #print axioms Omega.Frontier.FoldCertificate.idempotent
  #print axioms Omega.Frontier.PrefixZeroScanCertificate.canonical
  #print axioms Omega.SPG.ObservablePure
  #print axioms Omega.SPG.observablePure_iff_boundaryCells_eq_empty
  #print axioms Omega.SPG.scanError_eq_zero_iff_observablePure
  #print axioms Omega.SPG.scanError_eq_zero_iff_boundaryCells_eq_empty
  #print axioms Omega.SPG.scanError_compl
  #print axioms Omega.SPG.scanError_empty
  #print axioms Omega.SPG.scanError_univ
  #print axioms Omega.SPG.scanErrorMeasure_compl
  #print axioms Omega.SPG.scanErrorMeasure_empty
  #print axioms Omega.SPG.scanErrorMeasure_univ
  #print axioms Omega.Frontier.scanError_compl_discrete
  #print axioms Omega.Frontier.scanError_empty_discrete
  #print axioms Omega.Frontier.scanError_univ_discrete
  #print axioms Omega.Frontier.observableEvent_observablePure_discrete
  #print axioms Omega.Frontier.observablePure_iff_boundaryEmpty_discrete
  #print axioms Omega.Frontier.scanError_zero_iff_observablePure_discrete
  #print axioms Omega.Frontier.scanError_zero_iff_boundaryEmpty_discrete
  #print axioms Omega.Frontier.scanError_compl_measure
  #print axioms Omega.Frontier.scanError_empty_measure
  #print axioms Omega.Frontier.scanError_univ_measure
  #print axioms Omega.SPG.prefixScanError_eq_zero_iff_observablePure
  #print axioms Omega.SPG.prefixScanError_eq_zero_iff_boundaryCells_eq_empty
  #print axioms Omega.SPG.prefixScanError_compl
  #print axioms Omega.SPG.prefixScanError_empty
  #print axioms Omega.SPG.prefixScanError_univ
  #print axioms Omega.SPG.observablePureMeasure_toMeasure_iff_observablePure
  #print axioms Omega.SPG.prefixScanErrorMeasure_compl
  #print axioms Omega.SPG.prefixScanErrorMeasure_empty
  #print axioms Omega.SPG.prefixScanErrorMeasure_univ
  #print axioms Omega.SPG.sum_min_le_min_sum
  #print axioms Omega.Frontier.prefixEvent_observablePure_discrete
  #print axioms Omega.Frontier.prefixScanError_zero_iff_observablePure_discrete
  #print axioms Omega.Frontier.prefixScanError_zero_iff_boundaryEmpty_discrete
  #print axioms Omega.Frontier.prefixScanError_compl_discrete
  #print axioms Omega.Frontier.prefixScanError_empty_discrete
  #print axioms Omega.Frontier.prefixScanError_univ_discrete
  #print axioms Omega.Frontier.observablePure_measure_discrete_bridge
  #print axioms Omega.Frontier.prefixScanError_compl_measure
  #print axioms Omega.Frontier.prefixScanError_empty_measure
  #print axioms Omega.Frontier.prefixScanError_univ_measure
  #print axioms Omega.SPG.scanError_antitone_of_refines
  #print axioms Omega.SPG.prefixScanError_antitone
  #print axioms Omega.Frontier.scanError_antitone_of_refines
  #print axioms Omega.Frontier.prefixScanError_antitone
  #print axioms Omega.SPG.cellEventMass_sum_eq_setMass
  #print axioms Omega.SPG.cellComplMass_sum_eq_setMass_compl
  #print axioms Omega.SPG.cellMass_sum_eq_setMass_univ
  #print axioms Omega.SPG.scanError_le_min_setMass
  #print axioms Omega.SPG.scanErrorMeasure_le_min
  #print axioms Omega.Frontier.cellEventMass_partition
  #print axioms Omega.Frontier.cellComplMass_partition
  #print axioms Omega.Frontier.scanError_bayes_bound
  #print axioms Omega.Frontier.scanError_measure_bayes_bound
  #print axioms Omega.SPG.boundaryCylinderCount_eq_zero_iff_observablePure
  #print axioms Omega.SPG.scanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero
  #print axioms Omega.SPG.boundaryCylinderCount_observableEvent_eq_zero
  #print axioms Omega.SPG.boundaryCylinderCount_toMeasure_eq
  #print axioms Omega.SPG.prefixBoundaryCylinderCount_eq_zero_iff_observablePure
  #print axioms Omega.SPG.prefixScanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero
  #print axioms Omega.SPG.prefixBoundaryCylinderCount_prefixEvent_eq_zero
  #print axioms Omega.SPG.prefixBoundaryCylinderCount_toMeasure_eq
  #print axioms Omega.Frontier.stableSyntax_card_eq_fibonacci
  #print axioms Omega.Frontier.stableSyntax_card_recurrence
  #print axioms Omega.Frontier.stableWord_zeckendorf_valid
  #print axioms Omega.Frontier.stableValue_eq_fibonacci_weighted_sum
  #print axioms Omega.Frontier.stableValue_eq_zeckRep_sum
  -- Note: above has type ((zeckRep x).1.map fib).sum = stableValue x
  #print axioms Omega.Frontier.fold_fiber_card_pos
  #print axioms Omega.Frontier.boundaryCylinderCount_zero_iff_pure_measure
  #print axioms Omega.Frontier.scanError_zero_iff_boundaryCylinderCount_zero_measure
  #print axioms Omega.Frontier.boundaryCylinderCount_observableEvent_zero
  #print axioms Omega.Frontier.prefixBoundaryCylinderCount_prefixEvent_zero
  #print axioms Omega.Frontier.prefixBoundaryCylinderCount_zero_iff_pure_measure
  #print axioms Omega.Frontier.prefixScanError_zero_iff_boundaryCylinderCount_zero_measure
  #print axioms Omega.Frontier.boundaryCylinderCount_measure_discrete_bridge
  #print axioms Omega.Frontier.prefixBoundaryCylinderCount_measure_discrete_bridge
  #print axioms Omega.Frontier.scanError_measure_antitone_via_bridge
  #print axioms Omega.Frontier.prefixScanError_measure_antitone_via_bridge
  #print axioms Omega.SPG.cellEventMass_add_cellComplMass_eq_cellMass
  #print axioms Omega.Frontier.stableValue_injective
  #print axioms Omega.Frontier.stableValue_ofNat_roundtrip
  #print axioms Omega.Frontier.fold_ofNat_roundtrip
  #print axioms Omega.Frontier.cellEventMass_add_cellComplMass_partition
  -- Carry Defect (Plan 3)
  #print axioms Omega.X.paperFib_add_fib_eq
  #print axioms Omega.X.fib_sub_eq
  #print axioms Omega.X.fib_lt_paperFib_succ
  #print axioms Omega.X.stableValue_restrict_stableAdd_carry
  #print axioms Omega.X.restrict_stableAdd_carry_defect
  #print axioms Omega.X.carryElement_m6_value
  #print axioms Omega.X.carryElement_m5_value
  #print axioms Omega.X.carryElement_m7_value
  #print axioms Omega.X.carryElement_ne_zero
  -- FiberFusion (Plan 7): lem:pom-fib-fusion-submultiplicativity
  #print axioms Omega.X.fib_fusion
  #print axioms Omega.X.fib_prod_lt_fib_fusion
  #print axioms Omega.X.fib_fusion_lt_fib_sum
  #print axioms Omega.X.fib_prod_lt_fib_sum
  -- FiberFusion (Plan 7): cor:pom-fib-component-fusion-gain
  #print axioms Omega.X.fib_component_fusion_lt
  #print axioms Omega.X.fib_component_fusion_gain
  #print axioms Omega.X.fib_component_fusion_gain_lower
  #print axioms Omega.X.fib_component_fusion_gain_ge
  -- MaxFiber (Plan 8): def:pom-top-fiber-spectrum, thm:pom-max-fiber (partial: 递推上界), cor:pom-D-rec
  #print axioms Omega.X.maxFiberMultiplicity
  #print axioms Omega.X.maxFiberMultiplicity_achieved
  #print axioms Omega.X.fiberMultiplicity_le_max
  #print axioms Omega.X.maxFiberMultiplicity_pos
  -- thm:pom-max-fiber: 递推上界 D(m+2) ≤ D(m+1) + D(m)
  #print axioms Omega.X.maxFiberMultiplicity_le_add
  -- Zeckendorf carry preservation (auxiliary)
  #print axioms Omega.ofNat_add_paperFib
  -- Zeckendorf distinctness (auxiliary)
  #print axioms Omega.ofNat_ne_of_shift
  -- weight & snoc helpers (auxiliary)
  #print axioms Omega.X.weight_expand
  #print axioms Omega.X.weight_lt_paperFib
  #print axioms Omega.X.snoc_truncate_last
  -- restrict helpers (auxiliary)
  #print axioms Omega.restrict_ofNat
  #print axioms Omega.restrict_Fold_snoc_false
  -- fib membership bound (auxiliary)
  #print axioms Omega.X.fib_le_of_mem_zeckendorf
  -- cor:pom-D-rec: base values D_0 .. D_9 (native_decide)
  #print axioms Omega.X.maxFiberMultiplicity_zero
  #print axioms Omega.X.maxFiberMultiplicity_one
  #print axioms Omega.X.maxFiberMultiplicity_two
  #print axioms Omega.X.maxFiberMultiplicity_three
  #print axioms Omega.X.maxFiberMultiplicity_four
  #print axioms Omega.X.maxFiberMultiplicity_five
  #print axioms Omega.X.maxFiberMultiplicity_six
  #print axioms Omega.X.maxFiberMultiplicity_seven
  #print axioms Omega.X.maxFiberMultiplicity_eight
  #print axioms Omega.X.maxFiberMultiplicity_nine
  #print axioms Omega.X.maxFiberMultiplicity_ten
  -- ModularTower (Plan 4): thm:pom-modular-tower
  #print axioms Omega.X.modularProject_eq_restrict
  #print axioms Omega.X.modularProject_stableAdd_carry
  #print axioms Omega.X.stableValue_modularProject_stableMul
  #print axioms Omega.X.stableValue_restrict_stableMul
  #print axioms Omega.X.restrict_comp_restrict
  #print axioms Omega.X.tower_compatible
  #print axioms Omega.X.restrict_tower_transitivity
  #print axioms Omega.X.modularProject_stableZero
  #print axioms Omega.X.stableValue_modularProject_stableAdd_carry
  #print axioms Omega.X.stableValue_modularProject_compose
  #print axioms Omega.X.carryIndicator_comm
  #print axioms Omega.X.modularProject_tower_surjective
  -- TransferMatrix (Plan 19): def:golden-mean-adjacency-matrix, thm:fold-suite item 3, entries + Cayley-Hamilton
  #print axioms Omega.Graph.goldenMeanAdjacency
  #print axioms Omega.Graph.goldenMeanAdjacency_entry_00
  #print axioms Omega.Graph.goldenMeanAdjacency_entry_01
  #print axioms Omega.Graph.goldenMeanAdjacency_entry_10
  #print axioms Omega.Graph.goldenMeanAdjacency_entry_11
  #print axioms Omega.Graph.goldenMeanAdjacency_sq
  #print axioms Omega.Graph.goldenMeanAdjacency_trace
  #print axioms Omega.Graph.goldenMeanAdjacency_det
  -- InverseLimitTopology (Plan 23): thm:fold-suite item 3 + thm:inverse-limit-golden (complete)
  #print axioms Omega.X.isClosed_no11Inf
  #print axioms Omega.X.instMetricSpaceXInfinity
  #print axioms Omega.X.instInhabitedXInfinity
  #print axioms Omega.X.instInfiniteXInfinity
  -- ShiftDynamics (Plan 20前置): cor:pom-shift-conjugacy-on-godel-image + sofic shift 动力系统基础
  #print axioms Omega.X.shift
  #print axioms Omega.X.continuous_shift
  #print axioms Omega.X.shift_surjective
  #print axioms Omega.X.shift_val
  -- Round 9: S_2 矩谱基值 (prop:pom-s2-recurrence)
  #print axioms Omega.cMomentSum
  #print axioms Omega.cMomentSum_eq
  #print axioms Omega.momentSum_two_zero
  #print axioms Omega.momentSum_two_one
  #print axioms Omega.momentSum_two_two
  #print axioms Omega.momentSum_two_three
  #print axioms Omega.momentSum_two_four
  #print axioms Omega.momentSum_two_five
  #print axioms Omega.momentSum_two_six
  -- Round 10: CollisionKernel (Plan 10, partial): prop:pom-s2-recurrence
  #print axioms Omega.collisionKernel2
  #print axioms Omega.collisionKernel2_trace
  #print axioms Omega.collisionKernel2_det
  #print axioms Omega.collisionKernel2_cayley_hamilton
  #print axioms Omega.momentSum_two_recurrence_verified
  -- Round 11: Fibonacci 多项式 (def:pom-fibonacci-polynomial, thm:pom-path-indset-poly-closed 部分)
  #print axioms Omega.fibPoly
  #print axioms Omega.fibPoly_eval_one
  #print axioms Omega.pathIndSetPoly
  #print axioms Omega.pathIndSetPoly_eval_one
  -- Round 12: Cauchy-Schwarz 碰撞界 + S_q 单调性 (thm:fold-collision-convex-lower-bounds)
  #print axioms Omega.momentSum_mono_q
  #print axioms Omega.momentSum_two_ge_pow
  #print axioms Omega.momentSum_ge_card
  #print axioms Omega.momentSum_cauchy_schwarz
  -- Round 13: S_3 基值 + A_3 碰撞核矩阵 (prop:pom-s3-recurrence)
  #print axioms Omega.momentSum_three_zero
  #print axioms Omega.momentSum_three_one
  #print axioms Omega.momentSum_three_two
  #print axioms Omega.momentSum_three_three
  #print axioms Omega.momentSum_three_four
  #print axioms Omega.momentSum_three_five
  #print axioms Omega.momentSum_three_six
  #print axioms Omega.momentSum_three_recurrence_verified
  #print axioms Omega.collisionKernel3
  #print axioms Omega.collisionKernel3_trace
  #print axioms Omega.collisionKernel3_det
  #print axioms Omega.collisionKernel3_cayley_hamilton

The goal of phase 0/1 is that these core theorems use no project-defined axioms.
-/

def coreAuditTargets : List String :=
  [ "Omega.paperFib_recurrence"
  , "Omega.no11_truncate"
  , "Omega.X.restrict"
  , "Omega.X.card_eq_paperFib_succ"
  , "Omega.X.zeckIndices_isZeckendorfRep"
  , "Omega.X.stableValue_eq_sum_fib_zeckIndices"
  , "Omega.Fold_stable"
  , "Omega.Fold_idempotent"
  , "Omega.X.fiber_nonempty"
  , "Omega.X.rank_unrank"
  , "Omega.X.Fold_unrankWord"
  , "Omega.X.inverseLimitEquiv"
  , "Omega.Rewrite.step_value"
  , "Omega.Rewrite.step_stronglyTerminating"
  , "Omega.Rewrite.irreducible_supported_eq_iota_normalPrefix"
  , "Omega.Rewrite.irreducible_eq_of_normalPrefix_eq"
  , "Omega.Rewrite.reflTransGen_normalPrefix"
  , "Omega.Rewrite.exists_irreducible_descendant"
  , "Omega.Rewrite.irreducible_terminal_unique"
  , "Omega.Rewrite.irreducible_terminal_unique_unbounded"
  , "Omega.Rewrite.irreducible_terminal_eq_fold"
  , "Omega.Rewrite.step_confluent"
  , "Omega.Rewrite.step_locallyConfluent"
  , "Omega.globalDefect_eq_defectChain"
  , "Omega.Graph.acceptsWord_goldenMean_iff_no11"
  , "Omega.SPG.spg_decidableClopen"
  , "Omega.SPG.scanError_eq_sum_boundary"
  , "Omega.SPG.prefixScanError_eq_sum_boundary"
  , "Omega.SPG.prefixScanError_eq_zero_of_prefixEvent"
  , "Omega.SPG.scanErrorMeasure_observableEvent_eq_zero"
  , "Omega.SPG.observablePureMeasure_iff_boundaryCellsMeasure_eq_empty"
  , "Omega.SPG.scanErrorMeasure_eq_zero_of_observablePure"
  , "Omega.SPG.scanErrorMeasure_eq_sum_boundary"
  , "Omega.SPG.prefixScanErrorMeasure_eq_sum_boundary"
  , "Omega.SPG.prefixScanErrorMeasure_eq_zero_of_prefixEvent"
  , "Omega.SPG.scanErrorMeasure_toMeasure_eq_scanError"
  , "Omega.SPG.prefixScanErrorMeasure_toMeasure_eq_prefixScanError"
  , "Omega.Frontier.fullGeneration_certifies"
  , "Omega.Frontier.scanError_hasCertificate"
  , "Omega.Frontier.prefixScanError_hasCertificate"
  , "Omega.Frontier.localDefect_hasCertificate"
  , "Omega.Frontier.globalDefect_hasCertificate"
  , "Omega.Frontier.rewriteStep_hasCertificate"
  , "Omega.Frontier.stableIrreducible_hasCertificate"
  , "Omega.Frontier.fold_hasCertificate"
  , "Omega.Frontier.observableZeroScan_hasCertificate"
  , "Omega.Frontier.generatedDefectCertificate_sound"
  , "Omega.Frontier.scanError_certificate_sound"
  , "Omega.Frontier.prefixScanError_certificate_sound"
  , "Omega.Frontier.rewriteStep_certificate_value"
  , "Omega.Frontier.foldCertificate_idempotent"
  , "Omega.Frontier.foldCertificate_inFiber"
  , "Omega.Frontier.observableZeroScan_certificate_sound"
  , "Omega.Frontier.prefixZeroScan_certificate_sound"
  , "Omega.Frontier.fold_idempotent"
  , "Omega.Frontier.fold_fixedOnStable"
  , "Omega.Frontier.fold_surjective"
  , "Omega.Frontier.fold_fiber_nonempty"
  , "Omega.Frontier.fold_fiber_unrank_sound"
  , "Omega.Frontier.fold_choosePreimage_sound"
  , "Omega.Frontier.fold_choosePreimage_inFiber"
  , "Omega.Frontier.fold_unrank_rankOfEq"
  , "Omega.Frontier.fold_orderIndependent"
  , "Omega.Frontier.rewrite_stronglyTerminating"
  , "Omega.Frontier.rewrite_confluent"
  , "Omega.Frontier.rewrite_locallyConfluent"
  , "Omega.Frontier.rewrite_valueInvariant"
  , "Omega.Frontier.rewrite_irreducible_iff_stableCfg"
  , "Omega.Frontier.rewrite_irreducible_sameValue_unique"
  , "Omega.Frontier.rewrite_fold_irreducible"
  , "Omega.Frontier.rewrite_terminal_exists"
  , "Omega.Frontier.prefixEvent_pure_discrete"
  , "Omega.Frontier.prefixEvent_pure_measure"
  , "Omega.Frontier.rewrite_terminal_equals_fold"
  , "Omega.Frontier.inverseLimitPresentation"
  , "Omega.Frontier.localDefect_as_globalStep"
  , "Omega.Frontier.globalDefect_recursive"
  , "Omega.Frontier.defect_telescope"
  , "Omega.Frontier.stable_implies_sofic"
  , "Omega.Frontier.sofic_implies_stable"
  , "Omega.Frontier.stableLanguage_set_sofic"
  , "Omega.Frontier.prefixBall_is_cylinder"
  , "Omega.Frontier.cylinder_is_closedBall"
  , "Omega.Frontier.prefixBall_is_closedBall"
  , "Omega.Frontier.prefixEvent_decidableClopen"
  , "Omega.Frontier.prefixDetermined_clopen"
  , "Omega.Frontier.prefixDetermined_iff_fromWordSet"
  , "Omega.Frontier.prefixEvent_observablePure_measure"
  , "Omega.Frontier.observableEvent_boundaryEmpty_discrete"
  , "Omega.Frontier.observableEvent_zero_discrete"
  , "Omega.Frontier.scanError_boundary_decomposition_discrete"
  , "Omega.Frontier.scanError_boundary_mass_bound_discrete"
  , "Omega.Frontier.scanError_boundary_card_bound_discrete"
  , "Omega.Frontier.scanError_zero_of_boundaryEmpty_discrete"
  , "Omega.Frontier.observableEvent_observablePure_measure"
  , "Omega.Frontier.observableEvent_boundaryEmpty_measure"
  , "Omega.Frontier.observableEvent_zero_measure"
  , "Omega.Frontier.prefixEvent_boundaryEmpty_discrete"
  , "Omega.Frontier.prefixEvent_zero_discrete"
  , "Omega.Frontier.prefixScanError_zero_of_boundaryEmpty_discrete"
  , "Omega.Frontier.observablePure_iff_boundaryEmpty_measure"
  , "Omega.Frontier.scanError_zero_iff_observablePure_measure"
  , "Omega.Frontier.scanError_zero_iff_boundaryEmpty_measure"
  , "Omega.Frontier.prefixEvent_boundaryEmpty_measure"
  , "Omega.Frontier.prefixEvent_zero_measure"
  , "Omega.Frontier.prefixObservablePure_iff_boundaryEmpty_measure"
  , "Omega.Frontier.prefixScanError_zero_iff_observablePure_measure"
  , "Omega.Frontier.prefixScanError_zero_iff_boundaryEmpty_measure"
  , "Omega.Frontier.prefixObservablePure_zero_measure"
  , "Omega.Frontier.scanError_measure_boundary_decomposition"
  , "Omega.Frontier.scanError_measure_boundary_mass_bound"
  , "Omega.Frontier.scanError_measure_boundary_card_bound"
  , "Omega.Frontier.scanError_zero_of_boundaryEmpty_measure"
  , "Omega.Frontier.scanError_measure_discrete_bridge"
  , "Omega.Frontier.boundaryCells_measure_discrete_bridge"
  , "Omega.Frontier.prefixBoundaryCells_measure_discrete_bridge"
  , "Omega.Frontier.observableEvent_zero_measure_discrete_bridge"
  , "Omega.Frontier.prefixScanError_measure_discrete_bridge"
  , "Omega.Frontier.observablePure_zero_measure"
  , "Omega.Frontier.prefixScanError_measure_boundary_decomposition"
  , "Omega.Frontier.prefixScanError_measure_boundary_mass_bound"
  , "Omega.Frontier.prefixScanError_measure_boundary_card_bound"
  , "Omega.Frontier.prefixScanError_zero_of_boundaryEmpty_measure"
  , "Omega.Frontier.prefixEvent_pure_measure_discrete_bridge"
  , "Omega.Frontier.RewriteStepCertificate.value_preserved"
  , "Omega.Frontier.FoldCertificate.idempotent"
  , "Omega.Frontier.PrefixZeroScanCertificate.canonical"
  , "Omega.SPG.scanError_compl"
  , "Omega.SPG.scanError_empty"
  , "Omega.SPG.scanError_univ"
  , "Omega.SPG.observablePure_iff_boundaryCells_eq_empty"
  , "Omega.SPG.scanError_eq_zero_iff_observablePure"
  , "Omega.SPG.scanError_eq_zero_iff_boundaryCells_eq_empty"
  , "Omega.SPG.scanErrorMeasure_compl"
  , "Omega.SPG.scanErrorMeasure_empty"
  , "Omega.SPG.scanErrorMeasure_univ"
  , "Omega.Frontier.scanError_compl_discrete"
  , "Omega.Frontier.scanError_empty_discrete"
  , "Omega.Frontier.scanError_univ_discrete"
  , "Omega.Frontier.observableEvent_observablePure_discrete"
  , "Omega.Frontier.observablePure_iff_boundaryEmpty_discrete"
  , "Omega.Frontier.scanError_zero_iff_observablePure_discrete"
  , "Omega.Frontier.scanError_zero_iff_boundaryEmpty_discrete"
  , "Omega.Frontier.scanError_compl_measure"
  , "Omega.Frontier.scanError_empty_measure"
  , "Omega.Frontier.scanError_univ_measure"
  , "Omega.SPG.prefixScanError_eq_zero_iff_observablePure"
  , "Omega.SPG.prefixScanError_eq_zero_iff_boundaryCells_eq_empty"
  , "Omega.SPG.prefixScanError_compl"
  , "Omega.SPG.prefixScanError_empty"
  , "Omega.SPG.prefixScanError_univ"
  , "Omega.SPG.observablePureMeasure_toMeasure_iff_observablePure"
  , "Omega.SPG.prefixScanErrorMeasure_compl"
  , "Omega.SPG.prefixScanErrorMeasure_empty"
  , "Omega.SPG.prefixScanErrorMeasure_univ"
  , "Omega.SPG.sum_min_le_min_sum"
  , "Omega.Frontier.prefixEvent_observablePure_discrete"
  , "Omega.Frontier.prefixScanError_zero_iff_observablePure_discrete"
  , "Omega.Frontier.prefixScanError_zero_iff_boundaryEmpty_discrete"
  , "Omega.Frontier.prefixScanError_compl_discrete"
  , "Omega.Frontier.prefixScanError_empty_discrete"
  , "Omega.Frontier.prefixScanError_univ_discrete"
  , "Omega.Frontier.observablePure_measure_discrete_bridge"
  , "Omega.Frontier.prefixScanError_compl_measure"
  , "Omega.Frontier.prefixScanError_empty_measure"
  , "Omega.Frontier.prefixScanError_univ_measure"
  , "Omega.SPG.scanError_antitone_of_refines"
  , "Omega.SPG.prefixScanError_antitone"
  , "Omega.Frontier.scanError_antitone_of_refines"
  , "Omega.Frontier.prefixScanError_antitone"
  , "Omega.SPG.cellEventMass_sum_eq_setMass"
  , "Omega.SPG.cellComplMass_sum_eq_setMass_compl"
  , "Omega.SPG.cellMass_sum_eq_setMass_univ"
  , "Omega.SPG.scanError_le_min_setMass"
  , "Omega.SPG.scanErrorMeasure_le_min"
  , "Omega.Frontier.cellEventMass_partition"
  , "Omega.Frontier.cellComplMass_partition"
  , "Omega.Frontier.scanError_bayes_bound"
  , "Omega.Frontier.scanError_measure_bayes_bound"
  , "Omega.SPG.boundaryCylinderCount_eq_zero_iff_observablePure"
  , "Omega.SPG.scanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero"
  , "Omega.SPG.boundaryCylinderCount_observableEvent_eq_zero"
  , "Omega.SPG.boundaryCylinderCount_toMeasure_eq"
  , "Omega.SPG.prefixBoundaryCylinderCount_eq_zero_iff_observablePure"
  , "Omega.SPG.prefixScanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero"
  , "Omega.SPG.prefixBoundaryCylinderCount_prefixEvent_eq_zero"
  , "Omega.SPG.prefixBoundaryCylinderCount_toMeasure_eq"
  , "Omega.Frontier.stableSyntax_card_eq_fibonacci"
  , "Omega.Frontier.stableSyntax_card_recurrence"
  , "Omega.Frontier.stableWord_zeckendorf_valid"
  , "Omega.Frontier.stableValue_eq_fibonacci_weighted_sum"
  , "Omega.Frontier.stableValue_eq_zeckRep_sum"
  , "Omega.Frontier.fold_fiber_card_pos"
  , "Omega.Frontier.boundaryCylinderCount_zero_iff_pure_measure"
  , "Omega.Frontier.scanError_zero_iff_boundaryCylinderCount_zero_measure"
  , "Omega.Frontier.boundaryCylinderCount_observableEvent_zero"
  , "Omega.Frontier.prefixBoundaryCylinderCount_prefixEvent_zero"
  , "Omega.Frontier.prefixBoundaryCylinderCount_zero_iff_pure_measure"
  , "Omega.Frontier.prefixScanError_zero_iff_boundaryCylinderCount_zero_measure"
  , "Omega.Frontier.boundaryCylinderCount_measure_discrete_bridge"
  , "Omega.Frontier.prefixBoundaryCylinderCount_measure_discrete_bridge"
  , "Omega.Frontier.scanError_measure_antitone_via_bridge"
  , "Omega.Frontier.prefixScanError_measure_antitone_via_bridge"
  , "Omega.SPG.cellEventMass_add_cellComplMass_eq_cellMass"
  , "Omega.Frontier.stableValue_injective"
  , "Omega.Frontier.stableValue_ofNat_roundtrip"
  , "Omega.Frontier.fold_ofNat_roundtrip"
  , "Omega.Frontier.cellEventMass_add_cellComplMass_partition"
  -- Carry Defect (Plan 3)
  , "Omega.X.paperFib_add_fib_eq"
  , "Omega.X.fib_sub_eq"
  , "Omega.X.fib_lt_paperFib_succ"
  , "Omega.X.stableValue_restrict_stableAdd_carry"
  , "Omega.X.restrict_stableAdd_carry_defect"
  , "Omega.X.carryElement_m6_value"
  , "Omega.X.carryElement_m5_value"
  , "Omega.X.carryElement_m7_value"
  , "Omega.X.carryElement_ne_zero"
  -- Stable value bound & arithmetic
  , "Omega.stableValue_lt_paperFib_succ"
  , "Omega.X.stableValueFin"
  , "Omega.X.stableValueFin_injective"
  , "Omega.X.stableAdd"
  , "Omega.X.stableAdd_comm"
  , "Omega.Frontier.stableValue_bounded"
  , "Omega.Frontier.stableAdd_commutative"
  -- Fibonacci infrastructure
  , "Omega.paperFib_pos"
  , "Omega.paperFib_mono"
  , "Omega.paperFib_le_succ"
  , "Omega.paperFib_le_add_right"
  -- Fiber partition & word cardinality
  , "Omega.X.Word_card"
  , "Omega.X.fiber_card_sum"
  , "Omega.X.fiber_card_sum_eq_pow"
  , "Omega.Frontier.word_card"
  , "Omega.Frontier.fiber_card_partition"
  , "Omega.Frontier.fiber_card_partition_pow"
  -- Phase 9: complement symmetry & cell-level measure bounds
  , "Omega.SPG.observablePure_compl"
  , "Omega.SPG.boundaryCells_compl"
  , "Omega.SPG.prefixBoundaryCells_compl"
  , "Omega.SPG.cellEventMeasure_le_cellMeasure"
  , "Omega.SPG.cellComplMeasure_le_cellMeasure"
  , "Omega.SPG.cellEventMeasure_add_cellComplMeasure_eq_cellMeasure"
  , "Omega.SPG.observablePureMeasure_compl"
  , "Omega.SPG.boundaryCellsMeasure_compl"
  , "Omega.SPG.boundaryCylinderCount_compl"
  , "Omega.SPG.prefixBoundaryCellsMeasure_compl"
  , "Omega.SPG.prefixBoundaryCylinderCount_compl"
  , "Omega.Frontier.observablePure_compl_symmetric_discrete"
  , "Omega.Frontier.boundaryCells_compl_symmetric_discrete"
  , "Omega.Frontier.prefixBoundaryCells_compl_symmetric_discrete"
  , "Omega.Frontier.observablePure_compl_symmetric_measure"
  , "Omega.Frontier.boundaryCells_compl_symmetric_measure"
  , "Omega.Frontier.boundaryCylinderCount_compl_symmetric_measure"
  , "Omega.Frontier.prefixBoundaryCells_compl_symmetric_measure"
  , "Omega.Frontier.prefixBoundaryCylinderCount_compl_symmetric_measure"
  , "Omega.Frontier.cellEventMeasure_le_cell"
  , "Omega.Frontier.cellComplMeasure_le_cell"
  , "Omega.Frontier.cellPartition_identity_measure"
  -- Plans 2-6: stable arithmetic, measure monotonicity, fiber multiplicity
  , "Omega.X.stableValue_ofNat_lt"
  , "Omega.X.stableValue_ofNat_mod"
  , "Omega.X.stableZero"
  , "Omega.X.stableValue_stableZero"
  , "Omega.X.stableAdd_zero_left"
  , "Omega.X.stableAdd_zero_right"
  , "Omega.X.stableAdd_assoc"
  , "Omega.X.fiberMultiplicity"
  , "Omega.X.fiberMultiplicity_pos"
  , "Omega.X.fiberMultiplicity_sum_eq_pow"
  , "Omega.SPG.PMF_sum_coe_eq_one"
  , "Omega.SPG.two_mul_scanError_le_one"
  , "Omega.SPG.setMass_add_setMass_compl"
  , "Omega.SPG.observableCell_measurableSet"
  , "Omega.SPG.observableCell_pairwiseDisjoint"
  , "Omega.SPG.observableCell_iUnion"
  , "Omega.SPG.cellEventMeasure_sum"
  , "Omega.SPG.cellComplMeasure_sum"
  , "Omega.SPG.cellMeasure_sum"
  , "Omega.SPG.cellEventMeasure_refines_sum_measure"
  , "Omega.SPG.scanErrorMeasure_antitone_of_refines"
  , "Omega.Frontier.scanError_bayes_half_bound"
  , "Omega.Frontier.scanError_measure_antitone_direct"
  , "Omega.Frontier.fiberMultiplicity_positive"
  , "Omega.Frontier.fiberMultiplicity_sum"
  -- FiberFusion (Plan 7)
  , "Omega.X.fib_fusion"
  , "Omega.X.fib_prod_lt_fib_fusion"
  , "Omega.X.fib_fusion_lt_fib_sum"
  , "Omega.X.fib_prod_lt_fib_sum"
  , "Omega.X.fib_component_fusion_lt"
  , "Omega.X.fib_component_fusion_gain"
  , "Omega.X.fib_component_fusion_gain_lower"
  , "Omega.X.fib_component_fusion_gain_ge"
  -- MaxFiber (Plan 8 partial): def:pom-top-fiber-spectrum, thm:pom-max-fiber (partial), cor:pom-D-rec
  , "Omega.X.maxFiberMultiplicity"
  , "Omega.X.maxFiberMultiplicity_achieved"
  , "Omega.X.fiberMultiplicity_le_max"
  , "Omega.X.maxFiberMultiplicity_pos"
  -- InverseLimitTopology (Plan 23): thm:fold-suite item 3 + thm:inverse-limit-golden (complete)
  , "Omega.X.isClosed_no11Inf"
  , "Omega.X.instMetricSpaceXInfinity"
  , "Omega.X.instInhabitedXInfinity"
  , "Omega.X.instInfiniteXInfinity"
  -- ShiftDynamics (Plan 20前置): shift 映射基础
  , "Omega.X.shift"
  , "Omega.X.continuous_shift"
  , "Omega.X.shift_surjective"
  , "Omega.X.shift_val"
  -- FibonacciField (Plan 2): Fibonacci 素数域
  , "Omega.X.stableMul_inv_of_prime"
  , "Omega.paperFib_three_prime"
  , "Omega.paperFib_four_prime"
  , "Omega.paperFib_six_prime"
  , "Omega.paperFib_eight_not_prime"
  , "Omega.paperFib_twelve_prime"
  -- Round 8: Fibonacci 界 + momentSum
  , "Omega.paperFib_le_pow"
  , "Omega.momentSum"
  , "Omega.momentSum_zero"
  , "Omega.momentSum_one"
  , "Omega.momentSum_le_max_pow"
  -- Round 9: S_2 矩谱基值 (prop:pom-s2-recurrence)
  , "Omega.cMomentSum"
  , "Omega.cMomentSum_eq"
  , "Omega.momentSum_two_zero"
  , "Omega.momentSum_two_one"
  , "Omega.momentSum_two_two"
  , "Omega.momentSum_two_three"
  , "Omega.momentSum_two_four"
  , "Omega.momentSum_two_five"
  , "Omega.momentSum_two_six"
  -- Round 11: Fibonacci 多项式 (def:pom-fibonacci-polynomial, thm:pom-path-indset-poly-closed 部分)
  , "Omega.fibPoly"
  , "Omega.fibPoly_eval_one"
  , "Omega.pathIndSetPoly"
  , "Omega.pathIndSetPoly_eval_one"
  -- Phase 17: MaxFiber 闭式定理 (thm:pom-max-fiber, cor:pom-D-rec)
  , "Omega.maxFiberMultiplicity_zero"
  , "Omega.maxFiberMultiplicity_two"
  , "Omega.maxFiberMultiplicity_four"
  , "Omega.maxFiberMultiplicity_six"
  , "Omega.maxFiberMultiplicity_eight"
  , "Omega.maxFiberMultiplicity_ten"
  , "Omega.maxFiberMultiplicity_three"
  , "Omega.maxFiberMultiplicity_five"
  , "Omega.maxFiberMultiplicity_seven"
  , "Omega.maxFiberMultiplicity_nine"
  , "Omega.maxFiberMultiplicity_even"
  , "Omega.maxFiberMultiplicity_odd"
  , "Omega.maxFiberMultiplicity_le_add" ]

end Omega.Audit
