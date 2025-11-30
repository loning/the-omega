# 附录 E：Fubini-Study 距离与泛化力场

**(Fubini-Study Distance and Generalized Force)**

本附录将正文中"力是距离的梯度"形式化为变分原理。

在射影希尔伯特空间 $\mathbb{P}(\mathcal{H})$ 中，两点 $\psi_1, \psi_2$ 间的 Fubini-Study 距离定义为：

$$D_{FS}(\psi_1, \psi_2) = \arccos |\langle \psi_1 | \psi_2 \rangle|$$

定义广义势能 $V$ 为当前状态与目标状态（如真空态或真我轨道）之间的几何距离函数：

$$V(\psi) \propto D_{FS}^2(\psi, \psi_{target})$$

系统的演化遵循几何变分原理 $\delta S_{geo} = 0$，导致动力学方程：

$$\frac{d\psi}{d\tau} = -k \nabla_{FS} V(\psi) \quad \text{(E.1)}$$

其中 $\nabla_{FS}$ 是流形上的协变梯度。这一方程统一了物理学中的耗散运动（滑向低势能）和心理学中的目的论行为（趋向目标状态）。

