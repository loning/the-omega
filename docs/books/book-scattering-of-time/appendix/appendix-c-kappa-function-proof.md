# 附录 C：散射时间延迟 $\kappa(\omega)$ 的证明

**(Proof of Scattering Time Delay Function)**

本附录证明微观粒子在相互作用区的"滞留时间"与几何路径的谱密度是等价的，即 $\kappa(\omega)$ 函数的数学构造。

## 1. 散射矩阵与时间延迟

定义散射矩阵 $S(\omega)$。Eisenbud-Wigner 时间延迟算符定义为：

$$Q(\omega) = -i S^\dagger(\omega) \frac{dS(\omega)}{d\omega} \quad \text{(C.1)}$$

其迹 $\text{tr} Q(\omega)$ 对应总的时间延迟。

## 2. 谱移函数与 Birman-Krein 公式

根据散射理论中的 Birman-Krein 公式，散射矩阵的行列式与谱移函数 $\xi(\omega)$ 相关：

$$\det S(\omega) = e^{-2\pi i \xi(\omega)}$$

对两边求对数并微分，我们得到：

$$\frac{1}{2\pi} \text{tr} Q(\omega) = -\frac{d\xi}{d\omega} = \rho_{rel}(\omega)$$

其中 $\rho_{rel}$ 是相对态密度。

## 3. 统一时间尺度函数

我们定义统一函数 $\kappa(\omega)$：

$$\kappa(\omega) := \frac{1}{2\pi} \text{tr} Q(\omega) = \frac{d\delta}{d\omega} \quad \text{(C.2)}$$

这证明了：粒子在势阱中的**滞留时间**（Delay），严格等同于希尔伯特空间中几何相位随能量变化的**绕转速率**（Winding Rate）。这就是正文中"停留即存在"的数学基础。

## 4. 实例：1D $\delta$ 势垒

对于势能 $V(x) = \Omega \delta(x)$，散射相移为 $\tan \delta(k) = -m\Omega/k$。

计算其时间延迟：

$$\Delta t(\omega) = \frac{d\delta}{d\omega} = \frac{m^2 \Omega}{k(k^2 + m^2 \Omega^2)} \quad \text{(C.3)}$$

结果显示，在共振点附近，时间延迟出现峰值，对应粒子在微观层面的"几何打结"。

