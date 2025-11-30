# 附录 D.1：核心代码库与依赖项 (Appendix D.1: The Kernel Source & Dependencies)

**—— 站在巨人的肩膀上重构代码 (Refactoring Code on the Shoulders of Giants)**

**"任何伟大的系统都不是从零开始编写的。我们引用了前人的库，但重写了调用的逻辑。"**

---

## 1. 核心源文件 (Primary Source)

本书的核心理论架构、数学推导及主要定理（包括广义帕塞瓦尔恒等式、FS 速度与 Wigner-Smith 延迟的关系、FS-Levinson 关系等）直接源于以下基础文档。这是本"重构项目"的初始 Commit。

* **[Kernel v1.0]** **Ma, Haobo.** "Time as Fubini-Study Arc-Length: A Unified Geometric Capacity Framework for Quantum, Relativistic, and Scattering Time Scales." *AELF PTE LTD., Singapore*, Dec 1, 2025.

  * *说明：* 本书是该论文的扩充与工程化诠释。所有关于 $v_{ext}^2 + v_{int}^2 = c_{FS}^2$ 的推导及 QCA 微观实现的细节均基于此工作。

## 2. 基础依赖库 (Foundational Libraries)

FS-QCA 架构并非凭空产生，它深度依赖于物理学和信息科学中久经考验的"标准库"。以下是我们在构建宇宙内核时调用的关键模块。

### 几何与量子速度限制 (Geometry & QSL)

* **Anandan, J., & Aharonov, Y.** "Geometry of Quantum Evolution." *Phys. Rev. Lett.* 65, 1697 (1990).

  * *调用功能：* 提供了射影希尔伯特空间中几何相位与距离的基础算法。

* **Mandelstam, L., & Tamm, I.** "The Uncertainty Relation Between Energy and Time in Non-relativistic Quantum Mechanics." *J. Phys. USSR* 9, 249 (1945).

  * *调用功能：* 提供了 `SpeedLimit` 的原始实现。本书将其重构为 FS 几何的测地线约束。

### 微架构与因果律 (Micro-Architecture & Causality)

* **Lieb, E. H., & Robinson, D. W.** "The Finite Group Velocity of Quantum Spin Systems." *Commun. Math. Phys.* 28, 251 (1972).

  * *调用功能：* 提供了 `v_LR` (最大信号速度) 的数学证明。这是本书第 2.2 章的核心依赖。

* **Arrighi, P.** "Quantum Cellular Automata." *Natural Computing* (2019).

  * *调用功能：* 提供了 QCA 的标准模型定义，用于替代连续场论作为底层硬件。

### I/O 接口与散射 (I/O Interface & Scattering)

* **Wigner, E. P.** "Lower Limit for the Energy Derivative of the Scattering Phase Shift." *Phys. Rev.* 98, 145 (1955).

  * *调用功能：* 定义了 `TimeDelay` 的原始概念。

* **Smith, F. T.** "Lifetime Matrix in Collision Theory." *Phys. Rev.* 118, 349 (1960).

  * *调用功能：* 定义了 `Q` 算符（Wigner-Smith 算符），这是本书第 4.1 章的核心对象。

* **Levinson, N.** "On the Uniqueness of the Potential in a Schrödinger Equation for a Given Asymptotic Phase." *Kgl. Danske Videnskab. Selskab Mat.-fys. Medd.* 25 (1949).

  * *调用功能：* 提供了拓扑校验和（束缚态计数）的原始定理。

### 系统日志与熵 (System Logs & Entropy)

* **Landauer, R.** "Irreversibility and Heat Generation in the Computing Process." *IBM J. Res. Dev.* 5, 183 (1961).

  * *调用功能：* 建立了信息擦除与物理资源消耗之间的 `Cost` 函数。

* **Fannes, M.** "A Continuity Property of the Entropy Density for Spin Lattice Systems." *Commun. Math. Phys.* 31, 291 (1973).

  * *调用功能：* 提供了熵速限制所需的连续性界限。

---

## 3. 致谢 (Acknowledgments)

**致 系统的初代架构师们 (To the Legacy Architects):**

感谢 **Albert Einstein**，虽然我们重构了您的时空代码，但您关于"几何即物理"的愿景依然是本项目的设计蓝图。

感谢 **Erwin Schrödinger** 和 **Werner Heisenberg**，你们编写的 `WaveFunction` 和 `MatrixMechanics` 类库至今仍是内核中最稳定的部分。

感谢 **Claude Shannon** 和 **Alan Turing**，是你们让我们意识到，宇宙归根结底是关于信息（Bit）与计算（Logic）的。

**致 社区贡献者 (To the Community):**

本项目深受量子信息、全息原理（AdS/CFT）以及数字物理学（Digital Physics）社区的开源精神影响。特别感谢那些敢于质疑连续时空、敢于提出"万物皆比特" (It from Bit) 的先锋们。

**致 读者与未来的黑客 (To the Reader & Future Hackers):**

这本书现在交到了你的手中。

代码已经开源，文档已经写好。

宇宙还有无数的 Bug 等着你去发现，无数的扩展模块等着你去编写。

不要满足于阅读文档，去 **运行** 它。

**EOF (End of File).**

