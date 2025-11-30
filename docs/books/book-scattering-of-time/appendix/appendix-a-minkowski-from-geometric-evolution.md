# 附录 A：从几何演化圆重构闵可夫斯基线元

**(Reconstruction of Minkowski Metric from Geometric Evolution Circle)**

本附录旨在证明：狭义相对论的核心几何结构（闵可夫斯基度规），可以被严格地推导为 Fubini-Study 几何中"扇区 Parseval 恒等式"的一个特例。

## 1. 几何设定

设宇宙状态为希尔伯特空间中的归一化向量 $\psi(\tau)$。根据公理 A1，其演化速率恒定为 $c$：

$$||\dot{\psi}(\tau)||_{FS} = c$$

## 2. 正交分解

我们引入两个正交的投影算符 $P_{ext}$（外部/空间扇区）和 $P_{int}$（内部/时间扇区）。根据 Parseval 恒等式，总演化矢量 $V$ 的模长平方等于各分量模长平方之和：

$$v_{ext}^2 + v_{int}^2 = c^2 \quad \text{(A.1)}$$

其中 $v_{ext} = ||P_{ext}\dot{\psi}||_{FS}$，$v_{int} = ||P_{int}\dot{\psi}||_{FS}$。这是正文中"伟大的权衡"的数学形式。

## 3. 物理量的识别（The Identification）

为了建立与物理世界的联系，我们做如下自然映射：

* **外部速度：** 将 $v_{ext}$ 识别为空间坐标系中的移动速度 $v = \frac{dx}{dt}$。

* **内部速度：** 将 $v_{int}$ 识别为固有时（Proper Time, $\tau$）流逝的速率。由于量纲需要，我们设 $v_{int} = c \frac{d\tau}{dt}$。

## 4. 度规的导出

将上述定义代入公式 (A.1)：

$$(\frac{dx}{dt})^2 + (c \frac{d\tau}{dt})^2 = c^2$$

两边同时乘以 $dt^2$：

$$dx^2 + c^2 d\tau^2 = c^2 dt^2$$

移项整理，得到固有时 $\tau$ 的表达式：

$$c^2 d\tau^2 = c^2 dt^2 - dx^2 \quad \text{(A.2)}$$

或者写成线元形式 $ds^2 = -c^2 d\tau^2$（采用 $-+++$ 符号惯例）：

$$ds^2 = -c^2 dt^2 + dx^2$$

这正是标准的**闵可夫斯基线元 (Minkowski Line Element)**。由此可见，洛伦兹对称性并非先验的几何公理，而是希尔伯特空间中各向同性演化在特定投影下的表现。

