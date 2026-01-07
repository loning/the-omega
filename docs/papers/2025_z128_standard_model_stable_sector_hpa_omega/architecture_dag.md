# z128 大架构图：数学–物理双骨架 DAG

- **实线有向边（`-->`）**：直接推导 / 依赖（保持无环）
- **虚线无向边（`-.-`）**：数学概念 ↔ 物理概念的对应（字典映射；无箭头）

## 图例

- **数学节点（Math）**：
  - **命名**：以 `M_` 开头
  - **外形**：矩形 `[...]`
  - **颜色**：蓝色系（`classDef math`）
  - **含义**：闭合层的对象/构造/命题链（Tick+CAP 约束下的有限构造、折叠、锚点、连续代表等）
- **物理节点（Physics / Iface）**：
  - **命名**：以 `P_` 开头
  - **外形**：圆角矩形 `(...)`
  - **颜色**：绿色系（`classDef phys`）
  - **含义**：可操作量与观测链（协议化的可观测/可拟合/可证伪代理）
- **接口目标节点（Wish/Motive）**：
  - **外形**：圆角矩形 `(...)`
  - **颜色**：粉色系（`classDef iface`）
  - **含义**：组织语言与审计目标（不作为数学层前提，仅用于接口层/审计层叙事与选择说明）
- **对应关系（Math ↔ Physics）**：
  - **形式**：每对相邻的 `M_*` 与 `P_*` 用 **`-.-`** 连接
  - **含义**：字典式对应（无箭头，避免反向依赖误读）
- **推导关系（同骨架内部）**：
  - **形式**：用 **`-->`** 串联
  - **含义**：依赖/推导顺序（保持有向无环）

```mermaid
%%{init: {"flowchart": {"useMaxWidth": false, "nodeSpacing": 25, "rankSpacing": 40}, "themeVariables": {"fontSize": "12px"}}}%%
flowchart TB

  %% -------------------------
  %% Interface target (optional)
  %% -------------------------
  P_wish("“Wish（协议稳定目标数据）”")
  P_motive("“Motive（目标函数：误差/代价/熵）”")

  %% -------------------------
  %% Paired nodes (math rectangle, physics rounded)
  %% -------------------------
  M_tick["“Tick（读出序列性）”"]
  P_dt("“时间步（可操作 tick）”")
  M_tick -.- P_dt

  M_readout["“有限读出原语（scan/window/word）”"]
  P_obs("“有限观测对象（窗口词/事件序列）”")
  M_readout -.- P_obs

  M_cap["“CAP（有界复杂度闭合）”"]
  P_select("“有限候选族选择（可审计闭合）”")
  M_cap -.- P_select

  M_golden["“黄金分支（最小差异证书）”"]
  P_scan("“均匀扫描代理（覆盖/各向同性）”")
  M_golden -.- P_scan

  M_phi["“phi 通道（尺度语法）”"]
  P_phi("“尺度语法（分辨率基底）”")
  M_phi -.- P_phi

  M_pi["“pi 通道（回路闭合）”"]
  P_pi("“回路闭合（相位/拓扑一致性）”")
  M_pi -.- P_pi

  M_e["“e 通道（解析稳定/指数半群）”"]
  P_e("“指数半群/时间箭头（解析稳定）”")
  M_e -.- P_e

  M_fold["“分辨率折叠（Fold6：64→21）”"]
  P_fold("“稳定扇区压缩（64→21 类型）”")
  M_fold -.- P_fold

  M_anchor["“锚点（m=6，n=3）”"]
  P_screen("“屏幕图表（天球→平面）”")
  M_anchor -.- P_screen

  M_addr["“寻址基（addressing basis）”"]
  P_addr("“距离代理（寻址步数/图距离）”")
  M_addr -.- P_addr

  P_local("“局域结构（邻接/近邻）”")

  M_conn["“连接（connection）”"]
  P_conn("“连接（transport）”")
  M_conn -.- P_conn

  M_holo["“holonomy（回路不变量）”"]
  P_holo("“曲率/holonomy 响应”")
  M_holo -.- P_holo

  M_gauge["“规范补偿（gauge）”"]
  P_gauge("“规范场与冗余（gauge）”")
  M_gauge -.- P_gauge

  M_sm["“SM 标号闭合（21 稳定类型）”"]
  P_types("“稳定物质类型（粒子/场标签）”")
  M_sm -.- P_types

  M_mass["“质量/尺度闭合（latency 坐标）”"]
  P_mass("“质量=延迟/尺度（time delay）”")
  M_mass -.- P_mass

  %% -------------------------
  %% Continuum representative
  %% -------------------------
  M_equiv["“等价语义（对象=等价类）”"]
  P_equiv("“对象/可观测字典（等价类/不变泛函）”")
  M_equiv -.- P_equiv

  M_action["“连续代表作用量（Seff）”"]
  P_action("“有效作用量（Seff）”")
  M_action -.- P_action

  M_eom["“变分场方程（Einstein/YM/chi）”"]
  P_eom("“场方程（Einstein/YM/chi）”")
  M_eom -.- P_eom

  M_thermo["“热力学闭合（熵/温度/自由能）”"]
  P_thermo("“热力学（熵/温度/自由能）”")
  M_thermo -.- P_thermo

  M_grav["“overhead→引力闭合（chi/lapse/potential）”"]
  P_dyn("“弱场引力与有效密度（Poisson/rho_eff）”")
  M_grav -.- P_dyn

  P_lens("“透镜/时间延迟/红移通道”")

  M_recon["“chi 重建协议”"]
  P_recon("“chi 重建（从数据到场）”")
  M_recon -.- P_recon

  M_err["“协议→连续场误差控制”"]
  P_err("“误差预算（不确定性/鲁棒性）”")
  M_err -.- P_err

  M_qm["“量子测量闭合（POVM/Born）”"]
  P_qm("“量子测量（Born 概率）”")
  M_qm -.- P_qm

  %% -------------------------
  %% Scale flow & validation
  %% -------------------------
  M_rg["“RG：耦合运行（r 坐标）”"]
  P_rg("“耦合运行与阈值（RG）”")
  M_rg -.- P_rg

  M_cosmo["“宇宙学：分辨率流接口”"]
  P_cosmo("“宇宙学能量预算接口”")
  M_cosmo -.- P_cosmo

  M_gamma["“gamma 跨观测一致性（旋转/透镜/延迟/红移）”"]
  P_gamma("“gamma 跨观测一致性（联合拟合）”")
  M_gamma -.- P_gamma

  M_test["“可证伪输出（预测与审计）”"]
  P_test("“可证伪检验（跨观测一致性）”")
  M_test -.- P_test

  %% -------------------------
  %% Derivation edges (solid arrows)
  %% -------------------------
  P_wish --> P_motive --> P_select

  M_tick --> M_readout
  P_dt --> P_obs

  M_cap --> M_golden
  M_readout --> M_golden
  P_select --> P_scan
  P_obs --> P_scan

  M_golden --> M_phi
  P_scan --> P_phi

  M_phi --> M_pi
  M_phi --> M_e
  M_phi --> M_fold
  P_phi --> P_pi
  P_phi --> P_e
  P_pi --> P_fold

  M_pi --> M_fold
  M_fold --> M_anchor
  P_fold --> P_screen

  M_anchor --> M_addr
  P_screen --> P_addr

  P_addr --> P_local
  M_addr --> M_conn
  P_local --> P_conn

  M_conn --> M_holo
  P_conn --> P_holo

  M_holo --> M_gauge
  P_holo --> P_gauge

  M_gauge --> M_sm
  P_gauge --> P_types

  M_sm --> M_mass
  P_types --> P_mass

  M_mass --> M_rg
  P_mass --> P_rg
  P_rg --> P_cosmo

  M_tick --> M_equiv
  M_cap --> M_equiv
  M_equiv --> M_action --> M_eom --> M_grav --> M_recon --> M_err
  M_equiv --> M_thermo
  M_equiv --> M_qm

  M_grav --> M_gamma
  M_err --> M_test
  M_cosmo --> M_test
  M_qm --> M_test
  M_gamma --> M_test
  M_e --> M_test

  P_equiv --> P_action --> P_eom --> P_dyn --> P_lens --> P_gamma --> P_test
  P_lens --> P_recon --> P_err --> P_test
  P_equiv --> P_thermo --> P_test
  P_equiv --> P_qm --> P_test
  P_cosmo --> P_test

  %% -------------------------
  %% Styling (Material Design palette; math vs physics)
  %% -------------------------
  classDef iface fill:#FCE4EC,stroke:#D81B60,color:#880E4F,stroke-width:2px;
  classDef math fill:#E3F2FD,stroke:#1E88E5,color:#0D47A1,stroke-width:2px;
  classDef phys fill:#E8F5E9,stroke:#43A047,color:#1B5E20,stroke-width:2px;

  class P_wish,P_motive iface;
  class M_tick,M_readout,M_cap,M_golden,M_phi,M_pi,M_e,M_fold,M_anchor,M_addr,M_conn,M_holo,M_gauge,M_sm,M_mass,M_equiv,M_action,M_eom,M_thermo,M_grav,M_recon,M_err,M_qm,M_rg,M_cosmo,M_gamma,M_test math;
  class P_dt,P_obs,P_select,P_scan,P_phi,P_pi,P_e,P_fold,P_screen,P_addr,P_local,P_conn,P_holo,P_gauge,P_types,P_mass,P_equiv,P_action,P_eom,P_thermo,P_dyn,P_lens,P_recon,P_err,P_qm,P_rg,P_cosmo,P_gamma,P_test phys;

  style M_test stroke-width:4px;
  style P_test stroke-width:4px;
```


