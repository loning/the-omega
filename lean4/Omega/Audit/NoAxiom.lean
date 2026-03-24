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
import Omega.Folding.FiberSpectrum
import Omega.Folding.HankelSpectrum
import Omega.Folding.FiberArithmeticProperties
import Omega.Folding.Entropy
import Omega.Audit.SourceMap

namespace Omega.Audit

/-
Run these commands manually during audit:

  #print axioms Omega.no11_truncate
  #print axioms Omega.X.restrict
  #print axioms Omega.fib_succ_succ'
  #print axioms Omega.X.card_eq_fib
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
  #print axioms Omega.X.fib_succ_add_fib_eq
  #print axioms Omega.X.fib_sub_eq
  #print axioms Omega.X.fib_lt_fib_succ_succ
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
  -- ofNat_add_fib, weight_lt_fib are private in MaxFiber.lean
  -- Zeckendorf distinctness (auxiliary)
  #print axioms Omega.ofNat_ne_of_shift
  -- weight & snoc helpers (auxiliary)
  #print axioms Omega.X.weight_expand
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
  -- Round 14: S_2/S_3 扩展基值 + 有界递推 + 条件递推 (prop:pom-s2-recurrence, prop:pom-s3-recurrence)
  #print axioms Omega.momentSum_two_seven
  #print axioms Omega.momentSum_three_seven
  #print axioms Omega.momentSum_two_recurrence_bounded
  #print axioms Omega.momentSum_three_recurrence_bounded
  #print axioms Omega.momentSum_two_recurrence_of
  #print axioms Omega.momentSum_three_recurrence_of
  -- Round 15: 离散骨架 (cor:folding-stable-syntax-entropy-logqdim, Stage 1)
  #print axioms Omega.Graph.goldenMeanAdjacency_pow_add_two
  #print axioms Omega.Graph.goldenMeanAdjacency_row_sum
  #print axioms Omega.card_X_recurrence
  #print axioms Omega.card_X_ratio_bounds
  #print axioms Omega.card_X_eq_matrix_sum
  -- Plan 6: FiberRing — CommRing 实例 + 环同构 X m ≃+* ZMod(F_{m+2})
  #print axioms Omega.X.stableMul_one_left_univ
  #print axioms Omega.X.stableMul_one_right_univ
  #print axioms Omega.X.instCommRing
  #print axioms Omega.X.ring_add_eq
  #print axioms Omega.X.ring_mul_eq
  #print axioms Omega.X.ring_zero_eq
  #print axioms Omega.X.ring_one_eq
  #print axioms Omega.X.ring_neg_eq
  #print axioms Omega.X.instNeZeroFib
  #print axioms Omega.X.toZMod
  #print axioms Omega.X.toZMod_add
  #print axioms Omega.X.toZMod_mul
  #print axioms Omega.X.toZMod_zero
  #print axioms Omega.X.toZMod_one
  #print axioms Omega.X.stableValueRingHom
  #print axioms Omega.X.toZMod_injective
  #print axioms Omega.X.toZMod_surjective
  #print axioms Omega.X.stableValueRingEquiv
  -- Plan 2: cor:field-phase-fib-prime — Field 实例 (FiberRing.lean:143-174)
  #print axioms Omega.X.instFieldOfPrime
  #print axioms Omega.X.instField_X1
  #print axioms Omega.X.instField_X2
  #print axioms Omega.X.instField_X3
  #print axioms Omega.X.instField_X5
  #print axioms Omega.X.instField_X9
  #print axioms Omega.X.instField_X11
  -- Plan 20 深化: shift 全零固定点与非单射 (ShiftDynamics.lean:48-82)
  #print axioms Omega.X.allFalse
  #print axioms Omega.X.shift_allFalse
  #print axioms Omega.X.shift_fixed_iff
  #print axioms Omega.X.shift_not_injective
  -- Plan 4 深化: restrict 满射与纤维非空 (ModularTower.lean:134-142)
  #print axioms Omega.X.restrict_surjective
  #print axioms Omega.X.restrict_fiber_nonempty
  -- Round 16: TransferMatrix 幂次条目公式 (TransferMatrix.lean:74-113, 计划19/20深化)
  #print axioms Omega.Graph.goldenMeanAdjacency_pow_00
  #print axioms Omega.Graph.goldenMeanAdjacency_pow_01
  #print axioms Omega.Graph.goldenMeanAdjacency_pow_10
  #print axioms Omega.Graph.goldenMeanAdjacency_pow_11
  -- Round 16: 周期轨道 (ShiftDynamics.lean:87-105, 计划20深化)
  #print axioms Omega.X.period3Seq
  #print axioms Omega.X.shiftN_three_period3
  #print axioms Omega.X.shift_period3_ne
  #print axioms Omega.X.period2Seq
  #print axioms Omega.X.shiftN_two_period2
  -- Round 16: Fibonacci 多项式 x=0 评估与路径独立集递推 (FibonacciPolynomial.lean:42-57, 计划11前置)
  #print axioms Omega.fibPoly_eval_zero
  #print axioms Omega.pathIndSetPoly_eval_zero
  #print axioms Omega.pathIndSetPoly_recurrence
  -- Round 17: Frontier 包装 — ConditionalArithmetic + ConditionalSummary
  -- thm:finite-resolution-mod + cor:field-phase-fib-prime (ConditionalArithmetic.lean:640-645)
  #print axioms Omega.Frontier.stable_ring_isomorphism
  #print axioms Omega.Frontier.stable_field_of_prime
  -- prop:pom-projection-entropy, prop:pom-fiber-sum-identity (ConditionalSummary.lean:554-559)
  #print axioms Omega.Frontier.projection_entropy_cardinality
  #print axioms Omega.Frontier.fiber_sum_eq_pow
  -- thm:fold-collision-convex-lower-bounds, prop:pom-sq-monotone (ConditionalSummary.lean:562-568)
  #print axioms Omega.Frontier.cauchy_schwarz_collision_bound
  #print axioms Omega.Frontier.moment_monotone
  -- prop:pom-sq-lower, cor:pom-s2-lower (ConditionalSummary.lean:570-576)
  #print axioms Omega.Frontier.moment_ge_cardinality
  #print axioms Omega.Frontier.collision_sum_ge_pow
  -- Phase 18: ConditionalSummary — POM 存在性与熵率骨架
  -- thm:pom-max-fiber (存在部分), prop:pom-fiber-pigeonhole, thm:pom-max-fiber (正性)
  -- cor:pom-D-rec (上界), prop:pom-projection-entropy (严格版), 投影比率递减/正性
  #print axioms Omega.Frontier.max_fiber_achieved
  #print axioms Omega.Frontier.fiber_pigeonhole
  #print axioms Omega.Frontier.max_fiber_positive
  #print axioms Omega.Frontier.max_fiber_fib_bound
  #print axioms Omega.Frontier.entropy_gap_strict
  #print axioms Omega.Frontier.projection_ratio_decreasing
  #print axioms Omega.Frontier.projection_ratio_positive
  -- Phase 18: FiberSpectrum — 达到者数定义与基值 (thm:pom-max-achievers-phase-stabilization 前置)
  #print axioms Omega.cMaxFiberAchievers
  -- Phase 19: FiberSpectrum — 达到者数有界 + 次大纤维基值 m=8,9,10
  -- thm:pom-max-achievers-phase-stabilization (有界), thm:pom-second-max-fiber-closed-form (m=8,9,10)
  #print axioms Omega.cMaxFiberAchievers_le_univ
  #print axioms Omega.cNthMaxFiber_second_eight
  #print axioms Omega.cNthMaxFiber_second_nine
  #print axioms Omega.cNthMaxFiber_second_ten
  -- Phase 19: ConditionalSummary — S_q 正性与 Cauchy-Schwarz 重述
  -- prop:pom-sq-pos, prop:pom-sq-cauchy-schwarz-restated
  #print axioms Omega.Frontier.momentSum_pos
  #print axioms Omega.Frontier.momentSum_cauchy_schwarz_restated
  -- Phase 20: ConditionalSummary — Rényi 上界 + S_1/S_0 恒等式 + 最大纤维概率界
  -- prop:pom-rq-universal-bounds + cor:pom-max-fiber-rate-endpoint
  #print axioms Omega.Frontier.renyi_upper_bound
  #print axioms Omega.Frontier.moment_sum_one_eq_pow
  #print axioms Omega.Frontier.moment_sum_zero_eq_card
  #print axioms Omega.Frontier.max_fiber_le_pow
  #print axioms Omega.Frontier.max_fiber_ge_one
  #print axioms Omega.Frontier.max_fiber_prob_bounds
  -- Phase 20: FiberSpectrum — 奇偶纤维计数定义与基值 (cor:pom-fiber-parity 前置)
  #print axioms Omega.cOddFiberCount
  #print axioms Omega.cEvenFiberCount
  -- Phase 21: Fib — Fibonacci 双倍公式与平方和恒等式 (Fib.lean:93-107)
  #print axioms Omega.fib_double
  #print axioms Omega.fib_double_plus_one
  #print axioms Omega.fib_sq_add_sq
  -- Phase 21: TransferMatrix — 行列式幂次公式与 Cassini 恒等式 (TransferMatrix.lean:116-128)
  #print axioms Omega.Graph.goldenMeanAdjacency_pow_det
  #print axioms Omega.Graph.fib_cassini
  -- Phase 21: ShiftDynamics — Lucas 数定义 + Fibonacci 关系 + 迹公式 (ShiftDynamics.lean:149-186)
  #print axioms Omega.X.lucasNum
  #print axioms Omega.X.lucasNum_zero
  #print axioms Omega.X.lucasNum_one
  #print axioms Omega.X.lucasNum_two
  #print axioms Omega.X.lucasNum_three
  #print axioms Omega.X.lucasNum_succ_succ
  #print axioms Omega.X.lucasNum_eq_fib
  #print axioms Omega.X.goldenMeanAdjacency_pow_trace
  -- Phase 22: FiberSpectrum — 纤维直方图定义与基值
  #print axioms Omega.cFiberHist
  #print axioms Omega.cFiberHist_4_1
  #print axioms Omega.cFiberHist_4_2
  #print axioms Omega.cFiberHist_4_3
  #print axioms Omega.cFiberHist_6_1
  #print axioms Omega.cFiberHist_6_2
  #print axioms Omega.cFiberHist_6_3
  #print axioms Omega.cFiberHist_6_4
  #print axioms Omega.cFiberHist_6_5
  -- Phase 22: TransferMatrix — 路径计数 Fibonacci 等式
  #print axioms Omega.Graph.goldenMean_path_count_from_true
  #print axioms Omega.Graph.goldenMean_total_paths
  -- Phase 22: InverseLimitTopology — 位差异→序列不同
  #print axioms Omega.X.ne_of_bit_ne
  -- Phase 22: ConditionalSummary — No11 词计数
  #print axioms Omega.Frontier.no11_count
  -- Phase 26: HankelSpectrum (Round 20, Target A) — Hankel 行列式 + 最小递推阶数
  -- lem:pom-s2-hankel-det, lem:pom-s2-minimal-order (HankelSpectrum.lean:20-50)
  #print axioms Omega.hankelS2_2x2_det
  #print axioms Omega.hankelS2_3x3_det
  #print axioms Omega.hankelS2_4x4_det
  #print axioms Omega.hankelS2_3x3_det_ne_zero
  #print axioms Omega.momentSum_two_minimal_recurrence_order
  #print axioms Omega.hankelS3_2x2_det
  #print axioms Omega.hankelS3_3x3_det
  #print axioms Omega.hankelS3_4x4_det
  #print axioms Omega.momentSum_three_minimal_recurrence_order
  -- Phase 26: HankelSpectrum (Round 20, Target B) — 特征多项式验证
  #print axioms Omega.collisionKernel2_charpoly_eval
  #print axioms Omega.collisionKernel2_charpoly_coefficients
  #print axioms Omega.collisionKernel3_charpoly_eval
  #print axioms Omega.collisionKernel3_charpoly_coefficients
  #print axioms Omega.collision_kernels_shared_invariants
  #print axioms Omega.collision_kernel_root_sum_eq_trace
  #print axioms Omega.collision_kernel_root_product
  -- Phase 26: HankelSpectrum (Round 20, Target C) — S_2/S_3 分辨率单调性
  -- thm:pom-s2-rank-exact, prop:pom-s2-recurrence, prop:pom-s3-recurrence
  #print axioms Omega.momentSum_two_strict_mono_verified
  #print axioms Omega.momentSum_two_mono_verified
  #print axioms Omega.momentSum_three_strict_mono_verified
  #print axioms Omega.momentSum_three_mono_verified
  #print axioms Omega.momentSum_two_mono_of_recurrence
  #print axioms Omega.momentSum_three_mono_of_recurrence
  -- Round 23: ZeckendorfSignature 群统一深化
  #print axioms Omega.ZeckSig.zeckendorf_no_carry_sm_triple
  #print axioms Omega.ZeckSig.zeckendorf_no_carry_so10_triple
  #print axioms Omega.ZeckSig.sm_signature_union
  #print axioms Omega.ZeckSig.so10_uplift_gap
  #print axioms Omega.ZeckSig.cassini_gap_33_factorization
  #print axioms Omega.ZeckSig.boundary_square_identity_instances
  #print axioms Omega.ZeckSig.cassini_identity_8
  #print axioms Omega.ZeckSig.sm_dim_factorization
  -- Round 23: BinFold — thm:terminal-foldbin6-64-to-21-hist
  #print axioms Omega.cBinFiberHist_6_0
  #print axioms Omega.cBinFiberHist_6_1
  #print axioms Omega.cBinFiberHist_6_2
  #print axioms Omega.cBinFiberHist_6_3
  #print axioms Omega.cBinFiberHist_6_4
  #print axioms Omega.binFold6_histogram_certificate
  #print axioms Omega.binFold6_distinct_multiplicities
  #print axioms Omega.binFold6_sum_check
  -- Round 23: HammingDist — Hamming 距离定义与基本性质
  #print axioms Omega.hammingDist_self
  #print axioms Omega.hammingDist_comm
  #print axioms Omega.hammingDist_le
  #print axioms Omega.cMinStableHammingDist_two
  #print axioms Omega.cMinStableHammingDist_three
  #print axioms Omega.cMinStableHammingDist_four
  -- Round 24: BinFold 群统一攻坚 — Target 1 边分离
  -- thm:terminal-foldbin6-cube-edge-separation, 线性核障碍, 非均匀纤维
  #print axioms Omega.binFold6_edge_separation
  #print axioms Omega.binFold6_mult_three_exists
  #print axioms Omega.binFold6_no_uniform_fibers
  -- Round 24: BinFold — Target 2 Hamming 三值律
  -- thm:terminal-foldbin6-fiber-hamming-three-valued (13,6,2)
  #print axioms Omega.binFiber6_minHamming_hist_2
  #print axioms Omega.binFiber6_minHamming_hist_3
  #print axioms Omega.binFiber6_minHamming_hist_5
  -- Round 24: BinFold — Target 2 仿射平坦几何
  -- thm:terminal-foldbin6-fiber-affine-geometry: 11 个仿射纤维
  #print axioms Omega.cAffineFlatCount_six
  #print axioms Omega.nonAffineFiber_count_six
  -- Round 24: BinFold — Target 3 几何稳定子（平凡群，论文勘误）
  -- cor:terminal-foldbin6-geo-stabilizer 修正版
  #print axioms Omega.geoStabilizer_trivial
  #print axioms Omega.geoStabilizer_order_one
  -- Round 25: ZeckendorfSignature 群统一冲刺 (Phase 30)
  -- thm:terminal-window6-tail-three-branch, thm:terminal-family-uplift-lock
  -- thm:terminal-6d-microstate-golden-time-gut-branch
  #print axioms Omega.ZeckSig.uplift_three_branch
  #print axioms Omega.ZeckSig.dim_su5_top_term
  #print axioms Omega.ZeckSig.gut_top_terms_align
  #print axioms Omega.ZeckSig.family_lock_zeckendorf
  #print axioms Omega.ZeckSig.family_three_selects_so10
  #print axioms Omega.ZeckSig.gut_dimension_gaps
  #print axioms Omega.ZeckSig.exceptional_zeckendorf_signatures
  #print axioms Omega.ZeckSig.discrete_unification_certificate
  #print axioms Omega.ZeckSig.unification_triple_dynamic
  -- Round 25: BinFold — thm:terminal-foldbin6-pushforward-markov (Phase 30)
  -- detailed balance 不成立（已记录为论文修正）
  #print axioms Omega.cTypeAdjCount_symm_six
  #print axioms Omega.cTypeAdjCount_row_sum_six
  #print axioms Omega.cTypeAdjCount_nonzero_exists
  -- Round 30: CollisionZeta — 碰撞核迹幂 A_2/A_3 (Phase 35)
  -- def:pom-collision-zeta-a2/a3
  #print axioms Omega.collisionKernel2_trace_pow_1
  #print axioms Omega.collisionKernel2_trace_pow_2
  #print axioms Omega.collisionKernel2_trace_pow_3
  #print axioms Omega.collisionKernel2_trace_pow_4
  #print axioms Omega.collisionKernel2_trace_pow_5
  #print axioms Omega.collisionKernel2_trace_pow_6
  #print axioms Omega.collisionKernel3_trace_pow_1
  #print axioms Omega.collisionKernel3_trace_pow_2
  #print axioms Omega.collisionKernel3_trace_pow_3
  #print axioms Omega.collisionKernel3_trace_pow_4
  #print axioms Omega.collisionKernel3_trace_pow_5
  #print axioms Omega.collisionKernel3_trace_pow_6
  #print axioms Omega.collision_trace_pow1_eq
  #print axioms Omega.collisionKernel2_trace_recurrence
  -- Round 30: Window6 — 氢型量子数语法 (Phase 35)
  -- prop:conclusion-hydrogenic-address-grammar
  #print axioms Omega.sum_odd_eq_square
  #print axioms Omega.hydrogenic_instances
  #print axioms Omega.hydrogenic_total_count_instances
  #print axioms Omega.sum_squares_four
  -- Round 30: ZeckendorfSignature — 素赋值度量非退化 (Phase 35)
  -- thm:conclusion-valuation-isometry-classification (部分)
  #print axioms Omega.ZeckSig.factorization_determines_nat
  -- Round 32: A_4 碰撞核 + 递推验证 (prop:pom-s4-recurrence, CollisionKernel.lean:90-122)
  #print axioms Omega.collisionKernel4
  #print axioms Omega.collisionKernel4_trace
  #print axioms Omega.collisionKernel4_det
  #print axioms Omega.momentSum_four_recurrence_verified
  #print axioms Omega.collision_kernels_shared_invariants_triple
  -- Round 32: A_4 迹幂 + primitive 轨道 + Hankel + det 幂 (def:pom-collision-zeta-a4, CollisionZeta.lean:99-141)
  #print axioms Omega.collisionKernel4_trace_pow_0
  #print axioms Omega.collisionKernel4_trace_pow_1
  #print axioms Omega.collisionKernel4_trace_pow_2
  #print axioms Omega.collisionKernel4_trace_pow_3
  #print axioms Omega.collisionKernel4_trace_pow_4
  #print axioms Omega.primitive_orbit_A4
  #print axioms Omega.hankelS4_4x4
  #print axioms Omega.hankelS4_4x4_det
  #print axioms Omega.hankelS4_4x4_det_ne_zero
  #print axioms Omega.collisionKernel2_det_pow_2
  #print axioms Omega.collisionKernel2_det_pow_3
  #print axioms Omega.collisionKernel3_det_pow_2
  #print axioms Omega.collisionKernel3_det_pow_3
  #print axioms Omega.collisionKernel4_det_pow_2
  -- Round 33: S_5-S_8 基值 (prop:pom-s5/s6/s7/s8-base-values, MomentSum.lean:79-103)
  #print axioms Omega.momentSum_five_zero
  #print axioms Omega.momentSum_five_one
  #print axioms Omega.momentSum_five_two
  #print axioms Omega.momentSum_five_three
  #print axioms Omega.momentSum_five_four
  #print axioms Omega.momentSum_five_five
  #print axioms Omega.momentSum_six_zero
  #print axioms Omega.momentSum_six_one
  #print axioms Omega.momentSum_six_two
  #print axioms Omega.momentSum_six_three
  #print axioms Omega.momentSum_six_four
  #print axioms Omega.momentSum_seven_zero
  #print axioms Omega.momentSum_seven_one
  #print axioms Omega.momentSum_seven_two
  #print axioms Omega.momentSum_seven_three
  #print axioms Omega.momentSum_eight_zero
  #print axioms Omega.momentSum_eight_one
  #print axioms Omega.momentSum_eight_two
  #print axioms Omega.momentSum_eight_three
  -- Round 33: golden-mean ζ 分母 + 迹递推 (TransferMatrix.lean:170-181)
  #print axioms Omega.Graph.goldenMean_zeta_denom_at_one
  #print axioms Omega.Graph.goldenMean_trace_recurrence_verified
  -- Round 33: 统一迹/det 证书 + Perron 定位 (CollisionZeta.lean:145-186)
  #print axioms Omega.trace_comparison
  #print axioms Omega.det_comparison
  #print axioms Omega.charPoly_A2_sign_changes
  #print axioms Omega.perron_A2_in_interval
  #print axioms Omega.perron_A3_in_interval
  #print axioms Omega.charPoly_A3_root_in_01
  -- Round 34: Möbius 轨道扩展 + 判别式 + Pisano 周期 + Fibonacci 入口点 (Phase 39)
  -- def:pom-primitive-orbit-extended (CollisionZeta.lean:193-200)
  #print axioms Omega.primitive_orbit_A2_extended
  #print axioms Omega.primitive_orbit_A3_extended
  -- def:pom-charpoly-discriminant (CollisionZeta.lean:209-219)
  #print axioms Omega.charPoly_A2_discriminant_positive
  #print axioms Omega.charPoly_A3_discriminant_positive
  #print axioms Omega.collision_kernels_all_real_eigenvalues
  -- def:pom-perron-root-separated (CollisionZeta.lean:225-227)
  #print axioms Omega.perron_root_separated_by_three
  -- def:pom-pisano-period-2/3/5/7/6 (CollisionZeta.lean:235-247)
  #print axioms Omega.pisano_period_2
  #print axioms Omega.pisano_period_3
  #print axioms Omega.pisano_period_5
  #print axioms Omega.pisano_period_7
  #print axioms Omega.pisano_period_6
  -- def:pom-fib-entry-point-21 (CollisionZeta.lean:251-255)
  #print axioms Omega.fib_entry_point_21
  -- Round 38: Real 路线首轮 (Entropy.lean:14-69)
  #print axioms Omega.Entropy.coe_fib_pos
  #print axioms Omega.Entropy.stableSyntaxCount_pos
  #print axioms Omega.Entropy.goldenRatio_gt_one
  #print axioms Omega.Entropy.log_goldenRatio_pos
  #print axioms Omega.Entropy.goldenRatio_lt_two
  #print axioms Omega.Entropy.abs_goldenConj_lt_one
  #print axioms Omega.Entropy.goldenConj_bounds
  #print axioms Omega.Entropy.fib_ratio_tendsto
  #print axioms Omega.Entropy.log_continuous_at_phi
  #print axioms Omega.Entropy.log_fib_ratio_tendsto
  -- Phase 44 (Plan 20 complete): 拓扑熵 h_top = log φ (Entropy.lean:80-107)
  -- cor:folding-stable-syntax-entropy-logqdim 完整版: Cesaro + 望远镜求和 + Real 分析极限
  #print axioms Omega.Entropy.topological_entropy_eq_log_phi
  -- Round 39: 圆维度章节前置 (Entropy.lean:111-153)
  -- 黄金比例算术几何 + 熵率比较 + Binet 公式
  #print axioms Omega.Entropy.goldenRatio_gt_three_half
  #print axioms Omega.Entropy.goldenRatio_lt_five_thirds
  #print axioms Omega.Entropy.goldenRatio_eq_one_add_inv
  #print axioms Omega.Entropy.phi_irrational
  #print axioms Omega.Entropy.entropy_ordering_proxy
  #print axioms Omega.Entropy.entropy_gap_pos
  #print axioms Omega.Entropy.binet_formula
  -- Round 40: 圆维度正式开辟 (Entropy.lean:155-249)
  -- √5 算术 + φ vs √5 + goldenAngle + |ψ^n/√5| < 1/2 + fib_nearest_integer
  #print axioms Omega.Entropy.sqrt5_gt_two'
  #print axioms Omega.Entropy.sqrt5_lt_three'
  #print axioms Omega.Entropy.phi_lt_sqrt5
  #print axioms Omega.Entropy.phi_add_one_gt_sqrt5
  #print axioms Omega.Entropy.goldenAngle_pos
  #print axioms Omega.Entropy.goldenAngle_lt_one
  #print axioms Omega.Entropy.goldenAngle_sq
  #print axioms Omega.Entropy.abs_psi_pow_div_sqrt5_lt_half
  #print axioms Omega.Entropy.fib_nearest_integer
  -- Round 42: S_q 通用基值完整化 + ψ^n 收敛 (Phase 48)
  -- prop:pom-moment-zero-univ, prop:pom-moment-one-univ (MomentSum.lean:118,137)
  #print axioms Omega.momentSum_zero_univ
  #print axioms Omega.momentSum_one_univ
  -- aux:cdim-cassini-alternation (Entropy.lean:283)
  #print axioms Omega.Entropy.fib_convergent_alternation
  -- prop:cdim-psi-pow-tendsto-zero, prop:cdim-psi-pow-tendsto-zero-real (Entropy.lean:291,296)
  #print axioms Omega.Entropy.psi_pow_tendsto_zero
  #print axioms Omega.Entropy.psi_pow_tendsto_zero'

The goal of phase 0/1 is that these core theorems use no project-defined axioms.
-/

def coreAuditTargets : List String :=
  [ "Omega.fib_succ_succ'"
  , "Omega.no11_truncate"
  , "Omega.X.restrict"
  , "Omega.X.card_eq_fib"
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
  , "Omega.X.fib_succ_add_fib_eq"
  , "Omega.X.fib_sub_eq"
  , "Omega.X.fib_lt_fib_succ_succ"
  , "Omega.X.stableValue_restrict_stableAdd_carry"
  , "Omega.X.restrict_stableAdd_carry_defect"
  , "Omega.X.carryElement_m6_value"
  , "Omega.X.carryElement_m5_value"
  , "Omega.X.carryElement_m7_value"
  , "Omega.X.carryElement_ne_zero"
  -- Stable value bound & arithmetic
  , "Omega.stableValue_lt_fib"
  , "Omega.X.stableValueFin"
  , "Omega.X.stableValueFin_injective"
  , "Omega.X.stableAdd"
  , "Omega.X.stableAdd_comm"
  , "Omega.Frontier.stableValue_bounded"
  , "Omega.Frontier.stableAdd_commutative"
  -- Fibonacci infrastructure
  , "Omega.fib_succ_pos"
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
  , "Omega.fib_four_prime"
  , "Omega.fib_five_prime"
  , "Omega.fib_seven_prime"
  , "Omega.fib_nine_not_prime"
  , "Omega.fib_thirteen_prime"
  -- Round 8: Fibonacci 界 + momentSum
  , "Omega.fib_le_pow_two"
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
  , "Omega.maxFiberMultiplicity_le_add"
  -- Plan 6: FiberRing — CommRing + 环同构 X m ≃+* ZMod(F_{m+2})
  , "Omega.X.stableMul_one_left_univ"
  , "Omega.X.stableMul_one_right_univ"
  , "Omega.X.instCommRing"
  , "Omega.X.ring_add_eq"
  , "Omega.X.ring_mul_eq"
  , "Omega.X.ring_zero_eq"
  , "Omega.X.ring_one_eq"
  , "Omega.X.ring_neg_eq"
  , "Omega.X.instNeZeroFib"
  , "Omega.X.toZMod"
  , "Omega.X.toZMod_add"
  , "Omega.X.toZMod_mul"
  , "Omega.X.toZMod_zero"
  , "Omega.X.toZMod_one"
  , "Omega.X.stableValueRingHom"
  , "Omega.X.toZMod_injective"
  , "Omega.X.toZMod_surjective"
  , "Omega.X.stableValueRingEquiv"
  -- Phase 9 (partial): FiberSpectrum — 纤维谱定义与基值 (def:pom-top-fiber-spectrum)
  , "Omega.cNthMaxFiber_zero_eq_0"
  , "Omega.cNthMaxFiber_zero_eq_5"
  , "Omega.cNthMaxFiber_zero_eq_7"
  , "Omega.X.fiberValueSet_nonempty"
  , "Omega.cFiberSpectrum_zero"
  , "Omega.cFiberSpectrum_one"
  , "Omega.cFiberSpectrum_two"
  , "Omega.cFiberSpectrum_three"
  , "Omega.cFiberSpectrum_four"
  , "Omega.cFiberSpectrum_five"
  , "Omega.cFiberSpectrum_six"
  , "Omega.cFiberSpectrum_seven"
  , "Omega.cNthMaxFiber_second_four"
  , "Omega.cNthMaxFiber_second_five"
  , "Omega.cNthMaxFiber_second_six"
  , "Omega.cNthMaxFiber_second_seven"
  , "Omega.cNthMaxFiber_third_four"
  , "Omega.cNthMaxFiber_third_five"
  , "Omega.cNthMaxFiber_third_six"
  , "Omega.cNthMaxFiber_third_seven"
  -- 计划5: Fibonacci 整除性 (Fib.lean:81-92)
  , "Omega.fib_gcd"
  , "Omega.fib_coprime_succ"
  , "Omega.fib_dvd_mul"
  -- 计划4深化: restrict 保零保一 (ModularTower.lean:122-133)
  , "Omega.X.restrict_zero"
  , "Omega.X.restrict_one"
  -- 计划27初步: CRT 分解 (FiberRing.lean:179-192)
  , "Omega.X.crtDecomposition"
  , "Omega.X.X7_decomposition"
  , "Omega.X.X10_decomposition"
  -- 计划20深化: shift 全零固定点与非单射 (ShiftDynamics.lean:48-82)
  , "Omega.X.allFalse"
  , "Omega.X.shift_allFalse"
  , "Omega.X.shift_fixed_iff"
  , "Omega.X.shift_not_injective"
  -- 计划4深化: restrict 满射与纤维非空 (ModularTower.lean:134-142)
  , "Omega.X.restrict_surjective"
  , "Omega.X.restrict_fiber_nonempty"
  -- Phase 20: ConditionalSummary — Rényi 上界 + S_1/S_0 恒等式 + 最大纤维概率界
  , "Omega.Frontier.renyi_upper_bound"
  , "Omega.Frontier.moment_sum_one_eq_pow"
  , "Omega.Frontier.moment_sum_zero_eq_card"
  , "Omega.Frontier.max_fiber_le_pow"
  , "Omega.Frontier.max_fiber_ge_one"
  , "Omega.Frontier.max_fiber_prob_bounds"
  -- Phase 20: FiberSpectrum — 奇偶纤维计数定义与基值
  , "Omega.cOddFiberCount"
  , "Omega.cEvenFiberCount"
  -- Phase 21: Fib — Fibonacci 双倍公式与平方和恒等式 (Fib.lean:93-107)
  , "Omega.fib_double"
  , "Omega.fib_double_plus_one"
  , "Omega.fib_sq_add_sq"
  -- Phase 21: TransferMatrix — 行列式幂次公式与 Cassini 恒等式 (TransferMatrix.lean:116-128)
  , "Omega.Graph.goldenMeanAdjacency_pow_det"
  , "Omega.Graph.fib_cassini"
  -- Phase 21: ShiftDynamics — Lucas 数定义 + Fibonacci 关系 + 迹公式 (ShiftDynamics.lean:149-186)
  , "Omega.X.lucasNum"
  , "Omega.X.lucasNum_zero"
  , "Omega.X.lucasNum_one"
  , "Omega.X.lucasNum_two"
  , "Omega.X.lucasNum_three"
  , "Omega.X.lucasNum_succ_succ"
  , "Omega.X.lucasNum_eq_fib"
  , "Omega.X.goldenMeanAdjacency_pow_trace"
  -- Phase 23: ShiftDynamics — 周期轨道深化 (ShiftDynamics.lean:108-131)
  , "Omega.X.shift_period2_ne"
  , "Omega.X.period2_minimal"
  , "Omega.X.period3_minimal"
  , "Omega.X.period4Seq"
  , "Omega.X.shiftN_four_period4"
  -- Phase 23: Weight — 全零词 weight=0 (Weight.lean:50)
  , "Omega.weight_allFalse"
  -- Phase 23: Value — 全零稳定词 stableValue=0 (Value.lean:109)
  , "Omega.stableValue_allFalse"
  -- Phase 24: Zeckendorf — 全零稳定词 Zeckendorf 索引为空 (Zeckendorf.lean:162)
  , "Omega.X.zeckIndices_allFalse"
  -- Phase 25: Value — stableValue = weight (Value.lean:114)
  , "Omega.stableValue_eq_weight"
  -- Phase 25: FiberRing — 环特征 = F_{m+2} (FiberRing.lean:196)
  , "Omega.instCharP"
  -- Phase 26: HankelSpectrum — Hankel 行列式 + 最小递推阶数 + 特征多项式 + 分辨率单调性
  , "Omega.hankelS2_2x2_det"
  , "Omega.hankelS2_3x3_det"
  , "Omega.hankelS2_4x4_det"
  , "Omega.hankelS2_3x3_det_ne_zero"
  , "Omega.momentSum_two_minimal_recurrence_order"
  , "Omega.hankelS3_2x2_det"
  , "Omega.hankelS3_3x3_det"
  , "Omega.hankelS3_4x4_det"
  , "Omega.momentSum_three_minimal_recurrence_order"
  , "Omega.collisionKernel2_charpoly_eval"
  , "Omega.collisionKernel2_charpoly_coefficients"
  , "Omega.collisionKernel3_charpoly_eval"
  , "Omega.collisionKernel3_charpoly_coefficients"
  , "Omega.collision_kernels_shared_invariants"
  , "Omega.collision_kernel_root_sum_eq_trace"
  , "Omega.collision_kernel_root_product"
  , "Omega.momentSum_two_strict_mono_verified"
  , "Omega.momentSum_two_mono_verified"
  , "Omega.momentSum_three_strict_mono_verified"
  , "Omega.momentSum_three_mono_verified"
  , "Omega.momentSum_two_mono_of_recurrence"
  , "Omega.momentSum_three_mono_of_recurrence"
  -- Phase 26 补充 (Round 20): S_3 Hankel 归一化 + 4x4 秩 + 分辨率单调联合
  , "Omega.hankelS3_det"
  , "Omega.hankelS3_det_ne_zero"
  , "Omega.hankelS2_norm_4x4_det"
  , "Omega.hankelS2_rank_exact_three"
  , "Omega.momentSum_two_mono_resolution_verified"
  , "Omega.momentSum_three_mono_resolution_verified"
  -- Phase 27: FiberSplit — D_m 严格单调性 + 纤维分裂界 + D^{(2)} 基值
  , "Omega.X.maxFiberMultiplicity_strict_mono_verified"
  , "Omega.X.maxFiberMultiplicity_mono_verified"
  , "Omega.X.maxFiberMultiplicity_mono_of_two_step"
  , "Omega.X.maxFiberMultiplicity_strict_mono_of_two_step"
  , "Omega.X.maxFiberMultiplicity_split_bound"
  , "Omega.X.maxFiberMultiplicity_fibonacci_bound"
  , "Omega.X.cSecondMaxFiberMult_two"
  , "Omega.X.cSecondMaxFiberMult_three"
  , "Omega.X.cSecondMaxFiberMult_four"
  , "Omega.X.cSecondMaxFiberMult_five"
  , "Omega.X.cSecondMaxFiberMult_six"
  , "Omega.X.cSecondMaxFiberMult_seven"
  , "Omega.X.cSecondMaxFiberMult_eq_prev"
  -- Phase 28: BoundaryLayer (Round 22) — prop:bdry-fib-square-identity, cor:bdry-m6-square-instance
  , "Omega.cBoundaryCount_three"
  , "Omega.cBoundaryCount_four"
  , "Omega.cBoundaryCount_five"
  , "Omega.cBoundaryCount_six"
  , "Omega.cBoundaryCount_seven"
  , "Omega.cBoundaryCount_eight"
  , "Omega.cBoundaryCount_eq_fib"
  , "Omega.boundary_gap_six"
  , "Omega.boundary_gap_seven"
  , "Omega.boundary_gap_eight"
  , "Omega.boundary_gap_33_value"
  , "Omega.cFirstBitTrueCount_three"
  , "Omega.cFirstBitTrueCount_four"
  , "Omega.cFirstBitTrueCount_five"
  , "Omega.cFirstBitTrueCount_six"
  , "Omega.cFirstBitTrueCount_seven"
  , "Omega.cFirstBitTrueCount_eq_fib"
  -- Phase 28: Window6 (Round 22) — m=6 不变量
  , "Omega.card_Word_six"
  , "Omega.card_X_six'"
  , "Omega.cNontrivialFiberCount"
  , "Omega.cNontrivialFiberCount_six"
  , "Omega.abelianization_rank_six"
  , "Omega.compression_ratio_six"
  , "Omega.fiber_sum_six"
  , "Omega.nontrivial_microstate_count_six"
  -- Phase 28: ZeckendorfSignature (Round 22) — thm:zeckendorf-no-carry-additivity, thm:nap-so10-analytic-minimality
  , "Omega.ZeckSig.dim_so10_zeckendorf"
  , "Omega.ZeckSig.dim_sm_zeckendorf"
  , "Omega.ZeckSig.dim_su2"
  , "Omega.ZeckSig.dim_su3"
  , "Omega.ZeckSig.dim_so5"
  , "Omega.ZeckSig.dim_G2"
  , "Omega.ZeckSig.dim_su4"
  , "Omega.ZeckSig.dim_so7"
  , "Omega.ZeckSig.dim_su5"
  , "Omega.ZeckSig.dim_so8"
  , "Omega.ZeckSig.dim_so9"
  , "Omega.ZeckSig.dim_F4"
  , "Omega.ZeckSig.dim_E6"
  , "Omega.ZeckSig.dim_E7"
  , "Omega.ZeckSig.dim_E8"
  , "Omega.ZeckSig.so10_has_F4_and_F6"
  , "Omega.ZeckSig.sm12_has_F4_and_F6"
  , "Omega.ZeckSig.nap_su2"
  , "Omega.ZeckSig.nap_su3"
  , "Omega.ZeckSig.fib_4_val"
  , "Omega.ZeckSig.fib_6_val"
  , "Omega.ZeckSig.fib_8_val"
  , "Omega.ZeckSig.fib_9_val"
  , "Omega.ZeckSig.fib_10_val"
  , "Omega.ZeckSig.fib_11_val"
  , "Omega.ZeckSig.fib_13_val"
  -- Round 23: ZeckendorfSignature 群统一深化 (Phase 29)
  , "Omega.ZeckSig.zeckendorf_no_carry_sm_triple"
  , "Omega.ZeckSig.zeckendorf_no_carry_so10_triple"
  , "Omega.ZeckSig.sm_signature_union"
  , "Omega.ZeckSig.so10_uplift_gap"
  , "Omega.ZeckSig.cassini_gap_33_factorization"
  , "Omega.ZeckSig.boundary_square_identity_instances"
  , "Omega.ZeckSig.cassini_identity_8"
  , "Omega.ZeckSig.sm_dim_factorization"
  -- Round 23: BinFold — thm:terminal-foldbin6-64-to-21-hist (Phase 29)
  , "Omega.cBinFiberHist_6_0"
  , "Omega.cBinFiberHist_6_1"
  , "Omega.cBinFiberHist_6_2"
  , "Omega.cBinFiberHist_6_3"
  , "Omega.cBinFiberHist_6_4"
  , "Omega.binFold6_histogram_certificate"
  , "Omega.binFold6_distinct_multiplicities"
  , "Omega.binFold6_sum_check"
  -- Round 23: HammingDist — Hamming 距离定义与基本性质 (Phase 29)
  , "Omega.hammingDist_self"
  , "Omega.hammingDist_comm"
  , "Omega.hammingDist_le"
  , "Omega.cMinStableHammingDist_two"
  , "Omega.cMinStableHammingDist_three"
  , "Omega.cMinStableHammingDist_four"
  -- Round 24: BinFold 群统一攻坚 (Phase 29)
  -- Target 1: 边分离 + 线性核障碍 + 非均匀纤维
  , "Omega.binFold6_edge_separation"
  , "Omega.binFold6_mult_three_exists"
  , "Omega.binFold6_no_uniform_fibers"
  -- Target 2: Hamming 三值律 (thm:terminal-foldbin6-fiber-hamming-three-valued)
  , "Omega.binFiber6_minHamming_hist_2"
  , "Omega.binFiber6_minHamming_hist_3"
  , "Omega.binFiber6_minHamming_hist_5"
  -- Target 2: 仿射平坦几何 (thm:terminal-foldbin6-fiber-affine-geometry)
  , "Omega.cAffineFlatCount_six"
  , "Omega.nonAffineFiber_count_six"
  -- Target 3: 几何稳定子平凡 (cor:terminal-foldbin6-geo-stabilizer 修正版)
  , "Omega.geoStabilizer_trivial"
  , "Omega.geoStabilizer_order_one"
  -- Round 25: ZeckendorfSignature 群统一冲刺 (Phase 30)
  -- thm:terminal-window6-tail-three-branch, thm:terminal-family-uplift-lock
  -- thm:terminal-6d-microstate-golden-time-gut-branch
  , "Omega.ZeckSig.uplift_three_branch"
  , "Omega.ZeckSig.dim_su5_top_term"
  , "Omega.ZeckSig.gut_top_terms_align"
  , "Omega.ZeckSig.family_lock_zeckendorf"
  , "Omega.ZeckSig.family_three_selects_so10"
  , "Omega.ZeckSig.gut_dimension_gaps"
  , "Omega.ZeckSig.exceptional_zeckendorf_signatures"
  , "Omega.ZeckSig.discrete_unification_certificate"
  , "Omega.ZeckSig.unification_triple_dynamic"
  -- Round 25: BinFold — thm:terminal-foldbin6-pushforward-markov (Phase 30)
  , "Omega.cTypeAdjCount_symm_six"
  , "Omega.cTypeAdjCount_row_sum_six"
  , "Omega.cTypeAdjCount_nonzero_exists"
  -- Round 26: Window6 CRT 幂等元 (Phase 31)
  -- thm:conclusion-window6-visible-crt-arithmetic-phase-space
  -- prop:conclusion-window6-crt-idempotent-sector-splitting
  , "Omega.fib8_factorization"
  , "Omega.crt_idempotent_7"
  , "Omega.crt_idempotent_15"
  , "Omega.crt_idempotent_product"
  , "Omega.crt_idempotent_sum"
  , "Omega.zmod21_idempotents_complete"
  , "Omega.zmod21_unit_count"
  -- Round 26: BinFold 局部/全局分离 (Phase 31)
  -- thm:conclusion-window6-local-index-global-compression-separation
  , "Omega.cBinFiberMin_six"
  , "Omega.cBinFiberMax_six"
  , "Omega.local_index_lt_global_compression"
  , "Omega.total_hidden_dims_six"
  , "Omega.compression_bounds_six"
  , "Omega.multiplicity_spread_six"
  -- Round 26: ZeckendorfSignature GCD 实例 (Phase 31)
  -- thm:conclusion-valuation-median-group
  , "Omega.ZeckSig.gcd_as_median_instances"
  , "Omega.ZeckSig.fib_coprime_consecutive"
  , "Omega.ZeckSig.fib_gcd_instances"
  , "Omega.ZeckSig.phase_space_coprimality"
  -- Round 27: Window6 TQFT 配分函数 + 隐藏反射包 + 信息证书 (Phase 32)
  -- thm:conclusion-fold-symtft-partition-function-collision-moments
  -- cor:conclusion-tqft-sphere-partition-function-s2
  -- thm:conclusion-window6-hidden-a-type-weyl-package
  -- thm:conclusion-window6-hidden-logvolume-geometry-information-splitting
  , "Omega.tqft_sphere_eq_momentSum_two"
  , "Omega.tqft_torus_eq_card"
  , "Omega.sector_sum_six_q0"
  , "Omega.sector_sum_six_q1"
  , "Omega.sector_sum_six_q2"
  , "Omega.hidden_reflection_dim_six"
  , "Omega.hidden_reflection_from_histogram"
  , "Omega.quadratic_collision_mass_six"
  , "Omega.discriminant_total_degree_six"
  , "Omega.jones_index_lower_six"
  , "Omega.window6_information_certificate"
  , "Omega.tqft_triple_six"
  , "Omega.collision_ratio_bounds_six"
  -- Round 28: 结论章节深化 (Phase 33)
  -- thm:conclusion-window6-hidden-reflection-invariant-polynomial-ring
  -- cor:conclusion-window6-reflection-discriminant-degree-poincare
  -- prop:conclusion-watatani-handle-identity-trace-moment
  -- cor:conclusion-sector-resolved-collision-moments-by-genus
  , "Omega.invariant_ring_generator_count"
  , "Omega.invariant_ring_from_histogram"
  , "Omega.poincare_A2_coeffs"
  , "Omega.poincare_A3_coeffs"
  , "Omega.total_free_generators_eq_hidden_dim"
  , "Omega.sector_sum_six_q3"
  , "Omega.cauchy_schwarz_gap_six"
  , "Omega.tqft_genus_values_six"
  , "Omega.weyl_orders"
  , "Omega.gauge_group_order_factored"
  -- Round 29: ZeckendorfSignature — 15·F(n)/16·F(n) Zeckendorf 分解 (Phase 34)
  -- thm:conclusion-zeckendorf-15-16-closed (ZeckendorfSignature.lean:249-268)
  , "Omega.ZeckSig.zeckendorf_15Fn_instances"
  , "Omega.ZeckSig.zeckendorf_16Fn_instances"
  , "Omega.ZeckSig.dim_15_16_zeckendorf"
  -- Round 29: Window6 — TQFT 属格生成函数 + Q_6 超立方相二次闭合 (Phase 34)
  -- prop:conclusion-tqft-genus-generating-function-rational (Window6.lean:221-233)
  , "Omega.sector_sum_six_q4"
  , "Omega.sector_sum_six_q5"
  , "Omega.genus_recurrence_order_six"
  , "Omega.distinct_fiber_sq_six"
  -- thm:conclusion-hypercube-phase-quadratic-closure (Window6.lean:238-250)
  , "Omega.q6_multiplicities"
  , "Omega.q6_multiplicity_sum"
  , "Omega.q6_trace_zero"
  -- Round 30: CollisionZeta — 碰撞核迹幂（Zeta 有限部分章节入口，Phase 35）
  -- def:pom-collision-zeta-a2 (CollisionZeta.lean:11-16)
  , "Omega.collisionKernel2_trace_pow_1"
  , "Omega.collisionKernel2_trace_pow_2"
  , "Omega.collisionKernel2_trace_pow_3"
  , "Omega.collisionKernel2_trace_pow_4"
  , "Omega.collisionKernel2_trace_pow_5"
  , "Omega.collisionKernel2_trace_pow_6"
  -- def:pom-collision-zeta-a3 (CollisionZeta.lean:19-24)
  , "Omega.collisionKernel3_trace_pow_1"
  , "Omega.collisionKernel3_trace_pow_2"
  , "Omega.collisionKernel3_trace_pow_3"
  , "Omega.collisionKernel3_trace_pow_4"
  , "Omega.collisionKernel3_trace_pow_5"
  , "Omega.collisionKernel3_trace_pow_6"
  -- 迹相等 + A_2 递推验证 (CollisionZeta.lean:27-40)
  , "Omega.collision_trace_pow1_eq"
  , "Omega.collisionKernel2_trace_recurrence"
  -- Round 30: Window6 — 氢型量子数语法 (Phase 35)
  -- prop:conclusion-hydrogenic-address-grammar (Window6.lean:255-271)
  , "Omega.sum_odd_eq_square"
  , "Omega.hydrogenic_instances"
  , "Omega.hydrogenic_total_count_instances"
  , "Omega.sum_squares_four"
  -- Round 30: ZeckendorfSignature — 素赋值度量非退化 (Phase 35)
  -- thm:conclusion-valuation-isometry-classification (部分) (ZeckendorfSignature.lean:274-276)
  , "Omega.ZeckSig.factorization_determines_nat"
  -- Round 31: MomentSum — S_4 基值 (Phase 36)
  -- prop:pom-s4-base-values (MomentSum.lean:70-76)
  , "Omega.momentSum_four_zero"
  , "Omega.momentSum_four_one"
  , "Omega.momentSum_four_two"
  , "Omega.momentSum_four_three"
  , "Omega.momentSum_four_four"
  , "Omega.momentSum_four_five"
  , "Omega.momentSum_four_six"
  -- Round 31: CollisionZeta — 迹递推 + trace^0 + primitive 轨道 + ζ 分母 (Phase 36)
  -- def:pom-collision-zeta-a3-recurrence (CollisionZeta.lean:44-51)
  , "Omega.collisionKernel3_trace_recurrence"
  -- trace_pow_0 for both kernels (CollisionZeta.lean:56-57)
  , "Omega.collisionKernel2_trace_pow_0"
  , "Omega.collisionKernel3_trace_pow_0"
  -- def:pom-primitive-orbit-count (CollisionZeta.lean:68-79)
  , "Omega.primitive_orbit_A2"
  , "Omega.primitive_orbit_A3"
  -- def:pom-zeta-denom-coefficients (CollisionZeta.lean:88-97)
  , "Omega.zeta_denom_A2_coefficients"
  , "Omega.zeta_denom_A3_coefficients"
  -- Round 31: TransferMatrix — 矩阵幂次扩展 (Phase 36)
  -- thm:transfer-matrix-specific-powers (TransferMatrix.lean:153-165)
  , "Omega.Graph.goldenMeanAdjacency_pow_five_00"
  , "Omega.Graph.goldenMeanAdjacency_pow_six_00"
  , "Omega.Graph.goldenMeanAdjacency_pow_ten_00"
  -- Round 33: S_5-S_8 基值 (prop:pom-s5/s6/s7/s8-base-values, MomentSum.lean:79-103)
  , "Omega.momentSum_five_zero"
  , "Omega.momentSum_five_one"
  , "Omega.momentSum_five_two"
  , "Omega.momentSum_five_three"
  , "Omega.momentSum_five_four"
  , "Omega.momentSum_five_five"
  , "Omega.momentSum_six_zero"
  , "Omega.momentSum_six_one"
  , "Omega.momentSum_six_two"
  , "Omega.momentSum_six_three"
  , "Omega.momentSum_six_four"
  , "Omega.momentSum_seven_zero"
  , "Omega.momentSum_seven_one"
  , "Omega.momentSum_seven_two"
  , "Omega.momentSum_seven_three"
  , "Omega.momentSum_eight_zero"
  , "Omega.momentSum_eight_one"
  , "Omega.momentSum_eight_two"
  , "Omega.momentSum_eight_three"
  -- Round 33: golden-mean ζ 分母 + 迹递推 (TransferMatrix.lean:170-181)
  , "Omega.Graph.goldenMean_zeta_denom_at_one"
  , "Omega.Graph.goldenMean_trace_recurrence_verified"
  -- Round 33: 统一迹/det 证书 + Perron 定位 (CollisionZeta.lean:145-186)
  , "Omega.trace_comparison"
  , "Omega.det_comparison"
  , "Omega.charPoly_A2_sign_changes"
  , "Omega.perron_A2_in_interval"
  , "Omega.perron_A3_in_interval"
  , "Omega.charPoly_A3_root_in_01"
  -- Round 34: Möbius 轨道扩展 + 判别式 + Pisano 周期 + Fibonacci 入口点 (Phase 39)
  , "Omega.primitive_orbit_A2_extended"
  , "Omega.primitive_orbit_A3_extended"
  , "Omega.charPoly_A2_discriminant_positive"
  , "Omega.charPoly_A3_discriminant_positive"
  , "Omega.collision_kernels_all_real_eigenvalues"
  , "Omega.perron_root_separated_by_three"
  , "Omega.pisano_period_2"
  , "Omega.pisano_period_3"
  , "Omega.pisano_period_5"
  , "Omega.pisano_period_7"
  , "Omega.pisano_period_6"
  , "Omega.fib_entry_point_21"
  -- Round 35: GM primitive orbits + universal invariants + moment base + cross-q + Hankel S_5 (Phase 40)
  -- def:pom-gm-primitive-orbits (CollisionZeta.lean:261-263)
  , "Omega.goldenMean_primitive_orbits"
  -- def:pom-collision-kernel-universal-invariants (CollisionZeta.lean:268-274)
  , "Omega.collision_kernel_universal_invariants"
  -- def:pom-moment-universal-base (CollisionZeta.lean:277-291)
  , "Omega.moment_universal_base"
  -- prop:pom-sq-cross-q-mono-six (CollisionZeta.lean:296-298)
  , "Omega.momentSum_cross_q_mono_six"
  -- prop:pom-sq-cross-q-ratios-six (CollisionZeta.lean:301-304)
  , "Omega.momentSum_cross_q_ratios_six"
  -- lem:pom-hankel-s5-3x3-det (CollisionZeta.lean:313)
  , "Omega.hankelS5_3x3_det"
  -- cor:pom-hankel-s5-3x3-det-ne-zero (CollisionZeta.lean:315-316)
  , "Omega.hankelS5_3x3_det_ne_zero"
  -- Round 36: S_q(2)/S_q(3) 闭式 + m=4 扇区分解 + DFA 线性递推 (Phase 41, CollisionZeta)
  -- prop:pom-sq-at-two-formula (CollisionZeta.lean:322-329)
  , "Omega.momentSum_at_two_formula"
  -- prop:pom-sq-at-three-formula (CollisionZeta.lean:336-340)
  , "Omega.momentSum_at_three_formula"
  -- thm:pom-sector-decomp-m4-q0/q1/q2/q3 (CollisionZeta.lean:345-348)
  , "Omega.sector_decomp_m4_q0"
  , "Omega.sector_decomp_m4_q1"
  , "Omega.sector_decomp_m4_q2"
  , "Omega.sector_decomp_m4_q3"
  -- thm:pom-dfa-linear-recurrence (CollisionZeta.lean:353-355)
  , "Omega.dfa_linear_recurrence_instances"
  -- Round 36: 跨章节审计证书 + Fibonacci 骨架 (Phase 41, Window6)
  -- thm:conclusion-master-audit-certificate (Window6.lean:277-293)
  , "Omega.master_audit_certificate"
  -- thm:conclusion-fibonacci-backbone (Window6.lean:296-300)
  , "Omega.fibonacci_backbone"
  -- Round 37: S_9/S_10 基值 (prop:pom-s9/s10-base-values, MomentSum.lean:106-113)
  , "Omega.momentSum_nine_zero"
  , "Omega.momentSum_nine_one"
  , "Omega.momentSum_nine_two"
  , "Omega.momentSum_ten_zero"
  , "Omega.momentSum_ten_one"
  , "Omega.momentSum_ten_two"
  -- Round 37: PP 指数实例 (thm:pom-pimsner-popa-index/fibonacci-instances, Window6.lean:305-315)
  , "Omega.pimsner_popa_index_instances"
  , "Omega.pimsner_popa_fibonacci_instances"
  -- Round 37: S_q(2) 扩展 q=9,10 (prop:pom-sq-at-two-extended, Window6.lean:318-320)
  , "Omega.momentSum_at_two_extended"
  -- Round 37: Real.log 入口 (thm:entropy-real-log-infrastructure, Entropy.lean:8-9)
  , "Omega.Entropy.topological_entropy_bound"
  -- Round 38: Real 路线首轮 (cor:folding-stable-syntax-entropy-logqdim 部分, Entropy.lean:14-69)
  -- Fibonacci ℝ 正性
  , "Omega.Entropy.coe_fib_pos"
  , "Omega.Entropy.stableSyntaxCount_pos"
  -- Golden ratio properties
  , "Omega.Entropy.goldenRatio_gt_one"
  , "Omega.Entropy.log_goldenRatio_pos"
  , "Omega.Entropy.goldenRatio_lt_two"
  , "Omega.Entropy.abs_goldenConj_lt_one"
  , "Omega.Entropy.goldenConj_bounds"
  -- Topological entropy ingredients
  , "Omega.Entropy.fib_ratio_tendsto"
  , "Omega.Entropy.log_continuous_at_phi"
  -- per-step 收敛：核心突破
  , "Omega.Entropy.log_fib_ratio_tendsto"
  -- Round 39: 圆维度章节前置 (Entropy.lean:111-153)
  -- 黄金比例算术几何 + 熵率比较 + Binet 公式
  , "Omega.Entropy.goldenRatio_gt_three_half"
  , "Omega.Entropy.goldenRatio_lt_five_thirds"
  , "Omega.Entropy.goldenRatio_eq_one_add_inv"
  , "Omega.Entropy.phi_irrational"
  , "Omega.Entropy.entropy_ordering_proxy"
  , "Omega.Entropy.entropy_gap_pos"
  , "Omega.Entropy.binet_formula"
  -- Round 41: Chebyshev 相位 + 熵综合证书 + S_5 Hankel 4×4 + 递推阶模式
  -- (Entropy.lean:249-278, CollisionZeta.lean:357-370)
  , "Omega.Entropy.goldenRatio_div_two_sq"
  , "Omega.Entropy.goldenRatio_half_minpoly"
  , "Omega.Entropy.entropy_comprehensive_certificate"
  , "Omega.momentSum_five_six"
  , "Omega.hankelS5_4x4_det_ne_zero"
  , "Omega.Entropy.recursion_order_pattern"
  -- Round 43: Newton 恒等式 + S_2 增长率界 + 覆盖率证书 + Binet 夹逼
  -- (CollisionZeta.lean:376-405, Window6.lean:325-343, Entropy.lean:304-311)
  , "Omega.CollisionZeta.newton_identity_A2"
  , "Omega.CollisionZeta.newton_identity_A3"
  , "Omega.CollisionZeta.newton_identity_A4_partial"
  , "Omega.CollisionZeta.momentSum_two_ratio_bounds"
  , "Omega.Window6.coverage_certificate"
  , "Omega.Entropy.fib_growth_sandwich"
  -- Round 44: 扇区扩展 + A_4 Newton 完整 + 迹幂和 + fiber sum 实例 + 连分数误差
  -- (CollisionZeta.lean:406-439, Entropy.lean:317-328)
  , "Omega.CollisionZeta.sector_decomp_m4_q4"
  , "Omega.CollisionZeta.sector_decomp_m4_q5"
  , "Omega.CollisionZeta.sector_m2_q9"
  , "Omega.CollisionZeta.sector_m2_q10"
  , "Omega.CollisionZeta.sector_m2_q12"
  , "Omega.CollisionZeta.sector_m2_q16"
  , "Omega.CollisionZeta.sector_m3_q9"
  , "Omega.CollisionZeta.sector_m3_q10"
  , "Omega.CollisionZeta.newton_A4_full"
  , "Omega.CollisionZeta.trace_power_sum_A2"
  , "Omega.CollisionZeta.trace_power_sum_A3"
  , "Omega.CollisionZeta.fiber_sum_instances"
  , "Omega.Entropy.fib_ratio_error"
  , "Omega.Entropy.fib_ratio_error_lt_one"
  -- Round 45: 跨 q 单调性 + CS 实例 + Perron 根 + 压缩增长
  -- (CollisionZeta.lean:442-483)
  , "Omega.CollisionZeta.cross_q_consistency_m4"
  , "Omega.CollisionZeta.cross_q_consistency_m3"
  , "Omega.CollisionZeta.cauchy_schwarz_instance_q3_m4"
  , "Omega.CollisionZeta.perron_root_A4_in_interval"
  , "Omega.CollisionZeta.compression_growth"
  , "Omega.CollisionZeta.compression_ratios"
  -- Round 46: Window6 — 结论/圆维度论文编号定理 (Window6.lean:347-371)
  -- thm:conclusion-externalization-index-readout-time-lower-bound
  , "Omega.readout_time_lower_bound_instances"
  , "Omega.readout_needs_at_least_one_query"
  -- prop:cdim-audit-stability-iff-badly-approximable
  , "Omega.audit_stability_golden"
  -- prop:terminal-window6-1-8-12-split
  , "Omega.split_1_8_12_arithmetic"
  -- Round 47: 圆维度高阶谱 + Zeta 迹线性递推证书
  -- (Window6.lean:374, CollisionZeta.lean:486)
  , "Omega.higher_spectrum_not_marginal_determined"
  , "Omega.CollisionZeta.trace_linear_recurrence_certificate"
  -- Round 48: ζ 有理性 + DFA 密度二分法 + 终端分支合并 + Hurwitz 前置
  -- (CollisionZeta.lean:503-549, Window6.lean:386-389)
  , "Omega.goldenMean_zeta_rational"
  , "Omega.collision_zeta_denominator_coefficients"
  , "Omega.stable_language_exponentially_sparse"
  , "Omega.density_ratio_decreasing_instances"
  , "Omega.succ_branch_at_b6"
  , "Omega.zero_is_merge_point"
  , "Omega.s4_conjugacy_classes"
  , "Omega.hurwitz_genus_zero"
  -- Round 49: Ghost 素数不相容 + Hurwitz 覆叠亏格 + Zeta 辅助
  -- (CollisionZeta.lean:556-591)
  , "Omega.ghost_prime_incompatibility_proxy"
  , "Omega.hurwitz_covering_genus"
  , "Omega.riemann_hurwitz_s4"
  , "Omega.collision_kernel_dimensions"
  , "Omega.perron_roots_all_localized"
  -- Phase 56 批量补注册: 论文标签对应定理公理审计
  -- cor:pom-s4-asymptotic, rem:pom-collision-rh-margin-a2/a3
  -- prop:zetaK-mobius-primitive, def:pom-collision-zeta-a2/a3
  -- cor:pom-s2/s3-asymptotic, prop:pom-sq-cross-q-logconvex, prop:pom-s5-hankel-det
  , "Omega.CollisionZeta.perron_root_A4_in_interval"
  , "Omega.charPoly_A2_discriminant_positive"
  , "Omega.perron_A2_in_interval"
  , "Omega.charPoly_A3_discriminant_positive"
  , "Omega.perron_A3_in_interval"
  , "Omega.primitive_orbit_A2"
  , "Omega.primitive_orbit_A3"
  , "Omega.primitive_orbit_A4"
  , "Omega.goldenMean_primitive_orbits"
  , "Omega.zeta_denom_A2_coefficients"
  , "Omega.zeta_denom_A3_coefficients"
  , "Omega.CollisionZeta.cauchy_schwarz_instance_q3_m4"
  , "Omega.hankelS5_3x3_det_ne_zero"
  , "Omega.hankelS5_4x4_det_ne_zero" ]

end Omega.Audit
