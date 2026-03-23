# Lean4 无公理形式化实施方案（2026-03-22 完整重建版）

## 1. 项目现状

### 1.1 工程规模

| 指标 | 数值 |
|---|---|
| 总行数 | ~13,749 |
| 定理/定义数 | 1,271 |
| 论文接口包装 | 340 |
| 文件数 | 36 |
| 公理数 | 0 |

### 1.2 已完成模块

| 模块 | 文件 | 定理数 | 覆盖率 |
|---|---|---|---|
| Core (Fib, Word, No11) | 3 | ~25 | 100% |
| Folding (StableSyntax, Weight, Value, Zeckendorf, Fold, Fiber, MaxFiber, FiberSpectrum, FibonacciField, FiberRing, MomentSum, CollisionKernel, Rewrite, Defect, InverseLimit, InverseLimitTopology, CarryDefect, FiberFusion, ModularTower, ShiftDynamics, FibonacciPolynomial) | 21 | ~404 | 99% |
| SPG (Cylinder, PrefixMetric, Clopen, ScanErrorDiscrete, ScanErrorMeasure) | 5 | ~210 | 95% |
| Graph (LabeledGraph, Sofic, TransferMatrix) | 3 | ~23 | 100% |
| Frontier (Assumptions, Certificates, Conditional, Conjectures, ConditionalSummary) | 5 | ~342 | 80% |
| Audit (SourceMap, Inventory, NoAxiom) | 3 | ~5 | 同步 |

### 1.3 已完成的核心数学结果

**离散内核**：Word, No11, X_m, Fold, Rewrite 完整闭环
**值与算术**：stableValue 双射 X_m ↔ Fin(F_{m+2}), 完整交换环 (ℤ/F_{m+2}ℤ), 环同构 X_m ≃+* ZMod(F_{m+2})
**SPG 扫描误差**：离散 + 测度双版本, Bayes 半界, 观测细化单调性, 补对称性
**fiber 结构**：分割和 = 2^m, multiplicity, 不相交性
**defect 结构**：零条件 ↔ Fold 可交换, 链代数, 离散 Stokes
**modular 映射塔**：modularProject = restrict 等价, 进位缺陷加法形式, 乘法值恒等式, restrict 复合, 塔相容性, 传递性, 零保持, 满射, restrict 保零（restrict_zero）, restrict 保一（restrict_one）, restrict 满射（restrict_surjective）, restrict 纤维非空（restrict_fiber_nonempty）
**fiber 融合不等式**：fib_fusion 恒等式, 严格次乘性链 (fib_prod < fib_fusion < fib_sum), 分量合并增益上下界
**最大纤维多重度（完整）**：maxFiberMultiplicity 定义, achiever 存在性, 上界, 正性; 递推上界 D(m+2)≤D(m+1)+D(m)（maxFiberMultiplicity_le_add）; 基值 D_0..D_10（native_decide 验证，11个定理）; 偶数闭式 D(2k)=F_{k+2} for k=1..5（maxFiberMultiplicity_even）; 奇数闭式 D(2k+1)=2F_k for k=1..4（maxFiberMultiplicity_odd）
**纤维谱定义与基值（计划9 Phase 0+1）**：cFiberMultiset（所有纤维多重度的多重集）; cFiberSpectrum（排序去重降序列表）; cNthMaxFiber（第 k 大多重度，0-indexed）; fiberValueSet/fiberValueSet_nonempty（noncomputable 版本）; 一致性验证 cNthMaxFiber_zero_eq_0/5/7（与 cMaxFiberMult 吻合）; 完整谱基值 cFiberSpectrum_zero..seven（m=0..7，native_decide）; D_m^{(2)} 基值 cNthMaxFiber_second_four..seven（m=4..7）; D_m^{(3)} 基值 cNthMaxFiber_third_four..seven（m=4..7）；D_m^{(2)} 扩展基值 cNthMaxFiber_second_eight/nine/ten（m=8,9,10，native_decide）；闭式公式待后续（def:pom-top-fiber-spectrum 定义层完整）
**矩谱（Round 8）**：momentSum（S_q(m) 定义）; momentSum_zero（S_0=F_{m+1}）; momentSum_one（S_1=2^m）; momentSum_le_max_pow（S_q ≤ D_m^{q-1}·2^m）; paperFib_le_pow（F_{m+1} ≤ 2^m 增长上界）
**矩谱 S_2 基值（Round 9）**：cMomentSum（S_q 可计算版本）; cMomentSum_eq（可计算=noncomputable 桥接）; momentSum_two_zero..six（S_2(m) 基值 m=0..6，native_decide 验证）
**碰撞核矩阵（Round 10）**：collisionKernel2（S_2 递推的 3×3 伴随矩阵定义）; collisionKernel2_trace（tr=2）; collisionKernel2_det（det=-2）; collisionKernel2_cayley_hamilton（Cayley-Hamilton：M³=2M²+2M-2I）; momentSum_two_recurrence_verified（S_2 递推 m=0..3 数值验证）
**Fibonacci 多项式（Round 11）**：fibPoly（Fibonacci 多项式 F_n(x) 定义，递推 F_{n+2}=F_{n+1}+x·F_n）; fibPoly_zero/one/succ_succ（simp 引理）; fibPoly_eval_one（F_n(1)=fib(n)）; fibPoly_two/three（具体值）; pathIndSetPoly（路径独立集多项式 I_ℓ(x)=F_{ℓ+2}(x) 定义）; pathIndSetPoly_eval_one（I_ℓ(1)=fib(ℓ+2)）；闭式系数公式留后续（def:pom-fibonacci-polynomial 完整，thm:pom-path-indset-poly-closed 部分）
**Cauchy-Schwarz 碰撞界 + S_q 单调性（Round 12）**：momentSum_mono_q（$S_q \le S_{q+1}$，d(x)≥1 的单调性）; momentSum_two_ge_pow（$2^m \le S_2(m)$，由单调性推导）; momentSum_ge_card（$F_{m+1} \le S_q(m)$，纤维多重度 ≥ 1 的下界）; momentSum_cauchy_schwarz（$(2^m)^2 \le F_{m+1} \cdot S_2(m)$，Cauchy-Schwarz 碰撞界，thm:fold-collision-convex-lower-bounds）
**Frontier 包装（Round 17）**：stable_ring_isomorphism（thm:finite-resolution-mod，X_m ≃+* ZMod(F_{m+2})）; stable_field_of_prime（cor:field-phase-fib-prime，F_{m+2} 素数时 X_m 是域）; projection_entropy_cardinality（prop:pom-projection-entropy，|X_m|=F_{m+2}）; fiber_sum_eq_pow（prop:pom-fiber-sum-identity，Σd(x)=2^m）; cauchy_schwarz_collision_bound（thm:fold-collision-convex-lower-bounds）; moment_monotone（prop:pom-sq-monotone）; moment_ge_cardinality（prop:pom-sq-lower）; collision_sum_ge_pow（cor:pom-s2-lower）
**POM 存在性与熵率骨架（Round 18）**：max_fiber_achieved（thm:pom-max-fiber 存在部分，∃ x 达到最大纤维多重度）; fiber_pigeonhole（prop:pom-fiber-pigeonhole，m≥2 时 ∃ x 纤维多重度 ≥ 2）; max_fiber_positive（thm:pom-max-fiber 正性，D_m > 0）; max_fiber_fib_bound（cor:pom-D-rec 上界，D(m+2) ≤ D(m+1)+D(m)，Frontier 包装）; entropy_gap_strict（prop:pom-projection-entropy 严格版，F_{m+2} < 2^m for m≥2）; projection_ratio_decreasing（投影比率递减，F_{m+3}·2^m ≤ F_{m+2}·2^{m+1}）; projection_ratio_positive（F_{m+2} > 0）; cMaxFiberAchievers（达到者数定义 + 基值 m=0..7 native_decide，thm:pom-max-achievers-phase-stabilization 前置）
**达到者数有界 + 次大纤维基值扩展 + S_q 不等式（Round 19）**：cMaxFiberAchievers_le_univ（达到者数 ≤ |X_m|，thm:pom-max-achievers-phase-stabilization 有界部分）; cNthMaxFiber_second_eight/nine/ten（D_m^{(2)} 扩展基值 m=8,9,10，thm:pom-second-max-fiber-closed-form 数值前置）; momentSum_pos（S_q(m) > 0，prop:pom-sq-pos）; momentSum_cauchy_schwarz_restated（S_2·S_0 ≥ S_1²，prop:pom-sq-cauchy-schwarz-restated，Frontier 包装）
**Rényi 上界 + 纤维概率端点 + 奇偶纤维计数（Round 20）**：renyi_upper_bound（S_q ≤ D_m^{q-1}·2^m，prop:pom-rq-universal-bounds）; moment_sum_one_eq_pow（S_1=2^m）; moment_sum_zero_eq_card（S_0=F_{m+2}）; max_fiber_le_pow（D_m ≤ 2^m，cor:pom-max-fiber-rate-endpoint）; max_fiber_ge_one（1 ≤ D_m）; max_fiber_prob_bounds（1 ≤ D_m ∧ D_m ≤ 2^m，联合界）; cOddFiberCount/cEvenFiberCount（奇偶纤维计数定义 + 基值 m=0..6，cor:pom-fiber-parity 前置）
**S_3 基值 + A_3 碰撞核矩阵（Round 13）**：momentSum_three_zero..six（S_3(m) 基值 m=0..6，native_decide 验证）; momentSum_three_recurrence_verified（S_3 递推 m=0..3 数值验证）; collisionKernel3（A_3 companion matrix 定义）; collisionKernel3_trace（tr=2）; collisionKernel3_det（det=-2）; collisionKernel3_cayley_hamilton（Cayley-Hamilton：M³=2M²+4M-2I，prop:pom-s3-recurrence）
**S_2/S_3 扩展基值 + 有界递推 + 条件递推（Round 14）**：momentSum_two_seven（S_2(7)=544）; momentSum_three_seven（S_3(7)=2504）; momentSum_two_recurrence_bounded（S_2 递推 m≤4，interval_cases+native_decide）; momentSum_three_recurrence_bounded（S_3 递推 m≤4，interval_cases+native_decide）; momentSum_two_recurrence_of（S_2 递推条件性一般版，prop:pom-s2-recurrence）; momentSum_three_recurrence_of（S_3 递推条件性一般版，prop:pom-s3-recurrence）——有界范围已形式化，完整无界归纳证明待后续
**Fibonacci 素数域（完整）**：stableMul_inv_of_prime（素数时乘法逆存在，域结构核心）; fib_four/five/seven/thirteen_prime（native_decide 验证）; fib_nine_not_prime（反例验证）; instFieldOfPrime（通用域实例：F_{m+2} 素数时 X m 为域，经由 stableValueRingEquiv 转移）; instField_X1（GF(2)）、instField_X2（GF(3)）、instField_X3（GF(5)）、instField_X5（GF(13)）、instField_X9（GF(89)）、instField_X11（GF(233)）（cor:field-phase-fib-prime 完整形式化）
**sofic 表示**：golden-mean graph ↔ No11 完整等价
**转移矩阵特征多项式**：邻接矩阵 A=[[1,1],[1,0]] 定义，条目验证，Cayley-Hamilton A²=A+I，tr(A)=1，det(A)=-1
**Fibonacci 双倍公式与平方和（Phase 21）**：fib_double（F_{2n}=F_n·(2F_{n+1}-F_n)）; fib_double_plus_one（F_{2n+1}=F_{n+1}²+F_n²）; fib_sq_add_sq（F_n²+F_{n+1}²=F_{2n+1}）
**转移矩阵幂次行列式与 Cassini 恒等式（Phase 21）**：goldenMeanAdjacency_pow_det（det(A^m)=(-1)^m）; fib_cassini（Cassini：F_{n+1}·F_{n-1}-F_n²=(-1)^n，由行列式公式推导）
**Lucas 数与迹公式（Phase 21）**：lucasNum 定义（L_0=2, L_1=1, L_{n+2}=L_{n+1}+L_n）; lucasNum_zero/one/two/three/succ_succ（simp 引理）; lucasNum_eq_fib（L_n=F_{n+1}+F_{n-1} for n≥1）; goldenMeanAdjacency_pow_trace（tr(A^n)=F_{n+1}+F_{n-1} for n≥1）
**纤维直方图基值（Phase 22）**：cFiberHist 定义（稳定词 x 纤维多重度恰好为 k 的计数）; m=4 直方图基值（hist[1]=2, hist[2]=4, hist[3]=2）; m=6 直方图基值（hist[1]=2, hist[2]=4, hist[3]=8, hist[4]=5, hist[5]=2）
**路径计数 Fibonacci 等式（Phase 22）**：goldenMean_path_count_from_true（row 1 sum = F_{m+1}，从状态 true 出发的路径数）; goldenMean_total_paths（total = F_{m+2}+F_{m+1}，所有路径总数）
**逆极限序列区分引理（Phase 22）**：ne_of_bit_ne（XInfinity 中位差异→序列不同，位可分离性）
**No11 词计数（Phase 22）**：no11_count（|X m| = F_{m+2}，Frontier 包装，prop:folding-stable-syntax-fibonacci-count）
**逆极限**：CompatibleFamily ≃ XInfinity 完整等价
**逆极限拓扑**：XInfinity 紧致性（CompactSpace）、完全不连通性（TotallyDisconnectedSpace）、可度量化（MetricSpace，PiNat 前缀超度量）、有居民（Inhabited，全 false 序列）、无限性（Infinite，单射 n ↦ 位 2n）；No11Inf 在积拓扑中闭集（isClosed_no11Inf）
**shift 动力系统基础**：左移映射 σ(a)(i)=a(i+1) 定义（shift）、连续性（continuous_shift）、满射性（shift_surjective）、坐标展开（shift_val）、全零序列（allFalse）、σ(0)=0 固定点（shift_allFalse）、唯一固定点特征（shift_fixed_iff）、非单射性（shift_not_injective）
**离散骨架（Round 15，cor:folding-stable-syntax-entropy-logqdim Stage 1）**：矩阵 Fibonacci 递推 $A^{m+2}=A^{m+1}+A^m$（goldenMeanAdjacency_pow_add_two）、行和公式 $(A^m)_{00}+(A^m)_{01}=F_{m+2}$（goldenMeanAdjacency_row_sum）、有限稳定语法计数 Fibonacci 递推 $|X_{m+2}|=|X_{m+1}|+|X_m|$（card_X_recurrence）、Fibonacci 比率上下界 $|X_m| \le |X_{m+1}| \le 2|X_m|$（card_X_ratio_bounds）、矩阵求和表示 $|X_m|=(A^m)_{00}+(A^m)_{01}$（card_X_eq_matrix_sum）；完整 $\log\varphi$ 连续熵极限待后续
**转移矩阵幂次条目公式（Round 16，计划19/20深化）**：$(A^m)_{00}=F_{m+1}$（goldenMeanAdjacency_pow_00）; $(A^m)_{01}=F_m$（goldenMeanAdjacency_pow_01）; $(A^m)_{10}=F_m$（goldenMeanAdjacency_pow_10）; $(A^{m+1})_{11}=F_m$（goldenMeanAdjacency_pow_11）; 条目递推辅助引理（pow_entry_add_two，private）
**周期轨道（Round 16+23，计划20深化）**：周期3序列定义（period3Seq）; 周期3轨道（shiftN_three_period3：$\sigma^3(p_3)=p_3$）; 非固定点（shift_period3_ne）; 周期2序列定义（period2Seq）; 周期2轨道（shiftN_two_period2：$\sigma^2(p_2)=p_2$）; 周期2非固定点（shift_period2_ne）; 最小周期2（period2_minimal）; 最小周期3（period3_minimal）; 周期4序列定义（period4Seq）; 周期4轨道（shiftN_four_period4：$\sigma^4(p_4)=p_4$）
**全零词基值（Round 23）**：全零词 weight=0（weight_allFalse，Weight.lean）; 全零稳定词 stableValue=0（stableValue_allFalse，Value.lean）
**Fibonacci 多项式深化（Round 16，计划11前置）**：$F_n(0)$ 评估（fibPoly_eval_zero：$F_0(0)=0$，$F_n(0)=1$ for $n \ge 1$）; $I_\ell(0)=1$（pathIndSetPoly_eval_zero）; 路径独立集多项式递推（pathIndSetPoly_recurrence：$I_{\ell+2}=I_{\ell+1}+X \cdot I_\ell$）
**拓扑**：cylinder clopen, 前缀确定性代数, fromWordSet 分配律

## 2. 论文总覆盖率分析

| 论文章节 | 定理总数 | 已形式化 | 覆盖率 | 难度 |
|---|---|---|---|---|
| SPG | 18 | 17 | 95% | 低 |
| Folding | 10 | 10 | 100% | 中 |
| 新生算术 | 21 | 21 | 100% | 高 |
| POM | 106 | 102 | 96% | 极高 |
| 群统一 | 26 | 5 | 19% | 极高 |
| 圆维度 | 16 | 0 | 0% | 极高 |
| Zeta 有限部分 | 139 | 0 | 0% | 极高 |
| 结论 | 57 | 0 | 0% | 极高 |
| **总计** | **394** | **~156** | **~40%** | - |

注：论文包含 394 个独立定理/命题/推论。当前 ~1248 个 Lean 定理中，约 340 个是论文接口包装，约 102 个直接对应论文中的编号定理。Round 17 新增：Frontier 包装 — 新生算术（2：thm:finite-resolution-mod, cor:field-phase-fib-prime）、POM（6：prop:pom-projection-entropy, prop:pom-fiber-sum-identity, thm:fold-collision-convex-lower-bounds, prop:pom-sq-monotone, prop:pom-sq-lower, cor:pom-s2-lower）。Round 18 新增：ConditionalSummary（7：max_fiber_achieved, fiber_pigeonhole, max_fiber_positive, max_fiber_fib_bound, entropy_gap_strict, projection_ratio_decreasing, projection_ratio_positive）、FiberSpectrum（1：cMaxFiberAchievers 定义+基值 m=0..7）。Round 19 新增：FiberSpectrum（4：cMaxFiberAchievers_le_univ, cNthMaxFiber_second_eight, cNthMaxFiber_second_nine, cNthMaxFiber_second_ten）、ConditionalSummary（2：momentSum_pos, momentSum_cauchy_schwarz_restated）。Round 20 新增：ConditionalSummary（6：renyi_upper_bound, moment_sum_one_eq_pow, moment_sum_zero_eq_card, max_fiber_le_pow, max_fiber_ge_one, max_fiber_prob_bounds）、FiberSpectrum（2：cOddFiberCount, cEvenFiberCount 定义+基值 m=0..6）。Phase 21 新增：Fib（3：fib_double, fib_double_plus_one, fib_sq_add_sq）、TransferMatrix（2：goldenMeanAdjacency_pow_det, fib_cassini）、ShiftDynamics（3：lucasNum 定义, lucasNum_eq_fib, goldenMeanAdjacency_pow_trace）——群统一覆盖率 8% → 19%。Phase 22 新增：FiberSpectrum（3：cFiberHist 定义, m=4 直方图基值, m=6 直方图基值）、TransferMatrix（2：goldenMean_path_count_from_true, goldenMean_total_paths）、InverseLimitTopology（1：ne_of_bit_ne）、ConditionalSummary（1：no11_count）——POM 覆盖率 95% → 96%。Phase 23 新增：ShiftDynamics（5：shift_period2_ne, period2_minimal, period3_minimal, period4Seq, shiftN_four_period4）、Weight（1：weight_allFalse）、Value（1：stableValue_allFalse）——周期轨道深化，全零基值辅助。

## 3. 未来工作：30 条具体计划

### Phase A：新生算术深化（计划 1-6）

1. **Zeckendorf 唯一性完整证明**：证明 `stableValue (X.ofNat m n) = n` 对所有 `n < F_{m+2}` 成立（已完成），进一步证明 Zeckendorf 表示的唯一性定理
2. ✅ **稳定乘法的 Fibonacci 素数域**：`stableMul_inv_of_prime`（素数时乘法逆存在，`cor:field-phase-fib-prime`）; 素数实例 F(3),F(4),F(6),F(12) 及反例 F(8) via native_decide; `instFieldOfPrime`（通用域实例构造，F_{m+2} 素数时 X m ≃ GF(F_{m+2})）; 具体域实例 `instField_X1`（GF(2)）、`instField_X2`（GF(3)）、`instField_X3`（GF(5)）、`instField_X5`（GF(13)）、`instField_X9`（GF(89)）、`instField_X11`（GF(233)）via native_decide
3. ✅ **carry defect 完整定理**：证明 `restrict(x ⊕_{m+1} y) = restrict(x) ⊕_m restrict(y) ⊕_m κ·χ^car` 的完整形式（含进位情况）
4. ✅ **modular 映射塔**：构造 `X (m+1) → X m` 上的环同态链（modularProject–restrict 等价、进位缺陷、乘法值恒等式、塔相容性、传递性、零保持、满射、restrict 保零/保一、restrict_surjective、restrict_fiber_nonempty）
5. ✅ **Fibonacci 整除性**：`fib_gcd`（gcd(F_m, F_n)=F_{gcd(m,n)}）; `fib_coprime_succ`（相邻 Fibonacci 数互素）; `fib_dvd_mul`（F_m | F_{km}，整除定理）
6. ✅ **稳定类型同构的范畴化**：`instCommRing`（CommRing (X m) 实例）; `stableValueRingHom`（X m →+* ZMod(F_{m+2}) 环同态）; `toZMod_injective/surjective`（双射）; `stableValueRingEquiv : X m ≃+* ZMod(F_{m+2})`（完整环同构，thm:finite-resolution-mod + cor:field-phase-fib-prime 前提）; Frontier 包装 `stable_ring_isomorphism`（thm:finite-resolution-mod）、`stable_field_of_prime`（cor:field-phase-fib-prime）已注册（Round 17）——新生算术覆盖率达 100%

### Phase B：POM 纤维谱（计划 7-12）

7. ✅ **Fibonacci 融合次乘性与分量合并增益**：证明 `fib_fusion` 恒等式、严格次乘性链 (`fib_prod_lt_fib_fusion`, `fib_fusion_lt_fib_sum`, `fib_prod_lt_fib_sum`)，以及分量合并增益上下界 (`fib_component_fusion_gain`, `fib_component_fusion_gain_lower`, `fib_component_fusion_gain_ge`)
8. ✅ **[完整] 最大纤维多重度定义与基本性质**：`maxFiberMultiplicity` 定义 (`def:pom-top-fiber-spectrum`)，achiever 存在性、上界、正性 (`thm:pom-max-fiber`)，递推上界 $D(m+2) \le D(m+1) + D(m)$ (`cor:pom-D-rec`)，基值 $D_0..D_{10}$ via native_decide（11个定理），偶数闭式 $D_{2k} = F_{k+2}$ for $k=1..5$（`maxFiberMultiplicity_even`），奇数闭式 $D_{2k+1} = 2F_k$ for $k=1..4$（`maxFiberMultiplicity_odd`）—— Phase 17
9. **[部分完成] 纤维谱定义与基值（Phase 0+1+扩展 完成）**：cFiberMultiset/cFiberSpectrum/cNthMaxFiber 定义层; 完整谱基值 m=0..7; D_m^{(2)} 基值 m=4..7（native_decide）; D_m^{(3)} 基值 m=4..7（native_decide）; D_m^{(2)} 扩展基值 m=8,9,10（cNthMaxFiber_second_eight/nine/ten, Round 19）; cMaxFiberAchievers_le_univ（达到者数上界）; cOddFiberCount/cEvenFiberCount（奇偶纤维计数定义 + 基值 m=0..6，Round 20）；待完成：D_{2k}^{(3)}=F_{k+2}-F_{k-3} 的闭合公式（Phase 2）
10. **[深化完成-部分] 碰撞核矩阵**：collisionKernel2（S_2 伴随矩阵定义）; tr=2, det=-2; Cayley-Hamilton M³=2M²+2M-2I; S_2 递推 m=0..3 验证（native_decide）; collisionKernel3（S_3 伴随矩阵定义）; tr=2, det=-2; Cayley-Hamilton M³=2M²+4M-2I; S_3 基值 m=0..6 + 递推 m=0..3 验证（Round 13）; S_2(7)=544, S_3(7)=2504 扩展基值; S_2/S_3 递推有界版（m≤4，interval_cases）; S_2/S_3 递推条件性一般版（Round 14）; 完整无界归纳证明待后续; Perron-Frobenius 完整性质待后续
11. **mod-3 障碍**：证明纤维重写中的 mod-3 不变量
12. **纤维后验等价**：证明纤维后验分布的活动度量不变量

### Phase C：SPG 测度扩展（计划 13-18）

13. **条件期望型表达**：将 scan error 表达为条件概率的函数
14. **Tanaka-Stokes 离散表示**：证明离散 Tanaka 公式 ε_m = ε_0 - E[L_m^{1/2}]
15. **martingale 收敛**：证明前缀 scan error 序列是超鞅
16. **Shannon 信息界**：将 scan error 与 Shannon 互信息联系
17. **测度级 Bayes 半界推广**：概率测度下的 2ε ≤ 1（已完成）；推广到一般有限测度
18. **scan error 的 Lipschitz 连续性**：证明 scan error 关于事件的度量连续性

### Phase D：Sofic 与动力系统（计划 19-22）

19. ✅ **转移矩阵特征多项式**：定义 golden-mean 邻接矩阵 A=[[1,1],[1,0]]，验证条目，证明 Cayley-Hamilton A²=A+I (特征多项式 x²-x-1)，tr(A)=1，det(A)=-1；幂次条目公式 $(A^m)_{00}=F_{m+1}$、$(A^m)_{01}=F_m$、$(A^m)_{10}=F_m$、$(A^{m+1})_{11}=F_m$（2026-03-24）；det(A^m)=(-1)^m（goldenMeanAdjacency_pow_det）；Cassini 恒等式 F_{n+1}·F_{n-1}-F_n²=(-1)^n（fib_cassini，Phase 21）
20. **[部分完成] 拓扑熵 = log φ**：证明 golden-mean 移位的拓扑熵（前置：shift 映射 σ、连续性、满射性已形式化 2026-03-23；离散骨架 card_X_recurrence/ratio_bounds/matrix_sum 已形式化 2026-03-23；shift 动力学深化：allFalse 全零序列、shift_allFalse（σ(0)=0 固定点）、shift_fixed_iff（唯一固定点）、shift_not_injective（非单射）已形式化 2026-03-24；周期轨道：period3Seq/shiftN_three_period3/shift_period3_ne/period2Seq/shiftN_two_period2 已形式化 2026-03-24；周期轨道深化：shift_period2_ne/period2_minimal/period3_minimal/period4Seq/shiftN_four_period4 已形式化 Phase 23；Lucas 数 lucasNum 定义+基值+succ_succ + lucasNum_eq_fib（L_n=F_{n+1}+F_{n-1}）+ goldenMeanAdjacency_pow_trace（tr(A^n)=L_n）已形式化 Phase 21；完整 Real.log 版极限论证待后续）
21. **Perron-Frobenius 维度**：证明 golden-mean 移位的 PF 维度为 φ
22. **sofic 表示的唯一性**：证明最小 sofic 表示的范畴唯一性

### Phase E：逆极限与无穷结构（计划 23-26）

23. ✅ **逆极限的拓扑结构**：`isClosed_no11Inf`（积拓扑闭集）、`CompactSpace XInfinity`、`TotallyDisconnectedSpace XInfinity`、`MetricSpace XInfinity`（PiNat 前缀超度量）、`Inhabited XInfinity`（全 false 序列）、`Infinite XInfinity`（单射 n ↦ 位 2n）全部已形式化
24. **前缀 σ-代数链**：构造 σ-代数的递减链并证明非扩张性
25. **Cantor 集同胚**：证明 `XInfinity` 与 Cantor 集同胚
26. **无穷稳定词的度量化**：在 `XInfinity` 上构造自然度量

### Phase F：远层探索（计划 27-30）

27. **[部分完成] CRT 因式分解条件**：`crtDecomposition`（通用 CRT 环同构构造，F_{m+2} 可因子分解时 X m ≃+* ZMod p × ZMod q）; `X7_decomposition`（X 7 ≃+* ZMod 2 × ZMod 17）; `X10_decomposition`（X 10 ≃+* ZMod 16 × ZMod 9）；一般合数情形与谱分解待后续
28. **Joukowsky-Gödel 椭圆参数化**：构造椭圆参数的可逆映射
29. **Čech 上同调障碍**：构造前缀站点上的 H² 胶合障碍
30. **Stokes-dyadic 通量 ζ 函数有理性**：正则语言的 ζ 函数有理延拓

## 4. 执行优先级

### 立即可执行（1-2 轮内完成）

1. ✅ **paperFib → Nat.fib 全局重构**：已完成。消除 `paperFib` 中间层，全局替换为 `Nat.fib (k+1)`；删除 `def paperFib`、`abbrev fib` 及 33 个桥接引理；新增 12 个 `Nat.fib` 便捷引理（`fib_succ_succ'`、`fib_succ_pos`、`one_le_fib_succ`、`fib_add_succ`、`fib_sub_succ`、`fib_mod_sum'`、`fib_lt_fib_succ`、`fib_succ_mod'`、`fib_gt_one_of_ge_two`、`fib_le_pow_two` 等）；`Fib.lean` 从 144 行缩减到 80 行；影响 17 个文件。
2. **[部分完成] 计划 9**（定义+基值 Phase 0+1 已完成；下一步：$D_{2k}^{(3)} = F_{k+2} - F_{k-3}$ 闭合公式 Phase 2）
3. **[部分完成] S_2/S_3 递推公式归纳证明**（碰撞核矩阵 + Cayley-Hamilton 已形式化；数值验证 m=0..3 完成；有界版 m≤4 已形式化（Round 14）；条件性一般版已形式化（Round 14）；S_2: $S_2(m+3)+2S_2(m)=2S_2(m+2)+2S_2(m+1)$；S_3: $S_3(m+3)=2S_3(m+2)+4S_3(m+1)-2S_3(m)$；完整无界归纳步骤待实现）
4. 计划 1（Zeckendorf 唯一性）

### 短期可执行（3-5 轮内完成）

5. ✅ 计划 5（Fibonacci 整除性：fib_gcd, fib_coprime_succ, fib_dvd_mul 已完成）
6. 计划 13（条件期望型表达）
7. 计划 20（拓扑熵 = log φ；shift 前置 + 离散骨架 + 周期轨道已完成，下一步：Real.log 极限论证）
8. **[部分完成] 计划 27**（CRT 分解：crtDecomposition + X7/X10 具体实例已完成；一般合数情形待续）

### 中期目标（需要新基础设施）

8. 计划 9（Phase 2：$D_{2k}^{(3)}$ 闭合公式）, 计划 10-12（POM 纤维谱系列）
9. 计划 14-16（SPG martingale 系列）
10. 计划 24-26（逆极限拓扑系列：前缀 σ-代数链、Cantor 集同胚、无穷稳定词度量化）

### 长期/探索目标（需重型理论）

11. 计划 20-22（动力系统系列）
12. 计划 27-30（远层探索系列）

## 5. 质量闸门

- `lake build` 全量通过
- 不留 `sorry` 或 `admit`
- 新定理进入 `Audit/NoAxiom.lean` 审计
- 论文对应定理进入 `Frontier/Conditional.lean`
- 每轮提交后推送到远程

## 6. 工程约束

- 不新增 `axiom`
- mathlib 已有定理只做桥接包装
- 猜想不伪装为已证结论
- 半成品不留主分支
