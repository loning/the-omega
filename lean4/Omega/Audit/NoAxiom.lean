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
import Omega.Folding.CollisionZetaOperator
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
  -- Phase 21: TransferMatrix — Perron-Frobenius 维度（阶段性通过）
  #print axioms Omega.Graph.goldenMeanAdjacency_has_goldenRatio_eigenvector
  #print axioms Omega.Graph.goldenMeanAdjacency_charpoly_eval_goldenRatio
  #print axioms Omega.Graph.goldenMeanAdjacency_charpoly_eval_goldenConj
  #print axioms Omega.Graph.goldenMeanAdjacencyℝ_sq
  #print axioms Omega.Graph.eigenvalue_satisfies_quadratic
  #print axioms Omega.Graph.eigenvalue_eq_goldenRatio_or_goldenConj
  #print axioms Omega.Graph.goldenConj_abs_lt_goldenRatio
  #print axioms Omega.Graph.goldenMeanAdjacency_dominates_all_real_eigenvalues
  #print axioms Omega.Graph.goldenMeanAdjacency_pf_root_eq_goldenRatio
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
  -- Round 67: PathIndSet — 路径图独立集 Fibonacci 计数 (PathIndSet.lean:310-348)
  #print axioms Omega.pathIndCount_recurrence
  #print axioms Omega.path_independent_set_count
  #print axioms Omega.path_independent_set_count'
  -- Round 102: Window6 审计稳定性 + 高阶谱 (Window6.lean:19-481)
  #print axioms Omega.supNormIntVec
  #print axioms Omega.torusSupDistZero
  #print axioms Omega.auditSeparation
  #print axioms Omega.AuditStable
  #print axioms Omega.BadlyApproximable
  #print axioms Omega.AuditStableBoxwise
  #print axioms Omega.audit_stability_iff_badly_approximable
  #print axioms Omega.PrimeSupportObj
  #print axioms Omega.supportSpectrum
  #print axioms Omega.higher_spectrum_not_determined_by_marginals
  -- Round 116: CircleDimension Fibonacci radius / Poisson time identities (CircleDimension.lean:12-43)
  #print axioms Omega.fibRadius
  #print axioms Omega.poissonTimeOfRadius
  #print axioms Omega.poissonTimeOf_fibRadius
  #print axioms Omega.one_sub_sq_of_poissonTime_param
  #print axioms Omega.one_sub_fibRadius_sq
  #print axioms Omega.one_sub_sq_of_poissonTime_param_nat
  -- Round 117: Fibonacci radius asymptotics (Entropy.lean:312-449)
  #print axioms Omega.Entropy.phi_rpow_neg_nat_tendsto_zero
  #print axioms Omega.Entropy.fib_mul_phi_neg_tendsto_inv_sqrt5
  #print axioms Omega.Entropy.fib_add_two_mul_phi_neg_tendsto_inv_sqrt5
  #print axioms Omega.Entropy.one_sub_fibRadius_sq_tendsto
  #print axioms Omega.Entropy.one_sub_fibRadius_sq_isEquivalent
  #print axioms Omega.Entropy.psi_pow_mul_inv_phi_pow
  -- Round 118: Fibonacci semigroup factorization (CircleDimension.lean:46-59)
  #print axioms Omega.fib_semigroup_factorization
  -- Round 119: Right-handed Fibonacci semigroup factorizations (CircleDimension.lean:61-84)
  #print axioms Omega.fib_semigroup_factorization_right
  #print axioms Omega.fib_semigroup_factorization_right'
  -- Round 120: Reverse KL tilted splitting (Entropy.lean:44-70)
  #print axioms Omega.Entropy.kl_reverse_tilted_split
  -- Round 121: Plateau rigidity shell (Entropy.lean:19-29)
  #print axioms Omega.Entropy.plateau_rigidity_of_nonneg_dissipation
  -- Round 122: Jeffreys dissipation rigidity (Entropy.lean:31-42)
  #print axioms Omega.Entropy.jeffreys_dissipation_rigidity
  -- Round 123: Fibonacci platform finite certificates (Entropy.lean:44-75)
  #print axioms Omega.fib_platform_certificate_of_eq_succ
  #print axioms Omega.fib_platform_certificate_of_eq_succ_succ
  -- Round 124: RH defect Fibonacci discretization shell (Entropy.lean:77-96)
  #print axioms Omega.tendsto_zero_of_nonneg_le_of_tendsto_zero
  #print axioms Omega.fibRadius_discretization_of_le_tendsto_zero
  -- Round 125: Zero-modulus lower-bound certificates (Entropy.lean:98-120)
  #print axioms Omega.zero_modulus_lower_bound_of_log_defect_bound
  #print axioms Omega.fibRadius_zero_modulus_lower_bound_of_log_defect_bound

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
  -- Phase 21: TransferMatrix — Perron-Frobenius 维度（阶段性通过）
  , "Omega.Graph.goldenMeanAdjacency_has_goldenRatio_eigenvector"
  , "Omega.Graph.goldenMeanAdjacency_charpoly_eval_goldenRatio"
  , "Omega.Graph.goldenMeanAdjacency_charpoly_eval_goldenConj"
  , "Omega.Graph.goldenMeanAdjacencyℝ_sq"
  , "Omega.Graph.eigenvalue_satisfies_quadratic"
  , "Omega.Graph.eigenvalue_eq_goldenRatio_or_goldenConj"
  , "Omega.Graph.goldenConj_abs_lt_goldenRatio"
  , "Omega.Graph.goldenMeanAdjacency_dominates_all_real_eigenvalues"
  , "Omega.Graph.goldenMeanAdjacency_pf_root_eq_goldenRatio"
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
  , "Omega.supNormIntVec"
  , "Omega.torusSupDistZero"
  , "Omega.auditSeparation"
  , "Omega.AuditStable"
  , "Omega.BadlyApproximable"
  , "Omega.audit_stability_iff_badly_approximable"
  , "Omega.AuditStableBoxwise"
  , "Omega.PrimeSupportObj"
  , "Omega.supportSpectrum"
  -- Round 47: 圆维度高阶谱 + Zeta 迹线性递推证书
  -- (Window6.lean:481, CollisionZeta.lean:486)
  , "Omega.higher_spectrum_not_determined_by_marginals"
  -- Round 116: CircleDimension Fibonacci radius / Poisson time identities
  , "Omega.fibRadius"
  , "Omega.poissonTimeOfRadius"
  , "Omega.poissonTimeOf_fibRadius"
  , "Omega.one_sub_sq_of_poissonTime_param"
  , "Omega.one_sub_fibRadius_sq"
  , "Omega.one_sub_sq_of_poissonTime_param_nat"
  -- Round 117: Fibonacci radius asymptotics
  , "Omega.Entropy.phi_rpow_neg_nat_tendsto_zero"
  , "Omega.Entropy.fib_mul_phi_neg_tendsto_inv_sqrt5"
  , "Omega.Entropy.fib_add_two_mul_phi_neg_tendsto_inv_sqrt5"
  , "Omega.Entropy.one_sub_fibRadius_sq_tendsto"
  , "Omega.Entropy.one_sub_fibRadius_sq_isEquivalent"
  , "Omega.Entropy.psi_pow_mul_inv_phi_pow"
  -- Round 118: Fibonacci semigroup factorization
  , "Omega.fib_semigroup_factorization"
  -- Round 119: Right-handed Fibonacci semigroup factorizations
  , "Omega.fib_semigroup_factorization_right"
  , "Omega.fib_semigroup_factorization_right'"
  -- Round 120: Reverse KL tilted splitting
  , "Omega.Entropy.kl_reverse_tilted_split"
  -- Round 121: Plateau rigidity shell
  , "Omega.Entropy.plateau_rigidity_of_nonneg_dissipation"
  -- Round 122: Jeffreys dissipation rigidity
  , "Omega.Entropy.jeffreys_dissipation_rigidity"
  -- Round 123: Fibonacci platform finite certificates
  , "Omega.fib_platform_certificate_of_eq_succ"
  , "Omega.fib_platform_certificate_of_eq_succ_succ"
  -- Round 124: RH defect Fibonacci discretization shell
  , "Omega.tendsto_zero_of_nonneg_le_of_tendsto_zero"
  , "Omega.fibRadius_discretization_of_le_tendsto_zero"
  -- Round 125: Zero-modulus lower-bound certificates
  , "Omega.zero_modulus_lower_bound_of_log_defect_bound"
  , "Omega.fibRadius_zero_modulus_lower_bound_of_log_defect_bound"
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
  , "Omega.hankelS5_4x4_det_ne_zero"
  -- Round 51: DFA 密度二分法 + Zeckendorf 素数 + Kraft 不等式
  -- (CollisionZeta.lean:597-627)
  , "Omega.dfa_density_dichotomy_golden_mean"
  , "Omega.zeckendorf_primes_no_short_forbidden_pattern"
  , "Omega.primes_at_each_zeckendorf_length"
  , "Omega.kraft_sum_partial_integer"
  , "Omega.kraft_sum_lt_capacity"
  -- Round 52: 里程碑 90%（CollisionZeta.lean:632-668, Window6.lean:394）
  , "Omega.constant_memory_exponential_forgetting"
  , "Omega.finite_forbidden_exp_sparse"
  , "Omega.finite_zeta_all_real_poles"
  , "Omega.zeckendorf_regular_powerlaw"
  , "Omega.mealy_regular_cannot_detect_primes"
  , "Omega.nielsen_cardinality_s4"
  , "Omega.double_discriminant_two_parameter"
  , "Omega.edge_flux_total"
  , "Omega.curvature_parenthesization"
  -- Round 53: 密度代数 + Euler 积 + 非正则 + lumpability
  -- (CollisionZeta.lean:673-691)
  , "Omega.leftce_density_algebraic_golden_mean"
  , "Omega.euler_product_dense_phases"
  , "Omega.omega_not_regular_structural"
  , "Omega.lumpability_no_self_loops"
  , "Omega.non_uniform_fibers_no_equitable_quotient"
  -- Round 54: Fredholm + Möbius综合 + cyclotomic + 谱隙
  -- (CollisionZeta.lean:693-725)
  , "Omega.fredholmDet"
  , "Omega.mobius_primitive_comprehensive"
  , "Omega.cyclotomic_at_fibonacci"
  , "Omega.spectral_gap_A2_proxy"
  , "Omega.three_eigenvalue_regimes"
  -- Round 55: 循环置换行列式 + Euler 积截断 + 留数简单极点 + 实弧收敛
  -- (CollisionZeta.lean:726-741)
  , "Omega.cycle_permutation_det_instances"
  , "Omega.euler_product_truncation_check"
  , "Omega.resolvent_residue_simple_poles"
  , "Omega.real_arc_convergence"
  -- Round 56: 截断误差衰减 + primitive矩和 + 循环块行列式符号 + primitive数据非负
  --           Fredholm-Witt乘积 + 张量GCD/LCM + 张量行列式 + Schatten范数循环
  -- (CollisionZeta.lean:743-768)  里程碑：95%覆盖率
  , "Omega.truncation_error_decay"
  , "Omega.primitive_moments"
  , "Omega.cyclic_block_det_sign"
  , "Omega.primitive_data_nonneg"
  , "Omega.fredholm_witt_product_check"
  , "Omega.tensor_gcd_lcm_instances"
  , "Omega.tensor_det_instances"
  , "Omega.schatten_norm_cyclic"
  -- Round 57: 预解算符迹跳变 + 谱流符号翻转 + 约化行列式留数 + p-典型Frobenius + Witt幽灵迹对应
  -- (CollisionZeta.lean:770-779)
  , "Omega.resolvent_trace_jump_instances"
  , "Omega.spectral_flow_sign_change"
  , "Omega.reduced_determinant_residue_golden"
  , "Omega.p_typical_frobenius_instances"
  , "Omega.witt_ghost_trace_correspondence"
  -- Round 58: CollisionZeta拆分 + Fredholm等式可判定 + 矩异常比代理 + 异常通道计数 + 群逆Vieta代理 + 对称群阶数
  -- (CollisionZetaOperator.lean:392-400)
  , "Omega.fredholm_equality_decidable_finite"
  , "Omega.moment_anomaly_ratio_proxy"
  , "Omega.anomaly_channel_count"
  , "Omega.group_inverse_vieta_proxy"
  , "Omega.symmetric_group_orders"
  -- Round 59: 里程碑99% — lumpability谱刚性 + 非均匀纤维非lumpable + 后继唯一分支 + 边通量骨架
  -- (CollisionZetaOperator.lean:405-424)
  , "Omega.lumpability_spectral_rigidity"
  , "Omega.nonlumpable_by_nonuniform_fibers"
  , "Omega.succ_unique_branch_partial"
  , "Omega.edge_flux_skeleton_totals"
  -- Round 61: 项目最终登记 — Frontier占位注册（5个前沿定理，status=frontier）
  -- (Frontier/Conjectures.lean:31-57)
  , "Omega.Frontier.FrontierSPGPoincare"
  , "Omega.Frontier.FrontierCdimPoissonLp"
  , "Omega.Frontier.FrontierCdimKLAsymptotic"
  , "Omega.Frontier.FrontierCdimKLSixthNeg"
  , "Omega.Frontier.FrontierConclusionPalindrome"
  -- Round 63: S_2 递推基础引理 (CollisionZeta.lean:401-434)
  , "fiberMultiplicity_split_last_bit"
  , "collision_kernel2_mulVec_base"
  , "collision_kernel2_mulVec_step1"
  , "collision_kernel2_mulVec_step2"
  -- Round 64: 碰撞对恒等式 — S_2(m) = collision pair count (CollisionZeta.lean:436-480)
  , "Omega.momentSum_two_eq_collision"
  , "Omega.collision_pairs_count_verified"
  -- Round 66: Fibonacci奇偶性 + 最大纤维界 + 偶奇偶性 (CollisionZeta.lean:260-303, FiberSplit.lean:232, MaxFiber.lean:178)
  , "fib_mod_two_table"
  , "fib_even_iff_mod3"
  , "fib_odd_iff_not_mod3"
  , "maxFiber_lt_half_wordcount"
  , "maxFiberMultiplicity_even_parity"
  -- Round 67: PathIndSet — 路径图独立集计数 = Fibonacci (Combinatorics/PathIndSet.lean:310-348)
  , "Omega.pathIndCount_recurrence"
  , "Omega.path_independent_set_count"
  , "Omega.path_independent_set_count'"
  -- Round 68: 隐藏位计数理论 (MaxFiberTwoStep.lean:41-207)
  -- thm:pom-hidden-bit-count — hiddenBitCount 定义 + 基例 + 递推 + 闭式
  , "Omega.hiddenBitCount_zero"
  , "Omega.hiddenBitCount_one"
  , "Omega.hiddenBitCount_recurrence"
  , "Omega.hiddenBitCount_closed"
  -- Phase 71 补充: 末位辅助引理 (MaxFiberTwoStep.lean:6-34)
  , "Omega.ofNat_last_false_of_lt"
  , "Omega.ofNat_last_true_of_ge"
  -- Phase 72: lem:pom-one-bit — 单隐藏位分解 (MaxFiberTwoStep.lean:213-272)
  , "Omega.hiddenBit_le_one"
  , "Omega.ofNat_sub_fib_of_ge"
  , "Omega.weight_eq_stableValue_add_hiddenBit"
  -- Phase 73: lem:pom-fold-congruence — Fold 等价 ↔ weight 模同余 (MaxFiberTwoStep.lean:278-300)
  , "Omega.stableValue_Fold_mod"
  , "Omega.Fold_eq_iff_weight_mod"
  -- Phase 74: 纤维同余特征化 + pointwise 递推不等式 (MaxFiberTwoStep.lean:306-431)
  , "Omega.mem_fiber_iff_weight_mod"
  , "Omega.fiberMultiplicity_eq_weight_congr_count"
  , "Omega.fiberMultiplicity_le_restrict_add"
  -- Phase 75: 全零词纤维特征化 (FiberWeightCount.lean:10-106)
  , "Omega.X.ofNat_zero"
  , "Omega.Fold_eq_allFalse_of_weight_eq_fib"
  , "Omega.fiberMultiplicity_allFalse"
  -- Phase 76: exactWeightCount 基础设施 (FiberWeightCount.lean:113-224)
  , "Omega.exactWeightCount_zero_zero"
  , "Omega.exactWeightCount_zero_succ"
  , "Omega.exactWeightCount_succ"
  , "Omega.exactWeightCount_eq_zero_of_ge_fib"
  , "Omega.fiberMultiplicity_eq_two_ewc"
  -- Phase 77: ewc 双步递推 + allFalse 纤维递推与闭式 (FiberWeightCount.lean:230-344)
  , "Omega.exactWeightCount_succ_succ"
  , "Omega.exactWeightCount_fib_shift"
  , "Omega.fiberMultiplicity_allFalse_recurrence"
  , "Omega.fiberMultiplicity_allFalse_closed"
  -- Phase 78: weightCongruenceCount + S_2 同余矩表达 (FiberWeightCount.lean:346-413)
  , "Omega.weightCongruenceCount_eq_sum_ewc"
  , "Omega.fiberMultiplicity_eq_wcc"
  , "Omega.momentSum_two_eq_congr_sq_sum"
  -- Phase 79: wcc 守恒 + S_2 末位4分裂 + 取消对称性 (FiberWeightCount.lean:414-546)
  , "Omega.weightCongruenceCount_sum"
  , "Omega.momentSum_two_lastBit_split"
  , "Omega.collision_lastBit_cancel"
  -- Phase 80: 碰撞对称性 + S_2 两项分解 + exactWeightCollision (FiberWeightCount.lean:547-629)
  , "Omega.collision_cross_symm"
  , "Omega.momentSum_two_succ_two_term"
  , "Omega.collision_same_eq_exactWeightCollision"
  -- Phase 81: crossWeightCorrelation + E00 递推与望远镜和 (CollisionDecomp.lean:226-360)
  , "Omega.exactWeightCollision_succ"
  , "Omega.exactWeightCollision_eq_sum"
  -- Phase 82: crossCorr + E(0,1) 分解 + S_2 三项展开 (CollisionDecomp.lean:362-505)
  , "Omega.crossCorr_zero_eq"
  , "Omega.collision_cross_eq_two_crossCorr"
  , "Omega.momentSum_two_succ_three_term"
  -- Phase 83: S_2 递推里程碑 (CollisionDecomp.lean:506-776)
  -- ★ 里程碑：prop:pom-s2-recurrence 无条件版本
  , "Omega.momentSum_two_eq_exact_plus_crossCorr"
  , "Omega.crossCorr_fib_prev_eq_momentSum"
  , "Omega.momentSum_two_succ_succ_expand"
  , "Omega.momentSum_two_recurrence"
  -- Phase 84: S_2 递推推论族 (MomentRecurrence.lean:1-86)
  , "Omega.momentSum_two_recurrence_sub"
  , "Omega.momentSum_two_pos'"
  , "Omega.momentSum_two_mono'"
  , "Omega.momentSum_two_strict_mono'"
  -- Phase 85: S_q 一般化矩同余表达 + S_q 正性 (MomentRecurrence.lean:86-125)
  , "Omega.momentSum_eq_congr_pow_sum"
  , "Omega.momentSum_pos'"
  -- Phase 86: S_3 基础设施 (MomentRecurrence.lean:125-164)
  , "Omega.momentSum_three_eq_triple_collision"
  , "Omega.triple_collision_iff_weight_mod"
  -- Phase 87: S_q 普适不等式 (MomentRecurrence.lean:164-203)
  , "Omega.momentSum_ge_pow'"
  , "Omega.momentSum_le_succ'"
  , "Omega.momentSum_two_mul_card_ge"
  , "Omega.momentSum_ge_card'"
  , "Omega.momentSum_upper_bound'"
  -- Phase 88: S_2 数论性质 (MomentRecurrence.lean:203-263)
  , "Omega.momentSum_two_even"
  , "Omega.momentSum_two_succ_half"
  , "Omega.momentSum_two_succ_ge_double"
  , "Omega.momentSum_two_succ_le_quadruple"
  , "Omega.momentSum_two_succ_excess"
  -- Phase 89: S_2 整除性 + E00 比较 (MomentRecurrence.lean:263-341)
  , "Omega.momentSum_two_odd_iff"
  , "Omega.momentSum_two_mod_four"
  , "Omega.momentSum_two_ge_exactWeightCollision"
  , "Omega.exactWeightCollision_double"
  , "Omega.exactWeightCollision_ge_linear"
  -- Phase 90: 递推唯一性 + S_2 高阶纯递推值 (MomentRecurrence.lean:341-396)
  , "Omega.recurrence_unique"
  , "Omega.momentSum_two_determined"
  , "Omega.momentSum_two_seven_rec"
  , "Omega.momentSum_two_eight_rec"
  , "Omega.momentSum_two_nine_rec"
  -- Phase 91: 纤维结构界 (MomentRecurrence.lean:396-436)
  , "Omega.maxFiberMultiplicity_ge_avg"
  , "Omega.maxFiberMultiplicity_le_pow"
  , "Omega.fiberMultiplicity_le_pow"
  , "Omega.maxFiberMultiplicity_ge_one"
  , "Omega.maxFiberMultiplicity_achievers_pos"
  -- Phase 92: Fibonacci Pisano mod 2 (Core/Fib.lean:107-173)
  , "Omega.fib_even_of_three_dvd"
  , "Omega.three_dvd_of_fib_even"
  , "Omega.fib_even_iff_three_dvd"
  , "Omega.fib_mod_two_period"
  , "Omega.fib_odd_iff_not_three_dvd"
  -- Phase 93: Fibonacci 求和恒等式 (Core/Fib.lean:173-257)
  , "Omega.fib_partial_sum"
  , "Omega.fib_partial_sum_from_two"
  , "Omega.fib_sq_sum"
  , "Omega.fib_even_sum"
  , "Omega.fib_odd_sum"
  -- Phase 94: 权重极值 (MomentRecurrence.lean:436-513)
  , "Omega.weight_allTrue"
  , "Omega.weight_le_allTrue"
  , "Omega.Fold_allTrue"
  , "Omega.exactWeightCount_zero_eq_one'"
  -- Phase 95: complement 对称性 (MomentRecurrence.lean:513-569)
  , "Omega.complement_involution"
  , "Omega.truncate_complement"
  , "Omega.complement_allFalse"
  , "Omega.weight_complement"
  , "Omega.exactWeightCount_symmetric"
  -- Phase 96: Fold complement 对偶 + Gauss 和 (MomentRecurrence.lean:569-602)
  , "Omega.weight_complement_sub"
  , "Omega.Fold_complement"
  , "Omega.stableValue_sum"
  -- Phase 97: Fibonacci Cube 路径独立集等价 (Combinatorics/FibonacciCube.lean:1-87)
  , "Omega.wordSupport_isPathIndependent"
  , "Omega.indSetToWord_no11"
  , "Omega.wordSupport_indSetToWord"
  , "Omega.indSetToWord_wordSupport"
  , "Omega.xEquivPathIndSet"
  -- Phase 98: popcount 定义与基值 (Combinatorics/FibonacciCube.lean:87-105)
  , "Omega.popcount_allFalse"
  , "Omega.popcount_allTrue"
  -- Phase 99: popcount 结构性质 + totalPopcount (Combinatorics/FibonacciCube.lean:105-160)
  , "Omega.popcount_not"
  , "Omega.popcount_eq_zero_iff"
  , "Omega.popcount_truncate_le"
  , "Omega.totalPopcount_zero"
  -- Phase 100: Fold 泛性质唯一性 (Folding/MaxFiberTwoStep.lean:437-475)
  , "Omega.Fold_unique_of_weight_congr"
  , "Omega.Fold_unique_of_retraction"
  , "Omega.X.eq_of_stableValue_eq'"
  , "Omega.congr_map_fiber_const"
  , "Omega.fiber_independent_of_retraction"
  -- Phase 101: S_2 交叉验证与增长界 (Folding/MomentRecurrence.lean:606-661)
  , "Omega.momentSum_two_recurrence_matches_charpoly"
  , "Omega.momentSum_two_chain"
  , "Omega.momentSum_two_ratio_bounds'"
  , "Omega.momentSum_two_excess_pos"
  , "Omega.momentSum_two_ge_two_fib"
  -- Phase 102: 纤维判别式 (Folding/MomentRecurrence.lean:665-696)
  , "Omega.hiddenBit_stable"
  , "Omega.Fold_eq_self_iff"
  , "Omega.weight_stable_eq_stableValue"
  , "Omega.ewc_stableValue_pos"
  , "Omega.fiberMultiplicity_one_imp_ewc_zero"
  , "Omega.fiberMultiplicity_ge_ewc"
  -- Phase 103: weight 满射与 ewc 正性 (Combinatorics/FibonacciCube.lean:165-203)
  , "Omega.weight_surjective"
  , "Omega.ewc_pos_of_le"
  , "Omega.fiberMultiplicity_ge_two_of_sv_le"
  -- Phase 104: Fibonacci Pisano π(3) (Core/Fib.lean:260-296)
  , "Omega.fib_div_three_iff"
  -- Phase 105: Pisano 应用 + 奇偶性 (Folding/MomentRecurrence.lean:700-738)
  , "Omega.fiberMultiplicity_allFalse_odd_iff"
  , "Omega.hiddenBit_eq_one_iff"
  , "Omega.hiddenBit_eq_zero_iff"
  , "Omega.fiber_hidden_bit_split"
  , "Omega.momentSum_two_mod_six_base"
  -- Phase 106: Fold-snoc 分解 (Folding/MaxFiberTwoStep.lean:475-498)
  , "Omega.restrict_Fold_eq"
  , "Omega.Fold_snoc_false_eq"
  , "Omega.Fold_snoc_true_eq"
  , "Omega.stableValue_Fold_snoc_false"
  , "Omega.stableValue_Fold_snoc_true"
  -- Phase 107: weight 分解 + fiber 包装 (Combinatorics/FibonacciCube.lean:203-243)
  , "Omega.weight_truncate_add"
  , "Omega.weight_pos_iff"
  , "Omega.Fold_of_stable'"
  , "Omega.fiber_self_mem"
  -- Phase 108: D(m) 上界 (Combinatorics/FibonacciCube.lean:243-278)
  , "Omega.maxFiberMultiplicity_le_fib"
  , "Omega.fiberMultiplicity_le_fib"
  , "Omega.maxFiberMultiplicity_sq_le_momentSum"
  -- Phase 109: D(m) 下界 + 无界性 (Combinatorics/FibonacciCube.lean:278-310)
  , "Omega.maxFiberMultiplicity_ge_half"
  , "Omega.maxFiberMultiplicity_ge_two"
  , "Omega.maxFiberMultiplicity_bounds"
  , "Omega.maxFiberMultiplicity_unbounded"
  , "Omega.momentSum_two_ge_maxFiber_sq"
  -- Phase 110: S_2 三重界 + snoc 嵌入 + mod 8 整除性 (Folding/MomentBounds.lean:10-78)
  , "Omega.momentSum_two_succ_le_triple"
  , "Omega.fiberMultiplicity_ge_ewc_via_snoc"
  , "Omega.momentSum_two_mod_eight"
  -- Phase 111: weight Fibonacci 展开 + S_3 末位8-分裂 (Weight.lean:59, MomentTriple.lean:49)
  , "Omega.weight_eq_fib_ite_sum"
  , "Omega.momentSum_three_lastBit_split"
  -- Phase 112: S_3 对称性简化 8→3 碰撞类 (MomentTriple.lean:107-193, 修正版 53fba8443)
  , "Omega.tripleCollisionClass_cancel_111"
  , "Omega.tripleCollisionClass_swap12"
  , "Omega.tripleCollisionClass_swap23"
  , "Omega.tripleCollisionClass_swap13"
  , "Omega.momentSum_three_succ_three_term"
  -- Phase 113: T000 = exactWeightTriple + ewt 形式 + tripleCorr 定义 (MomentTriple.lean:189-235)
  , "Omega.tripleCollisionClass_000_eq_ewcCube"
  , "Omega.momentSum_three_succ_ewt_form"
  , "Omega.tripleCorr"
  -- Phase 114: crossCorrSq 定义 + tripleCorr 等价 (MomentTriple.lean:242-259)
  , "Omega.crossCorrSqHigh"
  , "Omega.crossCorrSqLow"
  , "Omega.crossCorrSqHigh_eq_tripleCorr"
  , "Omega.crossCorrSqLow_eq_tripleCorr"
  -- Phase 115: zeckRep 单射 + stableValue-zeckRep 桥接 (FiberArithmetic.lean:479-485)
  , "Omega.zeckRep_injective"
  , "Omega.stableValue_eq_zeckRep_fib_sum"
  -- Phase 116: Fold 因式分解 + stableValue 零判定 + S_3 界 (FiberArithmeticProperties.lean:439-446, MomentTriple.lean:267-274)
  , "Omega.Fold_factorization"
  , "Omega.stableValue_eq_zero_iff"
  , "Omega.momentSum_three_ge_pow"
  , "Omega.momentSum_three_ge_two"
  -- Phase 117b: PathIndSets Fintype + card + appendFalse 单射 (FibonacciCube.lean:323-338)
  , "Omega.card_pathIndSets"
  , "Omega.appendFalse_injective"
  -- Phase 117c: popcount 紧上界 (FibonacciCube.lean:339)
  , "Omega.popcount_le_half"
  -- Phase 118: Lucas 数正性 + Lucas-Fibonacci 乘积恒等式 + Cassini (ShiftDynamics.lean:220-251)
  , "Omega.lucasNum_pos"
  , "Omega.lucasNum_mul_fib"
  , "Omega.lucasNum_cassini"
  -- Phase 119: stableValue 取负 + Fold 加法权重 (FiberArithmeticProperties.lean:454-459)
  , "Omega.stableValue_neg'"
  , "Omega.Fold_add_weight"
  -- Phase 120: S_2 差分递推 + 严格单调 (MomentTriple.lean:280-293)
  , "Omega.momentSum_two_diff_recurrence"
  , "Omega.momentSum_two_diff_strict_mono"
  -- Phase 121: S_2 Fibonacci 增长下界 (MomentTriple.lean:373)
  , "Omega.momentSum_two_fibonacci_growth"
  -- Phase 122: ewc 总和 + S_2^2 ≤ F*S_4 (FiberWeightCount.lean:434, MomentTriple.lean:394)
  , "Omega.exactWeightCount_sum"
  , "Omega.momentSum_two_sq_le_card_mul_four"
  -- Phase 123: Cauchy-Schwarz 矩 + Lucas 倍角 + ewc 零权重 (MomentTriple.lean:413/426, ShiftDynamics.lean:271)
  , "Omega.momentSum_cauchy_schwarz_general"
  , "Omega.lucasNum_double"
  , "Omega.exactWeightCount_zero"
  -- Phase 124: ewc 最大权重 + Lucas 平方 + Fold 补码模 (MomentTriple.lean:430/437, ShiftDynamics.lean:295)
  , "Omega.exactWeightCount_max"
  , "Omega.lucasNum_sq"
  , "Omega.Fold_complement_mod"
  -- Phase 125: ewc 单位权重 + ewc 层稳定 + Lucas-Fib 加法 (MomentTriple.lean:442, FiberWeightCount.lean:450, ShiftDynamics.lean:332)
  , "Omega.exactWeightCount_one"
  , "Omega.exactWeightCount_succ_of_lt"
  , "Omega.lucasNum_add_fib"
  -- Phase 126: Lucas-Fib 减法 + Fib 比率界 + stableValue 最大值存在 (ShiftDynamics.lean:345, Fib.lean:297, MomentTriple.lean:462)
  , "Omega.lucasNum_sub_fib"
  , "Omega.fib_succ_le_double"
  , "Omega.stableValue_max_achieved"
  -- Phase 127: popcount ≤ weight + Fib 倍角 Lucas 乘积 (FibonacciCube.lean:435, ShiftDynamics.lean:356)
  , "Omega.popcount_le_weight"
  , "Omega.fib_double_eq_mul_lucas"
  -- Phase 128: S_2 基值扩展 + Lucas 奇偶 + S_2 mod 16 (MomentTriple.lean:472-495, ShiftDynamics.lean:361)
  , "Omega.momentSum_two_ten_rec"
  , "Omega.momentSum_two_eleven_rec"
  , "Omega.momentSum_two_twelve_rec"
  , "Omega.lucasNum_even_iff"
  , "Omega.momentSum_two_mod_sixteen"
  -- Phase 129: E00 下界 + Lucas mod 4 整除 + E00 严格单调 (MomentTriple.lean:523/541, ShiftDynamics.lean:393)
  , "Omega.exactWeightCollision_ge_fib"
  , "Omega.lucasNum_three_dvd"
  , "Omega.exactWeightCollision_strict_mono"
  -- Phase 130: S_2 链扩展 + Lucas Cassini Nat 版 (MomentTriple.lean:545, ShiftDynamics.lean:436-445)
  , "Omega.momentSum_two_chain_extended"
  , "Omega.lucasNum_cassini_even"
  , "Omega.lucasNum_cassini_odd"
  -- Phase 131: E00 指数下界 + S_2 凸性 + EWT ≥ E00 (MomentTriple.lean:559/569/586)
  , "Omega.exactWeightCollision_ge_pow"
  , "Omega.momentSum_two_convex"
  , "Omega.exactWeightTriple_ge_collision"
  -- Phase 132: Fib-Lucas 界 + Cassini 变体 (ShiftDynamics.lean:453-466)
  , "Omega.fib_le_lucasNum"
  , "Omega.lucasNum_le_two_fib_succ"
  , "Omega.fib_succ_sq_sub_prod"
  -- Phase 133: Fib 相邻乘积 + S_2 mod 4 小基值 (ShiftDynamics.lean:482, MomentTriple.lean:600-603)
  , "Omega.fib_adjacent_product"
  , "Omega.momentSum_two_two_mod_four"
  , "Omega.momentSum_two_three_mod_four"
  -- Phase 134: 隐藏比特计数递推 + 碰撞行列式普适 (MaxFiberTwoStep.lean:501, CollisionZeta.lean:530)
  , "Omega.paper_hiddenBitCount_recurrence"
  , "Omega.paper_collision_det_universal"
  -- Phase 135: S_2 Hankel 秩精确 + 隐藏比特闭合 + S_2 三状态唯一性证书 (HankelSpectrum.lean:312, MaxFiberTwoStep.lean:507, MomentTriple.lean:608)
  , "Omega.paper_s2_hankel_rank_exact"
  , "Omega.paper_hiddenBitCount_closed"
  , "Omega.paper_s2_unique_three_state_certificate"
  -- Phase 136: 稳定加法定义 + 交换环结构 + 加法折叠公式 (FiberArithmeticProperties.lean:469,474, FiberRing.lean:213)
  , "Omega.paper_stable_add_def"
  , "Omega.paper_stable_commutative_ring"
  , "Omega.paper_add_as_fold"
  -- Phase 136b: 零代码批量补登 (FiberArithmetic.lean:61, Fold.lean:198, FiberArithmeticProperties.lean:441, FiberArithmetic.lean:483, MaxFiberTwoStep.lean:292, FiberRing.lean:139)
  , "Omega.stableMul"
  , "Omega.X.Fold_stable"
  , "Omega.Fold_factorization"
  , "Omega.stableValue_eq_zeckRep_fib_sum"
  , "Omega.Fold_eq_iff_weight_mod"
  , "Omega.stableValueRingEquiv"
  -- Phase 136c: 零代码批量补登 (Value.lean:6, Zeckendorf.lean:102, BinFold.lean:9, FiberArithmetic.lean:10, ModularTower.lean:28)
  , "Omega.stableValue"
  , "Omega.X.stableValue_eq_sum_fib_zeckIndices"
  , "Omega.cBinFold"
  , "Omega.stableAdd"
  , "Omega.modularProject_eq_restrict"
  -- Phase 137: S_2/S_3 定义 + 稳定加法无零化子 (MomentTriple.lean:618,622, FiberArithmeticProperties.lean:480)
  , "Omega.paper_def_s2"
  , "Omega.paper_def_s3"
  , "Omega.paper_stable_add_no_null"
  -- Phase 138: q-重碰撞矩定义 + Fibonacci cube 等价 + S_2 Hankel 行列式 (MomentTriple.lean:626, FibonacciCube.lean:445, HankelSpectrum.lean:317)
  , "Omega.paper_def_moment_q"
  , "Omega.paper_fibonacci_cube_equiv"
  , "Omega.paper_s2_hankel_det"
  -- Phase 138b: 零代码批量补登 10 个论文标签
  , "Omega.cFiberSpectrum"
  , "Omega.fib_even_iff_three_dvd"
  , "Omega.hankelS2_3x3_det_ne_zero"
  , "Omega.collisionKernel4"
  , "Omega.cached_cMomentSum_5_0"
  , "Omega.DigitCfg"
  , "Omega.fib_dvd_mul"
  , "Omega.fib_gcd"
  , "Omega.X.instCommRing"
  , "Omega.inverseLimitEquiv"
  -- Phase 138c: 零代码批量补登 (CollisionZeta.lean:89, CollisionKernel.lean:39,103,116, FibonacciPolynomial.lean:9)
  , "Omega.zeta_denom_A2_coefficients"
  , "Omega.collisionKernel3_trace"
  , "Omega.collisionKernel4_trace"
  , "Omega.collision_kernels_shared_invariants_triple"
  , "Omega.fibPoly"
  -- Phase 139: 碰撞 zeta 不变量 + exactWeightCount 定义 + a3 不变量 (CollisionKernel.lean:123,132, MomentTriple.lean:630)
  , "Omega.paper_collision_zeta_invariants"
  , "Omega.paper_exactWeightCount_def"
  , "Omega.paper_collision_zeta_a3_invariants"
  -- Phase 139b: 零代码批量补登 (Fold.lean:202,206, MaxFiberTwoStep.lean:213,248, Value.lean:83,6)
  , "Omega.X.Fold_idempotent"
  , "Omega.hiddenBit"
  , "Omega.weight_eq_stableValue_add_hiddenBit"
  , "Omega.carryIndicator"
  , "Omega.stableValue"
  , "Omega.X.Fold_surjective"
  -- Phase 140: 一次折叠正规形 + kappa 定义 + hiddenBit 决定权重 (FiberArithmeticProperties.lean:486, CarryDefect.lean:139, MaxFiberTwoStep.lean:512)
  , "Omega.paper_one_fold_normal_form"
  , "Omega.paper_kappa_def"
  , "Omega.fold_hiddenBit_determines_weight"
  -- Phase 140b: 零代码批量补登 (Fold.lean:202,206, FibonacciPolynomial.lean:33,55, CollisionZeta.lean:173, FiberSpectrum.lean:35, MaxFiberTwoStep.lean:483)
  , "Omega.pathIndSetPoly_eval_one"
  , "Omega.pathIndSetPoly_recurrence"
  , "Omega.perron_A2_in_interval"
  , "Omega.cMaxFiberAchievers"
  , "Omega.X.Fold_snoc_false_eq"
  -- Phase 142: 追加 4 个定理实例 (FiberArithmeticProperties.lean:490, FibonacciCube.lean:449, FibonacciPolynomial.lean:60,63)
  , "Omega.paper_fold_order_independent"
  , "Omega.paper_fibonacci_cube"
  , "Omega.pathIndSetPoly_zero_val"
  , "Omega.pathIndSetPoly_one_val"
  -- Phase 143: 论文接口包装 (CollisionZeta.lean:536,537,540)
  , "Omega.paper_trace_recurrence_A2"
  , "Omega.paper_primitive_orbit_A2"
  , "Omega.paper_discriminant_positive"
  -- Phase 144: MomentTriple 新定理 (MomentTriple.lean:635,640)
  , "Omega.weightCongruenceCount_ge_ewc"
  , "Omega.momentSum_two_excess_sum"
  -- Phase 145b: 新定理 (FiberArithmeticProperties.lean:499, MomentTriple.lean:663,686,698)
  , "Omega.paper_truncation_not_commute"
  , "Omega.sum_word_eq_sum_fiber_mul"
  , "Omega.sum_word_fiberMult_pow"
  , "Omega.momentSum_two_sq_le_pow_mul_three"
  -- Phase 146: 新定理 (MaxFiberTwoStep.lean:527,540, MomentTriple.lean:712)
  , "Omega.weight_truncate_mod"
  , "Omega.momentSum_cauchy_schwarz_word"
  , "Omega.truncation_curvature_eq_hiddenBit"
  -- Phase 147: 新定理 (FiberWeightCount.lean:459, MomentTriple.lean:737,768)
  , "Omega.sum_word_apply_weight"
  , "Omega.momentSum_log_convex"
  , "Omega.momentSum_ratio_mono"
  -- Phase 148: 新文件 MomentBounds.lean (MomentBounds.lean:13,58)
  , "Omega.card_true_at_bit"
  , "Omega.weight_total_sum"
  -- Phase 149: 新定理 (MomentBounds.lean:88,97)
  , "Omega.momentSum_four_recurrence_sub_of"
  , "Omega.exactWeightTriple_succ_bounded"
  -- Phase 150: 新文件 EWTTelescope.lean (EWTTelescope.lean:10,40,49,79,126,131)
  , "Omega.exactWeightTriple_eq_triple_exact"
  , "Omega.exactTripleCollisionClass"
  , "Omega.exactTripleClass_card_eq"
  , "Omega.exactWeightTriple_lastBit_split"
  , "Omega.exactTripleClass_fff"
  , "Omega.exactTripleClass_ttt"
  -- Phase 151: EWT 望远镜完成 (EWTTelescope.lean:142,157,174,204,232)
  , "Omega.exactTripleClass_swap12"
  , "Omega.exactTripleClass_swap23"
  , "Omega.exactTripleClass_fft_eq_ccsl"
  , "Omega.exactTripleClass_ftt_eq_ccsh"
  , "Omega.exactWeightTriple_succ"
  -- Phase 152: 新文件 S3Recurrence.lean (S3Recurrence.lean:10,15,21,40,69,76)
  , "Omega.crossCorrSqHighPrev"
  , "Omega.crossCorrSqLowPrev"
  , "Omega.tripleCollisionClass_fff_eq_exact"
  , "Omega.tripleCollisionClass_ttt_eq_exact"
  , "Omega.momentSum_three_succ_decomposition_bounded"
  , "Omega.momentSum_three_succ_ewt_form_bounded"
  -- Phase 153: S3Recurrence.lean 新定理 (S3Recurrence.lean:60,66)
  , "Omega.tripleCollisionClass_fft_mod_split_bounded"
  , "Omega.tripleCollisionClass_ftt_mod_split_bounded"
  -- Phase 154: S3Recurrence.lean 新定理 (S3Recurrence.lean:86,103,112,138)
  , "Omega.recurrence_unique_three"
  , "Omega.momentSum_three_recurrence_sub_of"
  , "Omega.momentSum_three_strict_mono_of"
  , "Omega.momentSum_three_double_of"
  -- Phase 155: S3Recurrence.lean 新定理 (S3Recurrence.lean:86,125)
  , "Omega.modular_weight_count"
  , "Omega.tripleCollisionClass_fft_eq_sum"
  -- Phase 156: S3Recurrence.lean 新定理 (S3Recurrence.lean:262,272,282,292)
  , "Omega.momentSum_three_eight_of"
  , "Omega.momentSum_three_nine_of"
  , "Omega.momentSum_three_ten_of"
  , "Omega.momentSum_three_even_of"
  -- Phase 157: T_fft mod split 通用证明突破 (S3Recurrence.lean:170,176,188,201)
  , "Omega.ewc_zero_of_ge"
  , "Omega.crossCorrSqLow_range_truncate"
  , "Omega.crossCorrSqHighPrev_range_truncate"
  , "Omega.tripleCollisionClass_fft_mod_split"
  -- Phase 158: S_3 结构分解完全闭合 (S3Recurrence.lean:242,254,268,310,355)
  , "Omega.crossCorrSqHigh_range_truncate"
  , "Omega.crossCorrSqLowPrev_range_truncate"
  , "Omega.tripleCollisionClass_ftt_eq_sum"
  , "Omega.tripleCollisionClass_ftt_mod_split"
  , "Omega.momentSum_three_eq_ewt_plus_ccs"
  -- Phase 159: S3Recurrence.lean 新定理 (S3Recurrence.lean:388,395)
  , "Omega.ccs_prime_succ_bounded"
  , "Omega.momentSum_three_recurrence_extended"
  -- Phase 161: S3Recurrence.lean 新定义+定理 (S3Recurrence.lean:406,413)
  , "Omega.shiftedTriple"
  , "Omega.shiftedTriple_eq_ccs_prime"
  -- Phase 162: CCSPrimeTelescope.lean 新文件 (CCSPrimeTelescope.lean:27,65,97,103)
  , "Omega.crossCorrSqHigh_succ_eq_prev"
  , "Omega.crossCorrSqLow_succ_eq_prev"
  , "Omega.cc_succ_eq_ccs_prime"
  , "Omega.momentSum_three_add_ewt"
  -- Phase 162b: CCSPrime8Split.lean 新文件 — S_3 无条件递推 (CCSPrime8Split.lean:341,353,371)
  , "Omega.ccs_prime_succ"
  , "Omega.exactWeightTriple_recurrence"
  , "Omega.momentSum_three_recurrence"
  -- Phase 163: CCSPrime8Split.lean 无条件定理补全 (CCSPrime8Split.lean:554,559,564,569,573,577,581)
  , "Omega.momentSum_three_strict_mono"
  , "Omega.momentSum_three_double"
  , "Omega.momentSum_three_even"
  , "Omega.momentSum_three_eight"
  , "Omega.momentSum_three_nine"
  , "Omega.momentSum_three_ten"
  , "Omega.momentSum_three_recurrence_sub"
  -- Phase 164: CCSPrime8Split.lean 新定理 (CCSPrime8Split.lean:591,598,606)
  , "Omega.momentSum_three_ge_sq_div"
  , "Omega.momentSum_three_eleven"
  , "Omega.momentSum_three_twelve"
  -- Phase 165: CCSPrime8Split.lean 桥接定理 (CCSPrime8Split.lean:626,633)
  , "Omega.exactWeightTriple_strict_mono"
  , "Omega.crossCorrSq_recurrence"
  -- Phase 166: CCSPrime8Split.lean 桥接定理 (CCSPrime8Split.lean:653)
  , "Omega.ccs_prime_recurrence" ]

end Omega.Audit
