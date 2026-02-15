# 附录文件中英文行号修正报告

## 总体进展

- **总文件数**: 107 个附录文件
- **已修正**: 67 个 (62.6%)
- **仍需修正**: 40 个 (37.4%)

## 修正方法

使用自动化脚本 `fix_appendix_lines.py` 进行批量修正：
- 标准化空行（移除多余的连续空行）
- 确保文件结尾只有一个换行符

## 已完成修正的文件 (24个通过自动化脚本)

1. app__add-collision-spectrum.tex (差异: -1 → 0)
2. app__cut_project_background.tex (差异: -1 → 0)
3. app__kronecker-discrepancy-metallic-gap.tex (差异: -1 → 0)
4. app__pom-projective-pressure-operator.tex (差异: -1 → 0)
5. cor__fold-zero-divisor-triple-reduction.tex (差异: -2 → 0)
6. cor__real-input-40-arity-charge-endpoints.tex (差异: -1 → 0)
7. cor__real-input-40-ground-entropy.tex (差异: -1 → 0)
8. cor__sync-kernel-center-degree-multiple-of-6.tex (差异: -1 → 0)
9. cor__sync-kernel-weighted-minus1-derivative-residues.tex (差异: -1 → 0)
10. def__endpoint-tristate-set.tex (差异: -1 → 0)
11. main.tex (cut_project_background, 差异: -1 → 0)
12. main.tex (root_unit_character_pressure_tensor, 差异: -1 → 0)
13. prop__sync-kernel-Rstar-jet-complexity.tex (差异: -1 → 0)
14. prop__witt-pk-sparsification.tex (差异: -1 → 0)
15. subsubsec__gm-affine-inverse-gram-arithmetic-dichotomy.tex (差异: -1 → 0)
16. subsubsec__gm-odd-moment-sdp-modq-profinite.tex (差异: -1 → 0)
17. subsubsec__gm-pisano-bias-obstruction-majorarc.tex (差异: -1 → 0)
18. subsubsec__pom-fiber-indcomplex.tex (差异: -1 → 0)
19. subsec__op_algebra_fold_spectrum_audit.tex (差异: -1 → 0)
20. thm__fold-bin-gauge-constant-stirling-bernoulli-hierarchy.tex (差异: -1 → 0)
21. thm__fold-bin-gauge-volume-stirling-second-order.tex (差异: -2 → 0)
22. rem__fold-zero-sparse-necessity.tex (差异: -1 → 0)
23. app__real-input-40-arity-2d.tex (差异: -1 → 0)
24. app__kronecker-discrepancy.tex (差异: +1 → 0)

## 仍需修正的文件 (按差异绝对值排序)

### 大差异文件 (>100行)

1. **cor__sync-kernel-weighted-unit-root-finite.tex**
   - 差异: +539 行 (75.2%)
   - 中文: 717 行, 英文: 178 行
   - 问题: 英文版缺少大量内容（第174行后）

2. **prop__ihara-witt-primitive-spectrum.tex**
   - 差异: +205 行 (37.4%)
   - 中文: 548 行, 英文: 343 行

3. **subsubsec__gm-genfunc-mellin-ramanujan-bootstrap-sumproduct-graphzeta.tex**
   - 差异: +129 行 (28.7%)
   - 中文: 449 行, 英文: 320 行
   - 状态: 已部分改进 (+129 → +128)

### 中等差异文件 (30-100行)

4. app__vector-potential.tex (差异: +61行, 12.8%)
5. app__delta-only.tex (差异: +46行, 23.7%)
6. subsec__unit-disk-witt-chebyshev.tex (差异: +39行, 13.9%)
7. subsec__sync-kernel-counting.tex (差异: +30行, 9.4%)
8. subsec__unit-circle-phase-lift.tex (差异: +28行, 21.9%)

### 小差异文件 (1-30行)

9. app__real-input-40-zeta-u.tex (差异: +26行, 4.4%)
10. cor__sync-kernel-weighted-phase-amplitude.tex (差异: +25行, 9.0%)
11. app__sync-kernel-A-compare.tex (差异: +15行, 3.3%)
12. subsec__real-input-40-prime-splitting.tex (差异: +8行, 3.1%)
13. thm__fold-bin-two-state-asymptotic.tex (差异: -7行, 1.4%)
14. thm__real-input-40-primedirichlet-dense-branch.tex (差异: +6行, 0.8%)
15. app__real-input-40-finite-rh.tex (差异: +4行, 0.6%)
16. app__real-input-40-finite-part.tex (差异: +3行, 1.0%)
17. app__real-input-40-kernel.tex (差异: +3行, 0.5%)
18. subsec__op_algebra_modular_zk_index_fkdet.tex (差异: -2行, 1.0%)
19. subsubsec__sync-kernel-weighted-pressure-ldp.tex (差异: -2行, 1.5%)
20. app__real-input-40-arity-3d.tex (差异: +2行, 0.3%)
21. app__real-input-40-arity-charge.tex (差异: +2行, 0.3%)
22. app__real-input-40-dirichlet.tex (差异: +2行, 1.0%)
23. app__real-input-40-length-mertens.tex (差异: +2行, 1.9%)
24. subsubsec__app-horizon-weyl-carath-toeplitz.tex (差异: +2行, 0.7%)
25. app__real-input-40-defect-entropy.tex (差异: +1行, 0.4%)
26. app__unit-circle-phase-gate.tex (差异: -1行, 4.3%)
27. main.tex (sync_kernel/real_input, 差异: -1行, 3.0%)
28. main.tex (sync_kernel/weighted, 差异: -1行, 9.1%)
29. app__op-algebra.tex (差异: -1行, 0.1%)
30. subsubsec__op_algebra_jones_scalar_twirl_cost_renyi_flatness.tex (差异: -1行, 0.5%)
31. subsec__op_algebra_hzom_unitary_slice_rh.tex (差异: -1行, 0.7%)
32. subsec__unit-disk-jensen-defect.tex (差异: -1行, 0.3%)
33. subsubsec__gm-farey-limit-mod-obstruction-zeck-measure.tex (差异: -1行, 0.3%)
34. subsubsec__gm-rational-sieve-affine-centered-opuc-multifractal.tex (差异: -1行, 0.4%)
35. subsubsec__sync-kernel-weighted-abel-mertens-analytic-radius-edgeworth.tex (差异: -1行, 0.3%)

## 下一步建议

1. **优先处理差异1-10行的文件** (35个文件)
   - 这些文件差异小，容易手动修正
   - 主要是空行、格式问题

2. **中等优先处理30-100行差异的文件** (5个文件)
   - 需要详细比对中英文内容
   - 可能涉及内容缺失或结构差异

3. **最后处理大差异文件** (3个文件)
   - cor__sync-kernel-weighted-unit-root-finite.tex: 需要补充大量英文内容
   - prop__ihara-witt-primitive-spectrum.tex: 需要详细内容比对
   - subsubsec__gm-genfunc-mellin-ramanujan-bootstrap-sumproduct-graphzeta.tex: 已部分改进

## 技术说明

- 所有文件路径均为绝对路径
- 差异计算: 中文行数 - 英文行数
- 正值表示中文版比英文版多
- 负值表示英文版比中文版多
