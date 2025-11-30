# 附录 B：Dirac-QCA 模型的色散关系与洛伦兹破坏

**(Dispersion Relation and Lorentz Violation in Dirac-QCA)**

本附录展示当我们将连续时空离散化为量子元胞自动机（QCA）时，洛伦兹不变性如何作为一种低能近似涌现，以及高阶修正项（$O(p^4)$）的来源。

## 1. 离散演化算符

考虑一维晶格，晶格常数为 $a$，时间步长为 $\Delta t$。定义单步演化算符 $U$ 为平移算符 $S$ 和硬币算符（内部旋转）$C$ 的乘积：

$$U = S(p) \cdot C(\theta) = \begin{pmatrix} e^{ipa} & 0 \\ 0 & e^{-ipa} \end{pmatrix} \begin{pmatrix} \cos\theta & -i\sin\theta \\ -i\sin\theta & \cos\theta \end{pmatrix}$$

其中 $\theta$ 与质量相关，$p$ 为动量。

## 2. 色散关系的推导

求解本征方程 $\det(U - e^{-i\omega\Delta t}I) = 0$，我们得到严格的离散色散关系：

$$\cos(\omega \Delta t) = \cos(pa) \cos\theta$$

## 3. 连续极限与修正

在低能极限下（$p \ll 1/a$, $\omega \ll 1/\Delta t$），我们对余弦函数进行泰勒展开：

$$1 - \frac{(\omega \Delta t)^2}{2} \approx (1 - \frac{(pa)^2}{2})(1 - \frac{\theta^2}{2})$$

保留二阶项，我们恢复了狄拉克方程 $E^2 = c^2 p^2 + m^2 c^4$（其中 $c = a/\Delta t$）。

但如果我们保留更高阶项，就会发现洛伦兹破坏项：

$$E^2 \approx c^2 p^2 + m^2 c^4 - \alpha \frac{p^4}{M_{scale}^2} \quad \text{(B.1)}$$

这里的 $p^4$ 项代表了晶格结构带来的**几何饱和效应**。由于该项是动量的四次方，在低能下极难观测，这解释了为什么宏观宇宙看起来如此光滑。

