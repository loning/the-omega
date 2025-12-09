# 附录 A：Fubini-Study 度量与速度公式 (Appendix A: Fubini-Study Metric and Velocity Formula)

在正文中，我们构建了一个宏大的物理图景：宇宙是一个在射影希尔伯特空间中演化的矢量，受制于恒定的信息-速度预算。为了让这一图景不仅仅停留在哲学隐喻的层面，我们需要展示其底层的数学骨架。

本附录将详细定义 Fubini-Study (FS) 度量，推导 FS 速度公式，并阐明它与微观 Lieb-Robinson 速度之间的严格数量关系。这是支撑全书"毕达哥拉斯恒等式"的数学基石。

![FS几何](../assets/appendix/appendix-a-fs-geometry.png)

## A.1 射影空间与距离定义

我们所讨论的物理状态空间并非普通的希尔伯特空间 $\mathcal{H}$，而是 **射影希尔伯特空间 (Projective Hilbert Space, $P(\mathcal{H})$)**。这是因为在量子力学中，两个仅相差全局相位因子的状态矢量 $|\psi\rangle$ 和 $e^{i\theta}|\psi\rangle$ 代表的是同一个物理状态。

FS 度量是 $P(\mathcal{H})$ 上唯一自然的、酉不变的黎曼度量。对于 $\mathcal{H}$ 中两个归一化的纯态矢量 $|\psi\rangle$ 和 $|\phi\rangle$（即 $\langle\psi|\psi\rangle = \langle\phi|\phi\rangle = 1$），它们在射影空间中对应点 $[\psi]$ 和 $[\phi]$ 之间的 **FS 距离** 定义为：

$$d_{FS}([\psi], [\phi]) = \arccos\left( |\langle\psi|\phi\rangle| \right)$$

这个距离具有直观的几何意义：它衡量了两个量子态之间的"区分度"。如果两个状态完全重合（$|\langle\psi|\phi\rangle|=1$），距离为 0；如果两个状态正交（$|\langle\psi|\phi\rangle|=0$），距离为 $\pi/2$。

## A.2 FS 速度与方差的关系

考虑一条由参数 $\lambda$ 描述的可微曲线 $\lambda \mapsto |\psi(\lambda)\rangle$。这代表了宇宙随时间的演化轨迹。在这条轨迹上，**FS 速度** $v_{FS}^{(\lambda)}$ 定义为切线矢量的 FS 范数：

$$v_{FS}^{(\lambda)} = \left\| \frac{d}{d\lambda}\psi(\lambda) \right\|_{FS}$$

其具体计算公式为：

$$||\partial_{\lambda}\psi||_{FS}^2 = \langle\partial_{\lambda}\psi|\partial_{\lambda}\psi\rangle - |\langle\psi|\partial_{\lambda}\psi\rangle|^2$$

在量子力学中，演化通常由一个自伴算符（生成元）$K(\lambda)$ 驱动，满足薛定谔方程形式：

$$\frac{d}{d\lambda}|\psi(\lambda)\rangle = -iK(\lambda)|\psi(\lambda)\rangle$$

将此代入速度公式，我们得到了一个至关重要的物理结论：**FS 速度严格等于生成元的标准差（不确定度）**。

$$v_{FS}^{(\lambda)} = \Delta K(\lambda) = \sqrt{\langle K^2 \rangle - \langle K \rangle^2}$$

这解释了为什么我们在正文中反复强调"速度即方差"。当宇宙在演化时，它在几何空间中跑得有多快，完全取决于其驱动哈密顿量的能量涨落 $\Delta H$。对于本征态（$\Delta H = 0$），FS 速度为零，几何时间停止，这就是"静态"的数学定义。

## A.3 物理单位与 Lieb-Robinson 速度的校准

在全书中，我们使用了一个抽象的常数 $c_{FS}$ 作为宇宙的总预算。在实际物理模型中，这个常数并非随意选取，而是由微观离散结构决定的。

在一个晶格间距为 $a$、更新时间步长为 $\Delta t$ 的 **量子元胞自动机 (QCA)** 模型中，信息在空间中传播的最大物理速度（Lieb-Robinson 速度）为：

$$v_{LR}^{(phys)} = \frac{a}{\Delta t}$$

而与之对应的，射影希尔伯特空间中的最大 FS 速度（即我们的 $c_{FS}$）被校准为：

$$c_{FS}^{max} = \frac{2\pi}{\Delta t}$$

两者之间的关系是：

$$c_{FS}^{max} = \frac{2\pi}{a} v_{LR}^{(phys)}$$

这一关系揭示了量纲的转换：

* $v_{LR}^{(phys)}$ 是 **空间速度**（米/秒）。

* $c_{FS}$ 是 **信息容量** 或 **频率**（1/秒）。

当我们说"光速限制"时，在几何上我们实际上是指宇宙的"最大信息更新频率"是有限的。在正文的推导中，为了简洁，我们通常选取自然单位制（$\hbar=1, a=1$），使得 $c_{FS}$ 与 $v_{LR}$ 在数值上成正比，从而统一了宏观与微观的描述。

## A.4 内禀时间 $\tau$

最后，我们定义全书使用的 **内禀时间 (Intrinsic Time) $\tau$**。这是一种特殊的参数化选择，使得沿轨迹的 FS 速度恒定为 $c_{FS}$：

$$||\partial_{\tau}\psi(\tau)||_{FS} \equiv c_{FS}$$

在这种参数化下，任何其他物理参数 $\lambda$（如实验室时间 $t$）与内禀时间 $\tau$ 的关系由链式法则给出：

$$\frac{d\tau}{d\lambda} = \frac{v_{FS}^{(\lambda)}}{c_{FS}} = \frac{\Delta K(\lambda)}{c_{FS}}$$

这个公式是全书所有"时间膨胀"和"时间延迟"效应的数学母体。它告诉我们：任何物理时钟的走时速率，都取决于该时钟在 FS 几何中消耗预算 $\Delta K$ 的能力。

