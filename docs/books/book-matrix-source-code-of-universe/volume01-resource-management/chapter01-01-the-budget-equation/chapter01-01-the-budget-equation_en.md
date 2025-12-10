# Chapter 1.1: The Budget Equation

![The Budget Equation](../../assets/budget_equation.png)

**—— The Generalized Parseval Identity**

**"The system's total throughput is constant. Every displacement is a hijacking of computational resources."**

---

## 1. Orthogonal Decomposition of the Tangent Bundle

In the previous chapter, we established through Axiom I a fundamental property of the universe: the total Fubini-Study rate of state evolution is hardcoded as the constant **$c_{FS}$**. This raises a direct question: if the total rate is fixed, how do the diverse physical phenomena we observe in the macroscopic world (such as flying bullets, decaying atoms, entangled particles) arise?

The answer lies in **Allocation**.

To quantify this allocation, we need to delve into the geometric structure of projective Hilbert space. At any moment **$\tau$**, the tangent space **$T_{[\psi]}P(\mathcal{H})$** at the system state **$[\psi(\tau)]$** contains all possible directions of evolution at that moment. We decompose this tangent space into three mutually orthogonal linear subspaces (Sectors), corresponding to different categories of physical degrees of freedom.

### Definition 1.1.1 (Orthogonal Sector Decomposition)

Assuming the evolution on the total Hilbert space **$\mathcal{H}$** is driven by different sets of generators, we can decompose the tangent space as:

$$T_{[\psi]}P(\mathcal{H}) = V_{ext} \oplus V_{int} \oplus V_{env}$$

where:

* **$V_{ext}$ (External Sector):** The subspace spanned by generators such as spatial translations and rotations (e.g., momentum operator **$\hat{P}$**). Since momentum operators are associated with position changes, this sector corresponds to the **"external motion"** we observe in classical physics.

* **$V_{int}$ (Internal Sector):** The subspace spanned by generators of internal degrees of freedom (e.g., rest mass Hamiltonian **$\hat{H}_{rest}$**, spin, gauge charges). This sector corresponds to the **"intrinsic property evolution"** of particles, manifesting macroscopically as the elapse of proper time.

* **$V_{env}$ (Environmental Sector):** When we treat the system as open, the subspace spanned by generators involving interactions with auxiliary environmental degrees of freedom. This sector corresponds to the establishment of **"quantum entanglement"** and information leakage.

Correspondingly, the velocity vector **$\dot{\psi}(\tau)$** describing the total evolution of the universe can be uniquely projected and decomposed into three components:

$$\dot{\psi}(\tau) = \dot{\psi}_{ext}(\tau) + \dot{\psi}_{int}(\tau) + \dot{\psi}_{env}(\tau)$$

And we need to ensure these components are orthogonal in the Fubini-Study metric sense, i.e., **$\langle \dot{\psi}_{\alpha} | \dot{\psi}_{\beta} \rangle_{FS} = 0$** (when **$\alpha \neq \beta$**). This is usually guaranteed by the commutation properties of the underlying generators or specific state structures.

## 2. Theorem: The Generalized Parseval Identity

Based on the Riemannian geometric properties of the Fubini-Study metric and the orthogonal structure above, we derive the most central dynamics equation of this book, which forms the geometric foundation for unifying relativity and quantum mechanics.

### Theorem 1.1 (The Generalized Parseval Identity)

The instantaneous evolution velocity components of the universe strictly satisfy the following quadratic conservation law:

$$v_{ext}^2(\tau) + v_{int}^2(\tau) + v_{env}^2(\tau) \equiv c_{FS}^2$$

where **$v_{\alpha}(\tau) := ||\dot{\psi}_{\alpha}(\tau)||_{FS}$** denotes the instantaneous FS rate in sector **$\alpha$**.

**Proof:**

1. **Premise Introduction:** According to **Axiom I**, the total Fubini-Study modulus of the full differential tangent vector is constant, i.e., **$||\dot{\psi}(\tau)||_{FS}^2 = c_{FS}^2$**.

2. **Linear Decomposition:** Substitute the velocity vector, **$\dot{\psi} = \dot{\psi}_{ext} + \dot{\psi}_{int} + \dot{\psi}_{env}$**.

3. **Inner Product Expansion:** Compute the squared modulus:

   $$||\dot{\psi}||_{FS}^2 = \langle \dot{\psi}_{ext} + \dot{\psi}_{int} + \dot{\psi}_{env}, \dot{\psi}_{ext} + \dot{\psi}_{int} + \dot{\psi}_{env} \rangle_{FS}$$

4. **Orthogonality Utilization:** Since we define sectors **$V_{\alpha}$** as mutually orthogonal, all cross terms (such as **$\langle \dot{\psi}_{ext}, \dot{\psi}_{int} \rangle_{FS}$**) are zero.

5. **Pythagorean Theorem:** What remains are only self-interaction terms, i.e., the sum of squared moduli of each component:

   $$||\dot{\psi}||_{FS}^2 = ||\dot{\psi}_{ext}||_{FS}^2 + ||\dot{\psi}_{int}||_{FS}^2 + ||\dot{\psi}_{env}||_{FS}^2$$

6. **Conclusion:** Substituting the condition from Axiom I, we obtain **$v_{ext}^2 + v_{int}^2 + v_{env}^2 = c_{FS}^2$**.

## 3. Interpretation: The Zero-Sum Game of Computational Resources

This equation is not merely an elegant geometric identity; it is the **fundamental economic principle** governing physical reality. It reveals the "impossible triangle" in physics: changes in position, the elapse of time, and information entanglement are actually **competing** for the same finite resource pool.

We interpret **$c_{FS}^2$** as the **"Information-Velocity Budget"**.

* **$v_{ext}$ (Spatial Bandwidth Cost):** This is the computational power consumed by the system to update an object's position coordinates in external space.

* **$v_{int}$ (Internal Computation Cost):** This is the computational power consumed by the system to maintain the evolution of an object's internal quantum states (such as phase factors). Macroscopically, this corresponds to the existence of **mass** and the elapse of **proper time**.

* **$v_{env}$ (Network Communication Cost):** This is the computational power consumed by the system to handle interactions with the environment (establishing entanglement).

This identity enforces a **Zero-Sum Game**:

You cannot have everything. If you want to move fast in space (increasing **$v_{ext}$**), you must borrow budget from elsewhere. Typically, this budget is deducted from **$v_{int}$**.

### Corollary 1.1.1 (Geometric Reconstruction of Special Relativity)

For an isolated system (ignoring environmental entanglement, setting **$v_{env} \approx 0$**), the equation simplifies to:

$$v_{ext}^2 + v_{int}^2 = c_{FS}^2$$

This explains the physical mechanism of **Time Dilation**.

When a particle accelerates in space (**$v_{ext} \uparrow$**), to maintain equation balance, its internal evolution rate **$v_{int}$** **must** decrease.

When **$v_{ext}$** approaches the limit **$c_{FS}$**, **$v_{int}$** is forced to approach 0. This is why photons (Massless Particles) do not experience time—they are **"Computationally Bankrupt"** entities that spend all their budget on propagation, with no remaining resources to maintain an internal clock.

---

## The Architect's Note

### On: Multithreading on a Single Core

We can imagine the universe as a **single-core CPU**, whose clock frequency corresponds to **$c_{FS}$**. On this CPU, three main threads are running:

1. **I/O Thread ($v_{ext}$):** Responsible for moving data (changing positions).

2. **Worker Thread ($v_{int}$):** Responsible for processing business logic (evolving internal states, i.e., experiencing time).

3. **Network Thread ($v_{env}$):** Responsible for synchronizing with other nodes (entanglement).

The Generalized Parseval Identity tells us: **Because the bus bandwidth is locked, these three threads must time-share or compete for resources.**

* **Idle State:** The I/O thread is suspended (**$v_{ext}=0$**). All computational power is allocated to the Worker thread (**$v_{int}=c_{FS}$**). At this point, your internal clock runs fastest, and your "sense of existence" (mass) is strongest.

* **Full Load Transmission:** Like photons, the I/O thread occupies all bandwidth (**$v_{ext}=c_{FS}$**). The Worker thread is completely **Starved** (**$v_{int}=0$**). For photons, the moment they are emitted and the moment they are absorbed are simultaneous in their own reference frame, because they have never executed a single "internal clock interrupt."

* **Moving Clocks Slow Down:** This is not some mysterious spacetime curvature; it is simply the basic logic of the **Resource Scheduler**. When you run, the system is forced to **Throttle** your internal clock to handle the data stream generated by your displacement. Physics is essentially the **QoS (Quality of Service)** strategy of the universe's operating system.
