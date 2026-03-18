# Publication Workspace

当前权威版本：目录化拆稿方案。
同目录下较早的平面 `.md` 文件可视为第一轮粗拆草案；后续以各子目录 `README.md` 为准。

每个目录现在至少包含：

- `README.md`：目标期刊、边界、定位
- `OUTLINE.md`：建议章节框架
- `SOURCE_MAP.md`：从总稿抽取/排除的具体来源
- `MIN_SKELETON.md`：最小可投稿核
- `MAIN_PAPER_POSITION.md`：相对主论文的位置、上游、下游和冻结边界
- `THEOREM_LIST.md`：实际可抽取的 theorem chain 与来源标签
- `CONTENT_NOTES.md`：章节写法、图表建议、裁剪顺序和风险提醒
- `BIB_SCOPE.md`：可直接开始建 bibliography 的引文范围
- `main.tex`：可直接开写的最小 LaTeX scaffold

对应总稿：

- `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence`

## 第一批

1. `2026_zeckendorf_streaming_normalization_automata_rairo_ita` → RAIRO-ITA
2. `2026_folded_rotation_histogram_certificates_siads` → SIADS
3. `2026_resolution_folding_core_symbolic_dynamics_etds` → Journal of Number Theory（回退：Integers → Journal of Integer Sequences）
4. `2026_fibonacci_moduli_cross_resolution_arithmetic_integers` → Research in Number Theory

## 第二批

1. `2026_fold_truncation_defect_stokes_dynamical_systems` → Dynamical Systems (T&F)
2. `2026_prefix_scan_error_boundary_rates_dynamical_systems` → DCDS-B（回退：Dynamical Systems）
3. `2026_cubical_stokes_inverse_boundary_readout_jdsgt` → JMAA（回退：Potential Analysis）

## 第三批（观察期）

1. `2026_recursive_addressing_prefix_sites_tac` → TAC（源材料薄、外部依赖重，待第一二批完成后评估）

## 显式冻结

以下总稿章节在第一、二批周期内不立项：

- `sections/body/pom/` (65,842 行)
- `sections/body/zeta_finite_part/` (261,269 行)
- `sections/body/conclusion/` (65,949 行)
- `sections/body/group_unification/` 除 Parry 基线外 (17,004 行)
- `sections/body/circle_dimension_phase_gate/` (17,237 行)
- `sections/body/fold_residual_time/` (280 行，可并入 fold-defect 稿)
- `sections/body/discussion/` (2,743 行)

## 总体判断

细化版比第一轮更严格地做了四种切割：

1. 把 `folding` 的"核心 symbolic dynamics"与"multiscale defect/Stokes"分开。
2. 把 `emergent_arithmetic` 的"automata/transducer"与"Fibonacci 模结构/CRT"分开。
3. 把 `spg` 的"scan error/boundary rate"与"cubical Stokes inverse"分开。
4. 把 `recursive_addressing` 从第二批降级到第三批（观察期），因为源材料不足且外部依赖过重。

2026-03-13 审查后新增的修正：

- Resolution folding core 稿正式改投 Journal of Number Theory，并同步改写为 numeration / exact-decoding 口径
- Cubical Stokes 稿目标期刊从 JDSGT 改为 JMAA（质量与内容不匹配）
- Scan error 稿目标期刊从 Dynamical Systems 改为 DCDS-B（避免与 fold-defect 稿同期刊）
- 未覆盖章节（circle_dimension_phase_gate / fold_residual_time / discussion）显式冻结
