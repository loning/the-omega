# 附录 A.1：FS-API 参考手册 (Appendix A.1: The FS-API Reference)

**—— 物理量到几何量的映射字典 (The Mapping Dictionary: From Physics to Geometry)**

**"要重写宇宙的逻辑，首先必须掌握它的底层指令集。"**

---

## 1. 现实的罗塞塔石碑 (The Rosetta Stone of Reality)

本书的核心论点是：我们熟知的物理定律（力学、热力学、相对论）实际上是运行在更底层几何架构上的"应用程序"。为了方便未来的"开发者"（研究者）在这个框架下进行调试或扩展，我们编制了这份 **API 参考手册**。

这份文档将标准的物理学术语翻译为 **Fubini-Study (FS) 几何** 与 **量子元胞自动机 (QCA)** 的原生语言。

## 2. 核心数据类型与常量 (Core Data Types & Constants)

在 FS-QCA 架构中，所有的物理实体都被抽象为以下几种基础数据类型：

| 物理概念 (Legacy Physics) | 源代码类型 (Source Code Type) | 定义/映射关系 |
| :--- | :--- | :--- |
| **物理状态** (State) | `Ray` (射线) | $[\psi] \in P(\mathcal{H})$，即希尔伯特空间中的一维子空间（去相位的）。 |
| **时间** (Time) | `ArcLength` (弧长) | $\tau = \int d\lambda / c_{FS}$。系统内在的演化步数计数器。 |
| **真空光速** ($c$) | `MaxThroughput` (最大吞吐量) | $c_{FS}$。系统状态更新的全局速率限制。 |
| **普朗克常数** ($\hbar$) | `ScalingFactor` (缩放因子) | 将几何角度（弧度）转换为物理作用量（焦耳·秒）的换算系数。 |
| **能量** (Energy) | `GeneratorVariance` (生成元方差) | $E \propto \Delta H$。驱动系统演化的瞬时几何速率。 |

## 3. API 方法详解 (API Methods Reference)

以下是查询宇宙系统状态的核心函数调用。所有的物理测量本质上都是在调用这些底层接口。

### 3.1 获取对象属性 (Get Attributes)

* **`GetMass()` —— 获取内部计算负载**

  * **物理定义：** 静止质量 $m$。

  * **几何定义：** 内部扇区演化速率 $v_{int}$。

  * **API 描述：** 返回对象在静止参考系下，为了维持自身存在而消耗的 $c_{FS}$ 带宽份额。

  * **公式：** $m = (\hbar / c^2) \cdot v_{int}$。

* **`GetProperTime()` —— 获取固有日志**

  * **物理定义：** 固有时 $s$。

  * **几何定义：** 轨迹在内部扇区 $V_{int}$ 上的投影长度。

  * **API 描述：** 仅当对象具有非零质量时，该函数返回有效值。对于无状态对象（光子），返回 0。

  * **公式：** $ds = (v_{int} / c_{FS}) d\tau$。

* **`GetEntanglement()` —— 获取网络连接数**

  * **物理定义：** 纠缠熵 $S_{ent}$。

  * **几何定义：** 子系统状态在环境扇区 $V_{env}$ 上的投影深度。

  * **API 描述：** 衡量当前对象与全局网络的耦合程度。高返回值意味着对象的本地行为不再独立。

### 3.2 系统完整性检查 (System Integrity Checks)

* **`ValidateBudget()` —— 验证带宽分配**

  * **描述：** 检查当前进程是否遵守广义帕塞瓦尔恒等式。

  * **断言 (Assert)：** `v_ext^2 + v_int^2 + v_env^2 == c_FS^2`。

  * **异常：** 如果不相等，系统抛出 `KernelPanic`（物理定律崩溃）。

* **`CheckCausality(Target)` —— 检查路由可达性**

  * **描述：** 验证信号是否能在给定步数内到达目标区域。

  * **断言：** `Distance(Source, Target) <= v_LR * Steps`。

  * **异常：** 违反 Lieb-Robinson 界限的操作将被系统防火墙静默丢弃（指数抑制）。

## 4. 常见物理定律的重写指南 (Rewrite Guide for Common Laws)

如果你想把一个旧的物理公式移植到新架构，请遵循以下模式：

### 4.1 薛定谔方程 (Schrödinger Equation)

* **旧代码：** $i\hbar \frac{\partial}{\partial t} |\psi\rangle = H |\psi\rangle$

* **新架构：** 这是一个 **测地线方程 (Geodesic Equation)**。

  哈密顿量 $H$ 只是定义了流形上的"切向量场"。方程描述了状态 $[\psi]$ 沿着该向量场以恒定速率 $v_{FS} \propto \Delta H$ 移动的轨迹。

  *注意：必须剥离全局相位 $e^{-iEt/\hbar}$，只关注射影空间中的相对相位演化。*

### 4.2 海森堡不确定性原理 (Heisenberg Uncertainty Principle)

* **旧代码：** $\Delta x \Delta p \ge \hbar/2$

* **新架构：** 这是一个 **带宽-分辨率权衡 (Bandwidth-Resolution Tradeoff)**。

  要将位置锁定得非常精确（$\Delta x \to 0$），你需要调用极其剧烈的动量波函数变化（$\Delta p \to \infty$）。这将导致 $v_{ext}$ 瞬间耗尽所有 $c_{FS}$ 预算，导致时间冻结（$v_{int} \to 0$）。

### 4.3 热力学第二定律 (Second Law of Thermodynamics)

* **旧代码：** $dS \ge 0$

* **新架构：** **日志追加协议 (Log Append Protocol)**。

  系统状态 $|\psi(\tau)\rangle$ 总是纯态。$S$ 只是局部观察者视角的"丢失比特计数"。由于全系统纠缠总是倾向于扩散（从特殊态向典型态演化），该计数器在概率上单调递增。

---

## 架构师注解 (The Architect's Note)

### 关于：如何调试宇宙 (How to Debug the Universe)

当你使用这份 API 手册时，请记住：

1. **不要相信坐标系：** 坐标系（$x, y, z, t$）是用户界面的装饰品。真正的物理逻辑只发生在希尔伯特空间的向量之间。永远优先计算 **重叠 (Overlap)** 和 **距离 (Distance)**。

2. **关注资源竞争：** 当你看到一个奇怪的物理现象（比如动钟变慢，或者黑洞附近的红移），不要去想"时空弯曲了"，要去想 **"谁偷走了带宽？"**。通常，你会发现是 $v_{ext}$（运动）或者 $v_{env}$（引力势/纠缠）抢占了 $v_{int}$ 的份额。

3. **没有魔法：** 所有的物理常数（$G, \hbar, c$）本质上都是系统配置参数。在 QCA 的微观实现中，它们分别对应于：

   * **$c$：** 晶格更新的最大信号速度。

   * **$\hbar$：** 几何相位的单位换算率。

   * **$G$：** 网络拓扑对流量密度的响应系数。

这份文档是你重构物理认知的起点。Happy Coding.

