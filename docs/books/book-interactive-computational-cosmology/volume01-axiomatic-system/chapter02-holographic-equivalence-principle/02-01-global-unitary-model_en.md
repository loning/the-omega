# Volume I: Axiomatic Framework

**(第一卷：公理化体系)**

## Chapter 2: The Holographic Equivalence Principle

**(第二章：全息等价原理)**

> **"From the ultimate perspective of physics, 'possibility' is a pseudo-concept. For the entire universe, all possible histories already exist eternally as superpositions in Hilbert space. The true puzzle is not how the universe chose a path, but why local observers can only see one."**

This chapter will expound the core theorem of Interactive Computational Cosmology (ICC)—the **Holographic Equivalence Principle**. To prove this principle, we first need to strictly define the two endpoints of the dual relationship. This section will first construct the physical model from God's perspective, namely the **Global Unitary Model (QTM)**.

### 2.1 The Global Unitary Model

**(全局幺正演化模型)**

![Global Unitary Crystal](../../assets/global_qtm_crystal.png)

In Chapter 1, we established the finiteness and computability of physical reality. Based on this, we can construct a complete mathematical model describing the entire universe (including all matter, energy, and observers). In this model, we treat the universe as a **Quantum Turing Machine (QTM)** that is isolated from the outside world and runs self-consistently.

This model represents the ideal objective perspective pursued by physics—the ontology of the universe after removing all subjective observational effects. We will see that from this perspective, the universe is a strictly deterministic, information-conserving, static structure containing all historical branches.

#### 2.1.1 Global Hilbert Space

According to the **Axiom of Finite Information**, the total degrees of freedom of the universe are finite. Let the universe contain $N$ basic information units (qubits), then the global Hilbert space $\mathcal{H}_{total}$ can be defined as the tensor product of $N$ local two-dimensional Hilbert spaces:

$$
\mathcal{H}_{total} = \bigotimes_{x \in \Lambda} \mathcal{H}_x \cong (\mathbb{C}^2)^{\otimes N}
$$

where $\Lambda$ is a discrete spacetime lattice. The dimension of this space $D = 2^N$ is enormous but not infinite. The **Global Quantum State** $|\Psi(t)\rangle$ of the universe at any moment is a unit vector in $\mathcal{H}_{total}$.

This state vector $|\Psi(t)\rangle$ contains the positions, momenta, spins of all particles in the universe, as well as all complex entanglement relationships. It is a **complete description** of physical reality. According to the linear superposition principle of quantum mechanics, it can be expanded as a linear combination of a set of orthogonal basis states (such as all possible classical configurations):

$$
|\Psi(t)\rangle = \sum_{i=1}^{D} c_i(t) |World_i\rangle
$$

Here, each $|World_i\rangle$ represents a specific classical universe snapshot. The coefficients $c_i(t)$ are complex probability amplitudes, whose squared moduli $|c_i|^2$ represent the weight of that configuration in the global wave function.

#### 2.1.2 Eternal Dynamics: Global Unitary Operator $\hat{U}$

In the QTM model, the universe is a closed system that does not interact with any external environment. Therefore, its evolution strictly follows the **Unitarity** of quantum mechanics.

We encode physical laws as a global unitary evolution operator $\hat{U}$. The evolution equation of the universe state with discrete time steps $t$ is:

$$
|\Psi(t+1)\rangle = \hat{U} |\Psi(t)\rangle
$$

This equation is the discrete version of the Schrödinger equation. The operator $\hat{U}$ must satisfy the unitary condition $\hat{U}^\dagger \hat{U} = I$, which ensures the conservation of the norm of the global wave function:

$$
\langle \Psi(t+1) | \Psi(t+1) \rangle = \langle \Psi(t) | \hat{U}^\dagger \hat{U} | \Psi(t) \rangle = 1
$$

**Physical Implication: Information Conservation**

Unitary evolution means that the evolution of the global quantum state is **Reversible**. If we know the current state $|\Psi(t)\rangle$ and the physical law $\hat{U}$, we can not only perfectly predict any future state $|\Psi(t+n)\rangle$, but also perfectly retrodict past states $|\Psi(t-n)\rangle = (\hat{U}^\dagger)^n |\Psi(t)\rangle$.

In the QTM model, **information is never created nor destroyed**. What we call "entropy increase" or "forgetting" is merely information diffusing from local degrees of freedom into global entanglement correlations. For the omniscient God's perspective (possessing the computational capability of $\hat{U}^\dagger$), the von Neumann entropy of the universe always remains zero (pure state).

#### 2.1.3 Block Universe and Feynman Path Summation

If we examine the expansion of $|\Psi(t)\rangle$ along the time axis, the QTM model presents a **Block Universe** picture.

Using Feynman path integrals (path summation in the discrete architecture), the evolution from initial time $t=0$ to time $T$ can be expressed as coherent superposition of all possible historical paths:

$$
|\Psi(T)\rangle = \sum_{\text{all paths } \gamma} \mathcal{A}[\gamma] |Final_\gamma\rangle
$$

where $\mathcal{A}[\gamma]$ is the complex amplitude of path $\gamma$, determined by the action $e^{iS}$.

In this picture:

1.  **Multiple Histories Coexist**: All historical paths consistent with physical laws (e.g., "cat dead" and "cat alive") have non-zero amplitudes in the wave function. They are parallel existing realities.

2.  **No Collapse**: Since the system is closed, there is no external observer to perform measurements, so the wave function never collapses. Schrödinger's cat forever remains in a superposition of life and death.

3.  **Static Spacetime**: The time parameter $t$ is merely an index in Hilbert space. The entire historical structure $(|\Psi(0)\rangle, |\Psi(1)\rangle, \dots, |\Psi(T)\rangle)$ is like a completed crystal, statically suspended in logical space.

#### 2.1.4 The Absence of Subjective Experience

Although the QTM model is mathematically perfectly self-consistent, it faces a fatal explanatory gap: **it cannot derive the concepts of "now" and "I."**

In a wave function containing all possibilities, all moments are equal, and all historical branches are equal. There is no special pointer marking "now is 2025" or "I see the cat alive."

* **No "Now"**: Because all states at different $t$ are rigidly connected by $\hat{U}$, past and future are ontologically equivalent.

* **No "Choice"**: Because all branches occur, so-called choices are illusions. A person walking left at a fork and a person walking right are merely different components in the global wave function.

This leads to the core question of this book: **Why do we, as observers within the universe, experience not parallel multiple histories, but a single, linear, random time flow?**

To answer this question, we need to introduce the second endpoint of the duality—the **Classical Interactive Automaton Model (CITM)**, which will be detailed in the next section.
