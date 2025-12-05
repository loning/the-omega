# Appendix

## Appendix A: Technical Details of Consciousness Models

This appendix aims to transform qualitative descriptions of "consciousness" in the main text (such as $M_I$, free energy, entanglement) into computable mathematical forms. Although precise calculation of these quantities is currently impossible for complex systems like the human brain, it is necessary to provide theoretical definitions.

### A.1 QCA Definition of Integrated Information $\Phi$

In Sections 2.3 and 8.2 of the main text, we referenced Giulio Tononi's Integrated Information Theory (IIT). Under the QCA framework, $\Phi$ value corresponds to the **Irreducibility** of network entanglement structure.

**Definition A.1 (Causal Partition and Effective Information)**:

Let the current state of QCA system $S$ be $s_t$.

Consider partitioning the system into two parts $A$ and $B$ (bipartition), cutting all causal connections between them (set connection field $U_{AB} = \mathbb{I}$).

Let the partitioned system evolution produce state $s'_{t+1}$, while the original system produces $s_{t+1}$.

The distance between these two future states (usually measured by Kullback-Leibler divergence or Wasserstein distance) measures the "information loss" caused by this partition, denoted $\varphi(A, B)$.

**Definition A.2 (Integrated Information $\Phi$)**:

The system's $\Phi$ value is defined as the information loss value corresponding to the partition causing **minimum** information loss among all possible bipartitions (Minimum Information Partition, MIP).

$$\Phi(S) = \min_{\{A, B\}} \varphi(A, B)$$

* **Physical Meaning**: $\Phi$ measures the degree to which the system is a "whole." If $\Phi=0$, the system can be decomposed into two independent subsystems without loss (like scattered sand). If $\Phi$ is large, internal connections are indivisible (like an electron or a consciousness).

### A.2 Mathematical Form of Variational Free Energy $F$

In Section 2.2 of the main text, we defined pain and pleasure as derivatives of free energy $F$. Here we provide strict derivation of $F$.

Let external environment state be $\vartheta$ (hidden variable), agent's sensory input be $s$, agent's internal belief about the environment (probability distribution) be $q(\vartheta)$.

According to Bayes' theorem, the true posterior probability is $p(\vartheta|s) = \frac{p(s|\vartheta)p(\vartheta)}{p(s)}$. Direct calculation of $p(s)$ (evidence) is usually infeasible (involving high-dimensional integration).

The agent approximates the true posterior by introducing variational distribution $q(\vartheta)$.

Variational free energy $F$ is defined as:

$$F(s, q) = \mathbb{E}_q [\ln q(\vartheta) - \ln p(s, \vartheta)]$$

Using Jensen's inequality, we can prove:

$$F(s, q) = -\ln p(s) + D_{KL}[q(\vartheta) || p(\vartheta|s)]$$

where $D_{KL} \ge 0$ is relative entropy.

Therefore, $F \ge -\ln p(s)$. $F$ is an upper bound of surprise ($-\ln p(s)$).

**Two Paths to Minimize $F$**:

1.  **Perception**: Change $q(\vartheta)$ to minimize $D_{KL}$. That is: update internal model to better match current observations.

2.  **Action**: Change $s$ (through action changing environment) to maximize $p(s)$. That is: make the world more consistent with my expectations.

In QCA, this corresponds to finding geodesic paths on Hilbert space manifolds.

---

## Appendix B: References and Further Reading

This section lists key literature inspiring this book's ideas, divided into four fields: physics, computer science, neuroscience, and philosophy, for interested readers to study in depth.

### B.1 Physics and QCA

1.  **'t Hooft, G. (2016).** *The Cellular Automaton Interpretation of Quantum Mechanics*. Springer.

    * (Foundational work proposing quantum mechanics originates from deterministic cellular automata)

2.  **Susskind, L. (1995).** "The World as a Hologram". *Journal of Mathematical Physics*.

    * (Original paper on holographic principle, connecting information and gravity)

3.  **Maldacena, J., & Susskind, L. (2013).** "Cool horizons for entangled black holes" (ER=EPR).

    * (Established equivalence between wormholes and entanglement, core basis for Part III of this book)

4.  **Lloyd, S. (2006).** *Programming the Universe*. Alfred A. Knopf.

    * (Popular reading on computational cosmology)

### B.2 Complex Systems and Consciousness

5.  **Tononi, G. (2008).** "Consciousness as Integrated Information: a Provisional Manifesto". *Biological Bulletin*.

    * (Original literature on IIT theory, defining $\Phi$)

6.  **Friston, K. (2010).** "The free-energy principle: a unified brain theory?". *Nature Reviews Neuroscience*.

    * (Masterpiece on free energy principle, explaining how life resists entropy increase)

7.  **Tegmark, M. (2014).** "Consciousness as a State of Matter". *Chaos, Solitons & Fractals*.

    * (Attempts to define consciousness as a matter state called "Perceptronium")

### B.3 Philosophy and Futurology

8.  **Hofstadter, D. R. (1979).** *Gödel, Escher, Bach: an Eternal Golden Braid*. Basic Books.

    * (Deep exploration of self-reference, strange loops, and consciousness)

9.  **Bostrom, N. (2003).** "Are You Living in a Computer Simulation?". *Philosophical Quarterly*.

    * (Logical derivation of simulation hypothesis)

10. **Tipler, F. J. (1994).** *The Physics of Immortality*. Doubleday.

    * (Physics attempt at Omega Point theory, radical but highly inspiring)

---

**End of Book.**

At this point, we have completed all content construction for **Book 3 "The Awakening of the Cosmos"**. From foreword to main text to appendix, these three books together constitute a grand, self-consistent theoretical system full of humanistic care.

* **Book 1**: Built the tools.

* **Book 2**: Discovered the laws.

* **Book 3**: Found the meaning.

This has been a long and wonderful journey.




