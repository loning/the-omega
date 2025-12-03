# Appendix B: Geometric Proof of Naimark's Dilation

In the final chapter of *Vector Cosmology II*, we presented an ultimate vision full of Zen: the spiral is not the opposite of the circle; the spiral is merely a projection of a higher-dimensional great circle onto a lower-dimensional subspace. This view is not literary rhetoric in mathematics, but a direct physical application of **Naimark's Dilation Theorem** in functional analysis.

This appendix will provide a rigorous geometric proof of this "great circle containing small circle" structure, starting from operator theory in Hilbert space. We will show that any seemingly open, dissipative, or non-unitary evolution trajectory must be a **Contraction** or **Projection** of some higher-dimensional closed system's unitary evolution.

## B.1 Non-Unitary Evolution of Open Systems

In the main text, we described two characteristics of the spiral universe:

1.  **Dissipation**: Information flows to the environment (entropy increase).

2.  **Growth**: The system absorbs negative entropy from the environment (life/civilization).

In quantum mechanics, this corresponds to an **Open Quantum System**. Its state evolution is no longer described by a unitary operator $U(\tau)$ (satisfying $U^\dagger U = I$), but by a **Contraction Semigroup** or **Completely Positive Trace-Preserving (CPTP) Map** $\mathcal{E}_\tau$.

If we only focus on the system's internal Hilbert space $\mathcal{H}_S$, we find that the total vector's modulus (or coherence) is not conserved:

$$||\mathcal{E}_\tau |\psi_S\rangle || \ne || |\psi_S\rangle ||$$

Geometrically, this means the trajectory no longer stays on the unit sphere of $\mathcal{H}_S$, but curls inward (spiral downward) or diverges outward when external pumping is introduced (spiral upward). This is precisely the "spiral" picture we saw in the second book.

## B.2 Naimark's Theorem: Finding the Larger Space

The core insight of Naimark's theorem (and its subsequent generalizations, such as Stinespring dilation) is: **Non-conservation is due to too narrow a view.**

**Theorem Statement:**

Let $\mathcal{H}_S$ be a Hilbert space, and $\{V_\tau\}$ be a one-parameter contraction semigroup on it (i.e., the operator family describing spiral evolution).

Then, there necessarily exists a larger Hilbert space $\mathcal{K}$ such that $\mathcal{H}_S$ is a subspace of $\mathcal{K}$ ($\mathcal{H}_S \subset \mathcal{K}$), and on $\mathcal{K}$ there exists a unitary group (i.e., the operator family describing great circle evolution) $\{U_\tau\}$ satisfying:

$$V_\tau = P_S U_\tau P_S$$

where $P_S$ is the orthogonal projection operator from the large space $\mathcal{K}$ back to the small space $\mathcal{H}_S$.

**Physical Translation:**

This mathematical formula is the most stunning physical metaphor of the entire book:

* **$V_\tau$ (Spiral)**: The physical laws we observe in the macroscopic world, seemingly with birth and death.

* **$U_\tau$ (Great Circle)**: The actually occurring, eternally conserved evolution in the global space ($\mathcal{K} = \mathcal{H}_S \oplus \mathcal{H}_{env}$).

* **$P_S$ (Projection)**: Our observational limitations. Because we are part of the system, we can only "see" the component projected onto $\mathcal{H}_S$.

This rigorously proves: **Any spiral trajectory is the shadow of high-dimensional circular motion.**

## B.3 Geometric Reconstruction of the Environmental Term

The **environment velocity $v_{env}$** we introduced in the first book finds its precise geometric definition in Naimark dilation.

In the global space $\mathcal{K}$, the unitary evolution $U_\tau$ preserves the total modulus, satisfying the global FS capacity identity:

$$||\dot{\Psi}_{total}||_{FS}^2 = C_{TOTAL}^2$$

When we project it back to the system space $\mathcal{H}_S$, the tangent vector is decomposed as:

$$|\dot{\Psi}_{total}\rangle = |\dot{\psi}_{sys}\rangle + |\dot{\psi}_{env}\rangle$$

where:

* **$|\dot{\psi}_{sys}\rangle \in \mathcal{H}_S$**: This is the system evolution velocity we observe (containing $v_{ext}$ and $v_{int}$).

* **$|\dot{\psi}_{env}\rangle \in \mathcal{H}_{env}$**: This is the environmental evolution velocity orthogonal to the system.

According to the Pythagorean theorem (orthogonality in Hilbert space):

$$||\dot{\psi}_{sys}||^2 + ||\dot{\psi}_{env}||^2 = ||\dot{\Psi}_{total}||^2$$

This directly leads to the extended capacity identity we used in the main text:

$$v_{sys}^2(\tau) + v_{env}^2(\tau) = C_{TOTAL}^2$$

**Conclusion:**

Naimark's theorem mathematically guarantees from the bottom up that the "environment" is not an arbitrary trash can, but a necessary piece completing the geometric structure.

* When the system exhibits "dissipation," it is actually the vector of $v_{sys}$ rotating toward the $\mathcal{H}_{env}$ direction.

* When the system exhibits "ascension" or "absorption of negative entropy," it is actually the vector rotating back from the $\mathcal{H}_{env}$ direction to the $\mathcal{H}_S$ direction.

In that invisible $\mathcal{K}$ space, there is no dissipation, no growth, only **rotation of angles**. This is the geometric essence of "The Palm of the Buddha."

