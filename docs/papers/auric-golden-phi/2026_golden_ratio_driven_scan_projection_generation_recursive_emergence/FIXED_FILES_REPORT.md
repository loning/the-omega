# Finite-Part中等差异文件修正报告

## 已完成修正的文件 (2个)

### 1. 09_zeta_finite_04_03_subsec_arity-dirichlet-mertens-tensor_b
- **差异**: +14行（英文比中文多14行）
- **问题**: 英文版直接写入了rem:arity-335-selection-law-gp的内容，而中文版用\input引用
- **修正**: 将英文版的直接内容替换为\input语句
- **状态**: ✅ 已完成

### 2. app__delta-only
- **差异**: -46行（英文比中文少46行）
- **问题**: 英文版缺少三个corollary：
  - cor:completed-teichmueller-congruence
  - cor:completed-dwork-frobenius-tower
  - 相关证明
- **修正**: 补充了完整的三个corollary及其证明
- **状态**: ✅ 已完成

## 待处理文件 (17个)

### 优先级1: 差异10-30行（9个文件）

3. **app__real-input-40-zeta-u** (-26行)
   - 主要是语言翻译差异
   - 需检查\input语句_en后缀

4. **app__sync-kernel-A-compare** (-15行)
   - 需详细对比

5. **cor__sync-kernel-weighted-phase-amplitude** (-25行)
   - 需详细对比

6. **rem__arity-335-rational-tail** (+14行)
   - 文件大小差异显著(38K vs 46K)
   - 需详细对比内容

7. **subsec__sync-kernel-counting** (-30行)
   - 需详细对比

8. **subsec__xi-from-self-dual** (-27行)
   - 需详细对比

9. **subsec__xi-radial-counterexample-collapse** (-16行)
   - 需详细对比

10. **subsubsec__xi-fixed-slice-audit-chain** (-18行)
    - 需详细对比

11. **subsubsec__xi-quadratic-pencil-leakage-spectrum** (-22行)
    - 需详细对比

### 优先级2: 差异30-70行（9个文件）

12. **subsec__xi-near1-diffusive** (-55行)
13. **subsubsec__ramanujan-phase-lift-symmetry** (-37行)
14. **subsubsec__xi-endpoint-tomography-radial-profile** (-38行)
15. **subsubsec__xi-ramanujan-horizon-ledger-framework** (-69行)
16. **subsubsec__xi-read-reflector-completeness** (-16行)
17. **subsubsec__xi-time-protocol-conclusions** (-18行)
18. **subsubsec__xi-time-protocol-conclusions-part2** (-52行)
19. **subsubsec__xi-time-protocol-conclusions-part5** (-20行)

## 处理策略建议

1. **纯语言翻译差异**: 只需确保\input语句_en后缀正确
2. **实质内容差异**: 需逐一对比并补充缺失内容
3. **批处理方案**:
   - 对于<20行差异的文件，使用diff快速定位
   - 对于>30行差异的文件，需要完整读取对比

## 工作时间估算

- 已完成: 2个文件 (~30分钟)
- 待处理优先级1: 9个文件 (~2-3小时)
- 待处理优先级2: 9个文件 (~3-4小时)
- **总计**: ~5-7小时

## 下一步行动

建议先完成优先级1的9个文件，它们的差异较小，更容易快速修正。
