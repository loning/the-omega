# Volume I: Axiomatic Framework

**(第一卷：公理化体系)**

## Chapter 1: Foundations of Computational Ontology

**(第一章：计算本体论基础)**

### 1.1 Axiom of Finite Information

**(有限信息公理)**

![Finite Information Limit](../../assets/finite_info_bound.png)

> **"Physical reality does not contain infinities. Infinities are merely mathematical approximations we introduce for computational convenience. When these approximations are mistaken for ontology, physics falls into pathology."**

In the first step of constructing an interactive computational cosmology model, we must confront the greatest ontological assumption in classical physics and quantum field theory: the Continuum Hypothesis. This assumption holds that spacetime is infinitely divisible, and physical fields are defined at arbitrarily small scales. However, it is precisely this assumption that leads to the endless ultraviolet divergences (UV Divergence) and singularity problems in modern physics.

To rebuild the foundations of physics, we introduce the first core axiom of this theoretical framework—the **Axiom of Finite Information**.

#### 1.1.1 The Information Catastrophe of the Continuum

If we treat spacetime as a manifold of the real number set $\mathbb{R}^4$, then even a tiny cube with side length $L$ contains uncountably infinitely many points. If physical fields (such as the electromagnetic field) have independent degrees of freedom at each point, then the amount of information within this finite volume would be infinite.

This "infinite information density" might be tolerable in classical mechanics (since we assume infinite measurement precision), but in physical reality combining general relativity and quantum mechanics, it causes catastrophic consequences:

1.  **Ultraviolet Divergences**: In quantum field theory, integrating loop diagrams requires summing over all possible momenta $k$. If space is continuous, momentum $k$ can approach infinity (corresponding to wavelength $\lambda \to 0$), causing calculation results (such as vacuum zero-point energy) to diverge to infinity.

2.  **Singularity Problems**: General relativity predicts that at the center of black holes or at the moment of the Big Bang, matter density approaches infinity. This is actually a sign of mathematical model breakdown, not a feature of physical reality.

The "infinity" in physics has never been observed; it is merely an error report issued by mathematical models when they exceed their applicable scope.

#### 1.1.2 Bekenstein Bound: The Upper Limit of Bits in the Physical World

We not only reject infinity philosophically, but within physics itself, we have found conclusive evidence negating infinity. This evidence comes from black hole thermodynamics, specifically manifested as the **Bekenstein Bound**.

Jacob Bekenstein pointed out that for any spherical spatial region with radius $R$ containing energy $E$, the maximum entropy $S$ (i.e., maximum information content) it can contain has a strict upper bound:

$$
S \le \frac{2\pi k_B R E}{\hbar c}
$$

When matter collapses to form a black hole, this entropy value reaches its limit, namely the **Bekenstein-Hawking Entropy**, whose value is proportional to the surface area $A$ of the black hole horizon:

$$
S_{BH} = \frac{k_B c^3}{4G\hbar} A = \frac{A}{4 l_P^2}
$$

where $l_P = \sqrt{G\hbar/c^3}$ is the Planck length.

This formula reveals a remarkable fact: **the information capacity of physical systems is not infinite, but strictly limited by the geometric area of their boundaries.**

This implies:

1.  **Discreteness**: Each Planck area unit ($l_P^2$) can store approximately only 1/4 of a bit of information. Space is not a continuous container, but a discrete storage medium.

2.  **Finiteness**: For any finite macroscopic region in the universe, no matter how we compress matter, the total number of quantum states $W = e^S$ it contains is a finite integer.

#### 1.1.3 Local Finiteness of Hilbert Space

Based on the Bekenstein Bound, we can derive an important theorem about quantum mechanical state space.

**Theorem 1.1.1 (Hilbert Space Dimension Finiteness Theorem)**

For any causally closed region (Causal Diamond) in the physical universe with finite boundary area $A$, the Hilbert space $\mathcal{H}_{local}$ describing all possible physical states within it must have finite dimension $D$, satisfying:

$$
\dim(\mathcal{H}_{local}) \le \exp\left(\frac{A}{4 l_P^2}\right)
$$

**Proof Outline**: If the dimension of the Hilbert space is infinite, we can always construct a mixed state (such as an equal-probability mixture of all basis states) whose von Neumann entropy $S = -\text{Tr}(\rho \ln \rho)$ would tend to infinity, thereby violating the Bekenstein Bound. To ensure the self-consistency of the second law of thermodynamics and gravitational theory, the physical state space must be "truncated" to finite dimensions.

#### 1.1.4 Axiomatic Formulation and Ontological Implications

In summary, we introduce the first core axiom in this book as the cornerstone for rebuilding the edifice of physics:

> **Axiom of Finite Information**

> Physical reality consists of discrete information units. For any finite macroscopic spacetime volume, the independent physical degrees of freedom it contains are finite. There are no physical quantities with infinite precision real numbers, and spacetime structure has a natural cutoff (Natural Cutoff) at the Planck scale.

This axiom establishes the **Computational Ontology** stance of this book:

* **Universe as Computation**: The universe is essentially equivalent to a Quantum Cellular Automaton (QCA) running on a vast but finite lattice network.

* **De-continuization**: Differential equations are not fundamental; difference equations are. The "fields" in field theory are merely statistical approximations of discrete qubit arrays in the long-wavelength limit.

* **Resource Constraints**: Physical laws manifest in their current form (such as the speed of light limit, uncertainty principle) because the universe computer must operate under constraints of **Finite Memory** and **Finite Bandwidth**.

In the following chapters, we will see that it is precisely this simple "finiteness" constraint that derives the probabilistic nature of quantum mechanics and the spacetime curvature of general relativity.
