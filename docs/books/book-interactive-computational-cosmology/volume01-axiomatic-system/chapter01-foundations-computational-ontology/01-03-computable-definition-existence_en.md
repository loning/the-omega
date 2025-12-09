# Volume I: Axiomatic Framework

**(第一卷：公理化体系)**

## Chapter 1: Foundations of Computational Ontology

**(第一章：计算本体论基础)**

### 1.3 Computable Definition of Existence

**(存在性的可计算定义)**

![Lazy Loading Reality](../../assets/lazy_loading_reality.png)

> **"To exist is to be computed. If an object cannot be generated, indexed, or persisted by a Turing machine within finite steps, then it is physically equivalent to nothingness. Reality is not some metaphysical quality, but a topological stability of information in computational processes."**

After establishing the finiteness of physical reality (Axiom 1.1) and the Turing completeness of dynamics (Axiom 1.2), we need to address the last and most fundamental ontological question in the axiomatic framework of this volume: **What is "Existence"?**

In classical physics, existence is treated as an a priori axiom—particles occupy positions in spacetime, and they are "there" regardless of whether they are observed. However, within the framework of Interactive Computational Cosmology, where the universe is a program running on classical hardware, the definition of "existence" must undergo a profound **Operationalist** turn.

This section will argue that physical existence is essentially a **Persistent Data Structure** in computational systems. We will provide a strict computable definition, reducing the philosophical "ontology" to "accessibility" and "stability" in computer science.

#### 1.3.1 Void and Non-Existence: Uninitialized Memory

Before exploring "existence," we must first define "non-existence." In continuum physics, vacuum is considered a ground state filled with quantum fluctuations. But in computational ontology, vacuum has a purer meaning.

**Definition 1.3.1 (Computational Vacuum)**

The vacuum state $|0\rangle$ corresponds to a memory pool in the computational system that is **Uninitialized** or **initialized to NULL**. It contains no valid information and consumes no computational resources for maintaining structure.

In this sense, "non-existence" is not absolute nothingness, but a state of being **Uncomputed**. Just as unexplored map regions in video games do not exist in video memory but only in the potential of generation algorithms, unobserved regions in the physical universe exist only in the form of **wave functions (generation rules)**, not as entities.

#### 1.3.2 The Dual Criteria of Existence: Computability and Persistence

What kind of information structure qualifies as a "physical entity"? We propose two necessary criteria:

1.  **Constructibility Criterion**: The object must be generable from the ground state by the universe's underlying evolution operator $\hat{U}$ through finite steps of logic gate operations. This excludes all uncomputable mathematical objects (such as Chaitin's constant $\Omega$) from physical existence.

2.  **Stability Criterion**: The object must maintain the integrity of its information structure during system evolution, i.e., resist environmental decoherence or garbage collection mechanisms.

Based on this, we give the formal definition of existence:

**Definition 1.3.2 (Physical Existence)**

A quantum state $|\psi\rangle$ is called "physically existent" within a time window $\Delta t$ if and only if it is an **Approximate Eigenstate** of the system Hamiltonian (or effective generator of the evolution operator), and its corresponding eigenvalue maintains real stability within $\Delta t$.

$$
\hat{H}_{eff} |\psi\rangle \approx E |\psi\rangle
$$

This means that "existence" is **repetition**. Only when a computational process falls into some **Self-Referential Loop** or **Topological Knot**, thereby exhibiting **Invariance** on macroscopic time scales, do we say that an "object" exists there.

* **Fermions**: Highly stable topological solitons in computational networks, they are **Persisted** objects in the system.

* **Bosons**: Instantaneous message packets transmitted between systems, their existence is often transient, serving interactions.

#### 1.3.3 Observation as Instantiation: From Class to Object

In object-oriented programming (OOP), we distinguish between **Class** and **Object/Instance**. This distinction precisely corresponds to **superposition states** and **collapsed states** in quantum mechanics.

* **Potential Existence**: The wave function $|\Psi\rangle$ is like a "class" definition. It describes where a particle "might" be and what properties it "might" have, but it does not allocate specific coordinate values in physical memory. This is a **weak existence**.

* **Actual Existence**: Observation (measurement) behavior is equivalent to the **Instantiation** operation in programming (`new Particle()`). When an oracle (consciousness) intervenes and selects a specific historical branch, the system performs **Just-in-Time (JIT) compilation**, converting abstract probability distributions into definite spacetime coordinate data.

Therefore, **physical reality is not pre-existing, but Generated on Demand.**

The moon we see, when unobserved, is merely texture files and physical parameters stored on a hard drive (class); only when we look up at it does the rendering engine load it into video memory, instantiating it as a luminous sphere (object).

#### 1.3.4 Levels of Reality: Quantification of Ontology

Based on the above definition, existence is no longer a binary concept (yes or no), but a **continuous spectrum**, whose intensity depends on **Computational Depth** and **Degree of Entanglement**.

1.  **Transient Reality**: Such as virtual particles or quantum fluctuations. Their computational depth is extremely shallow, and their lifetime is extremely short, similar to temporary variables in computational processes, discarded by the system after use.

2.  **Consensus Reality**: Such as macroscopic objects (tables, planets). They are Nash equilibrium points in multi-agent games. Countless observers' mutual measurements lock their states, giving them extremely high "existence weight" and "hardness."

3.  **Ultimate Reality**: The underlying code of the system (physical laws themselves). They are unmodifiable read-only memory (ROM), constituting the background of all other forms of existence.

**Corollary 1.3.1 (Unity of Idealism and Materialism)**

In this framework, matter (computed data) and consciousness (the process executing computation) are inseparable. Without conscious observation (input), data forever remains in an unrendered potential state; without material feedback (output), consciousness falls into empty idling. **Existence is the interface between the computational system and the user.**

In summary, Chapter 1 constructs a complete **Computational Ontology**: the universe is a finite, Turing-complete, interactive computational system, and all things are persistent data structures instantiated by observation behaviors in this system. This establishes a solid logical foundation for Chapter 2's exploration of the Holographic Equivalence Principle.
