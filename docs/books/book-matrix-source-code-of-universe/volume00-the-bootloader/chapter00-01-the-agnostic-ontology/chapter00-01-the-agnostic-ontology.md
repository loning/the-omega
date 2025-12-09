# 第0.1章：不可知论本体 (Chapter 0.1: The Agnostic Ontology)

![The Agnostic Ontology](../../assets/agnostic_ontology.png)

**—— 为什么物理学是一种投影 (Why Physics is a Projection)**

**"我们无法直接读取硬件（本体），我们只能看到接口（Interface）的输出。"**

---

## 1. 表征立场：从"本体"到"接口" (The Representational Stance)

在启动任何系统内核之前，我们必须先定义系统的数据模型。在传统的物理学视角中，物理学家往往试图回答"宇宙实际上是什么"的问题。这是一种本体论（Ontology）上的执念，它假设观察者可以跳出系统，以某种上帝视角审查底层的"硬件实现"。

在本书中，我们采取一种更为务实的系统工程视角，称之为 **表征立场 (The Representational Stance)**。

我们要声明：我们对宇宙的"真实本体"一无所知，且不需要知道。作为系统内部的观察者，我们只能访问系统的 **公共接口 (Public Interface)**。所有的物理定律——无论是牛顿力学、广义相对论还是量子场论——本质上都是我们为了理解系统行为而构建的 **"表征" (Representations)** 或 **"投影视图" (Projection Views)**。

物理学的任务，不是去猜测黑盒（Black Box）里装的是什么材质的齿轮，而是去逆向工程出它的 **API 文档**。如果一套数学结构能够无损地容纳所有 API 的返回数据，并准确预测系统的响应，那么这套结构就是我们要寻找的"源代码"。

## 2. 希尔伯特空间：宇宙的通用缓冲区 (The Hilbert Space as Universal Buffer)

如果我们要设计一个能够兼容所有物理现象（从量子叠加到时空演化）的通用数据容器，最佳的选择是什么？

历史经验表明，时空流形（Spacetime Manifold）并不是最底层的容器，因为它难以自然地容纳量子非定域性。相比之下，**复可分希尔伯特空间 (Complex Separable Hilbert Space, $\mathcal{H}$)** 展现出了惊人的适应性。我们将希尔伯特空间视为宇宙的 **通用缓冲区 (Universal Buffer)**。

然而，原始的希尔伯特空间包含了冗余数据——**全局相位 (Global Phase)**。对于物理状态而言，矢量 $|\psi\rangle$ 和 $e^{i\theta}|\psi\rangle$ 描述的是完全相同的现实。这种冗余在系统设计中被称为"未规范化的数据" (Unnormalized Data)。为了构建高效的内核，我们必须对这个缓冲区进行清洗，提取出其几何本质。

## 3. 数学基础：射影几何与相位剔除 (Math Foundation: Projective Geometry)

为了形式化这一思想，我们引入 **射影希尔伯特空间 (Projective Hilbert Space)** 的概念。这是本书后续所有推导的几何舞台。

### 定义 0.1.1 (射线与等价类 / Rays and Equivalence Classes)

令 $\mathcal{H}$ 为一个复希尔伯特空间。对于任意非零矢量 $\psi \in \mathcal{H}$，我们定义物理状态不是矢量本身，而是 $\mathcal{H}$ 中的 **射线 (Ray)**，即一维子空间：

$$[\psi] = \{ c\psi : c \in \mathbb{C}, c \neq 0 \}$$

在物理上，为了方便计算，我们通常选取归一化的代表元，即 $||\psi|| = 1$，此时射线可以表示为相位的等价类：

$$[\psi] = \{ e^{i\theta}\psi : \theta \in \mathbb{R} \}$$

### 定义 0.1.2 (射影空间 / Projective Space)

所有物理状态的集合构成了射影希尔伯特空间 $P(\mathcal{H})$：

$$P(\mathcal{H}) := (\mathcal{H} \setminus \{0\}) / \sim$$

其中 $\sim$ 是上述的等价关系。

### 定理 0.1.1 (物理量的规范不变性)

在 $P(\mathcal{H})$ 中，所有的物理量必须是 **规范不变的 (Gauge Invariant)**。这意味着任何可观测的物理效应（如概率、能量、几何距离）仅仅依赖于射线 $[\psi]$ 本身，而不依赖于我们选择了哪个具体的相角 $\theta$。

例如，两个状态之间的 Fubini-Study 距离 $d_{FS}([\psi], [\phi])$ 是通过取模运算定义的，从而消除了相位的影响：

$$d_{FS}([\psi], [\phi]) = \arccos |\langle \psi | \phi \rangle|$$

这种几何化处理将"相位"剔除出了 **物理实体 (Entity)** 的范畴，将其降级为一种单纯的"坐标选择"或"内部变量"。真正的物理演化，是射线在 $P(\mathcal{H})$ 流形上的轨迹。

---

## 架构师注解 (The Architect's Note)

### 关于：数据封装与接口设计

假如我们将宇宙看作一个巨大的软件系统，那么 `HilbertVector` (希尔伯特矢量) 属于底层的 **私有数据成员 (Private Members)**，而 `ProjectiveState` (射影状态) 才是对外暴露的 **公共对象 (Public Object)**。

* **全局相位 $\theta$ 是系统内部的实现细节：**

    用户（观察者）永远无法直接调用 `getPhase()` 函数。系统内部可能在疯狂地旋转相位，但只要这种旋转不改变射线 $[\psi]$ 的指向（即不改变与其他射线的夹角），对于用户端来说，系统就是"静止"的。

* **物理定律是基于接口编程的：**

    我们不需要关心底层数据是如何存储的（波函数到底是什么）。我们只关心对象之间的交互协议——即 **重叠 (Overlap)** 或 **距离 (Distance)**。Fubini-Study 度规之所以如此重要，是因为它是唯一能够在这个接口层面上定义的、不破坏系统对称性（酉不变性）的"比较函数"。

这种 **"关注点分离" (Separation of Concerns)** 的设计极其高明。它将复杂的量子干涉现象封装在了一个简洁的几何模型中。当我们说"物理是投影"时，我们实际上是在说：**物理定律是运行在 $P(\mathcal{H})$ 这个接口层上的逻辑，而不是运行在底层 $\mathcal{H}$ 数据层上的逻辑。**
