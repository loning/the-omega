# Volume II: Emergence of Spacetime

**(第二卷：时空的涌现机制)**

## Chapter 3: Limits of Causal Connectivity

**(第三章：因果连通性的极限)**

### 3.1 Lieb-Robinson Bound and the Speed of Light

**(李-罗宾逊速度与光速)**

![Lieb-Robinson Cone](../../assets/lieb_robinson_cone.png)

> **"The speed of light is not the upper limit of object motion, but the bandwidth limit of causal relationships propagating in computational networks. Spacetime is not a pre-existing container, but a dynamic graph woven by local interactions."**

In Volume I, we established the computational ontology of physical reality: the universe is an interactive computational system running on finite Hilbert space. However, for this abstract algebraic structure to manifest as the geometrically extended physical world we perceive, the system must possess a **Topological Structure**.

The core constraint of this topological structure is **Locality**. This section will prove that as long as the computational system follows local interaction rules, there must be a maximum speed limit for information propagation within it. This limit is called the **Lieb-Robinson Velocity** in mathematical physics, and manifests as the **Speed of Light ($c$)** in macroscopic physics.

#### 3.1.1 Interaction Graph and Locality of the Hamiltonian

In continuum physics, distance is an axiomatic geometric concept. But in Interactive Computational Cosmology (ICC), distance is derived. We first define the system's **Interaction Graph** $G=(V, E)$.

* **Vertex Set $V$**: Represents basic information units in the universe (such as qubits or QCA lattice sites).

* **Edge Set $E$**: Represents direct logic gate operations or entanglement exchanges allowed between basic units.

The system's dynamics is driven by a local Hamiltonian $\hat{H}$:

$$\hat{H} = \sum_{X \subset V} \hat{h}_X$$

where $\hat{h}_X$ is a local operator acting on subregion $X$. If physical laws are local (which is an inevitable consequence of computational resource constraints, since fully connected networks require exponential bus resources), then interaction terms $\hat{h}_X$ are non-zero only when the diameter of $X$ is small.

This algebraic locality not only defines "neighbors" but also defines how causal relationships propagate. Information cannot instantaneously jump to arbitrary nodes in the network; it must transmit hop-by-hop along edges.

#### 3.1.2 Mathematical Formulation of the Lieb-Robinson Bound

In 1972, Elliott Lieb and Derek Robinson proved a fundamental theorem about quantum lattice systems. This theorem states that even for non-relativistic quantum many-body systems, as long as interactions are short-range, a finite upper limit for information propagation speed spontaneously emerges.

**Theorem 3.1.1 (Lieb-Robinson Bound)**

For quantum systems defined on lattices with short-range interactions, there exist constants $v_{LR}$ (Lieb-Robinson velocity), $\xi$ (correlation length), and $C$ such that for any two spatially separated local operators $\hat{A}_x$ (at node $x$) and $\hat{B}_y$ (at node $y$), the norm of their commutator under Heisenberg evolution satisfies:

$$
\| [\hat{A}_x(t), \hat{B}_y(0)] \| \le C \|A\| \|B\| \exp\left( -\frac{d(x,y) - v_{LR}|t|}{\xi} \right)
$$

where $d(x,y)$ is the graph distance between nodes.

**Physical Interpretation**:

The commutator $[\hat{A}_x(t), \hat{B}_y(0)]$ measures whether operations at $y$ can affect observation results at $x$ at time $t$, i.e., **signal transmission capability**.

The above inequality shows that outside the **Light Cone** defined with slope $v_{LR}$ (i.e., $d(x,y) > v_{LR}|t|$), causal correlations decay exponentially.

Although mathematically this decay is not strictly zero (an artifact of continuous-time evolution), under the precision limits of physical measurements, this constitutes an **Effective Causal Horizon**.

#### 3.1.3 Strict Light Cone in QCA: System Bus Bandwidth Limit

If we adopt the more fundamental **Quantum Cellular Automaton (QCA)** model (as defined in Volume I's CITM foundation), time evolution is discrete. In this case, the Lieb-Robinson bound becomes stricter.

Let the single-step update operator of QCA be $\hat{U}$, and $\hat{U}$ can be decomposed into local logic gates acting on neighboring nodes. Then, after $t$ time steps, information from a node can **strictly** only propagate to a region at distance $R \cdot t$, where $R$ is the interaction radius of local gates.

$$
\text{If } d(x,y) > R \cdot t, \text{ then } [\hat{A}_x(t), \hat{B}_y(0)] \equiv 0
$$

From this, we derive the **ontological definition of physical speed of light $c$**:

$$
c \equiv \frac{\text{Maximum Information Propagation Radius}}{\text{Minimum Logic Update Period}} = \frac{l_P}{t_P}
$$

In this framework, the constancy of the speed of light is no longer a puzzling assumption, but a direct manifestation of **System Bus Bandwidth**.

* **Bus Frequency**: The system's Planck clock frequency is locked.

* **Bus Width**: Within each clock cycle, information can only be transferred between adjacent memory addresses (lattice sites).

Therefore, any attempt to exceed the speed of light is computationally equivalent to trying to transfer data to addresses outside the bus architecture within one cycle, which will be directly intercepted by underlying hardware logic (physical laws) and throw an exception (causality violation).

#### 3.1.4 Special Relativity as a Resource Management Protocol

Through the Lieb-Robinson bound, we reconstruct special relativity as a **resource management protocol for distributed systems**.

Classical physics believes the speed of light limits material motion, while in computational cosmology, the speed of light limit is to **prevent Computational Avalanche**. If action-at-a-distance (infinite propagation speed) were allowed, any tiny perturbation in the network would instantly couple to the entire universe, causing the system's state update complexity to explode from $O(N)$ to $O(N^2)$ or higher, leading to system collapse.

**Corollary 3.1.1 (Causal Decoupling)**

The existence of the speed of light divides the universe into countless relatively independent **Causal Diamonds**. This allows the system to process local tasks in parallel without waiting for global synchronization. Relativity is not just a theory about motion; it is a **Partition Tolerance Protocol** that the universe, as a supercomputer, must obey to achieve **Massively Parallel Computing**.

In summary, spacetime structure is not an a priori background, but a dynamic network woven by the boundaries of interaction locality. The speed of light $c$ is the hard bandwidth limit for information flow on this network. In the next section, we will explore how this bandwidth limit maintains consistency of causal topology between different observers' reference frames through Lorentz transformations.
